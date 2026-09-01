import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import Project, User, Report
from app.schemas.report import ReportResponse, GenerateReportRequest
from app.dependencies import get_current_active_user
import uuid

router = APIRouter(prefix="/api/v1/projects/{project_id}/reports", tags=["reports"])

from app.services.storage_service import StorageService

@router.post("/generate", response_model=ReportResponse)
def generate_report(
    project_id: uuid.UUID,
    req: GenerateReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    import pandas as pd
    
    from app.models.models import OptimizationRun
    latest_run = db.query(OptimizationRun).filter(OptimizationRun.project_id == project_id).order_by(OptimizationRun.created_at.desc()).first()
    if not latest_run:
        raise HTTPException(status_code=404, detail="No optimization run found to generate a report from")

    storage = StorageService(latest_run.id)
    shifts_detailed_path = storage.result_path("agent_shifts_detailed.csv")
    
    opt_cost = 0.0
    if os.path.exists(shifts_detailed_path):
        df_det = pd.read_csv(shifts_detailed_path)
        opt_cost = float(df_det['cost'].sum())
        
    # Naive peak-staffing calculation: schedule peak demand agents for all 24 hours
    naive_cost = 0.0
    shift_schedule_path = storage.result_path("shift_schedule.csv")
    if shift_schedule_path.exists():
        df_shifts = pd.read_csv(shift_schedule_path)
        peak_agents = int(df_shifts['required_agents'].max())
        naive_cost = peak_agents * 24 * 15.0 # Wage = $15/hr
        
    daily_savings = max(0, naive_cost - opt_cost)
    annual_savings = daily_savings * 365

    reports_dir = storage.get_run_dir() / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    file_path = str(reports_dir / f"{project_id}_report.txt")
    with open(file_path, "w") as f:
        f.write("Business Impact Report\n")
        f.write("========================\n")
        f.write(f"Naive Cost: ${naive_cost:,.2f}\n")
        f.write(f"Optimized Cost: ${opt_cost:,.2f}\n")
        f.write(f"Daily Savings: ${daily_savings:,.2f}\n")
        f.write(f"Annual Savings: ${annual_savings:,.2f}\n")

    report = Report(
        project_id=project.id,
        report_type=req.report_type,
        file_path=file_path
    )
    db.add(report)
    db.commit()
    db.refresh(report)

    return report

@router.get("/", response_model=list[ReportResponse])
def get_reports(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return db.query(Report).filter(Report.project_id == project.id).all()

@router.get("/{report_id}/download")
def download_report(
    project_id: uuid.UUID,
    report_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    report = db.query(Report).filter(Report.id == report_id, Report.project_id == project_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="Report file not found on disk")
        
    return FileResponse(path=report.file_path, filename=os.path.basename(report.file_path), media_type='text/plain')
