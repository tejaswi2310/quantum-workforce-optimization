import os
import pandas as pd
import sys
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), "backend"))
from app.services.storage_service import StorageService

def run_sanity_check():
    print("--- Running Phase 4 Sanity Check ---")
    
    run_id = StorageService.get_latest_run_id()
    if not run_id:
        print("No runs found.")
        sys.exit(1)
    storage = StorageService(run_id)
    
    # Check 1: CSVs exist
    expected_files = [
        storage.result_path("shift_schedule.csv"),
        storage.result_path("queue_validation_results.csv"),
        storage.result_path("agent_shifts_detailed.csv"),
        storage.result_path("erlang_requirement_validation.csv"),
        storage.data_path("processed/forecast_evaluation.csv")
    ]
    
    for f in expected_files:
        if not f.exists():
            print(f"FAIL: Missing expected file {f}")
            sys.exit(1)
            
    # Check 2: Scheduled agents >= Required agents (No Shortfall)
    df_shifts = pd.read_csv(storage.result_path("shift_schedule.csv"))
    if df_shifts['scheduled_agents'].lt(df_shifts['required_agents']).any():
        print("FAIL: Mathematical Inconsistency - Scheduled agents are less than required agents in some hours.")
        print(df_shifts[df_shifts['scheduled_agents'] < df_shifts['required_agents']])
        sys.exit(1)
        
    # Check 3: Queue Validation SLA >= 80%
    df_queue = pd.read_csv(storage.result_path("queue_validation_results.csv"))
    if df_queue['sla_percent'].lt(80.0).any():
        print("FAIL: Mathematical Inconsistency - SLA fell below target 80% despite Erlang-C requirement.")
        print(df_queue[df_queue['sla_percent'] < 80.0])
        sys.exit(1)
        
    print("PASS: Phase 4 Sanity Check completed. Pipeline is mathematically honest.")
    
if __name__ == "__main__":
    run_sanity_check()
