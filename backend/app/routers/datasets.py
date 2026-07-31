import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import pandas as pd

from app.models.database import get_db
from app.models.models import Dataset, Project, User
from app.schemas.dataset import DatasetResponse
from app.dependencies import get_current_active_user
from app.config import settings

router = APIRouter(prefix="/api/v1/projects/{project_id}/datasets", tags=["datasets"])

UPLOAD_DIR = "uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload", response_model=DatasetResponse)
async def upload_dataset(
    project_id: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=415, detail="Only CSV files are supported")

    file_path = os.path.join(UPLOAD_DIR, f"{project_id}_{file.filename}")
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        df = pd.read_csv(file_path)
        row_count = len(df)
        schema_def = df.dtypes.astype(str).to_dict()
    except Exception as e:
        os.remove(file_path)
        raise HTTPException(status_code=400, detail=f"Error reading CSV: {str(e)}")

    dataset = Dataset(
        project_id=project.id,
        filename=file.filename,
        file_path=file_path,
        row_count=row_count,
        schema_definition=schema_def
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)
    return dataset

@router.get("/", response_model=List[DatasetResponse])
def get_datasets(
    project_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return db.query(Dataset).filter(Dataset.project_id == project_id).all()
