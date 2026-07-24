import json
from typing import Any

from openai import AsyncOpenAI
from tenacity import retry, stop_after_attempt, wait_exponential

from app.ai.domain.provider import LLMProvider
from app.configuration.settings import get_settings


class OpenAIProvider(LLMProvider):
    """
    LLM Provider implementation that wraps the OpenAI client.
    Can be used for OpenAI models or OpenAI-compatible endpoints like NVIDIA NIM.
    """

    def __init__(self):  # type: ignore
        self.settings = get_settings().llm
        self.client = AsyncOpenAI(
            api_key=self.settings.api_key,
            base_url=self.settings.base_url if self.settings.base_url else None,
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
    )
    async def generate_structured_insight(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Calls the OpenAI-compatible endpoint with JSON mode enabled to return structured output.
        """
        from app.chaos import ChaosMonkey
        await ChaosMonkey.maybe_fail_openai()

        response = await self.client.chat.completions.create(
            model=self.settings.model_name,
            messages=[
                {"role": "system", "content": "You are a specialized business intelligence analyst. You must output your analysis in JSON matching the exact schema provided."},
                {"role": "user", "content": f"Schema:\n{json.dumps(schema, indent=2)}\n\nPrompt:\n{prompt}"},
            ],
            response_format={"type": "json_object"},
            temperature=0.1,
        )

        content = response.choices[0].message.content
        if not content:
            raise ValueError("LLM returned empty response")

        content = ChaosMonkey.maybe_corrupt_ai_response(content)

        try:
            return json.loads(content)  # type: ignore
        except json.decoder.JSONDecodeError as e:
            # Re-raise to trigger tenacity retry
            import logging
            logging.error(f"Chaos/LLM Error: Failed to parse JSON response: {e}")
            raise
