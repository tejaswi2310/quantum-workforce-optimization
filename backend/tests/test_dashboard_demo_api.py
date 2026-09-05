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

def test_get_demo_whatif_baseline():
    """Test baseline scenario (volume_change=1.0)"""
    response = client.get("/api/v1/dashboard/demo/whatif?volume_change=1.0&budget=20000&sla=80")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        data = response.json()["data"]
        assert "projected_cost" in data
        assert "agents_needed" in data
        assert "expected_sla" in data
        assert "expected_wait_seconds" in data
        assert "expected_queue_length" in data
        assert data["budget"] == 20000

def test_get_demo_whatif_increased_volume():
    """Test increased volume scenario (+20%)"""
    response = client.get("/api/v1/dashboard/demo/whatif?volume_change=1.2&budget=20000&sla=90")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        data = response.json()["data"]
        assert data["projected_sla"] == 90
        assert data["budget"] == 20000

def test_get_demo_whatif_invalid():
    """Test invalid negative input for volume_change"""
    response = client.get("/api/v1/dashboard/demo/whatif?volume_change=-0.5&budget=20000&sla=90")
    assert response.status_code == 422 # FastAPI Validation Error

def test_get_demo_whatif_budget_validation():
    """Test budget validation logic"""
    response = client.get("/api/v1/dashboard/demo/whatif?volume_change=1.0&budget=10&sla=90")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        data = response.json()["data"]
        # If budget is extremely low, it should be over budget (if cost > 10)
        if data["projected_cost"] is not None and data["projected_cost"] > 10:
            assert data["is_over_budget"] is True
            assert data["budget_variance"] > 0

def test_get_demo_whatif_sla_validation():
    """Test invalid SLA input"""
    response = client.get("/api/v1/dashboard/demo/whatif?volume_change=1.0&budget=20000&sla=150")
    assert response.status_code == 422 # Should fail le=100 validation

    response_negative_sla = client.get("/api/v1/dashboard/demo/whatif?volume_change=1.0&budget=20000&sla=-10")
    assert response_negative_sla.status_code == 422 # Should fail ge=0 validation

def test_get_latest_global_run_selects_completed():
    """Regression test: verify dashboard demo endpoints select the latest COMPLETED run."""
    import uuid
    from datetime import datetime, timedelta
    from tests.conftest import TestingSessionLocal, engine
    from app.models.database import Base
    from app.models.models import OptimizationRun
    from app.routers.dashboard_demo import get_latest_global_run

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # Create an older COMPLETED run
        older_run_id = uuid.uuid4()
        older_run = OptimizationRun(
            id=older_run_id,
            status="COMPLETED",
            created_at=datetime.utcnow() - timedelta(minutes=10)
        )
        db.add(older_run)

        # Create a newer OPTIMIZING run
        newer_run_id = uuid.uuid4()
        newer_run = OptimizationRun(
            id=newer_run_id,
            status="OPTIMIZING",
            created_at=datetime.utcnow()
        )
        db.add(newer_run)
        
        db.commit()

        # Test the function directly
        latest = get_latest_global_run(db)
        
        # It should select the older COMPLETED run, ignoring the newer OPTIMIZING run
        assert latest.id == older_run_id
        
        # Cleanup isolated test data
        db.delete(newer_run)
        db.delete(older_run)
        db.commit()
    finally:
        db.close()
