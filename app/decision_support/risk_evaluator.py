"""Strategic risk evaluation and threat matrix computation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class RiskSignal:
    risk_type: str
    threat_level: str  # HIGH, MEDIUM, LOW
    risk_score: float
    description: str
    evidence: list[str] = field(default_factory=list)
    recommended_mitigation: str = ""


class StrategicRiskEvaluator:
    """Evaluates strategic risks from competitive intelligence data."""

    RISK_THRESHOLDS = {
        "price_war": {"high": 0.7, "medium": 0.4},
        "market_share_erosion": {"high": 0.6, "medium": 0.3},
        "expansion_collision": {"high": 0.65, "medium": 0.35},
        "service_commoditization": {"high": 0.6, "medium": 0.3},
    }

    def evaluate(
        self,
        pricing_trend: float = 0.0,
        service_count_delta: float = 0.0,
        competitor_growth_rate: float = 0.0,
        category_overlap_pct: float = 0.0,
        recent_changes: int = 0,
    ) -> list[RiskSignal]:
        risks = []

        # Price war risk
        if pricing_trend < -0.15:
            score = min(1.0, abs(pricing_trend) * 3)
            risks.append(RiskSignal(
                risk_type="price_war",
                threat_level=self._classify(score, "price_war"),
                risk_score=round(score, 3),
                description=f"Price declining at {abs(pricing_trend)*100:.0f}% — potential price war",
                evidence=[f"Pricing trend: {pricing_trend:.3f}"],
                recommended_mitigation="Lock in annual contracts; differentiate on quality",
            ))

        # Market share erosion
        if competitor_growth_rate > 0.2 and service_count_delta > 5:
            score = min(1.0, competitor_growth_rate * 2 + service_count_delta * 0.02)
            risks.append(RiskSignal(
                risk_type="market_share_erosion",
                threat_level=self._classify(score, "market_share_erosion"),
                risk_score=round(score, 3),
                description=f"Competitor growing at {competitor_growth_rate*100:.0f}% with +{service_count_delta:.0f} services",
                evidence=[f"Growth rate: {competitor_growth_rate:.3f}", f"Service delta: {service_count_delta}"],
                recommended_mitigation="Accelerate feature development; match service breadth",
            ))

        # Expansion collision
        if category_overlap_pct > 0.6:
            score = category_overlap_pct
            risks.append(RiskSignal(
                risk_type="expansion_collision",
                threat_level=self._classify(score, "expansion_collision"),
                risk_score=round(score, 3),
                description=f"{category_overlap_pct*100:.0f}% category overlap — direct competition",
                evidence=[f"Overlap: {category_overlap_pct:.1%}"],
                recommended_mitigation="Differentiate in high-overlap categories; defend key accounts",
            ))

        # Service commoditization
        if recent_changes > 10:
            score = min(1.0, recent_changes * 0.05)
            risks.append(RiskSignal(
                risk_type="service_commoditization",
                threat_level=self._classify(score, "service_commoditization"),
                risk_score=round(score, 3),
                description=f"{recent_changes} recent changes — rapid market evolution",
                evidence=[f"Changes in period: {recent_changes}"],
                recommended_mitigation="Monitor pricing closely; prepare counter-offers",
            ))

        risks.sort(key=lambda r: r.risk_score, reverse=True)
        return risks

    def _classify(self, score: float, risk_type: str) -> str:
        t = self.RISK_THRESHOLDS.get(risk_type, {"high": 0.6, "medium": 0.3})
        if score >= t["high"]:
            return "HIGH"
        elif score >= t["medium"]:
            return "MEDIUM"
        return "LOW"
