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
    WebSocket metrics endpoint for monitoring socket emission performance.
    
    Returns metrics about:
    - Total number of emits
    - Total bytes emitted
    - Average, min, and max emit times
    - Error count
    - Average payload size
    """
    from backend.socket_handlers import get_emit_metrics
    
    metrics = get_emit_metrics()
    
    return {
        "status": "ok",
        "metrics": metrics
    }
