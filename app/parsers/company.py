import re
from typing import Any
from urllib.parse import urljoin

from app.parsers.base import BaseParser



class CompanyParser(BaseParser):
    def parse(self, html: str, url: str) -> dict[str, Any]:
        soup = self._soup(html)
        og_data = self._extract_from_opengraph(soup, url)

        return {
            "url": url,
            "name": og_data.get("name") or self._extract_name(soup),
            "logo": og_data.get("logo") or self._extract_logo(soup, url),
            "description": og_data.get("description") or self._extract_description(soup),
            "industry": self._extract_industry(soup),
            "headquarters": self._extract_headquarters(soup),
            "operating_countries": self._extract_countries(soup),
            "operating_cities": self._extract_cities(soup),
            "service_categories": self._extract_service_categories(soup),
            "contact_email": self._normalize_email(self._extract_email(soup)),
            "contact_phone": self._normalize_phone(self._extract_phone(soup)),
            "social_links": self._extract_social_links(soup, url),
        }

    def _extract_from_opengraph(self, soup: Any, base_url: str) -> dict[str, Any]:
        """Extract all OpenGraph meta tags into a structured dict."""
        og: dict[str, Any] = {}
        for meta in soup.select("meta[property^='og:']"):
            prop = str(meta.get("property", "")).replace("og:", "")
            content = meta.get("content", "")
            if content:
                og[prop] = str(content)
        result: dict[str, Any] = {}
        if og.get("site_name"):
            result["name"] = og["site_name"]
        elif og.get("title"):
            result["name"] = og["title"]
        if og.get("description"):
            result["description"] = og["description"]
        if og.get("image"):
            result["logo"] = urljoin(base_url, og["image"])
        return result

    def _extract_name(self, soup: Any) -> str | None:
        for selector in ["h1", "meta[property='og:site_name']", ".company-name", ".brand"]:
            text = self._text(soup, selector)
            if text:
                return text
        meta = self._attr(soup, "meta[property='og:site_name']", "content")
        return meta

    def _extract_logo(self, soup: Any, base_url: str) -> str | None:
        for selector in [
            "meta[property='og:image']",
            "link[rel='icon']",
            "link[rel='shortcut icon']",
            ".logo img",
            "header img",
        ]:
            src = self._attr(soup, selector, "content") or self._attr(soup, selector, "href")
            if src:
                return urljoin(base_url, src)
            img = self._attr(soup, selector, "src")
            if img:
                return urljoin(base_url, img)
        return None

    def _extract_description(self, soup: Any) -> str | None:
        for selector in [
            "meta[property='og:description']",
            "meta[name='description']",
            ".company-description",
            ".about-text",
        ]:
            text = self._text(soup, selector)
            if text:
                return text
        content = self._attr(soup, "meta[property='og:description']", "content")
        if content:
            return content
        content = self._attr(soup, "meta[name='description']", "content")
        return content

    def _extract_industry(self, soup: Any) -> str | None:
        for selector in [".industry", ".sector", "[data-industry]"]:
            text = self._text(soup, selector)
            if text:
                return text
        return None

    def _extract_headquarters(self, soup: Any) -> str | None:
        for selector in [".headquarters", ".hq", "[data-location]"]:
            text = self._text(soup, selector)
            if text:
                return text
        # Fall back to <address> element
        address_el = soup.select_one("address")
        if address_el:
            return address_el.get_text(separator=", ", strip=True)
        # Try geo meta tag
        geo = self._attr(soup, "meta[name='geo.placename']", "content")
        return geo

    def _extract_countries(self, soup: Any) -> list[str]:
        for selector in [".countries", ".operating-countries", "[data-countries]"]:
            text = self._text(soup, selector)
            if text:
                return [c.strip() for c in text.split(",")]
        return []

    def _extract_cities(self, soup: Any) -> list[str]:
        for selector in [".cities", ".operating-cities", "[data-cities]"]:
            text = self._text(soup, selector)
            if text:
                return [c.strip() for c in text.split(",")]
        return []

    def _extract_service_categories(self, soup: Any) -> list[str]:
        for selector in [".service-categories", ".categories", "[data-categories]"]:
            text = self._text(soup, selector)
            if text:
                return [c.strip() for c in text.split(",")]
        return []

    def _extract_email(self, soup: Any) -> str | None:
        email_link = self._attr(soup, "a[href^='mailto:']", "href")
        if email_link:
            return email_link.replace("mailto:", "").strip()
        for selector in [".email", "[data-email]", "meta[property='og:email']"]:
            text = self._text(soup, selector)
            if text and "@" in text:
                return text.strip()
        content = self._attr(soup, "meta[property='og:email']", "content")
        if content and "@" in content:
            return content.strip()
        return None

    def _extract_phone(self, soup: Any) -> str | None:
        phone_link = self._attr(soup, "a[href^='tel:']", "href")
        if phone_link:
            return phone_link.replace("tel:", "").strip()
        for selector in [".phone", ".telephone", "[data-phone]"]:
            text = self._text(soup, selector)
            if text:
                return text.strip()
        return None

    def _normalize_email(self, email: str | None) -> str | None:
        """Lowercase and validate email format."""
        if not email:
            return None
        email = email.lower().strip()
        if re.match(r"^[\w.+-]+@[\w-]+\.[\w.]+$", email):
            return email
        return None

    def _normalize_phone(self, phone: str | None) -> str | None:
        """Strip non-digit chars and validate length (7-15 digits per E.164)."""
        if not phone:
            return None
        digits_only = re.sub(r"\D", "", phone)
        if 7 <= len(digits_only) <= 15:
            return phone.strip()  # Return original but stripped (preserve formatting)
        return None

    def _extract_social_links(self, soup: Any, base_url: str) -> dict[str, str]:
        social = {}
        social_domains = {
            "linkedin.com": "linkedin",
            "facebook.com": "facebook",
            "instagram.com": "instagram",
            "twitter.com": "twitter",
            "x.com": "twitter",
            "youtube.com": "youtube",
            "pinterest.com": "pinterest",
            "threads.net": "threads",
        }
        for a_tag in soup.select("a[href]"):
            href = a_tag.get("href", "")
            for domain, platform in social_domains.items():
                if domain in href and platform not in social:
                    social[platform] = urljoin(base_url, href)
        return social
