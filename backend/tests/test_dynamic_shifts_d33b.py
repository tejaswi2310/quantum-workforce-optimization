import pytest
from app.schemas.shift import ShiftConfig, generate_shifts, get_default_shift_configs, ShiftTemplate
from pydantic import ValidationError

def test_basic_shift_generation():
    """1. Basic shift generation, 6. Correct normal-shift duration"""
    config = ShiftConfig(name="Morning", start_hour=8, duration_hours=8, break_hour_offset=-1, is_overtime=False)
    shifts = generate_shifts([config])
    
    # 0 index is always 'None'
    assert len(shifts) == 2
    assert shifts[0].name == "None"
    
    shift = shifts[1]
    assert shift.name == "Morning"
    assert shift.start_hour == 8
    assert shift.end_hour == 16
    assert shift.duration_hours == 8
    assert sum(shift.x) == 8
    
    # 16. 24-hour planning compatibility
    assert len(shift.x) == 24
    assert shift.x[8:16] == [1] * 8

def test_multiple_shifts_and_ordering():
    """2. Multiple shifts, 14. Stable ordering"""
    # Order doesn't matter for input, output should be deterministic
    c1 = ShiftConfig(name="Afternoon", start_hour=14, duration_hours=8)
    c2 = ShiftConfig(name="Morning", start_hour=8, duration_hours=8)
    c3 = ShiftConfig(name="Night", start_hour=22, duration_hours=8)
    
    shifts = generate_shifts([c1, c2, c3])
    
    assert len(shifts) == 4
    assert shifts[0].name == "None"
    assert shifts[1].name == "Morning"   # 8
    assert shifts[2].name == "Afternoon" # 14
    assert shifts[3].name == "Night"     # 22

def test_overnight_shift():
    """7. Correct overnight-shift duration"""
    config = ShiftConfig(name="Night", start_hour=22, duration_hours=8)
    shifts = generate_shifts([config])
    shift = shifts[1]
    
    assert shift.end_hour == 6
    assert sum(shift.x) == 8
    assert shift.x[22] == 1
    assert shift.x[23] == 1
    assert shift.x[0] == 1
    assert shift.x[5] == 1
    assert shift.x[6] == 0

def test_invalid_shift_configurations():
    """8. Invalid zero-duration, 9. Negative-duration, 10. Malformed time, 11. Excessively long"""
    # 8. Zero duration
    with pytest.raises(ValidationError):
        ShiftConfig(name="Bad", start_hour=8, duration_hours=0)
        
    # 9. Negative duration
    with pytest.raises(ValidationError):
        ShiftConfig(name="Bad", start_hour=8, duration_hours=-5)
        
    # 10. Malformed time
    with pytest.raises(ValidationError):
        ShiftConfig(name="Bad", start_hour=25, duration_hours=8)
        
    with pytest.raises(ValidationError):
        ShiftConfig(name="Bad", start_hour=-1, duration_hours=8)
        
    # 11. Excessively long (>24 hours)
    with pytest.raises(ValidationError):
        ShiftConfig(name="Bad", start_hour=8, duration_hours=25)

def test_unique_shift_ids_and_duplicates():
    """4. Unique shift IDs, 13. Duplicate prevention"""
    c1 = ShiftConfig(name="Shift A", start_hour=9, duration_hours=8)
    c2 = ShiftConfig(name="Shift A", start_hour=9, duration_hours=8)
    c3 = ShiftConfig(name="Shift B", start_hour=9, duration_hours=8)
    
    # c1 and c2 should produce exactly the same ID
    assert c1.shift_id == c2.shift_id
    assert c1.shift_id != c3.shift_id
    
    # Duplicates should be filtered out during generation
    shifts = generate_shifts([c1, c2, c3])
    assert len(shifts) == 3 # None, Shift A, Shift B
    
    # Assert IDs are actually unique
    ids = [s.shift_id for s in shifts]
    assert len(ids) == len(set(ids))

def test_deterministic_generation():
    """5. Deterministic generation, 12. Configuration changes, 17. Repeated generation"""
    configs = [ShiftConfig(name="Test", start_hour=9, duration_hours=8)]
    
    shifts_run_1 = generate_shifts(configs)
    shifts_run_2 = generate_shifts(configs)
    
    # 17. Repeated generation returns equivalent results
    assert shifts_run_1 == shifts_run_2
    
    # 12. Configuration changes alter the result
    configs_mod = [ShiftConfig(name="Test", start_hour=10, duration_hours=8)]
    shifts_run_3 = generate_shifts(configs_mod)
    
    assert shifts_run_1 != shifts_run_3

def test_existing_shift_consumer_compatibility():
    """15. Existing shift-consumer compatibility"""
    # The default configs must perfectly mimic the original hardcoded loops
    configs = get_default_shift_configs()
    shifts = generate_shifts(configs)
    
    assert len(shifts) == 1 + 24 + 24 # None + 24 Base + 24 OT1
    
    # Verify the break logic is identical
    base_shift_08 = next(s for s in shifts if s.name == "Base_Start_08")
    assert base_shift_08.hours == 8
    assert base_shift_08.overtime_hours == 0
    assert base_shift_08.duration_hours == 9
    
    # Break is offset 4, which is 8+4=12. So x[12] == 0
    assert base_shift_08.x[12] == 0
    assert base_shift_08.x[11] == 1
    assert base_shift_08.x[13] == 1
    assert sum(base_shift_08.x) == 8
    
    ot_shift_08 = next(s for s in shifts if s.name == "OT1_Start_08")
    assert ot_shift_08.hours == 8
    assert ot_shift_08.overtime_hours == 1
    assert ot_shift_08.duration_hours == 10
    
    assert ot_shift_08.x[12] == 0
    assert sum(ot_shift_08.x) == 9
