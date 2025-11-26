from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config import settings
from backend.routes.games_core import CreateGameRequest
from backend.services import game_helpers as gh
from backend.services.live_bus import emit_state_update
from backend.services.snapshot_service import build_snapshot
from backend.services import game_service
from backend.sql_app import crud, models
from backend.sql_app.database import get_db

BASE_DIR = Path(__file__).resolve().parent

router = APIRouter(prefix="/testing", tags=["testing"])


@router.post("/create-scoreable-game")
async def create_scoreable_game(
    db: Annotated[AsyncSession, Depends(get_db)]
) -> dict[str, str]:
    """
    Test helper that seeds a scoreable game (first over ready, openers set).
    **Enabled only in non-production environments.**
    """
    if settings.ENV.lower() == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Testing endpoints are disabled in production environments.",
        )

    payload = CreateGameRequest(
        team_a_name="Cypress Test Team Alpha",
        team_b_name="Cypress Test Team Beta",
        players_per_team=11,
        match_type="limited",
        overs_limit=20,
    )

    db_game: models.Game = await game_service.create_game(payload, db)

    if not db_game:
        raise HTTPException(status_code=500, detail="Unable to create game")

    # Determine batting/bowling team order
    batting_side = (
        db_game.team_a
        if db_game.batting_team_name == db_game.team_a.get("name")
        else db_game.team_b
    )
    bowling_side = db_game.team_b if batting_side is db_game.team_a else db_game.team_a

    if not batting_side.get("players") or not bowling_side.get("players"):
        raise HTTPException(status_code=500, detail="Game lacks enough players")

    striker_id = str(batting_side["players"][0]["id"])
    non_striker_id = str(batting_side["players"][1]["id"])
    bowler_id = str(bowling_side["players"][0]["id"])

    db_game.current_striker_id = striker_id
    db_game.current_non_striker_id = non_striker_id
    db_game.current_bowler_id = bowler_id
    db_game.current_over_balls = 0
    db_game.balls_this_over = 0
    db_game.overs_completed = 0
    db_game.total_runs = 0
    db_game.total_wickets = 0
    db_game.needs_new_over = False
    db_game.needs_new_batter = False
    # db_game.needs_new_innings is computed from status
    db_game.pending_new_over = False
    db_game.mid_over_change_used = False
    db_game.status = models.GameStatus.in_progress
    # db_game.is_game_over is computed from status
    db_game.completed_at = None

    gh._rebuild_scorecards_from_deliveries(db_game)
    gh._recompute_totals_and_runtime(db_game)

    updated_game = await crud.update_game(db, game_model=db_game)

    snapshot = build_snapshot(updated_game, None, BASE_DIR)
    await emit_state_update(str(updated_game.id), snapshot)

    return {
        "game_id": str(updated_game.id),
        "batting_team_name": updated_game.batting_team_name or "",
        "bowling_team_name": updated_game.bowling_team_name or "",
    }
