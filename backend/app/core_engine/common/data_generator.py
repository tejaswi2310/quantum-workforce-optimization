"""
Module for generating synthetic historical call center data.
Simulates call volume patterns, handle times, and historical SLAs across channels and skills.
"""
import os
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import uuid
from app.services.storage_service import StorageService
from app.schemas.roster import RosterAgent
from pydantic import ValidationError

def generate_data(run_id: uuid.UUID = None):
    storage = StorageService(run_id)
    storage.ensure_run_dirs()

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

    data_path = storage.data_path("raw/synthetic_call_center.csv")
    storage.atomic_write_csv(df, data_path, index=False)

    print(f"Generated data shape: {df.shape}")
    print(f"Columns: {list(df.columns)}")
    print(f"Saved to {data_path}")

    # Generate synthetic roster (deterministic)
    roster = []
    # Seed strictly for roster generation
    np.random.seed(12345)

    for i in range(1, 121):  # 120 agents
        num_skills = np.random.choice([1, 2, 3], p=[0.6, 0.3, 0.1])
        agent_skills = np.random.choice(skills, size=num_skills, replace=False).tolist()

        # Ensure minimal coverage for all skills
        if i <= len(skills):
            agent_skills = [skills[i-1]]

        # Heterogeneous wage structure
        base_wage = 15.0
        if "Technical" in agent_skills:
            base_wage += 5.0
        if "Sales" in agent_skills:
            base_wage += 2.0

        # Add random noise to wage to differentiate individuals
        wage = base_wage + np.random.uniform(0.0, 5.0)

        # New Phase 6B D3.3-A Roster Fields
        contract_type = str(np.random.choice(["FT", "PT"], p=[0.8, 0.2]))
        if contract_type == "FT":
            max_weekly_hours = 40
            preferred_shift = str(np.random.choice(["morning", "afternoon", "evening", "flexible"]))
        else:
            max_weekly_hours = int(np.random.uniform(20, 30))
            preferred_shift = str(np.random.choice(["morning", "afternoon", "evening", "flexible"]))

        # 24-char binary availability string
        # To avoid making preferred_shift a hard constraint, availability
        # is determined independently. For FT, usually highly available.
        # For PT, block out some random contiguous hours.
        if contract_type == "FT":
            availability_array = ["1"] * 24
        else:
            availability_array = ["1"] * 24
            # Randomly block out a 6-hour window for PT to simulate constraints
            start_block = np.random.randint(0, 18)
            for j in range(start_block, start_block + 6):
                availability_array[j] = "0"

        # Expand 24-hour daily availability to a full 168-hour weekly availability
        weekly_availability_array = availability_array * 7

        availability_str = "".join(weekly_availability_array)

        agent_dict = {
            "agent_id": f"AGT-{i:03d}",
            "skills": "|".join(agent_skills),
            "wage": round(wage, 2),
            "contract_type": contract_type,
            "max_weekly_hours": max_weekly_hours,
            "preferred_shift": preferred_shift,
            "availability": availability_str
        }

        # Validate through Pydantic
        try:
            validated_agent = RosterAgent(**agent_dict)
            roster.append(validated_agent.model_dump() if hasattr(validated_agent, 'model_dump') else validated_agent.dict())
        except ValidationError as e:
            print(f"Validation failed for agent {agent_dict['agent_id']}: {e}")
            raise

    df_roster = pd.DataFrame(roster)
    roster_path = storage.data_path("raw/synthetic_roster.csv")
    storage.atomic_write_csv(df_roster, roster_path, index=False)
    print(f"Generated roster with {len(df_roster)} agents.")
    print(f"Saved to {roster_path}")

if __name__ == "__main__":
    generate_data()
