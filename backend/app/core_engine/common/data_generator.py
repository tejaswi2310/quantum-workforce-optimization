"""
Module for generating synthetic historical call center data.
Simulates call volume patterns, handle times, and historical SLAs across channels and skills.
"""
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta

def generate_data():
    np.random.seed(42)
    start_date = datetime(2026, 1, 1)
    days = 180
    channels = ["Voice", "Chat", "Email"]
    skills = ["Billing", "Technical", "Sales", "General"]
    
    records = []
    
    # Simple holiday list for 2026 (New Year, MLK, Memorial Day, etc.)
    holidays = {
        "2026-01-01": 1,
        "2026-01-19": 1,
        "2026-02-16": 1,
        "2026-05-25": 1,
        "2026-07-04": 1,
    }
    
    for day in range(days):
        current_date = start_date + timedelta(days=day)
        date_str = current_date.strftime("%Y-%m-%d")
        day_name = current_date.strftime("%A")
        is_holiday = holidays.get(date_str, 0)
        is_weekend = 1 if day_name in ["Saturday", "Sunday"] else 0
        
        for hour in range(24):
            # Base call pattern by hour (bell curve peaking around 11:00 and 14:00)
            if 8 <= hour <= 17:
                hour_factor = np.sin((hour - 8) / 9 * np.pi) * 20 + 15
            else:
                hour_factor = np.random.uniform(2, 8)
                
            # Weekend and holiday drops
            if is_weekend:
                hour_factor *= 0.5
            if is_holiday:
                hour_factor *= 0.3
                
            for channel in channels:
                channel_factor = 1.2 if channel == "Voice" else (0.8 if channel == "Chat" else 0.5)
                
                for skill in skills:
                    skill_factor = 1.0
                    if skill == "Technical":
                        skill_factor = 1.3
                    elif skill == "Sales":
                        skill_factor = 1.1
                    elif skill == "Billing":
                        skill_factor = 0.8
                    else:
                        skill_factor = 0.6
                        
                    # Calculate calls received
                    base_calls = hour_factor * channel_factor * skill_factor
                    calls = int(np.random.poisson(base_calls))
                    
                    # Average handle time in seconds
                    if channel == "Voice":
                        base_aht = 300
                    elif channel == "Chat":
                        base_aht = 450
                    else:
                        base_aht = 600
                    
                    # AHT varies slightly based on volume
                    aht = int(np.random.normal(base_aht, base_aht * 0.1))
                    if aht < 60:
                        aht = 60
                        
                    # Agents available - historically scheduled (rough estimation)
                    needed_agents = max(1, int(calls * (aht / 3600) * 1.2))
                    agents_avail = int(np.random.normal(needed_agents, max(1, needed_agents * 0.1)))
                    if agents_avail < 1:
                        agents_avail = 1
                        
                    # SLA Achieved (historical percentage between 0 and 100)
                    if agents_avail >= needed_agents:
                        sla = min(100.0, np.random.normal(92.0, 3.0))
                    else:
                        ratio = agents_avail / needed_agents
                        sla = max(30.0, min(100.0, np.random.normal(80.0 * ratio, 5.0)))
                        
                    records.append({
                        "date": date_str,
                        "day_of_week": day_name,
                        "hour": hour,
                        "interval": f"{hour:02d}:00-{(hour+1)%24:02d}:00",
                        "channel": channel,
                        "skill_group": skill,
                        "calls_received": calls,
                        "avg_handle_time": aht,
                        "agents_available": agents_avail,
                        "holiday": is_holiday,
                        "sla_achieved": round(sla, 2)
                    })
                    
    df = pd.DataFrame(records)
    
    # Create directory if not exists
    os.makedirs(os.path.join("data", "raw"), exist_ok=True)
    df.to_csv(os.path.join("data", "raw", "synthetic_call_center.csv"), index=False)
    
    print(f"Generated data shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")

if __name__ == "__main__":
    generate_data()
