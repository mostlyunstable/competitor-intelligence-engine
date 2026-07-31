"""Location validation and scoring for Indian/Chennai competitors."""

import re
from dataclasses import dataclass, field

import structlog

logger = structlog.get_logger(__name__)

# Indian cities with coordinates (for future GPS-based validation)
INDIAN_CITIES = {
    "chennai": {"state": "Tamil Nadu", "region": "South India", "priority": 1},
    "mumbai": {"state": "Maharashtra", "region": "West India", "priority": 2},
    "bangalore": {"state": "Karnataka", "region": "South India", "priority": 2},
    "bengaluru": {"state": "Karnataka", "region": "South India", "priority": 2},
    "hyderabad": {"state": "Telangana", "region": "South India", "priority": 2},
    "pune": {"state": "Maharashtra", "region": "West India", "priority": 3},
    "delhi": {"state": "Delhi", "region": "North India", "priority": 3},
    "new delhi": {"state": "Delhi", "region": "North India", "priority": 3},
    "kolkata": {"state": "West Bengal", "region": "East India", "priority": 3},
    "ahmedabad": {"state": "Gujarat", "region": "West India", "priority": 3},
    "jaipur": {"state": "Rajasthan", "region": "North India", "priority": 4},
    "lucknow": {"state": "Uttar Pradesh", "region": "North India", "priority": 4},
    "coimbatore": {"state": "Tamil Nadu", "region": "South India", "priority": 2},
    "madurai": {"state": "Tamil Nadu", "region": "South India", "priority": 2},
    "tiruchirappalli": {"state": "Tamil Nadu", "region": "South India", "priority": 2},
    "salem": {"state": "Tamil Nadu", "region": "South India", "priority": 3},
    "tirunelveli": {"state": "Tamil Nadu", "region": "South India", "priority": 3},
    "erode": {"state": "Tamil Nadu", "region": "South India", "priority": 3},
    "vellore": {"state": "Tamil Nadu", "region": "South India", "priority": 3},
}

# Indian TLDs and domain patterns
INDIAN_DOMAINS = [".in", ".co.in", ".org.in", ".net.in", ".gov.in"]

# Indian phone patterns
INDIAN_PHONE_PATTERNS = [
    r"\+91[\s-]?\d{10}",
    r"0\d{2,4}[\s-]?\d{6,8}",
    r"\d{10}",
]

# Chennai-specific keywords
CHENNAI_KEYWORDS = [
    "chennai", "madras", "t nagr", "t.nagar", "adyar", "adyar",
    "anna nagar", "velachery", "sholinganallur", "porur",
    " Tambaram", "chepauk", "triplicane", "mylapore",
    "nungambakkam", "chromepet", "pallavaram", "ambattur",
]


@dataclass
class LocationInfo:
    """Location information for a company."""
    is_indian: bool = False
    is_chennai: bool = False
    city: str = ""
    state: str = ""
    region: str = ""
    priority: int = 5  # 1=highest (Chennai), 5=lowest
    phone_indian: bool = False
    domain_indian: bool = False
    confidence: float = 0.0
    evidence: list[str] = field(default_factory=list)


class LocationValidator:
    """Validates and scores company location for Indian/Chennai market."""

    def validate(self, company_data: dict, url: str = "") -> LocationInfo:
        """Validate company location from extracted data."""
        info = LocationInfo()

        # Check domain
        if url:
            self._check_domain(info, url)

        # Check text content for city/state mentions
        text_content = self._extract_text(company_data)
        self._check_city_mentions(info, text_content)
        self._check_state_mentions(info, text_content)
        self._check_phone_numbers(info, text_content)

        # Calculate confidence score
        info.confidence = self._calculate_confidence(info)

        return info

    def _check_domain(self, info: LocationInfo, url: str) -> None:
        """Check if domain indicates Indian company."""
        url_lower = url.lower()
        for domain in INDIAN_DOMAINS:
            if domain in url_lower:
                info.domain_indian = True
                info.is_indian = True
                info.evidence.append(f"Indian domain: {domain}")
                break

    def _check_city_mentions(self, info: LocationInfo, text: str) -> None:
        """Check for city mentions in text."""
        text_lower = text.lower()
        for city, data in INDIAN_CITIES.items():
            if city in text_lower:
                info.is_indian = True
                info.city = city.title()
                info.state = data["state"]
                info.region = data["region"]
                info.priority = data["priority"]
                info.evidence.append(f"City mentioned: {city.title()}")

                if city == "chennai":
                    info.is_chennai = True
                break

    def _check_state_mentions(self, info: LocationInfo, text: str) -> None:
        """Check for state mentions in text."""
        text_lower = text.lower()
        tamil_nadu_patterns = ["tamil nadu", "tamilnadu", "tn"]
        for pattern in tamil_nadu_patterns:
            if pattern in text_lower:
                info.is_indian = True
                if not info.state:
                    info.state = "Tamil Nadu"
                    info.region = "South India"
                info.evidence.append(f"State mentioned: Tamil Nadu")
                break

    def _check_phone_numbers(self, info: LocationInfo, text: str) -> None:
        """Check for Indian phone numbers."""
        for pattern in INDIAN_PHONE_PATTERNS:
            matches = re.findall(pattern, text)
            if matches:
                info.phone_indian = True
                info.is_indian = True
                info.evidence.append(f"Indian phone found: {matches[0]}")
                break

    def _extract_text(self, data: dict) -> str:
        """Extract text content from company data."""
        texts = []
        for key, value in data.items():
            if isinstance(value, str):
                texts.append(value)
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, str):
                        texts.append(item)
                    elif isinstance(item, dict):
                        texts.extend(str(v) for v in item.values() if isinstance(v, str))
            elif isinstance(value, dict):
                texts.extend(str(v) for v in value.values() if isinstance(v, str))
        return " ".join(texts)

    def _calculate_confidence(self, info: LocationInfo) -> float:
        """Calculate confidence score for location."""
        score = 0.0

        if info.is_chennai:
            score += 0.5
        elif info.is_indian:
            score += 0.3

        if info.domain_indian:
            score += 0.2

        if info.phone_indian:
            score += 0.15

        if info.state:
            score += 0.1

        if info.city:
            score += 0.05

        return min(score, 1.0)

    def get_collection_priority(self, info: LocationInfo) -> int:
        """Get collection priority based on location (1=highest)."""
        if info.is_chennai:
            return 1
        elif info.is_indian and info.state == "Tamil Nadu":
            return 2
        elif info.is_indian:
            return 3
        return 5


location_validator = LocationValidator()
