from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any, cast

logger = logging.getLogger(__name__)

# Presence store: game_id -> { sid -> {"sid": str, "role": str, "name": str} }
_ROOM_PRESENCE: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
_SID_ROOMS: dict[str, set[str]] = defaultdict(set)

# Metrics for monitoring
_METRICS = {
    "connections": 0,
    "disconnections": 0,
    "joins": 0,
    "leaves": 0,
    "messages_sent": 0,
    "errors": 0,
}


def _room_snapshot(game_id: str) -> list[dict[str, str]]:
    return list(_ROOM_PRESENCE.get(game_id, {}).values())


def get_metrics() -> dict[str, Any]:
    """Get current WebSocket metrics."""
    return {
        **_METRICS,
        "active_connections": sum(len(rooms) for rooms in _SID_ROOMS.values()),
        "active_rooms": len(_ROOM_PRESENCE),
        "timestamp": time.time(),
    }


def emit_compact_delta(
    sio: Any,
    game_id: str,
    event_type: str,
    delta: dict[str, Any],
) -> None:
    """
    Emit a compact delta event instead of full game state.

    This reduces bandwidth and improves performance by sending only changes.

    Args:
        sio: Socket.IO server instance
        game_id: Game room ID
        event_type: Type of event (e.g., 'delivery', 'score_update', 'wicket')
        delta: Compact payload with only changed fields
    """
    try:
        # Add metadata
        payload = {
            "type": event_type,
            "game_id": game_id,
            "timestamp": time.time(),
            "delta": delta,
        }

        # Emit to room
        sio.emit("game:delta", payload, room=game_id)
        _METRICS["messages_sent"] += 1

        logger.debug(
            f"Emitted delta event",
            extra={
                "game_id": game_id,
                "event_type": event_type,
                "payload_size": len(str(delta)),
            },
        )
    except Exception as e:
        logger.error(f"Failed to emit delta: {e}", exc_info=True)
        _METRICS["errors"] += 1


def register_sio(sio: Any) -> None:
    """
    Register connect/join/leave/disconnect handlers on the provided AsyncServer
    instance. Call this once from main.py after creating the `sio` object.

    Includes enhanced logging, metrics, and error handling.
    """

    async def _connect(sid: str, environ: dict[str, Any], auth: Any | None) -> None:
        """Handle client connection."""
        _METRICS["connections"] += 1
        logger.info(f"Client connected: {sid}")
        return None

    async def _join(sid: str, data: dict[str, Any] | None) -> None:
        """
        Handle client joining a game room.

        data: { game_id: str, role?: "SCORER"|"COMMENTATOR"|"ANALYST"|"VIEWER", name?: str }
        """
        try:
            payload = data or {}
            game_id = cast(str | None, payload.get("game_id"))
            if not game_id:
                logger.warning(f"Join request without game_id from {sid}")
                return None

            role = str(payload.get("role") or "VIEWER")
            name = str(payload.get("name") or role)

            # Enter room and track presence
            await sio.enter_room(sid, game_id)
            _SID_ROOMS[sid].add(game_id)
            _ROOM_PRESENCE[game_id][sid] = {"sid": sid, "role": role, "name": name}

            _METRICS["joins"] += 1

            logger.info(
                f"Client joined room",
                extra={
                    "sid": sid,
                    "game_id": game_id,
                    "role": role,
                    "name": name,
                    "room_size": len(_ROOM_PRESENCE[game_id]),
                },
            )

            # Tell this client who's here, then broadcast updated presence to the room
            await sio.emit(
                "presence:init",
                {"game_id": game_id, "members": _room_snapshot(game_id)},
                room=sid,
            )
            await sio.emit(
                "presence:update",
                {"game_id": game_id, "members": _room_snapshot(game_id)},
                room=game_id,
            )
            _METRICS["messages_sent"] += 2

        except Exception as e:
            logger.error(f"Error in join handler: {e}", exc_info=True)
            _METRICS["errors"] += 1

        return None

    async def _leave(sid: str, data: dict[str, Any] | None) -> None:
        """Handle client leaving a game room."""
        try:
            payload = data or {}
            game_id = cast(str | None, payload.get("game_id"))
            if not game_id:
                return None

            await sio.leave_room(sid, game_id)
            _SID_ROOMS[sid].discard(game_id)
            _ROOM_PRESENCE.get(game_id, {}).pop(sid, None)

            _METRICS["leaves"] += 1

            logger.info(
                f"Client left room",
                extra={
                    "sid": sid,
                    "game_id": game_id,
                    "room_size": len(_ROOM_PRESENCE.get(game_id, {})),
                },
            )

            await sio.emit(
                "presence:update",
                {"game_id": game_id, "members": _room_snapshot(game_id)},
                room=game_id,
            )
            _METRICS["messages_sent"] += 1

        except Exception as e:
            logger.error(f"Error in leave handler: {e}", exc_info=True)
            _METRICS["errors"] += 1

        return None

    async def _disconnect(sid: str) -> None:
        """Handle client disconnection."""
        try:
            _METRICS["disconnections"] += 1

            # Remove from all rooms we know about
            rooms = list(_SID_ROOMS.get(sid, set()))
            for game_id in rooms:
                _ROOM_PRESENCE.get(game_id, {}).pop(sid, None)
                await sio.emit(
                    "presence:update",
                    {"game_id": game_id, "members": _room_snapshot(game_id)},
                    room=game_id,
                )
                _METRICS["messages_sent"] += 1

            _SID_ROOMS.pop(sid, None)

            logger.info(
                f"Client disconnected",
                extra={"sid": sid, "rooms_left": len(rooms)},
            )

        except Exception as e:
            logger.error(f"Error in disconnect handler: {e}", exc_info=True)
            _METRICS["errors"] += 1

        return None

    # Register handlers on the server instance
    sio.on("connect")(_connect)
    sio.on("join")(_join)
    sio.on("leave")(_leave)
    sio.on("disconnect")(_disconnect)

    logger.info("Socket.IO handlers registered")

