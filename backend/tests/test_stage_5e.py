import os
import uuid
import time
import pandas as pd
import pytest
import threading
from pathlib import Path
from app.services.storage_service import StorageService
from app.routers.dashboard import _load_queue_results_cached

def test_f01_atomic_temp_files_concurrency(tmp_path):
    storage = StorageService()
    storage.storage_root = tmp_path
    storage.run_dir = tmp_path / str(storage.run_id)
    storage.ensure_run_dirs()

    df = pd.DataFrame({"col1": [1, 2, 3]})
    filepath = storage.result_path("concurrent_test.csv")

    errors = []
    
    def writer():
        try:
            for _ in range(10):
                storage.atomic_write_csv(df, filepath)
        except Exception as e:
            errors.append(e)

    threads = [threading.Thread(target=writer) for _ in range(5)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert len(errors) == 0, f"Concurrency errors: {errors}"
    assert filepath.exists()
    
    tmp_files = list(filepath.parent.glob("*.tmp"))
    assert len(tmp_files) == 0

def test_f05_whatif_cache_invalidation(tmp_path):
    csv_path = tmp_path / "queue_validation_results.csv"
    
    df1 = pd.DataFrame({"hour": [0], "calls": [10], "required_agents": [1], "sla_percent": [80.0]})
    df1.to_csv(csv_path, index=False)
    
    mtime1 = os.path.getmtime(csv_path)
    res1 = _load_queue_results_cached(str(csv_path), mtime1)
    
    assert res1["calls"].iloc[0] == 10
    
    time.sleep(0.01)
    
    df2 = pd.DataFrame({"hour": [0], "calls": [20], "required_agents": [2], "sla_percent": [90.0]})
    df2.to_csv(csv_path, index=False)
    
    mtime2 = os.path.getmtime(csv_path)
    if mtime2 == mtime1:
        mtime2 += 1.0 
        
    res2 = _load_queue_results_cached(str(csv_path), mtime2)
    assert res2["calls"].iloc[0] == 20
