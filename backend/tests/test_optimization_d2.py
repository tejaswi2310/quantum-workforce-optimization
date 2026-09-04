import pytest
import pandas as pd
import uuid
import os
import json
from app.services.storage_service import StorageService
from app.core_engine.optimization.classical_optimizer import run_classical_optimization

def _make_168_hour_forecast(target_hour=8, target_demand=50, target_day=1):
    rows = []
    for day in range(1, 8):
        date_str = f'2026-01-{day:02d}'
        for hour in range(24):
            interval = f'{hour:02d}:00-{hour+1:02d}:00'
            calls = target_demand if (hour == target_hour and day == target_day) else 0
            rows.append({
                'date': date_str,
                'hour': hour,
                'interval': interval,
                'channel': 'Voice',
                'skill_group': 'General',
                'predicted_calls': calls
            })
    return pd.DataFrame(rows)

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
    df_forecast = _make_168_hour_forecast(target_hour=8, target_demand=50)
    df_forecast.to_csv(storage.data_path("processed/forecast_results.csv"), index=False)

    return run_id, storage

def create_roster(storage, agents):
    os.makedirs(storage.data_path("raw"), exist_ok=True)
    for agent in agents:
        if 'availability' not in agent:
            agent['availability'] = '1' * 168
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
    df_forecast = _make_168_hour_forecast(target_hour=8, target_demand=1)
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

def _load_metrics(storage):
    """Load optimization_metrics.json for a completed run."""
    with open(storage.result_path("optimization_metrics.json"), "r") as f:
        return json.load(f)


def _validate_shifts_invariants(df_shifts, valid_agent_ids, label):
    """
    Assert structural and business invariants on an agent_shifts_detailed DataFrame.
    Does NOT require any specific row ordering or that two runs produce identical assignments.
    """
    # All scheduled agents must come from the roster
    assert set(df_shifts['agent_id'].unique()).issubset(set(valid_agent_ids)), \
        f"{label}: scheduled agents not a subset of roster IDs"

    # No agent should have more than one shift on the same calendar day
    dup_check = df_shifts.groupby(['agent_id', 'date']).size()
    assert (dup_check <= 1).all(), \
        f"{label}: duplicate same-day assignments detected"

    # Every row must have a positive cost
    assert (df_shifts['cost'] > 0).all(), \
        f"{label}: shift rows with non-positive cost detected"


def test_determinism(mock_d2_workspace):
    """
    TEST H: Run identical input twice, verify stable reproducibility invariants.

    CP-SAT parallel search with multiple workers (num_search_workers=8) may return
    different but equally optimal assignments even with random_seed=42.  The
    reproducibility regression therefore validates objective value, feasibility,
    constraint, and business invariants rather than requiring identical row-level
    assignments.
    """
    run_id, storage = mock_d2_workspace
    valid_ids = ['EMP-1', 'EMP-2', 'EMP-3']

    create_roster(storage, [
        {'agent_id': 'EMP-1', 'skills': 'General', 'wage': 15.0},
        {'agent_id': 'EMP-2', 'skills': 'General', 'wage': 15.0},
        {'agent_id': 'EMP-3', 'skills': 'General', 'wage': 15.0}
    ])

    # --- Run 1 ---
    run_classical_optimization(run_id)
    df_shifts_1 = pd.read_csv(storage.result_path("agent_shifts_detailed.csv"))
    metrics_1 = _load_metrics(storage)

    # --- Run 2 ---
    run_classical_optimization(run_id)
    df_shifts_2 = pd.read_csv(storage.result_path("agent_shifts_detailed.csv"))
    metrics_2 = _load_metrics(storage)

    # 1. Solver status must be stable across both runs
    assert metrics_1["optimization_status"] == metrics_2["optimization_status"], (
        f"Solver status changed between runs: {metrics_1['optimization_status']} vs "
        f"{metrics_2['optimization_status']}"
    )
    # Both runs must reach feasibility (OPTIMAL or OPTIMAL_WITH_SHORTFALL)
    assert "INFEASIBLE" not in metrics_1["optimization_status"], \
        f"Run 1 was INFEASIBLE: {metrics_1}"

    # 2. Total cost must be identical (same objective value implies same cost for uniform wages)
    assert metrics_1["total_cost"] == metrics_2["total_cost"], (
        f"Total cost changed between runs: {metrics_1['total_cost']} vs "
        f"{metrics_2['total_cost']}"
    )

    # 3. Staffing shortfall must be identical (part of the objective)
    assert metrics_1["staffing_shortfall"] == metrics_2["staffing_shortfall"], (
        f"Shortfall changed between runs: {metrics_1['staffing_shortfall']} vs "
        f"{metrics_2['shortfall']}"
    )

    # 4. Total number of scheduled shifts must be identical
    assert len(df_shifts_1) == len(df_shifts_2), (
        f"Number of assigned shifts changed: {len(df_shifts_1)} vs {len(df_shifts_2)}"
    )

    # 5. Structural/constraint invariants on each run's output
    _validate_shifts_invariants(df_shifts_1, valid_ids, "Run 1")
    _validate_shifts_invariants(df_shifts_2, valid_ids, "Run 2")

    # 6. Aggregate cost computed from shifts must match the reported metric
    for label, df_shifts, metrics in [
        ("Run 1", df_shifts_1, metrics_1),
        ("Run 2", df_shifts_2, metrics_2),
    ]:
        computed_cost = round(df_shifts['cost'].sum(), 2)
        assert computed_cost == metrics["total_cost"], (
            f"{label}: computed cost {computed_cost} != reported {metrics['total_cost']}"
        )
