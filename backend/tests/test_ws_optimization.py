"""Tests for WebSocket delta optimization and metrics."""

from __future__ import annotations

import pytest

from backend.middleware.ws_metrics import EmissionMetrics, get_metrics, reset_metrics
from backend.utils.delta import (
    compute_delivery_delta,
    compute_scorecard_delta,
    compute_snapshot_delta,
    estimate_payload_size,
)


def test_compute_delivery_delta_append():
    """Test delta computation when new deliveries are appended."""
    prev_deliveries = [
        {"over": 1, "ball": 1, "runs": 0},
        {"over": 1, "ball": 2, "runs": 4},
    ]
    curr_deliveries = [
        {"over": 1, "ball": 1, "runs": 0},
        {"over": 1, "ball": 2, "runs": 4},
        {"over": 1, "ball": 3, "runs": 1},
    ]
    
    delta = compute_delivery_delta(prev_deliveries, curr_deliveries)
    
    assert delta["type"] == "append"
    assert delta["from_index"] == 2
    assert len(delta["new_deliveries"]) == 1
    assert delta["new_deliveries"][0]["ball"] == 3


def test_compute_delivery_delta_no_change():
    """Test delta computation when deliveries are unchanged."""
    deliveries = [
        {"over": 1, "ball": 1, "runs": 0},
        {"over": 1, "ball": 2, "runs": 4},
    ]
    
    delta = compute_delivery_delta(deliveries, deliveries)
    
    # When no changes, should return empty modify type
    assert "type" in delta


def test_compute_scorecard_delta_partial():
    """Test scorecard delta with partial changes."""
    prev_scorecard = {
        "player1": {"runs": 45, "balls": 32},
        "player2": {"runs": 23, "balls": 18},
    }
    curr_scorecard = {
        "player1": {"runs": 49, "balls": 34},  # Changed
        "player2": {"runs": 23, "balls": 18},  # Unchanged
    }
    
    delta = compute_scorecard_delta(prev_scorecard, curr_scorecard)
    
    assert delta is not None
    assert delta["type"] == "partial"
    assert "player1" in delta["changes"]
    assert "player2" not in delta["changes"]


def test_compute_scorecard_delta_first():
    """Test scorecard delta for first scorecard."""
    curr_scorecard = {
        "player1": {"runs": 10, "balls": 8},
    }
    
    delta = compute_scorecard_delta({}, curr_scorecard)
    
    assert delta["type"] == "full"
    assert delta["scorecard"] == curr_scorecard


def test_compute_snapshot_delta():
    """Test full snapshot delta computation."""
    prev_snapshot = {
        "id": "game-123",
        "total_runs": 145,
        "total_wickets": 5,
        "overs": "18.3",
        "deliveries": [{"over": 1, "ball": 1, "runs": 0}],
        "batting_scorecard": {"p1": {"runs": 45}},
        "bowling_scorecard": {"b1": {"wickets": 2}},
    }
    
    curr_snapshot = {
        "id": "game-123",
        "total_runs": 149,  # Changed
        "total_wickets": 5,
        "overs": "19.1",  # Changed
        "deliveries": [
            {"over": 1, "ball": 1, "runs": 0},
            {"over": 1, "ball": 2, "runs": 4},  # New
        ],
        "batting_scorecard": {"p1": {"runs": 49}},  # Changed
        "bowling_scorecard": {"b1": {"wickets": 2}},
    }
    
    delta = compute_snapshot_delta(prev_snapshot, curr_snapshot)
    
    assert delta["type"] == "delta"
    assert delta["id"] == "game-123"
    assert delta["total_runs"] == 149
    assert delta["overs"] == "19.1"
    assert "deliveries_delta" in delta
    assert "batting_scorecard_delta" in delta


def test_estimate_payload_size():
    """Test payload size estimation."""
    data = {
        "id": "game-123",
        "total_runs": 145,
        "deliveries": [{"over": 1, "ball": 1}],
    }
    
    size = estimate_payload_size(data)
    
    assert size > 0
    assert isinstance(size, int)


def test_emission_metrics():
    """Test emission metrics tracking."""
    metrics = EmissionMetrics()
    
    # Record some emissions
    metrics.record_emission("state:update", 1000, 5.0, is_delta=True)
    metrics.record_emission("state:update", 2000, 10.0, is_delta=False)
    metrics.record_emission("prediction:update", 500, 3.0, is_delta=False)
    
    assert metrics.total_emissions == 3
    assert metrics.delta_emissions == 1
    assert metrics.full_emissions == 2
    assert metrics.avg_payload_size == (1000 + 2000 + 500) / 3
    assert metrics.avg_latency_ms == (5.0 + 10.0 + 3.0) / 3
    assert metrics.delta_ratio == 1 / 3
    assert metrics.event_counts["state:update"] == 2
    assert metrics.event_counts["prediction:update"] == 1


def test_emission_metrics_to_dict():
    """Test metrics serialization to dict."""
    metrics = EmissionMetrics()
    metrics.record_emission("test", 1000, 5.0, is_delta=True)
    
    result = metrics.to_dict()
    
    assert isinstance(result, dict)
    assert "total_emissions" in result
    assert "delta_ratio" in result
    assert "avg_payload_size" in result
    assert "event_counts" in result


def test_reset_metrics():
    """Test metrics reset."""
    reset_metrics()
    
    metrics = get_metrics()
    metrics.record_emission("test", 1000, 5.0, is_delta=True)
    
    assert metrics.total_emissions == 1
    
    reset_metrics()
    metrics = get_metrics()
    
    assert metrics.total_emissions == 0


def test_delta_size_reduction():
    """Test that delta updates are significantly smaller than full snapshots."""
    prev_snapshot = {
        "id": "game-123",
        "total_runs": 145,
        "total_wickets": 5,
        "overs": "18.3",
        "deliveries": [{"over": i, "ball": j, "runs": 0} for i in range(1, 20) for j in range(1, 7)],
        "batting_scorecard": {f"p{i}": {"runs": i * 10, "balls": i * 8} for i in range(1, 12)},
        "bowling_scorecard": {f"b{i}": {"overs": i, "runs": i * 5} for i in range(1, 6)},
    }
    
    # Simulate adding one delivery
    curr_snapshot = prev_snapshot.copy()
    curr_snapshot["total_runs"] = 149
    curr_snapshot["overs"] = "19.1"
    curr_snapshot["deliveries"] = prev_snapshot["deliveries"] + [{"over": 20, "ball": 1, "runs": 4}]
    
    # Full snapshot size
    full_size = estimate_payload_size({"snapshot": curr_snapshot})
    
    # Delta size
    delta = compute_snapshot_delta(prev_snapshot, curr_snapshot)
    delta_size = estimate_payload_size({"delta": delta})
    
    # Delta should be much smaller (at least 50% smaller)
    assert delta_size < full_size * 0.5
    print(f"Full snapshot: {full_size} bytes, Delta: {delta_size} bytes")
    print(f"Reduction: {((full_size - delta_size) / full_size * 100):.1f}%")
