from __future__ import annotations

import asyncio
import json
import time
from typing import Any

# Match what tests reset and assert
_sio_server: Any | None = None

# Store previous states for delta computation
_PREV_STATES: dict[str, dict[str, Any]] = {}


def set_socketio_server(sio: Any) -> None:
    """Register the Socket.IO server instance once during app startup."""
    global _sio_server
    _sio_server = sio


async def emit(
    event: str, data: Any, *, room: str | None = None, namespace: str | None = None
) -> None:
    """Generic async emitter with best-effort error containment and metrics tracking."""
    if _sio_server is None:
        return

    start_time = time.time()

    try:
        await _sio_server.emit(event, data, room=room, namespace=namespace)

        # Track metrics
        from backend.socket_handlers import _track_emit_metric

        latency_ms = (time.time() - start_time) * 1000
        payload_size = len(json.dumps(data))
        _track_emit_metric(event, payload_size, latency_ms)

    except Exception:
        # Avoid breaking request handlers on emit failures
        return


def _compute_delta(prev: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    """Compute compact delta between previous and current state.

    Only includes fields that have changed to reduce payload size.

    Args:
        prev: Previous state (None if first emission)
        current: Current state

    Returns:
        Compact delta with only changed fields, plus '_full' flag if this is full state
    """
    if prev is None:
        # First emission, send full state with marker
        return {**current, "_full": True}

    delta: dict[str, Any] = {"_full": False}

    for key, value in current.items():
        if key not in prev or prev[key] != value:
            delta[key] = value

    # If delta is very small (< 20% of original), send it
    # Otherwise, send full state (more efficient for large changes)
    if len(delta) < len(current) * 0.2 + 2:  # +2 for _full and potential overhead
        return delta
    else:
        return {**current, "_full": True}


# Convenience emitters used by routes
async def emit_state_update(game_id: str, snapshot: dict[str, Any]) -> None:
    """Emit state update with delta compression."""
    prev_state = _PREV_STATES.get(game_id)
    delta = _compute_delta(prev_state, snapshot)

    # Store current state for next delta
    _PREV_STATES[game_id] = snapshot.copy()

    await emit("state:update", {"id": game_id, "snapshot": delta}, room=game_id)


async def emit_game_update(game_id: str, payload: dict[str, Any]) -> None:
    """Emit game update (tests expect raw payload)."""
    await emit("game:update", payload, room=game_id)


async def emit_prediction_update(game_id: str, prediction: dict[str, Any]) -> None:
    """Emit win probability prediction update to clients."""
    await emit("prediction:update", {"game_id": game_id, "prediction": prediction}, room=game_id)


# Sync-friendly wrapper used by some sync routes (e.g., games_dls)
def publish_game_update(game_id: str, payload: dict[str, Any]) -> None:
    """
    Fire-and-forget from sync contexts. If running in a worker thread without an event loop,
    silently no-op (same behavior as previous 'try: import fail -> no-op' pattern).
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            _ = loop.create_task(emit_game_update(game_id, payload))  # noqa: RUF006
    except Exception:
        # No running loop (e.g., threadpool) — safe no-op
        pass
