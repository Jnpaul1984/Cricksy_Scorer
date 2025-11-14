"""WebSocket metrics tracking middleware.

This module tracks WebSocket emission metrics including:
- Total emissions count
- Payload sizes (avg, min, max)
- Emission latency
- Delta vs full snapshot ratio
"""

from __future__ import annotations

import logging
import time
from collections import defaultdict
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class EmissionMetrics:
    """Metrics for WebSocket emissions."""
    
    total_emissions: int = 0
    full_emissions: int = 0
    delta_emissions: int = 0
    
    total_bytes_sent: int = 0
    min_payload_size: int = 0
    max_payload_size: int = 0
    
    total_latency_ms: float = 0.0
    
    # Per-event type counters
    event_counts: dict[str, int] = field(default_factory=lambda: defaultdict(int))
    
    def record_emission(
        self,
        event: str,
        payload_size: int,
        latency_ms: float,
        is_delta: bool = False,
    ) -> None:
        """Record a single emission."""
        self.total_emissions += 1
        self.event_counts[event] += 1
        
        if is_delta:
            self.delta_emissions += 1
        else:
            self.full_emissions += 1
        
        self.total_bytes_sent += payload_size
        
        if self.min_payload_size == 0 or payload_size < self.min_payload_size:
            self.min_payload_size = payload_size
        
        if payload_size > self.max_payload_size:
            self.max_payload_size = payload_size
        
        self.total_latency_ms += latency_ms
    
    @property
    def avg_payload_size(self) -> float:
        """Average payload size in bytes."""
        if self.total_emissions == 0:
            return 0.0
        return self.total_bytes_sent / self.total_emissions
    
    @property
    def avg_latency_ms(self) -> float:
        """Average emission latency in milliseconds."""
        if self.total_emissions == 0:
            return 0.0
        return self.total_latency_ms / self.total_emissions
    
    @property
    def delta_ratio(self) -> float:
        """Ratio of delta emissions to total emissions."""
        if self.total_emissions == 0:
            return 0.0
        return self.delta_emissions / self.total_emissions
    
    def to_dict(self) -> dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            "total_emissions": self.total_emissions,
            "full_emissions": self.full_emissions,
            "delta_emissions": self.delta_emissions,
            "delta_ratio": round(self.delta_ratio, 3),
            "total_bytes_sent": self.total_bytes_sent,
            "avg_payload_size": round(self.avg_payload_size, 2),
            "min_payload_size": self.min_payload_size,
            "max_payload_size": self.max_payload_size,
            "avg_latency_ms": round(self.avg_latency_ms, 3),
            "event_counts": dict(self.event_counts),
        }


# Global metrics instance
_metrics = EmissionMetrics()


def get_metrics() -> EmissionMetrics:
    """Get the global metrics instance."""
    return _metrics


def reset_metrics() -> None:
    """Reset all metrics to zero."""
    global _metrics
    _metrics = EmissionMetrics()


async def track_emission(
    event: str,
    data: Any,
    emit_fn: Any,
    **kwargs: Any,
) -> None:
    """
    Track an emission and record metrics.
    
    Args:
        event: Event name
        data: Payload data
        emit_fn: Async emission function
        **kwargs: Additional kwargs for emit_fn
    """
    from backend.utils.delta import estimate_payload_size
    
    start_time = time.perf_counter()
    payload_size = estimate_payload_size(data)
    is_delta = isinstance(data, dict) and data.get("type") == "delta"
    
    try:
        await emit_fn(event, data, **kwargs)
    finally:
        end_time = time.perf_counter()
        latency_ms = (end_time - start_time) * 1000
        
        _metrics.record_emission(
            event=event,
            payload_size=payload_size,
            latency_ms=latency_ms,
            is_delta=is_delta,
        )
        
        # Log slow emissions
        if latency_ms > 100:  # > 100ms
            logger.warning(
                f"Slow WebSocket emission: {event} took {latency_ms:.2f}ms, "
                f"payload size: {payload_size} bytes"
            )


def log_metrics() -> None:
    """Log current metrics to structured logs."""
    metrics_dict = _metrics.to_dict()
    logger.info(
        "WebSocket metrics",
        extra={"metrics": metrics_dict},
    )
