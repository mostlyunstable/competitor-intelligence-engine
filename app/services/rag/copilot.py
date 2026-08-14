"""Executive AI Copilot — LLM-powered conversational assistant."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


@dataclass
class ConversationTurn:
    role: str
    content: str
    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class CopilotResponse:
    answer: str
    confidence: float
    sources: list[dict[str, Any]]
    suggested_follow_ups: list[str]
    conversation_id: str


_UNSET = object()


class ExecutiveCopilot:
    """LLM-powered assistant for competitive intelligence queries."""

    def __init__(self) -> None:
        self._conversations: dict[str, list[ConversationTurn]] = {}
        self._provider: Any = _UNSET

    def _get_provider(self):
        if self._provider is _UNSET:
            try:
                from app.ai.infrastructure.providers.openai_provider import OpenAIProvider
                self._provider = OpenAIProvider()
            except Exception:
                logger.warning("llm_provider_unavailable")
                return None
        return self._provider if self._provider is not _UNSET else None

    def _classify_intent(self, question: str) -> str:
        q = question.lower()
        if any(w in q for w in ["compare", "versus", "vs", "difference"]):
            return "comparison"
        if any(w in q for w in ["grow", "growth", "forecast", "predict", "future"]):
            return "growth"
        if any(w in q for w in ["risk", "threat", "danger", "concern"]):
            return "risk"
        if any(w in q for w in ["recommend", "suggest", "strategy", "should"]):
            return "recommendation"
        if any(w in q for w in ["price", "pricing", "cost", "expensive", "cheap"]):
            return "pricing"
        if any(w in q for w in ["expand", "expansion", "new market", "city", "region"]):
            return "expansion"
        if any(w in q for w in ["report", "summary", "overview", "executive"]):
            return "report"
        if any(w in q for w in ["opportunity", "opportunities", "gap", "chance"]):
            return "opportunity"
        return "general"

    def _get_or_create_conversation(self, conversation_id: str | None) -> tuple[str, list[ConversationTurn]]:
        if conversation_id and conversation_id in self._conversations:
            return conversation_id, self._conversations[conversation_id]
        cid = conversation_id or f"conv_{datetime.now(UTC).strftime('%Y%m%d_%H%M%S')}"
        self._conversations[cid] = []
        return cid, self._conversations[cid]

    async def ask(
        self,
        question: str,
        conversation_id: str | None = None,
        session: AsyncSession | None = None,
    ) -> CopilotResponse:
        cid, history = self._get_or_create_conversation(conversation_id)
        history.append(ConversationTurn(role="user", content=question))

        context = await self._gather_context(question, session)

        provider = self._get_provider()
        if provider:
            answer = await self._llm_answer(question, context, history, provider)
        else:
            answer = self._fallback_answer(question, context)

        sources = [
            {"type": ctx.get("source_type", "data"), "id": ctx.get("source_id"), "relevance": ctx.get("score", 0.5)}
            for ctx in context.get("evidence", [])
        ]

        follow_ups = self._suggest_follow_ups(question)
        confidence = min(0.95, 0.6 + len(context.get("evidence", [])) * 0.05)

        turn = ConversationTurn(role="assistant", content=answer, metadata={"confidence": confidence})
        history.append(turn)

        return CopilotResponse(
            answer=answer, confidence=confidence, sources=sources,
            suggested_follow_ups=follow_ups, conversation_id=cid,
        )

    async def _gather_context(self, question: str, session: AsyncSession | None) -> dict[str, Any]:
        evidence: list[dict[str, Any]] = []

        if not session:
            return {"question": question, "evidence": evidence}

        try:
            from sqlalchemy import text

            # Gather competitor summary
            r = await session.execute(text("""
                SELECT c.id, c.name,
                       (SELECT COUNT(*) FROM competitor_services WHERE competitor_id = c.id) as services,
                       (SELECT COUNT(*) FROM competitor_pricing WHERE competitor_id = c.id) as pricing,
                       (SELECT COUNT(*) FROM competitor_content WHERE competitor_id = c.id) as content,
                       (SELECT COUNT(*) FROM change_logs WHERE competitor_id = c.id) as changes
                FROM competitors c WHERE c.enabled = true ORDER BY c.id
            """))
            competitors = []
            for row in r.fetchall():
                competitors.append({
                    "id": row.id, "name": row.name,
                    "services": row.services, "pricing": row.pricing,
                    "content": row.content, "changes": row.changes,
                })
            if competitors:
                evidence.append({
                    "source_type": "competitors",
                    "content": json.dumps(competitors, default=str),
                    "score": 0.9,
                })

            # Gather top services per competitor
            r1b = await session.execute(text("""
                SELECT c.name, cs.service_name, cs.starting_price, cs.description
                FROM competitor_services cs JOIN competitors c ON c.id = cs.competitor_id
                WHERE c.enabled = true
                ORDER BY c.id, cs.starting_price DESC NULLS LAST
            """))
            svc_by_comp: dict[str, list] = {}
            for row in r1b.fetchall():
                name = row.name
                if name not in svc_by_comp:
                    svc_by_comp[name] = []
                if len(svc_by_comp[name]) < 5:
                    svc_by_comp[name].append({
                        "service": row.service_name,
                        "price": float(row.starting_price) if row.starting_price else None,
                        "desc": (row.description or "")[:100],
                    })
            if svc_by_comp:
                evidence.append({
                    "source_type": "services",
                    "content": json.dumps(svc_by_comp, default=str),
                    "score": 0.85,
                })

            # Gather pricing per competitor
            r1c = await session.execute(text("""
                SELECT c.name, cp.service_name, cp.base_price, cp.category, cp.currency
                FROM competitor_pricing cp JOIN competitors c ON c.id = cp.competitor_id
                WHERE c.enabled = true
                ORDER BY c.id, cp.base_price DESC NULLS LAST
            """))
            prc_by_comp: dict[str, list] = {}
            for row in r1c.fetchall():
                name = row.name
                if name not in prc_by_comp:
                    prc_by_comp[name] = []
                if len(prc_by_comp[name]) < 5:
                    prc_by_comp[name].append({
                        "item": row.service_name,
                        "price": float(row.base_price) if row.base_price else None,
                        "category": row.category,
                        "currency": row.currency or "INR",
                    })
            if prc_by_comp:
                evidence.append({
                    "source_type": "pricing",
                    "content": json.dumps(prc_by_comp, default=str),
                    "score": 0.85,
                })

            # Gather recent predictions
            r2 = await session.execute(text("""
                SELECT prediction_type, competitor_id, prediction_data, confidence_score, created_at
                FROM competitor_predictions ORDER BY created_at DESC LIMIT 20
            """))
            predictions = []
            for row in r2.fetchall():
                predictions.append({
                    "type": row.prediction_type,
                    "competitor_id": row.competitor_id,
                    "data": str(row.prediction_data)[:200] if row.prediction_data else "",
                    "confidence": float(row.confidence_score) if row.confidence_score else 0,
                    "date": str(row.created_at)[:10] if row.created_at else "",
                })
            if predictions:
                evidence.append({
                    "source_type": "predictions",
                    "content": json.dumps(predictions, default=str),
                    "score": 0.8,
                })

            # Gather recent changes
            r3 = await session.execute(text("""
                SELECT cl.competitor_id, c.name, cl.change_type, cl.data_type, cl.details, cl.detected_at
                FROM change_logs cl JOIN competitors c ON c.id = cl.competitor_id
                ORDER BY cl.detected_at DESC LIMIT 15
            """))
            changes = []
            for row in r3.fetchall():
                changes.append({
                    "competitor": row.name,
                    "type": row.change_type,
                    "data_type": row.data_type,
                    "details": str(row.details)[:150] if row.details else "",
                    "date": str(row.detected_at)[:10] if row.detected_at else "",
                })
            if changes:
                evidence.append({
                    "source_type": "changes",
                    "content": json.dumps(changes, default=str),
                    "score": 0.7,
                })

        except Exception as e:
            logger.warning("context_gathering_failed", error=str(e))

        return {"question": question, "evidence": evidence}

    async def _llm_answer(self, question: str, context: dict[str, Any], history: list[ConversationTurn], provider: Any) -> str:
        evidence = context.get("evidence", [])
        evidence_text = ""
        for e in evidence[:8]:
            evidence_text += f"\n[{e.get('source_type', 'data')}]:\n{e.get('content', '')[:800]}\n"

        history_text = ""
        for turn in history[-6:]:
            prefix = "User" if turn.role == "user" else "Assistant"
            history_text += f"{prefix}: {turn.content[:500]}\n"

        system_prompt = """You are a senior competitive intelligence analyst for a home services company operating in Chennai, India. You have access to real competitor data including services offered, pricing, market predictions, recent changes, and industry benchmarks.

Your role: Provide deep, actionable business intelligence. Don't just list data — analyze it, find patterns, and give strategic recommendations.

SUPPORTED markdown (use ONLY these):
- **bold text** for key findings and competitor names
- *italic text* for strategic implications
- `code` for numbers, prices, percentages
- ### Header for sections
- | Col | Col | for tables (first row = headers, second row = --- separator)
- - item for bullet lists
- 1. item for numbered lists
- > quote for callouts
- --- for section dividers

DO NOT use: ####, ~~, [], (), or any other markdown syntax.

Analysis framework:
1. **What the data shows** — specific numbers and facts
2. **What it means** — patterns, trends, implications
3. **What to do** — concrete next steps"""

        user_prompt = f"""Here is the competitive intelligence data available:

{evidence_text}

Previous conversation:
{history_text}

Question: {question}

Provide a deep, structured analysis. Use tables for comparisons, bold for key findings, and end with actionable recommendations."""

        try:
            response = await provider._client.post(
                "/v1/responses",
                json={
                    "model": provider.model_name,
                    "input": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "temperature": 0.3,
                    "max_output_tokens": 2048,
                },
            )

            if response.status_code != 200:
                logger.error("llm_copilot_failed", status=response.status_code)
                return self._fallback_answer(question, context)

            data = response.json()
            content = ""
            for output_item in data.get("output", []):
                if output_item.get("type") == "message":
                    for content_item in output_item.get("content", []):
                        if content_item.get("type") == "output_text":
                            content = content_item.get("text", "")
                            break

            return content or self._fallback_answer(question, context)

        except Exception as e:
            logger.warning("llm_call_failed", error=str(e))
            return self._fallback_answer(question, context)

    def _fallback_answer(self, question: str, context: dict[str, Any]) -> str:
        evidence = context.get("evidence", [])
        if not evidence:
            return f"I don't have enough data to answer that. Try collecting more competitor data first."
        evidence_text = "\n".join(f"- [{e.get('source_type')}] {e.get('content', '')[:200]}" for e in evidence[:3])
        return f"Based on available data (LLM unavailable):\n\n{evidence_text}"

    def _suggest_follow_ups(self, question: str, _unused: str = "") -> list[str]:
        q = question.lower()
        if any(w in q for w in ["compare", "versus", "vs"]):
            return ["Which competitor is growing fastest?", "What are the pricing differences?"]
        if any(w in q for w in ["price", "pricing", "cost"]):
            return ["How do our prices compare?", "What pricing gaps exist?"]
        if any(w in q for w in ["risk", "threat"]):
            return ["How can we mitigate these risks?", "What's the timeline?"]
        if any(w in q for w in ["grow", "expansion", "expand"]):
            return ["Which city should we target?", "What's the market size?"]
        return ["Which competitor should I worry about most?", "What are the latest market trends?", "Summarize the competitive landscape"]

    def get_conversation_history(self, conversation_id: str) -> list[dict[str, str]]:
        return [{"role": t.role, "content": t.content, "timestamp": t.timestamp} for t in self._conversations.get(conversation_id, [])]

    def list_conversations(self) -> list[dict[str, Any]]:
        return [
            {"id": cid, "turns": len(turns), "last_message": turns[-1].timestamp if turns else None}
            for cid, turns in self._conversations.items()
        ]


executive_copilot = ExecutiveCopilot()
