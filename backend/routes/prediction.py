"""
API routes for win probability predictions.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.prediction_service import get_win_probability
from backend.sql_app.database import get_db
from backend.sql_app import crud

router = APIRouter(prefix="/predictions", tags=["predictions"])


@router.get("/games/{game_id}/win-probability")
async def get_game_win_probability(
    game_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get current win probability for a game.

    Returns real-time prediction based on current match state.

    Args:
        game_id: UUID of the game
        db: Database session

    Returns:
        Dictionary with win probabilities and factors

    Raises:
        HTTPException: If game not found
    """
    # Fetch game from database
    game = await crud.get_game(db, game_id)

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Build game state dictionary
    game_state = {
        "current_inning": game.current_inning,
        "total_runs": game.total_runs,
        "total_wickets": game.total_wickets,
        "overs_completed": game.overs_completed,
        "balls_this_over": game.balls_this_over,
        "overs_limit": game.overs_limit,
        "target": game.target,
        "match_type": game.match_type,
    }

    # Calculate prediction
    prediction = get_win_probability(game_state)

    # Add team names to response
    prediction["batting_team"] = game.batting_team_name
    prediction["bowling_team"] = game.bowling_team_name
    prediction["game_id"] = game_id

    return prediction
