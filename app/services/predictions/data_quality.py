"""Data Quality Intelligence: evaluates incoming data quality."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, TYPE_CHECKING

import structlog
from sqlalchemy import func, select

from app.services.predictions.analytics import clamp

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class DataQualityEvaluator:
    """Evaluates data completeness, freshness, accuracy, and consistency."""

    async def evaluate(
        self, competitor_id: int, session: AsyncSession
    ) -> dict[str, Any]:
        from app.database.models import (
            CompetitorService, CompetitorPricing, CompetitorContent,
            CompetitorSocial, CollectionLog, RawStorage,
        )

        now = datetime.now(UTC)
        last_30 = now - timedelta(days=30)

        svc = (await session.execute(
            select(func.count()).select_from(CompetitorService).where(
                CompetitorService.competitor_id == competitor_id)
        )).scalar() or 0

        prc = (await session.execute(
            select(func.count()).select_from(CompetitorPricing).where(
                CompetitorPricing.competitor_id == competitor_id)
        )).scalar() or 0

        cnt = (await session.execute(
            select(func.count()).select_from(CompetitorContent).where(
                CompetitorContent.competitor_id == competitor_id)
        )).scalar() or 0

        soc = (await session.execute(
            select(func.count()).select_from(CompetitorSocial).where(
                CompetitorSocial.competitor_id == competitor_id)
        )).scalar() or 0

        last_log_stmt = (
            select(CollectionLog.start_time, CollectionLog.success)
            .where(CollectionLog.competitor_id == competitor_id)
            .order_by(CollectionLog.start_time.desc())
            .limit(1)
        )
        last_log = (await session.execute(last_log_stmt)).one_or_none()

        total_logs = (await session.execute(
            select(func.count()).select_from(CollectionLog).where(
                CollectionLog.competitor_id == competitor_id)
        )).scalar() or 0

        success_logs = (await session.execute(
            select(func.count()).select_from(CollectionLog).where(
                CollectionLog.competitor_id == competitor_id,
                CollectionLog.success.is_(True))
        )).scalar() or 0

        raw_total = (await session.execute(
            select(func.count()).select_from(RawStorage).where(
                RawStorage.competitor_id == competitor_id)
        )).scalar() or 0

        raw_extracted = (await session.execute(
            select(func.count()).select_from(RawStorage).where(
                RawStorage.competitor_id == competitor_id,
                RawStorage.extracted_data.isnot(None))
        )).scalar() or 0

        # Scores
        completeness = self._score_completeness(svc, prc, cnt, soc)
        freshness = self._score_freshness(last_log.start_time if last_log else None, now)
        accuracy = success_logs / total_logs if total_logs > 0 else 0.0
        extraction_rate = raw_extracted / raw_total if raw_total > 0 else 0.0

        # Missing values detection
        missing_pricing = (await session.execute(
            select(func.count()).select_from(CompetitorPricing).where(
                CompetitorPricing.competitor_id == competitor_id,
                CompetitorPricing.base_price.is_(None))
        )).scalar() or 0

        overall = (
            completeness * 0.30
            + freshness * 0.25
            + accuracy * 0.25
            + extraction_rate * 0.20
        )

        return {
            "competitor_id": competitor_id,
            "completeness": round(completeness, 3),
            "freshness": round(freshness, 3),
            "accuracy": round(accuracy, 3),
            "extraction_rate": round(extraction_rate, 3),
            "missing_pricing_entries": missing_pricing,
            "overall_quality": round(overall, 3),
            "quality_level": (
                "high" if overall >= 0.7
                else "medium" if overall >= 0.4
                else "low"
            ),
            "data_counts": {
                "services": svc, "pricing": prc,
                "content": cnt, "social": soc,
                "raw_pages": raw_total, "extracted": raw_extracted,
            },
            "collection_stats": {
                "total_logs": total_logs,
                "success_rate": round(accuracy, 3),
            },
            "evaluated_at": now.isoformat(),
        }

    async def evaluate_all(self, session: AsyncSession) -> list[dict[str, Any]]:
        from app.database.models import Competitor

        stmt = select(Competitor).where(Competitor.enabled.is_(True))
        competitors = (await session.execute(stmt)).scalars().all()

        results = []
        for comp in competitors:
            result = await self.evaluate(comp.id, session)
            result["competitor_name"] = comp.name
            results.append(result)

        results.sort(key=lambda x: x["overall_quality"], reverse=True)
        return results

    def _score_completeness(self, svc: int, prc: int, cnt: int, soc: int) -> float:
        has_service = min(svc / 5.0, 1.0) * 0.30
        has_pricing = min(prc / 5.0, 1.0) * 0.30
        has_content = min(cnt / 3.0, 1.0) * 0.20
        has_social = min(soc / 2.0, 1.0) * 0.20
        return clamp(has_service + has_pricing + has_content + has_social)

    def _score_freshness(self, last_collected: datetime | None, now: datetime) -> float:
        if not last_collected:
            return 0.0
        age_days = (now - last_collected).total_seconds() / 86400
        if age_days <= 1:
            return 1.0
        elif age_days <= 7:
            return 0.85
        elif age_days <= 30:
            return 0.65
        elif age_days <= 90:
            return 0.40
        return 0.15


data_quality_evaluator = DataQualityEvaluator()
