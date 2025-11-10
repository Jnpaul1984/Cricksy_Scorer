from __future__ import annotations

import time
from collections import defaultdict
from typing import Any, cast

# Presence store: game_id -> { sid -> {"sid": str, "role": str, "name": str} }
_ROOM_PRESENCE: dict[str, dict[str, dict[str, str]]] = defaultdict(dict)
_SID_ROOMS: dict[str, set[str]] = defaultdict(set)

# WebSocket metrics tracking
_WS_METRICS = {
    "total_emits": 0,
    "total_bytes_sent": 0,
    "emit_count_by_event": defaultdict(int),
    "avg_payload_size": defaultdict(float),
    "emit_latencies": [],  # Store last 1000 latencies
    "max_latencies": defaultdict(float),
}


def _room_snapshot(game_id: str) -> list[dict[str, str]]:
    return list(_ROOM_PRESENCE.get(game_id, {}).values())


def _track_emit_metric(event: str, payload_size: int, latency_ms: float) -> None:
    """Track WebSocket emission metrics for monitoring."""
    _WS_METRICS["total_emits"] += 1
    _WS_METRICS["total_bytes_sent"] += payload_size
    _WS_METRICS["emit_count_by_event"][event] += 1

    # Update average payload size
    event_count = _WS_METRICS["emit_count_by_event"][event]
    prev_avg = _WS_METRICS["avg_payload_size"][event]
    _WS_METRICS["avg_payload_size"][event] = (prev_avg * (event_count - 1) + payload_size) / event_count

    # Track latency
    _WS_METRICS["emit_latencies"].append(latency_ms)
    if len(_WS_METRICS["emit_latencies"]) > 1000:
        _WS_METRICS["emit_latencies"].pop(0)

    # Track max latency per event
    if latency_ms > _WS_METRICS["max_latencies"].get(event, 0):
        _WS_METRICS["max_latencies"][event] = latency_ms


def get_ws_metrics() -> dict[str, Any]:
    """Get WebSocket emission metrics.

    Returns:
        Dictionary with metrics including:
        - total_emits: Total number of emissions
        - total_bytes_sent: Total bytes sent
        - emit_count_by_event: Count per event type
        - avg_payload_size: Average payload size per event
        - latencies: Latency statistics (p50, p95, p99, max)
    """
    latencies = sorted(_WS_METRICS["emit_latencies"])
    n = len(latencies)

    latency_stats = {}
    if n > 0:
        latency_stats = {
            "p50": latencies[int(n * 0.5)] if n > 0 else 0,
            "p95": latencies[int(n * 0.95)] if n > 0 else 0,
            "p99": latencies[int(n * 0.99)] if n > 0 else 0,
            "max": latencies[-1] if n > 0 else 0,
            "min": latencies[0] if n > 0 else 0,
            "count": n,
        }

    return {
        "total_emits": _WS_METRICS["total_emits"],
        "total_bytes_sent": _WS_METRICS["total_bytes_sent"],
        "emit_count_by_event": dict(_WS_METRICS["emit_count_by_event"]),
        "avg_payload_size": dict(_WS_METRICS["avg_payload_size"]),
        "max_latencies": dict(_WS_METRICS["max_latencies"]),
        "latencies": latency_stats,
    }


def _compact_delta(prev: dict[str, Any] | None, current: dict[str, Any]) -> dict[str, Any]:
    """Create a compact delta between previous and current state.

    Only includes fields that have changed to reduce payload size.

    Args:
        prev: Previous state (None if first emission)
        current: Current state

    Returns:
        Compact delta with only changed fields
    """
    if prev is None:
        return current  # First emission, send full state

    delta: dict[str, Any] = {}

    for key, value in current.items():
        if key not in prev or prev[key] != value:
            delta[key] = value

    return delta


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
        start_time = time.time()
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
        init_payload = {"game_id": game_id, "members": _room_snapshot(game_id)}
        await sio.emit("presence:init", init_payload, room=sid)

        update_payload = {"game_id": game_id, "members": _room_snapshot(game_id)}
        await sio.emit("presence:update", update_payload, room=game_id)

        # Track metrics
        import json

        latency_ms = (time.time() - start_time) * 1000
        _track_emit_metric("presence:init", len(json.dumps(init_payload)), latency_ms)
        _track_emit_metric("presence:update", len(json.dumps(update_payload)), latency_ms)

        return None

    async def _leave(sid: str, data: dict[str, Any] | None) -> None:
        start_time = time.time()
        payload = data or {}
        game_id = cast(str | None, payload.get("game_id"))
        if not game_id:
            return None
        await sio.leave_room(sid, game_id)
        _SID_ROOMS[sid].discard(game_id)
        _ROOM_PRESENCE.get(game_id, {}).pop(sid, None)

        update_payload = {"game_id": game_id, "members": _room_snapshot(game_id)}
        await sio.emit("presence:update", update_payload, room=game_id)

        # Track metrics
        import json

        latency_ms = (time.time() - start_time) * 1000
        _track_emit_metric("presence:update", len(json.dumps(update_payload)), latency_ms)

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
