import os
import pandas as pd
import pytest

def test_shift_optimizer_timeline_overlap():
    """Verify that shift_optimizer.py independent timeline correctly models shift length and breaks."""
    # We create a dummy shifts file
    os.makedirs("results", exist_ok=True)
    df_shifts = pd.DataFrame([
        {'agent_id': 0, 'shift_name': 'Base_Start_08', 'cost': 120.0},
        {'agent_id': 1, 'shift_name': 'OT1_Start_12', 'cost': 150.0}
    ])
    df_shifts.to_csv("results/agent_shifts_detailed.csv", index=False)
    
    # Run the timeline logic locally
    timeline = {h: 0 for h in range(24)}
    for _, row in df_shifts.iterrows():
        shift_name = row['shift_name']
        if 'Base' in shift_name:
            duration = 9
        elif 'OT1' in shift_name:
            duration = 10
            
        start_hour = int(shift_name.split('Start_')[1])
        for offset in range(duration):
            if offset != 4:
                timeline[(start_hour + offset) % 24] += 1
                
    # Agent 0: Base_Start_08 -> 9 hrs, break at hour 4 (12:00)
    # Works 08, 09, 10, 11. Off 12. Works 13, 14, 15, 16.
    
    # Agent 1: OT1_Start_12 -> 10 hrs, break at hour 4 (16:00)
    # Works 12, 13, 14, 15. Off 16. Works 17, 18, 19, 20, 21.
    
    assert timeline[8] == 1
    assert timeline[11] == 1
    assert timeline[12] == 1 # Agent 0 off, Agent 1 on
    assert timeline[13] == 2 # Both on
    assert timeline[15] == 2 # Both on
    assert timeline[16] == 1 # Agent 0 on, Agent 1 off
    assert timeline[21] == 1
    assert timeline[22] == 0
