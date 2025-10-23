from __future__ import annotations

from collections import defaultdict
from typing import Any, Dict, Optional, List, Mapping, cast

# Presence store: game_id -> { sid -> {"sid": str, "role": str, "name": str} }
_ROOM_PRESENCE: Dict[str, Dict[str, Dict[str, str]]] = defaultdict(dict)
_SID_ROOMS: Dict[str, set[str]] = defaultdict(set)


def _room_snapshot(game_id: str) -> List[Dict[str, str]]:
    return list(_ROOM_PRESENCE.get(game_id, {}).values())


def register_sio(sio: Any) -> None:
    """
    Register connect/join/leave/disconnect handlers on the provided AsyncServer
    instance. Call this once from main.py after creating the `sio` object.
    """

    async def _connect(sid: str, environ: Dict[str, Any], auth: Optional[Any]) -> None:
        # Keep connection open; auth/JWT (if any) can be validated on 'join'
        return None

    async def _join(sid: str, data: Optional[Dict[str, Any]]) -> None:
        """
        data: { game_id: str, role?: "SCORER"|"COMMENTATOR"|"ANALYST"|"VIEWER", name?: str }
        """
        payload = data or {}
        game_id = cast(Optional[str], payload.get("game_id"))
        if not game_id:
            return None
        role = str(payload.get("role") or "VIEWER")
        name = str(payload.get("name") or role)

        # enter room and track presence
        await sio.enter_room(sid, game_id)
        _SID_ROOMS[sid].add(game_id)
        _ROOM_PRESENCE[game_id][sid] = {"sid": sid, "role": role, "name": name}

        # Tell this client who's here, then broadcast updated presence to the room
        await sio.emit("presence:init", {"game_id": game_id, "members": _room_snapshot(game_id)}, room=sid)
        await sio.emit("presence:update", {"game_id": game_id, "members": _room_snapshot(game_id)}, room=game_id)
        return None

    async def _leave(sid: str, data: Optional[Dict[str, Any]]) -> None:
        payload = data or {}
        game_id = cast(Optional[str], payload.get("game_id"))
        if not game_id:
            return None
        await sio.leave_room(sid, game_id)
        _SID_ROOMS[sid].discard(game_id)
        _ROOM_PRESENCE.get(game_id, {}).pop(sid, None)
        await sio.emit("presence:update", {"game_id": game_id, "members": _room_snapshot(game_id)}, room=game_id)
        return None

    async def _disconnect(sid: str) -> None:
        # Remove from all rooms we know about
        for game_id in list(_SID_ROOMS.get(sid, set())):
            _ROOM_PRESENCE.get(game_id, {}).pop(sid, None)
            await sio.emit("presence:update", {"game_id": game_id, "members": _room_snapshot(game_id)}, room=game_id)
        _SID_ROOMS.pop(sid, None)
        return None

    # Register handlers on the server instance
    sio.on("connect")(_connect)
    sio.on("join")(_join)
    sio.on("leave")(_leave)
    sio.on("disconnect")(_disconnect)
