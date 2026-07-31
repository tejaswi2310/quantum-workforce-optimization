from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import Project, User
from app.dependencies import get_current_active_user

router = APIRouter(prefix="/api/v1/projects/{project_id}/dashboard", tags=["dashboard"])

@router.get("/metrics")
def get_dashboard_metrics(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return {
        "success": True,
        "data": {
            "total_calls": 51240,
            "avg_sla": 82.5,
            "avg_agents": 58,
            "avg_handle_time": 240,
            "peak_hour": "10:00 AM"
        }
    }

@router.get("/analytics")
def get_dashboard_analytics(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return {
        "success": True,
        "data": {
            "calls_per_hour": [
                {"hour": 0, "calls": 120}, {"hour": 1, "calls": 80}, {"hour": 2, "calls": 60},
                {"hour": 8, "calls": 450}, {"hour": 10, "calls": 800}, {"hour": 14, "calls": 600}
            ],
            "calls_by_channel": [
                {"name": "Voice", "value": 60},
                {"name": "Chat", "value": 30},
                {"name": "Email", "value": 10}
            ],
            "calls_by_day": [
                {"day": "Mon", "calls": 8000},
                {"day": "Tue", "calls": 7500}
            ]
        }
    }

@router.get("/whatif")
def get_whatif_scenario(
    project_id: str,
    volume_change: float = Query(0),
    budget: float = Query(5000),
    sla: float = Query(80),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    # Placeholder for what-if simulation
    return {
        "success": True,
        "data": {
            "projected_cost": 870 * (1 + volume_change/100),
            "projected_sla": max(0, min(100, sla - (volume_change * 0.5))),
            "agents_needed": int(58 * (1 + volume_change/100))
        }
    }
