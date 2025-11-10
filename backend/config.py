from __future__ import annotations

import os
from pathlib import Path


def _csv_list(env_val: str | None) -> list[str]:
    return [s.strip() for s in (env_val or "").split(",") if s.strip()]


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

    # Feature Flags
    ENABLE_UPLOADS: bool = os.getenv("CRICKSY_ENABLE_UPLOADS", "1" if os.getenv("CRICKSY_ENV") != "production" else "0") == "1"
    ENABLE_OCR: bool = os.getenv("CRICKSY_ENABLE_OCR", "1" if os.getenv("CRICKSY_ENV") != "production" else "0") == "1"

    # S3/MinIO Configuration
    S3_ENDPOINT: str | None = os.getenv("CRICKSY_S3_ENDPOINT")  # For MinIO dev: http://localhost:9000
    S3_REGION: str = os.getenv("CRICKSY_S3_REGION", "us-east-1")
    S3_BUCKET: str = os.getenv("CRICKSY_S3_BUCKET", "cricksy-uploads-dev")
    S3_ACCESS_KEY: str = os.getenv("CRICKSY_S3_ACCESS_KEY", "")  # Must be set via env
    S3_SECRET_KEY: str = os.getenv("CRICKSY_S3_SECRET_KEY", "")  # Must be set via env
    USE_MINIO: bool = bool(S3_ENDPOINT)  # Auto-detect MinIO if endpoint is set

    # Celery/Redis Configuration
    REDIS_URL: str = os.getenv("CRICKSY_REDIS_URL", "redis://localhost:6379/0")
    CELERY_BROKER_URL: str = os.getenv("CRICKSY_CELERY_BROKER_URL", REDIS_URL)
    CELERY_RESULT_BACKEND: str = os.getenv("CRICKSY_CELERY_RESULT_BACKEND", REDIS_URL)

    # WebSocket Configuration
    USE_REDIS_ADAPTER: bool = os.getenv("CRICKSY_USE_REDIS_ADAPTER", "0") == "1"
    SOCKET_REDIS_URL: str = os.getenv("CRICKSY_SOCKET_REDIS_URL", REDIS_URL)


settings = Settings()
