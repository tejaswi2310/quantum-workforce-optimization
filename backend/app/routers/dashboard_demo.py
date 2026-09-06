from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.models.database import get_db
from app.models.models import OptimizationRun
from app.services.storage_service import StorageService
import pandas as pd
import os
import math
import json
from pathlib import Path
from app.config import settings

from app.services.kpi_service import get_average_wage, calculate_optimized_cost, calculate_baseline_cost
from app.core_engine.queue.queue_simulator import required_agents_for_sla, erlang_c
from app.routers.dashboard import _load_queue_results_cached, sanitize_float

demo_router = APIRouter(prefix="/api/v1/dashboard/demo", tags=["dashboard_demo"])

def get_latest_global_run(db: Session) -> OptimizationRun:
    runs = db.query(OptimizationRun).filter(OptimizationRun.status == "COMPLETED").order_by(OptimizationRun.created_at.desc()).all()

    for run in runs:
        storage = StorageService(run.id)
        required_artifacts = [
            storage.result_path("queue_validation_results.csv"),
            storage.result_path("classical_optimization_schedule.csv"),
            storage.result_path("shift_schedule.csv"),
            storage.result_path("quantum_classical_comparison.csv"),
            storage.data_path("raw/synthetic_call_center.csv"),
            storage.data_path("processed/forecast_results.csv")
        ]
        if all(path.exists() for path in required_artifacts):
            return run

    raise HTTPException(status_code=404, detail="No optimization runs found globally with complete artifacts")

def safe_read_csv_to_dict(path):
    if not os.path.exists(path):
        return None
    try:
        df = pd.read_csv(path)
        df = df.replace({float("nan"): None})
        return df.to_dict(orient="records")
    except Exception:
        return None

def get_demo_metadata():
    repo_root = Path(__file__).resolve().parent.parent.parent.parent
    meta_path = repo_root / "demo_data" / "metadata.json"
    if meta_path.exists():
        with open(meta_path, "r") as f:
            return json.load(f)
    return {}

@demo_router.get("/datasets")
def get_demo_datasets(db: Session = Depends(get_db)):
    if settings.DASHBOARD_DEMO_MODE == "readonly":
        meta = get_demo_metadata()
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        demo_dir = repo_root / "demo_data"
        return {
            "success": True,
            "run_id": meta.get("run_id", "demo-readonly-run"),
            "data": {
                "raw": safe_read_csv_to_dict(demo_dir / "raw/synthetic_call_center.csv"),
                "forecast": safe_read_csv_to_dict(demo_dir / "processed/forecast_results.csv"),
                "classical": safe_read_csv_to_dict(demo_dir / "results/classical_optimization_schedule.csv"),
                "shift": safe_read_csv_to_dict(demo_dir / "results/shift_schedule.csv"),
                "quantum": safe_read_csv_to_dict(demo_dir / "results/quantum_classical_comparison.csv"),
                "validation": safe_read_csv_to_dict(demo_dir / "results/queue_validation_results.csv"),
            }
        }

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
    if settings.DASHBOARD_DEMO_MODE == "readonly":
        meta = get_demo_metadata()
        opt_cost_val = meta.get("optimized_cost", 0.0)
        baseline_cost_val = meta.get("baseline_cost", 0.0)
        weekly_savings = max(0.0, baseline_cost_val - opt_cost_val)
        annual_savings = weekly_savings * 52.0
        return {
            "success": True,
            "run_id": meta.get("run_id", "demo-readonly-run"),
            "data": {
                "Total Cost Raw": opt_cost_val,
                "Baseline Cost Raw": baseline_cost_val,
                "Weekly Savings": weekly_savings,
                "Annual Savings": annual_savings,
                "average_wage": meta.get("average_wage", 20.0)
            }
        }

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
    volume_change: float = Query(0.0, ge=-100.0, le=1000.0),
    budget: float = Query(5000, gt=0),
    sla: float = Query(80, ge=0, le=100),
    db: Session = Depends(get_db)
):
    if settings.DASHBOARD_DEMO_MODE == "readonly":
        repo_root = Path(__file__).resolve().parent.parent.parent.parent
        queue_path = repo_root / "demo_data" / "results" / "queue_validation_results.csv"
        meta = get_demo_metadata()
        avg_wage = meta.get("average_wage", 20.0)
    else:
        latest_run = get_latest_global_run(db)
        storage = StorageService(latest_run.id)
        queue_path = storage.result_path("queue_validation_results.csv")
        avg_wage = get_average_wage(latest_run.id)

    if not queue_path.exists():
        raise HTTPException(status_code=404, detail="Queue validation results not found")

    mtime = os.path.getmtime(queue_path)
    df_queue = _load_queue_results_cached(str(queue_path), mtime).copy()
    new_agents_needed = 0
    new_cost = 0.0

    total_calls = 0.0
    total_sla_calls = 0.0
    total_wait_time = 0.0
    total_queue_length = 0.0

    for row in df_queue.itertuples(index=False):
        base_calls = float(row.calls)
        adjusted_calls = base_calls * (1 + volume_change / 100.0)
        c, A, achieved_sla, p_w = required_agents_for_sla(adjusted_calls, 300, 3600, sla / 100.0, 20)
        new_agents_needed += c
        if avg_wage is not None:
            new_cost += c * avg_wage

        total_calls += adjusted_calls
        scheduled = float(getattr(row, "agents", getattr(row, "scheduled_agents", c)))
        p_w_current = erlang_c(scheduled, A)

        if scheduled > A:
            sla_current = 1.0 - p_w_current * math.exp(-(scheduled - A) * 20 / 300)
            asa_current = (p_w_current * 300) / (scheduled - A)
            q_len = p_w_current * A / (scheduled - A)
        else:
            sla_current = 0.0
            asa_current = 300.0
            q_len = adjusted_calls

        total_sla_calls += adjusted_calls * max(0.0, min(1.0, sla_current))
        total_wait_time += adjusted_calls * max(0.0, asa_current)
        total_queue_length += q_len

    if avg_wage is None:
        new_cost = None

    is_over_budget = None
    budget_variance = None
    if new_cost is not None:
        budget_variance = new_cost - budget
        is_over_budget = budget_variance > 0

    expected_sla = (total_sla_calls / total_calls * 100.0) if total_calls > 0 else 100.0
    expected_wait_seconds = (total_wait_time / total_calls) if total_calls > 0 else 0.0
    expected_queue_length = int(total_queue_length / len(df_queue)) if len(df_queue) > 0 else 0

    return {
        "success": True,
        "data": {
            "projected_cost": sanitize_float(new_cost),
            "projected_sla": sanitize_float(sla),
            "agents_needed": new_agents_needed,
            "budget": budget,
            "is_over_budget": is_over_budget,
            "budget_variance": sanitize_float(budget_variance),
            "expected_sla": sanitize_float(expected_sla),
            "expected_wait_seconds": sanitize_float(expected_wait_seconds),
            "expected_queue_length": expected_queue_length
        }
    }
