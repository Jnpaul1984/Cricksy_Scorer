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
    Get WebSocket emission metrics for observability.
    
    Returns aggregated metrics including:
    - Total emissions count
    - Payload sizes (avg, min, max)
    - Emission latency
    - Delta vs full snapshot ratio
    - Per-event type counts
    """
    from backend.middleware.ws_metrics import get_metrics
    
    metrics = get_metrics()
    return {
        "status": "ok",
        "metrics": metrics.to_dict(),
    }
