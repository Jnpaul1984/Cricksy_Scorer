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
    """Get WebSocket emission metrics.

    Returns metrics including:
    - total_emits: Total number of WebSocket emissions
    - total_bytes_sent: Total bytes sent via WebSocket
    - emit_count_by_event: Emission count per event type
    - avg_payload_size: Average payload size per event type
    - latencies: Latency statistics (p50, p95, p99, max, min)
    - max_latencies: Maximum latency per event type

    These metrics help monitor WebSocket performance and identify bottlenecks.
    """
    from backend.socket_handlers import get_ws_metrics

    return get_ws_metrics()
