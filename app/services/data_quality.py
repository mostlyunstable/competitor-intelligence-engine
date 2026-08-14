from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


        """
        Evaluate the quality of extracted competitor data.
        Never treats a scraper failure as "NO_DATA".
        """
class DataState(StrEnum):
    VALID_DATA = "valid_data"
    STALE_DATA = "stale_data"
    EXTRACTION_FAILED = "extraction_failed"
    NO_DATA = "no_data"


@dataclass
class QualityMetrics:
    state: DataState
    missing_fields: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    last_successful_scrape: datetime | None = None
    extraction_methods: list[str] = field(default_factory=list)
    failure_reason: str | None = None


class DataQualityValidator:
    def __init__(self, stale_threshold_days: int = 30):
        self.stale_threshold_days = stale_threshold_days

    def evaluate(
        self,
        extracted_data: dict[str, Any],
        last_scrape_time: datetime | None,
        is_scraper_failure: bool = False,
        failure_reason: str | None = None,
    ) -> QualityMetrics:
        if is_scraper_failure:
            return QualityMetrics(
                state=DataState.EXTRACTION_FAILED,
                last_successful_scrape=last_scrape_time,
                failure_reason=failure_reason or "Scraper failed completely.",
            )

        if not extracted_data:
            return QualityMetrics(
                state=DataState.NO_DATA,
                last_successful_scrape=last_scrape_time,
                failure_reason="Scrape succeeded but no relevant intelligence was found.",
            )

        # Check staleness
        if last_scrape_time:
            days_since = (datetime.now(UTC) - last_scrape_time).days
            if days_since > self.stale_threshold_days:
                return QualityMetrics(
                    state=DataState.STALE_DATA,
                    last_successful_scrape=last_scrape_time,
                    failure_reason=f"Data is {days_since} days old (threshold: {self.stale_threshold_days})",
                )

        # Validate data
        missing = []
        required_fields = ["company_name", "services", "pricing"]
        for field_name in required_fields:
            if not extracted_data.get(field_name):
                missing.append(field_name)

        # Approximate overall confidence if tracking provenance
        confidence = 0.0
        methods: list[str] = []
        # Fallback to VALID_DATA if not stale or failed, even with missing fields
        state = DataState.VALID_DATA

        return QualityMetrics(
            state=state,
            missing_fields=missing,
            confidence_score=confidence,
            last_successful_scrape=datetime.now(UTC),
            extraction_methods=methods,
        )
