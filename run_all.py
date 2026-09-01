"""
Master orchestration script for the Quantum Workforce Optimizer pipeline.
This script runs data generation, AI demand forecasting, classical optimization,
shift mapping, quantum simulation, and queue validation sequentially.
"""
import os
import sys
import uuid

# Ensure backend is in sys.path
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))

def main():
    print("==================================================")
    print("STARTING QUANTUM WORKFORCE OPTIMIZATION PIPELINE")
    print("==================================================")
    
    run_id = uuid.uuid4()
    print(f"Run ID: {run_id}")
    
    from app.models.database import SessionLocal
    from app.models.models import OptimizationRun
    
    # Create the db record
    db = SessionLocal()
    try:
        opt_run = OptimizationRun(id=run_id, run_type="full_pipeline", parameters={}, status="CREATED")
        db.add(opt_run)
        db.commit()
    except Exception as e:
        print(f"Database error: {e}")
        return
    finally:
        db.close()

    # Execute canonical pipeline
    from app.services.orchestration_service import execute_optimization_pipeline
    execute_optimization_pipeline(run_id)
    
    print("\n==================================================")
    print("PIPELINE COMPLETED!")
    print(f"All outputs generated in runtime/runs/{run_id}/ directories.")
    print("To launch the dashboard, run: streamlit run src/dashboard.py")
    print("==================================================")

if __name__ == "__main__":
    main()
