"""
Module for executing shift optimization.
Maps hourly agent requirements to real-world 8-hour shifts with mandatory breaks.
"""
import os
import pandas as pd
import numpy as np
from ortools.linear_solver import pywraplp

def run_shift_optimization():
    # Load required agents from the classical schedule
    classical_path = os.path.join("results", "classical_optimization_schedule.csv")
    if not os.path.exists(classical_path):
        raise FileNotFoundError(f"Classical schedule not found at {classical_path}. Run optimizer.py first.")
        
    df_classical = pd.read_csv(classical_path)
    required = df_classical['required_agents'].tolist()
    
    # OR-Tools SCIP solver
    solver = pywraplp.Solver.CreateSolver('SCIP')
    if not solver:
        raise Exception("OR-Tools SCIP solver not available.")
        
    # Variables
    # x[s] = number of agents starting a shift at hour s (s = 0..23)
    x = {}
    # y[s] = binary variable indicating if shift s is active (x[s] > 0)
    y = {}
    
    M = 100 # Large constant
    
    for s in range(24):
        x[s] = solver.IntVar(0, M, f'x_{s}')
        y[s] = solver.BoolVar(f'y_{s}')
        
        # Link x[s] and y[s]
        solver.Add(x[s] <= M * y[s])
        
    # Constraint: At most 7 shift start times are allowed
    solver.Add(sum(y[s] for s in range(24)) <= 7)
    
    # Coverage constraint for each hour h
    # An agent starting at s works 8 hours but takes a break at the 4th hour (index 4)
    # E.g. shift starting at 0 works: 0, 1, 2, 3, 5, 6, 7 (breaks at 4)
    for h in range(24):
        covering_agents = []
        for s in range(24):
            # Calculate hours worked relative to start hour s
            rel_hour = (h - s) % 24
            if 0 <= rel_hour < 8 and rel_hour != 4:
                covering_agents.append(x[s])
        
        solver.Add(sum(covering_agents) >= required[h])
        
    # Objective: Minimize total agents scheduled
    solver.Minimize(sum(x[s] for s in range(24)))
    
    status = solver.Solve()
    
    if status == pywraplp.Solver.OPTIMAL or status == pywraplp.Solver.FEASIBLE:
        total_agents = int(solver.Objective().Value())
        print(f"Shift optimization completed successfully.")
        print(f"Total agents scheduled across shifts: {total_agents}")
        
        active_shifts = []
        for s in range(24):
            val = int(x[s].solution_value())
            if val > 0:
                active_shifts.append((s, val))
                print(f"  Shift starting at {s:02d}:00: {val} agents")
                
        # Hourly coverage audit
        hourly_coverage = []
        coverage_pass = True
        for h in range(24):
            cov = 0
            for s, val in active_shifts:
                rel_hour = (h - s) % 24
                if 0 <= rel_hour < 8 and rel_hour != 4:
                    cov += val
            req = required[h]
            is_pass = cov >= req
            if not is_pass:
                coverage_pass = False
                
            hourly_coverage.append({
                'hour': h,
                'required_agents': req,
                'scheduled_agents': cov,
                'surplus': cov - req,
                'status': 'PASS' if is_pass else 'FAIL'
            })
            
        print(f"24/24 Hour Coverage Verification: {'PASS' if coverage_pass else 'FAIL'}")
        
        # Save results/shift_schedule.csv
        # The prompt expects results/shift_schedule.csv to contain shift info.
        # We will save the hourly coverage list to results/shift_schedule.csv and print the active shifts
        df_shifts = pd.DataFrame(hourly_coverage)
        os.makedirs("results", exist_ok=True)
        df_shifts.to_csv(os.path.join("results", "shift_schedule.csv"), index=False)
        
        # Save active shifts separately or log them in the file
        # Let's save a file results/active_shifts.csv for the dashboard's convenience
        df_active = pd.DataFrame(active_shifts, columns=['shift_start_hour', 'agents'])
        df_active.to_csv(os.path.join("results", "active_shifts.csv"), index=False)
    else:
        print("Solver failed to find a valid shift schedule.")

if __name__ == "__main__":
    run_shift_optimization()
