"""Unit tests for Sprint 7 Decision Support modules."""

import pytest

from app.decision_support.risk_evaluator import StrategicRiskEvaluator, RiskSignal
from app.decision_support.opportunity_miner import OpportunityMiner, MarketOpportunity
from app.decision_support.recommendation import StrategicRecommendationGenerator, StrategicRecommendation


# ─── StrategicRiskEvaluator Tests ─────────────────────────────────────────


class TestStrategicRiskEvaluator:
    def test_init(self):
        e = StrategicRiskEvaluator()
        assert len(e.RISK_THRESHOLDS) == 4

    def test_no_risks_low_values(self):
        e = StrategicRiskEvaluator()
        risks = e.evaluate(
            pricing_trend=0.0,
            service_count_delta=0.0,
            competitor_growth_rate=0.0,
            category_overlap_pct=0.0,
            recent_changes=0,
        )
        assert len(risks) == 0

    def test_price_war_risk(self):
        e = StrategicRiskEvaluator()
        risks = e.evaluate(pricing_trend=-0.2)
        assert len(risks) == 1
        assert risks[0].risk_type == "price_war"
        assert risks[0].threat_level in ("HIGH", "MEDIUM", "LOW")
        assert 0.0 <= risks[0].risk_score <= 1.0

    def test_price_war_extreme(self):
        e = StrategicRiskEvaluator()
        risks = e.evaluate(pricing_trend=-0.5)
        assert risks[0].threat_level == "HIGH"

    def test_market_share_erosion(self):
        e = StrategicRiskEvaluator()
        risks = e.evaluate(competitor_growth_rate=0.3, service_count_delta=10)
        assert any(r.risk_type == "market_share_erosion" for r in risks)

    def test_expansion_collision(self):
        e = StrategicRiskEvaluator()
        risks = e.evaluate(category_overlap_pct=0.8)
        assert any(r.risk_type == "expansion_collision" for r in risks)

    def test_service_commoditization(self):
        e = StrategicRiskEvaluator()
        risks = e.evaluate(recent_changes=15)
        assert any(r.risk_type == "service_commoditization" for r in risks)

    def test_multiple_risks(self):
        e = StrategicRiskEvaluator()
        risks = e.evaluate(
            pricing_trend=-0.3,
            competitor_growth_rate=0.4,
            service_count_delta=12,
            category_overlap_pct=0.8,
            recent_changes=20,
        )
        assert len(risks) >= 3

    def test_risks_sorted_by_score(self):
        e = StrategicRiskEvaluator()
        risks = e.evaluate(
            pricing_trend=-0.3,
            competitor_growth_rate=0.4,
            service_count_delta=12,
            recent_changes=20,
        )
        scores = [r.risk_score for r in risks]
        assert scores == sorted(scores, reverse=True)

    def test_risk_signal_fields(self):
        e = StrategicRiskEvaluator()
        risks = e.evaluate(pricing_trend=-0.2)
        r = risks[0]
        assert hasattr(r, "risk_type")
        assert hasattr(r, "threat_level")
        assert hasattr(r, "risk_score")
        assert hasattr(r, "description")
        assert hasattr(r, "evidence")
        assert hasattr(r, "recommended_mitigation")
        assert len(r.evidence) > 0
        assert len(r.recommended_mitigation) > 0

    def test_classify_high(self):
        e = StrategicRiskEvaluator()
        assert e._classify(0.8, "price_war") == "HIGH"

    def test_classify_medium(self):
        e = StrategicRiskEvaluator()
        assert e._classify(0.5, "price_war") == "MEDIUM"

    def test_classify_low(self):
        e = StrategicRiskEvaluator()
        assert e._classify(0.1, "price_war") == "LOW"


# ─── OpportunityMiner Tests ───────────────────────────────────────────────


class TestOpportunityMiner:
    def test_init(self):
        m = OpportunityMiner()
        assert m is not None

    def test_pricing_gaps(self):
        m = OpportunityMiner()
        opps = m.find_pricing_gaps({
            "plumbing": [100.0, 200.0, 300.0],
            "cleaning": [50.0],
        })
        assert len(opps) >= 1
        assert opps[0].opportunity_type == "pricing_gap"
        assert opps[0].opportunity_score > 0

    def test_pricing_gaps_no_spread(self):
        m = OpportunityMiner()
        opps = m.find_pricing_gaps({"plumbing": [100.0, 100.0, 100.0]})
        assert len(opps) == 0

    def test_pricing_gaps_single_price(self):
        m = OpportunityMiner()
        opps = m.find_pricing_gaps({"plumbing": [100.0]})
        assert len(opps) == 0

    def test_category_gaps(self):
        m = OpportunityMiner()
        opps = m.find_category_gaps(
            my_categories={"plumbing"},
            all_categories={"plumbing": 3, "cleaning": 2, "painting": 4},
        )
        assert len(opps) >= 1
        cats = [o.affected_categories[0] for o in opps]
        assert "cleaning" in cats or "painting" in cats

    def test_category_gaps_no_gap(self):
        m = OpportunityMiner()
        opps = m.find_category_gaps(
            my_categories={"plumbing", "cleaning"},
            all_categories={"plumbing": 3, "cleaning": 2},
        )
        assert len(opps) == 0

    def test_geographic_gaps(self):
        m = OpportunityMiner()
        opps = m.find_geographic_gaps(
            presence_regions={"chennai"},
            target_regions=["chennai", "mumbai", "delhi"],
        )
        assert len(opps) == 2
        regions = [o.affected_categories or [o.title.split()[-1].lower()] for o in opps]

    def test_mine(self):
        m = OpportunityMiner()
        opps = m.mine(
            my_categories={"plumbing"},
            all_categories={"plumbing": 3, "cleaning": 2},
            category_prices={"plumbing": [100, 200, 300]},
            presence_regions={"chennai"},
            target_regions=["chennai", "mumbai"],
        )
        assert len(opps) > 0
        assert len(opps) <= 15

    def test_opportunity_fields(self):
        m = OpportunityMiner()
        opps = m.find_pricing_gaps({"plumbing": [100, 200, 300]})
        o = opps[0]
        assert hasattr(o, "opportunity_type")
        assert hasattr(o, "title")
        assert hasattr(o, "opportunity_score")
        assert hasattr(o, "description")
        assert hasattr(o, "recommended_action")
        assert hasattr(o, "affected_categories")


# ─── StrategicRecommendationGenerator Tests ───────────────────────────────


class TestStrategicRecommendationGenerator:
    def test_init(self):
        g = StrategicRecommendationGenerator()
        assert g is not None

    def test_growing_competitor(self):
        g = StrategicRecommendationGenerator()
        recs = g.generate(growth_direction="growing", growth_score=0.2)
        assert len(recs) >= 1
        assert recs[0].category == "growth_response"
        assert recs[0].impact_rating == "HIGH"

    def test_declining_competitor(self):
        g = StrategicRecommendationGenerator()
        recs = g.generate(growth_direction="declining", growth_score=-0.2)
        assert len(recs) >= 1
        assert recs[0].category == "growth_opportunity"

    def test_high_risk_triggers_mitigation(self):
        g = StrategicRecommendationGenerator()
        recs = g.generate(
            risk_signals=[{"threat_level": "HIGH", "risk_type": "price_war", "recommended_mitigation": "Lock contracts"}],
        )
        assert any(r.category == "risk_mitigation" for r in recs)

    def test_price_cut_response(self):
        g = StrategicRecommendationGenerator()
        recs = g.generate(pricing_trend=-0.3)
        assert any(r.category == "pricing_strategy" for r in recs)

    def test_premium_opportunity(self):
        g = StrategicRecommendationGenerator()
        recs = g.generate(pricing_trend=0.3)
        assert any(r.category == "pricing_strategy" for r in recs)

    def test_service_gap_response(self):
        g = StrategicRecommendationGenerator()
        recs = g.generate(service_gap=5)
        assert any(r.category == "service_expansion" for r in recs)

    def test_no_recommendations_for_stable(self):
        g = StrategicRecommendationGenerator()
        recs = g.generate(
            growth_direction="stable",
            growth_score=0.0,
            risk_signals=[],
            pricing_trend=0.0,
            service_gap=0,
        )
        assert len(recs) == 0

    def test_recommendations_limited_to_8(self):
        g = StrategicRecommendationGenerator()
        recs = g.generate(
            growth_direction="growing",
            growth_score=0.3,
            risk_signals=[
                {"threat_level": "HIGH", "risk_type": "price_war", "recommended_mitigation": "A"},
                {"threat_level": "HIGH", "risk_type": "expansion", "recommended_mitigation": "B"},
            ],
            pricing_trend=-0.3,
            service_gap=5,
        )
        assert len(recs) <= 8

    def test_sorted_by_confidence(self):
        g = StrategicRecommendationGenerator()
        recs = g.generate(
            growth_direction="growing",
            growth_score=0.3,
            risk_signals=[{"threat_level": "HIGH", "risk_type": "price_war", "recommended_mitigation": "A"}],
            pricing_trend=-0.3,
        )
        confidences = [r.confidence for r in recs]
        assert confidences == sorted(confidences, reverse=True)

    def test_rec_fields(self):
        g = StrategicRecommendationGenerator()
        recs = g.generate(growth_direction="growing", growth_score=0.2)
        r = recs[0]
        assert hasattr(r, "category")
        assert hasattr(r, "title")
        assert hasattr(r, "recommendation")
        assert hasattr(r, "impact_rating")
        assert hasattr(r, "confidence")
        assert hasattr(r, "rationale")
        assert hasattr(r, "counter_actions")
        assert len(r.counter_actions) > 0
