"""Market Scenario Simulation.

Projects outcomes from real data — pricing adjustments, competitor exits,
and category entry. Uses actual DB data for projections.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, TYPE_CHECKING

import structlog
from sqlalchemy import func, select

from app.database.models import (
    Competitor,
    CompetitorPricing,
    CompetitorService,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class ScenarioSimulator:
    """Projects competitive scenarios using real market data."""

    def available_scenarios(self) -> list[dict[str, Any]]:
        return [
            {"type": "competitor_price_cut", "name": "Competitor Price Cut", "description": "Simulate 10-30% price reduction by a competitor"},
            {"type": "new_competitor", "name": "New Competitor Entry", "description": "Simulate entry of a new competitor"},
            {"type": "category_expansion", "name": "Category Expansion", "description": "Simulate entering a new service category"},
            {"type": "market_decline", "name": "Market Decline", "description": "Simulate market demand decline"},
            {"type": "price_war", "name": "Price War", "description": "Simulate aggressive price cuts across market"},
        ]

    async def simulate(
        self, scenario: str, params: dict[str, Any] | None = None, session: AsyncSession | None = None
    ) -> dict[str, Any]:
        params = params or {}
        now = datetime.now(UTC)
        base = await self._get_market_snapshot(session) if session else self._default_snapshot()

        if scenario == "competitor_price_cut":
            return await self._competitor_price_cut(params, base, session)
        elif scenario == "new_competitor":
            return await self._new_competitor(params, base, session)
        elif scenario == "category_expansion":
            return await self._category_entry(params, base, session)
        elif scenario == "market_decline":
            return await self._market_decline(params, base, session)
        elif scenario == "price_war":
            return await self._price_war(params, base, session)
        else:
            return {
                "scenario": scenario,
                "error": f"Unknown scenario: {scenario}",
                "available": [s["type"] for s in self.available_scenarios()],
            }

    def _default_snapshot(self) -> dict[str, Any]:
        return {
            "competitors": 7,
            "total_services": 200,
            "categories": 15,
            "avg_service_price": 1500,
            "avg_pricing": 800,
            "min_price": 200,
            "max_price": 5000,
            "price_data_points": 100,
            "activity_30d": 50,
        }

    async def _get_market_snapshot(self, session: AsyncSession | None) -> dict[str, Any]:
        if not session:
            return self._default_snapshot()

        now = datetime.now(UTC)
        last_30 = now - timedelta(days=30)

        comp_count = (await session.execute(
            select(func.count()).select_from(Competitor).where(Competitor.enabled.is_(True))
        )).scalar() or 0

        svc_stmt = select(
            func.count().label("total"),
            func.count(func.distinct(CompetitorService.service_category)).label("categories"),
            func.avg(CompetitorService.starting_price).label("avg_price"),
        )
        svc = (await session.execute(svc_stmt)).one()

        price_stmt = select(
            func.avg(CompetitorPricing.base_price).label("avg"),
            func.min(CompetitorPricing.base_price).label("min_p"),
            func.max(CompetitorPricing.base_price).label("max_p"),
            func.count().label("cnt"),
        ).where(CompetitorPricing.base_price.isnot(None))
        price = (await session.execute(price_stmt)).one()

        from app.database.models import ChangeLog
        activity_stmt = select(func.count()).select_from(ChangeLog).where(
            ChangeLog.detected_at >= last_30
        )
        activity_30d = (await session.execute(activity_stmt)).scalar() or 0

        return {
            "competitors": comp_count,
            "total_services": svc.total or 0,
            "categories": svc.categories or 0,
            "avg_service_price": float(svc.avg_price) if svc.avg_price else 0,
            "avg_pricing": float(price.avg) if price.avg else 0,
            "min_price": float(price.min_p) if price.min_p else 0,
            "max_price": float(price.max_p) if price.max_p else 0,
            "price_data_points": price.cnt or 0,
            "activity_30d": activity_30d,
        }

    async def _competitor_price_cut(
        self, params: dict[str, Any], base: dict[str, Any], session: AsyncSession | None
    ) -> dict[str, Any]:
        cut_pct = params.get("cut_percentage", 0.15)
        cut_pct_display = cut_pct * 100 if cut_pct <= 1 else cut_pct
        new_avg = base["avg_pricing"] * (1 - cut_pct)
        elasticity = 1.5
        volume_change = cut_pct_display * elasticity
        revenue_impact = ((1 - cut_pct) * (1 + volume_change / 100) - 1) * 100

        return {
            "scenario": "competitor_price_cut",
            "business_impact": {
                "revenue_impact_pct": round(revenue_impact, 1),
                "market_share_change_pct": round(-volume_change * 0.3, 1),
                "margin_pressure": "high" if cut_pct > 0.2 else "medium",
                "affected_categories": base.get("categories", 15),
            },
            "risk_analysis": {
                "overall_risk": "high" if cut_pct > 0.2 else "medium",
                "risk_factors": [
                    f"Competitor cuts prices by {cut_pct_display:.0f}%",
                    f"Price drops from ₹{base['avg_pricing']:.0f} to ₹{new_avg:.0f}",
                    f"Need {volume_change:.0f}% volume increase to break even",
                ],
                "time_sensitivity": "respond within 7 days",
            },
            "recommended_strategy": {
                "immediate": "Match price in high-overlap categories only",
                "short_term": "Bundle services to protect per-transaction revenue",
                "long_term": "Differentiate on quality and reliability to reduce price sensitivity",
            },
        }

    async def _price_war(
        self, params: dict[str, Any], base: dict[str, Any], session: AsyncSession | None
    ) -> dict[str, Any]:
        reduction = params.get("reduction_pct", 20)
        new_avg = base["avg_pricing"] * (1 - reduction / 100)
        elasticity = params.get("elasticity", 1.5)
        volume_change = reduction * elasticity
        revenue_impact = ((1 - reduction / 100) * (1 + volume_change / 100) - 1) * 100

        return {
            "scenario": "price_war",
            "business_impact": {
                "revenue_impact_pct": round(revenue_impact, 1),
                "market_share_change_pct": round(-volume_change * 0.2, 1),
                "margin_pressure": "very_high",
                "affected_categories": base.get("categories", 15),
            },
            "risk_analysis": {
                "overall_risk": "high",
                "risk_factors": [
                    f"Market-wide {reduction}% price reduction",
                    f"Margins compressed from avg ₹{base['avg_pricing']:.0f} to ₹{new_avg:.0f}",
                    f"Need {reduction / (1 - reduction / 100) * 100:.0f}% volume to break even",
                    f"Price floor: ₹{base['min_price']:.0f} → ₹{base['min_price'] * (1 - reduction / 100):.0f}",
                ],
                "time_sensitivity": "critical — respond within 48 hours",
            },
            "recommended_strategy": {
                "immediate": "Do NOT match full cut — protect margins",
                "short_term": "Bundle services and lock in annual contracts",
                "long_term": "Build brand loyalty to reduce price sensitivity",
            },
        }

    async def _new_competitor(
        self, params: dict[str, Any], base: dict[str, Any], session: AsyncSession | None
    ) -> dict[str, Any]:
        new_services = params.get("service_count", 20)
        total_services = base["total_services"] + new_services
        market_share_loss = (new_services / total_services) * 100

        return {
            "scenario": "new_competitor",
            "business_impact": {
                "market_share_loss_pct": round(market_share_loss, 1),
                "total_services_after": total_services,
                "new_competitor_share_pct": round((new_services / total_services) * 100, 1),
                "category_coverage": min(new_services // 3, base.get("categories", 15)),
            },
            "risk_analysis": {
                "overall_risk": "medium",
                "risk_factors": [
                    f"~{market_share_loss:.1f}% market share erosion from {new_services} new listings",
                    f"New entrant covers ~{min(new_services // 3, base.get('categories', 15))} categories",
                    "Price pressure likely in overlapping categories",
                ],
                "time_sensitivity": "monitor for 30 days before responding",
            },
            "recommended_strategy": {
                "immediate": "Lock in existing customers with loyalty incentives",
                "short_term": "Accelerate differentiation in strongest categories",
                "long_term": "Monitor new competitor pricing in first 30 days",
            },
        }

    async def _category_entry(
        self, params: dict[str, Any], base: dict[str, Any], session: AsyncSession | None
    ) -> dict[str, Any]:
        category = params.get("category", "new_category")
        services = params.get("services", 5)

        return {
            "scenario": "category_expansion",
            "business_impact": {
                "new_services": services,
                "total_services_after": base["total_services"] + services,
                "category_count_after": base.get("categories", 15) + 1,
                "estimated_category_share_pct": round(
                    (services / max(base["total_services"] + services, 1)) * 100, 1
                ),
            },
            "risk_analysis": {
                "overall_risk": "low",
                "risk_factors": [
                    f"New category '{category}' with {services} initial listings",
                    "Incumbent advantage in established categories",
                ],
                "time_sensitivity": "standard planning cycle",
            },
            "recommended_strategy": {
                "immediate": f"Research pricing in {category} before entry",
                "short_term": "Start with highest-demand subcategories",
                "long_term": "Scale based on initial traction data",
            },
        }

    async def _market_decline(
        self, params: dict[str, Any], base: dict[str, Any], session: AsyncSession | None
    ) -> dict[str, Any]:
        decline_pct = params.get("decline_pct", 20)
        surviving = max(1, base["competitors"] - max(1, int(base["competitors"] * decline_pct / 200)))
        survivor_share = 100 / max(surviving, 1)

        return {
            "scenario": "market_decline",
            "business_impact": {
                "demand_decline_pct": decline_pct,
                "surviving_competitors": surviving,
                "survivor_share_pct": round(survivor_share, 1),
                "services_affected": int(base["total_services"] * decline_pct / 100),
            },
            "risk_analysis": {
                "overall_risk": "high" if decline_pct > 20 else "medium",
                "risk_factors": [
                    f"{decline_pct}% demand reduction across market",
                    f"Estimated {int(base['total_services'] * decline_pct / 100)} services at risk",
                    f"{base['competitors'] - surviving} competitors may exit",
                ],
                "time_sensitivity": "begin consolidation immediately",
            },
            "recommended_strategy": {
                "immediate": "Consolidate underperforming service categories",
                "short_term": "Focus on highest-margin offerings",
                "long_term": "Diversify into adjacent service areas",
            },
        }


scenario_simulator = ScenarioSimulator()
