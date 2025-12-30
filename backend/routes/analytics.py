"""
API routes for game analytics including innings grades and performance metrics.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.innings_grade_service import get_innings_grade
from backend.services.pressure_analyzer import get_pressure_map
from backend.sql_app import crud
from backend.sql_app.database import get_db

router = APIRouter(prefix="/analytics", tags=["analytics"])


@router.get("/games/{game_id}/innings/{inning_num}/grade")
async def get_innings_grade_endpoint(
    game_id: str,
    inning_num: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get the performance grade for a specific innings.

    Grades are calculated based on:
    - Run rate vs par score (primary factor)
    - Wicket preservation (secondary)
    - Strike rotation efficiency (tertiary)
    - Boundary hitting ability (minor)

    Grade Scale:
    - A+: >150% of par score (exceptional)
    - A: 130-150% of par score (very good)
    - B: 100-130% of par score (good)
    - C: 70-100% of par score (average)
    - D: <70% of par score (below average)

    Args:
        game_id: UUID of the game
        inning_num: Innings number (1 or 2)
        db: Database session

    Returns:
        Dictionary with grade and detailed metrics

    Raises:
        HTTPException: If game not found or invalid inning number
    """
    # Validate inning number
    if inning_num not in (1, 2):
        raise HTTPException(status_code=400, detail="Inning number must be 1 or 2")

    # Fetch game from database
    game = await crud.get_game(db, game_id)

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Check if requested inning exists in game
    if game.current_inning < inning_num:
        raise HTTPException(
            status_code=400,
            detail=f"Inning {inning_num} has not been reached yet",
        )

    # Build game state dictionary
    # For historical innings, we need to extract the deliveries from that inning
    deliveries_data = None
    if game.deliveries:
        # Filter deliveries for the requested inning
        deliveries_data = [
            d
            for d in game.deliveries
            if d.get("inning_no") == inning_num or d.get("innings_no") == inning_num
        ]

    # For the current inning, use current stats
    if game.current_inning == inning_num:
        total_runs = game.total_runs
        total_wickets = game.total_wickets
        overs_completed = game.overs_completed
        balls_this_over = game.balls_this_over
    else:
        # For completed innings, we need to aggregate from deliveries
        # This is a simplified version - in production, store innings scores
        total_runs = 0
        total_wickets = 0
        overs_completed = 0
        balls_this_over = 0

        if deliveries_data:
            # Calculate from deliveries (simplified - actual implementation would aggregate)
            innings_stats = _aggregate_innings_from_deliveries(
                deliveries_data,
                game.batting_scorecard if inning_num == game.current_inning else {},
                game.bowling_scorecard if inning_num == game.current_inning else {},
            )
            total_runs = innings_stats["runs"]
            total_wickets = innings_stats["wickets"]
            overs_completed = innings_stats["overs_completed"]
            balls_this_over = innings_stats["balls_this_over"]

    game_state = {
        "total_runs": total_runs,
        "total_wickets": total_wickets,
        "overs_completed": overs_completed,
        "balls_this_over": balls_this_over,
        "overs_limit": game.overs_limit,
        "deliveries": deliveries_data or [],
        "is_completed": game.current_inning > inning_num
        or (game.current_inning == inning_num and game.status == "completed"),
    }

    # Calculate grade
    grade_data = get_innings_grade(game_state)

    # Add metadata
    grade_data["inning_num"] = inning_num
    grade_data["game_id"] = game_id
    grade_data["batting_team"] = game.batting_team_name if game.current_inning == inning_num else ""
    grade_data["bowling_team"] = game.bowling_team_name if game.current_inning == inning_num else ""

    return grade_data


@router.get("/games/{game_id}/innings/current/grade")
async def get_current_innings_grade(
    game_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get the performance grade for the current innings.

    Convenience endpoint that automatically fetches the current inning.

    Args:
        game_id: UUID of the game
        db: Database session

    Returns:
        Dictionary with grade and detailed metrics for current innings

    Raises:
        HTTPException: If game not found
    """
    # Fetch game from database
    game = await crud.get_game(db, game_id)

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Use the current inning
    current_inning = game.current_inning

    # Build game state dictionary
    deliveries_data = None
    if game.deliveries:
        deliveries_data = [
            d
            for d in game.deliveries
            if d.get("inning_no") == current_inning or d.get("innings_no") == current_inning
        ]

    game_state = {
        "total_runs": game.total_runs,
        "total_wickets": game.total_wickets,
        "overs_completed": game.overs_completed,
        "balls_this_over": game.balls_this_over,
        "overs_limit": game.overs_limit,
        "deliveries": deliveries_data or [],
        "is_completed": game.status == "completed",
    }

    # Calculate grade
    grade_data = get_innings_grade(game_state)

    # Add metadata
    grade_data["inning_num"] = current_inning
    grade_data["game_id"] = game_id
    grade_data["batting_team"] = game.batting_team_name
    grade_data["bowling_team"] = game.bowling_team_name

    return grade_data


def _aggregate_innings_from_deliveries(
    deliveries: list[dict[str, Any]],
    batting_scorecard: dict,
    bowling_scorecard: dict,
) -> dict[str, int]:
    """
    Aggregate innings statistics from deliveries list.

    This is a helper function to calculate stats when we only have delivery data.
    In production, this would typically be stored in the database for performance.

    Args:
        deliveries: List of delivery dictionaries
        batting_scorecard: Current batting scorecard
        bowling_scorecard: Current bowling scorecard

    Returns:
        Dictionary with aggregated stats
    """
    if not deliveries:
        return {"runs": 0, "wickets": 0, "overs_completed": 0, "balls_this_over": 0}

    # Get the last delivery to determine final over/ball
    last_delivery = deliveries[-1]
    overs_completed = last_delivery.get("over_number", 0)
    balls_this_over = last_delivery.get("ball_number", 0)

    # Sum runs from deliveries
    total_runs = sum(d.get("runs_scored", 0) for d in deliveries)

    # Count wickets (wickets are deliveries with is_wicket=True)
    total_wickets = sum(1 for d in deliveries if d.get("is_wicket", False))

    return {
        "runs": total_runs,
        "wickets": total_wickets,
        "overs_completed": overs_completed,
        "balls_this_over": balls_this_over,
    }


@router.get("/games/{game_id}/pressure-map")
async def get_pressure_map_endpoint(
    game_id: str,
    inning_num: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get pressure mapping for a game's innings.

    Analyzes delivery-by-delivery pressure based on:
    - Dot ball streaks (consecutive dots)
    - Required run rate vs actual run rate gap
    - Wicket timings
    - Overs remaining pressure
    - Match situation

    Pressure Scale:
    - 0-20: Low pressure (runs flowing)
    - 20-40: Moderate pressure (some dots)
    - 40-60: Building pressure (dot streaks)
    - 60-80: High pressure (critical moments)
    - 80-100: Extreme pressure (match-deciding)

    Args:
        game_id: UUID of the game
        inning_num: Optional innings number (default: current innings)
        db: Database session

    Returns:
        Dictionary with pressure points, summary, peak moments, and phases

    Raises:
        HTTPException: If game not found or no target set
    """
    # Fetch game from database
    game = await crud.get_game(db, game_id)

    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Default to current innings if not specified
    if inning_num is None:
        inning_num = game.current_inning

    # Validate inning number
    if inning_num not in (1, 2):
        raise HTTPException(status_code=400, detail="Inning number must be 1 or 2")

    # Check if requested inning exists
    if game.current_inning < inning_num:
        raise HTTPException(
            status_code=400,
            detail=f"Inning {inning_num} has not been reached yet",
        )

    # Get deliveries for the requested inning
    deliveries_data = []
    if game.deliveries:
        deliveries_data = [
            d
            for d in game.deliveries
            if d.get("inning_no") == inning_num or d.get("innings_no") == inning_num
        ]

    if not deliveries_data:
        return {
            "pressure_points": [],
            "summary": {
                "total_deliveries": 0,
                "average_pressure": 0,
                "peak_pressure": 0,
                "critical_moments": 0,
                "high_pressure_count": 0,
            },
            "peak_moments": [],
            "phases": {},
            "inning_num": inning_num,
            "game_id": game_id,
        }

    # Determine target (for second innings or when chasing)
    target = 0
    if inning_num == 2 and game.target:
        target = game.target
    elif inning_num == 1:
        # For first innings, use a hypothetical target based on par score
        target = (game.overs_limit or 20) * 8  # 8 runs per over as default

    # Calculate pressure map
    pressure_data = get_pressure_map(
        deliveries=deliveries_data,
        target=target,
        overs_limit=game.overs_limit or 20,
    )

    # Add metadata
    pressure_data["inning_num"] = inning_num
    pressure_data["game_id"] = game_id
    pressure_data["batting_team"] = (
        game.batting_team_name if game.current_inning == inning_num else ""
    )
    pressure_data["bowling_team"] = (
        game.bowling_team_name if game.current_inning == inning_num else ""
    )

    return pressure_data


@router.get("/games/{game_id}/innings/{inning_num}/pressure-map")
async def get_innings_pressure_map(
    game_id: str,
    inning_num: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, Any]:
    """
    Get pressure mapping for a specific innings (convenience endpoint).

    Args:
        game_id: UUID of the game
        inning_num: Innings number (1 or 2)
        db: Database session

    Returns:
        Pressure map data for the specified innings
    """
    return await get_pressure_map_endpoint(game_id, inning_num, db)
