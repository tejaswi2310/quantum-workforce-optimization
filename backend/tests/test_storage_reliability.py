import pytest
import uuid
import os
import shutil
import concurrent.futures
from pathlib import Path
from app.services.storage_service import StorageService

def test_run_directory_creation():
    run_id = uuid.uuid4()
    storage = StorageService(run_id)
    storage.ensure_run_dirs()
    assert storage.get_data_dir().exists()
    assert storage.get_results_dir().exists()
    assert storage.get_reports_dir().exists()

def test_idempotent_directory_creation():
    run_id = uuid.uuid4()
    storage = StorageService(run_id)
    # Call multiple times
    for _ in range(5):
        storage.ensure_run_dirs()
    assert storage.get_data_dir().exists()

def test_run_isolation():
    run_1 = uuid.uuid4()
    run_2 = uuid.uuid4()
    storage1 = StorageService(run_1)
    storage2 = StorageService(run_2)
    
    assert storage1.get_run_dir() != storage2.get_run_dir()
    
    file1 = storage1.data_path("test.txt")
    file2 = storage2.data_path("test.txt")
    
    file1.write_text("Run 1 data")
    file2.write_text("Run 2 data")
    
    assert file1.read_text() == "Run 1 data"
    assert file2.read_text() == "Run 2 data"

def test_sequential_lifecycle():
    run_1 = uuid.uuid4()
    storage1 = StorageService(run_1)
    storage1.ensure_run_dirs()
    f1 = storage1.result_path("test.csv")
    f1.write_text("data")
    assert f1.exists()
    
    # Cleanup Run 1 (Simulated)
    if storage1.get_run_dir().exists():
        shutil.rmtree(storage1.get_run_dir())
        
    run_2 = uuid.uuid4()
    storage2 = StorageService(run_2)
    storage2.ensure_run_dirs()
    f2 = storage2.result_path("test.csv")
    f2.write_text("data")
    assert f2.exists()

def execute_storage_lifecycle(run_id):
    storage = StorageService(run_id)
    storage.ensure_run_dirs()
    f = storage.result_path("test.csv")
    f.write_text(str(run_id))
    return f.read_text() == str(run_id)

def test_concurrent_lifecycle():
    run_ids = [uuid.uuid4() for _ in range(10)]
    with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
        results = list(executor.map(execute_storage_lifecycle, run_ids))
    assert all(results)

def test_previously_observed_failure_race_condition():
    """
    Simulates the FileNotFoundError where the parent directory
    might be missing (e.g. from rapid teardowns or if ensure_run_dirs was bypassed or incomplete).
    If _safe_path correctly enforces parent directory existence, this will pass.
    """
    run_id = uuid.uuid4()
    storage = StorageService(run_id)
    
    # We purposely do NOT call ensure_run_dirs()
    # Or we imagine another process deleted it:
    if storage.get_run_dir().exists():
        shutil.rmtree(storage.get_run_dir())
        
    # Attempt to write an artifact.
    # Without the fix in _safe_path, result_path() would return a Path
    # whose parent (results/) does NOT exist, leading to FileNotFoundError on write.
    # With the fix, result_path() forces the parent directory to exist just in time.
    
    out_file = storage.result_path("erlang_requirement_validation.csv")
    
    try:
        out_file.write_text("test,csv,data\n1,2,3")
        assert out_file.exists()
    except FileNotFoundError as e:
        pytest.fail(f"Race condition reproduced: Directory was missing at write time! {e}")
