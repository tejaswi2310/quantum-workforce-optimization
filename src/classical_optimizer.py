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
    # To satisfy demand (~753 total agent-hours), we generate 120 agents with random skills
    np.random.seed(42)
    num_agents = 120
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
    
    # Group agents by skill profile
    profiles = {}
    for i, agent in enumerate(agents):
        prof_key = tuple(sorted(agent['skills']))
        if prof_key not in profiles:
            profiles[prof_key] = []
        profiles[prof_key].append(agent['id'])
        
    # count[p, s] = number of agents with profile p taking shift template s
    count_vars = {}
    for p_key, agent_ids in profiles.items():
        for s in range(len(shift_templates)):
            # Cannot assign more agents than exist in this profile
            count_vars[(p_key, s)] = model.NewIntVar(0, len(agent_ids), f'count_{p_key}_{s}')
            
    # Total agents assigned to any shift for a profile must not exceed available agents in that profile
    for p_key, agent_ids in profiles.items():
        model.Add(sum(count_vars[(p_key, s)] for s in range(len(shift_templates))) <= len(agent_ids))
        
    # available_at_hour[p_key, t] = sum(count[p_key, s] * x[s, t])
    available_at_hour = {}
    for p_key in profiles.keys():
        for t in range(24):
            expr = sum(count_vars[(p_key, s)] for s in range(len(shift_templates)) if shift_templates[s]['x'][t] == 1)
            available_at_hour[(p_key, t)] = model.NewIntVar(0, len(profiles[p_key]), f'avail_{p_key}_{t}')
            model.Add(available_at_hour[(p_key, t)] == expr)
            
    # assign_prof[p_key, k, t] = how many agents of profile p are working on skill k at hour t
    assign_prof = {}
    for p_key in profiles.keys():
        for t in range(24):
            for k in skills:
                if k in p_key:
                    assign_prof[(p_key, k, t)] = model.NewIntVar(0, len(profiles[p_key]), f'assign_{p_key}_{k}_{t}')
                else:
                    assign_prof[(p_key, k, t)] = 0
                    
            # Sum of assignments across skills must equal available agents for that profile
            valid_skills = [k for k in skills if k in p_key]
            model.Add(sum(assign_prof[(p_key, k, t)] for k in valid_skills) == available_at_hour[(p_key, t)])

    # Shortfall and idle variables
    shortfall = {}
    idle = {}
    for k in skills:
        for t in range(24):
            shortfall[(k, t)] = model.NewIntVar(0, 1000, f'shortfall_{k}_{t}')
            idle[(k, t)] = model.NewIntVar(0, 1000, f'idle_{k}_{t}')
            
            assigned_total = sum(assign_prof[(p_key, k, t)] for p_key in profiles.keys() if k in p_key)
            
            diff = model.NewIntVar(-1000, 1000, f'diff_{k}_{t}')
            model.Add(diff == assigned_total - demand[(k, t)])
            model.AddMaxEquality(idle[(k, t)], [0, diff])
            
            neg_diff = model.NewIntVar(-1000, 1000, f'neg_diff_{k}_{t}')
            model.Add(neg_diff == demand[(k, t)] - assigned_total)
            model.AddMaxEquality(shortfall[(k, t)], [0, neg_diff])
            
    # 5. Objective Function
    w_cost = 1.0
    w_shortfall = 200.0  # Must strictly exceed shift cost (120) to prevent understaffing
    w_idle = 5.0        # Minor penalty for overstaffing
    
    total_cost = sum(count_vars[(p_key, s)] * shift_templates[s]['cost'] for p_key in profiles.keys() for s in range(len(shift_templates)))
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
                sched = sum(solver.Value(assign_prof[(p_key, k, t)]) for p_key in profiles.keys() if k in p_key)
                total_req += req
                total_sched += sched
                
            results.append({
                'hour': t,
                'interval': f"{t:02d}:00-{(t+1)%24:02d}:00",
                'calls': df_day[df_day['hour'] == t]['predicted_calls'].sum(),
                'required_agents': total_req,
                'scheduled_agents': total_sched
            })
            
        # Post-process to assign specific agent IDs
        agent_shifts = []
        total_cost_calc = 0
        
        for p_key, agent_ids in profiles.items():
            assigned_idx = 0
            for s in range(len(shift_templates)):
                num_on_shift = solver.Value(count_vars[(p_key, s)])
                template = shift_templates[s]
                
                for _ in range(num_on_shift):
                    if template['name'] != 'None':
                        agent_id = agent_ids[assigned_idx]
                        total_cost_calc += template['cost']
                        agent_shifts.append({
                            'agent_id': agent_id,
                            'skills': '|'.join(p_key),
                            'shift_name': template['name'],
                            'cost': template['cost'],
                            'overtime': template['overtime']
                        })
                    assigned_idx += 1
                    
        # Apply total cost to all rows for reference (optional, better to put in shifts summary)
        for r in results:
            r['cost'] = total_cost_calc
            
        df_results = pd.DataFrame(results)
        os.makedirs("results", exist_ok=True)
        df_results.to_csv(os.path.join("results", "classical_optimization_schedule.csv"), index=False)
        print("Classical optimization completed and saved to results/classical_optimization_schedule.csv")
        df_shifts = pd.DataFrame(agent_shifts)
        df_shifts.to_csv(os.path.join("results", "agent_shifts_detailed.csv"), index=False)
        
    else:
        print("Solver failed to find a feasible solution.")
        
if __name__ == "__main__":
    run_classical_optimization()
