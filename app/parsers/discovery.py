from typing import Any
from urllib.parse import urljoin

from app.parsers.base import BaseParser


class DiscoveryParser(BaseParser):
    def parse(self, html: str, url: str) -> dict[str, Any]:
        soup = self._soup(html)
        links = self._hrefs(soup, "a[href]")
        absolute_links = [urljoin(url, link) for link in links]

        sitemap_links = self._parse_sitemap_links(html, url)
        meta_links = self._parse_meta_links(soup, url)

        all_links = list(set(absolute_links + sitemap_links + meta_links))

        return {
            "url": url,
            "links": all_links,
            "link_count": len(all_links),
        }

    def _parse_sitemap_links(self, html: str, base_url: str) -> list[str]:
        soup = self._soup(html, parser="xml")
        links = []
        for loc in soup.select("urlset url loc"):
            if loc.string:
                links.append(urljoin(base_url, loc.string.strip()))
        for loc in soup.select("sitemapindex sitemap loc"):
            if loc.string:
                links.append(urljoin(base_url, loc.string.strip()))
        return links

    def _parse_meta_links(self, soup: Any, base_url: str) -> list[str]:
        links = []
        for tag in soup.select("link[href]"):
            href = tag.get("href")
            if href and tag.get("rel") in [
                ("canonical",),
                ["canonical"],
                ("alternate",),
                ["alternate"],
            ]:
                links.append(urljoin(base_url, href))
        return links
