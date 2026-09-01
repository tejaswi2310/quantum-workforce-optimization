from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import Project, User, OptimizationRun
from app.schemas.optimize import OptimizationRunResponse, OptimizationRequest
from app.dependencies import get_current_active_user
import uuid

router = APIRouter(prefix="/api/v1/projects/{project_id}/optimize", tags=["optimize"])

def start_optimization(project_id: uuid.UUID, run_type: str, parameters: dict, background_tasks: BackgroundTasks, db: Session, current_user: User):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    opt_run = OptimizationRun(
        project_id=project.id,
        run_type=run_type,
        parameters=parameters,
        status="pending"
    )
    db.add(opt_run)
    db.commit()
    db.refresh(opt_run)

    # Trigger Background task
    from app.services.orchestration_service import execute_optimization_pipeline
    background_tasks.add_task(execute_optimization_pipeline, opt_run.id)

    return opt_run

@router.post("/classical", response_model=OptimizationRunResponse)
def optimize_classical(project_id: uuid.UUID, req: OptimizationRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return start_optimization(project_id, "classical", req.parameters or {}, background_tasks, db, current_user)

@router.post("/shifts", response_model=OptimizationRunResponse)
def optimize_shifts(project_id: uuid.UUID, req: OptimizationRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return start_optimization(project_id, "shift", req.parameters or {}, background_tasks, db, current_user)

@router.post("/quantum", response_model=OptimizationRunResponse)
def optimize_quantum(project_id: uuid.UUID, req: OptimizationRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return start_optimization(project_id, "quantum", req.parameters or {}, background_tasks, db, current_user)

@router.post("/hybrid", response_model=OptimizationRunResponse)
def optimize_hybrid(project_id: uuid.UUID, req: OptimizationRequest, background_tasks: BackgroundTasks, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    return start_optimization(project_id, "hybrid", req.parameters or {}, background_tasks, db, current_user)

@router.get("/runs", response_model=list[OptimizationRunResponse])
def get_optimization_runs(project_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return db.query(OptimizationRun).filter(OptimizationRun.project_id == project_id).all()

@router.get("/runs/{run_id}", response_model=OptimizationRunResponse)
def get_optimization_run(project_id: uuid.UUID, run_id: uuid.UUID, db: Session = Depends(get_db), current_user: User = Depends(get_current_active_user)):
    run = db.query(OptimizationRun).filter(OptimizationRun.id == run_id, OptimizationRun.project_id == project_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Optimization run not found")
    return run
