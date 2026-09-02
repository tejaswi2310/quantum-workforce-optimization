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
from app.core_engine.queue.queue_simulator import required_agents_for_sla, TARGET_SLA, TARGET_WAIT_SECONDS, erlang_c
import uuid
from app.services.storage_service import StorageService

def run_classical_optimization(run_id: uuid.UUID = None):
    print("--- Running Classical Optimization (Full MIP) ---")
    storage = StorageService(run_id)
    storage.ensure_run_dirs()

    forecast_path = storage.data_path("processed/forecast_results.csv")
    if not os.path.exists(forecast_path):
        # Fallback to global data/processed for backward compatibility during tests if needed
        global_path = os.path.join("data", "processed", "forecast_results.csv")
        if os.path.exists(global_path):
            forecast_path = global_path
        else:
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
    
    pd.DataFrame(validation_results).to_csv(storage.result_path("erlang_requirement_validation.csv"), index=False)
    
    demand = {}
    skills = df_day['skill_group'].unique()
    for k in skills:
        for t in range(24):
            val = df_day[(df_day['skill_group'] == k) & (df_day['hour'] == t)]['required_agents'].sum()
            demand[(k, t)] = int(val)
            
    # 2. Setup Agents and Skills from Roster
    roster_path = storage.data_path("raw/synthetic_roster.csv")
    if not os.path.exists(roster_path):
        global_roster_path = os.path.join("data", "raw", "synthetic_roster.csv")
        if os.path.exists(global_roster_path):
            roster_path = global_roster_path
        else:
            raise FileNotFoundError(f"Roster not found at {roster_path}. Please run data_generator.py first.")
            
    df_roster = pd.read_csv(roster_path, dtype={'availability': str})
    if df_roster.empty:
        raise ValueError(f"Roster at {roster_path} is empty.")
        
    agents = []
    for _, row in df_roster.iterrows():
        agent_id = str(row['agent_id'])
        if not agent_id:
            raise ValueError("Found agent with empty ID.")
        
        agent_skills = str(row['skills']).split('|')
        agent_wage = float(row['wage'])
        if agent_wage <= 0:
            raise ValueError(f"Invalid wage for agent {agent_id}: {agent_wage}")
            
        availability_str = str(row.get('availability', '1'*24))
        max_hours = int(row.get('max_weekly_hours', 40))

        agents.append({
            'id': agent_id,
            'skills': agent_skills,
            'wage': agent_wage,
            'availability': availability_str,
            'max_weekly_hours': max_hours
        })

    # Validation: Enforce unique IDs
    agent_ids = [a['id'] for a in agents]
    if len(agent_ids) != len(set(agent_ids)):
        raise ValueError("Duplicate agent IDs found in the roster.")

    # 3. Define Shift Templates
    # Each template provides a 24-hour binary array for work (x)
    # 0 = not working, 1 = working
    from app.schemas.shift import get_default_shift_configs, generate_shifts

    # D3.3-B: Dynamic Shift Configuration
    # We use the default configs here to preserve identical backward compatibility
    # with the existing classical CP-SAT schedule architecture.
    configs = get_default_shift_configs()
    generated_templates = generate_shifts(configs)

    # Convert to standard dict structure for the solver
    shift_templates = [t.model_dump() for t in generated_templates]

    # 4. Initialize CP-SAT Model
    model = cp_model.CpModel()

    # x[i, s] = 1 if agent i takes shift template s
    x = {}
    for i, agent in enumerate(agents):
        for s in range(len(shift_templates)):
            template = shift_templates[s]
            x[(i, s)] = model.NewBoolVar(f'x_{i}_{s}')

            # Phase 2: Agent Availability Constraint
            # If the shift requires work at an hour the agent is unavailable, prohibit the assignment.
            if template['name'] != 'None':
                can_work = True
                for t in range(24):
                    if template['x'][t] == 1 and agent['availability'][t] == '0':
                        can_work = False
                        break
                if not can_work:
                    model.Add(x[(i, s)] == 0)

        # Agent can only take exactly one shift
        model.AddExactlyOne([x[(i, s)] for s in range(len(shift_templates))])

        # Phase 4 & 5: Maximum Weekly Hours Constraint
        # Sum of all assigned payable hours across all shifts must not exceed max_weekly_hours.
        assigned_payable_hours = sum(
            x[(i, s)] * (shift_templates[s]['hours'] + shift_templates[s]['overtime_hours'])
            for s in range(len(shift_templates))
        )
        model.Add(assigned_payable_hours <= agent['max_weekly_hours'])
        
    # y[i, k, t] = 1 if agent i is working on skill k at hour t
    y = {}
    for i, agent in enumerate(agents):
        for t in range(24):
            for k in skills:
                y[(i, k, t)] = model.NewBoolVar(f'y_{i}_{k}_{t}')
                # If agent doesn't have the skill, they can't answer it
                if k not in agent['skills']:
                    model.Add(y[(i, k, t)] == 0)
                    
            # At any hour t, an agent can answer at most 1 skill
            model.AddAtMostOne([y[(i, k, t)] for k in skills])
            
            # Agent can only answer a skill at hour t if they are working at hour t
            is_working_at_t = sum(x[(i, s)] for s in range(len(shift_templates)) if shift_templates[s]['x'][t] == 1)
            model.Add(sum(y[(i, k, t)] for k in skills) == is_working_at_t)

    # Shortfall and idle variables
    shortfall = {}
    idle = {}
    for k in skills:
        for t in range(24):
            shortfall[(k, t)] = model.NewIntVar(0, 1000, f'shortfall_{k}_{t}')
            idle[(k, t)] = model.NewIntVar(0, 1000, f'idle_{k}_{t}')
            
            assigned_total = sum(y[(i, k, t)] for i in range(len(agents)))
            
            diff = model.NewIntVar(-1000, 1000, f'diff_{k}_{t}')
            model.Add(diff == assigned_total - demand[(k, t)])
            model.AddMaxEquality(idle[(k, t)], [0, diff])
            
            neg_diff = model.NewIntVar(-1000, 1000, f'neg_diff_{k}_{t}')
            model.Add(neg_diff == demand[(k, t)] - assigned_total)
            model.AddMaxEquality(shortfall[(k, t)], [0, neg_diff])
            
    # 5. Objective Function
    # We want to minimize cost but severely penalize shortfall
    w_cost = 1
    w_shortfall = 20000  # Must strictly exceed maximum shift cost to prevent understaffing
    w_idle = 5
    
    total_cost_expr = []
    for i, agent in enumerate(agents):
        wage = agent['wage']
        ot_rate = wage * 1.5
        for s in range(len(shift_templates)):
            shift = shift_templates[s]
            cost = int(round(wage * shift['hours'] + ot_rate * shift['overtime_hours']))
            if cost > 0:
                total_cost_expr.append(x[(i, s)] * cost)
                
    total_cost = sum(total_cost_expr)
    total_shortfall = sum(shortfall[(k, t)] for k in skills for t in range(24))
    total_idle = sum(idle[(k, t)] for k in skills for t in range(24))
    
    model.Minimize(
        w_cost * total_cost + 
        w_shortfall * total_shortfall + 
        w_idle * total_idle
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
                sched = sum(solver.Value(y[(i, k, t)]) for i in range(len(agents)))
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
        total_cost_calc = 0.0
        
        for i, agent in enumerate(agents):
            for s in range(len(shift_templates)):
                if solver.Value(x[(i, s)]) == 1:
                    template = shift_templates[s]
                    if template['name'] != 'None':
                        wage = agent['wage']
                        ot_rate = wage * 1.5
                        shift_cost = round(wage * template['hours'] + ot_rate * template['overtime_hours'], 2)
                        total_cost_calc += shift_cost
                        
                        agent_shifts.append({
                            'agent_id': agent['id'],
                            'skills': '|'.join(agent['skills']),
                            'shift_name': template['name'],
                            'cost': shift_cost,
                            'overtime': template['overtime_hours']
                        })
                    break
                    
        # Apply total cost to all rows for reference (optional, better to put in shifts summary)
        for r in results:
            r['cost'] = total_cost_calc
            
        df_results = pd.DataFrame(results)
        df_results.to_csv(storage.result_path("classical_optimization_schedule.csv"), index=False)
        print(f"Classical optimization completed and saved to {storage.result_path('classical_optimization_schedule.csv')}")
        df_shifts = pd.DataFrame(agent_shifts)
        df_shifts.to_csv(storage.result_path("agent_shifts_detailed.csv"), index=False)
        
        # Save metrics for API response
        total_shortfall_val = sum(solver.Value(shortfall[(k, t)]) for k in skills for t in range(24))
        optimization_status = "OPTIMAL_WITH_SHORTFALL" if total_shortfall_val > 0 else "OPTIMAL"
        if status == cp_model.FEASIBLE:
            optimization_status = "FEASIBLE_WITH_SHORTFALL" if total_shortfall_val > 0 else "FEASIBLE"
            
        metrics = {
            "optimization_status": optimization_status,
            "staffing_shortfall": int(total_shortfall_val),
            "total_cost": round(total_cost_calc, 2)
        }
        with open(storage.result_path("optimization_metrics.json"), "w") as f:
            json.dump(metrics, f)
            
    else:
        print("Solver failed to find a feasible solution.")
        metrics = {
            "optimization_status": "INFEASIBLE",
            "staffing_shortfall": -1,
            "total_cost": 0.0
        }
        with open(storage.result_path("optimization_metrics.json"), "w") as f:
            json.dump(metrics, f)
        
if __name__ == "__main__":
    run_classical_optimization()
