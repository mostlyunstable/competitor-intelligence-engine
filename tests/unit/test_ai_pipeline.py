"""Tests for the AI analysis pipeline."""

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.ai.application.pipeline import AIPipeline
from app.ai.domain.entities import AIInsightResponse, ProviderHealth
from app.ai.domain.provider import LLMProvider
from app.ai.exceptions import PipelineError, ValidationError
from app.ai.prompts.builder import prompt_builder


# ─── Fixtures ────────────────────────────────────────────────────────────────

class MockProvider(LLMProvider):
    """Mock LLM provider for testing."""

    def __init__(self, response: dict | None = None, error: Exception | None = None):
        self._response = response or self._valid_response()
        self._error = error
        self.call_count = 0
        self.last_prompt = ""
        self.last_schema = {}

    @staticmethod
    def _valid_response() -> dict:
        return {
            "summary": "American Home Shield is a leading home warranty provider with competitive pricing.",
            "key_differentiators": ["Wide coverage", "24/7 support", "National presence"],
            "market_position": "AHS is positioned as a premium home warranty provider in the US market.",
            "confidence_score": 0.85,
            "pricing_analysis": {"overview": "Competitive pricing", "price_range": "$300-$600/yr", "positioning": "mid-range"},
            "feature_gaps": ["Limited international coverage"],
            "strategic_moves": ["Expanded HVAC coverage"],
            "recommendations": ["Compete on price", "Improve digital experience"],
            "latest_updates": ["New pricing tiers launched"],
        }

    async def generate_structured_insight(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        self.call_count += 1
        self.last_prompt = prompt
        self.last_schema = schema
        if self._error:
            raise self._error
        return self._response

    async def health(self) -> ProviderHealth:
        return ProviderHealth(healthy=True, provider="mock", model="mock-model", latency_ms=10)

    @property
    def provider_name(self) -> str:
        return "mock"

    @property
    def model_name(self) -> str:
        return "mock-model"


@pytest.fixture
def provider() -> MockProvider:
    return MockProvider()


@pytest.fixture
def pipeline(provider: MockProvider) -> AIPipeline:
    return AIPipeline(provider)


@pytest.fixture
def sample_raw_data() -> dict[str, Any]:
    return {
        "name": "American Home Shield",
        "url": "https://www.ahs.com",
        "services": [
            {"name": "HVAC Repair", "description": "Heating and cooling repair services"},
            {"name": "Plumbing", "description": "Plumbing repair and maintenance"},
        ],
        "pricing": [
            {"service": "Shield Silver", "price": 299, "currency": "USD", "category": "plan"},
            {"service": "Shield Gold", "price": 399, "currency": "USD", "category": "plan"},
        ],
        "content": [
            {"title": "Our Plans", "type": "page", "url": "https://www.ahs.com/plans"},
        ],
        "social": [
            {"platform": "facebook", "username": "ahs", "url": "https://facebook.com/ahs"},
        ],
        "extracted": {
            "team": [{"name": "CEO", "title": "Chief Executive Officer"}],
            "assets": ["logo.png"],
        },
    }


# ─── prepare_context tests ──────────────────────────────────────────────────

class TestPrepareContext:
    def test_maps_name_and_url(self, pipeline: AIPipeline) -> None:
        raw = {"name": "AHS", "url": "https://ahs.com"}
        ctx = pipeline.prepare_context(raw)
        assert ctx["competitor_name"] == "AHS"
        assert ctx["competitor_url"] == "https://ahs.com"

    def test_defaults_for_missing_fields(self, pipeline: AIPipeline) -> None:
        ctx = pipeline.prepare_context({})
        assert ctx["competitor_name"] == "Unknown"
        assert ctx["competitor_url"] == ""
        assert ctx["services"] == []
        assert ctx["pricing"] == []
        assert ctx["content"] == []
        assert ctx["social"] == []
        assert ctx["extracted_data"] == {}

    def test_normalizes_list_fields(self, pipeline: AIPipeline, sample_raw_data: dict) -> None:
        ctx = pipeline.prepare_context(sample_raw_data)
        assert len(ctx["services"]) == 2
        assert len(ctx["pricing"]) == 2
        assert len(ctx["content"]) == 1
        assert len(ctx["social"]) == 1
        assert "team" in ctx["extracted_data"]

    def test_non_list_services_becomes_empty(self, pipeline: AIPipeline) -> None:
        ctx = pipeline.prepare_context({"services": "not a list"})
        assert ctx["services"] == []

    def test_non_dict_extracted_becomes_empty(self, pipeline: AIPipeline) -> None:
        ctx = pipeline.prepare_context({"extracted": "not a dict"})
        assert ctx["extracted_data"] == {}


class TestCalculateDataQuality:
    def test_empty_data_returns_zero(self, pipeline: AIPipeline) -> None:
        ctx = {"services": [], "pricing": [], "content": [], "social": [], "extracted_data": {}}
        score = pipeline._calculate_data_quality(ctx)
        assert score == 0.0

    def test_full_data_returns_high_score(self, pipeline: AIPipeline) -> None:
        ctx = {
            "services": [{"name": f"s{i}"} for i in range(20)],
            "pricing": [{"price": i} for i in range(15)],
            "content": [{"title": f"c{i}"} for i in range(10)],
            "social": [{"platform": f"p{i}"} for i in range(5)],
            "extracted_data": {"a": 1, "b": 2, "c": 3, "d": 4, "e": 5},
        }
        score = pipeline._calculate_data_quality(ctx)
        assert score > 0.8

    def test_partial_data_returns_mid_score(self, pipeline: AIPipeline) -> None:
        ctx = {
            "services": [{"name": "s1"}, {"name": "s2"}],
            "pricing": [],
            "content": [],
            "social": [],
            "extracted_data": {},
        }
        score = pipeline._calculate_data_quality(ctx)
        assert 0.0 < score < 0.5

    def test_score_is_between_0_and_1(self, pipeline: AIPipeline) -> None:
        ctx = {
            "services": [{"name": f"s{i}"} for i in range(50)],
            "pricing": [{"price": i} for i in range(50)],
            "content": [{"title": f"c{i}"} for i in range(50)],
            "social": [{"platform": f"p{i}"} for i in range(50)],
            "extracted_data": {f"k{i}": i for i in range(50)},
        }
        score = pipeline._calculate_data_quality(ctx)
        assert 0.0 <= score <= 1.0


# ─── build_prompt tests ─────────────────────────────────────────────────────

class TestBuildPrompt:
    def test_prompt_contains_competitor_name(self, pipeline: AIPipeline) -> None:
        context = {"competitor_name": "American Home Shield", "competitor_url": "https://ahs.com",
                    "services": [], "pricing": [], "content": [], "social": [], "extracted_data": {},
                    "data_summary": "Data completeness: 0%"}
        prompt = pipeline.build_prompt(context)
        assert "American Home Shield" in prompt

    def test_prompt_contains_competitor_url(self, pipeline: AIPipeline) -> None:
        context = {"competitor_name": "Test", "competitor_url": "https://test.com",
                    "services": [], "pricing": [], "content": [], "social": [], "extracted_data": {},
                    "data_summary": "Data completeness: 0%"}
        prompt = pipeline.build_prompt(context)
        assert "https://test.com" in prompt

    def test_prompt_contains_services_json(self, pipeline: AIPipeline) -> None:
        context = {"competitor_name": "Test", "competitor_url": "",
                    "services": [{"name": "HVAC"}], "pricing": [], "content": [], "social": [], "extracted_data": {},
                    "data_summary": "Data completeness: 25%"}
        prompt = pipeline.build_prompt(context)
        assert "HVAC" in prompt

    def test_prompt_does_not_contain_raw_template_vars(self, pipeline: AIPipeline) -> None:
        context = {"competitor_name": "AHS", "competitor_url": "https://ahs.com",
                    "services": [], "pricing": [], "content": [], "social": [], "extracted_data": {},
                    "data_summary": "Data completeness: 0%"}
        prompt = pipeline.build_prompt(context)
        assert "{{competitor_name}}" not in prompt
        assert "{{competitor_url}}" not in prompt


# ─── validate_response tests ────────────────────────────────────────────────

class TestValidateResponse:
    def test_valid_response(self, pipeline: AIPipeline) -> None:
        result = pipeline.validate_response(MockProvider._valid_response())
        assert isinstance(result, AIInsightResponse)
        assert result.confidence_score == 0.85
        assert len(result.key_differentiators) == 3

    def test_missing_required_field(self, pipeline: AIPipeline) -> None:
        data = MockProvider._valid_response()
        del data["summary"]
        with pytest.raises(ValidationError, match="Schema validation failed"):
            pipeline.validate_response(data)

    def test_empty_summary(self, pipeline: AIPipeline) -> None:
        data = MockProvider._valid_response()
        data["summary"] = ""
        with pytest.raises(ValidationError):
            pipeline.validate_response(data)

    def test_short_summary(self, pipeline: AIPipeline) -> None:
        data = MockProvider._valid_response()
        data["summary"] = "Short"
        with pytest.raises(ValidationError):
            pipeline.validate_response(data)

    def test_confidence_score_too_high(self, pipeline: AIPipeline) -> None:
        data = MockProvider._valid_response()
        data["confidence_score"] = 1.5
        with pytest.raises(ValidationError):
            pipeline.validate_response(data)

    def test_confidence_score_negative(self, pipeline: AIPipeline) -> None:
        data = MockProvider._valid_response()
        data["confidence_score"] = -0.1
        with pytest.raises(ValidationError):
            pipeline.validate_response(data)

    def test_empty_key_differentiators_allowed(self, pipeline: AIPipeline) -> None:
        data = MockProvider._valid_response()
        data["key_differentiators"] = []
        result = pipeline.validate_response(data)
        assert result.key_differentiators == []


# ─── run_analysis tests ─────────────────────────────────────────────────────

class TestRunAnalysis:
    @pytest.mark.asyncio
    async def test_successful_analysis(self, pipeline: AIPipeline, sample_raw_data: dict) -> None:
        with patch("app.ai.infrastructure.cache.llm_cache") as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            result = await pipeline.run_analysis(1, sample_raw_data)

        assert result["summary"] != ""
        assert 0.0 <= result["confidence_score"] <= 1.0
        assert result["prompt_version"] == prompt_builder.prompt_version
        assert "data_quality_score" in result
        assert pipeline.provider.call_count == 1

    @pytest.mark.asyncio
    async def test_cache_hit_skips_llm(self, pipeline: AIPipeline, sample_raw_data: dict) -> None:
        cached_response = MockProvider._valid_response()
        with patch("app.ai.infrastructure.cache.llm_cache") as mock_cache:
            mock_cache.get = AsyncMock(return_value=cached_response)
            mock_cache.set = AsyncMock()
            result = await pipeline.run_analysis(1, sample_raw_data)

        assert result["summary"] != ""
        # Provider should not have been called (cache hit)
        assert pipeline.provider.call_count == 0

    @pytest.mark.asyncio
    async def test_provider_error_raises_pipeline_error(self, sample_raw_data: dict) -> None:
        from app.ai.exceptions import ProviderError
        failing_provider = MockProvider(error=ProviderError("API down", provider="mock"))
        pipeline = AIPipeline(failing_provider)

        with patch("app.ai.infrastructure.cache.llm_cache") as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            with pytest.raises(PipelineError, match="Pipeline failed"):
                await pipeline.run_analysis(1, sample_raw_data)

    @pytest.mark.asyncio
    async def test_validation_failure_triggers_repair(self, sample_raw_data: dict) -> None:
        """When first LLM response fails validation, pipeline retries with repair prompt."""
        bad_response = MockProvider._valid_response()
        bad_response["summary"] = ""  # Will fail validation

        good_response = MockProvider._valid_response()

        call_count = 0

        class RepairProvider(LLMProvider):
            async def generate_structured_insight(self, prompt: str, schema: dict) -> dict:
                nonlocal call_count
                call_count += 1
                if call_count == 1:
                    return bad_response  # First call: bad
                return good_response  # Second call (repair): good

            async def health(self) -> ProviderHealth:
                return ProviderHealth(healthy=True, provider="mock", model="mock")

            @property
            def provider_name(self) -> str:
                return "mock"

            @property
            def model_name(self) -> str:
                return "mock"

        pipeline = AIPipeline(RepairProvider())

        with patch("app.ai.infrastructure.cache.llm_cache") as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            mock_cache.set = AsyncMock()
            mock_cache.invalidate = AsyncMock()
            result = await pipeline.run_analysis(1, sample_raw_data)

        assert call_count == 2
        assert result["summary"] != ""
        mock_cache.invalidate.assert_called_once()

    @pytest.mark.asyncio
    async def test_repair_also_fails_raises_error(self, sample_raw_data: dict) -> None:
        """When both initial and repair responses fail validation, raises PipelineError."""
        bad_response = {"summary": ""}  # Always bad

        class AlwaysBadProvider(LLMProvider):
            async def generate_structured_insight(self, prompt: str, schema: dict) -> dict:
                return bad_response

            async def health(self) -> ProviderHealth:
                return ProviderHealth(healthy=True, provider="mock", model="mock")

            @property
            def provider_name(self) -> str:
                return "mock"

            @property
            def model_name(self) -> str:
                return "mock"

        pipeline = AIPipeline(AlwaysBadProvider())

        with patch("app.ai.infrastructure.cache.llm_cache") as mock_cache:
            mock_cache.get = AsyncMock(return_value=None)
            with pytest.raises(PipelineError):
                await pipeline.run_analysis(1, sample_raw_data)
