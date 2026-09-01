from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./workforce.db"
    SECRET_KEY: str = "super-secret-key-for-dev"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 15
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    CELERY_BROKER_URL: str = "sqla+sqlite:///./workforce.db"
    CELERY_RESULT_BACKEND: str = "db+sqlite:///./workforce.db"

    class Config:
        env_file = ".env"

settings = Settings()
