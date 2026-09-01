import os
import uuid
from pathlib import Path
from app.config import settings

class StorageService:
    def __init__(self, run_id: uuid.UUID = None):
        if not run_id:
            self.run_id = uuid.uuid4()
        else:
            self.run_id = run_id
            
        # Get the storage root. It must be an absolute path or relative to the repository root.
        # Since this file is in backend/app/services, the repository root is 4 levels up.
        # We define ROOT_DIR to be the absolute path to the repository root.
        self.root_dir = Path(__file__).resolve().parent.parent.parent.parent
        self.storage_root = self.root_dir / settings.RUNTIME_STORAGE_ROOT
        self.run_dir = self.storage_root / str(self.run_id)
        
    @classmethod
    def create_run(cls) -> "StorageService":
        """Helper to create a new isolated run."""
        return cls(uuid.uuid4())
    @classmethod
    def get_latest_run_id(cls) -> uuid.UUID:
        root_dir = Path(__file__).resolve().parent.parent.parent.parent
        runs_dir = root_dir / settings.RUNTIME_STORAGE_ROOT
        if runs_dir.exists():
            runs = [d for d in runs_dir.iterdir() if d.is_dir()]
            if runs:
                runs.sort(key=lambda x: x.stat().st_mtime, reverse=True)
                return uuid.UUID(runs[0].name)
        return None
        
    def get_run_dir(self) -> Path:
        return self.run_dir
        
    def get_data_dir(self) -> Path:
        return self.run_dir / "data"
        
    def get_results_dir(self) -> Path:
        return self.run_dir / "results"
        
    def get_reports_dir(self) -> Path:
        return self.run_dir / "reports"
        
    def ensure_run_dirs(self):
        """Ensures existence of data/ and results/ folders for this run."""
        self.get_data_dir().mkdir(parents=True, exist_ok=True)
        # We'll use data/raw and data/processed as per the previous layout convention
        (self.get_data_dir() / "raw").mkdir(parents=True, exist_ok=True)
        (self.get_data_dir() / "processed").mkdir(parents=True, exist_ok=True)
        self.get_results_dir().mkdir(parents=True, exist_ok=True)
        self.get_reports_dir().mkdir(parents=True, exist_ok=True)
        
    def _safe_path(self, base_dir: Path, filename: str) -> Path:
        """Safely joins a filename to a base directory, rejecting path traversal."""
        # Convert filename to Path and prevent absolute paths
        file_path = Path(filename)
        if file_path.is_absolute():
            raise ValueError(f"Filename must be relative: {filename}")
            
        # Join with base directory and resolve
        resolved_path = (base_dir / file_path).resolve()
        
        # Check that the resolved path is within the base directory
        if not str(resolved_path).startswith(str(base_dir.resolve())):
            raise ValueError(f"Path traversal detected: {filename}")
            
        return resolved_path

    def data_path(self, filename: str) -> Path:
        """Resolves to the run's data folder, enforcing path traversal prevention."""
        return self._safe_path(self.get_data_dir(), filename)

    def result_path(self, filename: str) -> Path:
        """Resolves to the run's results folder, enforcing path traversal prevention."""
        return self._safe_path(self.get_results_dir(), filename)
        
    def report_path(self, filename: str) -> Path:
        """Resolves to the run's reports folder, enforcing path traversal prevention."""
        return self._safe_path(self.get_reports_dir(), filename)
