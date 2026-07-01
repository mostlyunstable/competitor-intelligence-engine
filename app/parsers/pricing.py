from typing import Any

from app.parsers.base import BaseParser


class PricingParser(BaseParser):
    def parse(self, html: str, url: str) -> dict[str, Any]:
        soup = self._soup(html)

        return {
            "url": url,
            "pricing": self._extract_pricing(soup),
        }

    def _extract_pricing(self, soup: Any) -> list[dict[str, Any]]:
        pricing_items = []

        plan_cards = soup.select(
            ".pricing-card, .plan-card, .price-card, [data-plan], .tier, .package, .subscription"
        )
        for card in plan_cards:
            item = self._parse_plan_card(card)
            if item.get("service_name"):
                pricing_items.append(item)

        if not pricing_items:
            pricing_items = self._extract_pricing_from_tables(soup)

        if not pricing_items:
            pricing_items = self._extract_pricing_from_text(soup)

        return pricing_items

    def _parse_plan_card(self, card: Any) -> dict[str, Any]:
        name = self._text(card, "h2, h3, h4, .plan-name, .tier-name, .title")
        base_price = self._text(card, ".price, .base-price, .amount, [data-price]")
        promo_price = self._text(card, ".promo-price, .sale-price, .discount-price")
        discount = self._text(card, ".discount, .savings, .off")

        features = self._texts(card, "li, .feature")
        membership = self._text(card, ".membership, .membership-price")
        subscription = self._text(card, ".subscription, .monthly, .annual")

        return {
            "service_name": name,
            "category": self._text(card, ".category, .plan-type"),
            "base_price": self._parse_price(base_price),
            "promotional_price": self._parse_price(promo_price),
            "currency": self._detect_currency(base_price),
            "discount": self._parse_price(discount),
            "subscription_plans": self._parse_subscriptions(subscription, features),
            "membership_pricing": self._parse_membership(membership),
        }

    def _extract_pricing_from_tables(self, soup: Any) -> list[dict[str, Any]]:
        pricing_items = []
        tables = soup.select("table")
        for table in tables:
            rows = table.select("tr")
            if len(rows) < 2:
                continue
            for row in rows[1:]:
                cells = [td.get_text(strip=True) for td in row.select("td")]
                if len(cells) >= 2:
                    item = {
                        "service_name": cells[0],
                        "category": None,
                        "base_price": self._parse_price(cells[1] if len(cells) > 1 else None),
                        "promotional_price": None,
                        "currency": self._detect_currency(cells[1] if len(cells) > 1 else None),
                        "discount": None,
                        "subscription_plans": {},
                        "membership_pricing": None,
                    }
                    if len(cells) > 2:
                        item["category"] = cells[2]
                    pricing_items.append(item)
        return pricing_items

    def _extract_pricing_from_text(self, soup: Any) -> list[dict[str, Any]]:
        import re

        pricing_items: list[dict[str, Any]] = []
        text = soup.get_text()
        price_pattern = r"\$\d+(?:\.\d{2})?"
        matches = re.findall(price_pattern, text)
        for match in matches[:5]:
            pricing_items.append(
                {
                    "service_name": "Detected Price",
                    "category": None,
                    "base_price": self._parse_price(match),
                    "promotional_price": None,
                    "currency": "USD",
                    "discount": None,
                    "subscription_plans": {},
                    "membership_pricing": None,
                }
            )
        return pricing_items

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

    def _parse_subscriptions(
        self, subscription_text: str | None, features: list[str]
    ) -> dict[str, Any]:
        if not subscription_text:
            return {}
        return {"text": subscription_text, "features": features}

    def _parse_membership(self, membership_text: str | None) -> dict[str, Any] | None:
        if not membership_text:
            return None
        return {"text": membership_text}
