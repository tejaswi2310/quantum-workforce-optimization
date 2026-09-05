from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import OptimizationRun
from app.services.storage_service import StorageService
import pandas as pd
import uuid
import os
import math

from app.services.kpi_service import get_peak_hour, get_average_wage, calculate_optimized_cost, calculate_baseline_cost
from app.core_engine.queue.queue_simulator import required_agents_for_sla
from app.routers.dashboard import _load_queue_results_cached, sanitize_float

demo_router = APIRouter(prefix="/api/v1/dashboard/demo", tags=["dashboard_demo"])

def get_latest_global_run(db: Session) -> OptimizationRun:
    latest_run = db.query(OptimizationRun).order_by(OptimizationRun.created_at.desc()).first()
    if not latest_run:
        raise HTTPException(status_code=404, detail="No optimization runs found globally")
    return latest_run

def safe_read_csv_to_dict(path):
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path)
        # Handle nan values gracefully for JSON serialization
        df = df.replace({float('nan'): None})
        return df.to_dict(orient="records")
    except Exception:
        return None

@demo_router.get("/datasets")
def get_demo_datasets(db: Session = Depends(get_db)):
    """Returns the parsed DataFrames for the Streamlit dashboard as JSON records."""
    latest_run = get_latest_global_run(db)
    storage = StorageService(latest_run.id)
    
    return {
        "success": True,
        "run_id": str(latest_run.id),
        "data": {
            "raw": safe_read_csv_to_dict(storage.data_path("raw/synthetic_call_center.csv")),
            "forecast": safe_read_csv_to_dict(storage.data_path("processed/forecast_results.csv")),
            "classical": safe_read_csv_to_dict(storage.result_path("classical_optimization_schedule.csv")),
            "shift": safe_read_csv_to_dict(storage.result_path("shift_schedule.csv")),
            "quantum": safe_read_csv_to_dict(storage.result_path("quantum_classical_comparison.csv")),
            "validation": safe_read_csv_to_dict(storage.result_path("queue_validation_results.csv")),
        }
    }

@demo_router.get("/kpis")
def get_demo_kpis(db: Session = Depends(get_db)):
    """Returns the calculated KPI metrics for the latest global run."""
    latest_run = get_latest_global_run(db)
    
    opt_cost = calculate_optimized_cost(latest_run.id)
    baseline_cost = calculate_baseline_cost(latest_run.id)
    
    opt_cost_val = opt_cost if opt_cost is not None else 0.0
    baseline_cost_val = baseline_cost if baseline_cost is not None else 0.0
    
    weekly_savings = max(0.0, baseline_cost_val - opt_cost_val)
    annual_savings = weekly_savings * 52.0
    
    return {
        "success": True,
        "run_id": str(latest_run.id),
        "data": {
            "Total Cost Raw": opt_cost_val,
            "Baseline Cost Raw": baseline_cost_val,
            "Weekly Savings": weekly_savings,
            "Annual Savings": annual_savings,
            "average_wage": get_average_wage(latest_run.id)
        }
    }

@demo_router.get("/whatif")
def get_demo_whatif(
    volume_change: float = Query(0, ge=0, le=1000),
    budget: float = Query(5000, gt=0),
    sla: float = Query(80, ge=0, le=100),
    db: Session = Depends(get_db)
):
    """Executes the Erlang-C what-if simulation on the latest run."""
    latest_run = get_latest_global_run(db)
    storage = StorageService(latest_run.id)
    queue_path = storage.result_path("queue_validation_results.csv")

    if not queue_path.exists():
        raise HTTPException(status_code=404, detail="Queue validation results not found")

    mtime = os.path.getmtime(queue_path)
    df_queue = _load_queue_results_cached(str(queue_path), mtime).copy()
    new_agents_needed = 0
    new_cost = 0.0

    avg_wage = get_average_wage(latest_run.id)

    # Compute required agents
    for row in df_queue.itertuples(index=False):
        base_calls = float(row.calls)
        # Note: volume_multiplier is passed as the actual multiplier, e.g. 1.2
        adjusted_calls = base_calls * volume_change
        c, A, achieved_sla, p_w = required_agents_for_sla(adjusted_calls, 300, 3600, sla / 100.0, 20)
        new_agents_needed += c
        if avg_wage is not None:
            new_cost += c * avg_wage

    if avg_wage is None:
        new_cost = None

    is_over_budget = None
    budget_variance = None
    
    if new_cost is not None:
        budget_variance = new_cost - budget
        is_over_budget = budget_variance > 0

    return {
        "success": True,
        "data": {
            "projected_cost": sanitize_float(new_cost),
            "projected_sla": sanitize_float(sla),
            "agents_needed": new_agents_needed,
            "budget": budget,
            "is_over_budget": is_over_budget,
            "budget_variance": sanitize_float(budget_variance)
        }
    }
