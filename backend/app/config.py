import os
from pathlib import Path
from pydantic_settings import BaseSettings

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DEFAULT_DB_PATH = PROJECT_ROOT / "workforce.db"
DEFAULT_DB_URL = f"sqlite:///{DEFAULT_DB_PATH}"

class Settings(BaseSettings):
    DATABASE_URL: str = DEFAULT_DB_URL
    SECRET_KEY: str = "super-secret-key-for-dev"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CELERY_BROKER_URL: str = f"sqla+{DEFAULT_DB_URL}"
    CELERY_RESULT_BACKEND: str = f"db+{DEFAULT_DB_URL}"
    RUNTIME_STORAGE_ROOT: str = "runtime/runs"
    DASHBOARD_DEMO_MODE: str = "default"

    class Config:
        env_file = ".env"

settings = Settings()
