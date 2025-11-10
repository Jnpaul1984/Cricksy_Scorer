from __future__ import annotations

import logging
import time
from collections import defaultdict
from typing import Any, cast

logger = logging.getLogger(__name__)

# Presence store: game_id -> { sid -> {"sid": str, "role": str, "name": str} }
_ROOM_PRESENCE: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
_SID_ROOMS: dict[str, set[str]] = defaultdict(set)

# WebSocket metrics tracking (Week 3)
_WS_METRICS: dict[str, Any] = {
    "total_emits": 0,
    "total_payload_bytes": 0,
    "emit_durations_ms": [],
    "last_reset": time.time(),
}


def _room_snapshot(game_id: str) -> list[dict[str, str]]:
    return list(_ROOM_PRESENCE.get(game_id, {}).values())


def get_ws_metrics() -> dict[str, Any]:
    """Get WebSocket metrics for monitoring."""
    durations = _WS_METRICS["emit_durations_ms"]
    return {
        "total_emits": _WS_METRICS["total_emits"],
        "total_payload_bytes": _WS_METRICS["total_payload_bytes"],
        "avg_emit_duration_ms": sum(durations) / len(durations) if durations else 0,
        "max_emit_duration_ms": max(durations) if durations else 0,
        "uptime_seconds": time.time() - _WS_METRICS["last_reset"],
    }


def reset_ws_metrics() -> None:
    """Reset WebSocket metrics."""
    _WS_METRICS["total_emits"] = 0
    _WS_METRICS["total_payload_bytes"] = 0
    _WS_METRICS["emit_durations_ms"] = []
    _WS_METRICS["last_reset"] = time.time()


async def emit_compact_delta(
    sio: Any, event: str, delta: dict[str, Any], room: str
) -> None:
    """
    Emit a compact delta update to a room.

    This function wraps sio.emit() to:
    1. Track metrics (payload size, emit duration)
    2. Optionally compress/optimize payload
    3. Log emissions for debugging

    Args:
        sio: Socket.IO server instance
        event: Event name
        delta: Delta payload (should be minimal - only changed fields)
        room: Room/game ID to emit to
    """
    start_time = time.time()

    # Estimate payload size (rough approximation)
    payload_size = len(str(delta))

    # Emit to room
    await sio.emit(event, delta, room=room)

    # Track metrics
    duration_ms = (time.time() - start_time) * 1000
    _WS_METRICS["total_emits"] += 1
    _WS_METRICS["total_payload_bytes"] += payload_size
    _WS_METRICS["emit_durations_ms"].append(duration_ms)

    # Keep only last 1000 durations to avoid memory bloat
    if len(_WS_METRICS["emit_durations_ms"]) > 1000:
        _WS_METRICS["emit_durations_ms"] = _WS_METRICS["emit_durations_ms"][-1000:]

    logger.debug(
        f"Emitted {event} to room {room}: {payload_size} bytes in {duration_ms:.2f}ms"
    )


def register_sio(sio: Any) -> None:
    """
    Register connect/join/leave/disconnect handlers on the provided AsyncServer
    instance. Call this once from main.py after creating the `sio` object.
    """

    async def _connect(sid: str, environ: dict[str, Any], auth: Any | None) -> None:
        # Keep connection open; auth/JWT (if any) can be validated on 'join'
        return None

    async def _join(sid: str, data: dict[str, Any] | None) -> None:
        """
        data: { game_id: str, role?: "SCORER"|"COMMENTATOR"|"ANALYST"|"VIEWER", name?: str }
        """
        payload = data or {}
        game_id = cast(str | None, payload.get("game_id"))
        if not game_id:
            return None
        role = str(payload.get("role") or "VIEWER")
        name = str(payload.get("name") or role)

        # enter room and track presence
        await sio.enter_room(sid, game_id)
        _SID_ROOMS[sid].add(game_id)
        _ROOM_PRESENCE[game_id][sid] = {"sid": sid, "role": role, "name": name}

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
        return None

    async def _leave(sid: str, data: dict[str, Any] | None) -> None:
        payload = data or {}
        game_id = cast(str | None, payload.get("game_id"))
        if not game_id:
            return None
        await sio.leave_room(sid, game_id)
        _SID_ROOMS[sid].discard(game_id)
        _ROOM_PRESENCE.get(game_id, {}).pop(sid, None)
        await sio.emit(
            "presence:update",
            {"game_id": game_id, "members": _room_snapshot(game_id)},
            room=game_id,
        )
        return None

    async def _disconnect(sid: str) -> None:
        # Remove from all rooms we know about
        for game_id in list(_SID_ROOMS.get(sid, set())):
            _ROOM_PRESENCE.get(game_id, {}).pop(sid, None)
            await sio.emit(
                "presence:update",
                {"game_id": game_id, "members": _room_snapshot(game_id)},
                room=game_id,
            )
        _SID_ROOMS.pop(sid, None)
        return None

    # Register handlers on the server instance
    sio.on("connect")(_connect)
    sio.on("join")(_join)
    sio.on("leave")(_leave)
    sio.on("disconnect")(_disconnect)
