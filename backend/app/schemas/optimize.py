from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class OptimizationRunResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    run_type: str
    parameters: Optional[Dict[str, Any]]
    results: Optional[Dict[str, Any]]
    status: str
    completed_at: Optional[datetime]
    created_at: datetime

    class Config:
        from_attributes = True

class OptimizationRequest(BaseModel):
    parameters: Optional[Dict[str, Any]] = None
