"""Delta computation utilities for WebSocket optimization.

This module provides helpers to compute minimal delta updates for game state,
reducing payload size and latency for real-time updates.
"""

from __future__ import annotations

from typing import Any


def compute_delivery_delta(
    prev_deliveries: list[dict[str, Any]],
    curr_deliveries: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Compute a minimal delta for deliveries list.
    
    Instead of sending the entire deliveries list, only send:
    - New deliveries since last update
    - Modified deliveries (if any)
    
    Args:
        prev_deliveries: Previous deliveries list
        curr_deliveries: Current deliveries list
    
    Returns:
        Delta object with new/modified deliveries
    """
    prev_count = len(prev_deliveries)
    curr_count = len(curr_deliveries)
    
    # Most common case: new deliveries appended
    if curr_count > prev_count:
        new_deliveries = curr_deliveries[prev_count:]
        return {
            "type": "append",
            "new_deliveries": new_deliveries,
            "from_index": prev_count,
        }
    
    # If counts are equal, check for modifications
    if curr_count == prev_count:
        modified: list[tuple[int, dict[str, Any]]] = []
        for i, (prev, curr) in enumerate(zip(prev_deliveries, curr_deliveries)):
            if prev != curr:
                modified.append((i, curr))
        
        if modified:
            return {
                "type": "modify",
                "modified_deliveries": [{"index": idx, "delivery": d} for idx, d in modified],
            }
    
    # Full replacement needed (rare case)
    return {
        "type": "replace",
        "deliveries": curr_deliveries,
    }


def compute_scorecard_delta(
    prev_scorecard: dict[str, Any],
    curr_scorecard: dict[str, Any],
) -> dict[str, Any] | None:
    """
    Compute minimal delta for batting/bowling scorecard.
    
    Only send changed player entries rather than entire scorecard.
    
    Args:
        prev_scorecard: Previous scorecard
        curr_scorecard: Current scorecard
    
    Returns:
        Delta object or None if no changes
    """
    if not prev_scorecard:
        # First scorecard - send full
        return {"type": "full", "scorecard": curr_scorecard}
    
    changes: dict[str, Any] = {}
    
    # Compare each key in the scorecard
    for key, curr_value in curr_scorecard.items():
        prev_value = prev_scorecard.get(key)
        if prev_value != curr_value:
            changes[key] = curr_value
    
    if changes:
        return {"type": "partial", "changes": changes}
    
    return None


def compute_snapshot_delta(
    prev_snapshot: dict[str, Any],
    curr_snapshot: dict[str, Any],
) -> dict[str, Any]:
    """
    Compute a minimal delta for the entire game snapshot.
    
    This identifies which parts of the snapshot have changed and only
    includes those in the delta, significantly reducing payload size.
    
    Args:
        prev_snapshot: Previous snapshot
        curr_snapshot: Current snapshot
    
    Returns:
        Delta update with only changed fields
    """
    delta: dict[str, Any] = {
        "id": curr_snapshot.get("id"),
        "type": "delta",
    }
    
    # Always include critical state fields
    critical_fields = [
        "total_runs",
        "total_wickets",
        "overs",
        "current_striker_id",
        "current_non_striker_id",
        "current_bowler_id",
        "status",
    ]
    
    for field in critical_fields:
        if prev_snapshot.get(field) != curr_snapshot.get(field):
            delta[field] = curr_snapshot.get(field)
    
    # Compute delivery delta
    prev_deliveries = prev_snapshot.get("deliveries", [])
    curr_deliveries = curr_snapshot.get("deliveries", [])
    if prev_deliveries != curr_deliveries:
        delta["deliveries_delta"] = compute_delivery_delta(prev_deliveries, curr_deliveries)
    
    # Compute scorecard deltas
    prev_batting = prev_snapshot.get("batting_scorecard", {})
    curr_batting = curr_snapshot.get("batting_scorecard", {})
    batting_delta = compute_scorecard_delta(prev_batting, curr_batting)
    if batting_delta:
        delta["batting_scorecard_delta"] = batting_delta
    
    prev_bowling = prev_snapshot.get("bowling_scorecard", {})
    curr_bowling = curr_snapshot.get("bowling_scorecard", {})
    bowling_delta = compute_scorecard_delta(prev_bowling, curr_bowling)
    if bowling_delta:
        delta["bowling_scorecard_delta"] = bowling_delta
    
    # Only include flags that changed
    flag_fields = ["needs_new_batter", "needs_new_over", "is_game_over"]
    for field in flag_fields:
        if prev_snapshot.get(field) != curr_snapshot.get(field):
            delta[field] = curr_snapshot.get(field)
    
    return delta


def estimate_payload_size(data: Any) -> int:
    """
    Estimate payload size in bytes for logging/metrics.
    
    This is a rough estimate based on JSON serialization.
    
    Args:
        data: Data to estimate
    
    Returns:
        Estimated size in bytes
    """
    import json
    try:
        return len(json.dumps(data, default=str))
    except Exception:
        return 0


def should_send_full_snapshot(prev_snapshot: dict[str, Any] | None) -> bool:
    """
    Determine if we should send a full snapshot instead of delta.
    
    Send full snapshot if:
    - No previous snapshot (new connection)
    - Previous snapshot is too old (large gaps)
    - Delta would be similar size to full snapshot
    
    Args:
        prev_snapshot: Previous snapshot or None
    
    Returns:
        True if should send full, False if delta is better
    """
    if not prev_snapshot:
        return True
    
    # For now, always use delta if we have a previous snapshot
    # Can add more sophisticated logic later
    return False
