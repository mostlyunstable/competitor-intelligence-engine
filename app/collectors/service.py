import asyncio
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.base import BaseCollector
from app.database.repositories.competitor_service_repository import CompetitorServiceRepository
from app.parsers.strategy_parser import StrategyParser
from app.utilities.content_hasher import compute_service_hash


class ServiceCollector(BaseCollector):
    def __init__(self) -> None:
        super().__init__()
        self._parser = StrategyParser()

    async def collect(
        self, competitor_id: int, url: str, *, session: AsyncSession, **kwargs: Any
    ) -> dict[str, Any]:
        start_time: float = time.time()

        try:
            result = await self.fetch(url, competitor_id)
            if result.not_modified:
                return {
                    "status": "skipped",
                    "reason": "not_modified",
                    "services_found": 0,
                    "services_created": 0,
                    "services_updated": 0,
                    "elapsed_seconds": self._elapsed(start_time),
                }

            html = result.html

            if await self.is_unchanged(competitor_id, url, html, session):
                return {
                    "status": "skipped",
                    "reason": "unchanged",
                    "services_found": 0,
                    "services_created": 0,
                    "services_updated": 0,
                    "elapsed_seconds": self._elapsed(start_time),
                }

            parsed = await asyncio.to_thread(self._parser.parse_for_type, html, url, "services")
            await self.store_raw(competitor_id, url, html, session, extracted_data=parsed)
            services = parsed["services"]

            service_repo = CompetitorServiceRepository(session)
            services_created = 0
            services_updated = 0

            # Check existence before native upsert to track created vs updated
            skipped_count = 0
            for svc in services:
                service_name = (svc.get("name") or "").strip()
                if not service_name or len(service_name) > 500:
                    skipped_count += 1
                    continue

                service_category = (svc.get("category") or "").strip() or None
                if service_category and len(service_category) > 200:
                    service_category = service_category[:200]

                description = (svc.get("description") or "").strip() or None
                if description and len(description) > 2000:
                    description = description[:2000]

                starting_price = svc.get("starting_price")
                if starting_price is not None:
                    try:
                        starting_price = float(starting_price)
                        if starting_price < 0:
                            starting_price = None
                    except (ValueError, TypeError):
                        starting_price = None

                currency = (svc.get("currency") or "USD").strip().upper()
                if len(currency) != 3:
                    currency = "USD"

                content_hash = compute_service_hash(
                    service_name, service_category, description, starting_price, currency
                )

                # Single existence check — native upsert handles the actual write
                existing = await self._get_existing(service_repo, competitor_id, content_hash)
                await service_repo.upsert(
                    competitor_id=competitor_id,
                    content_hash=content_hash,
                    service_name=service_name,
                    service_category=service_category,
                    description=description,
                    starting_price=starting_price,
                    currency=currency,
                    estimated_duration=svc.get("estimated_duration"),
                )
                if existing:
                    services_updated += 1
                else:
                    services_created += 1

            return {
                "status": "success",
                "services_found": len(services),
                "services_created": services_created,
                "services_updated": services_updated,
                "services_skipped": skipped_count,
                "elapsed_seconds": self._elapsed(start_time),
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "services_found": 0,
                "services_created": 0,
                "services_updated": 0,
                "elapsed_seconds": self._elapsed(start_time),
            }

    @staticmethod
    async def _get_existing(
        repo: CompetitorServiceRepository, competitor_id: int, content_hash: str
    ) -> bool:
        """Check if a service with this content hash already exists.

        Uses a lightweight existence check instead of fetching the full row.
        """
        from sqlalchemy import select

        stmt = (
            select(1)
            .where(
                repo._model.competitor_id == competitor_id,
                repo._model.content_hash == content_hash,
            )
            .limit(1)
        )
        result = await repo._session.execute(stmt)
        return result.scalar_one_or_none() is not None
