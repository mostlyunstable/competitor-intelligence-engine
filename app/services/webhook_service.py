from typing import Any

import httpx
import structlog

from app.configuration.settings import get_settings

logger = structlog.get_logger(__name__)


class WebhookService:
    """Service to push real-time alerts to external systems (Slack/Teams)."""

    def __init__(self) -> None:
        self.settings = get_settings().webhook

    async def _send_http_post(
        self, url: str, payload: dict[str, Any], destination_name: str
    ) -> bool:
        if not url:
            return False

        max_attempts = 3
        base_delay = 2.0

        for attempt in range(1, max_attempts + 1):
            try:
                async with httpx.AsyncClient(timeout=10.0) as client:
                    response = await client.post(url, json=payload)
                    response.raise_for_status()
                    logger.info("webhook_sent", destination=destination_name, attempt=attempt)
                    return True
            except Exception as e:
                if attempt < max_attempts:
                    delay = base_delay * (2 ** (attempt - 1))
                    logger.warning(
                        "webhook_retry_attempt",
                        destination=destination_name,
                        attempt=attempt,
                        error=str(e),
                        next_retry_in=delay,
                    )
                    import asyncio

                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "webhook_failed_permanently",
                        destination=destination_name,
                        error=str(e),
                        attempts=attempt,
                    )
                    return False
        return False

    async def notify_change(self, competitor_name: str, data_type: str, message: str) -> None:
        """Send an alert that something changed for a competitor."""
        if not self.settings.enabled:
            return

        slack_url = self.settings.slack_webhook_url
        if slack_url:
            slack_payload = {
                "text": f"🚨 *Competitor Update:* {competitor_name}\n*Type:* {data_type}\n*Details:* {message}"
            }
            await self._send_http_post(slack_url, slack_payload, "slack")

        teams_url = self.settings.teams_webhook_url
        if teams_url:
            teams_payload = {
                "title": f"Competitor Update: {competitor_name}",
                "text": f"**Type:** {data_type}\n\n**Details:** {message}",
            }
            await self._send_http_post(teams_url, teams_payload, "teams")
