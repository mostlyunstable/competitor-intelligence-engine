"""Specific Competitor-vs-Competitor Comparison Service."""

from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.models import (
    Competitor,
    CompetitorAIInsight,
    CompetitorPricing,
    CompetitorService,
)


class ComparisonService:
    async def compare(
        self, session: AsyncSession, comp_a_id: int, comp_b_id: int
    ) -> dict[str, Any]:
        """Independently retrieves A and B, and calculates a specific comparison."""

        comp_a = await self._get_competitor_data(session, comp_a_id)
        comp_b = await self._get_competitor_data(session, comp_b_id)

        if not comp_a or not comp_b:
            return {"error": "One or both competitors not found"}

        a_service_names = {s["name"].lower() for s in comp_a["services"]}
        b_service_names = {s["name"].lower() for s in comp_b["services"]}

        shared_services = list(a_service_names.intersection(b_service_names))
        a_exclusive = list(a_service_names - b_service_names)
        b_exclusive = list(b_service_names - a_service_names)

        a_pricing = {
            p["name"].lower(): p["price"] for p in comp_a["pricing"] if p["price"] is not None
        }
        b_pricing = {
            p["name"].lower(): p["price"] for p in comp_b["pricing"] if p["price"] is not None
        }

        price_comparison = []
        for service in shared_services:
            if service in a_pricing and service in b_pricing:
                price_comparison.append(
                    {
                        "service": service,
                        "competitor_a_price": float(a_pricing[service]),
                        "competitor_b_price": float(b_pricing[service]),
                        "difference": float(a_pricing[service] - b_pricing[service]),
                    }
                )

        return {
            "competitor_a": {
                "id": comp_a["competitor"].id,
                "name": comp_a["competitor"].name,
                "summary": comp_a["insight"].summary
                if comp_a["insight"]
                else "No AI insight available",
                "key_differentiators": comp_a["insight"].key_differentiators
                if comp_a["insight"]
                else [],
            },
            "competitor_b": {
                "id": comp_b["competitor"].id,
                "name": comp_b["competitor"].name,
                "summary": comp_b["insight"].summary
                if comp_b["insight"]
                else "No AI insight available",
                "key_differentiators": comp_b["insight"].key_differentiators
                if comp_b["insight"]
                else [],
            },
            "comparison": {
                "shared_services": shared_services,
                "competitor_a_exclusive_services": a_exclusive,
                "competitor_b_exclusive_services": b_exclusive,
                "price_comparison": price_comparison,
            },
        }

    async def _get_competitor_data(
        self, session: AsyncSession, competitor_id: int
    ) -> dict[str, Any] | None:
        comp = await session.get(Competitor, competitor_id)
        if not comp:
            return None

        services_res = await session.execute(
            select(CompetitorService).where(CompetitorService.competitor_id == competitor_id)
        )
        services = [{"name": s.service_name} for s in services_res.scalars().all()]

        pricing_res = await session.execute(
            select(CompetitorPricing).where(CompetitorPricing.competitor_id == competitor_id)
        )
        pricing = [
            {"service": p.service_name, "name": p.service_name, "price": p.base_price} for p in pricing_res.scalars().all()
        ]

        insight_res = await session.execute(
            select(CompetitorAIInsight).where(CompetitorAIInsight.competitor_id == competitor_id)
        )
        insight = insight_res.scalar_one_or_none()

        return {"competitor": comp, "services": services, "pricing": pricing, "insight": insight}


comparison_service = ComparisonService()
