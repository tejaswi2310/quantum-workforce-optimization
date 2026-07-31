from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class OptimizationRunResponse(BaseModel):
    id: str
    project_id: str
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
