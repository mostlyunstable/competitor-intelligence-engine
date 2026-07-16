from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup, Tag

from app.parsers.strategy import ParsedResult, ParsingStrategy

_HEADER_KW: dict[str, set[str]] = {
    "name": {"service", "plan", "name", "product", "feature", "item", "package", "tier"},
    "price": {
        "price",
        "cost",
        "rate",
        "fee",
        "charge",
        "amount",
        "total",
        "per",
        "monthly",
        "annual",
        "starting",
    },
    "currency": {"currency", "cur", "symbol"},
    "duration": {
        "duration",
        "term",
        "period",
        "length",
        "commitment",
        "billing",
        "cycle",
        "frequency",
    },
    "description": {"description", "details", "desc", "info", "about", "overview"},
    "category": {"category", "type", "class", "group", "section", "department"},
    "discount": {"discount", "saving", "offer", "promo", "deal", "special"},
    "rating": {"rating", "review", "score", "stars", "rank"},
    "features": {
        "features",
        "includes",
        "included",
        "what's included",
        "benefits",
        "what you get",
        "highlights",
        "capabilities",
    },
}

_TABLE_KW: dict[str, set[str]] = {
    "pricing": {
        "pricing",
        "plan",
        "subscription",
        "package",
        "tier",
        "rate",
        "cost",
        "price",
        "membership",
    },
    "services": {"service", "offering", "solution", "product", "catalog", "menu", "what we offer"},
    "membership": {"membership", "member", "club", "premium", "loyalty", "rewards", "vip"},
}


_PRICE_RE = re.compile(
    r"""
    (?:[\$\€\£\₹\¥]\s*[\d,]+(?:\.\d{1,2})?)
    |
    (?:[\d,]+(?:\.\d{1,2})?\s*(?:USD|EUR|GBP|INR|JPY|CAD|AUD|EUR)\b)
    |
    (?:\b(?:\d+[.,]\d{1,2})\s*(?:per|month|year|hour|week|day|annually|yearly)?)
    """,
    re.I | re.X,
)

_DURATION_RE = re.compile(
    r"(per\s*month|/month|/mo|monthly|per\s*year|/year|/yr|annually|"  # monthly/yearly
    r"per\s*hour|/hour|hourly|per\s*week|/week|weekly|"  # hourly/weekly
    r"per\s*day|/day|daily|"  # daily
    r"one.time|one.off|setup\s*fee|once|flat\s*fee)",  # one-time
    re.I,
)

_FEATURE_SEP_RE = re.compile(r"[•●◆◇‣-▪▸→➤⇒✓✔✗✘⊕⊖±·⋅]+")

_CURRENCY_SYMBOLS: dict[str, str] = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "₹": "INR",
    "¥": "JPY",
    "C$": "CAD",
    "A$": "AUD",
    "CHF": "CHF",
}

_CURRENCY_CODES: dict[str, str] = {
    "USD": "USD",
    "EUR": "EUR",
    "GBP": "GBP",
    "INR": "INR",
    "JPY": "JPY",
    "CAD": "CAD",
    "AUD": "AUD",
    "CHF": "CHF",
}


def _find_nearest_heading(el: Tag, *levels: str) -> str:
    """Return text of the nearest preceding heading, or empty string."""
    for tag in levels or ("h1", "h2", "h3", "h4", "h5", "h6"):
        prev = el.find_previous(tag)
        if prev:
            return prev.get_text(strip=True)
    return ""


def _table_classifier_heading(heading: str) -> str | None:
    """Classify a table by its nearby heading text."""
    lower = heading.lower()
    for table_type, keywords in _TABLE_KW.items():
        for kw in keywords:
            if kw in lower:
                return table_type
    return None


def _table_classifier_structure(table: Tag) -> str | None:
    """Classify a table by its structural patterns."""
    rows = table.find_all("tr")
    if not rows:
        return None
    all_text = table.get_text(" ", strip=True).lower()
    price_hits = sum(1 for _ in _PRICE_RE.finditer(all_text))
    if price_hits >= 3:
        return "pricing"
    dur_hits = len(_DURATION_RE.findall(all_text))
    if dur_hits >= 2:
        return "pricing"
    header_cells = table.find_all("th")
    header_text = " ".join(th.get_text(strip=True).lower() for th in header_cells)
    svc_hits = sum(
        1 for kw in (_TABLE_KW["services"] | _TABLE_KW["membership"]) if kw in header_text
    )
    if svc_hits:
        return "services"
    return None


def _classify_column(header_text: str) -> str:
    """Infer column type from header content."""
    lower = header_text.strip().lower()
    for col_type, keywords in _HEADER_KW.items():
        for kw in keywords:
            if kw in lower:
                return col_type
    if _PRICE_RE.search(lower):
        return "price"
    if _DURATION_RE.search(lower):
        return "duration"
    return "unknown"


def _parse_price(text: str | None) -> float | None:
    if not text:
        return None
    clean = text.replace(",", "")
    numbers = re.findall(r"[\d]+\.?\d*", clean)
    if numbers:
        try:
            return float(numbers[0])
        except ValueError:
            return None
    return None


def _detect_currency(text: str | None) -> str:
    if not text:
        return "USD"
    for sym, code in _CURRENCY_SYMBOLS.items():
        if sym in text:
            return code
    upper = text.upper()
    for code in _CURRENCY_CODES:
        if code in upper:
            return code
    return "USD"


def _parse_duration(text: str | None) -> str | None:
    if not text:
        return None
    m = _DURATION_RE.search(text)
    if m:
        raw = m.group(1).strip().lower()
        norm: dict[str, str] = {
            "per month": "monthly",
            "/month": "monthly",
            "/mo": "monthly",
            "monthly": "monthly",
            "per year": "yearly",
            "/year": "yearly",
            "/yr": "yearly",
            "annually": "yearly",
            "per hour": "hourly",
            "/hour": "hourly",
            "hourly": "hourly",
            "per week": "weekly",
            "/week": "weekly",
            "weekly": "weekly",
            "per day": "daily",
            "/day": "daily",
            "daily": "daily",
            "one-time": "one-time",
            "one off": "one-time",
            "setup fee": "one-time",
            "once": "one-time",
            "flat fee": "one-time",
        }
        return norm.get(raw, raw)
    return None


def _extract_features(cell: Tag) -> list[str]:
    """Extract individual features from a cell, split by bullets or line breaks."""
    html = str(cell)
    parts: list[str] = _FEATURE_SEP_RE.split(html)
    features: list[str] = []
    for part in parts:
        soup = BeautifulSoup(part, "lxml")
        text = soup.get_text(" ", strip=True)
        if text and len(text) > 2:
            features.append(text)
    if not features:
        raw = cell.get_text("\n", strip=True)
        features = [f.strip() for f in raw.split("\n") if f.strip() and len(f.strip()) > 2]
    return features


def _collect_header_labels(table: Tag) -> list[str]:
    """Return a list of column header labels."""
    thead = table.find("thead")
    if thead:
        row = thead.find("tr")
        if row:
            return [th.get_text(strip=True) for th in row.find_all(["th", "td"])]
    first_row = table.find("tr")
    if first_row:
        headers = first_row.find_all("th")
        if headers:
            return [th.get_text(strip=True) for th in headers]
    return []


def _collect_all_rows(table: Tag) -> list[list[Tag]]:
    """Return all data rows as lists of cells (td/th)."""
    rows: list[list[Tag]] = []
    tbody = table.find("tbody")
    if tbody:
        tr_elements = tbody.find_all("tr", recursive=False)
    else:
        tr_elements = table.find_all("tr", recursive=False)
    for row in tr_elements:
        if not isinstance(row, Tag):
            continue
        cells = row.find_all(["td", "th"])
        if cells:
            rows.append(cells)
    return rows


class TableExtractionStrategy(ParsingStrategy):
    @property
    def name(self) -> str:
        return "table_extraction"

    @property
    def weight(self) -> float:
        return 0.20

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult:
        result = ParsedResult()
        for table in soup.find_all("table"):
            self._process_table(table, result, url)
        return result

    def parse_segments(self, segments: list[Any], url: str) -> ParsedResult:
        result = ParsedResult()
        for seg in segments:
            if isinstance(seg, Tag):
                self._process_table(seg, result, url)
            else:
                sub = (
                    seg.to_soup()
                    if hasattr(seg, "to_soup")
                    else BeautifulSoup(str(seg), "lxml")
                )
                for table in sub.find_all("table"):
                    self._process_table(table, result, url)
        return result

    def _process_table(self, table: Tag, result: ParsedResult, url: str) -> None:
        if not isinstance(table, Tag):
            return
        rows = table.find_all("tr")
        if len(rows) < 2:
            return

        heading = _find_nearest_heading(table)
        caption = table.find("caption")
        context = caption.get_text(strip=True) if caption else heading

        table_type = _table_classifier_heading(context)
        if not table_type:
            table_type = _table_classifier_structure(table)
        if not table_type:
            table_type = "unknown"

        headers = _collect_header_labels(table)
        col_types: list[str] = [_classify_column(h) for h in headers] if headers else []

        data_rows = _collect_all_rows(table)
        has_thead = table.find("thead") is not None
        skip_header = 1 if headers and not has_thead else 0
        for row in data_rows[skip_header:]:
            self._extract_row(row, col_types, table_type, context, result, url)

    def _extract_row(
        self,
        cells: list[Tag],
        col_types: list[str],
        table_type: str,
        context: str,
        result: ParsedResult,
        url: str,
    ) -> None:
        if not cells:
            return

        row_texts = [c.get_text(" ", strip=True) for c in cells]
        if all(len(t) < 2 for t in row_texts):
            return

        inferred: dict[str, Any] = {"name": None, "features": []}
        for i, (cell, raw_text) in enumerate(zip(cells, row_texts, strict=False)):
            col_type = col_types[i] if i < len(col_types) else "unknown"
            self._ingest_cell(cell, raw_text, col_type, table_type, inferred)

        service_name = (
            inferred.get("name") or (_find_nearest_heading(cells[0]) if cells else "") or context
        )

        features: list[str] = inferred.get("features", [])
        features_str = "; ".join(features) if features else None

        base_price = inferred.get("price")
        promo_price = inferred.get("promo_price")
        currency = inferred.get("currency", "USD")
        duration = inferred.get("duration")

        if table_type == "pricing" or (table_type == "unknown" and base_price is not None):
            result.pricing.append(
                {
                    "service_name": service_name,
                    "category": inferred.get("category"),
                    "base_price": base_price,
                    "promotional_price": promo_price,
                    "currency": currency,
                    "discount": inferred.get("discount"),
                    "subscription_plans": {},
                    "membership_pricing": inferred.get(
                        "membership_pricing", service_name if table_type == "membership" else None
                    ),
                    "features": features,
                    "estimated_duration": duration,
                }
            )
        else:
            result.services.append(
                {
                    "name": service_name,
                    "description": inferred.get("description") or features_str,
                    "category": inferred.get("category")
                    or (table_type if table_type != "unknown" else None),
                    "starting_price": base_price,
                    "currency": currency or "USD",
                    "estimated_duration": duration,
                    "features": features,
                }
            )

    def _ingest_cell(
        self,
        cell: Tag,
        text: str,
        col_type: str,
        table_type: str,
        inferred: dict[str, Any],
    ) -> None:
        if col_type == "name":
            if not inferred.get("name"):
                inferred["name"] = text
        elif col_type == "price":
            price = _parse_price(text)
            if price is not None:
                if _price_is_promo(text):
                    inferred["promo_price"] = price
                else:
                    inferred["price"] = price
            if not inferred.get("currency"):
                inferred["currency"] = _detect_currency(text)
            if not inferred.get("duration"):
                inferred["duration"] = _parse_duration(text)
        elif col_type == "duration":
            dur = _parse_duration(text)
            if dur:
                inferred["duration"] = dur
        elif col_type == "currency":
            inferred["currency"] = _detect_currency(text)
        elif col_type == "discount":
            inferred["discount"] = text[:200] if text else None
        elif col_type == "description":
            inferred["description"] = text
        elif col_type == "category":
            inferred["category"] = text
        elif col_type == "features":
            inferred["features"].extend(_extract_features(cell))
        elif col_type == "rating":
            pass
        else:
            if not inferred.get("name"):
                inferred["name"] = text
            elif not inferred.get("description"):
                inferred["description"] = text
            elif inferred.get("price") is None and table_type in ("pricing", "services"):
                price = _parse_price(text)
                if price is not None:
                    inferred["price"] = price
                    if not inferred.get("currency"):
                        inferred["currency"] = _detect_currency(text)


def _price_is_promo(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in ("sale", "offer", "promo", "discount", "now", "save", "was"))


class TestTableExtractionStrategy:
    """Minimal self-test helpers."""

    pass
