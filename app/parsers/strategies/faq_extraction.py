from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from app.parsers.strategy import ParsedResult, ParsingStrategy

_FAQ_HEADING_KWS = frozenset(
    {
        "faq",
        "frequently asked",
        "question",
        "answer",
        "common question",
        "got a question",
        "have a question",
        "help center",
        "knowledge base",
        "support",
    }
)

_SERVICE_KWS = frozenset(
    {"service", "offering", "solution", "product", "feature", "plan", "package", "tier", "option"}
)

_COVERAGE_KWS = frozenset(
    {
        "area",
        "location",
        "city",
        "region",
        "state",
        "zone",
        "coverage",
        "service area",
        "where",
        "serve",
        "operate",
    }
)

_PRICE_PAT = re.compile(
    r"(?:[\$\€\£\₹\¥]\s*[\d,]+(?:\.\d{1,2})?)"
    r"|(?:[\d,]+(?:\.\d{1,2})?\s*(?:USD|EUR|GBP|INR|JPY|CAD|AUD)\b)"
    r"|(?:\b(?:free|no charge|complimentary|included)\b)",
    re.I,
)

_DURATION_PAT = re.compile(
    r"(per\s*month|/month|monthly|per\s*year|/year|annually|per\s*hour|hourly|per\s*week|weekly)",
    re.I,
)

_FAQ_QUESTION_PAT = re.compile(
    r"^\s*(how|what|why|when|where|who|can|do|is|are|will|does|should|would|could|may|has|have)\b",
    re.I,
)

_COVERAGE_PAT = re.compile(
    r"(?:we\s+)?(?:serve|cover|operate|available\s+in|offer\s+in|service\s+(?:area|location)s?\s*(?:include|:)?\s*)(.+?)(?:\.|$)",
    re.I,
)


def _is_faq_heading(heading: Tag) -> bool:
    """Return True if heading text suggests an FAQ section."""
    text = heading.get_text(strip=True).lower()
    return any(kw in text for kw in _FAQ_HEADING_KWS)


def _looks_like_question(text: str) -> bool:
    return bool(_FAQ_QUESTION_PAT.match(text.strip()))


def _parse_details(form: Tag) -> list[tuple[str, str]]:
    """Extract Q/A pairs from <details>/<summary> elements."""
    pairs: list[tuple[str, str]] = []
    for details in form.find_all("details"):
        summary = details.find("summary")
        if not summary:
            continue
        question = summary.get_text(" ", strip=True)
        if not question:
            continue
        # Get all text, then remove summary text to get answer only
        all_text = details.get_text(" ", strip=True) or ""
        answer = all_text.replace(question, "", 1).strip()
        pairs.append((question, answer))
    return pairs


def _parse_definition_list(dl: Tag) -> list[tuple[str, str]]:
    """Extract term/definition pairs from <dl>."""
    pairs: list[tuple[str, str]] = []
    dts = dl.find_all("dt")
    dds = dl.find_all("dd")
    for dt, dd in zip(dts, dds, strict=False):
        q = dt.get_text(" ", strip=True)
        a = dd.get_text(" ", strip=True)
        if q and a:
            pairs.append((q, a))
    return pairs


def _parse_accordion(container: Tag) -> list[tuple[str, str]]:
    """Detect accordion patterns: heading followed immediately by a content block."""
    pairs: list[tuple[str, str]] = []
    headings = container.find_all(["h2", "h3", "h4"])
    accordion_candidates: list[tuple[Tag, Tag | None]] = []
    for h in headings:
        nxt = h.find_next_sibling()
        if nxt and nxt.name in ("div", "p", "section", "article"):
            accordion_candidates.append((h, nxt))
    if len(accordion_candidates) < 2:
        return []
    for h, content in accordion_candidates:
        q = h.get_text(" ", strip=True)
        if not q:
            continue
        a = content.get_text(" ", strip=True) if content else ""
        if a:
            pairs.append((q, a))
    return pairs


def _parse_microdata_faq(soup: BeautifulSoup) -> list[tuple[str, str]]:
    """Extract Q/A from FAQPage schema.org microdata."""
    pairs: list[tuple[str, str]] = []
    faq_container = soup.find(attrs={"itemtype": re.compile(r"FAQPage", re.I)})  # type: ignore[call-overload]
    if not faq_container:
        return pairs
    for question_el in faq_container.find_all(attrs={"itemprop": "mainEntity"}, recursive=True):
        q_el = question_el.find(attrs={"itemprop": "name"})
        a_el = question_el.find(attrs={"itemprop": "text"})
        q = q_el.get_text(" ", strip=True) if q_el else ""
        a = a_el.get_text(" ", strip=True) if a_el else ""
        if q and a:
            pairs.append((q, a))
    return pairs


def _extract_pricing_from_answer(text: str) -> list[dict[str, Any]]:
    """Extract pricing info from FAQ answer text."""
    pricing: list[dict[str, Any]] = []
    price_matches = _PRICE_PAT.finditer(text)
    for m in price_matches:
        raw = m.group(0)
        if raw.lower() in ("free", "no charge", "complimentary", "included"):
            continue
        clean = raw.replace(",", "")
        numbers = re.findall(r"[\d]+\.?\d*", clean)
        if numbers:
            try:
                price = float(numbers[0])
                currency = "USD"
                if "€" in raw:
                    currency = "EUR"
                elif "£" in raw:
                    currency = "GBP"
                elif "₹" in raw:
                    currency = "INR"
                elif "¥" in raw:
                    currency = "JPY"
                pricing.append(
                    {
                        "service_name": "FAQ Mentioned Service",
                        "category": None,
                        "base_price": price,
                        "promotional_price": None,
                        "currency": currency,
                        "discount": None,
                        "subscription_plans": {},
                        "membership_pricing": None,
                    }
                )
            except ValueError:
                continue
    return pricing


def _extract_service_from_answer(question: str, answer: str) -> list[dict[str, Any]]:
    """Extract service descriptions from FAQ Q/A that mention services."""
    services: list[dict[str, Any]] = []
    combined = (question + " " + answer).lower()
    matched_kws = [kw for kw in _SERVICE_KWS if kw in combined]
    if not matched_kws:
        return services
    lines = [line.strip() for line in re.split(r"[.!\n]", answer) if line.strip()]
    desc_lines = [line for line in lines if len(line) > 30]
    if desc_lines:
        name = question.strip()
        if len(name) > 100:
            name = name[:100]
        services.append(
            {
                "name": name,
                "description": desc_lines[0],
                "category": None,
                "starting_price": None,
                "currency": "USD",
                "estimated_duration": None,
            }
        )
    return services


def _extract_coverage_from_answer(answer: str) -> list[str]:
    """Extract coverage area mentions from answer text."""
    areas: list[str] = []
    for m in _COVERAGE_PAT.finditer(answer):
        raw = m.group(1).strip()
        parts = [p.strip() for p in re.split(r"[,;]", raw) if p.strip()]
        for part in parts:
            if len(part) > 2 and not _FAQ_QUESTION_PAT.match(part):
                areas.append(part)
    if not areas:
        lower = answer.lower()
        if any(kw in lower for kw in _COVERAGE_KWS):
            sentences = re.split(r"[.!?\n]", answer)
            for s in sentences:
                s = s.strip()
                if any(kw in s.lower() for kw in _COVERAGE_KWS) and len(s) > 10:
                    areas.append(s)
    return areas


class FaqExtractionStrategy(ParsingStrategy):
    @property
    def name(self) -> str:
        return "faq_extraction"

    @property
    def weight(self) -> float:
        return 0.20

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult:
        result = ParsedResult()
        pairs: list[tuple[str, str]] = []

        pairs.extend(_parse_details(soup))
        pairs.extend(_parse_microdata_faq(soup))

        for dl in soup.find_all("dl"):
            pairs.extend(_parse_definition_list(dl))

        for container in soup.find_all(["section", "div", "main", "article"]):
            if _is_faq_heading(container):
                pairs.extend(_parse_accordion(container))

        if not pairs:
            for container in soup.find_all(["div", "section"]):
                h = container.find(["h2", "h3", "h4"])
                if h and _is_faq_heading(h):
                    pairs.extend(_parse_accordion(container))

        seen_questions: set[str] = set()
        for question, answer in pairs:
            normalized_q = question.lower().strip()
            if normalized_q in seen_questions or not question:
                continue
            seen_questions.add(normalized_q)

            result.content.append(
                {
                    "title": question,
                    "author": None,
                    "publish_date": None,
                    "url": url,
                    "summary": answer[:2000] if answer else None,
                    "content_type": "faq",
                }
            )

            for pricing in _extract_pricing_from_answer(answer):
                existing = {p.get("service_name") for p in result.pricing}
                svc_name = pricing["service_name"]
                if svc_name not in existing:
                    existing.add(svc_name)
                    pricing_copy = dict(pricing)
                    pricing_copy["service_name"] = f"{question[:50]} — {svc_name}"
                    result.pricing.append(pricing_copy)

            for svc in _extract_service_from_answer(question, answer):
                existing = {s.get("name") for s in result.services}
                if svc["name"] not in existing:
                    result.services.append(svc)

            areas = _extract_coverage_from_answer(answer)
            for area in areas:
                # Add coverage areas as locations, not services
                existing = {loc.get("name") for loc in result.locations}
                if area not in existing:
                    result.locations.append(
                        {
                            "name": area,
                            "type": "coverage",
                            "source": "faq_coverage",
                        }
                    )

        return result

    def parse_segments(self, segments: list[Any], url: str) -> ParsedResult:
        result = ParsedResult()
        for seg in segments:
            if isinstance(seg, Tag):
                sub_result = self.parse(BeautifulSoup(str(seg), "html.parser"), url)
            else:
                sub = (
                    seg.to_soup()
                    if hasattr(seg, "to_soup")
                    else BeautifulSoup(str(seg), "html.parser")
                )
                sub_result = self.parse(sub, url)
            result.content.extend(sub_result.content)
            result.pricing.extend(sub_result.pricing)
            result.services.extend(sub_result.services)
        return result
