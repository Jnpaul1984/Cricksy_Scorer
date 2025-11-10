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

    # Feature flags for upload/OCR functionality
    ENABLE_UPLOADS: bool = os.getenv("CRICKSY_ENABLE_UPLOADS", "0") == "1"
    ENABLE_OCR: bool = os.getenv("CRICKSY_ENABLE_OCR", "0") == "1"

    # S3 / Object Storage (for uploads)
    S3_BUCKET: str = os.getenv("CRICKSY_S3_BUCKET", "cricksy-uploads")
    S3_REGION: str = os.getenv("CRICKSY_S3_REGION", "us-east-1")
    S3_ACCESS_KEY: str = os.getenv("CRICKSY_S3_ACCESS_KEY", "")
    S3_SECRET_KEY: str = os.getenv("CRICKSY_S3_SECRET_KEY", "")
    S3_ENDPOINT_URL: str | None = os.getenv("CRICKSY_S3_ENDPOINT_URL")  # for MinIO or local testing
    PRESIGNED_URL_EXPIRATION: int = int(os.getenv("CRICKSY_PRESIGNED_URL_EXPIRATION", "3600"))

    # Redis (for Celery/RQ and WebSocket adapter)
    REDIS_URL: str = os.getenv("CRICKSY_REDIS_URL", "redis://localhost:6379/0")
    
    # WebSocket Redis adapter (for scaling Socket.IO)
    ENABLE_REDIS_ADAPTER: bool = os.getenv("CRICKSY_ENABLE_REDIS_ADAPTER", "0") == "1"


settings = Settings()
