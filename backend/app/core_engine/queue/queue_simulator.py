"""
Module for executing Erlang C queue simulation.
Validates that the optimized schedule meets the required Service Level Agreement (SLA).
"""
import os
import math
import pandas as pd
import numpy as np
import uuid
from app.services.storage_service import StorageService

# Configuration parameters
TARGET_SLA = 0.80
TARGET_WAIT_SECONDS = 20
AVERAGE_PATIENCE_SECONDS = 120.0  # Configurable assumption for deterministic abandonment approximation

def required_agents_for_sla(calls, aht_seconds, interval_seconds, target_sla, target_wait_seconds):
    """
    Calculates the minimum required agents to achieve the target SLA using Erlang-C.
    Optimized to use the recursive Erlang-B/C relationship to avoid O(c^2) behavior.
    """
    if calls <= 0:
        return 0, 0.0, 1.0, 0.0 # agents, traffic, sla, wait_prob

    arrival_rate = calls / interval_seconds
    A = arrival_rate * aht_seconds

    # Must start iterating with agents > A for stability, minimum floor(A) + 1
    c = max(1, int(math.floor(A)) + 1)

    # Compute initial Erlang B for c
    B = 1.0
    if A > 0:
        for i in range(1, c + 1):
            B = (A * B) / (i + A * B)

    while True:
        if A <= 0:
            p_w = 0.0
        else:
            denom = c - A * (1 - B)
            p_w = (c * B) / denom if denom > 0 else 1.0

        p_w = max(0.0, min(1.0, p_w))
        sla = 1.0 - p_w * math.exp(-(c - A) * target_wait_seconds / aht_seconds)

        if sla >= target_sla:
            return c, A, sla, p_w

        # Advance B for c+1 for the next iteration
        c += 1
        if A > 0:
            B = (A * B) / (c + A * B)

def erlang_c(c, A):
    if A >= c:
        return 1.0
    if A <= 0:
        return 0.0

    # Numerically stable Erlang C calculation using recursive Erlang B formula
    try:
        B = 1.0
        for i in range(1, int(c) + 1):
            B = (A * B) / (i + A * B)

        denom = c - A * (1 - B)
        if denom <= 0:
            return 1.0

        p_w = (c * B) / denom
        return max(0.0, min(1.0, p_w))
    except Exception:
        return 0.0

def run_queue_simulation(run_id: uuid.UUID = None):
    storage = StorageService(run_id)
    storage.ensure_run_dirs()

    # Load classical optimization schedule
    # We will validate both classical and shift schedules, but the prompt focus is on running this script to verify SLA
    schedule_path = storage.result_path("classical_optimization_schedule.csv")
    if not os.path.exists(schedule_path):
        # Fallback to global results for backward compatibility
        global_path = os.path.join("results", "classical_optimization_schedule.csv")
        if os.path.exists(global_path):
            schedule_path = global_path
        else:
            raise FileNotFoundError(f"Schedule not found at {schedule_path}. Run optimizer.py first.")

    df = pd.read_csv(schedule_path)

    # Erlang C parameters
    aht = 300 # average handle time in seconds
    t = 20 # SLA target response time (e.g. 80% calls answered within 20 seconds)

    results = []
    lowest_sla = 100.0
    all_pass = True

    print("Running Erlang C Queue Validation for 168 hours:")
    print(f"{'Day':<12}{'Hour':<6}{'Calls':<8}{'Sched':<8}{'Req':<8}{'Traffic':<10}{'SLA %':<10}{'ASA (s)':<10}{'Status':<12}")
    print("-" * 87)

    for idx, row in df.iterrows():
        hour = int(row['hour'])
        t = int(row.get('absolute_hour', idx))
        d_str = row.get('date', 'Unknown')
        calls = float(row['calls'])
        scheduled_agents = int(row['scheduled_agents'])
        required_agents = int(row.get('required_agents', scheduled_agents))

        # Traffic intensity A = arrival_rate * AHT / 3600
        A = (calls * aht) / 3600.0

        # We must simulate EXACTLY what the optimizer provided.
        sim_agents = scheduled_agents

        sla_percent = None
        asa = None
        utilization = None
        metric_validity = "UNKNOWN"
        abandonment_not_modeled = True

        # Edge case: zero calls
        if calls <= 0:
            sla_percent = 100.0
            asa = 0.0
            utilization = 0.0
            metric_validity = "VALID_ERLANG_C"
            status = "PASS"
            p_w = 0.0
            abandonment_rate_percent = 0.0
            abandonment_not_modeled = False

        # Edge case: negative or zero agents but calls exist
        elif sim_agents <= 0:
            sla_percent = None
            asa = None
            utilization = None
            metric_validity = "INVALID_INPUT" if sim_agents < 0 else "OVERLOADED"
            status = "FAIL"
            p_w = 1.0
            all_pass = False
            lowest_sla = 0.0
            abandonment_rate_percent = 100.0
            abandonment_not_modeled = False

        # Overloaded: Erlang-C is mathematically unstable for c <= A
        elif sim_agents <= A:
            sla_percent = None
            asa = None
            utilization = (A / sim_agents) * 100.0
            metric_validity = "OVERLOADED"
            status = "FAIL"
            p_w = 1.0
            all_pass = False
            lowest_sla = 0.0
            abandonment_rate_percent = 100.0
            abandonment_not_modeled = False

        # Valid Erlang-C
        else:
            p_w = erlang_c(sim_agents, A)

            # Service Level (SLA)
            # SLA = 1 - P_w * exp(-(c - A) * t / AHT)
            sla = 1.0 - p_w * math.exp(-(sim_agents - A) * t / aht)
            sla_percent = max(0.0, min(100.0, sla * 100.0))

            # Average Speed of Answer (ASA) in seconds
            asa = (p_w * aht) / (sim_agents - A)

            # Agent utilization
            utilization = (A / sim_agents) * 100.0
            metric_validity = "VALID_ERLANG_C"

            # Deterministic Abandonment Approximation
            prob_abandon = p_w * (asa / (asa + AVERAGE_PATIENCE_SECONDS))
            abandonment_rate_percent = max(0.0, min(100.0, prob_abandon * 100.0))
            abandonment_not_modeled = False

            status = "PASS" if sla_percent >= 80.0 else "FAIL"
            if sla_percent < 80.0:
                all_pass = False
            if sla_percent < lowest_sla:
                lowest_sla = sla_percent

        results.append({
            "date": d_str,
            "hour": hour,
            "absolute_hour": t,
            "interval": f"{hour:02d}:00-{(hour+1)%24:02d}:00",
            "calls": calls,
            "scheduled_agents": sim_agents,
            "agents": sim_agents,  # For backward compatibility with dashboard.py
            "required_agents": required_agents,
            "offered_load": A,
            "sla_percent": round(sla_percent, 2) if sla_percent is not None else None,
            "asa_seconds": round(asa, 2) if asa is not None else None,
            "utilization_percent": round(utilization, 2) if utilization is not None else None,
            "abandonment_rate_percent": round(abandonment_rate_percent, 2) if abandonment_rate_percent is not None else None,
            "metric_validity": metric_validity,
            "abandonment_not_modeled": abandonment_not_modeled,
            "queue_status": status,
            "status": status  # For backward compatibility
        })

        asa_str = f"{asa:.2f}" if asa is not None else "N/A"
        sla_str = f"{sla_percent:.2f}" if sla_percent is not None else "N/A"
        print(f"{d_str:<12}{hour:<6}{calls:<8.1f}{sim_agents:<8}{required_agents:<8}{A:<10.2f}{sla_str:<10}{asa_str:<10}{metric_validity:<12}")

    df_validation = pd.DataFrame(results)
    storage.atomic_write_csv(df_validation, storage.result_path("queue_validation_results.csv"), index=False)

    print("-" * 87)
    print(f"Queue validation completed.")
    print(f"All 168 Hours PASS: {'YES' if all_pass else 'NO'}")
    print(f"Lowest SLA: {lowest_sla:.2f}%")

if __name__ == "__main__":
    run_queue_simulation()
