from __future__ import annotations

import asyncio
from typing import Any

# Match what tests reset and assert
_sio_server: Any | None = None


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
        return  # nosec


# Convenience emitters used by routes
async def emit_state_update(game_id: str, snapshot: dict[str, Any]) -> None:
    await emit("state:update", {"id": game_id, "snapshot": snapshot}, room=game_id)


async def emit_game_update(game_id: str, payload: dict[str, Any]) -> None:
    # Tests expect the raw payload (no id merged in)
    await emit("game:update", payload, room=game_id)


async def emit_prediction_update(game_id: str, prediction: dict[str, Any]) -> None:
    """Emit win probability prediction update to clients."""
    await emit(
        "prediction:update",
        {"game_id": game_id, "prediction": prediction},
        room=game_id,
    )


async def emit_innings_grade_update(game_id: str, grade_data: dict[str, Any]) -> None:
    """Emit innings grade update to clients."""
    await emit(
        "innings_grade:update",
        {"game_id": game_id, "grade_data": grade_data},
        room=game_id,
    )


async def emit_pressure_update(game_id: str, pressure_data: dict[str, Any]) -> None:
    """Emit pressure map update to clients."""
    await emit(
        "pressure:update",
        {"game_id": game_id, "pressure_data": pressure_data},
        room=game_id,
    )


async def emit_phase_prediction_update(game_id: str, prediction_data: dict[str, Any]) -> None:
    """Emit phase prediction update to clients."""
    await emit(
        "phase_prediction:update",
        {"game_id": game_id, "prediction_data": prediction_data},
        room=game_id,
    )


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
        pass  # nosec
