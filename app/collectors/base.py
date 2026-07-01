import logging
import time
from abc import ABC, abstractmethod
from typing import Any

from app.collectors.fetcher import FetchResult, HybridFetcher

logger = logging.getLogger(__name__)


class BaseCollector(ABC):
    def __init__(self) -> None:
        self._fetcher = HybridFetcher()

    async def close(self) -> None:
        await self._fetcher.close()

    async def fetch(self, url: str) -> FetchResult:
        """Fetch a page using hybrid strategy (httpx + Playwright fallback)."""
        return await self._fetcher.fetch(url)

    async def store_raw(
        self,
        competitor_id: int,
        url: str,
        html: str,
        session: Any,
        *,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        from app.database.repositories.raw_storage_repository import RawStorageRepository
        from app.utilities.content_hasher import compute_page_content_hash
        from app.utilities.url_normalizer import normalize_url

        normalized_url = normalize_url(url)
        content_hash = compute_page_content_hash(html, normalized_url)

        raw_repo = RawStorageRepository(session)
        await raw_repo.upsert(
            competitor_id=competitor_id,
            source_url=normalized_url,
            content_hash=content_hash,
            raw_html=html,
            raw_json={"url": normalized_url, "content_hash": content_hash},
            metadata=metadata,
        )

    @abstractmethod
    async def collect(
        self, competitor_id: int, url: str, *, session: Any, **kwargs: Any
    ) -> dict[str, Any]: ...

    async def collect_with_session(
        self, competitor_id: int, url: str, **kwargs: Any
    ) -> dict[str, Any]:
        from app.database.connection import db_manager

        async with db_manager.session() as session:
            return await self.collect(competitor_id, url, session=session, **kwargs)

    def _elapsed(self, start: float) -> float:
        return round(time.time() - start, 2)
