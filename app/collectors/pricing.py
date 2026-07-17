import asyncio
import re
import time
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.base import BaseCollector
from app.database.repositories.competitor_pricing_repository import CompetitorPricingRepository
from app.parsers.strategy_parser import StrategyParser
from app.utilities.content_hasher import compute_pricing_hash

# Navigation / junk patterns to reject from pricing
_NAV_NAMES_PRICING = frozenset({
    "home", "contact", "about", "about us", "services", "blog", "news",
    "faq", "faqs", "login", "sign up", "sign in", "search", "sitemap",
    "privacy policy", "terms of service", "terms", "user agreement",
    "accessibility", "careers", "jobs", "support", "help", "close",
    "menu", "skip to content", "back", "next", "prev", "submit",
    "cancel", "reset", "apply", "buy now", "purchase now", "contact us",
    "email us", "call us", "get a warranty", "get a quote",
})

_PRICING_PATTERNS = re.compile(
    r"(plan|pricing|price|cost|rate|fee|per month|per year|annually|monthly|starting at|\$)",
    re.IGNORECASE,
)


def _is_valid_pricing(service_name: str, base_price: float | None, category: str | None) -> bool:
    """Filter out navigation items from pricing results."""
    if not service_name or len(service_name) < 5 or len(service_name) > 200:
        return False

    lower = service_name.lower().strip()
    if lower in _NAV_NAMES_PRICING:
        return False

    if re.match(r"^[\d\s\-+().]+$", service_name):
        return False
    if "@" in service_name:
        return False
    if service_name.startswith(("http://", "https://", "www.", "/")):
        return False

    # Accept if it has a real price
    if base_price is not None and base_price > 0:
        return True

    # Accept if category looks like pricing
    if category and _PRICING_PATTERNS.search(category):
        return True

    # Accept if name itself mentions pricing concepts
    if _PRICING_PATTERNS.search(service_name):
        return True

    # Reject if it looks like navigation
    if re.match(r"^(get |buy |call |email |find |request |schedule |start |compare |view |see |read |learn |explore )", service_name, re.IGNORECASE):
        return False

    return False


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
            skipped_count = 0

            for item in pricing_items:
                service_name = (item.get("service_name") or "").strip()
                if not service_name or len(service_name) > 500:
                    skipped_count += 1
                    continue

                category = (item.get("category") or "").strip() or None
                if category and len(category) > 200:
                    category = category[:200]

                base_price = item.get("base_price")
                if base_price is not None:
                    try:
                        base_price = float(base_price)
                        if base_price < 0:
                            base_price = None
                    except (ValueError, TypeError):
                        base_price = None

                if not _is_valid_pricing(service_name, base_price, category):
                    skipped_count += 1
                    continue

                promotional_price = item.get("promotional_price")
                if promotional_price is not None:
                    try:
                        promotional_price = float(promotional_price)
                        if promotional_price < 0:
                            promotional_price = None
                    except (ValueError, TypeError):
                        promotional_price = None

                currency = (item.get("currency") or "USD").strip().upper()
                if len(currency) != 3:
                    currency = "USD"

                content_hash = compute_pricing_hash(
                    service_name, category, base_price, promotional_price, currency
                )

                existing = await self._get_existing(pricing_repo, competitor_id, content_hash)
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
                "pricing_skipped": skipped_count,
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

    @staticmethod
    async def _get_existing(
        repo: CompetitorPricingRepository, competitor_id: int, content_hash: str
    ) -> bool:
        """Lightweight existence check."""
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
