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

    forecast = ForecastModel(project_id=project.id, status="training")
    db.add(forecast)
    db.commit()
    db.refresh(forecast)

    # Trigger Background task
    from app.services.ml_service import train_random_forest
    background_tasks.add_task(train_random_forest, forecast.id)

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
    # Dummy implementation, to be replaced by actual ML predict
    return {"success": True, "data": {"predictions": [100, 110, 105, 120, 115, 130, 125][:request.days]}}
