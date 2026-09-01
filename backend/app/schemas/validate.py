from pydantic import BaseModel
from typing import Optional
import uuid

class QueueValidationResponse(BaseModel):
    id: uuid.UUID
    optimization_run_id: uuid.UUID
    hour: int
    calls: int
    agents: int
    sla_percent: float
    asa_seconds: float
    utilization_percent: float
    abandonment_percent: float
    pass_fail: str

    class Config:
        from_attributes = True

class ValidateRequest(BaseModel):
    optimization_run_id: uuid.UUID
