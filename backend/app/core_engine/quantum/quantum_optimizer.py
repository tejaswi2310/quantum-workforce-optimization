"""
Module for executing quantum optimization.
Builds a dynamically generated QUBO matrix for a Reduced Workforce Optimization Problem
based on ACTUAL demand, and compares classical exact results against Qiskit QAOA simulation.
"""
import os
import numpy as np
import pandas as pd
import uuid
from app.services.storage_service import StorageService

QISKIT_AVAILABLE = False
try:
    from qiskit_optimization import QuadraticProgram
    from qiskit_optimization.algorithms import MinimumEigenOptimizer
    from qiskit_algorithms import QAOA
    from qiskit_algorithms.optimizers import COBYLA
    from qiskit.primitives import StatevectorSampler
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

    # Load actual forecast to define the reduced problem
    forecast_path = storage.data_path("processed/forecast_results.csv")
    if not os.path.exists(forecast_path):
        # Fallback to global data/processed for backward compatibility during tests if needed
        global_path = os.path.join("data", "processed", "forecast_results.csv")
        if os.path.exists(global_path):
            forecast_path = global_path
        else:
            raise FileNotFoundError(f"Forecast results not found at {forecast_path}.")
        
    df_forecast = pd.read_csv(forecast_path)
    
    # Define a reduced problem: 1 Skill, 2 Hours, 4 Agents
    target_skill = "Technical"
    df_skill = df_forecast[df_forecast['skill_group'] == target_skill]
    
    # Take hours 10 and 11 as the peak window
    d_t0 = int(np.ceil(df_skill[df_skill['hour'] == 10]['predicted_calls'].sum() * 300 / 3600))
    d_t1 = int(np.ceil(df_skill[df_skill['hour'] == 11]['predicted_calls'].sum() * 300 / 3600))
    
    # Scale down demand for the toy 4-agent problem (e.g. cap at 2)
    d_t0 = min(d_t0, 2)
    d_t1 = min(d_t1, 2)
    
    print(f"--- REDUCED QUANTUM PROBLEM ---")
    print(f"Skill: {target_skill}, Hours: 10:00 - 12:00")
    print(f"Demand T0: {d_t0}, Demand T1: {d_t1}")
    
    # 4 Agents, 2 time periods => 8 decision variables x_{i,t}
    # Indexing: var_idx = i * 2 + t
    N_agents = 4
    N_time = 2
    N = N_agents * N_time
    
    wage = 15
    alpha = 50 # Shortfall/Idle quadratic penalty weight
    
    # Objective: min Z = sum_{i,t} wage * x_{i,t} + sum_{t} alpha * (D_t - sum_i x_{i,t})^2
    # Expanding the penalty term:
    # (D_t - sum_i x_{i,t})^2 = D_t^2 - 2 D_t sum_i x_{i,t} + (sum_i x_{i,t})^2
    # = D_t^2 - 2 D_t sum_i x_{i,t} + sum_i x_{i,t} + 2 sum_{i < j} x_{i,t} x_{j,t}  (since x^2 = x for binary)
    
    Q = np.zeros((N, N))
    
    # Add linear terms (diagonal)
    for i in range(N_agents):
        for t in range(N_time):
            idx = i * N_time + t
            D_t = d_t0 if t == 0 else d_t1
            Q[idx, idx] += wage - 2 * alpha * D_t + alpha
            
    # Add quadratic terms (off-diagonal)
    for t in range(N_time):
        for i in range(N_agents):
            for j in range(i + 1, N_agents):
                idx1 = i * N_time + t
                idx2 = j * N_time + t
                Q[idx1, idx2] += 2 * alpha
                
    # Solve Classically (Exact brute force for exact parity benchmark)
    classical_config, classical_val = solve_qubo_classical(Q, N)
    
    # Re-add the constant D_t^2 term to get actual objective value
    constant = alpha * (d_t0**2 + d_t1**2)
    classical_cost = classical_val + constant
    
    # Solve with Qiskit
    quantum_config = None
    quantum_cost = None
    quantum_status = "FAILED/SKIPPED"
    
    if QISKIT_AVAILABLE:
        try:
            print("Attempting to solve with Qiskit QAOA...")
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
            
            sampler = StatevectorSampler()
            qaoa = QAOA(sampler=sampler, optimizer=COBYLA(), reps=1)
            optimizer = MinimumEigenOptimizer(qaoa)
            
            result = optimizer.solve(qp)
            quantum_config = np.array([int(result.x[i]) for i in range(N)])
            quantum_val = quantum_config.dot(Q).dot(quantum_config)
            quantum_cost = quantum_val + constant
            quantum_status = "SUCCESS"
            print("Successfully solved using Qiskit QAOA!")
        except Exception as ex:
            print(f"Error solving with Qiskit QAOA: {ex}")
            quantum_status = f"FAILED: {ex}"
    else:
        print("Qiskit not available. Skipping QAOA execution.")
        quantum_status = "SKIPPED (Qiskit missing)"
        
    print(f"Classical Exact Result: Cost = {classical_cost:.2f}, Config = {list(classical_config)}")
    if quantum_status == "SUCCESS":
        print(f"Quantum QAOA Result: Cost = {quantum_cost:.2f}, Config = {list(quantum_config)}")
    
    # Compare results
    match_status = "YES" if (quantum_status == "SUCCESS" and classical_cost == quantum_cost and np.array_equal(classical_config, quantum_config)) else "NO"
    
    comparison_data = [
        {"Metric": "Execution Backend", "Classical_Exact": "CPU", "Quantum_QAOA": "Simulator (StatevectorSampler)" if quantum_status == "SUCCESS" else quantum_status, "Match": "N/A"},
        {"Metric": "Decision Variables", "Classical_Exact": str(N), "Quantum_QAOA": str(N), "Match": "YES"},
        {"Metric": "Target Agents T0", "Classical_Exact": str(d_t0), "Quantum_QAOA": str(d_t0), "Match": "N/A"},
        {"Metric": "Target Agents T1", "Classical_Exact": str(d_t1), "Quantum_QAOA": str(d_t1), "Match": "N/A"},
        {"Metric": "Objective Value", "Classical_Exact": f"{classical_cost:.2f}", "Quantum_QAOA": f"{quantum_cost:.2f}" if quantum_status == "SUCCESS" else quantum_status, "Match": match_status},
        {"Metric": "Optimal Config", "Classical_Exact": str(list(classical_config)), "Quantum_QAOA": str(list(quantum_config)) if quantum_status == "SUCCESS" else quantum_status, "Match": match_status}
    ]
    
    df_comparison = pd.DataFrame(comparison_data)
    df_comparison.to_csv(storage.result_path("quantum_classical_comparison.csv"), index=False)
    print(f"Quantum-Classical comparison saved to {storage.result_path('quantum_classical_comparison.csv')}")

if __name__ == "__main__":
    run_quantum_optimization()
