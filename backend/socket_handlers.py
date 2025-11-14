from __future__ import annotations

import asyncio
import logging
import time
from collections import defaultdict
from typing import Any, cast

logger = logging.getLogger(__name__)

# Presence store: game_id -> { sid -> {"sid": str, "role": str, "name": str} }
_ROOM_PRESENCE: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
_SID_ROOMS: dict[str, set[str]] = defaultdict(set)

# Metrics for monitoring
_EMIT_METRICS = {
    "total_emits": 0,
    "total_bytes": 0,
    "emit_times": [],
    "errors": 0
}


def _room_snapshot(game_id: str) -> list[dict[str, str]]:
    return list(_ROOM_PRESENCE.get(game_id, {}).values())


def _compact_payload(payload: Any) -> Any:
    """
    Create a compact version of a payload by removing null/empty values
    and using shorter key names where appropriate.
    """
    if not isinstance(payload, dict):
        return payload
    
    # Create compact version
    compact = {}
    for key, value in payload.items():
        # Skip null or empty values
        if value is None or value == "" or value == []:
            continue
        
        # Recursively compact nested dicts
        if isinstance(value, dict):
            compact[key] = _compact_payload(value)
        elif isinstance(value, list):
            compact[key] = [_compact_payload(item) if isinstance(item, dict) else item for item in value]
        else:
            compact[key] = value
    
    return compact


async def _emit_with_metrics(
    sio: Any,
    event: str,
    data: Any,
    room: str | None = None,
    namespace: str | None = None
) -> None:
    """
    Emit a message with metrics tracking and non-blocking behavior.
    """
    start_time = time.time()
    
    try:
        # Compact the payload to reduce size
        compact_data = _compact_payload(data)
        
        # Estimate payload size (rough approximation)
        import json
        try:
            payload_bytes = len(json.dumps(compact_data))
        except (TypeError, ValueError):
            payload_bytes = 0
        
        # Emit in background to avoid blocking
        asyncio.create_task(
            sio.emit(event, compact_data, room=room, namespace=namespace)
        )
        
        # Track metrics
        _EMIT_METRICS["total_emits"] += 1
        _EMIT_METRICS["total_bytes"] += payload_bytes
        
        emit_time = time.time() - start_time
        _EMIT_METRICS["emit_times"].append(emit_time)
        
        # Keep only last 1000 emit times
        if len(_EMIT_METRICS["emit_times"]) > 1000:
            _EMIT_METRICS["emit_times"] = _EMIT_METRICS["emit_times"][-1000:]
        
        # Log slow emits
        if emit_time > 0.1:
            logger.warning(
                f"Slow emit: event={event}, time={emit_time:.3f}s, bytes={payload_bytes}"
            )
    
    except Exception as e:
        _EMIT_METRICS["errors"] += 1
        logger.error(f"Error emitting {event}: {e}", exc_info=True)


def get_emit_metrics() -> dict[str, Any]:
    """
    Get current emit metrics for monitoring.
    """
    emit_times = _EMIT_METRICS["emit_times"]
    
    return {
        "total_emits": _EMIT_METRICS["total_emits"],
        "total_bytes": _EMIT_METRICS["total_bytes"],
        "errors": _EMIT_METRICS["errors"],
        "avg_emit_time": sum(emit_times) / len(emit_times) if emit_times else 0,
        "max_emit_time": max(emit_times) if emit_times else 0,
        "min_emit_time": min(emit_times) if emit_times else 0,
        "avg_payload_size": (
            _EMIT_METRICS["total_bytes"] / _EMIT_METRICS["total_emits"]
            if _EMIT_METRICS["total_emits"] > 0 else 0
        )
    }


def register_sio(sio: Any) -> None:
    """
    Register connect/join/leave/disconnect handlers on the provided AsyncServer
    instance. Call this once from main.py after creating the `sio` object.
    
    Enhanced with:
    - Compact payload emissions
    - Non-blocking emits
    - Metrics tracking
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
        # Use compact emit with metrics
        await _emit_with_metrics(
            sio,
            "presence:init",
            {"game_id": game_id, "members": _room_snapshot(game_id)},
            room=sid,
        )
        await _emit_with_metrics(
            sio,
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
        await _emit_with_metrics(
            sio,
            "presence:update",
            {"game_id": game_id, "members": _room_snapshot(game_id)},
            room=game_id,
        )
        return None

    async def _disconnect(sid: str) -> None:
        # Remove from all rooms we know about
        for game_id in list(_SID_ROOMS.get(sid, set())):
            _ROOM_PRESENCE.get(game_id, {}).pop(sid, None)
            await _emit_with_metrics(
                sio,
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
