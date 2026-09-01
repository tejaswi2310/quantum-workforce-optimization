import pytest
import pandas as pd
import uuid
import os
import json
from app.services.storage_service import StorageService
from app.core_engine.optimization.classical_optimizer import run_classical_optimization

@pytest.fixture
def mock_d2_workspace(tmp_path, monkeypatch):
    """
    Creates an isolated workspace with a tiny forecast to test D2 exact features.
    """
    run_id = uuid.uuid4()
    storage = StorageService(run_id)
    storage.ensure_run_dirs()
    
    # 1. Create a minimal demand forecast for 1 hour, 1 skill
    os.makedirs(storage.data_path("processed"), exist_ok=True)
    df_forecast = pd.DataFrame([{
        'date': '2026-01-01',
        'hour': 8,
        'interval': '08:00-09:00',
        'channel': 'Voice',
        'skill_group': 'General',
        'predicted_calls': 50  # Enough to need a few agents
    }])
    df_forecast.to_csv(storage.data_path("processed/forecast_results.csv"), index=False)
    
    return run_id, storage

def create_roster(storage, agents):
    os.makedirs(storage.data_path("raw"), exist_ok=True)
    df_roster = pd.DataFrame(agents)
    df_roster.to_csv(storage.data_path("raw/synthetic_roster.csv"), index=False)

def test_missing_roster_fails_cleanly(mock_d2_workspace, monkeypatch):
    """TEST B: The optimizer must fail if there is no workforce data. No 120-agent generation."""
    run_id, storage = mock_d2_workspace
    
    # Mock os.path.exists to return False for the global fallback
    original_exists = os.path.exists
    def mock_exists(path):
        path_str = str(path)
        if "data\\raw\\synthetic_roster.csv" in path_str or "data/raw/synthetic_roster.csv" in path_str:
            if str(storage.run_id) not in path_str:
                return False
        return original_exists(path)
        
    monkeypatch.setattr(os.path, "exists", mock_exists)
    
    with pytest.raises(FileNotFoundError):
        run_classical_optimization(run_id)

def test_real_roster_ids_and_duplicate_assignment(mock_d2_workspace):
    """TEST A & E: Optimizer only schedules agents from the roster and no duplicate simultaneous shifts."""
    run_id, storage = mock_d2_workspace
    
    create_roster(storage, [
        {'agent_id': 'EMP-1', 'skills': 'General', 'wage': 15.0},
        {'agent_id': 'EMP-2', 'skills': 'General', 'wage': 15.0}
    ])
    
    run_classical_optimization(run_id)
    
    df_shifts = pd.read_csv(storage.result_path("agent_shifts_detailed.csv"))
    
    # Assert no fabricated agents
    assert set(df_shifts['agent_id'].unique()).issubset({'EMP-1', 'EMP-2'})
    
    # Assert no duplicate assignments for the same agent
    assert len(df_shifts) == len(df_shifts['agent_id'].unique())

def test_skill_correctness(mock_d2_workspace):
    """TEST C: Agent with skill Y cannot answer skill X."""
    run_id, storage = mock_d2_workspace
    
    # Only EMP-1 has the required 'General' skill. EMP-2 has 'Sales'.
    create_roster(storage, [
        {'agent_id': 'EMP-1', 'skills': 'General', 'wage': 15.0},
        {'agent_id': 'EMP-2', 'skills': 'Sales', 'wage': 15.0}
    ])
    
    run_classical_optimization(run_id)
    
    df_shifts = pd.read_csv(storage.result_path("agent_shifts_detailed.csv"))
    
    # EMP-2 should NOT be scheduled for the General requirement
    assert 'EMP-2' not in df_shifts['agent_id'].values

def test_heterogeneous_cost(mock_d2_workspace):
    """TEST D: Given two identical agents, prefer the cheaper one."""
    run_id, storage = mock_d2_workspace
    
    # Demand is low enough that only one agent is needed, or at least they won't both be scheduled
    # if one is extremely expensive. Actually, if 50 calls, required agents ~ 6. 
    # Let's adjust demand so exactly 1 is needed to see the preference.
    df_forecast = pd.DataFrame([{
        'date': '2026-01-01',
        'hour': 8,
        'interval': '08:00-09:00',
        'channel': 'Voice',
        'skill_group': 'General',
        'predicted_calls': 1  # 1 call guarantees exactly 1 agent needed
    }])
    df_forecast.to_csv(storage.data_path("processed/forecast_results.csv"), index=False)
    
    create_roster(storage, [
        {'agent_id': 'CHEAP', 'skills': 'General', 'wage': 10.0},
        {'agent_id': 'EXPENSIVE', 'skills': 'General', 'wage': 500.0}
    ])
    
    run_classical_optimization(run_id)
    
    df_shifts = pd.read_csv(storage.result_path("agent_shifts_detailed.csv"))
    
    assert 'CHEAP' in df_shifts['agent_id'].values
    assert 'EXPENSIVE' not in df_shifts['agent_id'].values

def test_shortfall_honesty(mock_d2_workspace):
    """TEST G: Must explicitly expose shortfall when understaffed."""
    run_id, storage = mock_d2_workspace
    
    # Demand is 50 calls (~6 agents), but we only give it 1 agent.
    create_roster(storage, [
        {'agent_id': 'EMP-1', 'skills': 'General', 'wage': 15.0}
    ])
    
    run_classical_optimization(run_id)
    
    with open(storage.result_path("optimization_metrics.json"), "r") as f:
        metrics = json.load(f)
        
    assert metrics["optimization_status"] == "OPTIMAL_WITH_SHORTFALL"
    assert metrics["staffing_shortfall"] > 0

def test_determinism(mock_d2_workspace):
    """TEST H: Run identical input twice, verify stable results."""
    run_id, storage = mock_d2_workspace
    
    create_roster(storage, [
        {'agent_id': 'EMP-1', 'skills': 'General', 'wage': 15.0},
        {'agent_id': 'EMP-2', 'skills': 'General', 'wage': 15.0},
        {'agent_id': 'EMP-3', 'skills': 'General', 'wage': 15.0}
    ])
    
    run_classical_optimization(run_id)
    df_shifts_1 = pd.read_csv(storage.result_path("agent_shifts_detailed.csv"))
    
    run_classical_optimization(run_id)
    df_shifts_2 = pd.read_csv(storage.result_path("agent_shifts_detailed.csv"))
    
    pd.testing.assert_frame_equal(df_shifts_1, df_shifts_2)
