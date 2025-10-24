from __future__ import annotations

import os
from pathlib import Path
from typing import List, Union


def _csv_list(env_val: str | None) -> List[str]:
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
    CORS_ORIGINS: List[str] = _csv_list(os.getenv("CRICKSY_CORS_ORIGINS")) or _DEFAULT_CORS

    # DB mode
    IN_MEMORY_DB: bool = os.getenv("CRICKSY_IN_MEMORY_DB", "0") == "1"

    # Static paths
    STATIC_ROOT: Path = Path(os.getenv("CRICKSY_STATIC_ROOT") or (_ROOT / "static"))
    SPONSORS_DIR: Path = Path(os.getenv("CRICKSY_SPONSORS_DIR") or (STATIC_ROOT / "sponsors"))

    # Socket.IO
    SIO_CORS_ALLOWED_ORIGINS: Union[str, List[str]] = os.getenv("CRICKSY_SIO_CORS_ORIGINS", "*")

    # Logging
    LOG_LEVEL: str = os.getenv("CRICKSY_LOG_LEVEL", "INFO")


settings = Settings()


