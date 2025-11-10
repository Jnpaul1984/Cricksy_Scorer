from __future__ import annotations

import os
from pathlib import Path


def _csv_list(env_val: str | None) -> list[str]:
    return [s.strip() for s in (env_val or "").split(",") if s.strip()]


def _bool_env(env_key: str, default: str = "0") -> bool:
    """Parse boolean environment variable."""
    return os.getenv(env_key, default).lower() in ("1", "true", "yes", "on")


# Resolve relative to backend/ directory
_ROOT = Path(__file__).resolve().parent

_DEFAULT_CORS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:4173",
    "http://127.0.0.1:4173",
]


class Settings:
    # API
    API_TITLE: str = os.getenv("CRICKSY_API_TITLE", "Cricksy Scorer API")

    # CORS
    CORS_ORIGINS: list[str] = _csv_list(os.getenv("CRICKSY_CORS_ORIGINS")) or _DEFAULT_CORS

    # DB mode
    IN_MEMORY_DB: bool = os.getenv("CRICKSY_IN_MEMORY_DB", "0") == "1"

    # Static paths
    STATIC_ROOT: Path = Path(os.getenv("CRICKSY_STATIC_ROOT") or (_ROOT / "static"))
    SPONSORS_DIR: Path = Path(os.getenv("CRICKSY_SPONSORS_DIR") or (STATIC_ROOT / "sponsors"))

    # Socket.IO
    SIO_CORS_ALLOWED_ORIGINS: str | list[str] = os.getenv("CRICKSY_SIO_CORS_ORIGINS", "*")

    # Logging
    LOG_LEVEL: str = os.getenv("CRICKSY_LOG_LEVEL", "INFO")

    # Feature Flags (default enabled in development)
    ENABLE_UPLOADS: bool = _bool_env("ENABLE_UPLOADS", "1")
    ENABLE_OCR: bool = _bool_env("ENABLE_OCR", "1")

    # Upload Settings
    S3_UPLOAD_BUCKET: str = os.getenv("S3_UPLOAD_BUCKET", "cricksy-uploads")
    MAX_UPLOAD_SIZE_MB: int = int(os.getenv("MAX_UPLOAD_SIZE_MB", "10"))

    # Worker Settings (Celery + Redis)
    CELERY_BROKER_URL: str = os.getenv("CELERY_BROKER_URL", "redis://localhost:6379/0")
    CELERY_RESULT_BACKEND: str = os.getenv("CELERY_RESULT_BACKEND", "redis://localhost:6379/0")

    # Redis for Socket.IO adapter
    REDIS_URL: str = os.getenv("REDIS_URL", "redis://localhost:6379/1")


settings = Settings()
