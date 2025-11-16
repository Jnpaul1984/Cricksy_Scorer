from __future__ import annotations

import logging
import sys
import time
from typing import Any

import structlog


def configure_logging(json: bool = True, level: int = logging.INFO) -> None:
    """
    Configure structlog + stdlib logging.

    - JSON logs by default (set json=False for pretty console in dev).
    - Merges contextvars (e.g., request_id) into each log record.
    - Bridges stdlib loggers (uvicorn, sqlalchemy, etc.) to emit message-only, so
      structlog controls rendering.
    - Adds instrumentation processors for metrics and tracing.
    """
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
        add_instrumentation_context,  # NEW: Add custom instrumentation
    ]

    renderer = (
        structlog.processors.JSONRenderer()
        if json
        else structlog.dev.ConsoleRenderer(colors=True)
    )

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            renderer,
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Stdlib root logger -> message-only; structlog handles formatting.
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter("%(message)s"))

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)

    # Tame noisy loggers.
    logging.getLogger("uvicorn.error").setLevel(level)
    # Suppress uvicorn's default access logs (we emit our own structured access logs).
    logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
    logging.getLogger("sqlalchemy.engine.Engine").setLevel(logging.WARNING)


def add_instrumentation_context(
    logger: Any, method_name: str, event_dict: dict[str, Any]
) -> dict[str, Any]:
    """
    Add instrumentation context to log events.

    This processor adds:
    - Process/thread information
    - Performance metrics (if available)
    - Custom tags for filtering

    Can be extended to add distributed tracing context (e.g., OpenTelemetry).
    """
    # Add service identification
    event_dict["service"] = "cricksy-scorer"

    # Add performance context if available
    if "duration_ms" not in event_dict and hasattr(logger, "_context"):
        ctx = logger._context
        if "start_time" in ctx:
            duration_ms = (time.time() - ctx["start_time"]) * 1000
            event_dict["duration_ms"] = round(duration_ms, 2)

    # Add component tag based on logger name
    logger_name = event_dict.get("logger", "")
    if "socket" in logger_name.lower():
        event_dict["component"] = "websocket"
    elif "worker" in logger_name.lower():
        event_dict["component"] = "worker"
    elif "upload" in logger_name.lower():
        event_dict["component"] = "upload"
    elif "routes" in logger_name.lower():
        event_dict["component"] = "api"

    return event_dict


def get_logger(name: str) -> Any:
    """
    Get a structured logger instance with instrumentation support.

    Usage:
        logger = get_logger(__name__)
        logger.info("message", extra_field="value")
    """
    return structlog.get_logger(name)


class RequestInstrumentation:
    """
    Context manager for instrumenting requests/operations.

    Usage:
        with RequestInstrumentation("upload_processing", upload_id=upload_id):
            # do work
            pass
    """

    def __init__(self, operation: str, **context: Any):
        self.operation = operation
        self.context = context
        self.start_time = None
        self.logger = get_logger(__name__)

    def __enter__(self) -> RequestInstrumentation:
        self.start_time = time.time()
        structlog.contextvars.bind_contextvars(
            operation=self.operation,
            **self.context,
        )
        self.logger.info(f"{self.operation} started")
        return self

    def __exit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        duration_ms = (time.time() - self.start_time) * 1000 if self.start_time else 0

        if exc_type is None:
            self.logger.info(
                f"{self.operation} completed",
                duration_ms=round(duration_ms, 2),
                status="success",
            )
        else:
            self.logger.error(
                f"{self.operation} failed",
                duration_ms=round(duration_ms, 2),
                status="error",
                error_type=exc_type.__name__ if exc_type else None,
                error_message=str(exc_val) if exc_val else None,
            )

        structlog.contextvars.unbind_contextvars("operation", *self.context.keys())
