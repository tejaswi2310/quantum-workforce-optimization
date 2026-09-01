from pydantic import BaseModel, ConfigDict
from typing import Optional, Dict, Any
from datetime import datetime
import uuid

class ForecastResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    model_path: Optional[str]
    metrics: Optional[Dict[str, float]]
    feature_importance: Optional[Dict[str, float]]
    status: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True, protected_namespaces=())

class PredictRequest(BaseModel):
    days: int = 7
