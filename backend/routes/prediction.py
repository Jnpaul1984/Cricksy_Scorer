"""
API routes for win probability predictions.
"""

from __future__ import annotations

from typing import Any

from backend.domain.ai_boundary import AiOutputMetadata, AiOutputType, AiSourceReference
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


def _derive_match_phase(overs_completed: int, overs_limit: int | None) -> str | None:
    """Return a user-facing phase label for the current match state."""
    if overs_limit is None:
        return None

    if overs_limit <= 20:
        if overs_completed < 6:
            return "Powerplay"
        if overs_completed < 15:
            return "Middle overs"
        return "Death overs"

    if overs_completed < 10:
        return "Powerplay"
    if overs_completed < 40:
        return "Middle overs"
    return "Death overs"


def _prediction_method_label(method: str | None) -> str | None:
    """Normalize prediction-method identifiers into evidence labels."""
    if not method:
        return None
    if method.startswith("ml_"):
        return "Data source: Win-probability model"
    if method.startswith("rule_"):
        return "Data source: Rule-based fallback"
    return f"Data source: {method.replace('_', ' ')}"


def _build_prediction_source_refs(game: Any, prediction: dict[str, Any], game_id: str) -> list[AiSourceReference]:
    """Build compact evidence references for the advisory prediction payload."""
    factors = prediction.get("factors")
    factor_map = factors if isinstance(factors, dict) else {}
    refs: list[AiSourceReference] = [
        AiSourceReference(
            type="match",
            id=game_id,
            label=f"Match: {game.batting_team_name or 'Batting Team'} vs {game.bowling_team_name or 'Bowling Team'}",
        ),
        AiSourceReference(
            type="innings",
            id=f"innings_{game.current_inning}",
            label=f"Innings {game.current_inning}",
        ),
    ]

    phase_label = _derive_match_phase(int(game.overs_completed or 0), game.overs_limit)
    if phase_label:
        refs.append(
            AiSourceReference(
                type="phase",
                id=phase_label.lower().replace(" ", "_"),
                label=phase_label,
            )
        )

    if game.target:
        refs.append(
            AiSourceReference(
                type="metric",
                id="target",
                label=f"Target: {game.target}",
            )
        )

    metric_labels = {
        "current_run_rate": "Current RR",
        "required_run_rate": "Required RR",
        "wickets_remaining": "Wickets remaining",
        "projected_score": "Projected score",
        "par_score": "Par score",
    }
    for key, label in metric_labels.items():
        value = factor_map.get(key)
        if value is None:
            continue
        rendered = f"{value:.2f}" if isinstance(value, float) else str(value)
        refs.append(
            AiSourceReference(
                type="metric",
                id=key,
                label=f"{label}: {rendered}",
            )
        )

    method_label = _prediction_method_label(factor_map.get("prediction_method"))
    if method_label:
        refs.append(
            AiSourceReference(
                type="data_source",
                id=str(factor_map.get("prediction_method")),
                label=method_label,
            )
        )

    return refs


def _build_prediction_grounding_summary(source_refs: list[AiSourceReference]) -> str | None:
    """Summarize the key deterministic context behind the prediction."""
    labels = [ref.label for ref in source_refs]
    if not labels:
        return None

    summary_bits: list[str] = ["live match state"]
    if any(label.startswith("Innings ") for label in labels):
        summary_bits.append("innings context")
    if any(label == "Powerplay" or label == "Middle overs" or label == "Death overs" for label in labels):
        summary_bits.append("phase context")
    if any(label.startswith("Wickets remaining:") for label in labels):
        summary_bits.append("wickets remaining")
    if any(label.startswith("Current RR:") or label.startswith("Required RR:") for label in labels):
        summary_bits.append("run-rate pressure")
    if any(label.startswith("Data source: Rule-based fallback") for label in labels):
        summary_bits.append("fallback prediction logic")
    elif any(label.startswith("Data source: Win-probability model") for label in labels):
        summary_bits.append("model inference")

    if len(summary_bits) == 1:
        return "Based on live match state."
    return f"Based on {', '.join(summary_bits[:-1])}, and {summary_bits[-1]}."


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
    source_refs = _build_prediction_source_refs(game, prediction, game_id)
    ai_meta = AiOutputMetadata(
        output_type=AiOutputType.INSIGHT,
        is_official_truth=False,
        confidence_score=confidence_score,
        limitations=_PREDICTION_LIMITATIONS,
        source_refs=source_refs,
        grounding_summary=_build_prediction_grounding_summary(source_refs),
    )
    prediction["ai_metadata"] = ai_meta.model_dump()

    return prediction
