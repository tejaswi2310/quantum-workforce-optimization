import uuid
import traceback
import datetime
from sqlalchemy.orm import Session
from app.models.database import SessionLocal
from app.models.models import OptimizationRun
from app.services.storage_service import StorageService

def update_run_status(run_id: uuid.UUID, status: str, error_message: str = None):
    """
    Updates the status of an optimization run in the database.
    """
    db = SessionLocal()
    try:
        run = db.query(OptimizationRun).filter(OptimizationRun.id == run_id).first()
        if run:
            run.status = status
            if error_message:
                run.error_message = error_message
            if status in ["COMPLETED", "FAILED"]:
                run.completed_at = datetime.datetime.utcnow()
            db.commit()
    except Exception as e:
        print(f"Failed to update run status for {run_id}: {e}")
    finally:
        db.close()

def execute_optimization_pipeline(run_id: uuid.UUID):
    """
    Executes the full workforce optimization pipeline sequentially.
    Updates the OptimizationRun database record through lifecycle states.
    """
    
    # 1. DATA GENERATING
    update_run_status(run_id, "DATA_GENERATING")
    try:
        from app.core_engine.common.data_generator import generate_data
        generate_data(run_id)
    except Exception as e:
        update_run_status(run_id, "FAILED", error_message=f"Data generation failed: {str(e)}")
        _log_error_to_storage(run_id, e)
        return

    # 2. FORECASTING
    update_run_status(run_id, "FORECASTING")
    try:
        from app.core_engine.forecasting.demand_forecaster import train_forecast
        train_forecast(run_id)
    except Exception as e:
        update_run_status(run_id, "FAILED", error_message=f"Forecasting failed: {str(e)}")
        _log_error_to_storage(run_id, e)
        return

    # 3. OPTIMIZING
    update_run_status(run_id, "OPTIMIZING")
    try:
        from app.core_engine.optimization.classical_optimizer import run_classical_optimization
        from app.core_engine.optimization.shift_optimizer import run_shift_optimization
        from app.core_engine.quantum.quantum_optimizer import run_quantum_optimization
        
        run_classical_optimization(run_id)
        run_quantum_optimization(run_id)
        run_shift_optimization(run_id)
    except Exception as e:
        update_run_status(run_id, "FAILED", error_message=f"Optimization failed: {str(e)}")
        _log_error_to_storage(run_id, e)
        return

    # 4. SIMULATING
    update_run_status(run_id, "SIMULATING")
    try:
        from app.core_engine.queue.queue_simulator import run_queue_simulation
        run_queue_simulation(run_id)
    except Exception as e:
        update_run_status(run_id, "FAILED", error_message=f"Queue simulation failed: {str(e)}")
        _log_error_to_storage(run_id, e)
        return

    # 5. REPORTING
    update_run_status(run_id, "REPORTING")
    try:
        # In the future, this is where a PDF/Text report generator can be natively called.
        # Currently, the storage files represent the reports.
        pass
    except Exception as e:
        update_run_status(run_id, "FAILED", error_message=f"Reporting failed: {str(e)}")
        _log_error_to_storage(run_id, e)
        return

    # 6. COMPLETED
    db = SessionLocal()
    try:
        run = db.query(OptimizationRun).filter(OptimizationRun.id == run_id).first()
        if run:
            import json
            import os
            storage = StorageService(run_id)
            metrics_path = storage.result_path("optimization_metrics.json")
            if os.path.exists(metrics_path):
                try:
                    with open(metrics_path, "r") as f:
                        metrics = json.load(f)

                    # Store metrics in results json column
                    current_results = run.results or {}
                    current_results.update(metrics)
                    run.results = current_results
                    
                    # If the optimizer explicitly failed or had shortfall, we can optionally
                    # keep track of the specific optimizer status in the DB
                    if "optimization_status" in metrics:
                        # Only override to FAILED if it actually failed; otherwise let COMPLETED stand
                        if metrics["optimization_status"] == "INFEASIBLE":
                            run.status = "FAILED"
                            run.error_message = "Optimization found no feasible solution"
                except json.JSONDecodeError as e:
                    run.status = "FAILED"
                    run.error_message = f"Artifact corrupted: metrics.json is malformed. Error: {str(e)}"
                    # Let the overall run status be COMPLETED, but we could also bubble it up
                    pass
                    
            db.commit()
    except Exception as e:
        print(f"Failed to update results for {run_id}: {e}")
    finally:
        db.close()
        
    update_run_status(run_id, "COMPLETED")


def _log_error_to_storage(run_id: uuid.UUID, exception: Exception):
    """
    Logs full stack trace to the isolated runtime storage safely, 
    away from normal API consumers.
    """
    storage = StorageService(run_id)
    storage.ensure_run_dirs()
    log_file = storage.report_path("error_trace.log")
    with open(log_file, "w") as f:
        f.write("Pipeline Execution Error\\n")
        f.write("="*30 + "\\n")
        f.write(traceback.format_exc())
