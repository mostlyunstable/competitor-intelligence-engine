"""Reporting & analysis service for competitor intelligence data.

Provides:
- Collection reports with extraction summaries
- Diff reports between two collection runs
- Side-by-side competitor comparisons
- Trend analysis over time
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

    from app.database.models import (
        CollectionLog,
        Competitor,
        CompetitorContent,
        CompetitorPricing,
        CompetitorService,
        CompetitorSocial,
    )


@dataclass
class ReportSection:
    title: str
    data: list[dict[str, Any]]


@dataclass
class CollectionReport:
    """Summary of a single collection run."""

    competitor_name: str
    competitor_id: int
    start_time: str
    duration_seconds: float
    success: bool
    errors: list[str]
    services: list[dict[str, Any]]
    pricing: list[dict[str, Any]]
    content: list[dict[str, Any]]
    social: list[dict[str, Any]]
    records_collected: int


@dataclass
class DiffItem:
    change_type: str  # "added", "removed", "modified"
    field: str
    identifier: str
    before: dict[str, Any] | None
    after: dict[str, Any] | None


@dataclass
class DiffReport:
    competitor_name: str
    competitor_id: int
    before_time: str
    after_time: str
    services: list[DiffItem] = field(default_factory=list)
    pricing: list[DiffItem] = field(default_factory=list)
    content: list[DiffItem] = field(default_factory=list)
    social: list[DiffItem] = field(default_factory=list)

    @property
    def total_changes(self) -> int:
        return len(self.services) + len(self.pricing) + len(self.content) + len(self.social)


@dataclass
class CompetitorSummary:
    competitor_id: int
    competitor_name: str
    service_count: int
    pricing_count: int
    content_count: int
    social_count: int
    last_collected: str | None
    last_collection_duration: float | None


@dataclass
class ComparisonReport:
    competitors: list[CompetitorSummary] = field(default_factory=list)


@dataclass
class TrendPoint:
    date: str
    services_added: int
    pricing_added: int
    content_added: int
    records_collected: int
    duration_seconds: float


@dataclass
class TrendReport:
    competitor_name: str
    competitor_id: int
    collection_history: list[TrendPoint] = field(default_factory=list)


def _safe_str(val: Any) -> str:
    return str(val) if val is not None else ""


class ReportingService:
    """Generates reports and analysis from collected competitor data."""

    async def get_collection_report(
        self,
        competitor: Competitor,
        log: CollectionLog,
        services: Sequence[CompetitorService],
        pricing: Sequence[CompetitorPricing],
        content: Sequence[CompetitorContent],
        social: Sequence[CompetitorSocial],
    ) -> CollectionReport:
        errors: list[str] = []
        if log.errors:
            if isinstance(log.errors, list):
                errors = [str(e) for e in log.errors]
            elif isinstance(log.errors, str):
                errors = [log.errors]

        return CollectionReport(
            competitor_name=competitor.name,
            competitor_id=competitor.id,
            start_time=_safe_str(log.start_time),
            duration_seconds=log.duration_seconds or 0.0,
            success=log.success or False,
            errors=errors,
            services=[self._service_to_dict(s) for s in services],
            pricing=[self._pricing_to_dict(p) for p in pricing],
            content=[self._content_to_dict(c) for c in content],
            social=[self._social_to_dict(s) for s in social],
            records_collected=log.records_collected or 0,
        )

    def _service_to_dict(self, s: CompetitorService) -> dict[str, Any]:
        return {
            "id": s.id,
            "service_name": s.service_name,
            "service_category": s.service_category,
            "description": s.description,
            "starting_price": s.starting_price,
            "currency": s.currency,
            "estimated_duration": s.estimated_duration,
        }

    def _pricing_to_dict(self, p: CompetitorPricing) -> dict[str, Any]:
        return {
            "id": p.id,
            "service_name": p.service_name,
            "category": p.category,
            "base_price": p.base_price,
            "promotional_price": p.promotional_price,
            "currency": p.currency,
            "discount": p.discount,
        }

    def _content_to_dict(self, c: CompetitorContent) -> dict[str, Any]:
        return {
            "id": c.id,
            "title": c.title,
            "author": c.author,
            "publish_date": _safe_str(c.publish_date),
            "url": c.url,
            "summary": c.summary,
            "content_type": c.content_type,
        }

    def _social_to_dict(self, s: CompetitorSocial) -> dict[str, Any]:
        return {
            "id": s.id,
            "platform": s.platform,
            "profile_url": s.profile_url,
            "username": s.username,
        }

    async def compute_diff(
        self,
        competitor: Competitor,
        before_log: CollectionLog,
        after_log: CollectionLog,
        before_services: Sequence[CompetitorService],
        after_services: Sequence[CompetitorService],
        before_pricing: Sequence[CompetitorPricing],
        after_pricing: Sequence[CompetitorPricing],
        before_content: Sequence[CompetitorContent],
        after_content: Sequence[CompetitorContent],
        before_social: Sequence[CompetitorSocial],
        after_social: Sequence[CompetitorSocial],
    ) -> DiffReport:
        report = DiffReport(
            competitor_name=competitor.name,
            competitor_id=competitor.id,
            before_time=_safe_str(before_log.start_time),
            after_time=_safe_str(after_log.start_time),
        )

        report.services = self._diff_lists(
            [self._service_to_dict(s) for s in before_services],
            [self._service_to_dict(s) for s in after_services],
            "service_name",
            "services",
        )
        report.pricing = self._diff_lists(
            [self._pricing_to_dict(p) for p in before_pricing],
            [self._pricing_to_dict(p) for p in after_pricing],
            "service_name",
            "pricing",
        )
        report.content = self._diff_lists(
            [self._content_to_dict(c) for c in before_content],
            [self._content_to_dict(c) for c in after_content],
            "title",
            "content",
        )
        report.social = self._diff_lists(
            [self._social_to_dict(s) for s in before_social],
            [self._social_to_dict(s) for s in after_social],
            "platform",
            "social",
        )
        return report

    def _diff_lists(
        self,
        before: list[dict[str, Any]],
        after: list[dict[str, Any]],
        key_field: str,
        field_name: str,
    ) -> list[DiffItem]:
        before_map: dict[str, dict[str, Any]] = {}
        for item in before:
            key = _safe_str(item.get(key_field))
            if key:
                before_map[key] = item

        after_map: dict[str, dict[str, Any]] = {}
        for item in after:
            key = _safe_str(item.get(key_field))
            if key:
                after_map[key] = item

        items: list[DiffItem] = []

        before_keys = set(before_map)
        after_keys = set(after_map)

        for key in after_keys - before_keys:
            items.append(DiffItem("added", field_name, key, None, after_map[key]))

        for key in before_keys - after_keys:
            items.append(DiffItem("removed", field_name, key, before_map[key], None))

        for key in before_keys & after_keys:
            b = before_map[key]
            a = after_map[key]
            if b != a:
                items.append(DiffItem("modified", field_name, key, b, a))

        return items

    async def compute_comparison(
        self,
        competitors: Sequence[Competitor],
        services_map: dict[int, int],
        pricing_map: dict[int, int],
        content_map: dict[int, int],
        social_map: dict[int, int],
        last_logs: dict[int, CollectionLog | None],
    ) -> ComparisonReport:
        summaries: list[CompetitorSummary] = []
        for comp in competitors:
            log = last_logs.get(comp.id)
            summaries.append(
                CompetitorSummary(
                    competitor_id=comp.id,
                    competitor_name=comp.name,
                    service_count=services_map.get(comp.id, 0),
                    pricing_count=pricing_map.get(comp.id, 0),
                    content_count=content_map.get(comp.id, 0),
                    social_count=social_map.get(comp.id, 0),
                    last_collected=_safe_str(log.start_time) if log else None,
                    last_collection_duration=log.duration_seconds if log else None,
                )
            )
        return ComparisonReport(competitors=summaries)

    async def compute_trends(
        self,
        competitor: Competitor,
        logs: Sequence[CollectionLog],
    ) -> TrendReport:
        report = TrendReport(
            competitor_name=competitor.name,
            competitor_id=competitor.id,
        )
        for log in logs:
            report.collection_history.append(
                TrendPoint(
                    date=_safe_str(log.start_time),
                    services_added=0,
                    pricing_added=0,
                    content_added=0,
                    records_collected=log.records_collected or 0,
                    duration_seconds=log.duration_seconds or 0.0,
                )
            )
        return report


reporting_service = ReportingService()
