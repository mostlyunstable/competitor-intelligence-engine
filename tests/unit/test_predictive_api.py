"""Unit tests for Sprint 7 Predictive Analytics API endpoints."""

import pytest
from unittest.mock import AsyncMock, MagicMock
from fastapi.testclient import TestClient

from app.api.dependencies import get_session


@pytest.fixture
def client():
    from app.main import create_app
    app = create_app()
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c


def _auth_headers():
    import base64
    creds = base64.b64encode(b"admin:admin123").decode()
    return {"Authorization": f"Basic {creds}"}


def _mock_session(**overrides):
    """Create a mock session with configurable returns."""
    session = AsyncMock()
    for method, return_val in overrides.items():
        if method == "get":
            session.get = AsyncMock(return_value=return_val)
        elif method == "scalar":
            session.scalar = AsyncMock(return_value=return_val)
        elif method == "execute":
            session.execute = AsyncMock(return_value=return_val)
        elif method == "add":
            session.add = MagicMock()
    return session


def _empty_execute_result():
    result = MagicMock()
    result.scalars.return_value.all.return_value = []
    return result


# ─── Pricing Forecast Endpoint ────────────────────────────────────────────


class TestPredictivePricing:
    def test_pricing_404_unknown_competitor(self, client):
        from app.database.models import Competitor
        session = _mock_session(get=None)
        client.app.dependency_overrides[get_session] = lambda: session
        resp = client.get("/api/predictive/pricing/99999", headers=_auth_headers())
        assert resp.status_code == 404
        client.app.dependency_overrides.clear()

    def test_pricing_returns_forecast(self, client):
        from app.database.models import Competitor
        comp = Competitor(id=1, name="Test", website_url="http://test.com")
        session = _mock_session(get=comp, scalar=5, execute=_empty_execute_result())
        client.app.dependency_overrides[get_session] = lambda: session
        resp = client.get("/api/predictive/pricing/1?steps=3", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "forecast" in data
        assert "historical" in data
        assert "confidence" in data
        assert len(data["forecast"]["values"]) == 3
        client.app.dependency_overrides.clear()

    def test_pricing_custom_model(self, client):
        from app.database.models import Competitor
        comp = Competitor(id=1, name="Test", website_url="http://test.com")
        session = _mock_session(get=comp, scalar=3, execute=_empty_execute_result())
        client.app.dependency_overrides[get_session] = lambda: session
        resp = client.get("/api/predictive/pricing/1?model=exp_smoothing", headers=_auth_headers())
        assert resp.status_code == 200
        assert resp.json()["model"] == "exp_smoothing"
        client.app.dependency_overrides.clear()


# ─── Growth Velocity Endpoint ─────────────────────────────────────────────


class TestPredictiveGrowth:
    def test_growth_404(self, client):
        session = _mock_session(get=None)
        client.app.dependency_overrides[get_session] = lambda: session
        resp = client.get("/api/predictive/growth/99999", headers=_auth_headers())
        assert resp.status_code == 404
        client.app.dependency_overrides.clear()

    def test_growth_returns_metrics(self, client):
        from app.database.models import Competitor
        comp = Competitor(id=1, name="Test", website_url="http://test.com")
        session = _mock_session(get=comp, scalar=2, execute=_empty_execute_result())
        client.app.dependency_overrides[get_session] = lambda: session
        resp = client.get("/api/predictive/growth/1", headers=_auth_headers())
        assert resp.status_code == 200
        data = resp.json()
        assert "growth" in data
        assert "growth_direction" in data["growth"]
        assert data["growth"]["growth_direction"] in ("growing", "stable", "declining")
        client.app.dependency_overrides.clear()


# ─── Regional Opportunities Endpoint ──────────────────────────────────────


class TestRegionalOpportunities:
    def test_regional_returns_list(self, client):
        session = _mock_session(execute=_empty_execute_result())
        client.app.dependency_overrides[get_session] = lambda: session
        resp = client.get("/api/predictive/regional/opportunities", headers=_auth_headers())
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        client.app.dependency_overrides.clear()


# ─── Strategic Risks Endpoint ─────────────────────────────────────────────


class TestStrategicRisks:
    def test_risks_returns_list(self, client):
        session = _mock_session(execute=_empty_execute_result(), scalar=0)
        client.app.dependency_overrides[get_session] = lambda: session
        resp = client.get("/api/predictive/strategic-risks", headers=_auth_headers())
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        client.app.dependency_overrides.clear()


# ─── Recommendations Endpoint ─────────────────────────────────────────────


class TestPredictiveRecommendations:
    def test_recommendations_returns_list(self, client):
        session = _mock_session(execute=_empty_execute_result(), scalar=0)
        client.app.dependency_overrides[get_session] = lambda: session
        resp = client.get("/api/predictive/recommendations", headers=_auth_headers())
        assert resp.status_code == 200
        assert isinstance(resp.json(), list)
        client.app.dependency_overrides.clear()


# ─── Auth Tests ───────────────────────────────────────────────────────────


class TestPredictiveAuth:
    def test_no_auth_returns_401(self, client):
        resp = client.get("/api/predictive/pricing/1")
        assert resp.status_code == 401

    def test_wrong_auth_returns_401(self, client):
        import base64
        creds = base64.b64encode(b"admin:wrongpassword").decode()
        resp = client.get("/api/predictive/pricing/1", headers={"Authorization": f"Basic {creds}"})
        assert resp.status_code == 401
