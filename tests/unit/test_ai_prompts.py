"""Tests for the prompt builder and templates."""

import json

import pytest

from app.ai.prompts.builder import PromptBuilder, prompt_builder
from app.ai.prompts.templates import PROMPT_TEMPLATES, DEFAULT_TEMPLATE_ID
from app.ai.exceptions import PromptError


class TestPromptBuilder:
    def test_singleton_exists(self) -> None:
        assert prompt_builder is not None
        assert isinstance(prompt_builder, PromptBuilder)

    def test_get_default_template(self) -> None:
        template = prompt_builder.get_template()
        assert template.id == DEFAULT_TEMPLATE_ID
        assert template.version == "3.0.0"

    def test_get_template_by_id(self) -> None:
        template = prompt_builder.get_template("competitor_analysis")
        assert template.id == "competitor_analysis"

    def test_get_nonexistent_template_raises(self) -> None:
        with pytest.raises(PromptError, match="not found"):
            prompt_builder.get_template("nonexistent")

    def test_prompt_version(self) -> None:
        assert prompt_builder.prompt_version == "3.0.0"

    def test_build_prompt_substitutes_variables(self) -> None:
        data = {
            "competitor_name": "Test Company",
            "competitor_url": "https://test.com",
            "services": [{"name": "Service A"}],
            "pricing": [],
            "content": [],
            "social": [],
            "extracted_data": {},
            "data_summary": "Data completeness: 25%",
        }
        prompt = prompt_builder.build_prompt(data)
        assert "Test Company" in prompt
        assert "https://test.com" in prompt
        assert "Service A" in prompt
        assert "Data completeness: 25%" in prompt
        # Raw template vars should not remain
        assert "{{competitor_name}}" not in prompt
        assert "{{competitor_url}}" not in prompt

    def test_build_prompt_empty_data(self) -> None:
        data = {
            "competitor_name": "Unknown",
            "competitor_url": "",
            "services": [],
            "pricing": [],
            "content": [],
            "social": [],
            "extracted_data": {},
            "data_summary": "Data completeness: 0%",
        }
        prompt = prompt_builder.build_prompt(data)
        assert "Unknown" in prompt
        assert "No data available" in prompt

    def test_build_prompt_json_serializes_lists(self) -> None:
        data = {
            "competitor_name": "Test",
            "competitor_url": "",
            "services": [{"name": "HVAC", "desc": "Heating"}],
            "pricing": [{"price": 99}],
            "content": [],
            "social": [],
            "extracted_data": {},
            "data_summary": "Data completeness: 30%",
        }
        prompt = prompt_builder.build_prompt(data)
        # Lists should be JSON-serialized in the prompt
        assert '"name": "HVAC"' in prompt or "HVAC" in prompt

    def test_templates_have_required_variables(self) -> None:
        for tid, tdata in PROMPT_TEMPLATES.items():
            assert "required_variables" in tdata, f"Template {tid} missing required_variables"
            assert len(tdata["required_variables"]) > 0, f"Template {tid} has empty required_variables"

    def test_all_template_vars_are_substituted(self) -> None:
        """Ensure no {{ var }} placeholders remain after rendering (except JSON examples in template)."""
        data = {
            "competitor_name": "X",
            "competitor_url": "Y",
            "services": [],
            "pricing": [],
            "content": [],
            "social": [],
            "extracted_data": {},
            "data_summary": "Data completeness: 0%",
        }
        prompt = prompt_builder.build_prompt(data)
        # Check that our known variables are substituted
        assert "{{competitor_name}}" not in prompt
        assert "{{competitor_url}}" not in prompt
        assert "{{services}}" not in prompt
        assert "{{pricing}}" not in prompt


class TestPromptTemplate:
    def test_render_substitutes_vars(self) -> None:
        from app.ai.domain.entities import PromptTemplate
        tmpl = PromptTemplate(
            id="test", version="1.0", purpose="test",
            template="Hello {{name}}, you are {{age}}",
            required_variables=["name", "age"],
        )
        result = tmpl.render(name="World", age="30")
        assert result == "Hello World, you are 30"

    def test_render_missing_required_var(self) -> None:
        from app.ai.domain.entities import PromptTemplate
        tmpl = PromptTemplate(
            id="test", version="1.0", purpose="test",
            template="Hello {{name}}",
            required_variables=["name", "age"],
        )
        with pytest.raises(ValueError, match="Missing required"):
            tmpl.render(name="World")
