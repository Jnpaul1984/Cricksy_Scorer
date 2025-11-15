"""Worker module for background task processing."""
from backend.worker.celery_app import app

__all__ = ["app"]
