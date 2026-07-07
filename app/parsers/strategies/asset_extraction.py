"""Asset Extraction — documents, PDFs, brochures, downloads, technology stack.

Detects downloadable assets from:
  - Link href patterns: .pdf, .docx, .xlsx, .pptx, .zip
  - download attribute on anchors
  - Links near headings: "download", "brochure", "spec sheet", "whitepaper"
  - Technology signals: script src domains, meta generator tags, powered-by badges

No company-specific selectors. No class name dependencies.
"""

from __future__ import annotations

import re
from typing import TYPE_CHECKING
from urllib.parse import urljoin, urlparse

from app.parsers.strategy import ParsedResult, ParsingStrategy

if TYPE_CHECKING:
    from bs4 import BeautifulSoup

    from app.parsers.page_segmenter import PageSegment

# Document file extensions
_DOC_EXT = re.compile(r"\.(pdf|doc|docx|xls|xlsx|ppt|pptx|csv|txt|rtf|odt|ods|odp)$", re.IGNORECASE)

# Download-related anchor text patterns
_DOWNLOAD_KW = re.compile(
    r"\b(download|brochure|spec[\s-]sheet|whitepaper|ebook|case[\s-]study|"
    r"catalog|catalogue|price[\s-]list|menu|guide|checklist|template|"
    r"resource|report|fact[\s-]sheet|datasheet|pdf)\b",
    re.IGNORECASE,
)

# Technology detection: script src → technology
_TECH_SCRIPT_DOMAINS: dict[str, tuple[str, str]] = {
    "google-analytics.com": ("analytics", "Google Analytics"),
    "googletagmanager.com": ("analytics", "Google Tag Manager"),
    "googlesyndication.com": ("advertising", "Google Ads"),
    "facebook.net": ("analytics", "Facebook Pixel"),
    "hotjar.com": ("analytics", "Hotjar"),
    "hubspot.com": ("crm", "HubSpot"),
    "intercom.io": ("chat", "Intercom"),
    "zendesk.com": ("support", "Zendesk"),
    "drift.com": ("chat", "Drift"),
    "segment.com": ("analytics", "Segment"),
    "mixpanel.com": ("analytics", "Mixpanel"),
    "amplitude.com": ("analytics", "Amplitude"),
    "stripe.com": ("payment", "Stripe"),
    "paypal.com": ("payment", "PayPal"),
    "mailchimp.com": ("marketing", "Mailchimp"),
    "sendgrid.net": ("email", "SendGrid"),
    "cloudflare.com": ("cdn", "Cloudflare"),
    "amazonaws.com": ("hosting", "AWS"),
    "squarespace.com": ("cms", "Squarespace"),
    "wix.com": ("cms", "Wix"),
    "shopify.com": ("ecommerce", "Shopify"),
    "wordpress.com": ("cms", "WordPress"),
    "wp.com": ("cms", "WordPress"),
    "typekit.net": ("fonts", "Adobe Fonts"),
    "fonts.googleapis.com": ("fonts", "Google Fonts"),
}

# Meta generator patterns
_GENERATOR_PATTERN = re.compile(
    r"(wordpress|drupal|joomla|shopify|squarespace|wix|webflow|"
    r"gatsby|next\.js|nuxt|hexo|hugo|jekyll|craft|contentful|"
    r"hubspot|ghost|magento|prestashop|woocommerce|bigcommerce)",
    re.IGNORECASE,
)

# Heading keywords for download sections
_DOWNLOAD_HEADING_KW = frozenset({
    "download", "resources", "documents", "brochures", "literature",
    "whitepapers", "case studies", "guides", "templates", "toolkits",
})


class AssetExtractionStrategy(ParsingStrategy):
    """Extracts downloadable assets and technology stack signals."""

    @property
    def name(self) -> str:
        return "asset_extraction"

    @property
    def weight(self) -> float:
        return 0.15

    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult:
        result = ParsedResult()
        self._extract_documents(soup, result, url)
        self._extract_tech_from_scripts(soup, result)
        self._extract_tech_from_meta(soup, result)
        self._extract_tech_from_badges(soup, result)
        return result

    def parse_segments(self, segments: list[PageSegment], url: str) -> ParsedResult:
        result = ParsedResult()
        for seg in segments:
            soup = seg.to_soup()
            self._extract_documents(soup, result, url)
            if seg.segment_type in ("about", "footer", "hero"):
                self._extract_tech_from_scripts(soup, result)
                self._extract_tech_from_meta(soup, result)
                self._extract_tech_from_badges(soup, result)
        return result

    def _extract_documents(self, soup: BeautifulSoup, result: ParsedResult, url: str) -> None:
        seen_urls: set[str] = set()
        for a in soup.select("a[href]"):
            href = str(a.get("href", ""))
            if not href:
                continue
            full_url = urljoin(url, href)
            text = a.get_text(strip=True)

            # Check if this is a document download
            is_doc = bool(_DOC_EXT.search(href))
            is_download = a.has_attr("download")
            is_named_download = bool(text and _DOWNLOAD_KW.search(text))

            if not (is_doc or is_download or is_named_download):
                continue
            if full_url in seen_urls:
                continue
            seen_urls.add(full_url)

            # Determine asset type
            asset_type = "document"
            if is_doc:
                ext = href.rsplit(".", 1)[-1].lower() if "." in href else ""
                asset_type = ext if ext in ("pdf", "doc", "docx", "xls", "xlsx", "ppt", "pptx", "csv") else "document"
            elif is_download:
                asset_type = "download"

            result.assets.append({
                "url": full_url,
                "name": text if text else href.split("/")[-1].split("?")[0],
                "type": asset_type,
                "category": "document",
                "source": "asset_extraction",
            })

    def _extract_tech_from_scripts(self, soup: BeautifulSoup, result: ParsedResult) -> None:
        for script in soup.select("script[src]"):
            src = str(script.get("src", ""))
            if not src:
                continue
            parsed = urlparse(src)
            domain = parsed.netloc.lower()
            # Strip www. prefix
            if domain.startswith("www."):
                domain = domain[4:]

            for tech_domain, (category, tech_name) in _TECH_SCRIPT_DOMAINS.items():
                if tech_domain in domain:
                    self._add_tech(result, tech_name, category, "script_src")
                    break

    def _extract_tech_from_meta(self, soup: BeautifulSoup, result: ParsedResult) -> None:
        # Meta generator tag
        generator = soup.select_one('meta[name="generator"]')
        if generator:
            content = str(generator.get("content", ""))
            match = _GENERATOR_PATTERN.search(content)
            if match:
                self._add_tech(result, match.group(1).title(), "cms", "meta_generator")

        # Powered-by in meta
        for meta in soup.select('meta[name*="power"], meta[name*="theme"]'):
            content = str(meta.get("content", ""))
            if content:
                self._add_tech(result, content, "cms", "meta_powered_by")

    def _extract_tech_from_badges(self, soup: BeautifulSoup, result: ParsedResult) -> None:
        for img in soup.select("img"):
            alt = str(img.get("alt", "")).lower()
            title = str(img.get("title", "")).lower()
            src = str(img.get("src", "")).lower()
            combined = f"{alt} {title} {src}"

            if "powered by" in combined or "built with" in combined:
                # Extract the technology name
                for keyword in ("powered by", "built with"):
                    idx = combined.find(keyword)
                    if idx >= 0:
                        tech_text = combined[idx + len(keyword):].strip()
                        if tech_text and len(tech_text) < 50:
                            self._add_tech(result, tech_text.title(), "cms", "badge")
                            break

    @staticmethod
    def _add_tech(result: ParsedResult, name: str, category: str, method: str) -> None:
        name = name.strip()[:100]
        if not name:
            return
        # Deduplicate by name
        if any(t.get("name") == name for t in result.assets):
            return
        result.assets.append({
            "url": "",
            "name": name,
            "type": "technology",
            "category": category,
            "source": f"tech_{method}",
        })
