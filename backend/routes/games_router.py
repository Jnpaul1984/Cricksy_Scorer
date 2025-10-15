from __future__ import annotations

from typing import Any, Dict, Set, Optional, Sequence, TypedDict, cast
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import SQLAlchemyError
from sql_app import models, schemas
from sql_app.database import get_db  # async generator -> AsyncSession

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
    team_a_json: Dict[str, Any] = (game.team_a or {}).copy()
    team_b_json: Dict[str, Any] = (game.team_b or {}).copy()

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

@router.get("/{game_id}/results", response_model=schemas.MatchResult)
async def get_game_results(game_id: UUID, db: AsyncSession = Depends(get_db)) -> schemas.MatchResult:
    """Retrieve results for a specific game"""
    result = await db.execute(select(models.Game).where(models.Game.id == str(game_id)))
    game = result.scalar_one_or_none()
    if not game or not game.result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Results not found for the game"
        )
    # Ensure result is a dict with string keys and all required fields
    import json
    from datetime import datetime
    if type(game.result) is str:
        try:
            result_dict = json.loads(game.result)
        except Exception:
            result_dict = {}
    elif isinstance(game.result, dict):
        result_dict = game.result
    else:
        result_dict = {}

    required_fields = ["match_id", "winner", "team_a_score", "team_b_score"]
    missing = [field for field in required_fields if field not in result_dict]
    if missing:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Missing fields in result: {', '.join(missing)}"
        )
        
    # Convert types as needed before passing to MatchResult
    processed_dict = {
        "match_id": result_dict.get("match_id"),
        "winner": result_dict.get("winner"),
        "team_a_score": int(result_dict.get("team_a_score")),
        "team_b_score": int(result_dict.get("team_b_score")),
        "winner_team_id": result_dict.get("winner_team_id"),
        "winner_team_name": result_dict.get("winner_team_name")
    }
    
    # Handle optional fields with proper type conversion
    if "method" in result_dict:
        from sql_app.schemas import MatchMethod
        method_str = result_dict.get("method")
        processed_dict["method"] = MatchMethod(method_str) if method_str else None
        
    if "margin" in result_dict and result_dict.get("margin") is not None:
        processed_dict["margin"] = int(result_dict.get("margin"))
        
    if "result_text" in result_dict:
        processed_dict["result_text"] = result_dict.get("result_text")
        
    if "completed_at" in result_dict and result_dict.get("completed_at"):
        try:
            processed_dict["completed_at"] = datetime.fromisoformat(result_dict.get("completed_at"))
        except (ValueError, TypeError):
            pass
            
    return schemas.MatchResult(**processed_dict)


@router.post("/{game_id}/results", response_model=schemas.MatchResult, status_code=status.HTTP_201_CREATED)
async def post_game_results(
    game_id: UUID,
    payload: schemas.MatchResultRequest,
    db: AsyncSession = Depends(get_db)
) -> schemas.MatchResult:
    """Creates or updates results for a specific game"""
    try:
        result = await db.execute(select(models.Game).where(models.Game.id == str(game_id)))
        game = result.scalar_one_or_none()
        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Game not found"
            )

        # Update the game's result
        import json
        result_dict = {
            "match_id": str(payload.match_id),
            "winner": str(payload.winner) if payload.winner is not None else None,
            "team_a_score": int(payload.team_a_score),
            "team_b_score": payload.team_b_score,
            "winner_team_id": str(getattr(payload, "winner_team_id", "")) if getattr(payload, "winner_team_id", None) is not None else None,
            "winner_team_name": str(getattr(payload, "winner_team_name", "")) if getattr(payload, "winner_team_name", None) is not None else None,
            "method": getattr(payload, "method", None),
            "margin": int(getattr(payload, "margin", 0)) if getattr(payload, "margin", None) is not None else None,
            "result_text": str(getattr(payload, "result_text", "")) if getattr(payload, "result_text", None) is not None else None,
            "completed_at": getattr(payload, "completed_at", None)
        }
        game.result = json.dumps(result_dict)
        await db.commit()
        # Only pass fields that MatchResult expects, with correct types
        return schemas.MatchResult(
            match_id=result_dict["match_id"], # pyright: ignore[reportCallIssue]
            winner=result_dict["winner"], # pyright: ignore[reportCallIssue]
            team_a_score=result_dict["team_a_score"], # pyright: ignore[reportCallIssue]
            winner_team_id=result_dict["winner_team_id"],
            winner_team_name=result_dict["winner_team_name"],
            method=result_dict["method"],
            margin=result_dict["margin"],
            result_text=result_dict["result_text"],
            completed_at=result_dict["completed_at"]
        )
    except SQLAlchemyError:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred updating the game results"
        )