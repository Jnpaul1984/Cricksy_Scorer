"""
Phase Analysis Routes

REST API endpoints for match phase analysis:
- GET /phase-map: Full phase breakdown with predictions
- GET /phase-predictions: Phase-specific predictions
- GET /phase-trends: Phase-by-phase performance trends
"""

from typing import Any
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

from backend.sql_app.database import get_db
from backend.sql_app.models import Game, User
from backend.services.phase_analyzer import get_phase_analysis

router = APIRouter(prefix="/analytics", tags=["phase_analysis"])


@router.get("/games/{game_id}/phase-map")
async def get_phase_map(
    game_id: str,
    inning_num: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get complete phase map for a game with analysis and predictions.

    Returns:
    {
        "game_id": str,
        "inning_number": int,
        "phases": [
            {
                "phase_name": "powerplay"|"middle"|"death"|"mini_death",
                "phase_number": int,
                "start_over": int,
                "end_over": int,
                "total_runs": int,
                "total_wickets": int,
                "run_rate": float,
                "expected_runs_in_phase": float,
                "actual_vs_expected_pct": float,
                "wicket_rate": float,
                "boundary_count": int,
                "dot_ball_count": int,
                "aggressive_index": float,
            },
            ...
        ],
        "current_phase": str,
        "summary": {
            "total_runs": int,
            "total_wickets": int,
            "overall_run_rate": float,
            "acceleration_trend": "increasing"|"decreasing"|"stable",
        },
        "predictions": {
            "powerplay_actual": int,
            "total_expected_runs": int,
            "win_probability": float (if chasing),
        },
    }
    """
    try:
        # Fetch game
        stmt = (
            select(Game)
            .where(Game.id == game_id)
            .options(selectinload(Game.batting_order).selectinload(User.teams))
        )
        result = await db.execute(stmt)
        game = result.scalars().first()

        if not game:
            raise HTTPException(status_code=404, detail=f"Game {game_id} not found")

        # Determine which inning to analyze
        if inning_num is None:
            # Use the most recent completed/current inning
            inning_num = 2 if game.second_inning_json else 1

        # Get deliveries
        if inning_num == 2 and game.second_inning_json:
            inning_data = game.second_inning_json
            is_second_innings = True
        else:
            inning_data = game.first_inning_json if game.first_inning_json else {}
            is_second_innings = False

        deliveries = inning_data.get("deliveries", [])

        if not deliveries:
            raise HTTPException(status_code=400, detail=f"No deliveries in inning {inning_num}")

        # Get target
        target = get_current_target(game)

        # Analyze phases
        phase_data = get_phase_analysis(
            deliveries=deliveries,
            target=target,
            overs_limit=game.overs_per_side,
            is_second_innings=is_second_innings,
        )

        return {
            "game_id": game_id,
            "inning_number": inning_num,
            "overs_limit": game.overs_per_side,
            **phase_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Phase analysis error: {e!s}")


@router.get("/games/{game_id}/phase-predictions")
async def get_phase_predictions(
    game_id: str,
    inning_num: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get phase-specific predictions for a game.

    Returns:
    {
        "game_id": str,
        "inning_number": int,
        "phase_predictions": {
            "powerplay": {
                "actual_runs": int,
                "efficiency": float,
                "rate_vs_benchmark": float,
            },
            "middle": {...},
            "death": {...},
            "mini_death": {...},
        },
        "match_prediction": {
            "projected_total": int,
            "win_probability": float (if chasing),
            "confidence": float,
        },
    }
    """
    try:
        # Fetch game
        stmt = select(Game).where(Game.id == game_id)
        result = await db.execute(stmt)
        game = result.scalars().first()

        if not game:
            raise HTTPException(status_code=404, detail=f"Game {game_id} not found")

        # Determine which inning
        if inning_num is None:
            inning_num = 2 if game.second_inning_json else 1

        # Get deliveries
        if inning_num == 2 and game.second_inning_json:
            inning_data = game.second_inning_json
            is_second_innings = True
        else:
            inning_data = game.first_inning_json if game.first_inning_json else {}
            is_second_innings = False

        deliveries = inning_data.get("deliveries", [])

        if not deliveries:
            raise HTTPException(status_code=400, detail=f"No deliveries in inning {inning_num}")

        # Get target
        target = get_current_target(game)

        # Analyze phases
        phase_data = get_phase_analysis(
            deliveries=deliveries,
            target=target,
            overs_limit=game.overs_per_side,
            is_second_innings=is_second_innings,
        )

        # Extract phase performance
        phase_predictions = {}
        for phase in phase_data.get("phases", []):
            phase_name = phase["phase_name"]
            phase_predictions[phase_name] = {
                "actual_runs": phase["total_runs"],
                "expected_runs": phase["expected_runs_in_phase"],
                "efficiency": phase["actual_vs_expected_pct"],
                "run_rate": phase["run_rate"],
                "wickets_lost": phase["total_wickets"],
                "aggressive_index": phase["aggressive_index"],
            }

        # Match prediction
        match_prediction = {
            "projected_total": phase_data.get("predictions", {}).get("total_expected_runs", 0),
            "confidence": 0.75,  # Higher as more overs are bowled
        }

        if is_second_innings and target:
            match_prediction["win_probability"] = phase_data.get("predictions", {}).get(
                "win_probability", 0.5
            )

        return {
            "game_id": game_id,
            "inning_number": inning_num,
            "phase_predictions": phase_predictions,
            "match_prediction": match_prediction,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Phase prediction error: {e!s}")


@router.get("/games/{game_id}/phase-trends")
async def get_phase_trends(
    game_id: str,
    inning_num: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get phase-by-phase performance trends.

    Returns:
    {
        "game_id": str,
        "inning_number": int,
        "trends": {
            "run_rate_trend": [6.5, 7.2, 8.1, 11.5],  # RR by phase
            "wicket_rate_trend": [0.5, 0.33, 0.8, 1.0],  # Wickets/over
            "acceleration": "increasing"|"decreasing"|"stable",
            "phase_comparison": {
                "vs_powerplay": [1.0, 1.1, 1.35, 1.8],  # Ratio of each phase to powerplay
                "vs_benchmark": [0.76, 1.03, 0.9, 0.96],  # Ratio to expected
            },
        },
    }
    """
    try:
        # Fetch game
        stmt = select(Game).where(Game.id == game_id)
        result = await db.execute(stmt)
        game = result.scalars().first()

        if not game:
            raise HTTPException(status_code=404, detail=f"Game {game_id} not found")

        # Determine which inning
        if inning_num is None:
            inning_num = 2 if game.second_inning_json else 1

        # Get deliveries
        if inning_num == 2 and game.second_inning_json:
            inning_data = game.second_inning_json
            is_second_innings = True
        else:
            inning_data = game.first_inning_json if game.first_inning_json else {}
            is_second_innings = False

        deliveries = inning_data.get("deliveries", [])

        if not deliveries:
            raise HTTPException(status_code=400, detail=f"No deliveries in inning {inning_num}")

        # Get target
        target = get_current_target(game)

        # Analyze phases
        phase_data = get_phase_analysis(
            deliveries=deliveries,
            target=target,
            overs_limit=game.overs_per_side,
            is_second_innings=is_second_innings,
        )

        # Build trends
        phases = phase_data.get("phases", [])
        run_rate_trend = [p["run_rate"] for p in phases]
        wicket_rate_trend = [p["wicket_rate"] for p in phases]

        # Phase comparison (vs powerplay)
        powerplay_rr = run_rate_trend[0] if run_rate_trend else 1.0
        vs_powerplay = [p["run_rate"] / powerplay_rr if powerplay_rr > 0 else 1.0 for p in phases]

        # Phase comparison (vs benchmark)
        vs_benchmark = [p["actual_vs_expected_pct"] / 100 for p in phases]

        return {
            "game_id": game_id,
            "inning_number": inning_num,
            "trends": {
                "run_rate_trend": [round(x, 2) for x in run_rate_trend],
                "wicket_rate_trend": [round(x, 2) for x in wicket_rate_trend],
                "acceleration": phase_data.get("summary", {}).get("acceleration_trend", "stable"),
                "phase_comparison": {
                    "vs_powerplay": [round(x, 2) for x in vs_powerplay],
                    "vs_benchmark": [round(x, 2) for x in vs_benchmark],
                },
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Phase trends error: {e!s}")
