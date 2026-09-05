import pytest
from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

def test_get_demo_datasets():
    response = client.get("/api/v1/dashboard/demo/datasets")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        data = response.json()
        assert data["success"] is True
        assert "run_id" in data
        assert "data" in data
        assert "raw" in data["data"]
        assert "classical" in data["data"]

def test_get_demo_kpis():
    response = client.get("/api/v1/dashboard/demo/kpis")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        data = response.json()
        assert data["success"] is True
        assert "Total Cost Raw" in data["data"]

def test_get_demo_whatif_valid():
    response = client.get("/api/v1/dashboard/demo/whatif?volume_change=1.2&budget=20000&sla=90")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        data = response.json()
        assert data["success"] is True
        assert "projected_cost" in data["data"]
        assert "agents_needed" in data["data"]

def test_get_demo_whatif_invalid():
    # Negative volume_change
    response = client.get("/api/v1/dashboard/demo/whatif?volume_change=-150&budget=20000&sla=90")
    assert response.status_code == 422 # FastAPI Validation Error
