import pytest
import uuid
import os
import time
from sqlalchemy.orm import Session
from app.models.database import SessionLocal, Base, engine
from app.models.models import OptimizationRun, Project, User
from app.services.orchestration_service import execute_optimization_pipeline, update_run_status
from app.services.storage_service import StorageService
from app.config import settings

@pytest.fixture(scope="module")
def db_session():
    # Use existing test db setup if available, or just clear tables
    db = SessionLocal()
    yield db
    db.close()

@pytest.fixture
def mock_project(db_session: Session):
    user = User(email=f"test_{uuid.uuid4()}@example.com", hashed_password="hashed", is_active=True)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    project = Project(name="Test Project", description="Test", user_id=user.id)
    db_session.add(project)
    db_session.commit()
    db_session.refresh(project)
    return project

def test_orchestration_lifecycle_and_storage_isolation(mock_project, db_session: Session):
    run_id = uuid.uuid4()
    
    # 1. Database Creation
    opt_run = OptimizationRun(id=run_id, project_id=mock_project.id, run_type="full_pipeline", status="CREATED")
    db_session.add(opt_run)
    db_session.commit()

    # 2. Storage Setup (Temporary/Mocked by uuid)
    storage = StorageService(run_id)
    # Ensure it's empty
    assert not storage.data_path("processed/forecast_results.csv").exists()

    # 3. Execution
    execute_optimization_pipeline(run_id)
    
    # 4. Verification
    db_session.refresh(opt_run)
    assert opt_run.status == "COMPLETED", f"Expected COMPLETED, got {opt_run.status}. Error: {opt_run.error_message}"
    
    # Files must exist
    assert storage.data_path("processed/forecast_results.csv").exists()
    assert storage.result_path("shift_schedule.csv").exists()
    assert storage.result_path("queue_validation_results.csv").exists()
    assert storage.result_path("quantum_classical_comparison.csv").exists()

def test_orchestration_failure_state(mock_project, db_session: Session, monkeypatch):
    run_id = uuid.uuid4()
    opt_run = OptimizationRun(id=run_id, project_id=mock_project.id, run_type="full_pipeline", status="CREATED")
    db_session.add(opt_run)
    db_session.commit()

    # Force a failure in the forecast module
    def mock_train_forecast(*args, **kwargs):
        raise ValueError("Simulated Forecasting Failure")
        
    import app.core_engine.forecasting.demand_forecaster as df
    monkeypatch.setattr(df, "train_forecast", mock_train_forecast)

    execute_optimization_pipeline(run_id)
    
    db_session.refresh(opt_run)
    assert opt_run.status == "FAILED"
    assert "Simulated Forecasting Failure" in opt_run.error_message
    
    # Storage should contain the error log
    storage = StorageService(run_id)
    assert storage.report_path("error_trace.log").exists()

def test_storage_isolation_between_runs(mock_project, db_session: Session):
    run_1 = uuid.uuid4()
    run_2 = uuid.uuid4()
    
    storage1 = StorageService(run_1)
    storage2 = StorageService(run_2)
    
    storage1.ensure_run_dirs()
    storage2.ensure_run_dirs()
    
    f1 = storage1.data_path("test.txt")
    f2 = storage2.data_path("test.txt")
    
    with open(f1, "w") as f:
        f.write("Run 1 data")
        
    assert not f2.exists(), "Run 2 should be isolated from Run 1"
