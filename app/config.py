import os
from dataclasses import dataclass

from dotenv import load_dotenv


load_dotenv()


def optional_env(name: str) -> str | None:
    value = os.getenv(name, "").strip()
    return value or None


def csv_env(name: str, default: str) -> tuple[str, ...]:
    return tuple(
        item.strip().lower()
        for item in os.getenv(name, default).split(",")
        if item.strip()
    )


@dataclass
class Settings:
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "DotasPlus")
    API_V1_PREFIX: str = os.getenv("API_V1_PREFIX", "/api/v1")

    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", "postgresql://dotas:dotas_dev_only@db:5432/dotas_core"
    )
    CELERY_BROKER_URL: str = os.getenv(
        "CELERY_BROKER_URL", "redis://redis:6379/0"
    )
    CELERY_RESULT_BACKEND: str = os.getenv(
        "CELERY_RESULT_BACKEND", "redis://redis:6379/0"
    )

    TELEGRAM_BOT_TOKEN: str | None = optional_env("TELEGRAM_BOT_TOKEN")
    TELEGRAM_CHAT_ID: str | None = optional_env("TELEGRAM_CHAT_ID")
    TOR_PROXY_URL: str | None = optional_env("TOR_PROXY_URL")
    SOURCE_HOST_ALLOWLIST: tuple[str, ...] = csv_env(
        "SOURCE_HOST_ALLOWLIST", "fixture,localhost,127.0.0.1"
    )


settings = Settings()
