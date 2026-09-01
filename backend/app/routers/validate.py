from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import Project, User, OptimizationRun, QueueValidation
from app.schemas.validate import QueueValidationResponse, ValidateRequest
from app.dependencies import get_current_active_user
import uuid

router = APIRouter(prefix="/api/v1/projects/{project_id}/validate", tags=["validate"])

@router.post("/queue", response_model=list[QueueValidationResponse])
def validate_queue(
    project_id: uuid.UUID,
    req: ValidateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    opt_run = db.query(OptimizationRun).filter(OptimizationRun.id == req.optimization_run_id, OptimizationRun.project_id == project.id).first()
    if not opt_run:
        raise HTTPException(status_code=404, detail="Optimization run not found")

    # Trigger queue validation synchronously (since it's fast)
    # from app.services.ml_service import run_queue_validation
    # run_queue_validation(str(opt_run.id))

    return db.query(QueueValidation).filter(QueueValidation.optimization_run_id == opt_run.id).all()

@router.get("/results", response_model=list[QueueValidationResponse])
def get_validation_results(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    # This might need to be filtered by optimization run in a real scenario
    # Assuming latest run for now or return all for the project
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Simple join to get all validations for the project
    return db.query(QueueValidation).join(OptimizationRun).filter(OptimizationRun.project_id == project.id).all()
