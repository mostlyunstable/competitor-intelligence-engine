import json
import logging
from typing import Any

from app.ai.domain.entities import AIInsightResponse
from app.ai.domain.provider import LLMProvider

logger = logging.getLogger(__name__)


class AIPipeline:
    """
    Orchestrates the AI processing pipeline for a competitor.
    """

    def __init__(self, provider: LLMProvider):
        self.provider = provider

    async def process_competitor(self, competitor_id: int, raw_data: dict[str, Any]) -> dict[str, Any]:
        """
        Executes the AI pipeline for a given competitor using their raw collected data.
        """
        logger.info(f"Starting AI Pipeline for competitor_id={competitor_id}")

        # In a real scenario, we'd load versioned prompts from PromptManager
        prompt = f"""
        Analyze the following competitor data and provide a comprehensive intelligence report.
        Raw Data:
        {json.dumps(raw_data, indent=2)}
        """

        # Schema is automatically derived from the Pydantic model
        schema = AIInsightResponse.model_json_schema()

        try:
            logger.info("Calling LLM Provider...")
            result = await self.provider.generate_structured_insight(prompt, schema)

            # Validate output matches strict Pydantic model
            logger.info("Validating LLM Output...")
            validated_result = AIInsightResponse(**result)

            logger.info(f"AI Pipeline completed successfully for competitor_id={competitor_id}")
            return validated_result.model_dump()

        except Exception as e:
            logger.error(f"AI Pipeline failed for competitor_id={competitor_id}: {e!s}")
            raise
