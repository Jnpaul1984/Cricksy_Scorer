from __future__ import annotations

import datetime as dt
import json
from typing import (Annotated, Any, Dict, Optional, Sequence, Set, TypedDict,
                    cast)
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.sql_app import models, schemas
from backend.sql_app.database import get_db  # async generator -> AsyncSession

UTC = getattr(dt, "UTC", dt.timezone.utc)

# Ensure schemas.MatchResultRequest is imported and defined
# If not, add the following to sql_app/schemas.py:
# class MatchResultRequest(BaseModel):
#     match_id: UUID
#     winner: str
#     team_a_score: int
#     team_b_score: int

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
    players: Sequence[PlayerJSON] = cast(
        Sequence[PlayerJSON], team_json.get("players") or []
    )

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
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.PlayingXIResponse:
    # Fetch game (async)
    result = await db.execute(select(models.Game).where(models.Game.id == str(game_id)))
    game = result.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Typed JSON copies to keep Pylance happy
    team_a_json: Dict[str, Any] = (game.team_a or {}).copy()
    team_b_json: Dict[str, Any] = (game.team_b or {}).copy()

    allowed_a = _ids_from_team_json(team_a_json)
    allowed_b = _ids_from_team_json(team_b_json)

    req_a = set(map(str, payload.team_a))
    req_b = set(map(str, payload.team_b))

    if not req_a.issubset(allowed_a):
        unknown = sorted(req_a - allowed_a)
        raise HTTPException(
            status_code=400,
            detail={"error": "Unknown players in team A XI", "ids": unknown},
        )

    if not req_b.issubset(allowed_b):
        unknown = sorted(req_b - allowed_b)
        raise HTTPException(
            status_code=400,
            detail={"error": "Unknown players in team B XI", "ids": unknown},
        )

    # Persist XI lists into JSON blobs
    team_a_json["playing_xi"] = list(req_a)
    team_b_json["playing_xi"] = list(req_b)

    # Assign back to ORM instance
    setattr(game, "team_a", team_a_json)
    setattr(game, "team_b", team_b_json)

    # Captain / Keeper columns (Text/nullable on your model)
    setattr(
        game, "team_a_captain_id", str(payload.captain_a) if payload.captain_a else None
    )
    setattr(
        game, "team_a_keeper_id", str(payload.keeper_a) if payload.keeper_a else None
    )
    setattr(
        game, "team_b_captain_id", str(payload.captain_b) if payload.captain_b else None
    )
    setattr(
        game, "team_b_keeper_id", str(payload.keeper_b) if payload.keeper_b else None
    )

    await db.commit()

    return schemas.PlayingXIResponse(ok=True, game_id=game_id)


# Optional alias for underscore path
@router.post("/{game_id}/playing_xi", response_model=schemas.PlayingXIResponse)
async def set_playing_xi_alias(
    game_id: UUID,
    payload: schemas.PlayingXIRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.PlayingXIResponse:
    return await set_playing_xi(game_id, payload, db)


@router.get("/search")
async def search_games(
    db: Annotated[AsyncSession, Depends(get_db)],
    team_a: Optional[str] = None,
    team_b: Optional[str] = None,
) -> Sequence[Dict[str, Any]]:
    """
    Minimal search by team names (case-insensitive contains) without requiring game IDs.
    Filters in Python for portability; optimize later with JSONB paths if needed.
    """
    res = await db.execute(select(models.Game))
    rows = list(res.scalars().all())

    def _name(x: Dict[str, Any] | None) -> str:
        try:
            return str((x or {}).get("name") or "")
        except Exception:
            return ""

    ta_f = (team_a or "").strip().lower()
    tb_f = (team_b or "").strip().lower()

    out: list[Dict[str, Any]] = []
    for g in rows:
        ta = _name(getattr(g, "team_a", {}))
        tb = _name(getattr(g, "team_b", {}))
        ta_l = ta.lower()
        tb_l = tb.lower()

        ok = True
        if ta_f:
            ok = ok and (ta_f in ta_l or ta_f in tb_l)
        if tb_f:
            ok = ok and (tb_f in ta_l or tb_f in tb_l)
        if not ok:
            continue

        out.append(
            {
                "id": getattr(g, "id", None),
                "team_a_name": ta,
                "team_b_name": tb,
                "status": str(getattr(g, "status", "")),
                "current_inning": getattr(g, "current_inning", None),
                "total_runs": getattr(g, "total_runs", None),
                "total_wickets": getattr(g, "total_wickets", None),
            }
        )

    return out


@router.get("/{game_id}/results", response_model=schemas.MatchResult)
async def get_game_results(
    game_id: UUID, db: Annotated[AsyncSession, Depends(get_db)]
) -> schemas.MatchResult:
    """Retrieve results for a specific game.

    Decodes the stored JSON and returns it mapped to schemas.MatchResult
    for a consistent response shape.
    """
    res = await db.execute(select(models.Game).where(models.Game.id == str(game_id)))
    game = res.scalar_one_or_none()
    if not game or not game.result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Results not found for the game",
        )

    payload: dict[str, Any]
    raw = game.result
    try:
        payload = json.loads(raw)
    except Exception:
        payload = {}

    return schemas.MatchResult(
        winner_team_id=(
            str(payload.get("winner_team_id"))
            if payload.get("winner_team_id") is not None
            else None
        ),
        winner_team_name=(
            str(payload.get("winner_team_name"))
            if payload.get("winner_team_name") is not None
            else None
        ),
        method=payload.get("method"),
        margin=(
            int(payload.get("margin"))
            if payload.get("margin", None) is not None
            else None
        ),
        result_text=(
            str(payload.get("result_text"))
            if payload.get("result_text") is not None
            else None
        ),
        completed_at=payload.get("completed_at"),
    )


@router.post(
    "/{game_id}/results",
    response_model=schemas.MatchResult,
    status_code=status.HTTP_201_CREATED,
)
async def post_game_results(
    game_id: UUID,
    payload: schemas.MatchResultRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> schemas.MatchResult:
    """Creates or updates results for a specific game"""
    try:
        result = await db.execute(
            select(models.Game).where(models.Game.id == str(game_id))
        )
        game = result.scalar_one_or_none()
        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND, detail="Game not found"
            )

        # Update the game's result
        result_dict = {
            "match_id": str(payload.match_id),
            "winner": str(payload.winner) if payload.winner is not None else None,
            "team_a_score": int(payload.team_a_score),
            "team_b_score": payload.team_b_score,
            "winner_team_id": (
                str(getattr(payload, "winner_team_id", ""))
                if getattr(payload, "winner_team_id", None) is not None
                else None
            ),
            "winner_team_name": (
                str(getattr(payload, "winner_team_name", ""))
                if getattr(payload, "winner_team_name", None) is not None
                else None
            ),
            "method": getattr(payload, "method", None),
            "margin": (
                int(getattr(payload, "margin", 0))
                if getattr(payload, "margin", None) is not None
                else None
            ),
            "result_text": (
                str(getattr(payload, "result_text", ""))
                if getattr(payload, "result_text", None) is not None
                else None
            ),
            "completed_at": getattr(payload, "completed_at", None),
        }
        # Persist result payload
        game.result = json.dumps(result_dict)
        # Mark game as completed so frontends show the banner immediately
        try:
            game.status = models.GameStatus.completed  # type: ignore[assignment]
        except Exception:
            # Fallback as string if enum assignment differs
            setattr(
                game, "status", getattr(models.GameStatus, "completed", "completed")
            )
        setattr(game, "is_game_over", True)
        try:
            setattr(game, "completed_at", dt.datetime.now(UTC))
        except Exception:
            # If timezone not accepted, store naive UTC
            setattr(game, "completed_at", dt.datetime.now(UTC))

        await db.commit()
        # Only pass fields that MatchResult expects, with correct types
        return schemas.MatchResult(
            match_id=result_dict["match_id"],  # pyright: ignore[reportCallIssue]
            winner=result_dict["winner"],  # pyright: ignore[reportCallIssue]
            team_a_score=result_dict[
                "team_a_score"
            ],  # pyright: ignore[reportCallIssue]
            winner_team_id=result_dict["winner_team_id"],
            winner_team_name=result_dict["winner_team_name"],
            method=result_dict["method"],
            margin=result_dict["margin"],
            result_text=result_dict["result_text"],
            completed_at=result_dict["completed_at"],
        )
    except SQLAlchemyError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred updating the game results",
        ) from e


@router.get("/results")
async def list_game_results(
    db: Annotated[AsyncSession, Depends(get_db)],
) -> Sequence[Dict[str, Any]]:
    """Return all games that have a stored result as simple dicts."""
    res = await db.execute(select(models.Game).where(models.Game.result.isnot(None)))
    rows = res.scalars().all()

    out: list[Dict[str, Any]] = []
    for g in rows:
        raw = g.result
        if not raw:
            continue
        try:
            data = (
                json.loads(raw)
                if isinstance(raw, str)
                else (raw if isinstance(raw, dict) else {})
            )
        except Exception:
            data = {}

        # Ensure minimal keys exist for the caller expectations
        item: Dict[str, Any] = {
            "match_id": str(data.get("match_id", g.id)),
            "winner": data.get("winner"),
            "team_a_score": int(data.get("team_a_score") or 0),
            "team_b_score": int(data.get("team_b_score") or 0),
        }
        # Include any extra fields if present (non-breaking for clients)
        for k in (
            "winner_team_id",
            "winner_team_name",
            "method",
            "margin",
            "result_text",
            "completed_at",
        ):
            if k in data:
                item[k] = data[k]

        out.append(item)

    return out
