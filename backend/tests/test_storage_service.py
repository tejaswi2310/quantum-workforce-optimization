import uuid
from pathlib import Path
from app.services.storage_service import StorageService
import pytest

def test_storage_service_initialization():
    run_id = uuid.uuid4()
    storage = StorageService(run_id)
    
    assert storage.run_id == run_id
    assert storage.get_run_dir().name == str(run_id)

def test_storage_service_ensure_dirs():
    run_id = uuid.uuid4()
    storage = StorageService(run_id)
    storage.ensure_run_dirs()
    
    assert storage.get_data_dir().exists()
    assert (storage.get_data_dir() / "raw").exists()
    assert (storage.get_data_dir() / "processed").exists()
    assert storage.get_results_dir().exists()

def test_storage_service_paths():
    run_id = uuid.uuid4()
    storage = StorageService(run_id)
    storage.ensure_run_dirs()
    
    # Valid paths
    data_file = storage.data_path("raw/test.csv")
    assert str(storage.get_data_dir()) in str(data_file)
    
    res_file = storage.result_path("test.csv")
    assert str(storage.get_results_dir()) in str(res_file)

def test_storage_service_path_traversal():
    run_id = uuid.uuid4()
    storage = StorageService(run_id)
    storage.ensure_run_dirs()
    
    # Invalid paths
    with pytest.raises(ValueError):
        storage.data_path("../test.csv")
        
    with pytest.raises(ValueError):
        storage.result_path("../../test.csv")
        
    with pytest.raises(ValueError):
        storage.data_path("/etc/passwd")

def test_get_latest_run_id():
    run_id = uuid.uuid4()
    storage = StorageService(run_id)
    storage.ensure_run_dirs()
    
    latest_id = StorageService.get_latest_run_id()
    assert latest_id is not None
    # We can't guarantee it's run_id if there are others but it should return a UUID.
    assert isinstance(latest_id, uuid.UUID)
