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

    # Data Contract Validations
    if 'date' not in df_forecast.columns or df_forecast['date'].isnull().any():
        raise ValueError("Forecast missing required 'date' column or contains null dates.")
    if 'hour' not in df_forecast.columns or df_forecast['hour'].isnull().any():
        raise ValueError("Forecast missing required 'hour' column or contains null hours.")
    if 'skill_group' not in df_forecast.columns or df_forecast['skill_group'].isnull().any():
        raise ValueError("Forecast missing required 'skill_group' column or contains null skills.")

    invalid_hours = df_forecast[~df_forecast['hour'].astype(int).between(0, 23)]
    if not invalid_hours.empty:
        raise ValueError("Forecast contains invalid hour(s) outside 0..23 range.")

    unique_dates = sorted(df_forecast['date'].unique())
    if len(unique_dates) < 7:
        raise ValueError(f"Forecast must contain at least 7 days, found {len(unique_dates)}.")
    week_dates = unique_dates[:7]
    df_week = df_forecast[df_forecast['date'].isin(week_dates)].copy()
    df_week['hour'] = df_week['hour'].astype(int)
    df_week = df_week.sort_values(by=['date', 'hour']).reset_index(drop=True)

    date_hours = df_week[['date', 'hour']].drop_duplicates()
    if len(date_hours) != 168:
        raise ValueError(f"Forecast must contain exactly 168 hours for the week. Found {len(date_hours)}.")
    date_to_day_idx = {d: i for i, d in enumerate(week_dates)}


    # 1. Aggregate demand by skill and hour
    # P0-B FIX: Pool workload by skill group BEFORE calculating Erlang-C
    df_pooled = df_week.groupby(['date', 'hour', 'interval', 'skill_group'], as_index=False)['predicted_calls'].sum()

    aht = 300
    interval_seconds = 3600

    validation_results = []
    demand = {}
    skills = df_week['skill_group'].unique()
    for k in skills:
        for t in range(168):
            demand[(k, t)] = 0

    for idx, row in df_pooled.iterrows():
        calls = row['predicted_calls']
        c, A, achieved_sla, p_w = required_agents_for_sla(
            calls, aht, interval_seconds, TARGET_SLA, TARGET_WAIT_SECONDS
        )

        # Check minimality if c > 0
        minimality_check = "PASS"
        previous_agents_sla = 0.0
        if c > max(1, int(math.floor(A))):
            prev_c = c - 1
            prev_p_w = erlang_c(prev_c, A)
            previous_agents_sla = 1.0 - prev_p_w * math.exp(-(prev_c - A) * TARGET_WAIT_SECONDS / aht)
            if previous_agents_sla >= TARGET_SLA:
                minimality_check = "FAIL"
        elif c > 0 and c <= A:
            minimality_check = "FAIL (Unstable)"

        validation_results.append({
            'date': row['date'],
            'hour': row['hour'],
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
            'minimality_check': minimality_check
        })

        k = row['skill_group']
        t = date_to_day_idx[row['date']] * 24 + row['hour']
        demand[(k, t)] += int(c)

    pd.DataFrame(validation_results).to_csv(storage.result_path("erlang_requirement_validation.csv"), index=False)

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

        raw_avail = str(row.get('availability', '1'*168))
        if len(raw_avail) == 24:
            availability_str = raw_avail * 7
        elif len(raw_avail) > 168:
            availability_str = raw_avail[:168]
        elif len(raw_avail) == 168:
            availability_str = raw_avail
        else:
            raise ValueError(f"Agent {agent_id} has malformed availability string of length {len(raw_avail)}. Must be exactly 24 or 168 characters.")

        max_hours = int(row.get('max_weekly_hours', 40))
        preferred_shift = str(row.get('preferred_shift', 'flexible'))

        agents.append({
            'id': agent_id,
            'skills': agent_skills,
            'wage': agent_wage,
            'availability': availability_str,
            'max_weekly_hours': max_hours,
            'preferred_shift': preferred_shift
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

    # Precompute working absolute hours for each template on each day
    def get_shift_working_hours(template, day_index):
        if template['name'] == 'None':
            return []
        abs_start = day_index * 24 + template['start_hour']
        wh = []
        for offset in range(template['duration_hours']):
            # Check if this offset is a working hour by looking at the 24h wrapped pattern in 'x'
            if template['x'][(template['start_hour'] + offset) % 24] == 1:
                h = abs_start + offset
                if h < 168:
                    wh.append(h)
        return wh

    shift_working_hours = {}
    for d in range(7):
        for s in range(len(shift_templates)):
            shift_working_hours[(d, s)] = get_shift_working_hours(shift_templates[s], d)

    # x[i, d, s] = 1 if agent i takes shift template s on day d
    x = {}
    for i, agent in enumerate(agents):
        for d in range(7):
            for s in range(len(shift_templates)):
                x[(i, d, s)] = model.NewBoolVar(f'x_{i}_{d}_{s}')

                working_hours = shift_working_hours[(d, s)]
                if working_hours:
                    # Agent Availability Constraint
                    can_work = all(agent['availability'][t] == '1' for t in working_hours)
                    if not can_work:
                        model.Add(x[(i, d, s)] == 0)

            # Agent can only take exactly one shift per day (including None)
            model.AddExactlyOne([x[(i, d, s)] for s in range(len(shift_templates))])

        # Maximum Weekly Hours Constraint
        assigned_payable_hours = sum(
            x[(i, d, s)] * (shift_templates[s]['hours'] + shift_templates[s]['overtime_hours'])
            for d in range(7) for s in range(len(shift_templates))
        )
        model.Add(assigned_payable_hours <= agent['max_weekly_hours'])

        # Cross-day Overlap Prevention (an agent works at most 1 shift at any absolute hour t)
        for t in range(168):
            shifts_at_t = []
            d_curr = t // 24
            days_to_check = [d_curr, d_curr - 1] if d_curr > 0 else [d_curr]
            for d in days_to_check:
                for s in range(len(shift_templates)):
                    if t in shift_working_hours[(d, s)]:
                        shifts_at_t.append(x[(i, d, s)])
            if len(shifts_at_t) > 1:
                model.AddAtMostOne(shifts_at_t)

    # y[i, k, t] = 1 if agent i is working on skill k at absolute hour t
    y = {}
    for i, agent in enumerate(agents):
        for t in range(168):
            for k in skills:
                y[(i, k, t)] = model.NewBoolVar(f'y_{i}_{k}_{t}')
                if k not in agent['skills']:
                    model.Add(y[(i, k, t)] == 0)

            model.AddAtMostOne([y[(i, k, t)] for k in skills])

            d_curr = t // 24
            days_to_check = [d_curr, d_curr - 1] if d_curr > 0 else [d_curr]
            shifts_working_at_t = [
                x[(i, d, s)]
                for d in days_to_check
                for s in range(len(shift_templates))
                if t in shift_working_hours[(d, s)]
            ]
            model.Add(sum(y[(i, k, t)] for k in skills) == sum(shifts_working_at_t))

    # Shortfall and idle variables
    shortfall = {}
    idle = {}
    for k in skills:
        for t in range(168):
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
    w_pref = 5  # Soft penalty for schedule friction / preference violations

    total_cost_expr = []
    total_pref_penalty_expr = []

    for i, agent in enumerate(agents):
        wage = agent['wage']
        ot_rate = wage * 1.5
        pref = agent['preferred_shift']

        for d in range(7):
            for s in range(len(shift_templates)):
                shift = shift_templates[s]
                cost = int(round(wage * shift['hours'] + ot_rate * shift['overtime_hours']))
                if cost > 0:
                    total_cost_expr.append(x[(i, d, s)] * cost)

                if shift['name'] != 'None' and pref != 'flexible':
                    start_h = shift['start_hour']
                    is_match = True
                    if pref == 'morning' and not (6 <= start_h <= 10): is_match = False
                    elif pref == 'afternoon' and not (11 <= start_h <= 15): is_match = False
                    elif pref == 'evening' and not (16 <= start_h <= 20): is_match = False

                    if not is_match:
                        total_pref_penalty_expr.append(x[(i, d, s)])

    total_cost = sum(total_cost_expr)
    total_shortfall = sum(shortfall[(k, t)] for k in skills for t in range(168))
    total_idle = sum(idle[(k, t)] for k in skills for t in range(168))
    total_pref = sum(total_pref_penalty_expr)

    model.Minimize(
        w_cost * total_cost +
        w_shortfall * total_shortfall +
        w_idle * total_idle +
        w_pref * total_pref
    )

    # 6. Solve
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 60.0
    solver.parameters.num_search_workers = 8
    solver.parameters.random_seed = 42
    solver.parameters.log_search_progress = True
    status = solver.Solve(model)

    if status in [cp_model.OPTIMAL, cp_model.FEASIBLE]:
        print(f"Solver Status: {solver.StatusName(status)}")
        print(f"Objective Value: {solver.ObjectiveValue()}")

        # 7. Extract Results
        results = []
        for d_idx, d_str in enumerate(week_dates):
            for h in range(24):
                t = d_idx * 24 + h
                total_req = 0
                total_sched = 0
                for k in skills:
                    req = demand[(k, t)]
                    sched = sum(solver.Value(y[(i, k, t)]) for i in range(len(agents)))
                    total_req += req
                    total_sched += sched

                calls_at_t = df_week[(df_week['date'] == d_str) & (df_week['hour'] == h)]['predicted_calls'].sum()

                results.append({
                    'date': d_str,
                    'day_of_week': d_idx,
                    'hour': h,
                    'absolute_hour': t,
                    'interval': f"{h:02d}:00-{(h+1)%24:02d}:00",
                    'calls': calls_at_t,
                    'required_agents': total_req,
                    'scheduled_agents': total_sched
                })

        # Post-process to assign specific agent IDs
        agent_shifts = []
        total_cost_calc = 0.0

        for i, agent in enumerate(agents):
            for d in range(7):
                for s in range(len(shift_templates)):
                    if solver.Value(x[(i, d, s)]) == 1:
                        template = shift_templates[s]
                        if template['name'] != 'None':
                            wage = agent['wage']
                            ot_rate = wage * 1.5
                            shift_cost = round(wage * template['hours'] + ot_rate * template['overtime_hours'], 2)
                            total_cost_calc += shift_cost

                            agent_shifts.append({
                                'agent_id': agent['id'],
                                'day_index': d,
                                'date': week_dates[d],
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
        total_shortfall_val = sum(solver.Value(shortfall[(k, t)]) for k in skills for t in range(168))
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
