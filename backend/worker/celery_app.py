"""Celery application configuration for async task processing."""

from __future__ import annotations

from celery import Celery

from backend.config import settings

# Create Celery app
celery_app = Celery(
    "cricksy_worker",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=270,  # Soft limit at 4.5 minutes
    worker_prefetch_multiplier=1,  # Process one task at a time
    worker_max_tasks_per_child=100,  # Restart worker after 100 tasks
)

# Auto-discover tasks from worker.processor module
celery_app.autodiscover_tasks(["backend.worker"], related_name="processor")

__all__ = ["celery_app"]
