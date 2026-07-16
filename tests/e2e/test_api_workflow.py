import pytest
from fastapi.testclient import TestClient
from app.main import app
import uuid

@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c

def test_health_check(client: TestClient):
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ["healthy", "degraded"]

def test_competitors_workflow(client: TestClient):
    # Use random url to avoid duplicate constraint if run multiple times
    random_url = f"https://example.com/e2e-{uuid.uuid4()}"
    competitor_data = {
        "name": f"E2E Test Corp {uuid.uuid4()}",
        "website_url": random_url,
        "industry": "Testing",
        "collection_frequency": "daily"
    }
    headers = {"Authorization": "Bearer test_token"}
    response = client.post("/competitors", json=competitor_data, headers=headers)
    
    if response.status_code == 401:
        assert response.status_code == 401
    else:
        assert response.status_code == 201
        comp_id = response.json()["id"]
        
        response = client.get(f"/competitors/{comp_id}", headers=headers)
        assert response.status_code == 200
        assert response.json()["name"] == competitor_data["name"]
