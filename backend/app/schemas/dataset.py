from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime

class DatasetResponse(BaseModel):
    id: str
    project_id: str
    filename: str
    row_count: int
    schema_definition: Optional[Dict[str, Any]]
    uploaded_at: datetime

    class Config:
        from_attributes = True
