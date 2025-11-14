"""Celery application configuration for background task processing."""

from __future__ import annotations

from celery import Celery

from backend.config import settings

# Create Celery app instance
celery_app = Celery(
    "cricksy_worker",
    broker=settings.REDIS_URL,
    backend=settings.REDIS_URL,
)

# Configure Celery
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=600,  # 10 minutes max per task
    task_soft_time_limit=540,  # Soft limit at 9 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
)

# Auto-discover tasks from worker module
celery_app.autodiscover_tasks(["backend.worker"])
