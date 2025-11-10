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
        # Add metrics processor
        _add_metrics_context,
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


def _add_metrics_context(
    logger: logging.Logger, method_name: str, event_dict: dict
) -> dict:
    """
    Processor to add metrics context to log entries.
    
    This enriches logs with performance metrics when available.
    """
    # Add WebSocket metrics if logging socket-related events
    if "socket" in event_dict.get("event", "").lower() or "emit" in event_dict.get("event", "").lower():
        try:
            from backend.socket_handlers import get_emit_metrics
            metrics = get_emit_metrics()
            event_dict["ws_metrics"] = {
                "total_emits": metrics["total_emits"],
                "avg_emit_time_ms": round(metrics["avg_emit_time"] * 1000, 2),
                "errors": metrics["errors"]
            }
        except Exception:
            pass  # Don't fail logging if metrics unavailable
    
    return event_dict


def log_metric(metric_name: str, value: float, **tags) -> None:
    """
    Log a structured metric.
    
    Args:
        metric_name: Name of the metric (e.g., "upload.processing_time")
        value: Numeric value of the metric
        **tags: Additional tags/dimensions for the metric
    """
    logger = structlog.get_logger()
    logger.info(
        "metric",
        metric_name=metric_name,
        value=value,
        **tags
    )
