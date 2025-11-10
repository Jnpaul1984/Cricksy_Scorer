from __future__ import annotations

import asyncio
import logging
from typing import Any

# Match what tests reset and assert
_sio_server: Any | None = None

logger = logging.getLogger(__name__)


def set_socketio_server(sio: Any) -> None:
    """Register the Socket.IO server instance once during app startup."""
    global _sio_server
    _sio_server = sio


async def emit(
    event: str, data: Any, *, room: str | None = None, namespace: str | None = None
) -> None:
    """
    Generic async emitter with best-effort error containment and non-blocking behavior.
    
    Emits are now non-blocking by default using asyncio.create_task to avoid
    blocking request handlers on slow socket operations.
    """
    if _sio_server is None:
        return
    try:
        # Emit in background to avoid blocking
        asyncio.create_task(
            _sio_server.emit(event, data, room=room, namespace=namespace)
        )
    except Exception as e:
        # Avoid breaking request handlers on emit failures
        logger.error(f"Socket emit error for event {event}: {e}", exc_info=True)
        return


def _compact_game_state(snapshot: dict[str, Any]) -> dict[str, Any]:
    """
    Create a compact version of game state by removing redundant data.
    
    Only include fields that have changed or are essential for UI updates.
    """
    # Keep only essential fields
    compact = {
        "id": snapshot.get("id"),
        "status": snapshot.get("status"),
        "current_inning": snapshot.get("current_inning"),
        "total_runs": snapshot.get("total_runs"),
        "total_wickets": snapshot.get("total_wickets"),
        "overs_completed": snapshot.get("overs_completed"),
        "balls_this_over": snapshot.get("balls_this_over"),
    }
    
    # Optionally include latest delivery only
    deliveries = snapshot.get("deliveries", [])
    if deliveries:
        compact["latest_delivery"] = deliveries[-1]
    
    return compact


# Convenience emitters used by routes
async def emit_state_update(game_id: str, snapshot: dict[str, Any]) -> None:
    """Emit compact state update with delta."""
    compact_snapshot = _compact_game_state(snapshot)
    await emit("state:update", {"id": game_id, "snapshot": compact_snapshot}, room=game_id)


async def emit_game_update(game_id: str, payload: dict[str, Any]) -> None:
    """Emit game update with compact payload."""
    # Tests expect the raw payload (no id merged in)
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
