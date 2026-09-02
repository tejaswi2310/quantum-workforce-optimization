import pytest
import pandas as pd
import numpy as np
import uuid
import math
import os
from unittest.mock import patch, MagicMock

from app.routers.dashboard import sanitize_float
from app.core_engine.optimization.classical_optimizer import run_classical_optimization
from app.core_engine.queue.queue_simulator import run_queue_simulation

# P0-A: Test 3: Dashboard JSON safety
def test_dashboard_json_safety():
    assert sanitize_float(None) is None
    assert sanitize_float(np.nan) is None
    assert sanitize_float(math.nan) is None
    assert sanitize_float(float('inf')) is None
    assert sanitize_float(float('-inf')) is None

# P0-A: Test 4: Finite metric preservation
def test_finite_metric_preservation():
    assert sanitize_float(15.0) == 15.0
    assert sanitize_float(0.0) == 0.0
    assert sanitize_float(87.5) == 87.5
    assert sanitize_float("15.0") == 15.0

# P0-B: Test 1 & 2: Pooled staffing calculation and Skill isolation
@patch("app.core_engine.optimization.classical_optimizer.StorageService")
def test_pooled_staffing_and_skill_isolation(MockStorageService, tmp_path):
    mock_storage = MockStorageService.return_value
    mock_storage.ensure_run_dirs.return_value = None
    mock_storage.data_path.side_effect = lambda path: tmp_path / path
    mock_storage.result_path.side_effect = lambda path: tmp_path / path
    
    (tmp_path / "processed").mkdir(parents=True, exist_ok=True)
    (tmp_path / "raw").mkdir(parents=True, exist_ok=True)
    
    # 7 days * 24 hours = 168 hours
    dates = pd.date_range("2026-06-30", periods=7).strftime("%Y-%m-%d").tolist()
    forecast_data = []
    
    for d in dates:
        for h in range(24):
            forecast_data.append({"date": d, "hour": h, "interval": f"{h:02d}", "channel": "Voice", "skill_group": "Billing", "predicted_calls": 5})
            forecast_data.append({"date": d, "hour": h, "interval": f"{h:02d}", "channel": "Chat", "skill_group": "Billing", "predicted_calls": 5})
            forecast_data.append({"date": d, "hour": h, "interval": f"{h:02d}", "channel": "Voice", "skill_group": "Technical", "predicted_calls": 8})

    df_forecast = pd.DataFrame(forecast_data)
    df_forecast.to_csv(tmp_path / "processed/forecast_results.csv", index=False)
    
    # Fake roster with extremely high max_weekly_hours so we don't get infeasible
    roster_data = []
    for i in range(20):
        # Evenly split agents between Billing and Technical
        skill = "Billing" if i < 10 else "Technical"
        roster_data.append({"agent_id": f"A{i}", "skills": skill, "wage": 15, "max_weekly_hours": 168, "availability": "1"*168})
    df_roster = pd.DataFrame(roster_data)
    df_roster.to_csv(tmp_path / "raw/synthetic_roster.csv", index=False)
    
    class SolverReached(Exception): pass
    
    with patch("app.core_engine.optimization.classical_optimizer.cp_model.CpSolver") as MockSolver:
        mock_solver_inst = MockSolver.return_value
        mock_solver_inst.Solve.side_effect = SolverReached
        
        with pytest.raises(SolverReached):
            run_classical_optimization(uuid.uuid4())

    assert os.path.exists(tmp_path / "erlang_requirement_validation.csv")
    df_val = pd.read_csv(tmp_path / "erlang_requirement_validation.csv")
    
    billing_row = df_val[df_val['skill_group'] == 'Billing'].iloc[0]
    assert billing_row['predicted_calls'] == 10, "Calls for Billing should be pooled to 10"
    
    tech_row = df_val[df_val['skill_group'] == 'Technical'].iloc[0]
    assert tech_row['predicted_calls'] == 8, "Calls for Technical should be 8"

# Test 5 & 6: 168-hour timeline and Queue integration
@patch("app.core_engine.queue.queue_simulator.StorageService")
def test_168_hour_timeline_and_queue_integration(MockStorageService, tmp_path):
    mock_storage = MockStorageService.return_value
    mock_storage.ensure_run_dirs.return_value = None
    mock_storage.data_path.side_effect = lambda path: tmp_path / path
    mock_storage.result_path.side_effect = lambda path: tmp_path / path
    
    dates = pd.date_range("2026-06-30", periods=7).strftime("%Y-%m-%d").tolist()
    
    # Create fake 168-hour classical schedule
    schedule_data = []
    abs_hour = 0
    for d in dates:
        for h in range(24):
            # Normal queue load
            schedule_data.append({
                "date": d,
                "hour": h,
                "absolute_hour": abs_hour,
                "calls": 10, 
                "scheduled_agents": 4, 
                "required_agents": 4
            })
            abs_hour += 1
            
    # Inject one mathematically undefined/overloaded hour (Issue 6)
    schedule_data[50]["calls"] = 1000  # huge load
    schedule_data[50]["scheduled_agents"] = 1 # impossible to handle

    df_schedule = pd.DataFrame(schedule_data)
    df_schedule.to_csv(tmp_path / "classical_optimization_schedule.csv", index=False)
    
    run_queue_simulation(uuid.uuid4())
    
    assert os.path.exists(tmp_path / "queue_validation_results.csv")
    df_queue = pd.read_csv(tmp_path / "queue_validation_results.csv")
    
    # Verify 168 hours exact length
    assert len(df_queue) == 168, "Must produce exactly 168 hours of queue validation"
    
    # Chronological ordering and absolute mapping
    assert df_queue.iloc[0]['absolute_hour'] == 0
    assert df_queue.iloc[0]['hour'] == 0
    
    assert df_queue.iloc[23]['absolute_hour'] == 23
    assert df_queue.iloc[23]['hour'] == 23
    
    assert df_queue.iloc[24]['absolute_hour'] == 24
    assert df_queue.iloc[24]['hour'] == 0
    
    assert df_queue.iloc[167]['absolute_hour'] == 167
    assert df_queue.iloc[167]['hour'] == 23
    
    # Overloaded hour safely handled (JSON-safe NaN via sanitize_float elsewhere, but None in Python memory)
    # pandas writes None as empty string -> reads back as NaN
    overloaded_row = df_queue.iloc[50]
    assert np.isnan(overloaded_row['sla_percent'])
    assert np.isnan(overloaded_row['asa_seconds'])
    
    # Check that non-overloaded hours have finite numbers
    normal_row = df_queue.iloc[0]
    assert not np.isnan(normal_row['sla_percent'])
    assert not np.isnan(normal_row['asa_seconds'])

# Test 7: Availability Fallback Normalization
@patch("app.core_engine.optimization.classical_optimizer.StorageService")
def test_availability_fallback_normalization(MockStorageService, tmp_path):
    mock_storage = MockStorageService.return_value
    mock_storage.ensure_run_dirs.return_value = None
    mock_storage.data_path.side_effect = lambda path: tmp_path / path
    mock_storage.result_path.side_effect = lambda path: tmp_path / path
    
    (tmp_path / "processed").mkdir(parents=True, exist_ok=True)
    (tmp_path / "raw").mkdir(parents=True, exist_ok=True)
    
    # Create simple forecast
    dates = pd.date_range("2026-06-30", periods=7).strftime("%Y-%m-%d").tolist()
    forecast_data = []
    for d in dates:
        for h in range(24):
            forecast_data.append({"date": d, "hour": h, "interval": f"{h:02d}", "skill_group": "Billing", "predicted_calls": 1})
    pd.DataFrame(forecast_data).to_csv(tmp_path / "processed/forecast_results.csv", index=False)
    
    pd.DataFrame([{"shift_id": "S1", "name": "Base", "start_hour": 8, "duration_hours": 8, "break_hour_offset": 4, "is_overtime": False, "x": "[1]*24"}]).to_csv(tmp_path / "raw/shift_templates.csv", index=False)

    class SolverReached(Exception): pass
    
    # Roster with different availability scenarios
    def run_with_roster(roster_df):
        roster_df.to_csv(tmp_path / "raw/synthetic_roster.csv", index=False)
        with patch("app.core_engine.optimization.classical_optimizer.cp_model.CpSolver") as MockSolver:
            MockSolver.return_value.Solve.side_effect = SolverReached
            with pytest.raises(SolverReached):
                run_classical_optimization(uuid.uuid4())
                
    # 1. Missing availability
    run_with_roster(pd.DataFrame([{"agent_id": "A1", "skills": "Billing", "wage": 15, "max_weekly_hours": 40}]))
    
    # 2. 24-character availability
    run_with_roster(pd.DataFrame([{"agent_id": "A1", "skills": "Billing", "wage": 15, "max_weekly_hours": 40, "availability": "10"*12}]))
    
    # 3. 168-character availability
    run_with_roster(pd.DataFrame([{"agent_id": "A1", "skills": "Billing", "wage": 15, "max_weekly_hours": 40, "availability": "1"*168}]))
    
    # 4. > 168-character availability (should be truncated)
    run_with_roster(pd.DataFrame([{"agent_id": "A1", "skills": "Billing", "wage": 15, "max_weekly_hours": 40, "availability": "1"*200}]))
    
    # 5. Malformed availability (raises ValueError)
    roster_malformed = pd.DataFrame([{"agent_id": "A1", "skills": "Billing", "wage": 15, "max_weekly_hours": 40, "availability": "1"*100}])
    roster_malformed.to_csv(tmp_path / "raw/synthetic_roster.csv", index=False)
    with pytest.raises(ValueError, match="Must be exactly 24 or 168 characters"):
        run_classical_optimization(uuid.uuid4())
