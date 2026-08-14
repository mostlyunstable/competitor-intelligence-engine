"""Strategic recommendation synthesis from intelligence data."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class StrategicRecommendation:
    category: str
    title: str
    recommendation: str
    impact_rating: str  # HIGH, MEDIUM, LOW
    confidence: float
    rationale: str = ""
    counter_actions: list[str] = field(default_factory=list)


class StrategicRecommendationGenerator:
    """Synthesizes executive-level strategic recommendations."""

    def generate(
        self,
        growth_direction: str = "stable",
        growth_score: float = 0.0,
        risk_signals: list[dict[str, Any]] | None = None,
        pricing_trend: float = 0.0,
        service_gap: int = 0,
        opportunities: list[dict[str, Any]] | None = None,
    ) -> list[StrategicRecommendation]:
        recs = []
        risk_signals = risk_signals or []
        opportunities = opportunities or []

        # Growth-based recommendations
        if growth_direction == "growing" and growth_score > 0.15:
            recs.append(StrategicRecommendation(
                category="growth_response",
                title="Competitor expanding aggressively",
                recommendation="Match pace in high-overlap categories; lock in key accounts with long-term contracts",
                impact_rating="HIGH",
                confidence=0.85,
                rationale=f"Growth score {growth_score:.2f} indicates rapid expansion",
                counter_actions=["Accelerate feature roadmap", "Increase marketing spend", "Offer loyalty discounts"],
            ))
        elif growth_direction == "declining":
            recs.append(StrategicRecommendation(
                category="growth_opportunity",
                title="Competitor showing weakness",
                recommendation="Capitalize on their decline by targeting their customer base with aggressive offers",
                impact_rating="MEDIUM",
                confidence=0.75,
                rationale=f"Declining growth ({growth_score:.2f}) signals market opportunity",
                counter_actions=["Launch targeted campaigns", " poach key talent", " acquire their suppliers"],
            ))

        # Risk-based recommendations
        high_risks = [r for r in risk_signals if r.get("threat_level") == "HIGH"]
        if high_risks:
            risk_types = [r["risk_type"] for r in high_risks]
            recs.append(StrategicRecommendation(
                category="risk_mitigation",
                title=f"High-risk threats detected: {', '.join(risk_types)}",
                recommendation="Implement immediate defensive measures across affected categories",
                impact_rating="HIGH",
                confidence=0.9,
                rationale=f"{len(high_risks)} high-risk signal(s) identified",
                counter_actions=[r.get("recommended_mitigation", "Monitor closely") for r in high_risks],
            ))

        # Pricing-based recommendations
        if pricing_trend < -0.2:
            recs.append(StrategicRecommendation(
                category="pricing_strategy",
                title="Aggressive price cuts detected",
                recommendation="Do NOT match full cut — protect margins with bundled value-adds",
                impact_rating="HIGH",
                confidence=0.8,
                rationale=f"Price trend {pricing_trend:.1%} requires strategic response",
                counter_actions=["Bundle services", "Highlight quality differentiators", "Offer annual plans"],
            ))
        elif pricing_trend > 0.2:
            recs.append(StrategicRecommendation(
                category="pricing_strategy",
                title="Market accepting higher prices",
                recommendation="Consider premium tier launch — market demonstrates pricing power",
                impact_rating="MEDIUM",
                confidence=0.7,
                rationale=f"Upward price trend {pricing_trend:.1%}",
                counter_actions=["Design premium offering", "A/B test price points", "Add premium features"],
            ))

        # Service gap recommendations
        if service_gap > 3:
            recs.append(StrategicRecommendation(
                category="service_expansion",
                title=f"Service gap of {service_gap} categories",
                recommendation="Prioritize entering top 3 missing categories to close competitive gap",
                impact_rating="MEDIUM",
                confidence=0.8,
                rationale=f"Missing {service_gap} categories vs market average",
                counter_actions=["Research top categories", "Hire specialists", "Partner with local providers"],
            ))

        recs.sort(key=lambda r: r.confidence, reverse=True)
        return recs[:8]
