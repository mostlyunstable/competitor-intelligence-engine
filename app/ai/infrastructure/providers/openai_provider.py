"""OpenAI-compatible LLM provider implementation."""

import json
import time
from typing import Any

import structlog
from openai import AsyncOpenAI
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.ai.domain.provider import LLMProvider
from app.ai.domain.entities import ProviderHealth
from app.ai.exceptions import ProviderError
from app.configuration.settings import get_settings

logger = structlog.get_logger("ai.provider")


class OpenAIProvider(LLMProvider):
    """
    LLM Provider wrapping AsyncOpenAI.
    Works with OpenAI, NVIDIA NIM, and any OpenAI-compatible endpoint.
    """

    def __init__(self) -> None:
        self._settings = get_settings().llm
        if not self._settings.api_key:
            raise ProviderError("LLM API key not configured", provider="openai")
        self._client = AsyncOpenAI(
            api_key=self._settings.api_key,
            base_url=self._settings.base_url if self._settings.base_url else None,
            timeout=self._settings.timeout,
            max_retries=0,  # We handle retries via tenacity
        )

    @property
    def provider_name(self) -> str:
        return self._settings.provider or "openai"

    @property
    def model_name(self) -> str:
        return self._settings.model_name

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((ProviderError, TimeoutError, ConnectionError)),
        reraise=True,
    )
    async def generate_structured_insight(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Call the LLM with JSON mode and return structured output."""
        start = time.monotonic()
        try:
            response = await self._client.chat.completions.create(
                model=self._settings.model_name,
                messages=[
                    {
                        "role": "system",
                        "content": (
                            "You are a specialized business intelligence analyst. "
                            "You MUST output your analysis as valid JSON matching the schema provided. "
                            "No markdown, no explanation, no code fences — only raw JSON."
                        ),
                    },
                    {"role": "user", "content": f"Schema:\n{json.dumps(schema, indent=2)}\n\nData:\n{prompt}"},
                ],
                response_format={"type": "json_object"},
                temperature=self._settings.temperature,
                max_tokens=self._settings.max_tokens,
            )
            elapsed_ms = (time.monotonic() - start) * 1000

            content = response.choices[0].message.content
            if not content:
                raise ProviderError("LLM returned empty response", provider=self.provider_name)

            result = json.loads(content)

            # Attach token usage for cost tracking
            if response.usage:
                result["_token_usage"] = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }
                logger.info(
                    "llm_call_complete",
                    provider=self.provider_name,
                    model=self._settings.model_name,
                    prompt_tokens=response.usage.prompt_tokens,
                    completion_tokens=response.usage.completion_tokens,
                    elapsed_ms=round(elapsed_ms),
                )

            return result

        except json.JSONDecodeError as e:
            raise ProviderError(
                f"LLM returned invalid JSON: {e}",
                provider=self.provider_name,
            ) from e
        except ProviderError:
            raise
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            logger.error("llm_call_failed", provider=self.provider_name, error=str(e), elapsed_ms=round(elapsed_ms))
            raise ProviderError(
                f"LLM call failed: {e}",
                provider=self.provider_name,
                status_code=getattr(e, "status_code", 0),
            ) from e

    async def health(self) -> ProviderHealth:
        """Check provider connectivity with a minimal request."""
        start = time.monotonic()
        try:
            response = await self._client.models.list()
            elapsed_ms = (time.monotonic() - start) * 1000
            return ProviderHealth(
                healthy=True,
                provider=self.provider_name,
                model=self._settings.model_name,
                latency_ms=round(elapsed_ms),
            )
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            return ProviderHealth(
                healthy=False,
                provider=self.provider_name,
                model=self._settings.model_name,
                latency_ms=round(elapsed_ms),
                error=str(e),
            )
