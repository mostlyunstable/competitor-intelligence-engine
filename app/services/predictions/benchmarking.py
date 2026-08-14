"""Predictive Benchmarking.

Compares current and projected competitor performance across
multiple dimensions with growth, innovation, and risk scores.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, TYPE_CHECKING

import structlog
from sqlalchemy import func, select

from app.database.models import (
    Competitor,
    CompetitorContent,
    CompetitorPricing,
    CompetitorService,
    CompetitorSocial,
    ChangeLog,
)
from app.services.predictions.analytics import clamp as _clamp

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class PredictiveBenchmarker:
    """Generates predictive benchmarks for all competitors."""

    async def benchmark_all(self, session: AsyncSession) -> list[dict[str, Any]]:
        """Batch: fetches all metrics in 5 queries instead of 5*N."""
        stmt = select(Competitor).where(Competitor.enabled.is_(True))
        competitors = (await session.execute(stmt)).scalars().all()
        comp_ids = [c.id for c in competitors]
        comp_names = {c.id: c.name for c in competitors}

        if not comp_ids:
            return []

        # 5 batch count queries
        svc = await self._batch_count(session, CompetitorService, comp_ids)
        prc = await self._batch_count(session, CompetitorPricing, comp_ids)
        cnt = await self._batch_count(session, CompetitorContent, comp_ids)
        soc = await self._batch_count(session, CompetitorSocial, comp_ids)

        since = datetime.now(UTC) - timedelta(days=30)
        chg_stmt = (
            select(ChangeLog.competitor_id, func.count().label("cnt"))
            .where(ChangeLog.competitor_id.in_(comp_ids))
            .where(ChangeLog.detected_at >= since)
            .group_by(ChangeLog.competitor_id)
        )
        chg = {r[0]: r[1] for r in (await session.execute(chg_stmt)).all()}

        metrics = []
        for cid in comp_ids:
            metrics.append({
                "competitor_id": cid,
                "competitor_name": comp_names.get(cid, ""),
                "service_count": svc.get(cid, 0),
                "pricing_count": prc.get(cid, 0),
                "content_count": cnt.get(cid, 0),
                "social_count": soc.get(cid, 0),
                "change_count": chg.get(cid, 0),
            })

        services_sorted = sorted(metrics, key=lambda x: x["service_count"], reverse=True)
        pricing_sorted = sorted(metrics, key=lambda x: x["pricing_count"], reverse=True)
        content_sorted = sorted(metrics, key=lambda x: x["content_count"], reverse=True)
        change_sorted = sorted(metrics, key=lambda x: x["change_count"], reverse=True)

        id_to_idx = {m["competitor_id"]: i for i, m in enumerate(metrics)}

        for m in metrics:
            cid = m["competitor_id"]
            sr = next(j for j, x in enumerate(services_sorted) if x["competitor_id"] == cid)
            pr = next(j for j, x in enumerate(pricing_sorted) if x["competitor_id"] == cid)
            cr = next(j for j, x in enumerate(content_sorted) if x["competitor_id"] == cid)
            chr_ = next(j for j, x in enumerate(change_sorted) if x["competitor_id"] == cid)

            current_rank = round(((sr + pr + cr + chr_) / 4) + 1)
            growth_score = _clamp(m["change_count"] / 20.0) * 40 + _clamp(m["service_count"] / 20.0) * 30 + _clamp(m["content_count"] / 15.0) * 30
            innovation_score = _clamp(m["change_count"] / 15.0) * 50 + _clamp(m["content_count"] / 10.0) * 30 + _clamp(m["pricing_count"] / 8.0) * 20
            expansion_score = _clamp(m["service_count"] / 30.0) * 50 + _clamp(m["social_count"] / 5.0) * 30 + 20
            risk_score = max(0, 100 - growth_score)
            predicted_rank = max(1, round(current_rank - (growth_score / 50)))

            overall = "stable"
            if growth_score > 60:
                overall = "high_growth"
            elif growth_score > 30:
                overall = "medium_growth"
            elif growth_score < 15:
                overall = "declining"

            m.update({
                "current_rank": current_rank,
                "predicted_rank": predicted_rank,
                "growth_score": round(growth_score, 2),
                "innovation_score": round(innovation_score, 2),
                "expansion_score": round(expansion_score, 2),
                "risk_score": round(risk_score, 2),
                "overall_prediction": overall,
                "benchmark_data": {
                    "service_rank": sr + 1, "pricing_rank": pr + 1,
                    "content_rank": cr + 1, "change_rank": chr_ + 1,
                },
                "generated_at": datetime.now(UTC).isoformat(),
            })

        metrics.sort(key=lambda x: x["current_rank"])

        try:
            from app.services.predictions.scoring import advanced_scorer
            scores = await advanced_scorer.score_all(session)
            score_map = {s["competitor_id"]: s for s in scores}
            for m in metrics:
                if m["competitor_id"] in score_map:
                    m["advanced_score"] = score_map[m["competitor_id"]]
        except Exception as exc:
            logger.warning("scoring_integration_failed", error=str(exc))

        return metrics

    async def _batch_count(
        self, session: AsyncSession, model: Any, comp_ids: list[int]
    ) -> dict[int, int]:
        stmt = (
            select(model.competitor_id, func.count().label("cnt"))
            .where(model.competitor_id.in_(comp_ids))
            .group_by(model.competitor_id)
        )
        return {r[0]: r[1] for r in (await session.execute(stmt)).all()}

    async def benchmark_competitor(
        self, competitor_id: int, session: AsyncSession
    ) -> dict[str, Any]:
        all_benchmarks = await self.benchmark_all(session)
        for b in all_benchmarks:
            if b["competitor_id"] == competitor_id:
                return b
        return {}


predictive_benchmarker = PredictiveBenchmarker()
