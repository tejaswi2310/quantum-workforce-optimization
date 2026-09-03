import os
import uuid
import pandas as pd
from typing import Optional
from app.services.storage_service import StorageService

def get_average_wage(run_id: uuid.UUID) -> Optional[float]:
    """Calculates the average agent wage from the synthetic roster."""
    storage = StorageService(run_id)
    roster_path = storage.data_path("raw/synthetic_roster.csv")
    if not roster_path.exists():
        # Fallback for tests/local setups
        global_path = storage.root_dir / "data" / "raw" / "synthetic_roster.csv"
        if global_path.exists():
            roster_path = global_path
        else:
            return None

    try:
        df = pd.read_csv(roster_path)
        if 'wage' in df.columns and not df.empty:
            avg_wage = float(df['wage'].mean())
            return avg_wage if pd.notna(avg_wage) else None
        return None
    except Exception:
        return None

def calculate_baseline_cost(run_id: uuid.UUID) -> Optional[float]:
    """
    Calculates the naive baseline cost:
    Scheduling the maximum required agents for all 168 hours of the week at the average roster wage.
    Returns None if data is missing.
    """
    storage = StorageService(run_id)
    shift_schedule_path = storage.result_path("shift_schedule.csv")
    if not shift_schedule_path.exists():
        # Fallback to classical optimization schedule if shift_schedule not unified yet
        shift_schedule_path = storage.result_path("classical_optimization_schedule.csv")
        if not shift_schedule_path.exists():
            return None

    avg_wage = get_average_wage(run_id)
    if avg_wage is None:
        return None

    try:
        df = pd.read_csv(shift_schedule_path)
        if 'required_agents' in df.columns and not df.empty:
            peak_agents = float(df['required_agents'].max())
            if pd.notna(peak_agents):
                return float(peak_agents * 168 * avg_wage)
        return None
    except Exception:
        return None

def calculate_optimized_cost(run_id: uuid.UUID) -> Optional[float]:
    """
    Authoritative optimized cost calculated directly from actual assigned agent wages and hours.
    Extracts the pre-calculated cost column from agent_shifts_detailed.csv.
    """
    storage = StorageService(run_id)
    shifts_path = storage.result_path("agent_shifts_detailed.csv")
    if not shifts_path.exists():
        return None
    try:
        df = pd.read_csv(shifts_path)
        if 'cost' in df.columns and not df.empty:
            opt_cost = float(df['cost'].sum())
            return opt_cost if pd.notna(opt_cost) else None
        return None
    except Exception:
        return None

def get_peak_hour(run_id: uuid.UUID) -> Optional[str]:
    """
    Determines the peak demand hour dynamically from queue_validation_results.csv or forecast_results.csv.
    Tie-breaking: earliest absolute_hour.
    Returns a formatted string (e.g., '2023-10-01 14:00') or None if unavailable.
    """
    storage = StorageService(run_id)
    queue_path = storage.result_path("queue_validation_results.csv")

    if queue_path.exists():
        df = pd.read_csv(queue_path)
        metric_col = 'calls'
    else:
        forecast_path = storage.data_path("processed/forecast_results.csv")
        if forecast_path.exists():
            df = pd.read_csv(forecast_path)
            metric_col = 'predicted_calls'
        else:
            return None

    if metric_col not in df.columns or df.empty:
        return None

    try:
        if 'absolute_hour' in df.columns:
            sort_cols = [metric_col, 'absolute_hour']
            asc = [False, True]
        elif 'date' in df.columns and 'hour' in df.columns:
            sort_cols = [metric_col, 'date', 'hour']
            asc = [False, True, True]
        else:
            sort_cols = [metric_col]
            asc = [False]

        df_sorted = df.sort_values(by=sort_cols, ascending=asc)
        peak_row = df_sorted.iloc[0]

        day_str = peak_row.get('date', 'Unknown')
        hour_val = peak_row.get('hour')

        if pd.isna(hour_val) or hour_val == 'Unknown':
            return f"{day_str} Unknown"
        else:
            return f"{day_str} {int(hour_val):02d}:00"
    except Exception:
        return None
