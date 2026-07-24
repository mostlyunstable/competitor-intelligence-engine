"""Abstract LLM provider interface."""

from abc import ABC, abstractmethod
from typing import Any

from app.ai.domain.entities import ProviderHealth


class LLMProvider(ABC):
    """
    Abstract base class for LLM providers.
    Business logic depends only on this interface.
    """

    @abstractmethod
    async def generate_structured_insight(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """Generate a structured JSON response conforming to the given schema."""

    @abstractmethod
    async def health(self) -> ProviderHealth:
        """Check provider connectivity and model availability."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Return the provider identifier (e.g., 'openai', 'nvidia')."""

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the model identifier."""
