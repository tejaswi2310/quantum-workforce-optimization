from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime
from uuid import UUID

class DatasetResponse(BaseModel):
    id: UUID
    project_id: UUID
    filename: str
    row_count: int
    schema_definition: Optional[Dict[str, Any]]
    uploaded_at: datetime

    class Config:
        from_attributes = True
