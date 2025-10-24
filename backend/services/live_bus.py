from __future__ import annotations

from typing import Any, Optional, Dict, List
import asyncio

_SIO: Optional[Any] = None


def set_socketio_server(sio: Any) -> None:
    """Register the Socket.IO server instance once during app startup."""
    global _SIO
    _SIO = sio


async def emit(event: str, data: Any, *, room: Optional[str] = None, namespace: Optional[str] = None) -> None:
    """Generic async emitter with best-effort error containment."""
    if _SIO is None:
        return
    try:
        await _SIO.emit(event, data, room=room, namespace=namespace)
    except Exception:
        # Avoid breaking request handlers on emit failures
        return


# Convenience emitters used by routes
async def emit_state_update(game_id: str, snapshot: Dict[str, Any]) -> None:
    await emit("state:update", {"id": game_id, "snapshot": snapshot}, room=game_id)


async def emit_game_update(game_id: str, payload: Dict[str, Any]) -> None:
    await emit("game:update", {"id": game_id, **payload}, room=game_id)


# Keep references to tasks to avoid garbage collection warning (RUF006)
_tasks: List[asyncio.Task[Any]] = []


# Sync-friendly wrapper used by some sync routes (e.g., games_dls)
def publish_game_update(game_id: str, payload: Dict[str, Any]) -> None:
    """
    Fire-and-forget from sync contexts. If running in a worker thread without an event loop,
    silently no-op (same behavior as previous 'try: import fail -> no-op' pattern).
    """
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            task = loop.create_task(emit_game_update(game_id, payload))
            _tasks.append(task)
            # Clean up completed tasks periodically
            _tasks[:] = [t for t in _tasks if not t.done()]
    except Exception:
        # No running loop (e.g., threadpool) - safe no-op
        pass


