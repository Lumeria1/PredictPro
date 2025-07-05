import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # FastAPI
    APP_NAME: str = "PredictPro"
    APP_HOST: str = "0.0.0.0"
    APP_PORT: int = 8000

    # Database
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:pass@db:5432/football")

    # Celery
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/0")
    CELERY_RESULT_BACKEND: str = CELERY_BROKER_URL

    # API-Football
    API_FOOTBALL_KEY: str = os.getenv("API_FOOTBALL_KEY", "")
    API_FOOTBALL_BASE: str = "https://v3.football.api-sports.io/"

    class Config:
        env_file = ".env"

settings = Settings()