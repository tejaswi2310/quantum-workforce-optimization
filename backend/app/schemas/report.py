from pydantic import BaseModel
from typing import Optional
from datetime import datetime
import uuid

class ReportResponse(BaseModel):
    id: uuid.UUID
    project_id: uuid.UUID
    report_type: str
    file_path: str
    generated_at: datetime

    class Config:
        from_attributes = True

class GenerateReportRequest(BaseModel):
    report_type: str = "business_impact"
