"""Industry Benchmarking: percentile rankings and comparative analytics."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any, TYPE_CHECKING

import structlog
from sqlalchemy import func, select

from app.services.predictions.analytics import clamp, percentile, z_score

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class IndustryBenchmarker:
    """Benchmarks competitors against industry, regional, and category averages."""

    async def benchmark_all(self, session: AsyncSession) -> list[dict[str, Any]]:
        from app.services.predictions.scoring import advanced_scorer

        scores = await advanced_scorer.score_all(session)
        if not scores:
            return []

        # Compute aggregate statistics
        overall_scores = [s["overall_score"] for s in scores]
        overall_mean = sum(overall_scores) / len(overall_scores) if overall_scores else 0

        # Per-dimension stats
        dim_stats: dict[str, list[float]] = {}
        for s in scores:
            for dim, val in s.get("scores", {}).items():
                dim_stats.setdefault(dim, []).append(val)

        dim_means = {d: sum(v) / len(v) if v else 0 for d, v in dim_stats.items()}

        results = []
        for s in scores:
            comp_id = s["competitor_id"]
            overall = s["overall_score"]

            # Percentile ranking
            overall_pct = percentile(overall_scores, overall) / 100.0

            # Per-dimension percentiles
            dim_percentiles = {}
            for dim, val in s.get("scores", {}).items():
                dim_vals = dim_stats.get(dim, [])
                dim_percentiles[dim] = round(percentile(dim_vals, val) / 100.0, 3)

            # Z-score (how many stddev from mean)
            z = z_score(overall, overall_scores)

            # Comparisons
            vs_average = overall - overall_mean
            top_score = max(overall_scores) if overall_scores else 0
            vs_top = overall - top_score

            results.append({
                "competitor_id": comp_id,
                "competitor_name": s.get("competitor_name", ""),
                "overall_score": round(overall, 2),
                "percentile": round(overall_pct * 100, 1),
                "percentile_rank": round(overall_pct, 3),
                "z_score": round(z, 3),
                "vs_average": round(vs_average, 2),
                "vs_top_performer": round(vs_top, 2),
                "dimension_percentiles": dim_percentiles,
                "industry_stats": {
                    "mean": round(overall_mean, 2),
                    "top_score": round(top_score, 2),
                    "total_competitors": len(scores),
                },
                "rank": s.get("rank", 0),
                "grade": s.get("grade", "F"),
                "generated_at": datetime.now(UTC).isoformat(),
            })

        results.sort(key=lambda x: x["overall_score"], reverse=True)
        return results

    async def benchmark_competitor(
        self, competitor_id: int, session: AsyncSession
    ) -> dict[str, Any]:
        all_benchmarks = await self.benchmark_all(session)
        for b in all_benchmarks:
            if b["competitor_id"] == competitor_id:
                return b
        return {}

    async def get_category_benchmarks(
        self, session: AsyncSession
    ) -> dict[str, Any]:
        from app.database.models import Competitor, CompetitorService

        stmt = select(Competitor).where(Competitor.enabled.is_(True))
        competitors = (await session.execute(stmt)).scalars().all()

        cat_benchmarks: dict[str, list[dict[str, Any]]] = {}
        for comp in competitors:
            svc_stmt = (
                select(CompetitorService.service_category, func.count().label("cnt"))
                .where(CompetitorService.competitor_id == comp.id)
                .where(CompetitorService.service_category.isnot(None))
                .group_by(CompetitorService.service_category)
            )
            svc_cats = (await session.execute(svc_stmt)).all()

            for row in svc_cats:
                cat = row.service_category
                cat_benchmarks.setdefault(cat, []).append({
                    "competitor_id": comp.id,
                    "competitor_name": comp.name,
                    "service_count": row.cnt,
                })

        results = {}
        for cat, comps in cat_benchmarks.items():
            counts = [c["service_count"] for c in comps]
            results[cat] = {
                "category": cat,
                "competitor_count": len(comps),
                "average_services": round(sum(counts) / len(counts), 1) if counts else 0,
                "max_services": max(counts) if counts else 0,
                "min_services": min(counts) if counts else 0,
                "leaders": sorted(comps, key=lambda x: x["service_count"], reverse=True)[:3],
            }

        return results


industry_benchmarker = IndustryBenchmarker()
