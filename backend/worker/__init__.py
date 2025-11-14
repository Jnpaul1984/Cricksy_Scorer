"""Worker __init__ to expose celery app."""
from __future__ import annotations

from .celery_app import app as celery_app

__all__ = ["celery_app"]
