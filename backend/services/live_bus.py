from __future__ import annotations

import asyncio
import logging
from typing import Any

from backend.utils.delta import (
    compute_snapshot_delta,
    estimate_payload_size,
    should_send_full_snapshot,
)

logger = logging.getLogger(__name__)

# Match what tests reset and assert
_sio_server: Any | None = None

# Cache of last emitted snapshots per game for delta computation
_last_snapshots: dict[str, dict[str, Any]] = {}


def set_socketio_server(sio: Any) -> None:
    """Register the Socket.IO server instance once during app startup."""
    global _sio_server
    _sio_server = sio


async def emit(
    event: str, data: Any, *, room: str | None = None, namespace: str | None = None
) -> None:
    """Generic async emitter with best-effort error containment."""
    if _sio_server is None:
        return
    try:
        await _sio_server.emit(event, data, room=room, namespace=namespace)
    except Exception:
        # Avoid breaking request handlers on emit failures
        return


# Convenience emitters used by routes
async def emit_state_update(game_id: str, snapshot: dict[str, Any], *, use_delta: bool = True) -> None:
    """
    Emit state update with optional delta optimization.
    
    Args:
        game_id: Game ID
        snapshot: Current game snapshot
        use_delta: If True, compute and send delta instead of full snapshot
    """
    payload: dict[str, Any]
    
    if use_delta:
        prev_snapshot = _last_snapshots.get(game_id)
        
        if should_send_full_snapshot(prev_snapshot):
            # Send full snapshot
            payload = {"id": game_id, "snapshot": snapshot, "type": "full"}
            full_size = estimate_payload_size(payload)
            logger.debug(f"Emitting full snapshot for game {game_id}: {full_size} bytes")
        else:
            # Send delta
            delta = compute_snapshot_delta(prev_snapshot or {}, snapshot)
            payload = {"id": game_id, "delta": delta, "type": "delta"}
            delta_size = estimate_payload_size(payload)
            logger.debug(f"Emitting delta for game {game_id}: {delta_size} bytes")
        
        # Cache current snapshot for next delta
        _last_snapshots[game_id] = snapshot
    else:
        # Legacy: send full snapshot
        payload = {"id": game_id, "snapshot": snapshot, "type": "full"}
    
    await emit("state:update", payload, room=game_id)


async def emit_game_update(game_id: str, payload: dict[str, Any]) -> None:
    # Tests expect the raw payload (no id merged in)
    await emit("game:update", payload, room=game_id)


async def emit_prediction_update(game_id: str, prediction: dict[str, Any]) -> None:
    """Emit win probability prediction update to clients."""
    await emit("prediction:update", {"game_id": game_id, "prediction": prediction}, room=game_id)


def clear_snapshot_cache(game_id: str | None = None) -> None:
    """
    Clear cached snapshots for delta computation.
    
    Args:
        game_id: Specific game ID to clear, or None to clear all
    """
    if game_id:
        _last_snapshots.pop(game_id, None)
    else:
        _last_snapshots.clear()


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
