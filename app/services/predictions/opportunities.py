"""Opportunity Detection.

Detects business opportunities from real market data: pricing gaps,
service coverage gaps, and competitive whitespace analysis.
"""

from __future__ import annotations

from datetime import UTC, datetime
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


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))


class OpportunityDetector:
    """Detects business opportunities from competitive intelligence data."""

    async def detect(self, session: AsyncSession) -> list[dict[str, Any]]:
        pricing_gaps = await self._detect_pricing_gaps(session)
        service_gaps = await self._detect_service_gaps(session)
        category_whitespace = await self._detect_category_whitespace(session)
        pricing_trend_opps = await self._detect_pricing_trend_opportunities(session)

        # Merge and cap per-type so the top 15 has variety
        all_opps = []
        for group in (pricing_gaps, service_gaps, category_whitespace, pricing_trend_opps):
            all_opps.extend(group[:5])

        all_opps.sort(key=lambda x: x["opportunity_score"], reverse=True)
        return all_opps[:15]

    async def _detect_pricing_gaps(self, session: AsyncSession) -> list[dict[str, Any]]:
        """Detect pricing opportunities from service and pricing data."""
        opportunities: list[dict[str, Any]] = []

        # 1. Category-based gaps (if categories exist)
        stmt = (
            select(
                CompetitorPricing.category,
                CompetitorPricing.competitor_id,
                func.avg(CompetitorPricing.base_price).label("avg_price"),
                func.count(CompetitorPricing.id).label("count"),
            )
            .where(CompetitorPricing.base_price.isnot(None))
            .where(CompetitorPricing.category.isnot(None))
            .group_by(CompetitorPricing.category, CompetitorPricing.competitor_id)
        )
        rows = (await session.execute(stmt)).all()
        cat_data: dict[str, list[tuple[int, float, int]]] = {}
        for r in rows:
            cat_data.setdefault(r[0], []).append((r[1], float(r[2]), r[3]))

        for cat, entries in cat_data.items():
            if len(entries) < 2:
                continue
            prices = [e[1] for e in entries]
            avg = sum(prices) / len(prices)
            min_p, max_p = min(prices), max(prices)
            spread = max_p - min_p
            if avg > 0 and spread > avg * 0.15:
                high_comps = [e[0] for e in entries if e[1] > avg * 1.2]
                score = _clamp(spread / (avg * 2)) * 100
                opportunities.append({
                    "opportunity_type": "pricing_gap",
                    "title": f"Price gap in {cat} — {spread/avg*100:.0f}% spread",
                    "description": f"Prices range ₹{min_p:.0f}–₹{max_p:.0f} (avg ₹{avg:.0f}) across {len(entries)} competitors",
                    "opportunity_score": round(score, 1),
                    "priority": "high" if score > 60 else "medium",
                    "recommended_action": f"Position between ₹{min_p:.0f} and ₹{avg:.0f} to undercut premium players",
                    "affected_competitors": high_comps,
                    "detected_at": datetime.now(UTC).isoformat(),
                })

        # 2. Intra-competitor outliers: services priced far above competitor's median
        stmt2 = (
            select(
                CompetitorService.competitor_id,
                Competitor.name,
                CompetitorService.service_name,
                CompetitorService.starting_price,
            )
            .join(Competitor, CompetitorService.competitor_id == Competitor.id)
            .where(CompetitorService.starting_price.isnot(None))
            .where(CompetitorService.starting_price > 10)
        )
        svc_rows = (await session.execute(stmt2)).all()

        comp_services: dict[int, list[tuple[str, str, float]]] = {}
        for r in svc_rows:
            comp_services.setdefault(r.competitor_id, []).append((r.name, r.service_name, float(r.starting_price)))

        for comp_id, svcs in comp_services.items():
            if len(svcs) < 3:
                continue
            prices = sorted(s[2] for s in svcs)
            median = prices[len(prices) // 2]
            if median <= 0:
                continue

            for comp_name, svc_name, price in svcs:
                ratio = price / median
                # Overpriced service — opportunity to undercut
                if ratio > 1.8 and price > median + 30:
                    discount_pct = (1 - median / price) * 100
                    # Higher ratio = bigger undercut opportunity = higher score
                    score = _clamp((ratio - 1.5) / 1.5) * 100
                    opportunities.append({
                        "opportunity_type": "pricing_gap",
                        "title": f"Undercut {comp_name} on {svc_name[:40]}",
                        "description": f"{comp_name} charges ₹{price:.0f} vs their own median ₹{median:.0f} ({ratio:.1f}x). You could price at ₹{median:.0f}–₹{median*1.2:.0f}",
                        "opportunity_score": round(score, 1),
                        "priority": "high" if score > 40 else "medium",
                        "recommended_action": f"Offer {svc_name[:40]} at ₹{median:.0f}–₹{median*1.2:.0f} to undercut {comp_name}'s {discount_pct:.0f}% premium",
                        "affected_competitors": [comp_id],
                        "detected_at": datetime.now(UTC).isoformat(),
                    })

        # 3. Underpriced services — potential loss leaders or entry points
        for comp_id, svcs in comp_services.items():
            if len(svcs) < 3:
                continue
            prices = sorted(s[2] for s in svcs)
            median = prices[len(prices) // 2]
            if median <= 0:
                continue

            for comp_name, svc_name, price in svcs:
                ratio = price / median
                if ratio < 0.5 and price < median - 20:
                    # Lower ratio = bigger premium opportunity = higher score
                    score = _clamp((0.5 - ratio) / 0.5) * 90
                    opportunities.append({
                        "opportunity_type": "pricing_gap",
                        "title": f"Premium positioning vs {comp_name} on {svc_name[:40]}",
                        "description": f"{comp_name} sells {svc_name[:40]} for only ₹{price:.0f} (their median is ₹{median:.0f}). Premium/quality positioning possible at ₹{median:.0f}+",
                        "opportunity_score": round(score, 1),
                        "priority": "medium",
                        "recommended_action": f"Offer premium version of {svc_name[:40]} at ₹{median:.0f}–₹{median*1.5:.0f} while {comp_name} undercuts at ₹{price:.0f}",
                        "affected_competitors": [comp_id],
                        "detected_at": datetime.now(UTC).isoformat(),
                    })

        # 4. Cross-competitor price tier spread
        all_svcs = []
        for comp_id, svcs in comp_services.items():
            for comp_name, svc_name, price in svcs:
                all_svcs.append((comp_id, comp_name, svc_name, price))

        if len(all_svcs) >= 5:
            all_prices = sorted(s[3] for s in all_svcs)
            # Split into budget / mid / premium tiers
            p25 = all_prices[len(all_prices) // 4]
            p75 = all_prices[3 * len(all_prices) // 4]
            budget = [(c_id, c_name, s_name, p) for c_id, c_name, s_name, p in all_svcs if p <= p25 and p > 50]
            premium = [(c_id, c_name, s_name, p) for c_id, c_name, s_name, p in all_svcs if p >= p75]

            if budget and premium:
                avg_budget = sum(s[3] for s in budget) / len(budget)
                avg_premium = sum(s[3] for s in premium) / len(premium)
                spread = avg_premium - avg_budget
                if avg_budget > 0:
                    spread_pct = spread / avg_budget * 100
                    score = _clamp(spread_pct / 300) * 100
                    opportunities.append({
                        "opportunity_type": "pricing_gap",
                        "title": f"Market pricing tier spread — {spread_pct:.0f}% gap",
                        "description": f"Budget services avg ₹{avg_budget:.0f} vs premium avg ₹{avg_premium:.0f} across {len(all_svcs)} listings from {len(comp_services)} competitors",
                        "opportunity_score": round(score, 1),
                        "priority": "high" if score > 60 else "medium",
                        "recommended_action": f"Position mid-tier services at ₹{avg_budget*1.5:.0f}–₹{avg_premium*0.7:.0f} to capture the gap",
                        "affected_competitors": [],
                        "detected_at": datetime.now(UTC).isoformat(),
                    })

        return opportunities

    async def _detect_service_gaps(self, session: AsyncSession) -> list[dict[str, Any]]:
        """Find service categories with few competitors — whitespace to enter."""
        stmt = (
            select(
                CompetitorService.service_category,
                func.count(func.distinct(CompetitorService.competitor_id)).label("competitors"),
                func.count(CompetitorService.id).label("total_listings"),
                func.avg(CompetitorService.starting_price).label("avg_price"),
            )
            .where(CompetitorService.service_category.isnot(None))
            .group_by(CompetitorService.service_category)
        )
        rows = (await session.execute(stmt)).all()

        if not rows:
            return []

        avg_competitors = sum(r.competitors for r in rows) / len(rows)

        opportunities = []
        for row in rows:
            # Below average or low absolute count (≤2 competitors)
            if row.competitors <= max(2, avg_competitors * 0.7) and row.total_listings >= 1:
                gap = max(avg_competitors - row.competitors, 1)
                score = _clamp(gap / max(avg_competitors, 1)) * 90
                # Boost score for very low competition
                if row.competitors <= 1:
                    score = max(score, 50)

                opportunities.append({
                    "opportunity_type": "underserved_category",
                    "title": f"Whitespace: {row.service_category}",
                    "description": f"Only {row.competitors} competitor(s) serve this category (avg: {avg_competitors:.0f}), with {row.total_listings} total listings",
                    "opportunity_score": round(score, 1),
                    "priority": "high" if score > 50 else "medium",
                    "recommended_action": f"Enter {row.service_category} market — low competition, avg price ₹{float(row.avg_price):.0f}" if row.avg_price else f"Enter {row.service_category} market — low competition",
                    "affected_competitors": [],
                    "detected_at": datetime.now(UTC).isoformat(),
                })

        return opportunities

    async def _detect_category_whitespace(self, session: AsyncSession) -> list[dict[str, Any]]:
        """Find high-demand categories where a single competitor dominates."""
        stmt = (
            select(
                CompetitorService.service_category,
                CompetitorService.competitor_id,
                func.count(CompetitorService.id).label("cnt"),
            )
            .where(CompetitorService.service_category.isnot(None))
            .group_by(CompetitorService.service_category, CompetitorService.competitor_id)
        )
        rows = (await session.execute(stmt)).all()

        cat_comp: dict[str, dict[int, int]] = {}
        for r in rows:
            cat_comp.setdefault(r[0], {})[r[1]] = r[2]

        opportunities = []
        for cat, comps in cat_comp.items():
            total = sum(comps.values())
            max_count = max(comps.values())
            dominance = max_count / max(total, 1)

            if dominance >= 0.5:
                leader_id = max(comps, key=comps.get)
                score = dominance * 80
                # Single-competitor categories are strong entry signals
                if len(comps) == 1:
                    score = max(score, 60)
                opportunities.append({
                    "opportunity_type": "dominance_gap",
                    "title": f"Compete in {cat} — leader has {dominance:.0%} share",
                    "description": f"One competitor holds {max_count}/{total} listings in {cat}",
                    "opportunity_score": round(score, 1),
                    "priority": "high" if score > 50 else "medium",
                    "recommended_action": f"Challenge the dominant player in {cat} by entering with differentiated offerings",
                    "affected_competitors": [leader_id],
                    "detected_at": datetime.now(UTC).isoformat(),
                })

        return opportunities

    async def _detect_pricing_trend_opportunities(self, session: AsyncSession) -> list[dict[str, Any]]:
        """Find categories where prices are dropping — room for premium positioning."""
        from datetime import timedelta

        now = datetime.now(UTC)
        last_14 = now - timedelta(days=14)
        prev_14 = now - timedelta(days=28)

        # Recent prices
        recent_stmt = (
            select(
                CompetitorPricing.category,
                func.avg(CompetitorPricing.base_price).label("avg_recent"),
            )
            .where(CompetitorPricing.base_price.isnot(None))
            .where(CompetitorPricing.category.isnot(None))
            .where(CompetitorPricing.collected_at >= last_14)
            .group_by(CompetitorPricing.category)
            .having(func.count() >= 3)
        )
        recent = {r[0]: float(r[1]) for r in (await session.execute(recent_stmt)).all()}

        # Previous prices
        prev_stmt = (
            select(
                CompetitorPricing.category,
                func.avg(CompetitorPricing.base_price).label("avg_prev"),
            )
            .where(CompetitorPricing.base_price.isnot(None))
            .where(CompetitorPricing.category.isnot(None))
            .where(CompetitorPricing.collected_at >= prev_14)
            .where(CompetitorPricing.collected_at < last_14)
            .group_by(CompetitorPricing.category)
            .having(func.count() >= 3)
        )
        prev = {r[0]: float(r[1]) for r in (await session.execute(prev_stmt)).all()}

        opportunities = []
        for cat in recent:
            if cat not in prev or prev[cat] == 0:
                continue
            change = (recent[cat] - prev[cat]) / prev[cat]
            if change < -0.1:
                # Prices dropping — opportunity for premium positioning
                score = min(90, abs(change) * 200)
                opportunities.append({
                    "opportunity_type": "premium_positioning",
                    "title": f"Premium opportunity in {cat} — prices dropping {abs(change)*100:.0f}%",
                    "description": f"Avg price fell from ₹{prev[cat]:.0f} to ₹{recent[cat]:.0f} in 14 days",
                    "opportunity_score": round(score, 1),
                    "priority": "medium",
                    "recommended_action": f"Position as premium option in {cat} while competitors race to bottom",
                    "affected_competitors": [],
                    "detected_at": now.isoformat(),
                })

        return opportunities


opportunity_detector = OpportunityDetector()
