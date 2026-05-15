"""
API routes for win probability predictions.
"""

from __future__ import annotations

from typing import Any

from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType
from backend.services.prediction_service import get_win_probability
from backend.sql_app import crud
from backend.sql_app.database import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/predictions", tags=["predictions"])

# ---------------------------------------------------------------------------
# Advisory metadata injected into every prediction response (Phase 8)
# ---------------------------------------------------------------------------

_PREDICTION_LIMITATIONS = [
    "Advisory only — not official match truth.",
    "Prediction accuracy increases as the match progresses.",
    "Rule-based fallback is used when ML model is unavailable.",
    "Does not account for weather, pitch, or tactical changes.",
]


@router.get("/games/{game_id}/win-probability")
async def get_game_win_probability(
    game_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get current win probability for a game.

    Returns real-time prediction based on current match state.

    Phase 8: Response now includes ``ai_metadata`` with ``confidence_score``
    and ``limitations`` to make the advisory nature of the output explicit.

    Args:
        game_id: UUID of the game
        db: Database session

    Returns:
        Dictionary with win probabilities, factors, and AI advisory metadata.

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

    # Phase 8 — attach advisory AI metadata so consumers can see this is
    # non-authoritative and inspect confidence / limitations.
    raw_confidence: float | None = prediction.get("confidence")
    confidence_score: float | None = (
        round(raw_confidence / 100.0, 4) if isinstance(raw_confidence, (int, float)) else None
    )
    ai_meta = AiOutputMetadata(
        output_type=AiOutputType.INSIGHT,
        is_official_truth=False,
        confidence_score=confidence_score,
        limitations=_PREDICTION_LIMITATIONS,
    )
    prediction["ai_metadata"] = ai_meta.model_dump()

    return prediction
