from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "postgresql://user:pass@postgres:5432/workforce"
    CELERY_BROKER_URL: str = "sqla+postgresql://user:pass@postgres:5432/workforce"
    CELERY_RESULT_BACKEND: str = "db+postgresql://user:pass@postgres:5432/workforce"

    class Config:
        env_file = ".env"

settings = Settings()
