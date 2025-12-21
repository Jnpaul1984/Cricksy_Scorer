"""
Pressure Analysis Routes

Exposes real-time pressure mapping and analysis via REST API.
Endpoints for pressure map visualization, critical moments, and phase analysis.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.sql_app.database import get_db
from backend.sql_app.models import Game, Delivery
from backend.services.pressure_analyzer import get_pressure_map

router = APIRouter(prefix="/analytics", tags=["pressure_analysis"])


@router.get("/games/{game_id}/pressure-map")
async def get_game_pressure_map(
    game_id: str,
    inning_num: int | None = None,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get pressure map for a game or specific inning.

    Shows pressure score for each delivery with factors:
    - Dot ball streaks
    - Required run rate vs actual
    - Wicket timings
    - Overs remaining
    - Match situation

    Returns:
        {
            "game_id": str,
            "inning_num": int | None,  # If specific inning requested
            "pressure_points": [
                {
                    "delivery_num": int,
                    "over_num": float,  # e.g., 5.3
                    "pressure_score": float,  # 0-100
                    "pressure_level": str,  # low, moderate, building, high, extreme
                    "factors": {
                        "dot_streak": int,
                        "rrr_gap": float,
                        "wicket_factor": float,
                        ...
                    },
                    "rates": {
                        "required_run_rate": float,
                        "actual_run_rate": float,
                    },
                    "cumulative_stats": {...}
                },
                ...
            ],
            "summary": {
                "total_deliveries": int,
                "average_pressure": float,
                "peak_pressure": float,
                "peak_pressure_at_delivery": int,
                "critical_moments": int,  # deliveries with pressure >= 70
                "high_pressure_count": int,  # deliveries with pressure >= 60
            },
            "peak_moments": [top 5 critical deliveries],
            "phases": {
                "powerplay": [...],
                "middle": [...],
                "death": [...],
            }
        }
    """
    try:
        # Fetch game
        stmt = select(Game).where(Game.id == game_id)
        result = await db.execute(stmt)
        game = result.scalars().first()

        if not game:
            raise HTTPException(status_code=404, detail=f"Game {game_id} not found")

        # Fetch deliveries for the specified inning or current
        if inning_num is not None:
            stmt = (
                select(Delivery)
                .where((Delivery.game_id == game_id) & (Delivery.inning_num == inning_num))
                .order_by(Delivery.delivery_num)
            )
        else:
            # Get current inning
            stmt = (
                select(Delivery).where(Delivery.game_id == game_id).order_by(Delivery.delivery_num)
            )
            result = await db.execute(stmt)
            all_deliveries = result.scalars().all()

            # Group by inning and get latest
            if all_deliveries:
                inning_num = max(d.inning_num for d in all_deliveries)
                stmt = (
                    select(Delivery)
                    .where((Delivery.game_id == game_id) & (Delivery.inning_num == inning_num))
                    .order_by(Delivery.delivery_num)
                )

        result = await db.execute(stmt)
        deliveries_db = result.scalars().all()

        if not deliveries_db:
            raise HTTPException(status_code=400, detail="No deliveries found for this game")

        # Convert deliveries to analysis format
        deliveries = [
            {
                "runs_scored": int(d.runs_scored or 0),
                "extra": d.extra_type,
                "extra_runs": int(d.extra_runs or 0)
                if d.extra_type and d.extra_type in ["wd", "nb"]
                else 0,
                "is_wicket": bool(d.is_wicket),
                "how_out": d.dismissal_type,
                "ball_in_over": d.ball_in_over,
                "over_num": d.over_num,
            }
            for d in deliveries_db
        ]

        # Determine target (runs scored in first inning if chasing)
        if inning_num == 2:
            # Get first inning runs
            stmt = select(Delivery).where(
                (Delivery.game_id == game_id) & (Delivery.inning_num == 1)
            )
            result = await db.execute(stmt)
            first_inning_deliveries = result.scalars().all()
            target = sum(int(d.runs_scored or 0) for d in first_inning_deliveries)
        else:
            # Default target based on format
            target = int(game.overs_limit or 20) * 8  # ~8 runs per over

        # Get overs limit
        overs_limit = int(game.overs_limit or 20)

        # Generate pressure map
        pressure_data = get_pressure_map(
            deliveries=deliveries,
            target=target,
            overs_limit=overs_limit,
        )

        return {
            "game_id": str(game.id),
            "inning_num": inning_num,
            "batting_team": game.batting_team_name if inning_num == 1 else game.bowling_team_name,
            "bowling_team": game.bowling_team_name if inning_num == 1 else game.batting_team_name,
            "target": target,
            "overs_limit": overs_limit,
            **pressure_data,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to calculate pressure map: {e!s}")


@router.get("/games/{game_id}/critical-moments")
async def get_critical_moments(
    game_id: str,
    db: AsyncSession = Depends(get_db),
    threshold: float = 70,
    inning_num: int | None = None,
) -> dict:
    """
    Get critical pressure moments (high-pressure deliveries).

    Useful for highlighting key moments in match highlights.
    """
    try:
        # Fetch game
        stmt = select(Game).where(Game.id == game_id)
        result = await db.execute(stmt)
        game = result.scalars().first()

        if not game:
            raise HTTPException(status_code=404, detail=f"Game {game_id} not found")

        # Get pressure map
        pressure_response = await get_game_pressure_map(game_id, db, inning_num)

        # Filter for critical moments
        critical = [
            p for p in pressure_response["pressure_points"] if p["pressure_score"] >= threshold
        ]

        return {
            "game_id": str(game.id),
            "threshold": threshold,
            "critical_moments_count": len(critical),
            "critical_moments": critical,
            "summary": {
                "total_high_pressure": len(critical),
                "highest_pressure": max([p["pressure_score"] for p in critical]) if critical else 0,
                "most_critical_delivery": critical[0]["delivery_num"] if critical else None,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get critical moments: {e!s}")


@router.get("/games/{game_id}/pressure-phases")
async def get_pressure_phases(
    game_id: str,
    db: AsyncSession = Depends(get_db),
    inning_num: int | None = None,
) -> dict:
    """
    Get pressure analysis by match phase.

    Breaks down pressure by phases:
    - Powerplay (0-6 overs)
    - Middle (7-15 overs)
    - Death (16+ overs)
    """
    try:
        # Get pressure map
        pressure_response = await get_game_pressure_map(game_id, db, inning_num)

        phases = pressure_response.get("phases", {})

        # Add analysis for each phase
        phase_analysis = {}
        for phase_name in ["powerplay", "middle", "death"]:
            if f"{phase_name}_stats" in phases:
                phase_analysis[phase_name] = {
                    "phase": phase_name,
                    "statistics": phases[f"{phase_name}_stats"],
                    "deliveries": phases[phase_name],
                }

        return {
            "game_id": str(pressure_response["game_id"]),
            "phases": phase_analysis,
        }

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to analyze pressure phases: {e!s}")
