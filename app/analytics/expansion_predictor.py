"""Regional expansion opportunity detection."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ExpansionOpportunity:
    region: str
    opportunity_score: float
    signal_type: str  # "url_signal", "service_gap", "geographic_gap"
    evidence: list[str] = field(default_factory=list)
    recommended_action: str = ""


class RegionalExpansionPredictor:
    """Detects geographic expansion signals and opportunities."""

    # Major Indian metros for home services
    TARGET_REGIONS = [
        "chennai", "mumbai", "delhi", "bangalore", "hyderabad",
        "pune", "kolkata", "ahmedabad", "jaipur", "lucknow",
        "coimbatore", "madurai", "trichy", "vellore", "salem",
    ]

    def detect_from_urls(self, urls: list[str], competitor_id: int) -> list[ExpansionOpportunity]:
        opportunities = []
        mentioned_regions = set()

        for url in urls:
            url_lower = url.lower()
            for region in self.TARGET_REGIONS:
                if region in url_lower:
                    mentioned_regions.add(region)

        # Regions NOT mentioned in URLs = potential expansion targets
        for region in self.TARGET_REGIONS:
            if region not in mentioned_regions:
                opportunities.append(ExpansionOpportunity(
                    region=region,
                    opportunity_score=0.6,
                    signal_type="geographic_gap",
                    evidence=[f"No URL presence detected for {region}"],
                    recommended_action=f"Monitor {region} market for expansion signals",
                ))

        return opportunities

    def detect_from_services(
        self, service_categories: list[str], region_mentions: dict[str, int]
    ) -> list[ExpansionOpportunity]:
        opportunities = []

        # Regions with services but low competitor presence
        for region, count in region_mentions.items():
            if count < 3:
                opportunities.append(ExpansionOpportunity(
                    region=region,
                    opportunity_score=round(0.7 - count * 0.1, 2),
                    signal_type="service_gap",
                    evidence=[f"Only {count} service(s) in {region}"],
                    recommended_action=f"Consider entering {region} with {', '.join(service_categories[:3])} services",
                ))

        return opportunities

    def compute_opportunities(
        self, urls: list[str], service_categories: list[str],
        region_mentions: dict[str, int], competitor_id: int
    ) -> list[ExpansionOpportunity]:
        url_opps = self.detect_from_urls(urls, competitor_id)
        svc_opps = self.detect_from_services(service_categories, region_mentions)

        # Merge and deduplicate
        seen = set()
        merged = []
        for opp in url_opps + svc_opps:
            key = (opp.region, opp.signal_type)
            if key not in seen:
                seen.add(key)
                merged.append(opp)

        merged.sort(key=lambda x: x.opportunity_score, reverse=True)
        return merged[:10]
