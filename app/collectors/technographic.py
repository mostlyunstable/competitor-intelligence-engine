from datetime import UTC, datetime
from typing import Any

import structlog
from bs4 import BeautifulSoup
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.base import BaseCollector
from app.database.models import CompetitorTechStack

logger = structlog.get_logger(__name__)


class TechnographicCollector(BaseCollector):
    """Collects technology stack information from competitor websites."""

    def __init__(self) -> None:
        super().__init__()

    async def collect(
        self, competitor_id: int, url: str, *, session: AsyncSession, **kwargs: Any
    ) -> dict[str, Any]:
        detected_tech: list[dict[str, Any]] = []

        try:
            result = await self.fetch(url, competitor_id, force_render=True)
            if not result.html:
                return {"status": "failed", "error": "Empty response from Playwright"}

            html = result.html
            soup = BeautifulSoup(html, "html.parser")

            scripts = [s.get("src", "") for s in soup.find_all("script") if s.get("src")]
            for src_val in scripts:
                if not isinstance(src_val, str):
                    continue
                src_lower = src_val.lower()
                if "stripe.com" in src_lower:
                    detected_tech.append({"name": "Stripe", "category": "Payment Gateway"})
                if "hs-scripts.com" in src_lower or "hubspot" in src_lower:
                    detected_tech.append({"name": "HubSpot", "category": "CRM"})
                if "google-analytics.com" in src_lower or "googletagmanager" in src_lower:
                    detected_tech.append({"name": "Google Analytics", "category": "Analytics"})
                if "react" in src_lower:
                    detected_tech.append({"name": "React", "category": "Frontend Framework"})

            generator = soup.find("meta", attrs={"name": "generator"})
            if generator:
                gen_content = generator.get("content", "")
                if isinstance(gen_content, str) and gen_content:
                    content = gen_content.lower()
                    if "wordpress" in content:
                        detected_tech.append({"name": "WordPress", "category": "CMS"})
                    if "webflow" in content:
                        detected_tech.append({"name": "Webflow", "category": "CMS"})

            unique_tech = {t["name"]: t for t in detected_tech}.values()


            for tech in unique_tech:
                existing_stmt = select(CompetitorTechStack).where(
                    CompetitorTechStack.competitor_id == competitor_id,
                    CompetitorTechStack.technology_name == tech["name"],
                )
                existing = (await session.execute(existing_stmt)).scalar_one_or_none()

                if existing:
                    existing.confidence = 1.0
                    existing.discovered_at = datetime.now(UTC)
                else:
                    stack_entry = CompetitorTechStack(
                        competitor_id=competitor_id,
                        technology_name=tech["name"],
                        category=tech.get("category"),
                        confidence=1.0,
                        discovered_at=datetime.now(UTC),
                    )
                    session.add(stack_entry)


            return {
                "status": "success",
                "technologies_detected": len(unique_tech),
                "data": list(unique_tech),
            }

        except Exception as e:
            logger.error("technographic_collection_failed", error=str(e), url=url)
            return {"status": "failed", "error": str(e)}

    async def close(self) -> None:
        pass
