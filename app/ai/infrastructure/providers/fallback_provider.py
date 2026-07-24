"""Fallback LLM provider: tries primary provider, falls back to secondary."""

import structlog
from app.ai.domain.provider import LLMProvider
from app.ai.domain.entities import ProviderHealth
from app.ai.exceptions import ProviderError

logger = structlog.get_logger("ai.provider.fallback")


class FallbackProvider(LLMProvider):
    """
    Wraps primary and secondary providers.
    Falls back to secondary on primary failure.
    """

    def __init__(self, primary: LLMProvider, secondary: LLMProvider) -> None:
        self._primary = primary
        self._secondary = secondary

    @property
    def provider_name(self) -> str:
        return f"{self._primary.provider_name}+{self._secondary.provider_name}"

    @property
    def model_name(self) -> str:
        return self._primary.model_name

    async def generate_structured_insight(self, prompt: str, schema: dict) -> dict:
        try:
            return await self._primary.generate_structured_insight(prompt, schema)
        except ProviderError as e:
            logger.warning(
                "primary_provider_failed",
                primary=self._primary.provider_name,
                error=str(e),
                falling_back_to=self._secondary.provider_name,
            )
            return await self._secondary.generate_structured_insight(prompt, schema)

    async def health(self) -> ProviderHealth:
        primary_health = await self._primary.health()
        if primary_health.healthy:
            return primary_health
        return await self._secondary.health()
