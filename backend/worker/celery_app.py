"""Celery application for async OCR processing.

This module initializes the Celery app for processing uploaded scorecard images.
"""

from __future__ import annotations

from celery import Celery

from backend.config import settings

# Initialize Celery app
app = Celery(
    "cricksy_worker",
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
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    task_routes={
        "backend.worker.processor.process_upload_task": {"queue": "ocr"},
    },
)

# Auto-discover tasks
app.autodiscover_tasks(["backend.worker"])

if __name__ == "__main__":
    app.start()
