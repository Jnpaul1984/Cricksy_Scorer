"""Celery application configuration for async workers."""
from __future__ import annotations

from celery import Celery

from backend.config import settings

# Create Celery app
app = Celery(
    "cricksy_scorer",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
)

# Configure Celery
app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,  # 5 minutes max per task
    task_soft_time_limit=240,  # 4 minutes soft limit
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=100,
)

# Auto-discover tasks in worker module
app.autodiscover_tasks(["backend.worker"])

if __name__ == "__main__":
    app.start()
