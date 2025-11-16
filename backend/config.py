from __future__ import annotations

from pathlib import Path

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

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


class Settings(BaseSettings):
    """Runtime configuration sourced from environment/Secrets Manager."""

    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    API_TITLE: str = Field(default="Cricksy Scorer API", alias="CRICKSY_API_TITLE")
    DATABASE_URL: str = Field(..., alias="DATABASE_URL")
    APP_SECRET_KEY: str = Field(..., alias="APP_SECRET_KEY")
    BACKEND_CORS_ORIGINS: str = Field(
        default=",".join(_DEFAULT_CORS),
        alias="BACKEND_CORS_ORIGINS",
    )
    IN_MEMORY_DB: bool = Field(default=False, alias="CRICKSY_IN_MEMORY_DB")
    STATIC_ROOT: Path = Field(default=_ROOT / "static", alias="CRICKSY_STATIC_ROOT")
    SPONSORS_DIR: Path = Field(default=_ROOT / "static" / "sponsors", alias="CRICKSY_SPONSORS_DIR")
    SIO_CORS_ALLOWED_ORIGINS: str | list[str] = Field(
        default="*",
        alias="CRICKSY_SIO_CORS_ORIGINS",
    )
    LOG_LEVEL: str = Field(default="INFO", alias="CRICKSY_LOG_LEVEL")

    @field_validator("STATIC_ROOT", mode="before")
    @classmethod
    def _resolve_static_root(cls, value: Path | str | None) -> Path:
        if isinstance(value, Path):
            return value
        if value is None:
            return _ROOT / "static"
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return _ROOT / "static"
            return Path(stripped)
        return Path(value)

    @field_validator("SPONSORS_DIR", mode="before")
    @classmethod
    def _resolve_sponsors_dir(cls, value: Path | str | None) -> Path:
        if isinstance(value, Path):
            return value
        if value is None:
            return _ROOT / "static" / "sponsors"
        if isinstance(value, str):
            stripped = value.strip()
            if not stripped:
                return _ROOT / "static" / "sponsors"
            return Path(stripped)
        return Path(value)

    @property
    def database_url(self) -> str:
        return self.DATABASE_URL

    @property
    def app_secret_key(self) -> str:
        return self.APP_SECRET_KEY

    @property
    def backend_cors_origins(self) -> str:
        return self.BACKEND_CORS_ORIGINS

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
