"""Competitor Benchmark Matrix Service.

Computes multi-competitor pricing comparisons across normalized canonical services:
Utservio price vs competitor Min, Max, Mean, Median, Price Gap %, Price Index, and Market Position.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, TYPE_CHECKING
import statistics
import structlog
from sqlalchemy import select

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


@dataclass
class ServiceBenchmarkRow:
    canonical_service_name: str
    category: str
    utservio_price: float
    competitor_prices: dict[str, float]  # competitor_name -> price
    market_min: float
    market_max: float
    market_mean: float
    market_median: float
    price_gap_pct: float
    price_index: float
    market_position: str
    recommendation_summary: str


class CompetitorBenchmarkMatrix:
    """Computes benchmark pricing metrics across Utservio and 5+ competitors."""

    DEFAULT_BENCHMARK_MOCK_DATA = [
        {
            "canonical_service": "AC Split Unit Servicing & Deep Clean",
            "category": "AC & Appliance Repair",
            "utservio": 599.0,
            "competitors": {
                "Urban Company": 599.0,
                "Chennai Home Service": 499.0,
                "Vijay Home Services": 549.0,
                "NoBroker": 449.0,
                "Sulekha": 499.0,
                "Justdial": 525.0,
            }
        },
        {
            "canonical_service": "AC Gas Charging & Leak Fix",
            "category": "AC & Appliance Repair",
            "utservio": 2499.0,
            "competitors": {
                "Urban Company": 2299.0,
                "Chennai Home Service": 1999.0,
                "Vijay Home Services": 2199.0,
                "NoBroker": 1899.0,
                "Sulekha": 1999.0,
            }
        },
        {
            "canonical_service": "Deep Home Cleaning (3 BHK)",
            "category": "Cleaning & Pest Control",
            "utservio": 3499.0,
            "competitors": {
                "Urban Company": 3999.0,
                "Chennai Home Service": 3299.0,
                "Vijay Home Services": 3499.0,
                "NoBroker": 2999.0,
                "Sulekha": 3199.0,
            }
        },
        {
            "canonical_service": "Full House Bathroom Sanitization",
            "category": "Cleaning & Pest Control",
            "utservio": 899.0,
            "competitors": {
                "Urban Company": 899.0,
                "Chennai Home Service": 699.0,
                "Vijay Home Services": 799.0,
                "NoBroker": 649.0,
                "Sulekha": 699.0,
            }
        },
        {
            "canonical_service": "Ceiling Fan Installation & Repair",
            "category": "Plumbing & Electrical",
            "utservio": 149.0,
            "competitors": {
                "Urban Company": 149.0,
                "Chennai Home Service": 129.0,
                "Vijay Home Services": 139.0,
                "NoBroker": 119.0,
                "Sulekha": 129.0,
            }
        }
    ]

    def compute_matrix(self, input_rows: list[dict[str, Any]] | None = None) -> list[ServiceBenchmarkRow]:
        """Calculates benchmark matrix with Price Gap %, Price Index, and Market Position."""
        rows = input_rows if input_rows else self.DEFAULT_BENCHMARK_MOCK_DATA
        matrix_results: list[ServiceBenchmarkRow] = []

        for row in rows:
            utservio_p = float(row["utservio"])
            comp_dict = {k: float(v) for k, v in row["competitors"].items() if v is not None and float(v) > 0}
            comp_prices = list(comp_dict.values())

            if not comp_prices:
                continue

            m_min = round(min(comp_prices), 2)
            m_max = round(max(comp_prices), 2)
            m_mean = round(sum(comp_prices) / len(comp_prices), 2)
            m_median = round(statistics.median(comp_prices), 2)

            # Formula 1: Price Gap % = (Utservio Price - Competitor Median) / Competitor Median * 100
            price_gap_pct = round(((utservio_p - m_median) / max(m_median, 1e-5)) * 100, 2)

            # Formula 2: Price Index = Utservio Price / Competitor Median Price
            price_index = round(utservio_p / max(m_median, 1e-5), 2)

            # Market Position Classification
            if price_index > 1.15:
                pos = "overpriced"
                rec = f"Utservio is {price_gap_pct:.1f}% above competitor median. Consider promotional adjustment."
            elif price_index < 0.85:
                pos = "discount"
                rec = f"Utservio is {abs(price_gap_pct):.1f}% below competitor median. Room for margin expansion."
            elif 0.95 <= price_index <= 1.05:
                pos = "par_with_market"
                rec = "Utservio pricing is perfectly aligned with the market median."
            else:
                pos = "competitive"
                rec = "Pricing is within standard competitive tolerance limits."

            matrix_results.append(
                ServiceBenchmarkRow(
                    canonical_service_name=row["canonical_service"],
                    category=row.get("category", "General Services"),
                    utservio_price=utservio_p,
                    competitor_prices=comp_dict,
                    market_min=m_min,
                    market_max=m_max,
                    market_mean=m_mean,
                    market_median=m_median,
                    price_gap_pct=price_gap_pct,
                    price_index=price_index,
                    market_position=pos,
                    recommendation_summary=rec,
                )
            )

        return matrix_results


benchmark_matrix_service = CompetitorBenchmarkMatrix()
