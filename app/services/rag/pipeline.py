"""Retrieval-Augmented Generation (RAG) Pipeline.

Semantic search, vector embeddings, hybrid retrieval,
context assembly, and natural-language querying.
"""

from __future__ import annotations

import hashlib
import math
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


@dataclass
class DocumentChunk:
    id: str
    source_type: str
    source_id: int
    content: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class SearchResult:
    chunk: DocumentChunk
    score: float
    match_type: str  # "semantic", "keyword", "hybrid"


@dataclass
class RAGResponse:
    answer: str
    sources: list[dict[str, Any]]
    confidence: float
    evidence: list[str]


def _simple_hash_embedding(text: str, dim: int = 128) -> list[float]:
    """Deterministic pseudo-embedding from text hash. Replace with real model in production."""
    h = hashlib.sha512(text.lower().encode()).digest()
    embedding = []
    for i in range(0, min(len(h), dim * 4), 4):
        val = int.from_bytes(h[i:i+4], "big") / 0xFFFFFFFF
        embedding.append(val * 2 - 1)
    while len(embedding) < dim:
        embedding.append(0.0)
    norm = math.sqrt(sum(x * x for x in embedding[:dim]))
    if norm > 0:
        embedding = [x / norm for x in embedding[:dim]]
    return embedding[:dim]


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b) or not a:
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(x * x for x in b))
    return dot / (na * nb) if na > 0 and nb > 0 else 0.0


class RAGPipeline:
    """Semantic search and RAG pipeline for competitive intelligence."""

    def __init__(self) -> None:
        self._chunks: dict[str, DocumentChunk] = {}
        self._keyword_index: dict[str, set[str]] = defaultdict(set)
        self._source_type_index: dict[str, set[str]] = defaultdict(set)
        self._last_indexed: datetime | None = None

    async def index_all(self, session: AsyncSession) -> dict[str, int]:
        """Index all available data into the vector store."""
        from sqlalchemy import select
        from app.database.models import (
            Competitor, CompetitorContent, CompetitorService,
            CompetitorPricing, CompetitorAIInsight,
        )

        self._chunks.clear()
        self._keyword_index.clear()
        self._source_type_index.clear()
        stats: dict[str, int] = defaultdict(int)

        # ── AI Insights ──
        stmt = select(CompetitorAIInsight)
        insights = (await session.execute(stmt)).scalars().all()
        for insight in insights:
            if insight.summary:
                chunk = self._make_chunk(
                    source_type="ai_insight", source_id=insight.id,
                    content=insight.summary,
                    metadata={"competitor_id": insight.competitor_id, "market_position": insight.market_position},
                )
                stats["ai_insights"] += 1

            if insight.recommendations:
                for i, rec in enumerate(insight.recommendations if isinstance(insight.recommendations, list) else []):
                    chunk = self._make_chunk(
                        source_type="recommendation", source_id=insight.id,
                        content=str(rec),
                        metadata={"competitor_id": insight.competitor_id, "index": i},
                    )
                    stats["recommendations"] += 1

        # ── Content ──
        stmt = select(CompetitorContent)
        contents = (await session.execute(stmt)).scalars().all()
        for content in contents:
            text = f"{content.title or ''} {content.summary or ''} {(content.raw_content or '')[:1000]}"
            if text.strip():
                self._make_chunk(
                    source_type="content", source_id=content.id,
                    content=text.strip(),
                    metadata={"competitor_id": content.competitor_id, "content_type": content.content_type, "url": content.url},
                )
                stats["content"] += 1

        # ── Services ──
        stmt = select(CompetitorService)
        services = (await session.execute(stmt)).scalars().all()
        for svc in services:
            text = f"{svc.service_name}: {svc.description or ''} Category: {svc.service_category or ''}"
            if text.strip():
                self._make_chunk(
                    source_type="service", source_id=svc.id,
                    content=text.strip(),
                    metadata={"competitor_id": svc.competitor_id, "category": svc.service_category, "price": svc.starting_price},
                )
                stats["services"] += 1

        # ── Pricing ──
        stmt = select(CompetitorPricing)
        pricings = (await session.execute(stmt)).scalars().all()
        for prc in pricings:
            text = f"{prc.service_name}: {prc.currency} {prc.base_price}"
            if prc.promotional_price:
                text += f" (promo: {prc.promotional_price})"
            self._make_chunk(
                source_type="pricing", source_id=prc.id,
                content=text,
                metadata={"competitor_id": prc.competitor_id, "category": prc.category, "price": prc.base_price},
            )
            stats["pricing"] += 1

        # ── Competitors ──
        stmt = select(Competitor)
        competitors = (await session.execute(stmt)).scalars().all()
        for comp in competitors:
            text = f"{comp.name}: website={comp.website_url} tags={', '.join(comp.tags or [])}"
            self._make_chunk(
                source_type="competitor", source_id=comp.id,
                content=text,
                metadata={"competitor_id": comp.id, "name": comp.name},
            )
            stats["competitors"] += 1

        self._last_indexed = datetime.now(UTC)
        logger.info("rag_indexed", total_chunks=len(self._chunks), stats=dict(stats))
        return dict(stats)

    def _make_chunk(self, source_type: str, source_id: int, content: str, metadata: dict[str, Any]) -> DocumentChunk:
        chunk_id = f"{source_type}:{source_id}:{hashlib.md5(content[:200].encode()).hexdigest()[:8]}"
        chunk = DocumentChunk(
            id=chunk_id, source_type=source_type, source_id=source_id,
            content=content[:2000], metadata=metadata,
            embedding=_simple_hash_embedding(content),
        )
        self._chunks[chunk_id] = chunk
        self._source_type_index[source_type].add(chunk_id)
        for word in set(content.lower().split()):
            if len(word) > 2:
                self._keyword_index[word].add(chunk_id)
        return chunk

    def search(self, query: str, limit: int = 10, source_types: list[str] | None = None) -> list[SearchResult]:
        """Hybrid search: semantic + keyword."""
        query_embedding = _simple_hash_embedding(query)
        query_words = set(query.lower().split())

        # Semantic search
        semantic_scores: dict[str, float] = {}
        for cid, chunk in self._chunks.items():
            if source_types and chunk.source_type not in source_types:
                continue
            semantic_scores[cid] = _cosine_similarity(query_embedding, chunk.embedding)

        # Keyword search
        keyword_scores: dict[str, float] = defaultdict(float)
        for word in query_words:
            for cid in self._keyword_index.get(word, set()):
                if not source_types or self._chunks[cid].source_type in source_types:
                    keyword_scores[cid] += 1.0 / max(len(query_words), 1)

        # Combine
        all_ids = set(semantic_scores.keys()) | set(keyword_scores.keys())
        results: list[SearchResult] = []
        for cid in all_ids:
            sem = semantic_scores.get(cid, 0.0)
            kw = keyword_scores.get(cid, 0.0)
            hybrid = 0.6 * sem + 0.4 * kw
            match_type = "hybrid" if sem > 0.1 and kw > 0.1 else "semantic" if sem > kw else "keyword"
            results.append(SearchResult(chunk=self._chunks[cid], score=hybrid, match_type=match_type))

        results.sort(key=lambda x: x.score, reverse=True)
        return results[:limit]

    def retrieve_context(self, query: str, limit: int = 5) -> list[dict[str, Any]]:
        """Retrieve context chunks for RAG answering."""
        results = self.search(query, limit=limit)
        return [
            {
                "content": r.chunk.content,
                "source_type": r.chunk.source_type,
                "source_id": r.chunk.source_id,
                "score": round(r.score, 4),
                "metadata": r.chunk.metadata,
            }
            for r in results
        ]

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_chunks": len(self._chunks),
            "by_source_type": {t: len(ids) for t, ids in self._source_type_index.items()},
            "vocabulary_size": len(self._keyword_index),
            "last_indexed": self._last_indexed.isoformat() if self._last_indexed else None,
        }


rag_pipeline = RAGPipeline()
