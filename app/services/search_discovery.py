"""Search-based competitor discovery for Indian/Chennai market."""

import re
from dataclasses import dataclass, field
from urllib.parse import urlparse

import httpx
import structlog

from app.configuration.settings import get_settings

logger = structlog.get_logger(__name__)

# Default search queries for Chennai home services
DEFAULT_SEARCH_QUERIES = [
    "home cleaning Chennai",
    "housekeeping Chennai",
    "deep cleaning Chennai",
    "appliance repair Chennai",
    "plumber Chennai",
    "electrician Chennai",
    "facility management Chennai",
    "car cleaning Chennai",
    "maid services Chennai",
    "home maintenance Chennai",
    "pest control Chennai",
    "painting services Chennai",
    "carpenter Chennai",
    "AC repair Chennai",
    "sofa cleaning Chennai",
    "carpet cleaning Chennai",
    "kitchen cleaning Chennai",
    "office cleaning Chennai",
]


@dataclass
class DiscoveredCompetitor:
    """A competitor discovered through search."""
    name: str = ""
    url: str = ""
    domain: str = ""
    description: str = ""
    search_query: str = ""
    rank: int = 0
    is_relevant: bool = False
    location_hint: str = ""
    service_categories: list[str] = field(default_factory=list)


class SearchBasedDiscovery:
    """Discovers competitors through web search results."""

    def __init__(self) -> None:
        self._settings = get_settings()
        self._search_engines = {
            "google": "https://www.google.com/search?q={query}&num={num_results}",
            "bing": "https://www.bing.com/search?q={query}&count={num_results}",
        }

    async def discover(
        self,
        queries: list[str] = None,
        num_results_per_query: int = 10,
        exclude_domains: list[str] = None,
    ) -> list[DiscoveredCompetitor]:
        """Discover competitors through search queries."""
        if queries is None:
            queries = DEFAULT_SEARCH_QUERIES

        if exclude_domains is None:
            exclude_domains = []

        all_competitors: dict[str, DiscoveredCompetitor] = {}

        async with httpx.AsyncClient(
            timeout=httpx.Timeout(30),
            headers={"User-Agent": get_settings().collector.user_agent},
            follow_redirects=True,
        ) as client:
            for query in queries:
                try:
                    competitors = await self._search_query(
                        client, query, num_results_per_query, exclude_domains
                    )
                    for comp in competitors:
                        if comp.domain not in all_competitors:
                            all_competitors[comp.domain] = comp
                        else:
                            # Update rank if better
                            existing = all_competitors[comp.domain]
                            if comp.rank < existing.rank:
                                existing.rank = comp.rank
                                existing.search_query = comp.query if hasattr(comp, 'query') else query
                except Exception as e:
                    logger.warning("search_query_failed", query=query, error=str(e))

        # Sort by rank
        result = sorted(all_competitors.values(), key=lambda x: x.rank)
        logger.info("discovery_complete", total=len(result), queries=len(queries))

        return result

    async def _search_query(
        self,
        client: httpx.AsyncClient,
        query: str,
        num_results: int,
        exclude_domains: list[str],
    ) -> list[DiscoveredCompetitor]:
        """Search for a single query and extract competitors."""
        competitors = []

        # Try Google first, fallback to Bing
        for engine_name, engine_url in self._search_engines.items():
            try:
                url = engine_url.format(query=query.replace(" ", "+"), num_results=num_results)
                response = await client.get(url)

                if response.status_code == 200:
                    competitors = self._parse_search_results(
                        response.text, query, exclude_domains
                    )
                    if competitors:
                        break
            except Exception as e:
                logger.warning("search_engine_failed", engine=engine_name, error=str(e))

        return competitors

    def _parse_search_results(
        self,
        html: str,
        query: str,
        exclude_domains: list[str],
    ) -> list[DiscoveredCompetitor]:
        """Parse search results HTML to extract competitors."""
        competitors = []

        # Extract URLs and titles from search results
        # This is a simplified parser - in production, use a proper HTML parser
        url_pattern = r'href="(https?://[^"]+)"'
        urls = re.findall(url_pattern, html)

        rank = 1
        for url in urls:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.lower()

                # Skip search engines and common non-competitor sites
                if self._should_skip_domain(domain):
                    continue

                # Skip excluded domains
                if domain in exclude_domains:
                    continue

                # Extract name from URL
                name = self._extract_name_from_url(url)

                # Check relevance
                is_relevant = self._check_relevance(url, query)

                if is_relevant:
                    competitor = DiscoveredCompetitor(
                        name=name,
                        url=url,
                        domain=domain,
                        search_query=query,
                        rank=rank,
                        is_relevant=is_relevant,
                        service_categories=self._extract_service_categories(query),
                    )
                    competitors.append(competitor)
                    rank += 1

                    if rank > 10:  # Limit per query
                        break

            except Exception as e:
                logger.debug("url_parse_failed", url=url, error=str(e))

        return competitors

    def _should_skip_domain(self, domain: str) -> bool:
        """Check if domain should be skipped."""
        skip_patterns = [
            "google.com", "bing.com", "yahoo.com", "duckduckgo.com",
            "facebook.com", "twitter.com", "instagram.com", "linkedin.com",
            "youtube.com", "wikipedia.org", "amazon.com", "flipkart.com",
            "justdial.com", "sulekha.com", "indiamart.com", "tradeindia.com",
            "india.com", "timesofindia.com", "ndtv.com", "reuters.com",
        ]
        return any(pattern in domain for pattern in skip_patterns)

    def _extract_name_from_url(self, url: str) -> str:
        """Extract company name from URL."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()

        # Remove www. and common TLDs
        name = domain.replace("www.", "")
        for tld in [".com", ".in", ".co.in", ".org", ".net"]:
            name = name.replace(tld, "")

        # Convert to title case
        return name.replace("-", " ").replace("_", " ").title()

    def _check_relevance(self, url: str, query: str) -> bool:
        """Check if URL is relevant to the search query."""
        url_lower = url.lower()
        query_words = query.lower().split()

        # Check if query words appear in URL
        matches = sum(1 for word in query_words if word in url_lower)
        return matches >= 2  # At least 2 query words match

    def _extract_service_categories(self, query: str) -> list[str]:
        """Extract service categories from search query."""
        categories = []
        query_lower = query.lower()

        category_keywords = {
            "cleaning": ["cleaning", "clean"],
            "plumbing": ["plumber", "plumbing"],
            "electrical": ["electrician", "electrical"],
            "appliance-repair": ["appliance", "repair"],
            "pest-control": ["pest", "pest control"],
            "painting": ["painting", "painter"],
            "carpentry": ["carpenter", "carpentry"],
            "hvac": ["ac", "hvac", "air conditioning"],
            "facility-management": ["facility", "management"],
            "car-cleaning": ["car", "vehicle"],
            "maid-services": ["maid", "housekeeping"],
        }

        for category, keywords in category_keywords.items():
            if any(keyword in query_lower for keyword in keywords):
                categories.append(category)

        return categories


search_based_discovery = SearchBasedDiscovery()
