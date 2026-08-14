"""Advanced Competitor Scoring: 10-dimension composite intelligence score."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, TYPE_CHECKING

import structlog
from sqlalchemy import func, select

from app.services.predictions.analytics import clamp

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class AdvancedScorer:
    """Computes a 10-dimension composite intelligence score."""

    WEIGHTS = {
        "market_presence": 0.12,
        "growth_potential": 0.12,
        "innovation_score": 0.10,
        "pricing_competitiveness": 0.10,
        "regional_strength": 0.10,
        "digital_presence": 0.10,
        "service_diversity": 0.10,
        "customer_reach": 0.08,
        "technology_adoption": 0.08,
        "content_authority": 0.10,
    }

    async def score_all(self, session: AsyncSession) -> list[dict[str, Any]]:
        from app.database.models import (
            Competitor, CompetitorService, CompetitorPricing,
            CompetitorContent, CompetitorSocial, CompetitorSource, ChangeLog,
        )

        stmt = select(Competitor).where(Competitor.enabled.is_(True))
        competitors = (await session.execute(stmt)).scalars().all()
        comp_ids = [c.id for c in competitors]
        comp_names = {c.id: c.name for c in competitors}

        if not comp_ids:
            return []

        # Batch queries
        svc = await self._batch_count(session, CompetitorService, comp_ids)
        prc = await self._batch_count(session, CompetitorPricing, comp_ids)
        cnt = await self._batch_count(session, CompetitorContent, comp_ids)
        soc = await self._batch_count(session, CompetitorSocial, comp_ids)
        src = await self._batch_count(session, CompetitorSource, comp_ids)

        since = datetime.now(UTC) - timedelta(days=30)
        chg_stmt = (
            select(ChangeLog.competitor_id, func.count().label("cnt"))
            .where(ChangeLog.competitor_id.in_(comp_ids))
            .where(ChangeLog.detected_at >= since)
            .group_by(ChangeLog.competitor_id)
        )
        chg = {r[0]: r[1] for r in (await session.execute(chg_stmt)).all()}

        # Pricing stats per competitor
        prc_stats_stmt = (
            select(
                CompetitorPricing.competitor_id,
                func.avg(CompetitorPricing.base_price).label("avg_p"),
                func.count(CompetitorPricing.id).label("cnt"),
            )
            .where(CompetitorPricing.competitor_id.in_(comp_ids))
            .where(CompetitorPricing.base_price.isnot(None))
            .group_by(CompetitorPricing.competitor_id)
        )
        prc_stats = {r[0]: r for r in (await session.execute(prc_stats_stmt)).all()}

        # Global averages
        all_prices_stmt = select(func.avg(CompetitorPricing.base_price)).where(
            CompetitorPricing.base_price.isnot(None)
        )
        global_avg_price = float((await session.execute(all_prices_stmt)).scalar() or 500.0)

        all_svc_total = sum(svc.values())
        avg_svc = all_svc_total / len(comp_ids) if comp_ids else 0

        results = []
        for cid in comp_ids:
            scores = {}
            tags = []
            for c in competitors:
                if c.id == cid:
                    tags = [t.lower() for t in (c.tags or [])]
                    break

            # Market Presence: services + pricing + sources
            scores["market_presence"] = clamp(
                (svc.get(cid, 0) / max(avg_svc, 1)) * 0.5
                + clamp(prc.get(cid, 0) / 10.0) * 0.3
                + clamp(src.get(cid, 0) / 10.0) * 0.2
            ) * 100

            # Growth Potential: change velocity + service additions
            scores["growth_potential"] = clamp(
                clamp(chg.get(cid, 0) / 15.0) * 0.6
                + clamp(svc.get(cid, 0) / 20.0) * 0.4
            ) * 100

            # Innovation Score: changes + content + pricing diversity
            scores["innovation_score"] = clamp(
                clamp(chg.get(cid, 0) / 10.0) * 0.4
                + clamp(cnt.get(cid, 0) / 15.0) * 0.3
                + clamp(prc.get(cid, 0) / 8.0) * 0.3
            ) * 100

            # Pricing Competitiveness: how close to market average
            pr = prc_stats.get(cid)
            if pr and pr.avg_p:
                price_ratio = float(pr.avg_p) / global_avg_price if global_avg_price else 1.0
                scores["pricing_competitiveness"] = clamp(1.0 - abs(price_ratio - 1.0)) * 100
            else:
                scores["pricing_competitiveness"] = 30.0

            # Regional Strength: tier tags, chennai focus
            regional = 0.3
            if any("chennai" in t for t in tags):
                regional += 0.3
            if any("tier-1" in t for t in tags):
                regional += 0.2
            if any("national" in t or "pan-india" in t for t in tags):
                regional += 0.2
            scores["regional_strength"] = clamp(regional) * 100

            # Digital Presence: social + sources
            scores["digital_presence"] = clamp(
                clamp(soc.get(cid, 0) / 5.0) * 0.6
                + clamp(src.get(cid, 0) / 10.0) * 0.4
            ) * 100

            # Service Diversity: unique categories
            scores["service_diversity"] = clamp(svc.get(cid, 0) / max(avg_svc * 1.5, 1)) * 100

            # Customer Reach: social + pricing (affordability indicator)
            scores["customer_reach"] = clamp(
                clamp(soc.get(cid, 0) / 4.0) * 0.5
                + clamp(prc.get(cid, 0) / 8.0) * 0.5
            ) * 100

            # Technology Adoption: digital indicators
            scores["technology_adoption"] = clamp(
                clamp(soc.get(cid, 0) / 3.0) * 0.4
                + clamp(src.get(cid, 0) / 8.0) * 0.3
                + clamp(cnt.get(cid, 0) / 10.0) * 0.3
            ) * 100

            # Content Authority: content + pricing (transparency)
            scores["content_authority"] = clamp(
                clamp(cnt.get(cid, 0) / 15.0) * 0.6
                + clamp(prc.get(cid, 0) / 6.0) * 0.4
            ) * 100

            overall = sum(scores[k] * self.WEIGHTS[k] for k in self.WEIGHTS)

            results.append({
                "competitor_id": cid,
                "competitor_name": comp_names.get(cid, ""),
                "scores": {k: round(v, 2) for k, v in scores.items()},
                "overall_score": round(overall, 2),
                "generated_at": datetime.now(UTC).isoformat(),
            })

        results.sort(key=lambda x: x["overall_score"], reverse=True)
        for i, r in enumerate(results):
            r["rank"] = i + 1

        all_overalls = [r["overall_score"] for r in results]
        for r in results:
            r["grade"] = self._grade(r["overall_score"], all_overalls)

        return results

    def _grade(self, score: float, all_scores: list[float] | None = None) -> str:
        """Grade based on relative position among competitors, not absolute thresholds."""
        if all_scores and len(all_scores) >= 2:
            sorted_scores = sorted(all_scores, reverse=True)
            n = len(sorted_scores)
            rank = next((i for i, s in enumerate(sorted_scores) if s == score), 0)
            pct = rank / max(n - 1, 1)
            if pct == 0:
                return "A"
            if pct <= 0.25:
                return "B"
            if pct <= 0.50:
                return "C"
            if pct <= 0.75:
                return "D"
            return "F"
        if score >= 65:
            return "A"
        if score >= 50:
            return "B"
        if score >= 35:
            return "C"
        if score >= 20:
            return "D"
        return "F"

    async def _batch_count(
        self, session: AsyncSession, model: Any, comp_ids: list[int]
    ) -> dict[int, int]:
        stmt = (
            select(model.competitor_id, func.count().label("cnt"))
            .where(model.competitor_id.in_(comp_ids))
            .group_by(model.competitor_id)
        )
        return {r[0]: r[1] for r in (await session.execute(stmt)).all()}


advanced_scorer = AdvancedScorer()
