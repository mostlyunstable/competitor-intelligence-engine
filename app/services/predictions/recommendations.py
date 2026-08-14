"""Strategic Recommendation Engine.

Generates actionable recommendations derived from real competitive data:
forecast trends, pricing analysis, service gaps, and growth signals.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, TYPE_CHECKING

import structlog
from sqlalchemy import func, select

from app.database.models import (
    CompetitorPricing,
    CompetitorService,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class RecommendationEngine:
    """Generates strategic recommendations from intelligence data."""

    async def generate(
        self, competitor_id: int, session: AsyncSession
    ) -> list[dict[str, Any]]:
        recs = []

        recs.extend(await self._pricing_strategy(competitor_id, session))
        recs.extend(await self._service_expansion(competitor_id, session))
        recs.extend(await self._competitive_position(competitor_id, session))
        recs.extend(await self._growth_momentum(competitor_id, session))

        recs.sort(key=lambda x: x.get("confidence_score", 0), reverse=True)
        return recs[:8]

    async def generate_all(self, session: AsyncSession) -> list[dict[str, Any]]:
        """Generate recommendations for all enabled competitors."""
        from app.database.models import Competitor

        comps = (await session.execute(
            select(Competitor).where(Competitor.enabled.is_(True))
        )).scalars().all()

        all_recs: list[dict[str, Any]] = []
        for comp in comps:
            try:
                recs = await self.generate(comp.id, session)
                for r in recs:
                    r["competitor_id"] = comp.id
                    r["competitor_name"] = comp.name
                all_recs.extend(recs)
            except Exception:
                logger.warning("recommendation_failed", competitor_id=comp.id)
                continue

        all_recs.sort(key=lambda x: x.get("confidence_score", 0), reverse=True)
        return all_recs

    async def _pricing_strategy(
        self, cid: int, session: AsyncSession
    ) -> list[dict[str, Any]]:
        """Recommend pricing actions based on actual price data analysis."""
        now = datetime.now(UTC)
        last_14 = now - timedelta(days=14)
        prev_14 = now - timedelta(days=28)

        # Current pricing stats
        stmt = (
            select(
                func.avg(CompetitorPricing.base_price).label("avg"),
                func.min(CompetitorPricing.base_price).label("min_p"),
                func.max(CompetitorPricing.base_price).label("max_p"),
                func.count(CompetitorPricing.id).label("cnt"),
            )
            .where(CompetitorPricing.competitor_id == cid)
            .where(CompetitorPricing.base_price.isnot(None))
        )
        row = (await session.execute(stmt)).one()
        if not row or row.cnt == 0:
            return []

        avg, min_p, max_p, cnt = float(row.avg), float(row.min_p), float(row.max_p), row.cnt
        recs = []
        now_iso = now.isoformat()

        # Price trend
        recent_stmt = (
            select(func.avg(CompetitorPricing.base_price))
            .where(CompetitorPricing.competitor_id == cid)
            .where(CompetitorPricing.base_price.isnot(None))
            .where(CompetitorPricing.collected_at >= last_14)
        )
        recent_avg = (await session.execute(recent_stmt)).scalar()

        prev_stmt = (
            select(func.avg(CompetitorPricing.base_price))
            .where(CompetitorPricing.competitor_id == cid)
            .where(CompetitorPricing.base_price.isnot(None))
            .where(CompetitorPricing.collected_at >= prev_14)
            .where(CompetitorPricing.collected_at < last_14)
        )
        prev_avg = (await session.execute(prev_stmt)).scalar()

        if recent_avg and prev_avg and prev_avg > 0:
            trend = (float(recent_avg) - float(prev_avg)) / float(prev_avg)
            if trend < -0.15:
                recs.append({
                    "category": "pricing",
                    "title": "Prices declining — defend margins",
                    "recommendation": f"Average price dropped {abs(trend)*100:.0f}% over 14 days (₹{float(prev_avg):.0f} → ₹{float(recent_avg):.0f}). Consider bundling or value-adds to maintain revenue.",
                    "why": f"Sustained price decline of {abs(trend)*100:.0f}% signals competitive pressure or commodity positioning.",
                    "expected_benefit": "Stabilize revenue per transaction",
                    "risk_level": "medium",
                    "confidence_score": 0.85,
                    "priority": "high",
                    "generated_at": now_iso,
                    "applied": False,
                })
            elif trend > 0.2:
                recs.append({
                    "category": "pricing",
                    "title": "Pricing power increasing",
                    "recommendation": f"Prices rose {trend*100:.0f}% over 14 days. Market accepts higher prices — consider premium tier.",
                    "why": "Upward price trend indicates strong demand or reduced competition.",
                    "expected_benefit": "15-25% revenue uplift from premium positioning",
                    "risk_level": "low",
                    "confidence_score": 0.8,
                    "priority": "medium",
                    "generated_at": now_iso,
                    "applied": False,
                })

        # Price spread analysis
        if max_p > avg * 2.5 and cnt >= 5:
            recs.append({
                "category": "pricing",
                "title": "Tiered pricing opportunity",
                "recommendation": f"Price range ₹{min_p:.0f}–₹{max_p:.0f} (spread {((max_p-min_p)/avg*100):.0f}% of avg) indicates untapped segmentation.",
                "why": "Wide price spread suggests different customer segments with different willingness to pay.",
                "expected_benefit": "Capture both budget and premium segments",
                "risk_level": "low",
                "confidence_score": 0.75,
                "priority": "medium",
                "generated_at": now_iso,
                "applied": False,
            })

        return recs

    async def _service_expansion(
        self, cid: int, session: AsyncSession
    ) -> list[dict[str, Any]]:
        """Recommend service expansion based on category analysis."""
        now = datetime.now(UTC)
        now_iso = now.isoformat()

        # This competitor's categories
        my_stmt = (
            select(CompetitorService.service_category, func.count().label("cnt"))
            .where(CompetitorService.competitor_id == cid)
            .where(CompetitorService.service_category.isnot(None))
            .group_by(CompetitorService.service_category)
        )
        my_cats = {r[0]: r[1] for r in (await session.execute(my_stmt)).all()}

        # All categories across all competitors
        all_stmt = (
            select(
                CompetitorService.service_category,
                func.count(func.distinct(CompetitorService.competitor_id)).label("competitors"),
                func.count().label("total"),
            )
            .where(CompetitorService.service_category.isnot(None))
            .group_by(CompetitorService.service_category)
        )
        all_cats = {r[0]: (r[1], r[2]) for r in (await session.execute(all_stmt)).all()}

        recs = []

        # Categories we're missing that others have
        missing = []
        for cat, (comp_count, total) in all_cats.items():
            if cat not in my_cats and comp_count >= 2:
                missing.append((cat, comp_count, total))

        if missing:
            missing.sort(key=lambda x: x[1], reverse=True)
            top_missing = missing[:3]
            cat_list = ", ".join(f"{c[0]} ({c[1]} competitors)" for c in top_missing)
            recs.append({
                "category": "service_expansion",
                "title": f"Add {len(missing)} missing service categories",
                "recommendation": f"Missing categories with competition: {cat_list}. Entering these closes the gap with market.",
                "why": f"{len(missing)} categories have competitor presence but zero listings here.",
                "expected_benefit": f"Access to {sum(c[2] for c in top_missing)} additional market listings",
                "risk_level": "low",
                "confidence_score": 0.82,
                "priority": "high",
                "generated_at": now_iso,
                "applied": False,
            })

        # Categories where we're underrepresented
        avg_per_cat = sum(my_cats.values()) / max(len(my_cats), 1)
        weak_cats = [(cat, cnt) for cat, cnt in my_cats.items() if cnt < avg_per_cat * 0.5 and cnt < 3]
        if weak_cats:
            cat_name = weak_cats[0][0]
            recs.append({
                "category": "service_expansion",
                "title": f"Strengthen {cat_name} presence",
                "recommendation": f"Only {weak_cats[0][1]} listing(s) in {cat_name} vs your avg of {avg_per_cat:.0f} per category.",
                "why": "Underrepresented categories leave room for competitors to capture market share.",
                "expected_benefit": "Defend existing market position",
                "risk_level": "medium",
                "confidence_score": 0.7,
                "priority": "medium",
                "generated_at": now_iso,
                "applied": False,
            })

        return recs

    async def _competitive_position(
        self, cid: int, session: AsyncSession
    ) -> list[dict[str, Any]]:
        """Recommend positioning based on relative competitive strength."""
        now = datetime.now(UTC)
        now_iso = now.isoformat()

        # My total services
        my_stmt = select(func.count()).select_from(CompetitorService).where(
            CompetitorService.competitor_id == cid
        )
        my_count = (await session.execute(my_stmt)).scalar() or 0

        # Market stats
        all_stmt = (
            select(CompetitorService.competitor_id, func.count().label("cnt"))
            .group_by(CompetitorService.competitor_id)
        )
        all_counts = [r[1] for r in (await session.execute(all_stmt)).all()]

        if not all_counts:
            return []

        avg = sum(all_counts) / len(all_counts)
        market_max = max(all_counts)
        recs = []

        if my_count < avg * 0.7:
            gap = avg - my_count
            recs.append({
                "category": "competitive_positioning",
                "title": f"Close the service gap — add ~{int(gap)} services",
                "recommendation": f"Currently {my_count} services vs market avg of {avg:.0f} and leader at {market_max}. Gap of {int(gap)} services.",
                "why": f"Service count at {my_count/max(avg,1)*100:.0f}% of market average limits competitive reach.",
                "expected_benefit": f"Match market average and access {int(gap)} additional service touchpoints",
                "risk_level": "medium",
                "confidence_score": 0.88,
                "priority": "high",
                "generated_at": now_iso,
                "applied": False,
            })
        elif my_count >= market_max * 0.9:
            recs.append({
                "category": "competitive_positioning",
                "title": "Market leader position — defend and differentiate",
                "recommendation": f"With {my_count} services (market max: {market_max}), focus on quality and differentiation rather than volume.",
                "why": "Near market leadership means growth comes from depth, not breadth.",
                "expected_benefit": "Strengthen market leadership through quality differentiation",
                "risk_level": "low",
                "confidence_score": 0.78,
                "priority": "medium",
                "generated_at": now_iso,
                "applied": False,
            })

        return recs

    async def generate_executive_briefing(
        self, session: AsyncSession
    ) -> dict[str, Any]:
        """Generate an LLM-narrated executive briefing from current recommendations."""
        recs = await self.generate_all(session)
        if not recs:
            return {"briefing": "No recommendations available. Run data collection first.", "recs_count": 0}

        # Build context for LLM
        rec_lines = []
        for r in recs[:10]:
            comp = r.get("competitor_name", "Unknown")
            rec_lines.append(
                f"- [{r.get('category', 'general')}] **{r.get('title', '')}** "
                f"(competitor: {comp}, priority: {r.get('priority', 'medium')}, "
                f"confidence: {r.get('confidence_score', 0):.0%})\n"
                f"  Recommendation: {r.get('recommendation', '')}\n"
                f"  Why: {r.get('why', '')}\n"
                f"  Expected benefit: {r.get('expected_benefit', '')}"
            )

        recs_text = "\n\n".join(rec_lines)

        provider = self._get_provider()
        if not provider:
            # Fallback: return structured text without LLM
            briefing = f"## Executive Briefing\n\n{len(recs)} strategic recommendations generated.\n\n" + recs_text
            return {"briefing": briefing, "recs_count": len(recs), "llm_used": False}

        system_prompt = (
            "You are a senior strategic advisor preparing an executive briefing memo. "
            "Convert the raw recommendation data into a concise, actionable executive summary. "
            "Use markdown formatting: headers, bold for key points, bullet lists for actions. "
            "Keep it under 500 words. Focus on the top 3-5 most critical actions."
        )

        user_prompt = (
            f"Here are the latest strategic recommendations from our competitive intelligence system:\n\n"
            f"{recs_text}\n\n"
            "Please synthesize this into an executive briefing memo with:\n"
            "1. **Critical Actions** — the 3-5 most urgent items\n"
            "2. **Strategic Themes** — patterns across recommendations\n"
            "3. **Risk Summary** — top threats to watch\n"
            "4. **Next Steps** — concrete immediate actions"
        )

        try:
            response = await provider._client.post(
                "/v1/responses",
                json={
                    "model": provider.model_name,
                    "input": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.3,
                    "max_output_tokens": 1024,
                },
            )

            if response.status_code != 200:
                logger.warning("llm_briefing_failed", status=response.status_code)
                return {"briefing": recs_text, "recs_count": len(recs), "llm_used": False}

            data = response.json()
            content = ""
            for output_item in data.get("output", []):
                if output_item.get("type") == "message":
                    for content_item in output_item.get("content", []):
                        if content_item.get("type") == "output_text":
                            content = content_item.get("text", "")
                            break

            if content:
                return {"briefing": content, "recs_count": len(recs), "llm_used": True}

        except Exception as e:
            logger.warning("llm_briefing_error", error=str(e))

        return {"briefing": recs_text, "recs_count": len(recs), "llm_used": False}

    def _get_provider(self):
        try:
            from app.ai.infrastructure.providers.openai_provider import OpenAIProvider
            return OpenAIProvider()
        except Exception:
            return None

    async def _growth_momentum(
        self, cid: int, session: AsyncSession
    ) -> list[dict[str, Any]]:
        """Recommend actions based on activity momentum signals."""
        from app.database.models import ChangeLog

        now = datetime.now(UTC)
        now_iso = now.isoformat()
        last_7 = now - timedelta(days=7)
        prev_7 = now - timedelta(days=14)

        # Recent changes
        recent_stmt = select(func.count()).select_from(ChangeLog).where(
            ChangeLog.competitor_id == cid,
            ChangeLog.detected_at >= last_7,
        )
        recent = (await session.execute(recent_stmt)).scalar() or 0

        prev_stmt = select(func.count()).select_from(ChangeLog).where(
            ChangeLog.competitor_id == cid,
            ChangeLog.detected_at >= prev_7,
            ChangeLog.detected_at < last_7,
        )
        previous = (await session.execute(prev_stmt)).scalar() or 0

        recs = []

        if previous > 0:
            momentum = (recent - previous) / previous
            if momentum > 0.5:
                recs.append({
                    "category": "growth_response",
                    "title": "Competitor activity surging — respond",
                    "recommendation": f"Change activity up {momentum*100:.0f}% week-over-week ({previous} → {recent}). Accelerate your own innovation cycle.",
                    "why": "Rapid increase in competitor changes signals aggressive expansion or product launches.",
                    "expected_benefit": "Maintain competitive parity during growth phase",
                    "risk_level": "high",
                    "confidence_score": 0.82,
                    "priority": "high",
                    "generated_at": now_iso,
                    "applied": False,
                })
            elif momentum < -0.5:
                recs.append({
                    "category": "growth_opportunity",
                    "title": "Competitor activity declining — capitalize",
                    "recommendation": f"Change activity dropped {abs(momentum)*100:.0f}% ({previous} → {recent}). Window to gain share.",
                    "why": "Declining competitor activity may indicate resource constraints or strategic pivot.",
                    "expected_benefit": "Capture market share during competitor slowdown",
                    "risk_level": "low",
                    "confidence_score": 0.75,
                    "priority": "medium",
                    "generated_at": now_iso,
                    "applied": False,
                })

        return recs


recommendation_engine = RecommendationEngine()
