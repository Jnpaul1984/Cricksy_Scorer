from __future__ import annotations

from typing import Any

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/health/ws-metrics")
def ws_metrics() -> dict[str, Any]:
    """
    Get WebSocket emission metrics.

    Returns metrics about WebSocket emissions including:
    - Total number of emits
    - Total payload size in bytes
    - Average and max emit duration
    - Uptime since last reset
    """
    from backend.socket_handlers import get_ws_metrics

    return get_ws_metrics()
