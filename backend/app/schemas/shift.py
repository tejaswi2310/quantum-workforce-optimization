from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import List, Optional
import hashlib
import json

class ShiftConfig(BaseModel):
    """
    Configuration for a shift definition.
    """
    name: str = Field(..., min_length=1)
    start_hour: int = Field(..., ge=0, le=23)
    duration_hours: int = Field(..., gt=0, le=24)
    break_hour_offset: int = Field(default=-1)
    is_overtime: bool = Field(default=False)

    @property
    def end_hour(self) -> int:
        return (self.start_hour + self.duration_hours) % 24

    @property
    def shift_id(self) -> str:
        # Deterministic stable ID based on configuration
        config_str = f"{self.name}_{self.start_hour}_{self.duration_hours}_{self.break_hour_offset}_{self.is_overtime}"
        return hashlib.md5(config_str.encode('utf-8')).hexdigest()[:10]
        
    def generate_binary_array(self) -> List[int]:
        """Generates a 24-hour binary coverage array for 24-hour planning compatibility."""
        x = [0] * 24
        for offset in range(self.duration_hours):
            if offset != self.break_hour_offset:
                x[(self.start_hour + offset) % 24] = 1
        return x

class ShiftTemplate(BaseModel):
    """
    Generated deterministic shift template ready for downstream consumption (CP-SAT).
    """
    shift_id: str
    name: str
    start_hour: int
    end_hour: int
    duration_hours: int
    x: List[int]
    hours: int
    overtime_hours: int

def generate_shifts(configs: List[ShiftConfig]) -> List[ShiftTemplate]:
    """
    Generates deterministic shift templates from configurations.
    Enforces stable ordering by start_hour, then duration.
    """
    shifts = []
    
    # 0. Always include a 'None' shift for CP-SAT compatibility where agents don't work
    # We use a deterministic empty shift
    none_shift = ShiftTemplate(
        shift_id="none_00000",
        name="None",
        start_hour=0,
        end_hour=0,
        duration_hours=0,
        x=[0]*24,
        hours=0,
        overtime_hours=0
    )
    shifts.append(none_shift)
    
    # Generate requested configurations
    for config in configs:
        x_array = config.generate_binary_array()
        
        # Calculate payable hours (excluding break)
        # If break_hour_offset is within duration, subtract 1
        payable_hours = config.duration_hours
        if 0 <= config.break_hour_offset < config.duration_hours:
            payable_hours -= 1
            
        # In the existing classical setup, an OT shift implies 8 base hours + N overtime hours.
        # We preserve this exact logic: if it's an OT shift with e.g. 9 payable hours, it means 8 base + 1 OT.
        if config.is_overtime:
            base_hours = 8
            overtime = payable_hours - 8 if payable_hours > 8 else 0
        else:
            base_hours = payable_hours
            overtime = 0
        
        template = ShiftTemplate(
            shift_id=config.shift_id,
            name=config.name,
            start_hour=config.start_hour,
            end_hour=config.end_hour,
            duration_hours=config.duration_hours,
            x=x_array,
            hours=base_hours,
            overtime_hours=overtime
        )
        shifts.append(template)
        
    # Remove duplicates preserving order
    seen = set()
    unique_shifts = []
    for s in shifts:
        if s.shift_id not in seen:
            seen.add(s.shift_id)
            unique_shifts.append(s)
            
    # Deterministic sorting: None is always first. 
    # Others sorted by start_hour, then duration_hours, then name.
    active_shifts = sorted(unique_shifts[1:], key=lambda s: (s.start_hour, s.duration_hours, s.name))
    
    return [unique_shifts[0]] + active_shifts

def get_default_shift_configs() -> List[ShiftConfig]:
    """
    Returns the standard default set of shifts ensuring backward compatibility
    with existing classical_optimizer.py behavior.
    """
    configs = []
    for start_h in range(24):
        # Base shift: 9 hrs total (8 hrs work + 1 hr break at offset 4)
        configs.append(ShiftConfig(
            name=f"Base_Start_{start_h:02d}",
            start_hour=start_h,
            duration_hours=9,
            break_hour_offset=4,
            is_overtime=False
        ))
        # OT shift: 10 hrs total (9 hrs work + 1 hr break at offset 4)
        configs.append(ShiftConfig(
            name=f"OT1_Start_{start_h:02d}",
            start_hour=start_h,
            duration_hours=10,
            break_hour_offset=4,
            is_overtime=True
        ))
    return configs
