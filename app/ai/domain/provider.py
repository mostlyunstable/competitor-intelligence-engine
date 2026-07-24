from abc import ABC, abstractmethod
from typing import Any


class LLMProvider(ABC):
    """Abstract base class for LLM providers in the AI Intelligence Layer."""

    @abstractmethod
    async def generate_structured_insight(self, prompt: str, schema: dict[str, Any]) -> dict[str, Any]:
        """
        Generate a structured JSON response from the LLM given a prompt and a JSON schema.

        Args:
            prompt: The formatted prompt to send to the LLM.
            schema: The JSON schema definition of the expected output format.

        Returns:
            A dictionary containing the structured response, conforming to the schema.
        """
        pass
