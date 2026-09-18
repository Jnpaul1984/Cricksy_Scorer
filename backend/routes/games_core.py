from __future__ import annotations

from typing import Annotated, Any, Literal, cast

from backend.routes import games as _games_impl  # contains create_game_impl
from backend.security import get_current_user_optional
from backend.services import school_competition_service
from backend.sql_app import crud, models, schemas
from backend.sql_app.database import get_db
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["games:core"])


class CreateGameRequest(BaseModel):
    team_a_name: str
    team_b_name: str
    # Allow either explicit player lists OR a players_per_team count for tests/clients
    players_a: list[str] | None = Field(None, min_length=0)
    players_b: list[str] | None = Field(None, min_length=0)
    players_per_team: int | None = Field(None, ge=1)

    match_type: Literal["limited", "multi_day", "custom"] = "limited"
    overs_limit: int | None = Field(None, ge=1, le=120)
    days_limit: int | None = Field(None, ge=1, le=7)
    overs_per_day: int | None = Field(None, ge=1, le=120)
    dls_enabled: bool = False
    interruptions: list[dict[str, Any]] = []  # type: ignore[assignment]

    # Make toss / decision optional for simpler test payloads; default behavior is safe
    toss_winner_team: str | None = None
    decision: Literal["bat", "bowl"] | None = None


@router.post("/games", response_model=schemas.Game)
async def create_game(
    payload: CreateGameRequest, db: Annotated[AsyncSession, Depends(get_db)]
) -> schemas.Game:
    # Delegate to the existing implementation to avoid duplication
    db_game = await _games_impl.create_game_impl(payload, db)
    return schemas.Game.model_validate(db_game, from_attributes=True)


@router.get("/games/{game_id}", response_model=schemas.Game)
async def get_game(
    game_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[models.User | None, Depends(get_current_user_optional)],
) -> schemas.Game:
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")
    try:
        await school_competition_service.require_school_game_member(
            db, game=db_game, user=current_user
        )
    except school_competition_service.SchoolCompetitionServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return cast(schemas.Game, db_game)
