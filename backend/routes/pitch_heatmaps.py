"""
API routes for pitch heatmap overlays.
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.db import get_async_db
from backend.services.pitch_heatmap_generator import (
    PitchHeatmapGenerator,
    PitchZone,
)
from backend.sql_app.models import (
    Game,
    Player,
    BattingScorecard,
    BowlingScorecard,
)
from fastapi import Depends

router = APIRouter(prefix="/heatmaps", tags=["heatmaps"])


@router.get("/players/{player_id}/batting-heatmap")
async def get_player_batting_heatmap(
    player_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get batting scoring heatmap for a player across all games.
    Shows where player scores runs (pitch zones).
    """
    try:
        # Fetch player
        stmt = select(Player).where(Player.id == player_id)
        result = await db.execute(stmt)
        player = result.scalar_one_or_none()

        if not player:
            raise HTTPException(status_code=404, detail="Player not found")

        # Fetch all batting scorecards
        stmt = select(BattingScorecard).where(BattingScorecard.player_id == player_id)
        result = await db.execute(stmt)
        scorecards = result.scalars().all()

        if not scorecards:
            return {
                "status": "success",
                "player_id": player_id,
                "player_name": player.name,
                "message": "No batting data available",
                "heatmap": None,
            }

        # Convert scorecards to delivery format
        # NOTE: In real implementation, would need delivery-level data
        # For now, use scorecard-level aggregation
        deliveries = [
            {
                "zone": PitchZone.MIDDLE_FULL,  # Default zone
                "runs_scored": sc.runs_scored,
                "deliveries": sc.deliveries_faced,
            }
            for sc in scorecards
        ]

        # Generate heatmap
        heatmap = PitchHeatmapGenerator.generate_batter_scoring_heatmap(
            player_id=player_id,
            player_name=player.name,
            deliveries=deliveries,
        )

        return {
            "status": "success",
            "player_id": player_id,
            "player_name": player.name,
            "heatmap": {
                "heatmap_id": heatmap.heatmap_id,
                "heatmap_type": heatmap.heatmap_type,
                "data_points": [
                    {
                        "zone": dp.zone,
                        "x_coordinate": dp.x_coordinate,
                        "y_coordinate": dp.y_coordinate,
                        "value": dp.value,
                        "count": dp.count,
                        "detail": dp.detail,
                    }
                    for dp in heatmap.data_points
                ],
                "average_value": heatmap.average_value,
                "total_events": heatmap.total_events,
                "metadata": heatmap.metadata,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Heatmap generation failed: {e!s}")


@router.get("/players/{player_id}/dismissal-heatmap")
async def get_player_dismissal_heatmap(
    player_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get dismissal heatmap for a player.
    Shows pitch zones where player typically gets dismissed.
    """
    try:
        # Fetch player
        stmt = select(Player).where(Player.id == player_id)
        result = await db.execute(stmt)
        player = result.scalar_one_or_none()

        if not player:
            raise HTTPException(status_code=404, detail="Player not found")

        # Fetch dismissed scorecards
        stmt = select(BattingScorecard).where(
            (BattingScorecard.player_id == player_id) & (BattingScorecard.is_dismissed == True)
        )
        result = await db.execute(stmt)
        dismissed_scorecards = result.scalars().all()

        if not dismissed_scorecards:
            return {
                "status": "success",
                "player_id": player_id,
                "player_name": player.name,
                "message": "No dismissal data available",
                "heatmap": None,
            }

        # Convert to dismissal format
        dismissals = [
            {
                "zone": PitchZone.MIDDLE_FULL,  # Default
                "dismissal_type": sc.dismissal_type or "unknown",
            }
            for sc in dismissed_scorecards
        ]

        # Generate heatmap
        heatmap = PitchHeatmapGenerator.generate_dismissal_heatmap(
            player_id=player_id,
            player_name=player.name,
            dismissals=dismissals,
        )

        return {
            "status": "success",
            "player_id": player_id,
            "player_name": player.name,
            "heatmap": {
                "heatmap_id": heatmap.heatmap_id,
                "heatmap_type": heatmap.heatmap_type,
                "data_points": [
                    {
                        "zone": dp.zone,
                        "x_coordinate": dp.x_coordinate,
                        "y_coordinate": dp.y_coordinate,
                        "value": dp.value,
                        "count": dp.count,
                        "detail": dp.detail,
                    }
                    for dp in heatmap.data_points
                ],
                "average_value": heatmap.average_value,
                "total_events": heatmap.total_events,
                "metadata": heatmap.metadata,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Dismissal heatmap failed: {e!s}")


@router.get("/bowlers/{bowler_id}/release-zones")
async def get_bowler_release_zones(
    bowler_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get bowler's release point heatmap.
    Shows consistency and primary zones where bowler delivers from.
    """
    try:
        # Fetch bowler
        stmt = select(Player).where(Player.id == bowler_id)
        result = await db.execute(stmt)
        bowler = result.scalar_one_or_none()

        if not bowler:
            raise HTTPException(status_code=404, detail="Bowler not found")

        # Fetch all bowling scorecards
        stmt = select(BowlingScorecard).where(BowlingScorecard.bowler_id == bowler_id)
        result = await db.execute(stmt)
        bowling_scorecards = result.scalars().all()

        if not bowling_scorecards:
            return {
                "status": "success",
                "bowler_id": bowler_id,
                "bowler_name": bowler.name,
                "message": "No bowling data available",
                "heatmap": None,
            }

        # Create delivery zones (simplified)
        deliveries = [
            {
                "zone": PitchZone.MIDDLE_FULL,
                "bowler_zone": PitchZone.MIDDLE_FULL,
            }
            for _ in range(max(1, sum(s.deliveries_bowled for s in bowling_scorecards)))
        ]

        # Generate heatmap
        heatmap = PitchHeatmapGenerator.generate_bowler_release_heatmap(
            bowler_id=bowler_id,
            bowler_name=bowler.name,
            deliveries=deliveries,
        )

        return {
            "status": "success",
            "bowler_id": bowler_id,
            "bowler_name": bowler.name,
            "heatmap": {
                "heatmap_id": heatmap.heatmap_id,
                "heatmap_type": heatmap.heatmap_type,
                "data_points": [
                    {
                        "zone": dp.zone,
                        "x_coordinate": dp.x_coordinate,
                        "y_coordinate": dp.y_coordinate,
                        "value": dp.value,
                        "count": dp.count,
                        "detail": dp.detail,
                    }
                    for dp in heatmap.data_points
                ],
                "average_value": heatmap.average_value,
                "total_events": heatmap.total_events,
                "metadata": heatmap.metadata,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Release zone analysis failed: {e!s}")


@router.get("/matchups/{batter_id}/vs/{bowler_id}")
async def get_matchup_analysis(
    batter_id: str,
    bowler_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Analyze specific batter vs bowler spatial matchup.
    """
    try:
        # Fetch players
        batter_stmt = select(Player).where(Player.id == batter_id)
        batter_result = await db.execute(batter_stmt)
        batter = batter_result.scalar_one_or_none()

        bowler_stmt = select(Player).where(Player.id == bowler_id)
        bowler_result = await db.execute(bowler_stmt)
        bowler = bowler_result.scalar_one_or_none()

        if not batter:
            raise HTTPException(status_code=404, detail="Batter not found")
        if not bowler:
            raise HTTPException(status_code=404, detail="Bowler not found")

        # Fetch batter's scorecards and dismissals
        batter_stmt = select(BattingScorecard).where(BattingScorecard.player_id == batter_id)
        batter_result = await db.execute(batter_stmt)
        batter_scorecards = batter_result.scalars().all()

        # Simplified delivery list
        deliveries = [
            {"zone": PitchZone.MIDDLE_FULL}
            for _ in range(sum(s.deliveries_faced for s in batter_scorecards))
        ]

        dismissals = [{"zone": PitchZone.MIDDLE_FULL} for s in batter_scorecards if s.is_dismissed]

        # Analyze matchup
        matchup = PitchHeatmapGenerator.analyze_matchup(
            batter_id=batter_id,
            batter_name=batter.name,
            bowler_id=bowler_id,
            bowler_name=bowler.name,
            deliveries=deliveries,
            dismissals=dismissals,
        )

        return {
            "status": "success",
            "matchup": {
                "batter_id": matchup.batter_id,
                "batter_name": matchup.batter_name,
                "bowler_id": matchup.bowler_id,
                "bowler_name": matchup.bowler_name,
                "total_deliveries": matchup.total_deliveries,
                "dangerous_areas": matchup.dangerous_areas,
                "weak_overlap_areas": matchup.weak_overlap_areas,
                "dismissal_zones": matchup.dismissal_zones,
                "recommendation": matchup.recommendation,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Matchup analysis failed: {e!s}")


@router.get("/games/{game_id}/team-{team_side}/heatmap-summary")
async def get_game_heatmap_summary(
    game_id: str,
    team_side: str,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Get aggregate heatmap for entire team in a game.
    """
    try:
        if team_side not in ["a", "b"]:
            raise HTTPException(status_code=400, detail="Invalid team_side (use 'a' or 'b')")

        # Fetch game
        stmt = select(Game).where(Game.id == game_id)
        result = await db.execute(stmt)
        game = result.scalar_one_or_none()

        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        # Fetch team batting scorecards
        inning_number = 1 if team_side == "a" else 2
        stmt = select(BattingScorecard).where(
            (BattingScorecard.game_id == game_id)
            & (BattingScorecard.inning_number == inning_number)
        )
        result = await db.execute(stmt)
        scorecards = result.scalars().all()

        if not scorecards:
            return {
                "status": "success",
                "game_id": game_id,
                "team_side": team_side,
                "message": "No team batting data",
                "summary": None,
            }

        # Aggregate team stats
        total_runs = sum(sc.runs_scored for sc in scorecards)
        total_dismissals = sum(1 for sc in scorecards if sc.is_dismissed)
        average_runs_per_player = round(total_runs / len(scorecards), 1)

        return {
            "status": "success",
            "game_id": game_id,
            "team_side": team_side,
            "summary": {
                "total_players": len(scorecards),
                "total_runs": total_runs,
                "total_dismissals": total_dismissals,
                "average_runs_per_player": average_runs_per_player,
                "players_with_data": len([sc for sc in scorecards if sc.runs_scored > 0]),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Team heatmap failed: {e!s}")
