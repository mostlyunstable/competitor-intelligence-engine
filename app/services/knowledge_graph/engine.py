"""Knowledge Graph Intelligence Engine.

In-memory graph database for competitor intelligence.
Builds graph from existing DB data, supports traversal,
relationship discovery, influence detection, and market clustering.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Any, TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


class EntityType(str, Enum):
    COMPETITOR = "competitor"
    SERVICE = "service"
    CITY = "city"
    STATE = "state"
    PRICING = "pricing"
    CATEGORY = "category"
    TECHNOLOGY = "technology"
    CONTENT = "content"
    SOCIAL = "social"
    REPORT = "report"


class RelationshipType(str, Enum):
    OFFERS = "offers"
    OPERATES_IN = "operates_in"
    COMPETES_WITH = "competes_with"
    USES = "uses"
    MENTIONS = "mentions"
    OWNS = "owns"
    LOCATED_IN = "located_in"
    EXPANDED_TO = "expanded_to"
    PRICED_AT = "priced_at"


@dataclass
class GraphNode:
    id: str
    entity_type: EntityType
    name: str
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class GraphEdge:
    source_id: str
    target_id: str
    relationship: RelationshipType
    weight: float = 1.0
    properties: dict[str, Any] = field(default_factory=dict)
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())


@dataclass
class GraphPath:
    nodes: list[str]
    edges: list[GraphEdge]
    total_weight: float = 0.0


class KnowledgeGraph:
    """In-memory graph engine for competitive intelligence."""

    def __init__(self) -> None:
        self._nodes: dict[str, GraphNode] = {}
        self._edges: list[GraphEdge] = []
        self._adjacency: dict[str, list[GraphEdge]] = defaultdict(list)
        self._reverse_adjacency: dict[str, list[GraphEdge]] = defaultdict(list)
        self._type_index: dict[EntityType, set[str]] = defaultdict(set)
        self._name_index: dict[str, str] = {}
        self._built_at: datetime | None = None

    async def build_from_database(self, session: AsyncSession) -> dict[str, int]:
        """Build the graph from all existing database data."""
        from sqlalchemy import select
        from app.database.models import (
            Competitor, CompetitorService, CompetitorPricing,
            CompetitorContent, CompetitorSocial, ChangeLog,
        )

        self._nodes.clear()
        self._edges.clear()
        self._adjacency.clear()
        self._reverse_adjacency.clear()
        self._type_index.clear()
        self._name_index.clear()

        stats = {"nodes": 0, "edges": 0}

        # ── Competitors ──
        stmt = select(Competitor).where(Competitor.enabled.is_(True))
        competitors = (await session.execute(stmt)).scalars().all()
        for comp in competitors:
            nid = f"competitor:{comp.id}"
            self._add_node(GraphNode(
                id=nid, entity_type=EntityType.COMPETITOR,
                name=comp.name,
                properties={"website_url": comp.website_url, "tags": comp.tags or [], "modules": comp.modules or []},
            ))
            stats["nodes"] += 1

            # Extract cities/states from tags
            for tag in (comp.tags or []):
                tag_lower = tag.lower()
                if any(c in tag_lower for c in ["chennai", "mumbai", "delhi", "bangalore", "hyderabad", "pune", "kolkata", "jaipur", "ahmedabad", "lucknow"]):
                    city_nid = f"city:{tag_lower}"
                    self._add_node(GraphNode(id=city_nid, entity_type=EntityType.CITY, name=tag.title()))
                    self._add_edge(GraphEdge(source_id=nid, target_id=city_nid, relationship=RelationshipType.OPERATES_IN))
                    stats["edges"] += 1

        # ── Services → Categories ──
        stmt = select(CompetitorService)
        services = (await session.execute(stmt)).scalars().all()
        categories_seen: set[str] = set()
        for svc in services:
            svc_nid = f"service:{svc.id}"
            self._add_node(GraphNode(
                id=svc_nid, entity_type=EntityType.SERVICE,
                name=svc.service_name,
                properties={"category": svc.service_category, "price": svc.starting_price},
            ))
            self._add_edge(GraphEdge(
                source_id=f"competitor:{svc.competitor_id}",
                target_id=svc_nid,
                relationship=RelationshipType.OWNS,
            ))
            stats["nodes"] += 1
            stats["edges"] += 1

            if svc.service_category and svc.service_category not in categories_seen:
                categories_seen.add(svc.service_category)
                cat_nid = f"category:{svc.service_category.lower()}"
                self._add_node(GraphNode(id=cat_nid, entity_type=EntityType.CATEGORY, name=svc.service_category))
                self._add_edge(GraphEdge(source_id=svc_nid, target_id=cat_nid, relationship=RelationshipType.USES))
                stats["edges"] += 1

        # ── Pricing ──
        stmt = select(CompetitorPricing)
        pricings = (await session.execute(stmt)).scalars().all()
        for prc in pricings:
            prc_nid = f"pricing:{prc.id}"
            self._add_node(GraphNode(
                id=prc_nid, entity_type=EntityType.PRICING,
                name=f"{prc.service_name} - {prc.currency} {prc.base_price}",
                properties={"base_price": prc.base_price, "currency": prc.currency, "category": prc.category},
            ))
            self._add_edge(GraphEdge(
                source_id=f"competitor:{prc.competitor_id}",
                target_id=prc_nid,
                relationship=RelationshipType.PRICED_AT,
            ))
            stats["nodes"] += 1
            stats["edges"] += 1

        # ── Content → extract technology mentions ──
        stmt = select(CompetitorContent)
        contents = (await session.execute(stmt)).scalars().all()
        tech_keywords = {"react", "angular", "vue", "python", "node", "aws", "gcp", "azure", "kubernetes", "docker", "tensorflow", "pytorch", "redis", "postgresql", "mongodb", "graphql", "rest", "flutter", "react native", "swift", "kotlin"}
        for content in contents:
            content_nid = f"content:{content.id}"
            self._add_node(GraphNode(
                id=content_nid, entity_type=EntityType.CONTENT,
                name=content.title or f"Content #{content.id}",
                properties={"content_type": content.content_type, "url": content.url},
            ))
            self._add_edge(GraphEdge(
                source_id=f"competitor:{content.competitor_id}",
                target_id=content_nid,
                relationship=RelationshipType.OWNS,
            ))
            stats["nodes"] += 1
            stats["edges"] += 1

            # Extract tech mentions
            text = (content.title or "").lower() + " " + (content.raw_content or "")[:500].lower()
            for tech in tech_keywords:
                if tech in text:
                    tech_nid = f"technology:{tech}"
                    self._add_node(GraphNode(id=tech_nid, entity_type=EntityType.TECHNOLOGY, name=tech.title()))
                    self._add_edge(GraphEdge(
                        source_id=f"competitor:{content.competitor_id}",
                        target_id=tech_nid,
                        relationship=RelationshipType.USES,
                        weight=0.5,
                    ))
                    stats["edges"] += 1

        # ── Social profiles ──
        stmt = select(CompetitorSocial)
        socials = (await session.execute(stmt)).scalars().all()
        for soc in socials:
            soc_nid = f"social:{soc.id}"
            self._add_node(GraphNode(
                id=soc_nid, entity_type=EntityType.SOCIAL,
                name=f"{soc.platform.value}: {soc.username or soc.profile_url}",
                properties={"platform": soc.platform.value, "url": soc.profile_url},
            ))
            self._add_edge(GraphEdge(
                source_id=f"competitor:{soc.competitor_id}",
                target_id=soc_nid,
                relationship=RelationshipType.OWNS,
            ))
            stats["nodes"] += 1
            stats["edges"] += 1

        # ── Build competitor↔competitor edges (shared categories) ──
        comp_categories: dict[int, set[str]] = defaultdict(set)
        for svc in services:
            if svc.service_category:
                comp_categories[svc.competitor_id].add(svc.service_category.lower())

        comp_ids = list(comp_categories.keys())
        for i in range(len(comp_ids)):
            for j in range(i + 1, len(comp_ids)):
                shared = comp_categories[comp_ids[i]] & comp_categories[comp_ids[j]]
                if shared:
                    weight = len(shared) / 5.0
                    self._add_edge(GraphEdge(
                        source_id=f"competitor:{comp_ids[i]}",
                        target_id=f"competitor:{comp_ids[j]}",
                        relationship=RelationshipType.COMPETES_WITH,
                        weight=min(weight, 1.0),
                        properties={"shared_categories": list(shared)},
                    ))
                    stats["edges"] += 1

        self._built_at = datetime.now(UTC)
        logger.info("knowledge_graph_built", nodes=stats["nodes"], edges=stats["edges"])
        return stats

    def _add_node(self, node: GraphNode) -> None:
        self._nodes[node.id] = node
        self._type_index[node.entity_type].add(node.id)
        self._name_index[node.name.lower()] = node.id

    def _add_edge(self, edge: GraphEdge) -> None:
        self._edges.append(edge)
        self._adjacency[edge.source_id].append(edge)
        self._reverse_adjacency[edge.target_id].append(edge)

    def get_node(self, node_id: str) -> GraphNode | None:
        return self._nodes.get(node_id)

    def get_neighbors(self, node_id: str, relationship: RelationshipType | None = None) -> list[tuple[GraphNode, GraphEdge]]:
        results = []
        for edge in self._adjacency.get(node_id, []):
            if relationship is None or edge.relationship == relationship:
                target = self._nodes.get(edge.target_id)
                if target:
                    results.append((target, edge))
        return results

    def get_reverse_neighbors(self, node_id: str, relationship: RelationshipType | None = None) -> list[tuple[GraphNode, GraphEdge]]:
        results = []
        for edge in self._reverse_adjacency.get(node_id, []):
            if relationship is None or edge.relationship == relationship:
                source = self._nodes.get(edge.source_id)
                if source:
                    results.append((source, edge))
        return results

    def find_path(self, source_id: str, target_id: str, max_depth: int = 5) -> GraphPath | None:
        """BFS shortest path between two nodes."""
        if source_id == target_id:
            return GraphPath(nodes=[source_id], edges=[])

        visited: set[str] = {source_id}
        queue: deque[tuple[str, list[str], list[GraphEdge]]] = deque([(source_id, [source_id], [])])

        while queue:
            current, path_nodes, path_edges = queue.popleft()
            if len(path_nodes) > max_depth:
                continue

            for edge in self._adjacency.get(current, []):
                if edge.target_id not in visited:
                    new_nodes = path_nodes + [edge.target_id]
                    new_edges = path_edges + [edge]
                    if edge.target_id == target_id:
                        return GraphPath(
                            nodes=new_nodes, edges=new_edges,
                            total_weight=sum(e.weight for e in new_edges),
                        )
                    visited.add(edge.target_id)
                    queue.append((edge.target_id, new_nodes, new_edges))

        return None

    def find_competitors_in_city(self, city: str) -> list[GraphNode]:
        city_nid = f"city:{city.lower()}"
        return [n for n, _ in self.get_reverse_neighbors(city_nid, RelationshipType.OPERATES_IN)]

    def find_competitors_in_category(self, category: str) -> list[GraphNode]:
        cat_nid = f"category:{category.lower()}"
        services = [n for n, _ in self.get_reverse_neighbors(cat_nid, RelationshipType.USES)]
        competitor_ids = set()
        for svc in services:
            for comp, _ in self.get_reverse_neighbors(svc.id, RelationshipType.OWNS):
                if comp.entity_type == EntityType.COMPETITOR:
                    competitor_ids.add(comp.id)
        return [self._nodes[cid] for cid in competitor_ids if cid in self._nodes]

    def detect_hidden_competitors(self) -> list[dict[str, Any]]:
        """Find competitors that share many categories but aren't directly linked."""
        comp_nodes = [n for n in self._nodes.values() if n.entity_type == EntityType.COMPETITOR]
        hidden = []
        for comp in comp_nodes:
            neighbors = {n.id for n, _ in self.get_neighbors(comp.id, RelationshipType.COMPETES_WITH)}
            cat_services = [n for n, _ in self.get_neighbors(comp.id, RelationshipType.OWNS)
                          if n.entity_type == EntityType.SERVICE]
            cat_ids = set()
            for svc in cat_services:
                for cat, _ in self.get_neighbors(svc.id, RelationshipType.USES):
                    cat_ids.add(cat.id)

            # Find competitors in same categories not directly linked
            potential: dict[str, int] = defaultdict(int)
            for cat_id in cat_ids:
                for other, _ in self.get_reverse_neighbors(cat_id, RelationshipType.USES):
                    if other.entity_type == EntityType.SERVICE:
                        for comp2, _ in self.get_reverse_neighbors(other.id, RelationshipType.OWNS):
                            if comp2.entity_type == EntityType.COMPETITOR and comp2.id != comp.id and comp2.id not in neighbors:
                                potential[comp2.id] += 1

            for pid, shared_cats in potential.items():
                if shared_cats >= 2:
                    hidden.append({
                        "competitor_a": comp.name,
                        "competitor_b": self._nodes[pid].name,
                        "shared_categories": shared_cats,
                        "hidden_competitor_id": pid,
                    })
        return hidden

    def detect_market_clusters(self) -> list[dict[str, Any]]:
        """Find clusters of competitors using union-find on COMPETES_WITH edges."""
        comp_ids = {n.id for n in self._nodes.values() if n.entity_type == EntityType.COMPETITOR}
        parent: dict[str, str] = {cid: cid for cid in comp_ids}

        def find(x: str) -> str:
            while parent[x] != x:
                parent[x] = parent[parent[x]]
                x = parent[x]
            return x

        def union(x: str, y: str) -> None:
            rx, ry = find(x), find(y)
            if rx != ry:
                parent[rx] = ry

        for edge in self._edges:
            if edge.relationship == RelationshipType.COMPETES_WITH:
                if edge.source_id in comp_ids and edge.target_id in comp_ids:
                    union(edge.source_id, edge.target_id)

        clusters: dict[str, list[str]] = defaultdict(list)
        for cid in comp_ids:
            clusters[find(cid)].append(cid)

        result = []
        for root, members in clusters.items():
            if len(members) > 1:
                names = [self._nodes[m].name for m in members]
                result.append({
                    "cluster_id": root,
                    "members": names,
                    "member_ids": [int(m.split(":")[1]) for m in members],
                    "size": len(members),
                })
        return result

    def get_influence_scores(self) -> dict[str, float]:
        """Simple PageRank-inspired influence scoring."""
        comp_ids = [n.id for n in self._nodes.values() if n.entity_type == EntityType.COMPETITOR]
        if not comp_ids:
            return {}

        scores: dict[str, float] = {cid: 1.0 / len(comp_ids) for cid in comp_ids}
        damping = 0.85
        iterations = 20

        comp_set = set(comp_ids)
        for _ in range(iterations):
            new_scores: dict[str, float] = {cid: (1 - damping) / len(comp_ids) for cid in comp_ids}
            for edge in self._edges:
                if edge.relationship == RelationshipType.COMPETES_WITH and edge.source_id in comp_set and edge.target_id in comp_set:
                    out_edges = [e for e in self._adjacency.get(edge.source_id, [])
                                if e.target_id in comp_set and e.relationship == RelationshipType.COMPETES_WITH]
                    if out_edges:
                        contribution = scores[edge.source_id] / len(out_edges)
                        new_scores[edge.target_id] += damping * contribution
            scores = new_scores

        return {k: round(v, 4) for k, v in scores.items()}

    def search(self, query: str, limit: int = 10) -> list[GraphNode]:
        """Simple name-based search across all nodes."""
        query_lower = query.lower()
        results = []
        for node in self._nodes.values():
            if query_lower in node.name.lower():
                results.append(node)
            if len(results) >= limit:
                break
        return results

    def get_stats(self) -> dict[str, Any]:
        return {
            "total_nodes": len(self._nodes),
            "total_edges": len(self._edges),
            "nodes_by_type": {t.value: len(ids) for t, ids in self._type_index.items()},
            "built_at": self._built_at.isoformat() if self._built_at else None,
        }

    def to_dict(self, include_edges: bool = True) -> dict[str, Any]:
        """Export graph as JSON-serializable dict for frontend visualization."""
        nodes = [
            {"id": n.id, "type": n.entity_type.value, "name": n.name, "properties": n.properties}
            for n in self._nodes.values()
        ]
        edges = []
        if include_edges:
            edges = [
                {"source": e.source_id, "target": e.target_id, "relationship": e.relationship.value, "weight": e.weight}
                for e in self._edges
            ]
        return {"nodes": nodes, "edges": edges, "stats": self.get_stats()}


knowledge_graph = KnowledgeGraph()
