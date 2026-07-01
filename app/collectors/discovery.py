from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.base import BaseCollector
from app.database.repositories.competitor_source_repository import CompetitorSourceRepository
from app.parsers.discovery import DiscoveryParser
from app.utilities.url_normalizer import normalize_url


class DiscoveryCollector(BaseCollector):
    def __init__(self) -> None:
        super().__init__()
        self._parser = DiscoveryParser()

    async def collect(
        self, competitor_id: int, url: str, *, session: AsyncSession, **kwargs: Any
    ) -> dict[str, Any]:
        start_time: float = __import__("time").time()

        try:
            result = await self.fetch(url)
            html = result.html

            await self.store_raw(competitor_id, url, html, session)

            parsed = self._parser.parse(html, url)
            links = parsed["links"]

            source_repo = CompetitorSourceRepository(session)
            sources_created = 0
            sources_updated = 0
            for link in links:
                normalized_link = normalize_url(link, base_url=url)
                existing = await source_repo.get_by_url(competitor_id, normalized_link)
                if not existing:
                    await source_repo.create(
                        competitor_id=competitor_id,
                        url=normalized_link,
                        page_type=self._classify_url(normalized_link),
                    )
                    sources_created += 1
                else:
                    await source_repo.mark_crawled(existing.id)
                    sources_updated += 1

            elapsed = self._elapsed(start_time)
            return {
                "status": "success",
                "sources_discovered": len(links),
                "sources_created": sources_created,
                "sources_updated": sources_updated,
                "elapsed_seconds": elapsed,
            }
        except Exception as e:
            elapsed = self._elapsed(start_time)
            return {
                "status": "failed",
                "error": str(e),
                "sources_discovered": 0,
                "sources_created": 0,
                "sources_updated": 0,
                "elapsed_seconds": elapsed,
            }

    def _classify_url(self, url: str) -> str:
        url_lower = url.lower()
        if any(p in url_lower for p in ("service", "our-service", "what-we-do")):
            return "services"
        if any(p in url_lower for p in ("pric", "cost", "rate")):
            return "pricing"
        if any(p in url_lower for p in ("blog", "article", "news", "post")):
            return "content"
        if any(p in url_lower for p in ("about", "company", "team", "contact")):
            return "company"
        if any(p in url_lower for p in ("social", "follow")):
            return "social"
        if "sitemap" in url_lower:
            return "sitemap"
        return "general"
