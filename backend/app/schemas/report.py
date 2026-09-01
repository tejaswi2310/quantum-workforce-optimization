from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class ReportResponse(BaseModel):
    id: str
    project_id: str
    report_type: str
    file_path: str
    generated_at: datetime

    class Config:
        from_attributes = True

class GenerateReportRequest(BaseModel):
    report_type: str = "business_impact"
