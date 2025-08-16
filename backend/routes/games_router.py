from __future__ import annotations

from typing import Any, Dict, Set, Optional, Sequence, TypedDict, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from sql_app import models, schemas
from sql_app.database import get_db  # async generator -> AsyncSession

router = APIRouter(prefix="/games", tags=["games"])


# --- Typed JSON helpers to satisfy Pylance ---
class PlayerJSON(TypedDict, total=False):
    id: str  # UUID as string is fine for transport/JSON
    name: str

class TeamJSON(TypedDict, total=False):
    name: str
    players: Sequence[PlayerJSON]


def _ids_from_team_json(team_json: Optional[Dict[str, Any]]) -> Set[str]:
    """
    Expected shape in DB JSON:
      {
        "name": "Team A",
        "players": [{"id": "<uuid>", "name": "..."}, ...]
      }
    """
    if not team_json:
        return set()

    # Keep this cast: it tells Pylance 'players' is a list of PlayerJSON
    players: Sequence[PlayerJSON] = cast(Sequence[PlayerJSON], team_json.get("players") or [])

    ids: Set[str] = set()
    for p in players:
        pid = p.get("id")          
        if isinstance(pid, str) and pid:
            ids.add(pid)
    return ids



@router.post("/{game_id}/playing-xi", response_model=schemas.PlayingXIResponse)
async def set_playing_xi(
    game_id: UUID,
    payload: schemas.PlayingXIRequest,
    db: AsyncSession = Depends(get_db),
) -> schemas.PlayingXIResponse:
    # Fetch game (async)
    result = await db.execute(select(models.Game).where(models.Game.id == str(game_id)))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Typed JSON copies to keep Pylance happy
    team_a_json: Dict[str, Any] = cast(Dict[str, Any], (game.team_a or {})).copy()
    team_b_json: Dict[str, Any] = cast(Dict[str, Any], (game.team_b or {})).copy()

    allowed_a = _ids_from_team_json(team_a_json)
    allowed_b = _ids_from_team_json(team_b_json)

    req_a = set(map(str, payload.team_a))
    req_b = set(map(str, payload.team_b))

    if not req_a.issubset(allowed_a):
        unknown = sorted(req_a - allowed_a)
        raise HTTPException(status_code=400, detail={"error": "Unknown players in team A XI", "ids": unknown})

    if not req_b.issubset(allowed_b):
        unknown = sorted(req_b - allowed_b)
        raise HTTPException(status_code=400, detail={"error": "Unknown players in team B XI", "ids": unknown})

    # Persist XI lists into JSON blobs
    team_a_json["playing_xi"] = list(req_a)
    team_b_json["playing_xi"] = list(req_b)

    # Assign back to ORM instance
    setattr(game, "team_a", team_a_json)
    setattr(game, "team_b", team_b_json)

    # Captain / Keeper columns (Text/nullable on your model)
    setattr(game, "team_a_captain_id", str(payload.captain_a) if payload.captain_a else None)
    setattr(game, "team_a_keeper_id",  str(payload.keeper_a)  if payload.keeper_a  else None)
    setattr(game, "team_b_captain_id", str(payload.captain_b) if payload.captain_b else None)
    setattr(game, "team_b_keeper_id",  str(payload.keeper_b)  if payload.keeper_b  else None)

    await db.commit()

    return schemas.PlayingXIResponse(ok=True, game_id=game_id)


# Optional alias for underscore path
@router.post("/{game_id}/playing_xi", response_model=schemas.PlayingXIResponse)
async def set_playing_xi_alias(
    game_id: UUID,
    payload: schemas.PlayingXIRequest,
    db: AsyncSession = Depends(get_db),
) -> schemas.PlayingXIResponse:
    return await set_playing_xi(game_id, payload, db)
