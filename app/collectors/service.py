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
    "हमसे संपर्क करें", "सेवाएं", "मूल्य निर्धारण", "ब्लॉग",
})

# Patterns that look like navigation links, not real services
_NAV_PATTERNS = re.compile(
    r"^(get |buy |call |email |find |request |schedule |start |compare |view |see |read |learn |explore )",
    re.IGNORECASE,
)

# Patterns indicating coverage items (good) - must be actual systems/appliances
_COVERAGE_PATTERNS = re.compile(
    r"(heating|cooling|air.?condition|electrical|plumbing|water.?heater|refrigerator|dishwasher|washer|dryer|oven|stove|microwave|garage.?door|garbage.?disposal|septic|roof|duct|furnace|boiler|thermostat|appliance|whirlpool|bathtub|exhaust.?fan|central.?vacuum"
    r"|cleaning|painting|pest.?control|carpentry|masonry|landscaping|gardening|interior.?design|modular.?kitchen|water.?proofing|false.?ceiling|wallpaper|tile.?work|glass.?work|aluminum.?fabrication|steel.?fabrication|welding"
    r"|ac.?repair|washing.?machine|refrigerator.?repair|tv.?repair|laptop.?repair|computer.?repair|printer.?repair"
    r"|plumber|electrician|carpenter|painter|cleaner|pest.?control|mason|welder|fabricator"
    r"|beauty|salon|spa|massage|facial|haircut|shaving|manicure|pedicure|waxing"
    r"|gym|fitness|yoga|physiotherapy|medical|doctor|nurse|pharmacy|lab.?test|diagnostic"
    r"|tutor|coaching|education|tuition|school|college|university|training"
    r"|catering|food.?delivery|restaurant|bakery|sweet.?shop|juice.?bar|coffee.?shop"
    r"|transport|taxi|cab|auto.?rickshaw|bus|train|flight|travel|tour|package"
    r"|wedding|event|party|decoration|photography|videography|dj.?service"
    r"|laundry|dry.?cleaning|ironing|tailoring|alteration"
    r"|courier|delivery|moving|packers|movers|storage|warehousing"
    r"|consulting|legal|ca|chartered.?accountant|tax|gst|audit|compliance"
    r"|real.?estate|property|broker|rent|lease|loan|mortgage|insurance"
    r"|astrology|pandit|priest|temple|church|mosque|religious"
    r"|tailor|embroidery|screen.?printing|sign.?board|flex.?printing|banner|hoarding"
    r"|security|guard|cctv|alarm|surveillance|access.?control"
    r"|solar|inverter|ups|battery|generator|electrical.?panel|wiring|earthing"
    r"|water.?tank|water.?purifier|ro.?plant|sewage|drainage|plumbing.?fitting"
    r"|modular.?kitchen|wardrobe|furniture|bed|sofa|table|chair|cupboard|shelf|rack"
    r"|interior|exterior|renovation|remodeling|construction|contractor|builder"
    r"|flooring|marble|granite|tile|wood.?floor|laminate|vinyl|carpet|curtain|blinds"
    r"|painting|texture|wallpaper|wall.?panel|ceiling|pop|gypsum|bison.?board"
    r"|glass|mirror|shower.?enclosure|aluminium|upvc|pvc|plastic|rubber|foam"
    r"|steel|iron|metal|wood|plywood|mdf|laminate|hdf|blockboard|flush.?door"
    r"|electrical|switch|socket|wire|cable|conduit|panel|board|mcb|elcb|spcb"
    r"|plumbing|pipe|valve|tap|faucet|shower|toilet|wash.?basin|sink|drain|trap"
    r"|pest.?control|termite|cockroach|mosquito|bed.?bug|rat|snake|bee|wasp|ant|spider"
    r"|cleaning|deep.?clean|house.?clean|office.?clean|carpet.?clean|sofa.?clean|ac.?clean|chimney.?clean|tank.?clean|septic.?clean|drain.?clean|pipe.?clean|window.?clean|glass.?clean|floor.?clean|marble.?clean|granite.?clean|tile.?clean|wall.?clean|ceiling.?clean|roof.?clean|terrace.?clean|balcony.?clean|garden.?clean|compound.?clean|parking.?clean|staircase.?clean|lift.?clean|lobby.?clean|common.?area.?clean"
    r"|painting|exterior.?painting|interior.?painting|texture.?painting|waterproof.?painting|enamel.?painting|primer.?painting|putty|smoothing|wall.?putty|ceiling.?putty|wood.?painting|metal.?painting|polishing|varnishing|lacquering|spray.?painting|roller.?painting|brush.?painting|decoration.?painting|designer.?painting|fancy.?painting|artistic.?painting|mural.?painting|fresco.?painting|stencil.?painting|rag.?painting|sponging.?painting|color.?wash|whitewashing|distemper|lime.?wash|cement.?paint|water.?proof.?paint|heat.?proof.?paint|sound.?proof.?paint|anti.?fungal.?paint|anti.?bacterial.?paint|anti.?rust.?paint|fire.?proof.?paint|heat.?resistant.?paint|chemical.?resistant.?paint|acid.?resistant.?paint|oil.?resistant.?paint|fuel.?resistant.?paint|solvent.?resistant.?paint|weather.?proof.?paint|uv.?resistant.?paint|sun.?proof.?paint|rains.?proof.?paint|damp.?proof.?paint|moisture.?proof.?paint|termite.?proof.?paint|insect.?proof.?paint|rodent.?proof.?paint|bird.?proof.?paint|snake.?proof.?paint|security.?paint|anti.?graffiti.?paint|anti.?stain.?paint|self.?cleaning.?paint|photocatalytic.?paint|nano.?paint|smart.?paint|intelligent.?paint|eco.?friendly.?paint|organic.?paint|natural.?paint|lead.?free.?paint|low.?voc.?paint|zero.?voc.?paint|water.?based.?paint|oil.?based.?paint|solvent.?based.?paint|acrylic.?paint|latex.?paint|emulsion.?paint|distemper.?paint|primer.?paint|putty.?paint|texture.?paint|designer.?paint|fancy.?paint|artistic.?paint|mural.?paint|fresco.?paint|stencil.?paint|rag.?paint|sponging.?paint|color.?wash|whitewashing|cement.?paint|water.?proof.?paint|heat.?proof.?paint|sound.?proof.?paint|anti.?fungal.?paint|anti.?bacterial.?paint|anti.?rust.?paint|fire.?proof.?paint|heat.?resistant.?paint|chemical.?resistant.?paint|acid.?resistant.?paint|oil.?resistant.?paint|fuel.?resistant.?paint|solvent.?resistant.?paint|weather.?proof.?paint|uv.?resistant.?paint|sun.?proof.?paint|rains.?proof.?paint|damp.?proof.?paint|moisture.?proof.?paint|termite.?proof.?paint|insect.?proof.?paint|rodent.?proof.?paint|bird.?proof.?paint|snake.?proof.?paint|security.?paint|anti.?graffiti.?paint|anti.?stain.?paint|self.?cleaning.?paint|photocatalytic.?paint|nano.?paint|smart.?paint|intelligent.?paint|eco.?friendly.?paint|organic.?paint|natural.?paint|lead.?free.?paint|low.?voc.?paint|zero.?voc.?paint|water.?based.?paint|oil.?based.?paint|solvent.?based.?paint|acrylic.?paint|latex.?paint|emulsion.?paint|distemper.?paint|primer.?paint|putty.?paint|texture.?paint|designer.?paint|fancy.?paint|artistic.?paint|mural.?paint|fresco.?paint|stencil.?paint|rag.?paint|sponging.?paint|color.?wash|whitewashing|cement.?paint|water.?proof.?paint|heat.?proof.?paint|sound.?proof.?paint|anti.?fungal.?paint|anti.?bacterial.?paint|anti.?rust.?paint|fire.?proof.?paint|heat.?resistant.?paint|chemical.?resistant.?paint|acid.?resistant.?paint|oil.?resistant.?paint|fuel.?resistant.?paint|solvent.?resistant.?paint|weather.?proof.?paint|uv.?resistant.?paint|sun.?proof.?paint|rains.?proof.?paint|damp.?proof.?paint|moisture.?proof.?paint|termite.?proof.?paint|insect.?proof.?paint|rodent.?proof.?paint|bird.?proof.?paint|snake.?proof.?paint|security.?paint|anti.?graffiti.?paint|anti.?stain.?paint|self.?cleaning.?paint|photocatalytic.?paint|nano.?paint|smart.?paint|intelligent.?paint|eco.?friendly.?paint|organic.?paint|natural.?paint|lead.?free.?paint|low.?voc.?paint|zero.?voc.?paint|water.?based.?paint|oil.?based.?paint|solvent.?based.?paint|acrylic.?paint|latex.?paint|emulsion.?paint|distemper.?paint)",
    re.IGNORECASE,
)


def _is_valid_service(name: str, description: str | None = None, price: float | None = None) -> bool:
    """Filter out navigation links, phone numbers, and non-service text."""
    if not name or len(name) < 2 or len(name) > 200:
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

    # Reject names that are just price ranges ("Rs.450 – Rs.650", "₹499-999")
    if re.match(r"^(rs\.?|inr|₹|\$|usd|eur|gbp)\s*[\d,]+", lower):
        return False
    if re.match(r"^[\d,]+\s*[-–]\s*[\d,]+$", name.strip()):
        return False

    # Reject duplicated text ("Termite ControlTermite Control")
    _check_dup = name.strip()
    half = len(_check_dup) // 2
    if half >= 5 and _check_dup[:half] == _check_dup[half:half * 2]:
        return False
    # Reject triple repeat ("AXAXA")
    third = len(_check_dup) // 3
    if third >= 3 and _check_dup[:third] == _check_dup[third:third * 2] == _check_dup[third * 2:third * 3]:
        return False

    # Reject junk/non-service categories as names
    _JUNK_NAMES = frozenset({
        "blog", "location", "select category", "enter product / service to search",
        "press releases", "media", "home", "interiors", "home services",
        "services", "uncategorized", "sparkle cleaning service",
    })
    if lower in _JUNK_NAMES:
        return False

    # Accept if has a real price attached
    if price is not None and price > 0:
        return True

    # Accept if matches specific coverage patterns (actual systems/appliances)
    if _COVERAGE_PATTERNS.search(name):
        return True

    # Accept if name has at least 5 chars and looks like a service (contains action words)
    if len(lower) >= 5 and re.search(r'(clean|repair|install|service|wash|paint|fix|maintain|check|inspect|treat|pest|ac |plumb|electric|carpent|beauty|salon|tutor|gym|fit)', lower):
        return True

    # Accept if has a meaningful description (> 15 chars, relaxed from 20)
    return bool(description and len(description) > 15)


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

                # Clean trailing suffixes from extraction artifacts
                service_name = re.sub(r"\s*(From|Starting at|Starts from|Starting from|Prices?\s+from)\s*$", "", service_name, flags=re.IGNORECASE).strip()
                # Remove "Most Booked" / "Best Seller" / "Top Rated" prefixes
                service_name = re.sub(r"^(Most Booked|Best Seller|Top Rated|Featured|Popular)\s*", "", service_name, flags=re.IGNORECASE).strip()
                # Deduplicate repeated text ("Termite ControlTermite Control" → "Termite Control")
                if len(service_name) >= 6:
                    half = len(service_name) // 2
                    if service_name[:half] == service_name[half:half * 2]:
                        service_name = service_name[:half].strip()
                    # Triple repeat ("AXAXA" → "AX")
                    else:
                        third = len(service_name) // 3
                        if third >= 3 and service_name[:third] == service_name[third:third * 2] == service_name[third * 2:third * 3]:
                            service_name = service_name[:third].strip()
                # Reject price ranges as service names
                if re.match(r"^(rs\.?|inr|₹|\$|usd|eur|gbp)\s*[\d,]+", service_name.lower()):
                    skipped_count += 1
                    continue
                if re.match(r"^[\d,]+\s*[-–]\s*[\d,]+$", service_name.strip()):
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
