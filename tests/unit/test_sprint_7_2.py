"""Unit tests for Sprint 7.2: Enterprise AI Intelligence."""

import math
import pytest

from app.services.knowledge_graph.engine import (
    KnowledgeGraph, EntityType, RelationshipType, GraphNode, GraphEdge, GraphPath,
)
from app.services.rag.pipeline import RAGPipeline, _simple_hash_embedding, _cosine_similarity
from app.services.rag.copilot import ExecutiveCopilot
from app.services.agents.coordinator import (
    CoordinatorAgent, AgentType, MarketResearchAgent, PricingAgent,
    GrowthForecastAgent, RiskAgent, OpportunityAgent, BenchmarkAgent,
)
from app.services.ml.forecaster import (
    MLForecaster, _linear_regression_forecast, _moving_average_forecast,
    _exponential_smoothing_forecast, _heuristic_forecast,
)
from app.services.streaming.events import EventStreamingManager, EventType, Event
from app.services.geo.intelligence import GeographicIntelligence, CITY_DATA


# ─── Knowledge Graph Tests ─────────────────────────────────────────────────


class TestKnowledgeGraph:
    def test_init(self):
        kg = KnowledgeGraph()
        assert kg._built_at is None
        assert len(kg._nodes) == 0

    def test_add_node(self):
        kg = KnowledgeGraph()
        node = GraphNode(id="test:1", entity_type=EntityType.COMPETITOR, name="Test")
        kg._add_node(node)
        assert kg.get_node("test:1") is not None
        assert kg.get_node("test:1").name == "Test"

    def test_add_edge(self):
        kg = KnowledgeGraph()
        n1 = GraphNode(id="c:1", entity_type=EntityType.COMPETITOR, name="A")
        n2 = GraphNode(id="c:2", entity_type=EntityType.COMPETITOR, name="B")
        kg._add_node(n1)
        kg._add_node(n2)
        edge = GraphEdge(source_id="c:1", target_id="c:2", relationship=RelationshipType.COMPETES_WITH)
        kg._add_edge(edge)
        neighbors = kg.get_neighbors("c:1", RelationshipType.COMPETES_WITH)
        assert len(neighbors) == 1
        assert neighbors[0][0].id == "c:2"

    def test_reverse_neighbors(self):
        kg = KnowledgeGraph()
        n1 = GraphNode(id="c:1", entity_type=EntityType.COMPETITOR, name="A")
        n2 = GraphNode(id="s:1", entity_type=EntityType.SERVICE, name="Service")
        kg._add_node(n1)
        kg._add_node(n2)
        kg._add_edge(GraphEdge(source_id="c:1", target_id="s:1", relationship=RelationshipType.OWNS))
        rev = kg.get_reverse_neighbors("s:1", RelationshipType.OWNS)
        assert len(rev) == 1
        assert rev[0][0].id == "c:1"

    def test_find_path(self):
        kg = KnowledgeGraph()
        for i in range(4):
            kg._add_node(GraphNode(id=f"n:{i}", entity_type=EntityType.COMPETITOR, name=f"N{i}"))
        kg._add_edge(GraphEdge(source_id="n:0", target_id="n:1", relationship=RelationshipType.COMPETES_WITH))
        kg._add_edge(GraphEdge(source_id="n:1", target_id="n:2", relationship=RelationshipType.COMPETES_WITH))
        kg._add_edge(GraphEdge(source_id="n:2", target_id="n:3", relationship=RelationshipType.COMPETES_WITH))
        path = kg.find_path("n:0", "n:3")
        assert path is not None
        assert len(path.nodes) == 4

    def test_find_path_none(self):
        kg = KnowledgeGraph()
        kg._add_node(GraphNode(id="a", entity_type=EntityType.COMPETITOR, name="A"))
        kg._add_node(GraphNode(id="b", entity_type=EntityType.COMPETITOR, name="B"))
        assert kg.find_path("a", "b") is None

    def test_search(self):
        kg = KnowledgeGraph()
        kg._add_node(GraphNode(id="c:1", entity_type=EntityType.COMPETITOR, name="Urban Company"))
        kg._add_node(GraphNode(id="c:2", entity_type=EntityType.COMPETITOR, name="HomeFix"))
        results = kg.search("urban")
        assert len(results) == 1
        assert results[0].name == "Urban Company"

    def test_stats(self):
        kg = KnowledgeGraph()
        kg._add_node(GraphNode(id="c:1", entity_type=EntityType.COMPETITOR, name="A"))
        stats = kg.get_stats()
        assert stats["total_nodes"] == 1
        assert stats["nodes_by_type"]["competitor"] == 1

    def test_to_dict(self):
        kg = KnowledgeGraph()
        kg._add_node(GraphNode(id="c:1", entity_type=EntityType.COMPETITOR, name="A"))
        data = kg.to_dict()
        assert len(data["nodes"]) == 1
        assert data["nodes"][0]["type"] == "competitor"

    def test_market_clusters(self):
        kg = KnowledgeGraph()
        kg._add_node(GraphNode(id="c:1", entity_type=EntityType.COMPETITOR, name="A"))
        kg._add_node(GraphNode(id="c:2", entity_type=EntityType.COMPETITOR, name="B"))
        kg._add_node(GraphNode(id="c:3", entity_type=EntityType.COMPETITOR, name="C"))
        kg._add_edge(GraphEdge(source_id="c:1", target_id="c:2", relationship=RelationshipType.COMPETES_WITH))
        kg._add_edge(GraphEdge(source_id="c:2", target_id="c:3", relationship=RelationshipType.COMPETES_WITH))
        clusters = kg.detect_market_clusters()
        assert len(clusters) == 1
        assert clusters[0]["size"] == 3

    def test_influence_scores(self):
        kg = KnowledgeGraph()
        kg._add_node(GraphNode(id="c:1", entity_type=EntityType.COMPETITOR, name="A"))
        kg._add_node(GraphNode(id="c:2", entity_type=EntityType.COMPETITOR, name="B"))
        kg._add_edge(GraphEdge(source_id="c:1", target_id="c:2", relationship=RelationshipType.COMPETES_WITH))
        scores = kg.get_influence_scores()
        assert len(scores) == 2
        assert all(0 < s < 1 for s in scores.values())

    def test_hidden_competitors(self):
        kg = KnowledgeGraph()
        # Two competitors sharing 2+ categories but NOT directly linked
        kg._add_node(GraphNode(id="c:1", entity_type=EntityType.COMPETITOR, name="A"))
        kg._add_node(GraphNode(id="c:2", entity_type=EntityType.COMPETITOR, name="B"))
        kg._add_node(GraphNode(id="s:1", entity_type=EntityType.SERVICE, name="Svc1"))
        kg._add_node(GraphNode(id="s:2", entity_type=EntityType.SERVICE, name="Svc2"))
        kg._add_node(GraphNode(id="cat:1", entity_type=EntityType.CATEGORY, name="Plumbing"))
        kg._add_node(GraphNode(id="cat:2", entity_type=EntityType.CATEGORY, name="Cleaning"))
        # A owns Svc1, Svc1 uses Plumbing and Cleaning
        kg._add_edge(GraphEdge(source_id="c:1", target_id="s:1", relationship=RelationshipType.OWNS))
        kg._add_edge(GraphEdge(source_id="s:1", target_id="cat:1", relationship=RelationshipType.USES))
        kg._add_edge(GraphEdge(source_id="s:1", target_id="cat:2", relationship=RelationshipType.USES))
        # B owns Svc2, Svc2 uses Plumbing and Cleaning
        kg._add_edge(GraphEdge(source_id="c:2", target_id="s:2", relationship=RelationshipType.OWNS))
        kg._add_edge(GraphEdge(source_id="s:2", target_id="cat:1", relationship=RelationshipType.USES))
        kg._add_edge(GraphEdge(source_id="s:2", target_id="cat:2", relationship=RelationshipType.USES))
        hidden = kg.detect_hidden_competitors()
        assert len(hidden) == 2  # Bidirectional: A→B and B→A


# ─── RAG Pipeline Tests ────────────────────────────────────────────────────


class TestHashEmbedding:
    def test_deterministic(self):
        a = _simple_hash_embedding("hello world")
        b = _simple_hash_embedding("hello world")
        assert a == b

    def test_different_inputs(self):
        a = _simple_hash_embedding("hello")
        b = _simple_hash_embedding("world")
        assert a != b

    def test_normalized(self):
        emb = _simple_hash_embedding("test")
        norm = math.sqrt(sum(x * x for x in emb))
        assert abs(norm - 1.0) < 0.01


class TestCosineSimilarity:
    def test_identical(self):
        a = [1.0, 0.0, 0.0]
        assert _cosine_similarity(a, a) == pytest.approx(1.0)

    def test_orthogonal(self):
        assert _cosine_similarity([1, 0], [0, 1]) == pytest.approx(0.0)

    def test_empty(self):
        assert _cosine_similarity([], []) == 0.0

    def test_different_lengths(self):
        assert _cosine_similarity([1, 0], [1, 0, 0]) == 0.0


class TestRAGPipeline:
    def test_init(self):
        p = RAGPipeline()
        assert len(p._chunks) == 0

    def test_make_chunk(self):
        p = RAGPipeline()
        chunk = p._make_chunk("test", 1, "Hello world test content", {"key": "val"})
        assert chunk.source_type == "test"
        assert len(chunk.embedding) == 128
        assert len(p._chunks) == 1
        assert chunk.id.startswith("test:1:")

    def test_search(self):
        p = RAGPipeline()
        p._make_chunk("content", 1, "Urban Company provides cleaning services in Chennai", {})
        p._make_chunk("content", 2, "HomeFix offers plumbing services in Mumbai", {})
        results = p.search("cleaning Chennai", limit=5)
        assert len(results) > 0
        assert results[0].score > 0

    def test_keyword_search(self):
        p = RAGPipeline()
        p._make_chunk("content", 1, "plumbing repair services available", {})
        p._make_chunk("content", 2, "cleaning and painting services", {})
        results = p.search("plumbing", limit=5)
        assert len(results) >= 1

    def test_stats(self):
        p = RAGPipeline()
        p._make_chunk("test", 1, "content", {})
        stats = p.get_stats()
        assert stats["total_chunks"] == 1


# ─── Copilot Tests ─────────────────────────────────────────────────────────


class TestExecutiveCopilot:
    def test_init(self):
        copilot = ExecutiveCopilot()
        assert len(copilot._conversations) == 0

    def test_classify_intent(self):
        copilot = ExecutiveCopilot()
        assert copilot._classify_intent("compare Urban Company and HomeFix") == "comparison"
        assert copilot._classify_intent("what is the growth forecast?") == "growth"
        assert copilot._classify_intent("what are the risks?") == "risk"
        assert copilot._classify_intent("suggest a strategy") == "recommendation"
        assert copilot._classify_intent("how much does it cost?") == "pricing"
        assert copilot._classify_intent("should we expand to Mumbai?") == "recommendation"  # "should" matches recommendation
        assert copilot._classify_intent("generate a report") == "report"
        assert copilot._classify_intent("what opportunities exist?") == "opportunity"
        assert copilot._classify_intent("random question") == "general"

    def test_suggest_follow_ups(self):
        copilot = ExecutiveCopilot()
        follow_ups = copilot._suggest_follow_ups("comparison", "")
        assert len(follow_ups) > 0

    def test_conversation_history(self):
        copilot = ExecutiveCopilot()
        import asyncio
        asyncio.run(copilot.ask("test question"))
        convs = copilot.list_conversations()
        assert len(convs) == 1
        assert convs[0]["turns"] == 2  # user + assistant


# ─── Agent Tests ───────────────────────────────────────────────────────────


class TestAgentTypes:
    def test_all_types(self):
        types = list(AgentType)
        assert len(types) == 7

    def test_coordinator_init(self):
        coord = CoordinatorAgent()
        assert len(coord._agents) == 6


# ─── ML Forecaster Tests ──────────────────────────────────────────────────


class TestLinearRegression:
    def test_empty(self):
        result = _linear_regression_forecast([], 5)
        assert len(result.predictions) == 5

    def test_linear(self):
        result = _linear_regression_forecast([1, 2, 3, 4, 5], 3)
        assert len(result.predictions) == 3
        assert result.predictions[0] > 5

    def test_metrics(self):
        result = _linear_regression_forecast([1, 2, 3, 4, 5], 3)
        assert "mae" in result.metrics
        assert "rmse" in result.metrics


class TestMovingAverage:
    def test_short(self):
        result = _moving_average_forecast([1, 2], 3)
        assert len(result.predictions) == 3

    def test_with_window(self):
        result = _moving_average_forecast([1, 2, 3, 4, 5], 3, window=3)
        assert len(result.predictions) == 3


class TestExponentialSmoothing:
    def test_empty(self):
        result = _exponential_smoothing_forecast([], 3)
        assert len(result.predictions) == 3

    def test_single(self):
        result = _exponential_smoothing_forecast([5], 3)
        assert len(result.predictions) == 3


class TestHeuristic:
    def test_empty(self):
        result = _heuristic_forecast([], 3)
        assert len(result.predictions) == 3

    def test_trend(self):
        result = _heuristic_forecast([1, 2, 3, 4, 5], 3)
        assert result.predictions[0] > 5


class TestMLForecaster:
    def test_init(self):
        f = MLForecaster()
        assert len(f._models) >= 4

    def test_available_models(self):
        f = MLForecaster()
        models = f.available_models()
        assert len(models) >= 4
        assert any(m["name"] == "linear_regression" for m in models)

    def test_forecast(self):
        f = MLForecaster()
        result = f.forecast([1, 2, 3, 4, 5], steps=5, model_name="linear_regression")
        assert len(result.predictions) == 5
        assert result.model_type == "linear_regression"

    def test_evaluate(self):
        f = MLForecaster()
        result = f.evaluate_model([1, 2, 3, 4, 5, 6, 7, 8, 9, 10], model_name="linear_regression")
        assert result.mae >= 0
        assert result.rmse >= 0

    def test_select_best(self):
        f = MLForecaster()
        best_name, eval_result = f.select_best_model([1, 2, 3, 4, 5, 6, 7, 8, 9, 10])
        assert best_name in ["linear_regression", "moving_average", "exponential_smoothing", "heuristic"]

    def test_history(self):
        f = MLForecaster()
        f.forecast([1, 2, 3], steps=2)
        assert len(f.get_history()) == 1

    def test_fallback(self):
        f = MLForecaster()
        result = f.forecast([1, 2, 3], steps=2, model_name="nonexistent_model")
        assert result.model_type == "heuristic"


# ─── Event Streaming Tests ─────────────────────────────────────────────────


class TestEventStreaming:
    def test_publish_sync(self):
        mgr = EventStreamingManager()
        event = Event(event_type=EventType.PRICE_CHANGE, data={"price": 100})
        mgr.publish_sync(event)
        assert len(mgr._event_history) == 1

    def test_recent_events(self):
        mgr = EventStreamingManager()
        mgr.publish_sync(Event(event_type=EventType.PRICE_CHANGE, data={}))
        mgr.publish_sync(Event(event_type=EventType.SERVICE_LAUNCH, data={}))
        events = mgr.get_recent_events()
        assert len(events) == 2

    def test_filter_by_type(self):
        mgr = EventStreamingManager()
        mgr.publish_sync(Event(event_type=EventType.PRICE_CHANGE, data={}))
        mgr.publish_sync(Event(event_type=EventType.SERVICE_LAUNCH, data={}))
        events = mgr.get_recent_events(EventType.PRICE_CHANGE)
        assert len(events) == 1

    def test_stats(self):
        mgr = EventStreamingManager()
        mgr.publish_sync(Event(event_type=EventType.ALERT, data={}))
        stats = mgr.get_stats()
        assert stats["history_size"] == 1
        assert stats["events_by_type"]["alert"] == 1


# ─── Geographic Intelligence Tests ─────────────────────────────────────────


class TestGeoIntelligence:
    def test_city_data(self):
        assert "chennai" in CITY_DATA
        assert CITY_DATA["chennai"]["tier"] == 1
        assert CITY_DATA["chennai"]["population"] > 0

    def test_init(self):
        geo = GeographicIntelligence()
        assert len(geo._competitor_cities) == 0

    def test_city_comparison(self):
        geo = GeographicIntelligence()
        geo._city_competitors = {"chennai": [1, 2, 3], "mumbai": [1]}
        result = geo.city_comparison(["chennai", "mumbai"])
        assert len(result) == 2
        assert result[0]["competitor_count"] == 3

    def test_city_comparison_unknown(self):
        geo = GeographicIntelligence()
        result = geo.city_comparison(["unknown_city"])
        assert len(result) == 0

    def test_saturation_map(self):
        geo = GeographicIntelligence()
        geo._city_competitors = {"chennai": [1, 2, 3, 4, 5]}
        result = geo._saturation_map()
        assert len(result) > 0
        chennai = next(c for c in result if c["city"] == "Chennai")
        assert chennai["competitors"] == 5
