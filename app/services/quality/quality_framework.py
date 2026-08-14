"""7-Dimension Data Quality Framework.

Evaluates every pricing observation against 7 dimensions (Completeness, Accuracy,
Consistency, Timeliness, Validity, Uniqueness, Comparability) and calculates a weighted
Data Quality Score to prevent low-quality records from entering ML training sets.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any
import structlog

logger = structlog.get_logger(__name__)


@dataclass
class DataQualityReport:
    completeness: float
    accuracy: float
    consistency: float
    timeliness: float
    validity: float
    uniqueness: float
    comparability: float
    overall_quality_score: float
    is_ml_ready: bool
    quality_flags: list[str]


class DataQualityFramework:
    """7-Dimension Data Quality Assessment Engine."""

    # Dimension Weights (Total = 1.0)
    WEIGHTS = {
        "completeness": 0.20,
        "accuracy": 0.20,
        "consistency": 0.15,
        "timeliness": 0.15,
        "validity": 0.10,
        "uniqueness": 0.10,
        "comparability": 0.10,
    }

    def evaluate(self, observation: dict[str, Any]) -> DataQualityReport:
        """Evaluates 7 quality dimensions for an observation dictionary."""
        flags: list[str] = []

        # 1. Completeness (Are all key fields present?)
        required = ["original_service_name", "price", "currency", "competitor_id", "location"]
        present = sum(1 for f in required if observation.get(f) is not None)
        completeness = round(present / len(required), 2)
        if completeness < 1.0:
            flags.append(f"Missing required fields (completeness={completeness})")

        # 2. Accuracy (Range & numeric integrity check)
        price = observation.get("price")
        accuracy = 1.0
        if price is None or price <= 0:
            accuracy = 0.0
            flags.append("Invalid or zero price value")
        elif price > 500000:
            accuracy = 0.5
            flags.append("Extreme pricing value outlier (> ₹5,00,000)")

        # 3. Consistency (Currency and unit check)
        currency = str(observation.get("currency", "INR")).upper()
        unit = str(observation.get("pricing_unit", "per_service"))
        consistency = 1.0
        if currency not in {"INR", "USD", "EUR", "GBP"}:
            consistency = 0.5
            flags.append(f"Unusual currency code '{currency}'")
        if not unit:
            consistency -= 0.3

        # 4. Timeliness (Data freshness decay)
        collected_at = observation.get("collected_at")
        timeliness = 1.0
        if collected_at:
            if isinstance(collected_at, str):
                try:
                    dt = datetime.fromisoformat(collected_at.replace("Z", "+00:00"))
                except ValueError:
                    dt = datetime.now(UTC)
            else:
                dt = collected_at
            days_old = (datetime.now(UTC) - dt).days
            if days_old > 30:
                timeliness = round(max(0.2, 1.0 - (days_old - 30) * 0.02), 2)
                flags.append(f"Stale pricing observation ({days_old} days old)")

        # 5. Validity (String length and schema sanity)
        s_name = str(observation.get("original_service_name", ""))
        validity = 1.0
        if len(s_name) < 3 or len(s_name) > 300:
            validity = 0.4
            flags.append("Invalid service name length")

        # 6. Uniqueness (Duplicate flag check)
        is_duplicate = bool(observation.get("is_duplicate", False))
        uniqueness = 0.0 if is_duplicate else 1.0
        if is_duplicate:
            flags.append("Duplicate observation detected")

        # 7. Comparability (Taxonomy match score)
        similarity = float(observation.get("similarity_score", observation.get("confidence_score", 0.8)))
        comparability = round(min(1.0, max(0.0, similarity)), 2)
        if comparability < 0.6:
            flags.append(f"Low taxonomy comparability score ({comparability})")

        # Weighted Overall Score
        overall = (
            self.WEIGHTS["completeness"] * completeness
            + self.WEIGHTS["accuracy"] * accuracy
            + self.WEIGHTS["consistency"] * consistency
            + self.WEIGHTS["timeliness"] * timeliness
            + self.WEIGHTS["validity"] * validity
            + self.WEIGHTS["uniqueness"] * uniqueness
            + self.WEIGHTS["comparability"] * comparability
        )
        overall = round(overall, 2)
        is_ml_ready = overall >= 0.70 and not is_duplicate and accuracy > 0

        return DataQualityReport(
            completeness=completeness,
            accuracy=accuracy,
            consistency=consistency,
            timeliness=timeliness,
            validity=validity,
            uniqueness=uniqueness,
            comparability=comparability,
            overall_quality_score=overall,
            is_ml_ready=is_ml_ready,
            quality_flags=flags,
        )


data_quality_framework = DataQualityFramework()
