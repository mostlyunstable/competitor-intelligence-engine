from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any

from bs4 import BeautifulSoup, Tag


@dataclass
class ParsedResult:
    company_name: str | None = None
    description: str | None = None
    logo: str | None = None
    industry: str | None = None
    headquarters: str | None = None
    contact_email: str | None = None
    contact_phone: str | None = None
    social_links: dict[str, str] = field(default_factory=dict)
    services: list[dict[str, Any]] = field(default_factory=list)
    pricing: list[dict[str, Any]] = field(default_factory=list)
    content: list[dict[str, Any]] = field(default_factory=list)
    social_profiles: list[dict[str, str | None]] = field(default_factory=list)
    confidence: float = 0.0
    strategy_results: dict[str, float] = field(default_factory=dict)

    def merge(self, other: "ParsedResult", strategy_name: str, weight: float) -> None:
        if other.company_name and not self.company_name:
            self.company_name = other.company_name
        if other.description and not self.description:
            self.description = other.description
        if other.logo and not self.logo:
            self.logo = other.logo
        if other.industry and not self.industry:
            self.industry = other.industry
        if other.headquarters and not self.headquarters:
            self.headquarters = other.headquarters
        if other.contact_email and not self.contact_email:
            self.contact_email = other.contact_email
        if other.contact_phone and not self.contact_phone:
            self.contact_phone = other.contact_phone
        if other.social_links:
            for k, v in other.social_links.items():
                if k not in self.social_links:
                    self.social_links[k] = v
        if other.services:
            existing_names = {s.get("name") for s in self.services}
            for svc in other.services:
                if svc.get("name") and svc["name"] not in existing_names:
                    self.services.append(svc)
                    existing_names.add(svc["name"])
        if other.pricing:
            existing_names = {p.get("service_name") for p in self.pricing}
            for price in other.pricing:
                if price.get("service_name") and price["service_name"] not in existing_names:
                    self.pricing.append(price)
                    existing_names.add(price["service_name"])
        if other.content:
            existing_titles = {c.get("title") for c in self.content}
            for item in other.content:
                if item.get("title") and item["title"] not in existing_titles:
                    self.content.append(item)
                    existing_titles.add(item["title"])
        if other.social_profiles:
            existing_platforms = {p.get("platform") for p in self.social_profiles}
            for profile in other.social_profiles:
                if profile.get("platform") and profile["platform"] not in existing_platforms:
                    self.social_profiles.append(profile)
                    existing_platforms.add(profile["platform"])
        self.strategy_results[strategy_name] = weight
        self.confidence = min(1.0, self.confidence + weight)

    def to_company_dict(self) -> dict[str, Any]:
        return {
            "url": "",
            "name": self.company_name,
            "logo": self.logo,
            "description": self.description,
            "industry": self.industry,
            "headquarters": self.headquarters,
            "operating_countries": [],
            "operating_cities": [],
            "service_categories": [],
            "contact_email": self.contact_email,
            "contact_phone": self.contact_phone,
            "social_links": self.social_links,
        }

    def to_service_dict(self) -> dict[str, Any]:
        return {"url": "", "services": self.services}

    def to_pricing_dict(self) -> dict[str, Any]:
        return {"url": "", "pricing": self.pricing}

    def to_content_dict(self) -> dict[str, Any]:
        return {"url": "", "content": self.content}

    def to_social_dict(self) -> dict[str, Any]:
        profiles = list(self.social_profiles)
        existing_platforms = {p.get("platform") for p in profiles}
        for platform, url in self.social_links.items():
            if platform not in existing_platforms:
                profiles.append(
                    {
                        "platform": platform,
                        "profile_url": url,
                        "username": None,
                    }
                )
                existing_platforms.add(platform)
        return {"url": "", "social_profiles": profiles}


class ParsingStrategy(ABC):
    @property
    @abstractmethod
    def name(self) -> str: ...

    @property
    @abstractmethod
    def weight(self) -> float: ...

    @abstractmethod
    def parse(self, soup: BeautifulSoup, url: str) -> ParsedResult: ...

    def _soup(self, html: str) -> BeautifulSoup:
        return BeautifulSoup(html, "html.parser")

    def _text(self, soup: BeautifulSoup | Tag, selector: str) -> str | None:
        element = soup.select_one(selector)
        return element.get_text(strip=True) if element else None

    def _texts(self, soup: BeautifulSoup | Tag, selector: str) -> list[str]:
        return [el.get_text(strip=True) for el in soup.select(selector)]

    def _attr(self, soup: BeautifulSoup | Tag, selector: str, attribute: str) -> str | None:
        element = soup.select_one(selector)
        value = element.get(attribute) if element else None
        if isinstance(value, list):
            return str(value[0]) if value else None
        return str(value) if value is not None else None

    def _attrs(self, soup: BeautifulSoup | Tag, selector: str, attribute: str) -> list[str]:
        result: list[str] = []
        for el in soup.select(selector):
            value = el.get(attribute)
            if isinstance(value, list):
                if value:
                    result.append(str(value[0]))
            elif value is not None:
                result.append(str(value))
        return result
