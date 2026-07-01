from typing import Any

from app.parsers.base import BaseParser


class ContentParser(BaseParser):
    def parse(self, html: str, url: str) -> dict[str, Any]:
        soup = self._soup(html)

        return {
            "url": url,
            "content": self._extract_content(soup, url),
        }

    def _extract_content(self, soup: Any, base_url: str) -> list[dict[str, Any]]:
        articles = []

        article_cards = soup.select(
            "article, .blog-post, .post-card, .article-card, "
            ".news-item, .press-release, [data-article]"
        )
        for card in article_cards:
            article = self._parse_article_card(card, base_url)
            if article.get("title"):
                articles.append(article)

        if not articles:
            articles = self._extract_from_listing(soup, base_url)

        return articles

    def _parse_article_card(self, card: Any, base_url: str) -> dict[str, Any]:
        title_el = card.select_one("h1, h2, h3, h4, .title, .headline")
        title = title_el.get_text(strip=True) if title_el else None

        link_el = card.select_one("a[href]")
        link = link_el.get("href", "") if link_el else None

        author = self._text(card, ".author, .byline, [data-author]")
        date = self._text(card, "time, .date, .publish-date, [data-date]")
        summary = self._text(card, ".summary, .excerpt, .teaser, p")

        content_type = self._detect_content_type(card, title or "")

        return {
            "title": title,
            "author": author,
            "publish_date": date,
            "url": link,
            "summary": summary,
            "content_type": content_type,
        }

    def _extract_from_listing(self, soup: Any, base_url: str) -> list[dict[str, Any]]:
        articles = []
        headings = soup.select("h2 a, h3 a, .post-title a, .article-title a")
        for link_el in headings:
            title = link_el.get_text(strip=True)
            href = link_el.get("href", "")
            parent = link_el.find_parent(["li", "div", "article"])
            summary = None
            if parent:
                summary_el = parent.select_one("p, .summary, .excerpt")
                if summary_el:
                    summary = summary_el.get_text(strip=True)

            articles.append(
                {
                    "title": title,
                    "author": None,
                    "publish_date": None,
                    "url": href,
                    "summary": summary,
                    "content_type": "article",
                }
            )
        return articles

    def _detect_content_type(self, card: Any, title: str) -> str:
        classes = " ".join(card.get("class", []))
        text = (classes + " " + title).lower()

        if any(kw in text for kw in ["blog", "post"]):
            return "blog"
        if any(kw in text for kw in ["news", "press", "release"]):
            return "news"
        if any(kw in text for kw in ["announcement", "launch"]):
            return "announcement"
        if any(kw in text for kw in ["update", "feature", "release"]):
            return "update"
        return "article"
