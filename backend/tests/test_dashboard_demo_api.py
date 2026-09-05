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
    """Regression test: verify dashboard demo endpoints select the newest COMPLETED and FULLY USABLE run."""
    import uuid
    import os
    from datetime import datetime, timedelta
    from tests.conftest import TestingSessionLocal, engine
    from app.models.database import Base
    from app.models.models import OptimizationRun
    from app.routers.dashboard_demo import get_latest_global_run
    from app.services.storage_service import StorageService

    Base.metadata.create_all(bind=engine)
    db = TestingSessionLocal()
    try:
        # Create an older COMPLETED run WITH artifacts
        older_run_id = uuid.uuid4()
        older_run = OptimizationRun(
            id=older_run_id,
            status="COMPLETED",
            created_at=datetime.utcnow() - timedelta(minutes=10)
        )
        db.add(older_run)

        # Create the artifacts for the older run
        storage_older = StorageService(older_run_id)
        storage_older.ensure_run_dirs()
        storage_older.result_path("queue_validation_results.csv").touch()
        storage_older.result_path("classical_optimization_schedule.csv").touch()
        storage_older.result_path("shift_schedule.csv").touch()
        storage_older.result_path("quantum_classical_comparison.csv").touch()
        storage_older.data_path("raw/synthetic_call_center.csv").touch()
        storage_older.data_path("processed/forecast_results.csv").touch()

        # Create a newer COMPLETED run MISSING artifacts
        newer_run_id = uuid.uuid4()
        newer_run = OptimizationRun(
            id=newer_run_id,
            status="COMPLETED",
            created_at=datetime.utcnow()
        )
        db.add(newer_run)

        db.commit()

        # Test the function directly
        latest = get_latest_global_run(db)

        # It should select the older COMPLETED run, ignoring the newer one with missing artifacts
        assert latest.id == older_run_id

        # Cleanup isolated test data
        db.delete(newer_run)
        db.delete(older_run)
        db.commit()
    finally:
        db.close()

def test_readonly_demo_mode_without_db(monkeypatch):
    from app.config import settings
    monkeypatch.setattr(settings, "DASHBOARD_DEMO_MODE", "readonly")

    # Test /kpis
    kpi_resp = client.get("/api/v1/dashboard/demo/kpis")
    assert kpi_resp.status_code == 200
    kpi_data = kpi_resp.json()
    assert kpi_data["success"] is True
    assert "average_wage" in kpi_data["data"]

    # Test /datasets
    ds_resp = client.get("/api/v1/dashboard/demo/datasets")
    assert ds_resp.status_code == 200
    ds_data = ds_resp.json()
    assert ds_data["success"] is True
    assert "raw" in ds_data["data"]

    # Test /whatif
    wi_resp = client.get("/api/v1/dashboard/demo/whatif?volume_change=1.0&budget=20000&sla=80")
    assert wi_resp.status_code == 200
    wi_data = wi_resp.json()
    assert wi_data["success"] is True
    assert "projected_cost" in wi_data["data"]
