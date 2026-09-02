from pydantic import BaseModel, Field, field_validator, ValidationInfo
from typing import List, Literal
import re

class RosterAgent(BaseModel):
    agent_id: str = Field(..., min_length=1)
    skills: str = Field(..., min_length=1)
    wage: float = Field(..., gt=0)
    contract_type: Literal["FT", "PT"]
    max_weekly_hours: int = Field(..., gt=0)
    preferred_shift: Literal["morning", "afternoon", "evening", "flexible"]
    availability: str

    @field_validator("availability")
    @classmethod
    def validate_availability(cls, v):
        if len(v) != 168:
            raise ValueError("Availability must be exactly 168 characters long.")
        if not re.match(r"^[01]{168}$", v):
            raise ValueError("Availability must contain only 0s and 1s.")
        return v

    @field_validator("max_weekly_hours")
    @classmethod
    def validate_max_weekly_hours(cls, v: int, info: ValidationInfo):
        contract = info.data.get("contract_type")
        if contract == "FT" and v < 35:
            raise ValueError("FT agents should typically have 35+ max weekly hours.")
        if contract == "PT" and v >= 35:
            raise ValueError("PT agents should typically have < 35 max weekly hours.")
        return v
