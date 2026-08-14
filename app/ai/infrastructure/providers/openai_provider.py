"""Utservio LLM proxy provider using Responses API format."""

import json
import time
from typing import Any

import httpx
import structlog
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
    LLM Provider for Utservio proxy using OpenAI Responses API format.
    """

    def __init__(self) -> None:
        self._settings = get_settings().llm
        if not self._settings.api_key:
            raise ProviderError("LLM API key not configured", provider="openai")
        self._client = httpx.AsyncClient(
            base_url=self._settings.base_url.rstrip("/"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self._settings.api_key}",
            },
            timeout=httpx.Timeout(60.0),
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
            system_prompt = (
                "You are a specialized business intelligence analyst. "
                "You MUST output your analysis as valid JSON matching the schema provided. "
                "No markdown, no explanation, no code fences — only raw JSON."
            )
            user_message = f"Schema:\n{json.dumps(schema, indent=2)}\n\nData:\n{prompt}"

            response = await self._client.post(
                "/v1/responses",
                json={
                    "model": self._settings.model_name,
                    "input": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_message},
                    ],
                    "text": {"format": {"type": "json_object"}},
                    "temperature": self._settings.temperature,
                    "max_output_tokens": self._settings.max_tokens,
                },
            )
            elapsed_ms = (time.monotonic() - start) * 1000

            if response.status_code != 200:
                error_msg = f"LLM API error: {response.status_code} - {response.text[:200]}"
                logger.error("llm_call_failed", error=error_msg, elapsed_ms=round(elapsed_ms))
                raise ProviderError(error_msg, provider=self.provider_name)

            data = response.json()

            # Extract text from Responses API format
            content = ""
            for output_item in data.get("output", []):
                if output_item.get("type") == "message":
                    for content_item in output_item.get("content", []):
                        if content_item.get("type") == "output_text":
                            content = content_item.get("text", "")
                            break

            if not content:
                raise ProviderError("LLM returned empty response", provider=self.provider_name)

            result = json.loads(content)

            # Attach token usage for cost tracking
            usage = data.get("usage", {})
            if usage:
                result["_token_usage"] = {
                    "prompt_tokens": usage.get("input_tokens", 0),
                    "completion_tokens": usage.get("output_tokens", 0),
                    "total_tokens": usage.get("total_tokens", 0),
                }
                logger.info(
                    "llm_call_complete",
                    provider=self.provider_name,
                    model=self._settings.model_name,
                    prompt_tokens=usage.get("input_tokens", 0),
                    completion_tokens=usage.get("output_tokens", 0),
                    elapsed_ms=round(elapsed_ms),
                )

            return result

        except json.JSONDecodeError as e:
            logger.error("llm_json_parse_failed", error=str(e))
            raise ProviderError(f"Failed to parse LLM response as JSON: {e}", provider=self.provider_name)
        except httpx.HTTPError as e:
            logger.error("llm_http_error", error=str(e))
            raise ProviderError(f"HTTP error calling LLM: {e}", provider=self.provider_name)

    async def health(self) -> ProviderHealth:
        """Quick health check with a simple prompt."""
        start = time.monotonic()
        try:
            response = await self._client.post(
                "/v1/responses",
                json={
                    "model": self._settings.model_name,
                    "input": "Reply with exactly: OK",
                    "max_output_tokens": 5,
                },
            )
            latency_ms = (time.monotonic() - start) * 1000

            if response.status_code == 200:
                return ProviderHealth(
                    healthy=True,
                    provider=self.provider_name,
                    model=self._settings.model_name,
                    latency_ms=latency_ms,
                )
            return ProviderHealth(
                healthy=False,
                provider=self.provider_name,
                model=self._settings.model_name,
                latency_ms=latency_ms,
                error=f"HTTP {response.status_code}",
            )
        except Exception as e:
            latency_ms = (time.monotonic() - start) * 1000
            return ProviderHealth(
                healthy=False,
                provider=self.provider_name,
                model=self._settings.model_name,
                latency_ms=latency_ms,
                error=str(e),
            )

    async def close(self) -> None:
        """Close the HTTP client."""
        await self._client.aclose()
