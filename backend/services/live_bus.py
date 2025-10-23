"""
Live event bus for decoupling route handlers from Socket.IO server.

Provides a clean API for emitting Socket.IO events without requiring
lazy imports of backend.main.sio, reducing circular import risk and
simplifying testing.
"""
from __future__ import annotations

import asyncio
import logging
from typing import Any, Optional, Dict

logger = logging.getLogger(__name__)

# Global reference to the Socket.IO server, set once at startup
_sio_server: Optional[Any] = None


def set_socketio_server(sio: Any) -> None:
    """
    Register the AsyncServer instance once at startup.
    Call this from main.py after creating the Socket.IO server.
    
    Args:
        sio: The socketio.AsyncServer instance
    """
    global _sio_server
    _sio_server = sio
    logger.info("Socket.IO server registered with live event bus")


async def emit(
    event: str,
    data: Any,
    *,
    room: Optional[str] = None,
    namespace: Optional[str] = None,
) -> None:
    """
    Generic event emitter that safely emits to Socket.IO.
    
    If the bus is not initialized (e.g., during certain tests),
    this is a no-op instead of raising an error.
    
    Args:
        event: The event name (e.g., "state:update", "game:update")
        data: The event payload
        room: Optional room to emit to (typically a game_id)
        namespace: Optional Socket.IO namespace
    """
    if _sio_server is None:
        logger.debug(f"Socket.IO server not initialized, skipping emit of {event}")
        return
    
    try:
        await _sio_server.emit(event, data, room=room, namespace=namespace)
    except Exception as e:
        # Log but don't break the request handler
        logger.error(f"Failed to emit {event}: {e}", exc_info=True)


async def emit_state_update(game_id: str, snapshot: Dict[str, Any]) -> None:
    """
    Convenience method for emitting state:update events.
    
    Args:
        game_id: The game ID (used as the room)
        snapshot: The game state snapshot to broadcast
    """
    await emit("state:update", {"id": game_id, "snapshot": snapshot}, room=game_id)


async def emit_game_update(game_id: str, payload: Dict[str, Any]) -> None:
    """
    Convenience method for emitting game:update events.
    
    Args:
        game_id: The game ID (used as the room)
        payload: The update payload to broadcast
    """
    await emit("game:update", payload, room=game_id)


def publish_game_update(game_id: str, payload: Dict[str, Any]) -> None:
    """
    Sync-friendly wrapper for emit_game_update.
    
    This schedules the emit when an event loop is available, making it
    safe to call from synchronous contexts (e.g., SQLAlchemy session threads).
    
    Args:
        game_id: The game ID (used as the room)
        payload: The update payload to broadcast
    """
    if _sio_server is None:
        logger.debug(f"Socket.IO server not initialized, skipping publish_game_update for {game_id}")
        return
    
    try:
        # Try to get the running event loop
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Schedule as a task
            asyncio.create_task(emit_game_update(game_id, payload))
        else:
            # Run until complete if no loop is running
            loop.run_until_complete(emit_game_update(game_id, payload))
    except RuntimeError:
        # No event loop available, try creating one
        try:
            asyncio.run(emit_game_update(game_id, payload))
        except Exception as e:
            logger.error(f"Failed to publish game update for {game_id}: {e}", exc_info=True)
    except Exception as e:
        logger.error(f"Failed to publish game update for {game_id}: {e}", exc_info=True)
