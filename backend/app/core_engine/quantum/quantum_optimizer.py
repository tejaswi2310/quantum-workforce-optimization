"""
Module for executing quantum optimization.
Builds a dynamically generated QUBO matrix for a Reduced Workforce Optimization Problem
based on ACTUAL demand, and compares classical exact results against Qiskit QAOA simulation.
"""
import os
import json
import numpy as np
import pandas as pd
import uuid
import time
from app.services.storage_service import StorageService

QISKIT_AVAILABLE = False
try:
    from qiskit_optimization import QuadraticProgram
    from qiskit_optimization.algorithms import MinimumEigenOptimizer
    from qiskit_algorithms import QAOA
    from qiskit_algorithms.optimizers import COBYLA
    from qiskit.primitives import StatevectorSampler
    from qiskit_algorithms.utils import algorithm_globals
    QISKIT_AVAILABLE = True
except Exception as e:
    print(f"Warning: Qiskit components could not be fully imported: {e}")

def solve_qubo_classical(Q, N):
    """Exact classical solver using brute force over 2^N combinations."""
    best_val = float('inf')
    best_config = None

    for i in range(2**N):
        # Convert integer to binary array of length N
        config = np.array([int(x) for x in f"{i:0{N}b}"])
        # Evaluate x^T * Q * x
        val = config.dot(Q).dot(config)
        if val < best_val:
            best_val = val
            best_config = config

    return best_config, best_val

def run_quantum_optimization(run_id: uuid.UUID = None):
    storage = StorageService(run_id)
    storage.ensure_run_dirs()

    print(f"--- REDUCED QUANTUM PROBLEM ---")

    # 1. D1 INTEGRATION: Load actual Erlang-C requirements from classical optimization
    erlang_path = storage.result_path("erlang_requirement_validation.csv")
    if not os.path.exists(erlang_path):
        global_path = os.path.join("results", "erlang_requirement_validation.csv")
        if os.path.exists(global_path):
            erlang_path = global_path
        else:
            raise FileNotFoundError(f"Erlang requirement not found at {erlang_path}.")

    df_erlang = pd.read_csv(erlang_path)

    target_skill = "Technical"
    df_skill = df_erlang[df_erlang['skill_group'] == target_skill]

    # Take hours 10 and 11 as the peak window
    row_t0 = df_skill[df_skill['interval'].str.startswith("10:00")]
    row_t1 = df_skill[df_skill['interval'].str.startswith("11:00")]

    req_t0 = int(row_t0['required_agents'].values[0]) if not row_t0.empty else 0
    req_t1 = int(row_t1['required_agents'].values[0]) if not row_t1.empty else 0

    d_t0 = req_t0
    d_t1 = req_t1

    original_required = [req_t0, req_t1]
    requirement_reduced = False
    reduction_reason = "None"

    # Scale down demand for the toy 4-agent problem
    if d_t0 > 2 or d_t1 > 2:
        requirement_reduced = True
        reduction_reason = "Reduced quantum instance capacity (4 agents) cannot cover original D1 requirement."
        d_t0 = min(d_t0, 2)
        d_t1 = min(d_t1, 2)

    print(f"Skill: {target_skill}, Hours: 10:00 - 12:00")
    print(f"Original Demand T0: {req_t0}, Demand T1: {req_t1}")
    if requirement_reduced:
        print(f"Reduced to Demand T0: {d_t0}, Demand T1: {d_t1} ({reduction_reason})")

    # 2. D2 INTEGRATION: Load actual roster
    roster_path = storage.data_path("raw/synthetic_roster.csv")
    if not os.path.exists(roster_path):
        global_path = os.path.join("data", "raw", "synthetic_roster.csv")
        if os.path.exists(global_path):
            roster_path = global_path
        else:
            raise FileNotFoundError(f"Roster not found at {roster_path}.")

    df_roster = pd.read_csv(roster_path)

    # Deterministic selection: technical skill, sorted by agent_id, take top 4
    eligible_agents = df_roster[df_roster['skills'].str.contains(target_skill)].sort_values('agent_id')
    selected_agents_df = eligible_agents.head(4)
    if len(selected_agents_df) == 0:
        print("No eligible agents for the quantum reduced instance. Skipping.")
        metadata_data = [
            {"Metric": "Instance ID", "Value": str(run_id) if run_id else "N/A"},
            {"Metric": "Optimization Status", "Value": "SKIPPED (0 eligible agents)"},
            {"Metric": "Conclusion", "Value": "QAOA was skipped due to insufficient eligible agents."}
        ]
        df_meta = pd.DataFrame(metadata_data)
        meta_path = storage.result_path("quantum_metadata.csv")
        storage.atomic_write_csv(df_meta, meta_path, index=False)
        return

    selected_agents = selected_agents_df.to_dict('records')
    for a in selected_agents:
        print(f"Selected Agent: {a['agent_id']}, Wage: {a['wage']}, Skills: {a['skills']}")

    # 4 Agents, 2 time periods => 8 decision variables x_{i,t}
    # Indexing: var_idx = i * 2 + t
    N_agents = len(selected_agents)
    N_time = 2
    N = N_agents * N_time

    # Penalty weight for coverage
    # Z = sum_{i,t} wage[i] * x_{i,t} + sum_{t} alpha * (D_t - sum_i x_{i,t})^2
    # Alpha acts as a soft penalty for exact coverage.
    # It must exceed max(wage) so understaffing costs more than hiring an agent.
    # We use a soft penalty to avoid the qubit overhead of inequality slack variables.
    alpha = 50

    Q = np.zeros((N, N))

    # Add linear terms (diagonal)
    for i in range(N_agents):
        wage_i = selected_agents[i]['wage']
        for t in range(N_time):
            idx = i * N_time + t
            D_t = d_t0 if t == 0 else d_t1
            Q[idx, idx] += wage_i - 2 * alpha * D_t + alpha

    # Add quadratic terms (off-diagonal)
    for t in range(N_time):
        for i in range(N_agents):
            for j in range(i + 1, N_agents):
                idx1 = i * N_time + t
                idx2 = j * N_time + t
                Q[idx1, idx2] += 2 * alpha

    # Solve Classically (Exact brute force for exact parity benchmark)
    t0_classical = time.perf_counter()
    classical_config, classical_val = solve_qubo_classical(Q, N)
    classical_runtime = time.perf_counter() - t0_classical

    # Re-add the constant D_t^2 term to get actual objective value
    constant = alpha * (d_t0**2 + d_t1**2)
    classical_cost = classical_val + constant

    # Solve with Qiskit
    quantum_config = None
    quantum_cost = None
    quantum_runtime = 0.0
    quantum_status = "FAILED/SKIPPED"
    feasible = False
    shortfall = 0
    overstaffing = 0
    invalid_assignments = 0
    qaoa_reps = 1

    if QISKIT_AVAILABLE:
        try:
            print("Attempting to solve with Qiskit QAOA...")
            # Reproducibility
            np.random.seed(42)
            algorithm_globals.random_seed = 42

            qp = QuadraticProgram()
            for i in range(N):
                qp.binary_var(name=f'x_{i}')

            linear = {}
            quadratic = {}
            for i in range(N):
                linear[f'x_{i}'] = Q[i, i]
                for j in range(i+1, N):
                    if Q[i, j] != 0:
                        quadratic[(f'x_{i}', f'x_{j}')] = Q[i, j]

            qp.minimize(linear=linear, quadratic=quadratic)

            sampler = StatevectorSampler(seed=42)
            qaoa = QAOA(sampler=sampler, optimizer=COBYLA(maxiter=100), reps=qaoa_reps)
            optimizer = MinimumEigenOptimizer(qaoa)

            t0_qaoa = time.perf_counter()
            result = optimizer.solve(qp)
            quantum_runtime = time.perf_counter() - t0_qaoa

            quantum_config = np.array([int(result.x[i]) for i in range(N)])
            quantum_val = quantum_config.dot(Q).dot(quantum_config)
            quantum_cost = quantum_val + constant
            quantum_status = "SUCCESS"
            print("Successfully solved using Qiskit QAOA!")

            # Result Decoding and Feasibility
            decoded_assignments = []
            assigned_t0 = 0
            assigned_t1 = 0
            for i in range(N_agents):
                for t in range(N_time):
                    idx = i * N_time + t
                    is_assigned = quantum_config[idx] == 1
                    if is_assigned:
                        if t == 0: assigned_t0 += 1
                        elif t == 1: assigned_t1 += 1
                        else: invalid_assignments += 1
                    decoded_assignments.append({
                        "agent_id": selected_agents[i]['agent_id'],
                        "time_slot": 10 + t,
                        "wage": selected_agents[i]['wage'],
                        "assigned": is_assigned
                    })

            shortfall_t0 = max(0, d_t0 - assigned_t0)
            shortfall_t1 = max(0, d_t1 - assigned_t1)
            overstaffing_t0 = max(0, assigned_t0 - d_t0)
            overstaffing_t1 = max(0, assigned_t1 - d_t1)

            shortfall = shortfall_t0 + shortfall_t1
            overstaffing = overstaffing_t0 + overstaffing_t1
            feasible = (shortfall == 0 and invalid_assignments == 0)

            print("\\n--- Decoded QAOA Assignments ---")
            for a in decoded_assignments:
                if a["assigned"]:
                    print(f"Agent {a['agent_id']} assigned to {a['time_slot']}:00 (Wage: ${a['wage']})")
            print(f"Feasible: {feasible}, Shortfall: {shortfall}, Overstaffing: {overstaffing}")

        except Exception as ex:
            print(f"Error solving with Qiskit QAOA: {ex}")
            quantum_status = f"FAILED: {ex}"
    else:
        print("Qiskit not available. Skipping QAOA execution.")
        quantum_status = "SKIPPED (Qiskit missing)"

    print(f"Classical Exact Result: Cost = {classical_cost:.2f}, Config = {list(classical_config)}")
    if quantum_status == "SUCCESS":
        print(f"Quantum QAOA Result: Cost = {quantum_cost:.2f}, Config = {list(quantum_config)}")

    # Compare results based purely on Objective Value
    objective_match = "YES" if (quantum_status == "SUCCESS" and np.isclose(classical_cost, quantum_cost)) else "NO"
    configuration_match = "YES" if (quantum_status == "SUCCESS" and np.array_equal(classical_config, quantum_config)) else "NO"

    absolute_gap = abs(classical_cost - quantum_cost) if quantum_status == "SUCCESS" else None
    relative_gap = (absolute_gap / abs(classical_cost) * 100) if (quantum_status == "SUCCESS" and classical_cost != 0) else None

    # quantum_classical_comparison.csv (Benchmark Data)
    benchmark_data = [
        {"Metric": "Target Agents T0", "Classical_Exact": str(d_t0), "Quantum_QAOA": str(d_t0), "Match": "N/A"},
        {"Metric": "Target Agents T1", "Classical_Exact": str(d_t1), "Quantum_QAOA": str(d_t1), "Match": "N/A"},
        {"Metric": "Objective Value", "Classical_Exact": f"{classical_cost:.2f}", "Quantum_QAOA": f"{quantum_cost:.2f}" if quantum_status == "SUCCESS" else "N/A", "Match": objective_match},
        {"Metric": "Absolute Gap", "Classical_Exact": "0.00", "Quantum_QAOA": f"{absolute_gap:.2f}" if quantum_status == "SUCCESS" else "N/A", "Match": "N/A"},
        {"Metric": "Relative Gap (%)", "Classical_Exact": "0.00%", "Quantum_QAOA": f"{relative_gap:.2f}%" if quantum_status == "SUCCESS" else "N/A", "Match": "N/A"},
        {"Metric": "Optimal Config", "Classical_Exact": str(list(classical_config)), "Quantum_QAOA": str(list(quantum_config)) if quantum_status == "SUCCESS" else "N/A", "Match": configuration_match},
        {"Metric": "Runtime (s)", "Classical_Exact": f"{classical_runtime:.4f}", "Quantum_QAOA": f"{quantum_runtime:.4f}" if quantum_status == "SUCCESS" else "N/A", "Match": "N/A"}
    ]

    df_comparison = pd.DataFrame(benchmark_data)
    comparison_path = storage.result_path("quantum_classical_comparison.csv")
    storage.atomic_write_csv(df_comparison, comparison_path, index=False)
    print(f"Quantum-Classical comparison saved to {comparison_path}")

    # quantum_metadata.csv (Audit and Run Details)
    metadata_data = [
        {"Metric": "Instance ID", "Value": str(run_id) if run_id else "N/A"},
        {"Metric": "Benchmark Name", "Value": f"Reduced_QAOA_{N_agents}x{N_time}"},
        {"Metric": "Skill Group", "Value": target_skill},
        {"Metric": "Original D1 Demand", "Value": f"T0:{req_t0}|T1:{req_t1}"},
        {"Metric": "Quantum POC Capacity", "Value": "2 agents per slot"},
        {"Metric": "Reduced Demand Actually Optimized", "Value": f"T0:{d_t0}|T1:{d_t1}"},
        {"Metric": "Reduction Flag", "Value": str(requirement_reduced)},
        {"Metric": "Reduction Reason", "Value": reduction_reason},
        {"Metric": "Selected Agent Count", "Value": str(N_agents)},
        {"Metric": "Selected Agents", "Value": "|".join([a['agent_id'] for a in selected_agents])},
        {"Metric": "Slot Count", "Value": str(N_time)},
        {"Metric": "Selected Time Slots", "Value": "10:00|11:00"},
        {"Metric": "Number of Qubits", "Value": str(N)},
        {"Metric": "Penalty Alpha", "Value": str(alpha)},
        {"Metric": "QAOA Reps", "Value": str(qaoa_reps)},
        {"Metric": "QAOA Optimizer", "Value": "COBYLA"},
        {"Metric": "Classical Solver", "Value": "Exact Brute Force"},
        {"Metric": "Quantum Solver", "Value": "QAOA Statevector"},
        {"Metric": "Seed", "Value": "42"},
        {"Metric": "Feasibility Checked", "Value": str(feasible)},
        {"Metric": "Optimization Status", "Value": quantum_status},
        {"Metric": "Conclusion", "Value": "QAOA matched the exact classical objective on the tested reduced 8-qubit instance." if objective_match == "YES" else "QAOA did not match the exact classical objective or was skipped."}
    ]

    df_meta = pd.DataFrame(metadata_data)
    meta_path = storage.result_path("quantum_metadata.csv")
    storage.atomic_write_csv(df_meta, meta_path, index=False)
    print(f"Quantum metadata saved to {meta_path}")

if __name__ == "__main__":
    run_quantum_optimization()
