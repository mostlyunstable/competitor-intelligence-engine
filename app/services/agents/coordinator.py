"""Multi-Agent Intelligence Architecture.

Specialized AI agents for different intelligence domains.
Coordinator merges results from all agents.
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Callable, Coroutine, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class AgentType(str, Enum):
    MARKET_RESEARCH = "market_research"
    PRICING = "pricing"
    GROWTH_FORECAST = "growth_forecast"
    RISK = "risk"
    OPPORTUNITY = "opportunity"
    BENCHMARK = "benchmark"
    COORDINATOR = "coordinator"


@dataclass
class AgentResult:
    agent_type: AgentType
    status: str
    data: dict[str, Any]
    confidence: float = 0.0
    execution_time_ms: float = 0.0
    error: str | None = None


@dataclass
class CoordinatedResult:
    results: dict[str, AgentResult]
    merged_summary: str
    overall_confidence: float
    execution_time_ms: float
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


class BaseAgent:
    agent_type: AgentType
    _handler: Callable[..., Coroutine[Any, Any, dict[str, Any]]] | None = None

    def __init__(self, agent_type: AgentType) -> None:
        self.agent_type = agent_type

    async def execute(self, session: AsyncSession, params: dict[str, Any] | None = None) -> AgentResult:
        start = datetime.now(UTC)
        try:
            if self._handler:
                data = await self._handler(session, params)
            else:
                data = await self._default_execute(session, params)
            elapsed = (datetime.now(UTC) - start).total_seconds() * 1000
            return AgentResult(
                agent_type=self.agent_type, status="success",
                data=data, confidence=data.get("_confidence", 0.7),
                execution_time_ms=elapsed,
            )
        except Exception as exc:
            elapsed = (datetime.now(UTC) - start).total_seconds() * 1000
            logger.warning("agent_failed", agent=self.agent_type.value, error=str(exc))
            return AgentResult(
                agent_type=self.agent_type, status="error",
                data={}, error=str(exc), execution_time_ms=elapsed,
            )

    async def _default_execute(self, session: AsyncSession, params: dict[str, Any] | None) -> dict[str, Any]:
        return {"_confidence": 0.5, "message": f"{self.agent_type.value} agent: no handler configured"}


class MarketResearchAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(AgentType.MARKET_RESEARCH)

    async def _default_execute(self, session: AsyncSession, params: dict[str, Any] | None) -> dict[str, Any]:
        from sqlalchemy import select, func
        from app.database.models import Competitor, CompetitorContent, CompetitorService

        total = (await session.execute(select(func.count()).select_from(Competitor).where(Competitor.enabled.is_(True)))).scalar() or 0
        svc_count = (await session.execute(select(func.count()).select_from(CompetitorService))).scalar() or 0
        content_count = (await session.execute(select(func.count()).select_from(CompetitorContent))).scalar() or 0

        return {
            "active_competitors": total,
            "total_services": svc_count,
            "total_content": content_count,
            "market_summary": f"Tracking {total} competitors with {svc_count} services and {content_count} content pieces",
            "_confidence": 0.8,
        }


class PricingAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(AgentType.PRICING)

    async def _default_execute(self, session: AsyncSession, params: dict[str, Any] | None) -> dict[str, Any]:
        from sqlalchemy import select, func
        from app.database.models import CompetitorPricing

        total = (await session.execute(select(func.count()).select_from(CompetitorPricing))).scalar() or 0
        avg_price_stmt = select(func.avg(CompetitorPricing.base_price)).where(CompetitorPricing.base_price > 0)
        avg_price = (await session.execute(avg_price_stmt)).scalar()

        return {
            "total_pricing_entries": total,
            "average_price": round(float(avg_price or 0), 2),
            "pricing_summary": f"{total} pricing entries tracked, average ₹{avg_price:.0f}" if avg_price else f"{total} pricing entries tracked",
            "_confidence": 0.7,
        }


class GrowthForecastAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(AgentType.GROWTH_FORECAST)

    async def _default_execute(self, session: AsyncSession, params: dict[str, Any] | None) -> dict[str, Any]:
        from app.services.predictions.growth import growth_forecaster
        forecasts = await growth_forecaster.forecast_all(session)
        high_growth = [f for f in forecasts if f.get("growth_level") == "high"]
        return {
            "total_forecasts": len(forecasts),
            "high_growth_count": len(high_growth),
            "high_growth_competitors": [f.get("competitor_name") for f in high_growth[:5]],
            "_confidence": 0.75,
        }


class RiskAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(AgentType.RISK)

    async def _default_execute(self, session: AsyncSession, params: dict[str, Any] | None) -> dict[str, Any]:
        from app.services.predictions.risks import risk_analyzer
        risks = await risk_analyzer.analyze_all(session)
        high_risks = [r for r in risks if r.get("risk_level") == "high"]
        return {
            "total_risks": len(risks),
            "high_risk_count": len(high_risks),
            "risk_types": list(set(r.get("risk_type") for r in risks)),
            "_confidence": 0.7,
        }


class OpportunityAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(AgentType.OPPORTUNITY)

    async def _default_execute(self, session: AsyncSession, params: dict[str, Any] | None) -> dict[str, Any]:
        from app.services.predictions.opportunities import opportunity_detector
        opps = await opportunity_detector.detect(session)
        return {
            "total_opportunities": len(opps),
            "high_priority": len([o for o in opps if o.get("priority") == "high"]),
            "types": list(set(o.get("opportunity_type") for o in opps)),
            "_confidence": 0.65,
        }


class BenchmarkAgent(BaseAgent):
    def __init__(self) -> None:
        super().__init__(AgentType.BENCHMARK)

    async def _default_execute(self, session: AsyncSession, params: dict[str, Any] | None) -> dict[str, Any]:
        from app.services.predictions.benchmarking import predictive_benchmarker
        benchmarks = await predictive_benchmarker.benchmark_all(session)
        return {
            "total_benchmarks": len(benchmarks),
            "top_performer": benchmarks[0]["competitor_name"] if benchmarks else None,
            "average_growth_score": round(sum(b["growth_score"] for b in benchmarks) / max(len(benchmarks), 1), 2),
            "_confidence": 0.75,
        }


class CoordinatorAgent:
    """Merges results from all specialized agents."""

    def __init__(self) -> None:
        self._agents: dict[AgentType, BaseAgent] = {
            AgentType.MARKET_RESEARCH: MarketResearchAgent(),
            AgentType.PRICING: PricingAgent(),
            AgentType.GROWTH_FORECAST: GrowthForecastAgent(),
            AgentType.RISK: RiskAgent(),
            AgentType.OPPORTUNITY: OpportunityAgent(),
            AgentType.BENCHMARK: BenchmarkAgent(),
        }

    async def coordinate(
        self,
        session: AsyncSession,
        agent_types: list[AgentType] | None = None,
        params: dict[str, Any] | None = None,
    ) -> CoordinatedResult:
        import time
        start = time.monotonic()

        types_to_run = agent_types or list(self._agents.keys())
        agents = [self._agents[t] for t in types_to_run if t in self._agents]

        tasks = [agent.execute(session, params) for agent in agents]
        results_list = await asyncio.gather(*tasks, return_exceptions=True)

        results: dict[str, AgentResult] = {}
        for agent, result in zip(agents, results_list):
            if isinstance(result, Exception):
                results[agent.agent_type.value] = AgentResult(
                    agent_type=agent.agent_type, status="error",
                    data={}, error=str(result),
                )
            else:
                results[agent.agent_type.value] = result

        successful = [r for r in results.values() if r.status == "success"]
        overall_confidence = sum(r.confidence for r in successful) / max(len(successful), 1)

        merged = self._merge_results(results)
        elapsed = (time.monotonic() - start) * 1000

        return CoordinatedResult(
            results=results, merged_summary=merged,
            overall_confidence=overall_confidence, execution_time_ms=elapsed,
        )

    def _merge_results(self, results: dict[str, AgentResult]) -> str:
        parts = []
        for name, result in results.items():
            if result.status == "success":
                summary = result.data.get(f"{name}_summary", result.data.get("market_summary", result.data.get("pricing_summary", "")))
                if summary:
                    parts.append(f"**{name.replace('_', ' ').title()}**: {summary}")
                elif result.data:
                    key_items = [f"{k}: {v}" for k, v in result.data.items() if not k.startswith("_") and isinstance(v, (str, int, float))]
                    if key_items:
                        parts.append(f"**{name.replace('_', ' ').title()}**: {', '.join(key_items[:3])}")
            else:
                parts.append(f"**{name.replace('_', ' ').title()}**: Error - {result.error}")
        return "\n\n".join(parts) if parts else "No results available."


coordinator = CoordinatorAgent()
