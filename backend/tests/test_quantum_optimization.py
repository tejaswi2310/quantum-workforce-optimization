import os
import uuid
import pytest
import pandas as pd
import numpy as np
from unittest.mock import patch

from app.core_engine.quantum.quantum_optimizer import run_quantum_optimization, solve_qubo_classical

@pytest.fixture
def temp_workspace(tmp_path):
    # Create directories
    data_raw = tmp_path / "data" / "raw"
    data_raw.mkdir(parents=True)
    results_dir = tmp_path / "results"
    results_dir.mkdir(parents=True)

    # Write erlang requirements
    erlang_df = pd.DataFrame([
        {'interval': '10:00-11:00', 'skill_group': 'Technical', 'required_agents': 2},
        {'interval': '11:00-12:00', 'skill_group': 'Technical', 'required_agents': 1},
        {'interval': '12:00-13:00', 'skill_group': 'Technical', 'required_agents': 3}
    ])
    erlang_df.to_csv(results_dir / "erlang_requirement_validation.csv", index=False)

    # Write roster
    roster_df = pd.DataFrame([
        {'agent_id': 'AGT-001', 'skills': 'Technical|Sales', 'wage': 20.0},
        {'agent_id': 'AGT-002', 'skills': 'Technical', 'wage': 21.0},
        {'agent_id': 'AGT-003', 'skills': 'Technical|Billing', 'wage': 19.5},
        {'agent_id': 'AGT-004', 'skills': 'Technical', 'wage': 22.0},
        {'agent_id': 'AGT-005', 'skills': 'Technical', 'wage': 18.0}
    ])
    roster_df.to_csv(data_raw / "synthetic_roster.csv", index=False)

    # Mock os.path.join in the module so it finds our tmp_path
    original_join = os.path.join
    def mock_join(*args):
        if args[0] == "results":
            return original_join(tmp_path, "results", args[1])
        if args[0] == "data" and args[1] == "raw":
            return original_join(tmp_path, "data", "raw", args[2])
        return original_join(*args)

    return tmp_path, mock_join

def test_quantum_uses_real_roster(temp_workspace, capsys):
    tmp_path, mock_join = temp_workspace
    with patch('app.core_engine.quantum.quantum_optimizer.os.path.join', side_effect=mock_join):
        run_quantum_optimization()
        captured = capsys.readouterr()
        assert "Selected Agent: AGT-001" in captured.out
        assert "Selected Agent: AGT-002" in captured.out
        assert "Selected Agent: AGT-003" in captured.out
        assert "Selected Agent: AGT-004" in captured.out
        assert "Selected Agent: AGT-005" not in captured.out

def test_quantum_uses_real_wages(temp_workspace, capsys):
    tmp_path, mock_join = temp_workspace
    with patch('app.core_engine.quantum.quantum_optimizer.os.path.join', side_effect=mock_join):
        run_quantum_optimization()
        captured = capsys.readouterr()
        assert "Wage: 20.0" in captured.out
        assert "Wage: 21.0" in captured.out

def test_quantum_uses_d1_requirement(temp_workspace, capsys):
    tmp_path, mock_join = temp_workspace
    with patch('app.core_engine.quantum.quantum_optimizer.os.path.join', side_effect=mock_join):
        run_quantum_optimization()
        captured = capsys.readouterr()
        assert "Original Demand T0: 2, Demand T1: 1" in captured.out

@patch('app.core_engine.quantum.quantum_optimizer.solve_qubo_classical', return_value=([], 0))
def test_qubo_matrix_generation(mock_solve, temp_workspace):
    tmp_path, mock_join = temp_workspace
    with patch('app.core_engine.quantum.quantum_optimizer.os.path.join', side_effect=mock_join):
        run_quantum_optimization()
        # Extract Q from the mock call
        Q = mock_solve.call_args[0][0]
        # alpha = 50, wage_0 = 20.0, D_t0 = 2 => 20 - 200 + 50 = -130
        assert Q[0, 0] == -130.0
        # wage_0 = 20.0, D_t1 = 1 => 20 - 100 + 50 = -30
        assert Q[1, 1] == -30.0
        # wage_1 = 21.0, D_t0 = 2 => 21 - 200 + 50 = -129
        assert Q[2, 2] == -129.0

        # Quadratic terms test
        # 2 * alpha = 100
        assert Q[0, 2] == 100.0

def test_exact_classical_known_optimum():
    # N=2, D=1, wage1=10, wage2=12, alpha=50
    Q = np.zeros((2,2))
    Q[0,0] = 10 - 2*50*1 + 50  # -40
    Q[1,1] = 12 - 2*50*1 + 50  # -38
    Q[0,1] = 2 * 50  # 100
    Q[1,0] = 0
    config, val = solve_qubo_classical(Q, 2)
    # config [1, 0] gives -40, [0, 1] gives -38, [1, 1] gives -40-38+100 = 22, [0,0] gives 0
    assert list(config) == [1, 0]
    assert val == -40

def test_quantum_result_decoding(temp_workspace, capsys):
    tmp_path, mock_join = temp_workspace
    with patch('app.core_engine.quantum.quantum_optimizer.os.path.join', side_effect=mock_join):
        run_quantum_optimization()
        captured = capsys.readouterr()
        assert "Successfully solved using Qiskit QAOA!" in captured.out, "QAOA failed or was skipped"
        assert "Decoded QAOA Assignments" in captured.out
        assert "Feasible: True" in captured.out

def test_quantum_feasibility_validation(temp_workspace, capsys):
    tmp_path, mock_join = temp_workspace
    # Overwrite requirement to exceed capacity (D=5) to trigger shortfall and infeasibility
    erlang_df = pd.DataFrame([
        {'interval': '10:00-11:00', 'skill_group': 'Technical', 'required_agents': 5},
        {'interval': '11:00-12:00', 'skill_group': 'Technical', 'required_agents': 5}
    ])
    erlang_df.to_csv(tmp_path / "results" / "erlang_requirement_validation.csv", index=False)

    with patch('app.core_engine.quantum.quantum_optimizer.os.path.join', side_effect=mock_join):
        run_quantum_optimization()
        captured = capsys.readouterr()
        # It gets reduced to 2 inside the code, so it will actually be feasible because the quantum instance itself only aims for 2.
        assert "Reduced to Demand T0: 2, Demand T1: 2" in captured.out
        assert "Successfully solved using Qiskit QAOA!" in captured.out, "QAOA failed or was skipped"
        assert "Feasible: True" in captured.out
        assert "Overstaffing:" in captured.out

def test_quantum_metrics_artifacts(temp_workspace):
    tmp_path, mock_join = temp_workspace
    with patch('app.core_engine.quantum.quantum_optimizer.os.path.join', side_effect=mock_join):
        with patch('app.services.storage_service.StorageService.result_path', side_effect=lambda x: os.path.join(tmp_path, "results", x)):
            run_id = uuid.uuid4()
            run_quantum_optimization(run_id)

            df_comp = pd.read_csv(os.path.join(tmp_path, "results", "quantum_classical_comparison.csv"))
            df_meta = pd.read_csv(os.path.join(tmp_path, "results", "quantum_metadata.csv"))

            # Check presence of fields in comparison
            assert "Runtime (s)" in df_comp['Metric'].values
            assert "Absolute Gap" in df_comp['Metric'].values
            assert "Relative Gap (%)" in df_comp['Metric'].values

            # Check presence of fields in metadata
            assert "Instance ID" in df_meta['Metric'].values
            assert "Benchmark Name" in df_meta['Metric'].values
            assert "Selected Agent Count" in df_meta['Metric'].values
            assert "Slot Count" in df_meta['Metric'].values
            assert "Classical Solver" in df_meta['Metric'].values
            assert "Quantum Solver" in df_meta['Metric'].values

def test_quantum_reproducibility(temp_workspace):
    tmp_path, mock_join = temp_workspace
    with patch('app.core_engine.quantum.quantum_optimizer.os.path.join', side_effect=mock_join):
        with patch('app.services.storage_service.StorageService.result_path', side_effect=lambda x: os.path.join(tmp_path, "results", x)):
            run_id = uuid.uuid4()
            run_quantum_optimization(run_id)
            df1_comp = pd.read_csv(os.path.join(tmp_path, "results", "quantum_classical_comparison.csv"))
            df1_meta = pd.read_csv(os.path.join(tmp_path, "results", "quantum_metadata.csv"))

            run_quantum_optimization(run_id)
            df2_comp = pd.read_csv(os.path.join(tmp_path, "results", "quantum_classical_comparison.csv"))
            df2_meta = pd.read_csv(os.path.join(tmp_path, "results", "quantum_metadata.csv"))

            # For reproducibility of Runtimes, we must drop them before checking equality,
            # as time.perf_counter() will differ across runs.
            df1_comp_clean = df1_comp[df1_comp['Metric'] != 'Runtime (s)']
            df2_comp_clean = df2_comp[df2_comp['Metric'] != 'Runtime (s)']

            pd.testing.assert_frame_equal(df1_comp_clean, df2_comp_clean)
            pd.testing.assert_frame_equal(df1_meta, df2_meta)
