"""Geographic Intelligence Module.

Spatial intelligence for competitive analysis:
heatmaps, competitor density, market opportunity maps,
expansion paths, coverage analysis, city comparison,
region scoring, market saturation maps.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)

# Indian cities with coordinates and market data
CITY_DATA: dict[str, dict[str, Any]] = {
    "chennai": {"lat": 13.0827, "lon": 80.2707, "population": 10971000, "tier": 1, "state": "Tamil Nadu", "home_services_market": "high"},
    "mumbai": {"lat": 19.0760, "lon": 72.8777, "population": 20411000, "tier": 1, "state": "Maharashtra", "home_services_market": "high"},
    "delhi": {"lat": 28.7041, "lon": 77.1025, "population": 18980000, "tier": 1, "state": "Delhi", "home_services_market": "high"},
    "bangalore": {"lat": 12.9716, "lon": 77.5946, "population": 12349000, "tier": 1, "state": "Karnataka", "home_services_market": "high"},
    "hyderabad": {"lat": 17.3850, "lon": 78.4867, "population": 10004000, "tier": 1, "state": "Telangana", "home_services_market": "medium"},
    "pune": {"lat": 18.5204, "lon": 73.8567, "population": 7424000, "tier": 2, "state": "Maharashtra", "home_services_market": "medium"},
    "kolkata": {"lat": 22.5726, "lon": 88.3639, "population": 14850000, "tier": 1, "state": "West Bengal", "home_services_market": "medium"},
    "jaipur": {"lat": 26.9124, "lon": 75.7873, "population": 3960000, "tier": 2, "state": "Rajasthan", "home_services_market": "medium"},
    "ahmedabad": {"lat": 23.0225, "lon": 72.5714, "population": 8063000, "tier": 2, "state": "Gujarat", "home_services_market": "medium"},
    "lucknow": {"lat": 26.8467, "lon": 80.9462, "population": 3382000, "tier": 2, "state": "Uttar Pradesh", "home_services_market": "low"},
    "coimbatore": {"lat": 11.0168, "lon": 76.9558, "population": 1866000, "tier": 2, "state": "Tamil Nadu", "home_services_market": "low"},
    "madurai": {"lat": 9.9252, "lon": 78.1198, "population": 1465000, "tier": 3, "state": "Tamil Nadu", "home_services_market": "low"},
    "trichy": {"lat": 10.7905, "lon": 78.7047, "population": 917000, "tier": 3, "state": "Tamil Nadu", "home_services_market": "low"},
    "salem": {"lat": 11.6643, "lon": 78.1460, "population": 831000, "tier": 3, "state": "Tamil Nadu", "home_services_market": "low"},
    "tirunelveli": {"lat": 8.7139, "lon": 77.7567, "population": 474000, "tier": 3, "state": "Tamil Nadu", "home_services_market": "low"},
}

STATE_DATA: dict[str, dict[str, Any]] = {
    "Tamil Nadu": {"capital": "chennai", "population": 72147000, "gdp_per_capita": 25000, "urbanization": 0.48},
    "Maharashtra": {"capital": "mumbai", "population": 112374000, "gdp_per_capita": 28000, "urbanization": 0.45},
    "Karnataka": {"capital": "bangalore", "population": 61095000, "gdp_per_capita": 26000, "urbanization": 0.38},
    "Delhi": {"capital": "delhi", "population": 16788000, "gdp_per_capita": 35000, "urbanization": 0.97},
    "Telangana": {"capital": "hyderabad", "population": 35003000, "gdp_per_capita": 27000, "urbanization": 0.39},
    "West Bengal": {"capital": "kolkata", "population": 91276000, "gdp_per_capita": 15000, "urbanization": 0.32},
    "Rajasthan": {"capital": "jaipur", "population": 68548000, "gdp_per_capita": 16000, "urbanization": 0.25},
    "Gujarat": {"capital": "ahmedabad", "population": 60439000, "gdp_per_capita": 24000, "urbanization": 0.43},
    "Uttar Pradesh": {"capital": "lucknow", "population": 199812000, "gdp_per_capita": 11000, "urbanization": 0.22},
}


@dataclass
class CityScore:
    city: str
    state: str
    lat: float
    lon: float
    population: int
    tier: int
    competitor_count: int
    market_saturation: float
    opportunity_score: float
    coverage_level: str
    market_demand: str


@dataclass
class HeatmapPoint:
    lat: float
    lon: float
    intensity: float
    label: str
    value: float


class GeographicIntelligence:
    """Spatial intelligence engine for competitive analysis."""

    def __init__(self) -> None:
        self._competitor_cities: dict[int, list[str]] = {}
        self._city_competitors: dict[str, list[int]] = {}

    async def analyze(self, session: AsyncSession) -> dict[str, Any]:
        from sqlalchemy import select
        from app.database.models import Competitor, CompetitorService

        # Build competitor-city mapping
        self._competitor_cities.clear()
        self._city_competitors.clear()

        stmt = select(Competitor).where(Competitor.enabled.is_(True))
        competitors = (await session.execute(stmt)).scalars().all()

        for comp in competitors:
            cities = []
            for tag in (comp.tags or []):
                tag_lower = tag.lower()
                if tag_lower in CITY_DATA:
                    cities.append(tag_lower)
                    self._city_competitors.setdefault(tag_lower, []).append(comp.id)
            self._competitor_cities[comp.id] = cities

        return {
            "city_analysis": self._analyze_cities(),
            "heatmap": self._generate_heatmap(),
            "coverage": self._analyze_coverage(),
            "expansion_paths": self._suggest_expansion_paths(),
            "saturation_map": self._saturation_map(),
        }

    def _analyze_cities(self) -> list[CityScore]:
        scores = []
        for city, data in CITY_DATA.items():
            comp_count = len(self._city_competitors.get(city, []))
            total_competitors = max(sum(len(v) for v in self._city_competitors.values()), 1)
            saturation = comp_count / max(total_competitors, 1)
            opportunity = max(0, 1 - saturation) * (data["population"] / 20_000_000)
            coverage = "covered" if comp_count > 3 else "partial" if comp_count > 0 else "uncovered"
            demand = data["home_services_market"]

            scores.append(CityScore(
                city=city.title(), state=data["state"],
                lat=data["lat"], lon=data["lon"],
                population=data["population"], tier=data["tier"],
                competitor_count=comp_count,
                market_saturation=round(saturation, 3),
                opportunity_score=round(opportunity, 3),
                coverage_level=coverage, market_demand=demand,
            ))

        scores.sort(key=lambda x: x.opportunity_score, reverse=True)
        return scores

    def _generate_heatmap(self) -> list[HeatmapPoint]:
        points = []
        for city, data in CITY_DATA.items():
            comp_count = len(self._city_competitors.get(city, []))
            intensity = min(1.0, comp_count / 5.0)
            points.append(HeatmapPoint(
                lat=data["lat"], lon=data["lon"],
                intensity=round(intensity, 3),
                label=f"{city.title()} ({comp_count} competitors)",
                value=comp_count,
            ))
        return points

    def _analyze_coverage(self) -> dict[str, Any]:
        covered = [c for c in CITY_DATA if self._city_competitors.get(c)]
        uncovered = [c for c in CITY_DATA if not self._city_competitors.get(c)]
        return {
            "covered_cities": [{"city": c.title(), "competitors": len(self._city_competitors.get(c, []))} for c in covered],
            "uncovered_cities": [c.title() for c in uncovered],
            "coverage_percentage": round(len(covered) / max(len(CITY_DATA), 1) * 100, 1),
        }

    def _suggest_expansion_paths(self) -> list[dict[str, Any]]:
        paths = []
        for city, data in CITY_DATA.items():
            comp_count = len(self._city_competitors.get(city, []))
            if comp_count < 2:
                score = data["population"] / 20_000_000
                paths.append({
                    "city": city.title(),
                    "state": data["state"],
                    "tier": data["tier"],
                    "priority_score": round(score, 3),
                    "reason": f"Low competition ({comp_count} competitors), {data['home_services_market']} demand",
                })
        paths.sort(key=lambda x: x["priority_score"], reverse=True)
        return paths

    def _saturation_map(self) -> list[dict[str, Any]]:
        saturation = []
        for city, data in CITY_DATA.items():
            comp_count = len(self._city_competitors.get(city, []))
            max_expected = data["population"] / 500_000
            sat = min(1.0, comp_count / max(max_expected, 1))
            level = "high" if sat > 0.7 else "medium" if sat > 0.3 else "low"
            saturation.append({
                "city": city.title(),
                "saturation": round(sat, 3),
                "level": level,
                "competitors": comp_count,
                "expected_capacity": int(max_expected),
            })
        saturation.sort(key=lambda x: x["saturation"], reverse=True)
        return saturation

    def city_comparison(self, cities: list[str]) -> list[dict[str, Any]]:
        comparison = []
        for city in cities:
            data = CITY_DATA.get(city.lower(), CITY_DATA.get(city.lower().replace(" ", "")))
            if not data:
                continue
            comp_count = len(self._city_competitors.get(city.lower(), []))
            comparison.append({
                "city": city.title(),
                "state": data["state"],
                "population": data["population"],
                "tier": data["tier"],
                "competitor_count": comp_count,
                "market_demand": data["home_services_market"],
            })
        return comparison

    def get_map_data(self) -> dict[str, Any]:
        return {
            "cities": [
                {"name": city.title(), "lat": data["lat"], "lon": data["lon"],
                 "tier": data["tier"], "population": data["population"],
                 "competitors": len(self._city_competitors.get(city, [])),
                 "state": data["state"]}
                for city, data in CITY_DATA.items()
            ],
            "states": [
                {"name": state, "capital": data["capital"],
                 "population": data["population"],
                 "gdp_per_capita": data["gdp_per_capita"]}
                for state, data in STATE_DATA.items()
            ],
        }


geo_intelligence = GeographicIntelligence()
