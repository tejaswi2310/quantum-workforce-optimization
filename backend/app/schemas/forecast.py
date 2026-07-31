from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class ForecastResponse(BaseModel):
    id: str
    project_id: str
    model_path: Optional[str]
    metrics: Optional[Dict[str, float]]
    feature_importance: Optional[Dict[str, float]]
    status: str
    created_at: datetime

    class Config:
        from_attributes = True

class PredictRequest(BaseModel):
    days: int = 7
