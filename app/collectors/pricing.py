import asyncio
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.base import BaseCollector
from app.database.repositories.competitor_pricing_repository import CompetitorPricingRepository
from app.parsers.strategy_parser import StrategyParser
from app.utilities.content_hasher import compute_pricing_hash


class PricingCollector(BaseCollector):
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
                    "pricing_found": 0,
                    "pricing_created": 0,
                    "pricing_updated": 0,
                    "elapsed_seconds": self._elapsed(start_time),
                }

            html = result.html

            if await self.is_unchanged(competitor_id, url, html, session):
                return {
                    "status": "skipped",
                    "reason": "unchanged",
                    "pricing_found": 0,
                    "pricing_created": 0,
                    "pricing_updated": 0,
                    "elapsed_seconds": self._elapsed(start_time),
                }

            parsed = await asyncio.to_thread(self._parser.parse_for_type, html, url, "pricing")
            await self.store_raw(competitor_id, url, html, session, extracted_data=parsed)
            pricing_items = parsed["pricing"]

            pricing_repo = CompetitorPricingRepository(session)
            pricing_created = 0
            pricing_updated = 0

            from sqlalchemy import select
            stmt = select(pricing_repo._model.content_hash).where(pricing_repo._model.competitor_id == competitor_id)
            result = await session.execute(stmt)
            existing_hashes = set(result.scalars().all())

            for item in pricing_items:
                service_name = item.get("service_name", "Unknown")
                category = item.get("category")
                base_price = item.get("base_price")
                promotional_price = item.get("promotional_price")
                currency = item.get("currency", "USD")

                content_hash = compute_pricing_hash(
                    service_name, category, base_price, promotional_price, currency
                )

                existing = content_hash in existing_hashes
                await pricing_repo.upsert(
                    competitor_id=competitor_id,
                    content_hash=content_hash,
                    service_name=service_name,
                    category=category,
                    base_price=base_price,
                    promotional_price=promotional_price,
                    currency=currency,
                    discount=item.get("discount"),
                    membership_pricing=item.get("membership_pricing"),
                    subscription_plans=item.get("subscription_plans", {}),
                )
                if existing:
                    pricing_updated += 1
                else:
                    pricing_created += 1

            return {
                "status": "success",
                "pricing_found": len(pricing_items),
                "pricing_created": pricing_created,
                "pricing_updated": pricing_updated,
                "elapsed_seconds": self._elapsed(start_time),
            }
        except Exception as e:
            return {
                "status": "failed",
                "error": str(e),
                "pricing_found": 0,
                "pricing_created": 0,
                "pricing_updated": 0,
                "elapsed_seconds": self._elapsed(start_time),
            }
