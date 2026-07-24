"""AI processing pipeline: orchestrates analysis from data to database."""

import json
import math
from typing import Any

import structlog
from app.ai.domain.entities import AIInsightResponse
from app.ai.domain.provider import LLMProvider
from app.ai.exceptions import PipelineError, ValidationError
from app.ai.prompts.builder import prompt_builder

logger = structlog.get_logger("ai.pipeline")

# Data quality weights for confidence calibration
_DATA_WEIGHTS = {
    "services": 0.25,
    "pricing": 0.25,
    "content": 0.20,
    "social": 0.15,
    "extracted_data": 0.15,
}

# Expected counts for "full" data per category
_DATA_EXPECTED = {
    "services": 15,
    "pricing": 10,
    "content": 8,
    "social": 4,
    "extracted_data": 5,
}


class AIPipeline:
    """
    Orchestrates AI analysis for a competitor.

    Flow:
        prepare_context -> build_prompt -> call_provider -> validate -> return
    """

    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider
        self._schema = AIInsightResponse.model_json_schema()

    @staticmethod
    def _calculate_data_quality(context: dict[str, Any]) -> float:
        """
        Calculate a data quality score (0.0-1.0) based on completeness.
        Uses log scaling so diminishing returns for massive datasets.
        """
        scores = []
        for category, weight in _DATA_WEIGHTS.items():
            data = context.get(category, [])
            if isinstance(data, dict):
                count = len(data) if data else 0
            elif isinstance(data, list):
                count = len(data)
            else:
                count = 0

            expected = _DATA_EXPECTED[category]
            # Log scaling: 0 items = 0, expected items = ~1.0, 2x expected = ~1.07
            if count == 0:
                cat_score = 0.0
            else:
                cat_score = min(1.0, math.log(1 + count) / math.log(1 + expected))
            scores.append(cat_score * weight)

        return round(sum(scores), 3)

    def prepare_context(self, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Normalize raw data into a consistent context dict.
        Handles both DB-gathered format and collection-service format.
        """
        context: dict[str, Any] = {}

        context["competitor_name"] = raw_data.get("name", "Unknown")
        context["competitor_url"] = raw_data.get("url", "")

        # Normalize services
        services = raw_data.get("services", [])
        if isinstance(services, list):
            context["services"] = services
        else:
            context["services"] = []

        # Normalize pricing
        pricing = raw_data.get("pricing", [])
        if isinstance(pricing, list):
            context["pricing"] = pricing
        else:
            context["pricing"] = []

        # Normalize content
        content = raw_data.get("content", [])
        if isinstance(content, list):
            context["content"] = content
        else:
            context["content"] = []

        # Normalize social
        social = raw_data.get("social", [])
        if isinstance(social, list):
            context["social"] = social
        else:
            context["social"] = []

        # Extracted data (may be nested dict from raw_storage)
        extracted = raw_data.get("extracted", {})
        if isinstance(extracted, dict):
            context["extracted_data"] = extracted
        else:
            context["extracted_data"] = {}

        # Calculate data quality score for confidence calibration
        context["data_quality_score"] = self._calculate_data_quality(context)
        context["data_summary"] = (
            f"Data completeness: {context['data_quality_score']:.0%} "
            f"(services={len(context['services'])}, pricing={len(context['pricing'])}, "
            f"content={len(context['content'])}, social={len(context['social'])})"
        )

        return context

    def build_prompt(self, context: dict[str, Any]) -> str:
        """Build the LLM prompt from prepared context."""
        return prompt_builder.build_prompt(context)

    def validate_response(self, raw_result: dict[str, Any]) -> AIInsightResponse:
        """Validate LLM output against strict schema. Raises on failure."""
        try:
            validated = AIInsightResponse(**raw_result)
        except Exception as e:
            raise ValidationError(f"Schema validation failed: {e}", errors=[str(e)]) from e

        if validated.confidence_score < 0.0 or validated.confidence_score > 1.0:
            raise ValidationError(
                f"Confidence score {validated.confidence_score} out of range [0.0, 1.0]"
            )

        if not validated.summary or len(validated.summary) < 10:
            raise ValidationError("Summary is too short or empty")

        return validated

    async def run_analysis(self, competitor_id: int, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Full pipeline: context -> prompt -> cache check -> LLM -> validate -> return dict.
        On validation failure, retries once with a repair prompt.
        """
        logger.info("pipeline_start", competitor_id=competitor_id)

        try:
            # 1. Prepare context
            context = self.prepare_context(raw_data)
            logger.info("context_prepared", competitor_id=competitor_id, keys=list(context.keys()))

            # 2. Build prompt
            prompt = self.build_prompt(context)
            logger.info("prompt_built", competitor_id=competitor_id, length=len(prompt))

            # 3. Check cache
            from app.ai.infrastructure.cache import llm_cache
            cached = await llm_cache.get(prompt)
            if cached:
                logger.info("cache_hit", competitor_id=competitor_id)
                raw_result = cached
            else:
                # 4. Call LLM provider
                raw_result = await self.provider.generate_structured_insight(prompt, self._schema)
                logger.info("llm_response_received", competitor_id=competitor_id)
                # 5. Cache the response
                await llm_cache.set(prompt, raw_result)

            # 6. Validate
            try:
                validated = self.validate_response(raw_result)
            except ValidationError as ve:
                # Retry with repair prompt
                logger.warning("validation_failed_retry", competitor_id=competitor_id, error=str(ve))
                repair_prompt = (
                    f"Your previous response failed validation: {ve}\n\n"
                    f"Here is the required schema:\n{json.dumps(self._schema, indent=2)}\n\n"
                    f"Original data context:\n{prompt[:2000]}\n\n"
                    f"Fix ONLY the invalid fields. Return complete valid JSON."
                )
                raw_result = await self.provider.generate_structured_insight(repair_prompt, self._schema)
                await llm_cache.invalidate(prompt)  # Don't cache repaired response
                validated = self.validate_response(raw_result)

            logger.info("validation_passed", competitor_id=competitor_id, confidence=validated.confidence_score)

            # 7. Override confidence with data-calibrated score
            data_quality = context.get("data_quality_score", 0.5)
            llm_confidence = validated.confidence_score
            # Blend: 60% data quality + 40% LLM confidence (prevents LLM from ignoring data)
            calibrated = round(0.6 * data_quality + 0.4 * llm_confidence, 3)
            validated.confidence_score = calibrated

            # 8. Return as dict
            result = validated.model_dump()
            result["prompt_version"] = prompt_builder.prompt_version
            result["data_quality_score"] = data_quality
            return result

        except Exception as e:
            logger.error("pipeline_failed", competitor_id=competitor_id, error=str(e))
            raise PipelineError(f"Pipeline failed for competitor {competitor_id}: {e}") from e
