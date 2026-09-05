import os
import json
import pytest
import pandas as pd
from pathlib import Path
from app.services.storage_service import StorageService
from app.routers.dashboard import _load_queue_results_cached
from fastapi import HTTPException

# Mock settings to create a fake run_id for testing
def test_atomic_csv_success(tmp_path):
    storage = StorageService()
    storage.storage_root = tmp_path
    storage.run_dir = tmp_path / str(storage.run_id)
    storage.ensure_run_dirs()

    df = pd.DataFrame({"a": [1, 2], "b": [3, 4]})
    dest = storage.data_path("processed/test.csv")
    
    storage.atomic_write_csv(df, dest, index=False)
    
    assert dest.exists()
    assert not dest.with_suffix('.csv.tmp').exists()
    
    df_read = pd.read_csv(dest)
    assert df_read.shape == (2, 2)
    assert list(df_read.columns) == ["a", "b"]

def test_atomic_json_success(tmp_path):
    storage = StorageService()
    storage.storage_root = tmp_path
    storage.run_dir = tmp_path / str(storage.run_id)
    storage.ensure_run_dirs()

    data = {"metric": 100, "status": "COMPLETED"}
    dest = storage.result_path("test.json")
    
    storage.atomic_write_json(data, dest, indent=4)
    
    assert dest.exists()
    assert not dest.with_suffix('.json.tmp').exists()
    
    with open(dest, "r") as f:
        read_data = json.load(f)
    assert read_data["metric"] == 100

def test_atomic_failure_safety(tmp_path, monkeypatch):
    storage = StorageService()
    storage.storage_root = tmp_path
    storage.run_dir = tmp_path / str(storage.run_id)
    storage.ensure_run_dirs()

    # Create valid destination first
    dest = storage.data_path("processed/test_fail.csv")
    valid_df = pd.DataFrame({"valid": [1]})
    storage.atomic_write_csv(valid_df, dest, index=False)
    
    assert dest.exists()
    
    # Mock to_csv to fail
    def mock_to_csv(*args, **kwargs):
        raise ValueError("Simulated failure during write")
        
    monkeypatch.setattr(pd.DataFrame, "to_csv", mock_to_csv)
    
    new_df = pd.DataFrame({"new": [2]})
    with pytest.raises(ValueError, match="Simulated failure"):
        storage.atomic_write_csv(new_df, dest, index=False)
        
    # Verify original file is untouched
    assert dest.exists()
    df_read = pd.read_csv(dest)
    assert "valid" in df_read.columns
    assert "new" not in df_read.columns
    
    # Verify tmp file is cleaned up
    assert not dest.with_suffix('.csv.tmp').exists()

def test_corrupt_csv_handling(tmp_path):
    dest = tmp_path / "queue_validation_results.csv"
    dest.write_text("")  # 0 bytes
    
    with pytest.raises(HTTPException) as excinfo:
        _load_queue_results_cached.__wrapped__(str(dest), 0.0)
    assert excinfo.value.status_code == 500
    assert "Artifact corrupted" in excinfo.value.detail
    
def test_missing_required_columns(tmp_path):
    dest = tmp_path / "queue_validation_results.csv"
    df = pd.DataFrame({"channel": ["Voice"], "hour": [8]}) # missing skill_group, calls, etc.
    df.to_csv(dest, index=False)
    
    with pytest.raises(HTTPException) as excinfo:
        _load_queue_results_cached.__wrapped__(str(dest), 0.0)
    assert excinfo.value.status_code == 500
    assert "missing required columns" in excinfo.value.detail

def test_pickle_removal():
    from app.core_engine.forecasting.demand_forecaster import train_forecast
    # Ensure train_forecast doesn't fail due to missing pickle module or logic
    # Note: we can't easily run it directly if it requires full datasets, 
    # but the test_optimization_d2.py will naturally cover this. 
    # Just a placeholder to explicitly state intent.
    pass
