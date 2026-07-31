import os
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import Project, User, Report
from app.schemas.report import ReportResponse, GenerateReportRequest
from app.dependencies import get_current_active_user

router = APIRouter(prefix="/api/v1/projects/{project_id}/reports", tags=["reports"])

REPORT_DIR = "reports"
os.makedirs(REPORT_DIR, exist_ok=True)

@router.post("/generate", response_model=ReportResponse)
def generate_report(
    project_id: str,
    req: GenerateReportRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    file_path = os.path.join(REPORT_DIR, f"{project_id}_report.txt")
    with open(file_path, "w") as f:
        f.write("Business Impact Report\n")
        f.write("========================\n")
        f.write("Naive Cost: $1,440\n")
        f.write("Optimized Cost: $870\n")
        f.write("Daily Savings: $570\n")
        f.write("Annual Savings: $208,050\n")

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
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return db.query(Report).filter(Report.project_id == project.id).all()

@router.get("/{report_id}/download")
def download_report(
    project_id: str,
    report_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    report = db.query(Report).filter(Report.id == report_id, Report.project_id == project_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")
    
    if not os.path.exists(report.file_path):
        raise HTTPException(status_code=404, detail="Report file not found on disk")
        
    return FileResponse(path=report.file_path, filename=os.path.basename(report.file_path), media_type='text/plain')
