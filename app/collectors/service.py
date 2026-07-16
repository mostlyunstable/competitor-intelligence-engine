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

            # Pre-fetch existing hashes to prevent N+1 queries
            from sqlalchemy import select
            stmt = select(service_repo._model.content_hash).where(service_repo._model.competitor_id == competitor_id)
            result = await session.execute(stmt)
            existing_hashes = set(result.scalars().all())

            # Check existence before native upsert to track created vs updated
            for svc in services:
                service_name = svc.get("name", "Unknown")
                service_category = svc.get("category")
                description = svc.get("description")
                starting_price = svc.get("starting_price")
                currency = svc.get("currency", "USD")

                content_hash = compute_service_hash(
                    service_name, service_category, description, starting_price, currency
                )

                existing = content_hash in existing_hashes
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
