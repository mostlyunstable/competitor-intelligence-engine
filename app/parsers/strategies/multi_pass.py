"""
Multi-Pass Extraction Engine
============================
Implements 6 sequential passes over a parsed HTML document.

Pass 1  — Structured data      : JSON-LD, Schema.org, Microdata
Pass 2  — Semantic HTML        : main, article, section, table, dl, nav
Pass 3  — Repeated Structure Extraction: cards, grids, repeated sections/containers
Pass 4  — DOM relationships    : heading → paragraph → list → button → price
Pass 5  — Metadata             : OpenGraph, Twitter Card, canonical
Pass 6  — Regex fallback       : raw-text price, email, phone, social patterns

Rules
-----
- No competitor-specific selectors.
- No hardcoded HTML class names.
- Every pass contributes *partial* data to a shared result bag.
- A field that already has a value is NEVER overwritten by a later pass.
  (Lower-confidence passes fill in gaps, they never replace existing data.)
- The final merged object is as rich as possible.
"""

from __future__ import annotations

import contextlib
import json
import re
from typing import TYPE_CHECKING, Any, ClassVar
from urllib.parse import urljoin

from bs4 import BeautifulSoup, Tag

from app.parsers.strategy import ParsedResult, ParsingStrategy

if TYPE_CHECKING:
    from app.parsers.page_segmenter import PageSegment

# ---------------------------------------------------------------------------
# Shared constants
# ---------------------------------------------------------------------------

_SOCIAL_DOMAINS: dict[str, str] = {
    "linkedin.com": "linkedin",
    "facebook.com": "facebook",
    "instagram.com": "instagram",
    "twitter.com": "twitter",
    "x.com": "twitter",
    "youtube.com": "youtube",
    "pinterest.com": "pinterest",
    "tiktok.com": "tiktok",
    "threads.net": "threads",
}

_PRICE_RE = re.compile(
    r"""
    (?:
        (?P<sym>[$€£₹¥])       # leading currency symbol
        \s*
    )?
    (?P<amount>[\d,]+(?:\.\d{1,2})?)   # numeric amount
    (?:
        \s*(?P<code>USD|EUR|GBP|INR|JPY|AUD|CAD|SGD)  # trailing ISO code
    )?
    """,
    re.VERBOSE | re.IGNORECASE,
)

_EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}")
_PHONE_RE = re.compile(r"(?:\+?\d[\d\s\-().]{6,17}\d)")

_CURRENCY_MAP: dict[str, str] = {
    "$": "USD",
    "€": "EUR",
    "£": "GBP",
    "₹": "INR",
    "¥": "JPY",
}

_SERVICE_KW = frozenset(
    [
        "service",
        "repair",
        "install",
        "maintenance",
        "plan",
        "cleaning",
        "plumb",
        "hvac",
        "electric",
        "pest",
        "lawn",
        "paint",
        "handyman",
    ]
)

_PRICE_KW = frozenset(
    [
        "price",
        "pricing",
        "cost",
        "fee",
        "plan",
        "subscription",
        "package",
        "rate",
        "charge",
        "tariff",
        "tier",
    ]
)

_BLOG_KW = frozenset(["article", "blog", "post", "news", "update", "guide", "tips", "story"])


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _parse_price(text: str) -> tuple[float | None, str]:
    """Return (amount, currency_code) from arbitrary text."""
    m = _PRICE_RE.search(text.replace(",", ""))
    if not m:
        return None, "USD"
    amount_str = m.group("amount").replace(",", "")
    try:
        amount = float(amount_str)
    except ValueError:
        return None, "USD"
    sym = m.group("sym") or ""
    code = m.group("code") or ""
    currency = code.upper() if code else _CURRENCY_MAP.get(sym, "USD")
    return amount, currency


def _detect_social(href: str) -> str | None:
    for domain, name in _SOCIAL_DOMAINS.items():
        if domain in href:
            return name
    return None


def _safe_set(result: ParsedResult, field: str, value: Any) -> None:
    """Only set a scalar field if it isn't already populated."""
    if value and not getattr(result, field, None):
        setattr(result, field, value)


def _add_service(result: ParsedResult, name: str, **kwargs: Any) -> None:
    if not name:
        return
    name = name.strip()[:200]
    if any(s.get("name") == name for s in result.services):
        return
    result.services.append(
        {
            "name": name,
            "description": kwargs.get("description"),
            "category": kwargs.get("category"),
            "starting_price": kwargs.get("starting_price"),
            "currency": kwargs.get("currency", "USD"),
            "estimated_duration": kwargs.get("estimated_duration"),
        }
    )


def _add_pricing(result: ParsedResult, service_name: str, **kwargs: Any) -> None:
    if not service_name:
        return
    service_name = service_name.strip()[:200]
    if any(p.get("service_name") == service_name for p in result.pricing):
        return
    result.pricing.append(
        {
            "service_name": service_name,
            "category": kwargs.get("category"),
            "base_price": kwargs.get("base_price"),
            "promotional_price": kwargs.get("promotional_price"),
            "currency": kwargs.get("currency", "USD"),
            "discount": kwargs.get("discount"),
            "subscription_plans": kwargs.get("subscription_plans", {}),
            "membership_pricing": kwargs.get("membership_pricing"),
        }
    )


def _add_content(result: ParsedResult, title: str, **kwargs: Any) -> None:
    if not title:
        return
    title = title.strip()[:300]
    if any(c.get("title") == title for c in result.content):
        return
    result.content.append(
        {
            "title": title,
            "author": kwargs.get("author"),
            "publish_date": kwargs.get("publish_date"),
            "url": kwargs.get("url"),
            "summary": kwargs.get("summary"),
            "content_type": kwargs.get("content_type", "article"),
        }
    )


def _normalize_date(raw: str | None) -> str | None:
    if not raw:
        return None
    m = re.search(r"(\d{4}-\d{2}-\d{2})", raw)
    if m:
        return m.group(1)
    m = re.search(r"(\d{2})[/\-](\d{2})[/\-](\d{4})", raw)
    if m:
        return f"{m.group(3)}-{m.group(1)}-{m.group(2)}"
    return raw[:10] if len(raw) >= 10 else raw


# ---------------------------------------------------------------------------
# Pass 1: Structured data (JSON-LD, Schema.org microdata)
# ---------------------------------------------------------------------------


class _Pass1Structured:
    """Extract from <script type="application/ld+json"> and itemprop microdata."""

    _ORG_TYPES: ClassVar[set[str]] = {"LocalBusiness", "Organization", "Corporation", "Company"}
    _SVC_TYPES: ClassVar[set[str]] = {"Service", "ServiceList", "ItemList"}
    _PRICE_TYPES: ClassVar[set[str]] = {"Offer", "AggregateOffer", "Product"}
    _ARTICLE_TYPES: ClassVar[set[str]] = {"Article", "BlogPosting", "NewsArticle"}

    @staticmethod
    def _is_org_type(raw_type: str) -> bool:
        """Check if a Schema.org type is or inherits from Organization/LocalBusiness."""
        short = raw_type.split("/")[-1]
        if short in _Pass1Structured._ORG_TYPES:
            return True
        return short.endswith("Business") or short.endswith("Organization")

    def run(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        # ---- JSON-LD ----
        for script in soup.select('script[type="application/ld+json"]'):
            try:
                data = json.loads(script.string or "")
            except (json.JSONDecodeError, TypeError, ValueError):
                continue
            items = data if isinstance(data, list) else [data]
            for item in items:
                if isinstance(item, dict):
                    self._process(item, result, url)

        # ---- Schema.org microdata (itemprop) ----
        for scope in soup.select("[itemscope]"):
            item_type = str(scope.get("itemtype", ""))
            self._process_microdata(scope, item_type, result, url)

    def _process(self, item: dict[str, Any], result: ParsedResult, url: str) -> None:
        # Flatten @graph
        if "@graph" in item:
            for child in item["@graph"]:
                if isinstance(child, dict):
                    self._process(child, result, url)

        raw_type = item.get("@type", "")
        item_type = raw_type if isinstance(raw_type, str) else " ".join(raw_type)

        if self._is_org_type(item_type):
            self._org(item, result, url)
        if item_type in self._SVC_TYPES:
            self._service(item, result, url)
        if item_type in self._PRICE_TYPES:
            self._product(item, result)
        if item_type in self._ARTICLE_TYPES:
            self._article(item, result, url)
        if item_type == "FAQPage":
            self._faq(item, result, url)

        # Recurse into nested offers
        offers = item.get("offers")
        for offer in (
            offers if isinstance(offers, list) else ([offers] if isinstance(offers, dict) else [])
        ):
            if isinstance(offer, dict):
                self._product(offer, result)

        # Recurse into hasPart
        for child in item.get("hasPart", []):
            if isinstance(child, dict):
                self._process(child, result, url)

        # Recurse into itemListElement
        for child in item.get("itemListElement", []):
            if isinstance(child, dict):
                self._process(child, result, url)

    def _org(self, item: dict[str, Any], result: ParsedResult, url: str) -> None:
        _safe_set(result, "company_name", item.get("name"))
        _safe_set(result, "description", item.get("description"))
        _safe_set(result, "industry", item.get("industry"))
        _safe_set(result, "contact_email", item.get("email"))
        _safe_set(result, "contact_phone", item.get("telephone"))
        logo = item.get("logo")
        if logo and not result.logo:
            result.logo = urljoin(url, logo if isinstance(logo, str) else logo.get("url", ""))
        addr = item.get("address", {})
        if addr and not result.headquarters:
            if isinstance(addr, dict):
                parts = [
                    addr.get(f, "")
                    for f in ("streetAddress", "addressLocality", "addressRegion", "addressCountry")
                ]
                result.headquarters = ", ".join(p for p in parts if p)
            else:
                result.headquarters = str(addr)
        for link in item.get("sameAs") or []:
            if isinstance(link, str):
                platform = _detect_social(link)
                if platform and platform not in result.social_links:
                    result.social_links[platform] = link

    def _service(self, item: dict[str, Any], result: ParsedResult, url: str) -> None:
        name = item.get("name", "")
        if not name:
            return
        price, currency = None, "USD"
        offers = item.get("offers")
        if isinstance(offers, dict):
            p = offers.get("price") or offers.get("lowPrice")
            currency = offers.get("priceCurrency", "USD")
            if p:
                with contextlib.suppress(ValueError):
                    price = float(str(p).replace(",", ""))
        _add_service(
            result,
            name,
            description=item.get("description"),
            category=item.get("category"),
            starting_price=price,
            currency=currency,
        )

    def _product(self, item: dict[str, Any], result: ParsedResult) -> None:
        name = item.get("name", "Offer")
        currency = item.get("priceCurrency", "USD")
        raw_type = item.get("@type", "Offer")
        if raw_type == "AggregateOffer":
            low = item.get("lowPrice")
            high = item.get("highPrice")
            _add_pricing(
                result,
                name,
                base_price=float(str(low).replace(",", "")) if low is not None else None,
                promotional_price=float(str(high).replace(",", "")) if high is not None else None,
                currency=currency,
            )
        else:
            price = item.get("price")
            _add_pricing(
                result,
                name,
                base_price=float(str(price).replace(",", "")) if price is not None else None,
                currency=currency,
            )

    def _article(self, item: dict[str, Any], result: ParsedResult, url: str) -> None:
        title = item.get("headline") or item.get("name")
        if not title:
            return
        author = item.get("author")
        if isinstance(author, dict):
            author = author.get("name")
        elif isinstance(author, list) and author:
            a0 = author[0]
            author = a0.get("name") if isinstance(a0, dict) else a0
        _add_content(
            result,
            title,
            author=author,
            publish_date=_normalize_date(item.get("datePublished")),
            url=urljoin(url, item.get("url", "")),
            summary=item.get("description"),
            content_type="article",
        )

    def _faq(self, item: dict[str, Any], result: ParsedResult, url: str) -> None:
        for entity in item.get("mainEntity", []):
            if not isinstance(entity, dict):
                continue
            question = entity.get("name", "")
            answer_block = entity.get("acceptedAnswer", {})
            answer = answer_block.get("text", "") if isinstance(answer_block, dict) else ""
            if question:
                _add_content(
                    result,
                    question,
                    summary=answer[:500] if answer else None,
                    url=url,
                    content_type="faq",
                )

    def _process_microdata(
        self, scope: Tag, item_type: str, result: ParsedResult, url: str
    ) -> None:
        def _prop(name: str) -> str | None:
            el = scope.select_one(f'[itemprop="{name}"]')
            if not el:
                return None
            return str(el.get("content") or el.get("href") or el.get_text(strip=True)) or None

        if self._is_org_type(item_type):
            _safe_set(result, "company_name", _prop("name"))
            _safe_set(result, "description", _prop("description"))
            _safe_set(result, "contact_email", _prop("email"))
            _safe_set(result, "contact_phone", _prop("telephone"))
        if "Product" in item_type or "Offer" in item_type:
            name = _prop("name") or "Detected Product"
            price_raw = _prop("price")
            currency = _prop("priceCurrency") or "USD"
            price_val = None
            if price_raw:
                with contextlib.suppress(ValueError):
                    price_val = float(price_raw.replace(",", ""))
            _add_pricing(result, name, base_price=price_val, currency=currency)


# ---------------------------------------------------------------------------
# Pass 2: Semantic HTML
# ---------------------------------------------------------------------------


class _Pass2Semantic:
    """Scan structural HTML5 elements: main, article, section, table, dl, nav."""

    def run(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        self._header(soup, result, url)
        self._footer(soup, result, url)
        self._nav(soup, result)
        self._main(soup, result, url)
        self._articles(soup, result, url)
        self._sections(soup, result)
        self._definition_lists(soup, result)
        self._tables(soup, result)

    def _header(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        header = soup.select_one("header")
        if not header:
            return
        if not result.company_name:
            h1 = header.select_one("h1")
            if h1:
                result.company_name = h1.get_text(strip=True)
        if not result.logo:
            img = header.select_one("img[src]")
            if img:
                result.logo = urljoin(url, str(img.get("src", "")))

    def _footer(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        footer = soup.select_one("footer")
        if not footer:
            return
        if not result.contact_email:
            a = footer.select_one("a[href^='mailto:']")
            if a:
                result.contact_email = str(a["href"]).replace("mailto:", "").strip()
        if not result.contact_phone:
            a = footer.select_one("a[href^='tel:']")
            if a:
                result.contact_phone = str(a["href"]).replace("tel:", "").strip()
        # Social links in footer
        for a in footer.select("a[href]"):
            href = str(a.get("href", ""))
            platform = _detect_social(href)
            if platform and platform not in result.social_links:
                result.social_links[platform] = urljoin(url, href)

    def _nav(self, soup: BeautifulSoup, result: ParsedResult) -> None:
        # Collect social links from nav
        for nav in soup.select("nav"):
            for a in nav.select("a[href]"):
                href = str(a.get("href", ""))
                platform = _detect_social(href)
                if platform and platform not in result.social_links:
                    result.social_links[platform] = href

    def _main(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        main = soup.select_one("main") or soup.select_one('[role="main"]') or soup
        if not result.description:
            intro = main.select_one("p")
            if intro:
                text = intro.get_text(strip=True)
                if len(text) > 40:
                    result.description = text[:500]

    def _articles(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        for article in soup.select("article"):
            title_el = article.select_one("h1, h2, h3, h4")
            title = title_el.get_text(strip=True) if title_el else None
            if not title:
                continue
            link_el = article.select_one("a[href]")
            link = str(link_el.get("href", "")) if link_el else None
            summary_el = article.select_one("p")
            summary = summary_el.get_text(strip=True) if summary_el else None
            author_el = article.select_one("a[rel='author'], [rel='author']")
            author = author_el.get_text(strip=True) if author_el else None
            time_el = article.select_one("time[datetime]")
            pub_date = _normalize_date(str(time_el.get("datetime"))) if time_el else None
            _add_content(
                result,
                title,
                author=author,
                publish_date=pub_date,
                url=urljoin(url, link) if link else url,
                summary=summary,
                content_type="article",
            )

    def _sections(self, soup: BeautifulSoup, result: ParsedResult) -> None:
        for section in soup.select("section"):
            heading = section.select_one("h2, h3, h4")
            if not heading:
                continue
            text = heading.get_text(strip=True)
            lower = text.lower()
            if any(kw in lower for kw in _SERVICE_KW):
                desc_el = section.select_one("p")
                _add_service(
                    result, text, description=desc_el.get_text(strip=True) if desc_el else None
                )

    def _definition_lists(self, soup: BeautifulSoup, result: ParsedResult) -> None:
        for dl in soup.select("dl"):
            for dt, dd in zip(dl.select("dt"), dl.select("dd"), strict=False):
                term = dt.get_text(strip=True)
                definition = dd.get_text(strip=True)
                if any(kw in term.lower() for kw in _SERVICE_KW):
                    price, currency = _parse_price(definition)
                    _add_service(
                        result,
                        term,
                        description=definition,
                        starting_price=price,
                        currency=currency,
                    )

    def _tables(self, soup: BeautifulSoup, result: ParsedResult) -> None:
        for table in soup.select("table"):
            rows = table.select("tr")
            for row in rows[1:]:
                cells = [td.get_text(strip=True) for td in row.select("td")]
                if len(cells) < 2:
                    continue
                name = cells[0]
                price_text = cells[1] if len(cells) > 1 else ""
                price, currency = _parse_price(price_text)
                if price or any(kw in name.lower() for kw in _SERVICE_KW | _PRICE_KW):
                    _add_pricing(
                        result,
                        name,
                        base_price=price,
                        currency=currency,
                        category=cells[2] if len(cells) > 2 else None,
                    )


# ---------------------------------------------------------------------------
# Pass 3: Repeated Structure Extraction (cards, grids, repeated containers)
# ---------------------------------------------------------------------------


class _Pass3RepeatedStructure:
    """
    Detect repeated DOM patterns — no visual rendering, DOM structure only.
    Finds: cards, grids, repeated sections, repeated containers, service blocks.
    """

    def run(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        self._repeated_card_grids(soup, result, url)
        self._figure_cards(soup, result)
        self._data_attr_blocks(soup, result)

    def _repeated_card_grids(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        """
        Detect repeated structural patterns:
          - Homogeneous sibling groups (same tag, similar structure)
          - Grid containers (multiple direct children with same child tags)
          - Card patterns (div/li/article with heading + description + optional price)
        """
        candidates: list[Tag] = []
        for parent in soup.select("ul, ol, div, section, main, article, nav, aside, form"):
            children = [c for c in parent.children if isinstance(c, Tag)]
            if len(children) < 2:
                continue
            tags = {c.name for c in children}
            if len(tags) != 1:
                continue
            child_tag = next(iter(tags))
            if child_tag not in ("li", "div", "article", "section", "tr", "figure"):
                continue
            candidates.append(parent)
            self._extract_from_group(parent, children, result, url)

        self._detect_cards_from_structure(soup, result, url)

    def _extract_from_group(
        self,
        parent: Tag,
        children: list[Tag],
        result: ParsedResult,
        url: str,
    ) -> None:
        for child in children:
            heading = child.select_one("h1, h2, h3, h4, h5, h6")
            if not heading:
                continue
            title = heading.get_text(strip=True)
            if not title or len(title) < 2:
                continue

            all_text = child.get_text(" ", strip=True)
            price, currency = _parse_price(all_text)
            desc_el = child.select_one("p")
            desc = desc_el.get_text(strip=True) if desc_el else None
            link_el = child.select_one("a[href]")
            time_el = child.select_one("time[datetime]")

            # Classify the block by content keywords and structure
            lower_title = title.lower()
            lower_all = all_text.lower()
            has_price_kw = any(kw in lower_all for kw in _PRICE_KW)
            has_svc_kw = any(kw in lower_title for kw in _SERVICE_KW)
            has_date = time_el is not None
            has_link = link_el is not None

            if price is not None and has_price_kw:
                _add_pricing(result, title, base_price=price, currency=currency)
                if has_svc_kw:
                    _add_service(result, title, description=desc)
            elif price is not None and has_svc_kw:
                _add_service(
                    result, title, description=desc, starting_price=price, currency=currency
                )
            elif has_svc_kw:
                _add_service(result, title, description=desc)
            elif has_date or has_link:
                link = urljoin(url, str(link_el.get("href", ""))) if link_el else url
                pub_date = _normalize_date(str(time_el.get("datetime"))) if time_el else None
                _add_content(result, title, summary=desc, publish_date=pub_date, url=link)
            elif has_price_kw and price is not None:
                _add_pricing(result, title, base_price=price, currency=currency)

    def _detect_cards_from_structure(
        self, soup: BeautifulSoup, result: ParsedResult, url: str
    ) -> None:
        """
        Detect card-like patterns without class names.
        A card = a container whose direct children are divs/articles/sections
        that each contain exactly one heading and one paragraph (typical card pattern).
        """
        for container in soup.select("div, section, main"):
            children = [c for c in container.children if isinstance(c, Tag)]
            if len(children) < 2:
                continue
            # Check each child looks like a card: contains heading + text
            non_card = 0
            for child in children:
                h = child.select_one("h1, h2, h3, h4, h5, h6")
                p = child.select_one("p")
                if not h or not p:
                    non_card += 1
            if non_card > len(children) // 2:
                continue  # less than half look like cards
            for child in children:
                heading = child.select_one("h1, h2, h3, h4, h5, h6")
                if not heading:
                    continue
                title = heading.get_text(strip=True)
                if not title:
                    continue
                p = child.select_one("p")
                desc = p.get_text(strip=True) if p else None
                price, currency = _parse_price(child.get_text(" ", strip=True))
                if price is not None:
                    _add_pricing(result, title, base_price=price, currency=currency)
                _add_service(result, title, description=desc, starting_price=price)

    def _figure_cards(self, soup: BeautifulSoup, result: ParsedResult) -> None:
        for figure in soup.select("figure"):
            caption_el = figure.select_one("figcaption")
            if not caption_el:
                continue
            caption = caption_el.get_text(strip=True)
            if not caption:
                continue
            img = figure.select_one("img")
            alt = str(img.get("alt", "")) if img else ""
            price, currency = _parse_price(caption)
            if price is not None:
                _add_pricing(result, caption, base_price=price, currency=currency)
            elif any(kw in caption.lower() for kw in _SERVICE_KW):
                _add_service(result, caption, description=alt or None)

    def _data_attr_blocks(self, soup: BeautifulSoup, result: ParsedResult) -> None:
        """Elements with explicit data-* service/price attributes."""
        for el in soup.select(
            "[data-service-name], [data-service], [data-product-name], [data-card], [data-item]"
        ):
            name = (
                el.get("data-service-name")
                or el.get("data-service")
                or el.get("data-product-name")
                or el.get_text(strip=True)[:100]
            )
            if not name:
                continue
            price_raw = el.get("data-price") or el.get("data-amount")
            price, currency = _parse_price(str(price_raw)) if price_raw else (None, "USD")
            category = el.get("data-category")
            _add_service(
                result,
                str(name),
                description=el.get("data-description") or el.get_text(strip=True)[:200],
                category=category,
                starting_price=price,
                currency=currency,
                estimated_duration=el.get("data-duration"),
            )


# ---------------------------------------------------------------------------
# Pass 4: DOM relationship traversal (heading → paragraph → list → button → price)
# ---------------------------------------------------------------------------


class _Pass4DomRelationships:
    """
    Walk heading → sibling paragraph → sibling list → sibling button chain.
    Captures pricing/service blocks that aren't wrapped in semantic containers.
    """

    def run(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        for heading in soup.select("h1, h2, h3, h4"):
            text = heading.get_text(strip=True)
            if not text or len(text) > 150:
                continue

            # Walk next siblings until we hit another heading or a max depth
            paragraphs: list[str] = []
            list_items: list[str] = []
            price: float | None = None
            currency = "USD"
            depth = 0

            sibling = heading.find_next_sibling()
            while sibling and depth < 5:
                if isinstance(sibling, Tag):
                    tag = sibling.name
                    if tag in ("h1", "h2", "h3", "h4"):
                        break
                    if tag == "p":
                        t = sibling.get_text(strip=True)
                        if t:
                            paragraphs.append(t)
                            p, c = _parse_price(t)
                            if p is not None:
                                price, currency = p, c
                    elif tag in ("ul", "ol"):
                        for li in sibling.select("li"):
                            li_text = li.get_text(strip=True)
                            if li_text:
                                list_items.append(li_text)
                                p, c = _parse_price(li_text)
                                if p is not None:
                                    price, currency = p, c
                    elif tag in ("button", "a"):
                        btn_text = sibling.get_text(strip=True)
                        p, c = _parse_price(btn_text)
                        if p is not None:
                            price, currency = p, c
                depth += 1
                sibling = sibling.find_next_sibling()

            if not paragraphs and not list_items:
                continue

            description = paragraphs[0] if paragraphs else None

            lower = text.lower()
            if price is not None and any(kw in lower for kw in _PRICE_KW | _SERVICE_KW):
                _add_pricing(result, text, base_price=price, currency=currency)
            elif any(kw in lower for kw in _SERVICE_KW | _PRICE_KW):
                _add_service(
                    result, text, description=description, starting_price=price, currency=currency
                )


# ---------------------------------------------------------------------------
# Pass 5: Metadata (OpenGraph, Twitter Card, canonical)
# ---------------------------------------------------------------------------


class _Pass5Metadata:
    """Extract OpenGraph, Twitter Card tags and <link> metadata."""

    def run(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        # OpenGraph
        og_map = {
            "og:title": "company_name",
            "og:description": "description",
            "og:image": "logo",
        }
        for prop, field in og_map.items():
            tag = soup.select_one(f'meta[property="{prop}"]')
            if tag:
                _safe_set(result, field, tag.get("content"))

        # Twitter Card
        twitter_map = {
            "twitter:title": "company_name",
            "twitter:description": "description",
            "twitter:image": "logo",
        }
        for name, field in twitter_map.items():
            tag = soup.select_one(f'meta[name="{name}"]')
            if tag:
                _safe_set(result, field, tag.get("content"))

        # Generic meta description
        if not result.description:
            tag = soup.select_one('meta[name="description"]')
            if tag:
                result.description = str(tag.get("content"))

        # Social identity via <link rel="me">
        for link in soup.select('link[rel="me"]'):
            href = str(link.get("href", ""))
            platform = _detect_social(href)
            if platform and platform not in result.social_links:
                result.social_links[platform] = href


# ---------------------------------------------------------------------------
# Pass 6: Regex fallback (raw text scan)
# ---------------------------------------------------------------------------


class _Pass6Regex:
    """
    Last-resort scan of the full visible text for emails, phones,
    social URLs, and prices that earlier passes may have missed.
    """

    def run(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        body = soup.get_text(" ", strip=True)

        # Email
        if not result.contact_email:
            m = _EMAIL_RE.search(body)
            if m:
                result.contact_email = m.group(0).lower()

        # Phone
        if not result.contact_phone:
            m = _PHONE_RE.search(body)
            if m:
                raw = m.group(0).strip()
                if 7 <= len(re.sub(r"\D", "", raw)) <= 15:
                    result.contact_phone = raw

        # Social links from all anchors
        for a in soup.select("a[href]"):
            href = str(a.get("href", ""))
            platform = _detect_social(href)
            if platform and platform not in result.social_links:
                result.social_links[platform] = urljoin(url, href)

        # Prices in raw text where nothing was found earlier
        if not result.pricing:
            for match in _PRICE_RE.finditer(body.replace(",", "")):
                amount_str = match.group("amount")
                sym = match.group("sym") or ""
                code = match.group("code") or ""
                currency = code.upper() if code else _CURRENCY_MAP.get(sym, "USD")
                try:
                    amount = float(amount_str)
                except ValueError:
                    continue
                if amount > 0:
                    _add_pricing(result, "Detected Price", base_price=amount, currency=currency)
                    break  # one fallback price is enough; others are noise


# ---------------------------------------------------------------------------
# MultiPassStrategy — the public strategy class
# ---------------------------------------------------------------------------


class MultiPassStrategy(ParsingStrategy):
    """
    6-pass multi-pass extraction engine.

    Each pass runs sequentially and contributes partial results.
    Higher-confidence results (earlier passes) are never overwritten.
    """

    @property
    def name(self) -> str:
        return "multi_pass"

    @property
    def weight(self) -> float:
        # Higher weight because this strategy does the most thorough extraction
        return 0.40

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult:
        result = ParsedResult()

        # Pass 1 — Structured data (highest confidence)
        _Pass1Structured().run(soup, result, url)

        # Pass 2 — Semantic HTML
        _Pass2Semantic().run(soup, result, url)

        # Pass 3 — Repeated Structure Extraction (cards, grids, containers)
        _Pass3RepeatedStructure().run(soup, result, url)

        # Pass 4 — DOM relationship traversal
        _Pass4DomRelationships().run(soup, result, url)

        # Pass 5 — Metadata (OpenGraph / Twitter Card)
        _Pass5Metadata().run(soup, result, url)

        # Pass 6 — Regex fallback (lowest confidence, fills remaining gaps)
        _Pass6Regex().run(soup, result, url)

        return result

    def parse_segments(self, segments: list[PageSegment], url: str) -> ParsedResult:
        """Process each segment independently for passes that benefit from segmentation."""
        result = ParsedResult()

        # Pass 1 — Structured data (global, but prefer segment with most JSON-LD)
        best_jsonld_segment = max(
            segments,
            key=lambda s: len(s.element.select('script[type="application/ld+json"]')),
            default=None,
        )
        if best_jsonld_segment:
            _Pass1Structured().run(best_jsonld_segment.to_soup(), result, url)

        # Pass 2 — Semantic HTML (per segment)
        for seg in segments:
            _Pass2Semantic().run(seg.to_soup(), result, url)

        # Pass 3 — Repeated Structure Extraction (cards, grids, containers) (services/pricing segments)
        for seg in segments:
            if seg.segment_type in ("services", "pricing", "hero", "about"):
                _Pass3RepeatedStructure().run(seg.to_soup(), result, url)

        # Pass 4 — DOM relationship traversal (per segment)
        for seg in segments:
            _Pass4DomRelationships().run(seg.to_soup(), result, url)

        # Pass 5 — Metadata (global, first segment with <head>)
        for seg in segments:
            if seg.element.select_one("head"):
                _Pass5Metadata().run(seg.to_soup(), result, url)
                break

        # Pass 6 — Regex fallback (global, combined text)
        # Instead of serializing all segments to HTML and re-parsing,
        # extract text and links from each segment's cached soup directly.
        body_text = " ".join(seg.text_content() for seg in segments)
        social_soup = BeautifulSoup("", "html.parser")
        for seg in segments:
            for a in seg.to_soup().select("a[href]"):
                social_soup.append(a)
        combined_soup = BeautifulSoup(body_text, "html.parser")
        for a in social_soup.select("a[href]"):
            combined_soup.append(a)
        _Pass6Regex().run(combined_soup, result, url)

        return result
