import warnings
from abc import ABC, abstractmethod
from typing import Any

from bs4 import BeautifulSoup, XMLParsedAsHTMLWarning

warnings.filterwarnings("ignore", category=XMLParsedAsHTMLWarning)


class BaseParser(ABC):
    @abstractmethod
    def parse(self, html: str, url: str) -> dict[str, Any]: ...

    def _soup(self, html: str) -> BeautifulSoup:
        if "xml" in html[:100].lower() or html.strip().startswith("<?xml"):
            return BeautifulSoup(html, "xml")
        return BeautifulSoup(html, "html.parser")

    def _text(self, soup: BeautifulSoup, selector: str) -> str | None:
        element = soup.select_one(selector)
        return element.get_text(strip=True) if element else None

    def _texts(self, soup: BeautifulSoup, selector: str) -> list[str]:
        return [el.get_text(strip=True) for el in soup.select(selector)]

    def _attr(self, soup: BeautifulSoup, selector: str, attribute: str) -> str | None:
        element = soup.select_one(selector)
        value = element.get(attribute) if element else None
        if isinstance(value, list):
            return str(value[0]) if value else None
        return str(value) if value is not None else None

    def _attrs(self, soup: BeautifulSoup, selector: str, attribute: str) -> list[str]:
        result: list[str] = []
        for el in soup.select(selector):
            value = el.get(attribute)
            if isinstance(value, list):
                if value:
                    result.append(str(value[0]))
            elif value is not None:
                result.append(str(value))
        return result

    def _hrefs(self, soup: BeautifulSoup, selector: str) -> list[str]:
        return self._attrs(soup, selector, "href")
