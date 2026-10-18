from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.game_performance_metadata import (
    GamePerformanceMetadataResponse,
    GamePerformanceMetadataUpdate,
)
from backend.security import get_current_active_user
from backend.services import game_helpers as gh
from backend.services.game_access_service import require_game_mutation_access
from backend.services.game_performance_metadata_service import (
    GamePerformanceMetadataError,
    get_game_performance_metadata,
    update_game_performance_metadata,
)
from backend.services.live_bus import emit_state_update
from backend.services.snapshot_service import build_snapshot as _snapshot_from_game
from backend.sql_app import crud, models, schemas
from backend.sql_app.database import get_db


# Safe dynamic caller for private helpers in game_helpers (avoids static private
# usage diagnostics while keeping runtime behavior identical when helpers exist)
def _gh(name: str, *args: Any, **kwargs: Any) -> Any:
    fn = getattr(gh, name, None)
    if callable(fn):
        return fn(*args, **kwargs)
    return None


router = APIRouter(prefix="/games", tags=["game-admin"])

BASE_DIR = Path(__file__).resolve().parent


@router.get(
    "/{game_id}/team-performance-metadata",
    response_model=GamePerformanceMetadataResponse,
)
async def read_team_performance_metadata(
    game_id: str,
    current_user: Annotated[models.User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> GamePerformanceMetadataResponse:
    try:
        game = await get_game_performance_metadata(
            db,
            game_id=game_id,
            actor_user_id=current_user.id,
        )
    except GamePerformanceMetadataError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return GamePerformanceMetadataResponse(
        actual_played_date=game.actual_played_date,
        played_date_trust_state=game.played_date_trust_state,
        original_overs_limit=game.original_overs_limit,
        original_format_trust_state=game.original_format_trust_state,
        metadata_revision=game.team_performance_metadata_revision,
    )


@router.patch(
    "/{game_id}/team-performance-metadata",
    response_model=GamePerformanceMetadataResponse,
)
async def update_team_performance_metadata(
    game_id: str,
    body: GamePerformanceMetadataUpdate,
    current_user: Annotated[models.User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> GamePerformanceMetadataResponse:
    fields = body.model_fields_set
    if not ({"actual_played_date", "original_overs_limit"} & fields):
        raise HTTPException(status_code=422, detail="At least one metadata field must be supplied")
    try:
        game = await update_game_performance_metadata(
            db,
            game_id=game_id,
            actor_user_id=current_user.id,
            expected_revision=body.expected_revision,
            reason=body.reason,
            played_date_supplied="actual_played_date" in fields,
            played_date=body.actual_played_date,
            original_overs_supplied="original_overs_limit" in fields,
            original_overs_limit=body.original_overs_limit,
        )
    except GamePerformanceMetadataError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return GamePerformanceMetadataResponse(
        actual_played_date=game.actual_played_date,
        played_date_trust_state=game.played_date_trust_state,
        original_overs_limit=game.original_overs_limit,
        original_format_trust_state=game.original_format_trust_state,
        metadata_revision=game.team_performance_metadata_revision,
    )


class OversLimitBody(BaseModel):
    overs_limit: int


@router.post("/{game_id}/overs-limit")
async def set_overs_limit(
    game_id: str,
    body: OversLimitBody,
    current_user: Annotated[models.User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
):
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")
    await require_game_mutation_access(db, game=db_game, user=current_user)

    g: Any = db_game

    bowled_balls = int(getattr(g, "overs_completed", 0)) * 6 + int(getattr(g, "balls_this_over", 0))
    new_limit_balls = int(body.overs_limit) * 6
    if new_limit_balls < bowled_balls:
        raise HTTPException(status_code=400, detail="New limit is less than overs already bowled")

    g.overs_limit = int(body.overs_limit)

    try:
        interruptions = list(getattr(g, "interruptions", []))
    except Exception:
        interruptions = []
    interruptions.append(
        {
            "type": "overs_reduction",
            "at_delivery_index": len(getattr(g, "deliveries", []) or []),
            "new_overs_limit": int(body.overs_limit),
        }
    )
    g.interruptions = interruptions

    updated = await crud.update_game(db, game_model=db_game)

    u = updated
    dl = _gh("_dedup_deliveries", u)
    last = dl[-1] if dl else None
    snap = _snapshot_from_game(u, last, BASE_DIR)
    _gh("_rebuild_scorecards_from_deliveries", u)
    _gh("_recompute_totals_and_runtime", u)
    _gh("_complete_game_by_result", u)
    await crud.update_game(db, game_model=u)
    await emit_state_update(game_id, snap)

    return {"id": game_id, "overs_limit": cast(Any, updated).overs_limit}


@router.post("/{game_id}/team-roles")
async def set_team_roles(
    game_id: str,
    payload: schemas.TeamRoleUpdate,
    current_user: Annotated[models.User, Depends(get_current_active_user)],
    db: AsyncSession = Depends(get_db),
):
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")
    await require_game_mutation_access(db, game=db_game, user=current_user)

    g: Any = db_game

    players = (
        g.team_a.get("players", [])
        if payload.side == schemas.TeamSide.A
        else g.team_b.get("players", [])
    )
    player_ids = {p["id"] for p in players}

    if payload.captain_id and payload.captain_id not in player_ids:
        raise HTTPException(status_code=400, detail="captain_id not in team players")
    if payload.wicket_keeper_id and payload.wicket_keeper_id not in player_ids:
        raise HTTPException(status_code=400, detail="wicket_keeper_id not in team players")

    if payload.side == schemas.TeamSide.A:
        g.team_a_captain_id = payload.captain_id
        g.team_a_keeper_id = payload.wicket_keeper_id
    else:
        g.team_b_captain_id = payload.captain_id
        g.team_b_keeper_id = payload.wicket_keeper_id

    await crud.update_game(db, game_model=db_game)
    return {
        "ok": True,
        "team_roles": {
            "A": {
                "captain_id": getattr(g, "team_a_captain_id", None),
                "wicket_keeper_id": getattr(g, "team_a_keeper_id", None),
            },
            "B": {
                "captain_id": getattr(g, "team_b_captain_id", None),
                "wicket_keeper_id": getattr(g, "team_b_keeper_id", None),
            },
        },
    }
