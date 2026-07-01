from typing import Any

from app.parsers.base import BaseParser


class ServiceParser(BaseParser):
    def parse(self, html: str, url: str) -> dict[str, Any]:
        soup = self._soup(html)

        return {
            "url": url,
            "services": self._extract_services(soup),
        }

    def _extract_services(self, soup: Any) -> list[dict[str, Any]]:
        services = []
        service_cards = soup.select(
            ".service-card, .service-item, .service, "
            "[data-service], .product-card, .product-item, .product"
        )
        for card in service_cards:
            service = self._parse_service_card(card)
            if service.get("name"):
                services.append(service)

        if not services:
            services = self._extract_services_from_text(soup)

        return services

    def _parse_service_card(self, card: Any) -> dict[str, Any]:
        name = self._text(card, "h2, h3, h4, .service-name, .product-name, .title") or self._text(
            card, "a"
        )
        description = self._text(card, "p, .description, .desc, .summary")
        price = self._text(card, ".price, .starting-price, [data-price]")
        duration = self._text(card, ".duration, .estimated-duration, [data-duration]")
        category = self._text(card, ".category, .service-category, [data-category]")

        return {
            "name": name,
            "description": description,
            "category": category,
            "starting_price": self._parse_price(price),
            "currency": self._detect_currency(price),
            "estimated_duration": duration,
        }

    def _extract_services_from_text(self, soup: Any) -> list[dict[str, Any]]:
        services = []
        headings = soup.select("h2, h3")
        for heading in headings:
            text = heading.get_text(strip=True)
            if any(
                keyword in text.lower()
                for keyword in ["service", "repair", "install", "maintenance", "plan"]
            ):
                desc_el = heading.find_next_sibling("p")
                services.append(
                    {
                        "name": text,
                        "description": desc_el.get_text(strip=True) if desc_el else None,
                        "category": None,
                        "starting_price": None,
                        "currency": None,
                        "estimated_duration": None,
                    }
                )
        return services

    def _parse_price(self, price_text: str | None) -> float | None:
        if not price_text:
            return None
        import re

        numbers = re.findall(r"[\d,]+\.?\d*", price_text.replace(",", ""))
        if numbers:
            try:
                return float(numbers[0])
            except ValueError:
                return None
        return None

    def _detect_currency(self, price_text: str | None) -> str:
        if not price_text:
            return "USD"
        if "$" in price_text:
            return "USD"
        if "€" in price_text:
            return "EUR"
        if "£" in price_text:
            return "GBP"
        if "₹" in price_text:
            return "INR"
        return "USD"
