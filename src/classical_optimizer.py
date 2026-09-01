"""
Module for executing classical optimization using OR-Tools CP-SAT.
Formulates the full workforce scheduling MIP including skill matching, shifts, breaks,
overtime, and multi-objective penalties.
"""
import os
import json
import pandas as pd
import numpy as np
import math
from ortools.sat.python import cp_model
from src.queue_simulator import required_agents_for_sla, TARGET_SLA, TARGET_WAIT_SECONDS, erlang_c

def run_classical_optimization():
    print("--- Running Classical Optimization (Full MIP) ---")
    forecast_path = os.path.join("data", "processed", "forecast_results.csv")
    if not os.path.exists(forecast_path):
        raise FileNotFoundError(f"Forecast results not found at {forecast_path}.")
        
    df_forecast = pd.read_csv(forecast_path)
    first_day = df_forecast['date'].min()
    df_day = df_forecast[df_forecast['date'] == first_day].copy()
    
    # 1. Aggregate demand by skill and hour
    aht = 300
    interval_seconds = 3600
    
    validation_results = []
    required_agents = []
    
    for idx, row in df_day.iterrows():
        calls = row['predicted_calls']
        c, A, achieved_sla, p_w = required_agents_for_sla(
            calls, aht, interval_seconds, TARGET_SLA, TARGET_WAIT_SECONDS
        )
        required_agents.append(c)
        
        # Check minimality if c > 0
        minimumity_check = "PASS"
        previous_agents_sla = 0.0
        if c > max(1, int(math.floor(A))):
            prev_c = c - 1
            prev_p_w = erlang_c(prev_c, A)
            previous_agents_sla = 1.0 - prev_p_w * math.exp(-(prev_c - A) * TARGET_WAIT_SECONDS / aht)
            if previous_agents_sla >= TARGET_SLA:
                minimumity_check = "FAIL"
        elif c > 0 and c <= A:
            minimumity_check = "FAIL (Unstable)"
            
        validation_results.append({
            'interval': row['interval'],
            'skill_group': row['skill_group'],
            'predicted_calls': calls,
            'aht_seconds': aht,
            'interval_seconds': interval_seconds,
            'offered_traffic': A,
            'required_agents': c,
            'target_sla': TARGET_SLA,
            'achieved_sla': achieved_sla,
            'previous_agents_sla': previous_agents_sla,
            'minimumity_check': minimumity_check
        })
        
    df_day['required_agents'] = required_agents
    
    os.makedirs("results", exist_ok=True)
    pd.DataFrame(validation_results).to_csv(os.path.join("results", "erlang_requirement_validation.csv"), index=False)
    
    demand = {}
    skills = df_day['skill_group'].unique()
    for k in skills:
        for t in range(24):
            val = df_day[(df_day['skill_group'] == k) & (df_day['hour'] == t)]['required_agents'].sum()
            demand[(k, t)] = int(val)
            
    # 2. Setup Agents and Skills
    # To satisfy demand (~58 peak total), we generate 80 agents with random skills
    np.random.seed(42)
    num_agents = 80
    agents = []
    
    for i in range(num_agents):
        # Assign 1 or 2 skills to each agent
        num_skills = np.random.choice([1, 2], p=[0.7, 0.3])
        agent_skills = np.random.choice(skills, size=num_skills, replace=False).tolist()
        # Make sure every skill is represented
        if i < len(skills):
            agent_skills = [skills[i]]
            
        agents.append({
            'id': i,
            'skills': agent_skills,
            'wage': 15,
            'ot_penalty': 30
        })
        
    # 3. Define Shift Templates
    # Each template provides a 24-hour binary array for work (x)
    # 0 = not working, 1 = working
    shift_templates = []
    
    # Template 0: No shift
    shift_templates.append({
        'name': 'None',
        'x': [0]*24,
        'cost': 0,
        'overtime': 0
    })
    
    for start_h in range(24):
        # Base shift: 8 hrs work + 1 hr break
        x_base = [0]*24
        for offset in range(9):
            if offset != 4: # Break at hour 4
                x_base[(start_h + offset) % 24] = 1
        shift_templates.append({
            'name': f'Base_Start_{start_h:02d}',
            'x': x_base,
            'cost': 8 * 15,
            'overtime': 0
        })
        
        # OT shift (+1 hr)
        x_ot1 = [0]*24
        for offset in range(10):
            if offset != 4:
                x_ot1[(start_h + offset) % 24] = 1
        shift_templates.append({
            'name': f'OT1_Start_{start_h:02d}',
            'x': x_ot1,
            'cost': 8 * 15 + 1 * 30,
            'overtime': 1
        })

    # 4. Initialize CP-SAT Model
    model = cp_model.CpModel()
    
    # Variables
    # y[i, s] = 1 if agent i takes shift template s
    y = {}
    for i in range(num_agents):
        for s, template in enumerate(shift_templates):
            y[(i, s)] = model.NewBoolVar(f'y_{i}_{s}')
            
    # Each agent takes exactly one shift template (can be 'None')
    for i in range(num_agents):
        model.AddExactlyOne([y[(i, s)] for s in range(len(shift_templates))])
        
    # x[i, t] = 1 if agent i is working at hour t
    x = {}
    for i in range(num_agents):
        for t in range(24):
            x[(i, t)] = model.NewBoolVar(f'x_{i}_{t}')
            # Link x to y
            model.Add(x[(i, t)] == sum(y[(i, s)] * shift_templates[s]['x'][t] for s in range(len(shift_templates))))
            
    # Agent assignment to skills at hour t
    # assign[i, k, t] = 1 if agent i is working AND answering skill k at time t
    assign = {}
    for i in range(num_agents):
        agent_skills = agents[i]['skills']
        for t in range(24):
            for k in skills:
                assign[(i, k, t)] = model.NewBoolVar(f'assign_{i}_{k}_{t}')
                if k not in agent_skills:
                    model.Add(assign[(i, k, t)] == 0)
            
            # Agent can only handle 1 skill at a time, and only if they are working
            model.Add(sum(assign[(i, k, t)] for k in skills) == x[(i, t)])

    # Shortfall variables
    shortfall = {}
    for k in skills:
        for t in range(24):
            shortfall[(k, t)] = model.NewIntVar(0, 1000, f'shortfall_{k}_{t}')
            # Coverage constraint: assigned agents + shortfall >= demand
            assigned_total = sum(assign[(i, k, t)] for i in range(num_agents))
            model.Add(assigned_total + shortfall[(k, t)] >= demand[(k, t)])
            
    # Idle time
    # idle[k, t] = assigned - demand
    idle = {}
    for k in skills:
        for t in range(24):
            idle[(k, t)] = model.NewIntVar(0, 1000, f'idle_{k}_{t}')
            assigned_total = sum(assign[(i, k, t)] for i in range(num_agents))
            # If assigned > demand, idle = assigned - demand. Else idle = 0.
            # We can just penalize assigned_total since demand is constant, 
            # but using idle explicitly is cleaner.
            model.AddMaxEquality(idle[(k, t)], [0, assigned_total - demand[(k, t)]])
            
    # 5. Objective Function
    # Weights based on manager priorities
    w_cost = 1.0
    w_shortfall = 50.0  # High penalty for missing SLA
    w_idle = 5.0        # Minor penalty for overstaffing
    
    total_cost = sum(y[(i, s)] * shift_templates[s]['cost'] for i in range(num_agents) for s in range(len(shift_templates)))
    total_shortfall = sum(shortfall[(k, t)] for k in skills for t in range(24))
    total_idle = sum(idle[(k, t)] for k in skills for t in range(24))
    
    model.Minimize(
        int(w_cost) * total_cost + 
        int(w_shortfall) * total_shortfall + 
        int(w_idle) * total_idle
    )
    
    # 6. Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 30.0
    status = solver.Solve(model)
    
    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        print(f"Solver Status: {solver.StatusName(status)}")
        print(f"Objective Value: {solver.ObjectiveValue()}")
        
        # 7. Extract Results
        results = []
        for t in range(24):
            total_req = 0
            total_sched = 0
            for k in skills:
                req = demand[(k, t)]
                sched = sum(solver.Value(assign[(i, k, t)]) for i in range(num_agents))
                total_req += req
                total_sched += sched
                
            # Compute cost for the hour (apportioned base wage + overtime)
            # For simplicity, we just charge $15 per scheduled agent-hour in this summary
            cost_h = total_sched * 15
            
            results.append({
                'hour': t,
                'calls': df_day[df_day['hour'] == t]['predicted_calls'].sum(),
                'required_agents': total_req,
                'scheduled_agents': total_sched,
                'cost': cost_h
            })
            
        df_results = pd.DataFrame(results)
        os.makedirs("results", exist_ok=True)
        df_results.to_csv(os.path.join("results", "classical_optimization_schedule.csv"), index=False)
        print("Classical optimization completed and saved to results/classical_optimization_schedule.csv")
        
        # Also save detailed shift assignments for shift_optimizer and transparency
        agent_shifts = []
        for i in range(num_agents):
            for s, template in enumerate(shift_templates):
                if solver.Value(y[(i, s)]) == 1 and template['name'] != 'None':
                    agent_shifts.append({
                        'agent_id': i,
                        'skills': '|'.join(agents[i]['skills']),
                        'shift_name': template['name'],
                        'cost': template['cost'],
                        'overtime': template['overtime']
                    })
        df_shifts = pd.DataFrame(agent_shifts)
        df_shifts.to_csv(os.path.join("results", "agent_shifts_detailed.csv"), index=False)
        
    else:
        print("Solver failed to find a feasible solution.")
        
if __name__ == "__main__":
    run_classical_optimization()
