# routes/interruptions.py
from __future__ import annotations
import datetime as dt
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

# â¬‡ï¸ change these to match your project
from backend.sql_app.database import get_db
from backend.sql_app.models import Game

UTC = getattr(dt, "UTC", dt.timezone.utc)
# â¬†ï¸ change these to match your project

router = APIRouter(prefix="/games", tags=["interruptions"])

# ---------- Schemas ----------
Kind = Literal["weather", "light", "injury", "other"]

class InterruptionStart(BaseModel):
    kind: Kind = "weather"
    note: Optional[str] = None
    at_utc: Optional[dt.datetime] = None

class InterruptionStop(BaseModel):
    kind: Optional[Kind] = None
    at_utc: Optional[dt.datetime] = None

# Compat â€œupsertâ€ payload: POST /games/{id}/interruptions
class InterruptionUpsert(BaseModel):
    # action/op/status or boolean flags, any of these work
    action: Optional[Literal["start", "stop", "begin", "end"]] = None
    op: Optional[Literal["start", "stop", "begin", "end"]] = None
    status: Optional[Literal["start", "stop"]] = None
    start: Optional[bool] = None
    stop: Optional[bool] = None

    kind: Optional[Kind] = "weather"
    type: Optional[Kind] = None  # tolerate { type: "weather" }
    note: Optional[str] = None
    at_utc: Optional[dt.datetime] = None

# ---------- Helpers ----------
def _now_iso(value: Optional[dt.datetime]) -> str:
    if value is None:
        value = dt.datetime.now(UTC)
    if value.tzinfo is None:
        value = value.replace(tzinfo=UTC)
    return value.isoformat()

def _ensure_game(game: Optional[Game]) -> Game:
    if not game:
        raise HTTPException(404, "Game not found")
    return game

# ---------- helpers ----------

def _is_open(it: Dict[str, Any]) -> bool:
    # Only open when the *key exists* and is explicitly null/empty
    end_present = ("ended_at" in it) or ("endedAt" in it) or ("end" in it)
    if not end_present:
        return False
    end_val = it.get("ended_at", it.get("endedAt", it.get("end", None)))
    return end_val is None or end_val == ""

def _last_open_index(history: List[Dict[str, Any]], kind: Optional[Kind]) -> Optional[int]:
    for i in range(len(history) - 1, -1, -1):
        it = history[i] or {}
        if _is_open(it) and (kind is None or it.get("kind") == kind):
            return i
    return None

def _normalize_history(history: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    # One-time safety: legacy items without ended_at are treated as CLOSED.
    out: List[Dict[str, Any]] = []
    for it in history:
        it = dict(it or {})
        if ("ended_at" not in it) and ("endedAt" not in it) and ("end" not in it):
            # mark closed with a non-null value so it won't be considered open
            it["ended_at"] = it.get("endedAt") or it.get("end") or (it.get("started_at") or "")
        out.append(it)
    return out

# ---------- core ----------

def _start_core(game: Game, kind: Kind, note: Optional[str], at_utc: Optional[dt.datetime]) -> List[Dict[str, Any]]:
    history: List[Dict[str, Any]] = _normalize_history(list(game.interruptions or []))
    if _last_open_index(history, kind) is not None:
        raise HTTPException(400, f"{kind} interruption already active")
    history.append({
        "id": uuid4().hex,
        "kind": kind,
        "started_at": _now_iso(at_utc),
        "ended_at": None,  # <-- explicit null while active
        "note": note or "",
    })
    game.interruptions = history
    return history

def _stop_core(game: Game, kind: Optional[Kind], at_utc: Optional[dt.datetime]) -> List[Dict[str, Any]]:
    history: List[Dict[str, Any]] = _normalize_history(list(game.interruptions or []))
    idx = _last_open_index(history, kind)
    if idx is None:
        raise HTTPException(400, "No active interruption to stop")
    history[idx]["ended_at"] = _now_iso(at_utc)  # <-- close with timestamp
    game.interruptions = history
    return history

# ---------- GET route (normalize before returning) ----------

@router.get("/{game_id}/interruptions")
async def list_interruptions(game_id: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    game = _ensure_game(await db.scalar(select(Game).where(Game.id == game_id)))
    game.interruptions = _normalize_history(list(game.interruptions or []))
    return {"ok": True, "interruptions": game.interruptions or []}

@router.post("/{game_id}/interruptions/start")
async def start_interruption(
    game_id: str,
    payload: InterruptionStart,
    request: Request,                                 # â¬…ï¸ add Request
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    game = _ensure_game(await db.scalar(select(Game).where(Game.id == game_id)))
    _start_core(game, payload.kind, payload.note, payload.at_utc)
    await db.commit()
    await db.refresh(game)

    # â¬‡ï¸ broadcast so widgets refresh immediately
    try:
        sio = request.app.state.sio
        await sio.emit("interruptions:update", {"game_id": game_id}, room=game_id)
    except Exception:
        pass

    return {"ok": True, "interruptions": game.interruptions}


@router.post("/{game_id}/interruptions/stop")
async def stop_interruption(
    game_id: str,
    payload: InterruptionStop,
    request: Request,                                 # â¬…ï¸ add Request
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    game = _ensure_game(await db.scalar(select(Game).where(Game.id == game_id)))
    _stop_core(game, payload.kind, payload.at_utc)
    await db.commit()
    await db.refresh(game)

    # â¬‡ï¸ broadcast so widgets refresh immediately
    try:
        sio = request.app.state.sio
        await sio.emit("interruptions:update", {"game_id": game_id}, room=game_id)
    except Exception:
        pass

    return {"ok": True, "interruptions": game.interruptions}


@router.post("/{game_id}/interruptions")
async def upsert_interruption(
    game_id: str,
    payload: InterruptionUpsert,
    request: Request,                                 # â¬…ï¸ add Request
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    game = _ensure_game(await db.scalar(select(Game).where(Game.id == game_id)))

    act = (payload.action or payload.op or payload.status or
           ("start" if payload.start else None) or
           ("stop" if payload.stop else None))
    if act is None:
        raise HTTPException(422, "Provide 'action' ('start'|'stop') or boolean 'start'/'stop'")

    kind: Kind = (payload.kind or payload.type or "weather")
    if act in ("start", "begin"):
        _start_core(game, kind, payload.note, payload.at_utc)
    else:
        _stop_core(game, kind, payload.at_utc)

    await db.commit()
    await db.refresh(game)

    # â¬‡ï¸ broadcast so widgets refresh immediately
    try:
        sio = request.app.state.sio
        await sio.emit("interruptions:update", {"game_id": game_id}, room=game_id)
    except Exception:
        pass

    return {"ok": True, "interruptions": game.interruptions}


