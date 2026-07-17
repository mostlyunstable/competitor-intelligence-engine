import asyncio
import re
import time
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.collectors.base import BaseCollector
from app.database.repositories.competitor_service_repository import CompetitorServiceRepository
from app.parsers.strategy_parser import StrategyParser
from app.utilities.content_hasher import compute_service_hash

# Navigation / junk patterns to reject
_NAV_NAMES = frozenset({
    "home", "contact", "about", "about us", "services", "pricing", "blog",
    "news", "faq", "faqs", "login", "sign up", "sign in", "register",
    "search", "sitemap", "privacy policy", "terms of service", "terms",
    "user agreement", "accessibility", "careers", "jobs", "support",
    "help", "close", "menu", "skip to content", "back", "next", "prev",
    "submit", "cancel", "reset", "apply", "buy now", "get a quote",
    "get a warranty", "purchase now", "contact us", "email us", "call us",
})

# Patterns that look like navigation links, not real services
_NAV_PATTERNS = re.compile(
    r"^(get |buy |call |email |find |request |schedule |start |compare |view |see |read |learn |explore )",
    re.IGNORECASE,
)

# Patterns indicating coverage items (good) - must be actual systems/appliances
_COVERAGE_PATTERNS = re.compile(
    r"(heating|cooling|air.?condition|electrical|plumbing|water.?heater|refrigerator|dishwasher|washer|dryer|oven|stove|microwave|garage.?door|garbage.?disposal|septic|roof|duct|furnace|boiler|thermostat|appliance|whirlpool|bathtub|exhaust.?fan|central.?vacuum)",
    re.IGNORECASE,
)


def _is_valid_service(name: str, description: str | None = None, price: float | None = None) -> bool:
    """Filter out navigation links, phone numbers, and non-service text."""
    if not name or len(name) < 5 or len(name) > 200:
        return False

    lower = name.lower().strip()

    # Reject exact nav names
    if lower in _NAV_NAMES:
        return False

    # Reject phone numbers, emails, URLs
    if re.match(r"^[\d\s\-+().]+$", name):
        return False
    if "@" in name:
        return False
    if name.startswith(("http://", "https://", "www.", "/")):
        return False

    # Reject navigation-pattern names
    if _NAV_PATTERNS.match(name):
        return False

    # Reject state-specific navigation ("California Residents", "Texas Coverage")
    if re.match(r"^[A-Z][a-z]+ (Residents|Coverage|Customers|Members)$", name):
        return False

    # Reject questions (page titles, FAQ items)
    if "?" in name:
        return False

    # Reject items with exclamation marks (marketing)
    if "!" in name:
        return False

    # Accept if has a real price attached
    if price is not None and price > 1.0:
        return True

    # Accept if matches specific coverage patterns (actual systems/appliances)
    if _COVERAGE_PATTERNS.search(name):
        return True

    # Accept if has a meaningful description (> 30 chars)
    if description and len(description) > 30:
        return True

    return False


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

                description = (svc.get("description") or "").strip() or None
                starting_price = svc.get("starting_price")
                if starting_price is not None:
                    try:
                        starting_price = float(starting_price)
                        if starting_price < 0:
                            starting_price = None
                    except (ValueError, TypeError):
                        starting_price = None

                if not _is_valid_service(service_name, description, starting_price):
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
