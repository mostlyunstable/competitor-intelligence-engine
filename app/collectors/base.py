import time
from abc import ABC, abstractmethod
from typing import Any

import structlog

from app.collectors.fetcher import FetchResult, HybridFetcher
from app.utilities.performance import ContentDeduplicator, URLDeduplicator

logger: Any = structlog.get_logger(__name__)

_shared_fetcher: HybridFetcher | None = None

# Shared deduplicators across all collectors.
# Reset via reset_deduplicators() at the start of each collection run
# to prevent unbounded memory growth.
_url_deduplicator = URLDeduplicator()
_content_deduplicator = ContentDeduplicator()


def reset_deduplicators() -> None:
    """Reset global deduplicators for a new collection run.

    Must be called at the start of each competitor collection to prevent
    the seen-URL sets and content-hash dicts from growing unboundedly
    across the process lifetime.
    """
    _url_deduplicator.reset()
    _content_deduplicator.reset()
    logger.debug("deduplicators_reset")


def get_shared_fetcher() -> HybridFetcher:
    """Get or create a shared HybridFetcher instance.

    Sharing the fetcher across collectors ensures:
    - Single httpx.AsyncClient connection pool
    - Single Playwright browser instance
    - Consistent rate limiting across all collectors
    """
    global _shared_fetcher
    if _shared_fetcher is None:
        _shared_fetcher = HybridFetcher()
    return _shared_fetcher


class BaseCollector(ABC):
    def __init__(self, fetcher: HybridFetcher | None = None) -> None:
        self._fetcher = fetcher or get_shared_fetcher()
        self._url_deduplicator = _url_deduplicator
        self._content_deduplicator = _content_deduplicator

    async def close(self) -> None:
        await self._fetcher.close()

    async def fetch(
        self, url: str, competitor_id: int | None = None, *, force_render: bool = False
    ) -> FetchResult:
        """Fetch a page using hybrid strategy (httpx + Playwright fallback)."""
        return await self._fetcher.fetch(url, competitor_id, force_render=force_render)

    def is_duplicate_url(self, url: str) -> bool:
        """Check if URL has been seen before."""
        return self._url_deduplicator.is_duplicate(url)

    def mark_url_seen(self, url: str) -> None:
        """Mark URL as seen."""
        self._url_deduplicator.mark_seen(url)

    def is_duplicate_content(self, content_hash: str, url: str) -> bool:
        """Check if content hash has been seen before for a different URL."""
        return self._content_deduplicator.is_duplicate(content_hash, url)

    def mark_content_seen(self, content_hash: str, url: str) -> None:
        """Mark content hash as seen for a URL."""
        self._content_deduplicator.register(content_hash, url)

    async def is_unchanged(self, competitor_id: int, url: str, html: str, session: Any) -> bool:
        from app.database.repositories.raw_storage_repository import RawStorageRepository
        from app.utilities.content_hasher import compute_page_content_hash
        from app.utilities.url_normalizer import normalize_url

        normalized_url = normalize_url(url)
        content_hash = compute_page_content_hash(html, normalized_url)

        raw_repo = RawStorageRepository(session)
        latest = await raw_repo.get_by_url(competitor_id, normalized_url)

        if latest and latest.content_hash == content_hash:
            logger.info("UNCHANGED_PAGE_SKIPPED", url=normalized_url, hash=content_hash)
            return True

        return False

    async def store_raw(
        self,
        competitor_id: int,
        url: str,
        html: str,
        session: Any,
        *,
        metadata: dict[str, Any] | None = None,
        extracted_data: dict[str, Any] | None = None,
    ) -> None:
        from app.database.repositories.raw_storage_repository import RawStorageRepository
        from app.storage.provider import storage_provider
        from app.utilities.content_hasher import compute_page_content_hash
        from app.utilities.url_normalizer import normalize_url

        normalized_url = normalize_url(url)
        content_hash = compute_page_content_hash(html, normalized_url)

        # Save raw html to Object Storage
        mime_type = "text/html"
        storage_uri = await storage_provider.save(content_hash, html, mime_type)
        file_size_bytes = len(html.encode("utf-8"))

        raw_repo = RawStorageRepository(session)
        await raw_repo.upsert(
            competitor_id=competitor_id,
            source_url=normalized_url,
            content_hash=content_hash,
            storage_uri=storage_uri,
            mime_type=mime_type,
            file_size_bytes=file_size_bytes,
            metadata=metadata,
            extracted_data=extracted_data,
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
