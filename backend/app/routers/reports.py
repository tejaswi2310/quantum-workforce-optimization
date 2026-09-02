import os
import uuid
import pandas as pd
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import Project, User, Report, OptimizationRun
from app.schemas.report import ReportResponse, GenerateReportRequest
from app.dependencies import get_current_active_user
from app.services.storage_service import StorageService
from app.services.kpi_service import calculate_baseline_cost, calculate_optimized_cost

router = APIRouter(prefix="/api/v1/projects/{project_id}/reports", tags=["reports"])

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

    latest_run = db.query(OptimizationRun).filter(OptimizationRun.project_id == project_id).order_by(OptimizationRun.created_at.desc()).first()
    if not latest_run:
        raise HTTPException(status_code=404, detail="No optimization run found to generate a report from")

    storage = StorageService(latest_run.id)
    shifts_detailed_path = storage.result_path("agent_shifts_detailed.csv")

    opt_cost = calculate_optimized_cost(latest_run.id)
    naive_cost = calculate_baseline_cost(latest_run.id)

    if opt_cost is not None and naive_cost is not None:
        weekly_savings = max(0.0, naive_cost - opt_cost)
        daily_savings = weekly_savings / 7.0
        annual_savings = weekly_savings * 52.0  # 52-week projection from the 168-hour week
    else:
        weekly_savings = None
        daily_savings = None
        annual_savings = None

    reports_dir = storage.get_run_dir() / "reports"
    reports_dir.mkdir(parents=True, exist_ok=True)
    file_path = str(reports_dir / f"{project_id}_report.txt")
    with open(file_path, "w") as f:
        f.write("Business Impact Report\n")
        f.write("========================\n")

        def fmt(v): return f"${v:,.2f}" if v is not None else "N/A"

        f.write(f"Naive Cost: {fmt(naive_cost)}\n")
        f.write(f"Optimized Cost: {fmt(opt_cost)}\n")
        f.write(f"Weekly Savings: {fmt(weekly_savings)}\n")
        f.write(f"Daily Savings: {fmt(daily_savings)}\n")
        f.write(f"Annual Savings (Projected): {fmt(annual_savings)}\n")

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
