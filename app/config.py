from pydantic import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "DOTAS++ Lite"
    API_V1_PREFIX: str = "/api/v1"

    DATABASE_URL: str = "postgresql://dotas:dotas_secret@db:5432/dotas_core"
    CELERY_BROKER_URL: str = "redis://redis:6379/0"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/0"

    TELEGRAM_BOT_TOKEN: str | None = None
    TELEGRAM_CHAT_ID: str | None = None

    class Config:
        env_file = ".env"


settings = Settings()
