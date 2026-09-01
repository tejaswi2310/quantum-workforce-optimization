import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from sqlalchemy.orm import Session
from typing import List
import pandas as pd
import uuid

from app.models.database import get_db
from app.models.models import Dataset, Project, User
from app.schemas.dataset import DatasetResponse
from app.dependencies import get_current_active_user
from app.config import settings

router = APIRouter(prefix="/api/v1/projects/{project_id}/datasets", tags=["datasets"])

from app.services.storage_service import StorageService

@router.post("/upload", response_model=DatasetResponse)
async def upload_dataset(
    project_id: uuid.UUID,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    if not file.filename.endswith('.csv'):
        raise HTTPException(status_code=415, detail="Only CSV files are supported")

    # Create dataset record first to get a UUID
    dataset = Dataset(
        project_id=project.id,
        filename=file.filename,
        file_path="",  # will update after saving
        row_count=0,
        schema_definition={}
    )
    db.add(dataset)
    db.commit()
    db.refresh(dataset)

    safe_filename = f"{dataset.id}_{uuid.uuid4()}.csv"
    # Isolate dataset upload using its own UUID
    storage = StorageService(dataset.id)
    storage.ensure_run_dirs()
    
    file_path = str(storage.data_path(f"raw/{safe_filename}"))
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        df = pd.read_csv(file_path)
        if df.empty:
            raise ValueError("CSV file is empty")
        
        required_cols = {'date', 'hour', 'day_of_week', 'channel', 'skill_group', 'calls_received'}
        missing_cols = required_cols - set(df.columns)
        if missing_cols:
            raise ValueError(f"Missing required columns: {', '.join(missing_cols)}")
            
        row_count = len(df)
        schema_def = df.dtypes.astype(str).to_dict()
    except pd.errors.EmptyDataError:
        os.remove(file_path)
        db.delete(dataset)
        db.commit()
        raise HTTPException(status_code=400, detail="CSV file is empty")
    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        db.delete(dataset)
        db.commit()
        raise HTTPException(status_code=400, detail=f"Error processing CSV: {str(e)}")

    dataset.file_path = file_path
    dataset.row_count = row_count
    dataset.schema_definition = schema_def
    db.commit()
    db.refresh(dataset)
    return dataset

@router.get("/", response_model=List[DatasetResponse])
def get_datasets(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    project = db.query(Project).filter(Project.id == project_id, Project.user_id == current_user.id).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    
    return db.query(Dataset).filter(Dataset.project_id == project_id).all()
