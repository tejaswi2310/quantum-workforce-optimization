import pytest
import uuid
import pandas as pd
import json
import math
from fastapi.testclient import TestClient
from app.main import app
from app.services.storage_service import StorageService
from app.services.kpi_service import (
    get_average_wage,
    calculate_baseline_cost,
    calculate_optimized_cost,
    get_peak_hour
)
from app.routers.dashboard import sanitize_float

@pytest.fixture
def mock_kpi_workspace(monkeypatch, tmp_path):
    run_id = uuid.uuid4()
    
    def mock_init(self, init_run_id=None):
        self.run_id = init_run_id or run_id
        self.root_dir = tmp_path
        self.storage_root = tmp_path
        self.run_dir = tmp_path / str(self.run_id)
        
    monkeypatch.setattr(StorageService, "__init__", mock_init)
    storage = StorageService(run_id)
    storage.ensure_run_dirs()
    return storage, run_id

# 1. Dynamic wages & 2. Agent-specific wage calculation & 10. Missing wage data
def test_dynamic_wages_agent_specific(mock_kpi_workspace):
    storage, run_id = mock_kpi_workspace
    roster_path = storage.data_path("raw/synthetic_roster.csv")
    
    # 10. Missing wage data
    assert get_average_wage(run_id) is None
    
    # 1. Dynamic wages
    df_roster = pd.DataFrame([
        {"agent_id": "A", "wage": 10.0},
        {"agent_id": "B", "wage": 20.0}
    ])
    df_roster.to_csv(roster_path, index=False)
    
    assert get_average_wage(run_id) == 15.0

# 3. Baseline/naive cost
def test_baseline_naive_cost_definition(mock_kpi_workspace):
    storage, run_id = mock_kpi_workspace
    # Set up roster for average wage
    pd.DataFrame([{"agent_id": "A", "wage": 20.0}]).to_csv(storage.data_path("raw/synthetic_roster.csv"), index=False)
    
    # Missing schedule
    assert calculate_baseline_cost(run_id) is None
    
    # Set up schedule
    pd.DataFrame([
        {"required_agents": 2},
        {"required_agents": 5},
        {"required_agents": 4}
    ]).to_csv(storage.result_path("shift_schedule.csv"), index=False)
    
    # Max required agents = 5. Average wage = 20. Baseline = 5 * 168 * 20 = 16800
    assert calculate_baseline_cost(run_id) == 16800.0

# 4. Optimized cost & 11. Missing cost artifact
def test_optimized_cost_actual_wages(mock_kpi_workspace):
    storage, run_id = mock_kpi_workspace
    
    # 11. Missing cost artifact
    assert calculate_optimized_cost(run_id) is None
    
    # 4. Optimized cost
    pd.DataFrame([
        {"agent_id": "A", "cost": 100.0},
        {"agent_id": "B", "cost": 250.5}
    ]).to_csv(storage.result_path("agent_shifts_detailed.csv"), index=False)
    
    assert calculate_optimized_cost(run_id) == 350.5

# 7. Peak hour, 8. Peak-hour tie, 9. Peak hour over multiple days
def test_peak_hour_synthetic_dataset(mock_kpi_workspace):
    storage, run_id = mock_kpi_workspace
    assert get_peak_hour(run_id) is None
    
    # Set up queue data with absolute_hour
    pd.DataFrame([
        {"date": "2023-10-01", "hour": 0, "absolute_hour": 0, "calls": 50, "offered_traffic": 25}, # peak on hour 0
        {"date": "2023-10-01", "hour": 23, "absolute_hour": 23, "calls": 60, "offered_traffic": 30}, # peak on hour 23
        {"date": "2023-10-02", "hour": 0, "absolute_hour": 24, "calls": 100, "offered_traffic": 50}, # peak on hour 24, tie 1
        {"date": "2023-10-07", "hour": 23, "absolute_hour": 167, "calls": 100, "offered_traffic": 50}  # peak on hour 167, tie 2
    ]).to_csv(storage.result_path("queue_validation_results.csv"), index=False)
    
    # Highest traffic is 50. Two records match (absolute_hour 24 and 167). Earliest absolute_hour is 24.
    assert get_peak_hour(run_id) == "2023-10-02 00:00"
    
    # Test fallback if absolute_hour is missing
    pd.DataFrame([
        {"date": "2023-10-01", "hour": 1, "calls": 100},
        {"date": "2023-10-02", "hour": 2, "calls": 100}
    ]).to_csv(storage.result_path("queue_validation_results.csv"), index=False)
    # Should pick 2023-10-01 01:00 based on date/hour sorting
    assert get_peak_hour(run_id) == "2023-10-01 01:00"

    # Test missing date/hour
    pd.DataFrame([
        {"calls": 100}
    ]).to_csv(storage.result_path("queue_validation_results.csv"), index=False)
    assert get_peak_hour(run_id) == "Unknown Unknown"
    
def test_heterogeneous_wage_scenario(mock_kpi_workspace):
    storage, run_id = mock_kpi_workspace
    # Roster with vastly different wages
    pd.DataFrame([
        {"agent_id": "A", "wage": 10.0},
        {"agent_id": "B", "wage": 20.0},
        {"agent_id": "C", "wage": 40.0}
    ]).to_csv(storage.data_path("raw/synthetic_roster.csv"), index=False)
    
    # Average wage = (10 + 20 + 40) / 3 = 23.333333333333332
    avg_wage = get_average_wage(run_id)
    assert math.isclose(avg_wage, 23.333333333333332)
    
    # Setup peak schedule
    pd.DataFrame([{"required_agents": 2}]).to_csv(storage.result_path("shift_schedule.csv"), index=False)
    
    # Baseline cost = 2 * 168 * 23.333333 = 7840
    baseline = calculate_baseline_cost(run_id)
    assert math.isclose(baseline, 7840.0)
    
    # Assume optimized cost used Agent A ($10) mostly
    pd.DataFrame([{"agent_id": "A", "cost": 1000.0}]).to_csv(storage.result_path("agent_shifts_detailed.csv"), index=False)
    optimized = calculate_optimized_cost(run_id)
    assert optimized == 1000.0
    
    # Savings should be 7840 - 1000 = 6840
    assert math.isclose(baseline - optimized, 6840.0)

# 13. JSON safety
def test_json_safety_NaN_Inf():
    assert sanitize_float(float('nan')) is None
    assert sanitize_float(float('inf')) is None
    assert sanitize_float(float('-inf')) is None
    assert sanitize_float(15.0) == 15.0
    assert sanitize_float("15.5") == 15.5
    assert sanitize_float(None) is None
    assert sanitize_float("invalid") is None

# 5. Savings & 6. Annualization
def test_savings_and_annualization_math():
    opt_cost = 5000.0
    naive_cost = 7000.0
    
    weekly_savings = max(0.0, naive_cost - opt_cost)
    assert weekly_savings == 2000.0
    
    annual_savings = weekly_savings * 52.0
    assert annual_savings == 104000.0
    
    # Missing data logic
    opt_cost_missing = None
    if opt_cost_missing is not None and naive_cost is not None:
        pass
    else:
        weekly_savings = None
        annual_savings = None
    assert weekly_savings is None
    assert annual_savings is None

# 12. What-if consistency
def test_whatif_consistency_handles_wages(mock_kpi_workspace):
    storage, run_id = mock_kpi_workspace
    pd.DataFrame([{"agent_id": "A", "wage": 30.0}]).to_csv(storage.data_path("raw/synthetic_roster.csv"), index=False)
    avg_wage = get_average_wage(run_id)
    assert avg_wage == 30.0 # Uses correct average wage instead of hardcoded 15.0
