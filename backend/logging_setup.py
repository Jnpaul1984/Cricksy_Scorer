from __future__ import annotations

import logging
import sys

import structlog


def configure_logging(json: bool = True, level: int = logging.INFO) -> None:
    """
    Configure structlog + stdlib logging.

    - JSON logs by default (set json=False for pretty console in dev).
    - Merges contextvars (e.g., request_id) into each log record.
    - Bridges stdlib loggers (uvicorn, sqlalchemy, etc.) to emit message-only, so
      structlog controls rendering.
    """
    timestamper = structlog.processors.TimeStamper(fmt="iso", utc=True)

    shared_processors = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        timestamper,
    ]

    renderer = (
        structlog.processors.JSONRenderer() if json else structlog.dev.ConsoleRenderer(colors=True)
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
