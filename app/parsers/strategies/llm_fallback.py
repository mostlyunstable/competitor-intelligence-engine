import json
import time
from typing import Any

import structlog
from bs4 import BeautifulSoup

try:
    from openai import APIConnectionError, APIStatusError, APITimeoutError, OpenAI

    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False
    APIConnectionError = Exception  # type: ignore
    APIStatusError = Exception  # type: ignore
    APITimeoutError = Exception  # type: ignore
    OpenAI = Any  # type: ignore
from tenacity import retry, retry_if_exception_type, stop_after_attempt, wait_exponential

from app.configuration.settings import get_settings
from app.parsers.strategy import ParsedResult

logger = structlog.get_logger(__name__)


_CIRCUIT_FAILURES = 0
_CIRCUIT_OPEN_UNTIL = 0.0
_MAX_FAILURES = 5
_COOLDOWN_SECONDS = 60.0


class LLMFallbackService:
    """
    Ultimate fallback service using an LLM to extract data.
    Runs ONLY when all deterministic strategies have completed and overall confidence is low.
    """

    def __init__(self, api_key: str | None = None) -> None:
        self.settings = get_settings().llm
        self.base_url = (
            "https://integrate.api.nvidia.com/v1"
            if self.settings.provider.lower() == "nvidia"
            else None
        )

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=1, min=2, max=10),
        retry=retry_if_exception_type((APIConnectionError, APIStatusError, APITimeoutError)),
        reraise=True,
    )
    def _call_llm_with_retry(self, client: Any, prompt: str) -> str:
        """Call LLM with strict timeouts, token limits, and exponential backoff retries."""
        logger.info("llm_api_call_attempt")
        response = client.chat.completions.create(
            model=self.settings.model_name,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.0,
            max_tokens=1024,
            timeout=15.0,  # Strict timeout
        )

        # Token budgeting / Cost logging
        usage = response.usage
        if usage:
            cost = (
                usage.prompt_tokens * 0.0005 + usage.completion_tokens * 0.0015
            ) / 1000  # Dummy approximation
            logger.info(
                "llm_token_usage",
                prompt_tokens=usage.prompt_tokens,
                completion_tokens=usage.completion_tokens,
                estimated_cost_usd=round(cost, 6),
            )

        return response.choices[0].message.content or ""

    def execute_fallback(
        self, soup: BeautifulSoup, url: str, combined_result: ParsedResult
    ) -> ParsedResult:
        """Execute the LLM fallback on the page content and merge it into the result."""
        global _CIRCUIT_FAILURES, _CIRCUIT_OPEN_UNTIL

        if not OPENAI_AVAILABLE:
            logger.info("llm_fallback_skipped_openai_not_installed", url=url)
            return combined_result

        if not self.settings.enabled or not self.settings.api_key:
            return combined_result

        now = time.time()
        if _CIRCUIT_FAILURES >= _MAX_FAILURES:
            if now < _CIRCUIT_OPEN_UNTIL:
                logger.warning("llm_circuit_breaker_open_skipping_call", url=url)
                return combined_result
            else:
                logger.info("llm_circuit_breaker_half_open_testing", url=url)

        text = soup.get_text(separator="\n", strip=True)
        # Only run if there is meaningful text to avoid useless API calls
        if len(text) < 100:
            logger.info("llm_fallback_skipped_no_meaningful_text", url=url, text_length=len(text))
            return combined_result

        # Truncate text to avoid massive token costs
        if len(text) > 20000:
            text = text[:20000]

        prompt = f"""
        Analyze the following text extracted from a competitor's website ({url}) and extract structured business intelligence.
        Return ONLY valid JSON with the following structure. Do not include markdown blocks or any other text.
        {{
            "company_name": "Name",
            "description": "Description",
            "services": [{{"name": "Service Name", "description": "Desc"}}],
            "pricing": [{{"plan_name": "Plan", "price": 99.0, "currency": "USD", "billing_period": "monthly"}}]
        }}

        Text:
        {text}
        """

        try:
            client = OpenAI(api_key=self.settings.api_key, base_url=self.base_url)

            content = self._call_llm_with_retry(client, prompt)

            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]

            data = json.loads(content)

            # We create a new partial result and merge it so it gets confidence tracked
            partial = ParsedResult()

            if "company_name" in data and isinstance(data["company_name"], str):
                partial.company_name = data["company_name"]
            if "description" in data and isinstance(data["description"], str):
                partial.description = data["description"]

            if "services" in data and isinstance(data["services"], list):
                for s in data["services"]:
                    if isinstance(s, dict) and "name" in s:
                        partial.services.append(s)

            if "pricing" in data and isinstance(data["pricing"], list):
                for p in data["pricing"]:
                    if isinstance(p, dict) and "plan_name" in p:
                        partial.pricing.append(p)

            # Merge the partial result with a moderate confidence weight
            combined_result.merge(partial, "llm_fallback", 0.40)
            logger.info("llm_extraction_success", url=url, model=self.settings.model_name)

            # Reset circuit on success
            if _CIRCUIT_FAILURES > 0:
                logger.info("llm_circuit_breaker_reset")
            _CIRCUIT_FAILURES = 0

        except Exception as e:
            logger.error("llm_extraction_failed", error=str(e), url=url)
            _CIRCUIT_FAILURES += 1
            if _CIRCUIT_FAILURES >= _MAX_FAILURES:
                _CIRCUIT_OPEN_UNTIL = time.time() + _COOLDOWN_SECONDS
                logger.error(
                    "llm_circuit_breaker_tripped",
                    failures=_CIRCUIT_FAILURES,
                    cooldown=_COOLDOWN_SECONDS,
                )

        return combined_result
