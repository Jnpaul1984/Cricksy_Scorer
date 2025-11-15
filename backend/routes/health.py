from __future__ import annotations

from fastapi import APIRouter

router = APIRouter(tags=["health"])


@router.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/healthz")
def healthz() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/api/health/ws-metrics")
def ws_metrics() -> dict[str, any]:
    """
    Get WebSocket/Socket.IO metrics.

    Returns connection statistics, message counts, and error rates.
    Useful for monitoring and alerting.
    """
    from backend.socket_handlers import get_metrics

    return get_metrics()
