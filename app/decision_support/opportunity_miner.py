"""Market opportunity detection from competitive gaps."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class MarketOpportunity:
    opportunity_type: str
    title: str
    opportunity_score: float
    description: str
    recommended_action: str = ""
    affected_categories: list[str] = field(default_factory=list)


class OpportunityMiner:
    """Detects pricing gaps, geographic whitespaces, and service category gaps."""

    def find_pricing_gaps(
        self, category_prices: dict[str, list[float]]
    ) -> list[MarketOpportunity]:
        opportunities = []
        for category, prices in category_prices.items():
            if len(prices) < 2:
                continue
            avg = sum(prices) / len(prices)
            spread = max(prices) - min(prices)
            if avg > 0 and spread > avg * 0.25:
                score = min(100, (spread / avg) * 100)
                opportunities.append(MarketOpportunity(
                    opportunity_type="pricing_gap",
                    title=f"Price gap in {category}",
                    opportunity_score=round(score, 1),
                    description=f"Prices range ₹{min(prices):.0f}–₹{max(prices):.0f} (avg ₹{avg:.0f})",
                    recommended_action=f"Position between ₹{min(prices):.0f} and ₹{avg:.0f}",
                    affected_categories=[category],
                ))
        return sorted(opportunities, key=lambda o: o.opportunity_score, reverse=True)

    def find_category_gaps(
        self, my_categories: set[str], all_categories: dict[str, int]
    ) -> list[MarketOpportunity]:
        opportunities = []
        for cat, comp_count in all_categories.items():
            if cat not in my_categories and comp_count >= 2:
                score = min(100, comp_count * 15)
                opportunities.append(MarketOpportunity(
                    opportunity_type="category_gap",
                    title=f"Enter {cat} market",
                    opportunity_score=round(score, 1),
                    description=f"{comp_count} competitors serve this category",
                    recommended_action=f"Launch {cat} services to capture market share",
                    affected_categories=[cat],
                ))
        return sorted(opportunities, key=lambda o: o.opportunity_score, reverse=True)

    def find_geographic_gaps(
        self, presence_regions: set[str], target_regions: list[str]
    ) -> list[MarketOpportunity]:
        opportunities = []
        for region in target_regions:
            if region not in presence_regions:
                opportunities.append(MarketOpportunity(
                    opportunity_type="geographic_gap",
                    title=f"Expand to {region.title()}",
                    opportunity_score=70.0,
                    description=f"No presence detected in {region}",
                    recommended_action=f"Evaluate {region} market demand and competition",
                    affected_categories=[],
                ))
        return opportunities

    def mine(
        self,
        my_categories: set[str],
        all_categories: dict[str, int],
        category_prices: dict[str, list[float]],
        presence_regions: set[str],
        target_regions: list[str],
    ) -> list[MarketOpportunity]:
        all_opps = []
        all_opps.extend(self.find_pricing_gaps(category_prices))
        all_opps.extend(self.find_category_gaps(my_categories, all_categories))
        all_opps.extend(self.find_geographic_gaps(presence_regions, target_regions))
        all_opps.sort(key=lambda o: o.opportunity_score, reverse=True)
        return all_opps[:15]
