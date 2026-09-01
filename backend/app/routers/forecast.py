from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import Project, User, ForecastModel
from app.schemas.forecast import ForecastResponse, PredictRequest
from app.dependencies import get_current_active_user
import uuid

router = APIRouter(prefix="/api/v1/projects/{project_id}/forecast", tags=["forecast"])

@router.post("/train", response_model=ForecastResponse)
def train_forecast(
    project_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Creating a ForecastModel just for legacy API compatibility, but we will actually
    # spawn a full pipeline run to satisfy canonical run_id requirements.
    forecast = ForecastModel(project_id=project.id, status="training")
    db.add(forecast)
    
    from app.models.models import OptimizationRun
    opt_run = OptimizationRun(
        project_id=project.id,
        run_type="full_pipeline",
        parameters={},
        status="CREATED"
    )
    db.add(opt_run)
    db.commit()
    db.refresh(forecast)
    db.refresh(opt_run)

    # Trigger actual true Background task
    from app.services.orchestration_service import execute_optimization_pipeline
    background_tasks.add_task(execute_optimization_pipeline, opt_run.id)

    return forecast

@router.get("/status/{task_id}", response_model=ForecastResponse)
def get_forecast_status(
    project_id: uuid.UUID,
    task_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # For now, task_id is just the forecast_model id
    forecast = db.query(ForecastModel).filter(ForecastModel.id == task_id, ForecastModel.project_id == project_id).first()
    if not forecast:
        raise HTTPException(status_code=404, detail="Forecast task not found")
    return forecast

@router.get("/results", response_model=list[ForecastResponse])
def get_forecast_results(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(ForecastModel).filter(ForecastModel.project_id == project_id).all()

@router.post("/predict")
def predict_forecast(
    project_id: uuid.UUID,
    request: PredictRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    from app.services.storage_service import StorageService
    from app.models.models import OptimizationRun
    import pandas as pd

    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    latest_run = db.query(OptimizationRun).filter(OptimizationRun.project_id == project.id).order_by(OptimizationRun.created_at.desc()).first()
    if not latest_run:
        raise HTTPException(status_code=404, detail="No optimization run found for project")

    storage = StorageService(latest_run.id)
    forecast_path = storage.data_path("processed/forecast_results.csv")
    
    if not forecast_path.exists():
        raise HTTPException(status_code=404, detail="Forecast results not found for the latest run")

    try:
        df = pd.read_csv(forecast_path)
        # Just grab the predicted calls as a flat array for the requested days (assuming 1 day = 24 hours, so request.days * 24)
        predictions = df['predicted_calls'].tolist()
        
        # Optionally slice by days
        limit = min(request.days * 24, len(predictions))
        predictions = predictions[:limit]
        
        return {"success": True, "data": {"predictions": predictions}}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read forecast data: {str(e)}")
