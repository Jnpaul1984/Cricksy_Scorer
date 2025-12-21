"""
Tactical Suggestion Engine API Routes

Provides real-time coaching recommendations during match play:
- Best bowler recommendations
- Batter weakness analysis
- Fielding setup suggestions
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.sql_app.database import get_db
from backend.sql_app.models import Game, Player, BattingScorecard, BowlingScorecard
from backend.services.tactical_suggestion_engine import (
    TacticalSuggestionEngine,
)

router = APIRouter(prefix="/tactical", tags=["tactical_suggestions"])


@router.get("/games/{game_id}/suggestions/best-bowler")
async def get_best_bowler_suggestion(
    game_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get recommendation for best bowler to bowl next delivery.

    Considers:
    - Bowler effectiveness (economy, wicket-taking)
    - Batter weaknesses
    - Recent bowler usage (avoid fatigue)

    Returns:
        {
            "bowler_id": str,
            "bowler_name": str,
            "reason": str,
            "effectiveness_vs_batter": float (0-100),
            "expected_economy": float,
            "confidence": float (0-1)
        }
    """
    try:
        # Fetch game
        game = await db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        # Get current innings and batter
        current_inning = game.current_inning_number
        current_batter_id = game.striker_id

        if not current_batter_id:
            raise HTTPException(status_code=400, detail="No current batter")

        # Fetch bowler statistics
        bowlers_data = []
        bowling_stats = (
            await db.query(BowlingScorecard)
            .filter(
                BowlingScorecard.game_id == game_id,
                BowlingScorecard.inning_number == current_inning,
            )
            .all()
        )

        for stat in bowling_stats:
            bowler = await db.query(Player).filter(Player.id == stat.bowler_id).first()
            if bowler:
                bowlers_data.append(
                    {
                        "bowler_id": stat.bowler_id,
                        "bowler_name": bowler.name,
                        "total_deliveries": stat.deliveries,
                        "runs_conceded": stat.runs_conceded,
                        "wickets_taken": stat.wickets_taken,
                        "economy_rate": stat.economy_rate or 0.0,
                        "strike_rate_against": (
                            (stat.runs_conceded / max(1, stat.deliveries)) * 100
                        )
                        if stat.deliveries > 0
                        else 0,
                    }
                )

        # Fetch batter profile
        batter = await db.query(Player).filter(Player.id == current_batter_id).first()
        if not batter:
            raise HTTPException(status_code=404, detail="Batter not found")

        batting_stats = (
            await db.query(BattingScorecard)
            .filter(
                BattingScorecard.player_id == current_batter_id,
            )
            .all()
        )

        total_runs = sum(s.runs_scored for s in batting_stats)
        total_deliveries = sum(s.deliveries_faced for s in batting_stats)
        dismissals = sum(1 for s in batting_stats if s.is_dismissed)

        batter_data = {
            "batter_id": batter.id,
            "batter_name": batter.name,
            "total_runs": total_runs,
            "total_deliveries": total_deliveries,
            "dismissals": dismissals,
            "batting_average": (total_runs / max(1, dismissals)) if dismissals > 0 else 0,
            "strike_rate": ((total_runs / max(1, total_deliveries)) * 100)
            if total_deliveries > 0
            else 0,
        }

        # Get recent bowlers to avoid repeats
        recent_bowlers: list[str] = []  # Could track last 2-3 bowlers if needed

        # Get suggestion
        suggestion = TacticalSuggestionEngine.get_best_bowler(
            bowlers_data,
            batter_data,
            recent_bowlers,
        )

        if not suggestion:
            return {
                "status": "no_suggestion",
                "message": "Could not determine best bowler recommendation",
            }

        return {
            "status": "success",
            "game_id": game_id,
            "current_batter": batter_data["batter_name"],
            "recommendation": {
                "bowler_id": suggestion.bowler_id,
                "bowler_name": suggestion.bowler_name,
                "reason": suggestion.reason,
                "effectiveness_vs_batter": suggestion.effectiveness_vs_batter,
                "expected_economy": suggestion.expected_economy,
                "confidence": suggestion.confidence,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/games/{game_id}/suggestions/weakness-analysis")
async def get_weakness_analysis(
    game_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Analyze current batter's weaknesses and recommend delivery type.

    Returns:
        {
            "primary_weakness": str (pace/spin/yorker/dot_strategy),
            "weakness_score": float (0-100),
            "secondary_weakness": str or null,
            "recommended_line": str,
            "recommended_length": str,
            "recommended_speed": float or null,
            "confidence": float (0-1)
        }
    """
    try:
        # Fetch game
        game = await db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        current_batter_id = game.striker_id
        if not current_batter_id:
            raise HTTPException(status_code=400, detail="No current batter")

        # Fetch batter profile
        batter = await db.query(Player).filter(Player.id == current_batter_id).first()
        if not batter:
            raise HTTPException(status_code=404, detail="Batter not found")

        batting_stats = (
            await db.query(BattingScorecard)
            .filter(
                BattingScorecard.player_id == current_batter_id,
            )
            .all()
        )

        total_runs = sum(s.runs_scored for s in batting_stats)
        total_deliveries = sum(s.deliveries_faced for s in batting_stats)
        dismissals = sum(1 for s in batting_stats if s.is_dismissed)

        batter_data = {
            "batter_id": batter.id,
            "batter_name": batter.name,
            "total_runs": total_runs,
            "total_deliveries": total_deliveries,
            "dismissals": dismissals,
            "batting_average": (total_runs / max(1, dismissals)) if dismissals > 0 else 0,
            "strike_rate": ((total_runs / max(1, total_deliveries)) * 100)
            if total_deliveries > 0
            else 0,
            "pace_weakness": 35.0,  # Default, can be enhanced with ML
            "spin_weakness": 25.0,
            "yorker_weakness": 60.0,
            "dot_ball_weakness": 40.0,
        }

        # Get weakness analysis
        analysis = TacticalSuggestionEngine.analyze_weakness(batter_data)

        return {
            "status": "success",
            "game_id": game_id,
            "batter": batter_data["batter_name"],
            "weakness_analysis": {
                "primary_weakness": analysis.primary_weakness,
                "weakness_score": analysis.weakness_score,
                "secondary_weakness": analysis.secondary_weakness,
                "recommended_line": analysis.recommended_line,
                "recommended_length": analysis.recommended_length,
                "recommended_speed": analysis.recommended_speed,
                "confidence": analysis.confidence,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/games/{game_id}/suggestions/fielding-setup")
async def get_fielding_setup(
    game_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get recommended fielding positions based on batter's scoring zones.

    Returns:
        {
            "bowler_id": str,
            "batter_id": str,
            "primary_zone": str,
            "recommended_positions": [
                {
                    "position": str (e.g., "mid-wicket"),
                    "priority": int (1 = highest),
                    "coverage_reason": str
                }
            ],
            "confidence": float (0-1),
            "reasoning": str
        }
    """
    try:
        # Fetch game
        game = await db.query(Game).filter(Game.id == game_id).first()
        if not game:
            raise HTTPException(status_code=404, detail="Game not found")

        current_bowler_id = game.bowler_id
        current_batter_id = game.striker_id

        if not current_bowler_id or not current_batter_id:
            raise HTTPException(status_code=400, detail="No current bowler or batter")

        # Fetch bowler and batter info
        bowler = await db.query(Player).filter(Player.id == current_bowler_id).first()
        batter = await db.query(Player).filter(Player.id == current_batter_id).first()

        bowler_data = (
            {
                "bowler_id": bowler.id,
                "bowler_name": bowler.name,
            }
            if bowler
            else {}
        )

        batter_data = (
            {
                "batter_id": batter.id,
                "batter_name": batter.name,
            }
            if batter
            else {}
        )

        # Mock scoring zones - in production would fetch from analytics
        scoring_zones = [
            {
                "line": "off",
                "length": "good",
                "runs_scored": 24,
                "dismissals": 2,
                "deliveries": 30,
            },
            {
                "line": "leg",
                "length": "full",
                "runs_scored": 18,
                "dismissals": 1,
                "deliveries": 20,
            },
            {
                "line": "middle",
                "length": "short",
                "runs_scored": 12,
                "dismissals": 0,
                "deliveries": 15,
            },
        ]

        # Get fielding recommendation
        fielding = TacticalSuggestionEngine.recommend_fielding(
            bowler_data,
            batter_data,
            scoring_zones,
        )

        return {
            "status": "success",
            "game_id": game_id,
            "bowler": bowler_data.get("bowler_name"),
            "batter": batter_data.get("batter_name"),
            "fielding_setup": {
                "primary_zone": fielding.primary_zone,
                "recommended_positions": [
                    {
                        "position": p.position,
                        "priority": p.priority,
                        "coverage_reason": p.coverage_reason,
                    }
                    for p in fielding.recommended_positions
                ],
                "confidence": fielding.confidence,
                "reasoning": fielding.reasoning,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/games/{game_id}/suggestions/all")
async def get_all_suggestions(
    game_id: str,
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get all tactical suggestions at once.

    Combines best bowler, weakness analysis, and fielding setup
    into a single comprehensive suggestion for the coach.
    """
    try:
        # Fetch best bowler
        best_bowler_response = await get_best_bowler_suggestion(game_id, db)

        # Fetch weakness analysis
        weakness_response = await get_weakness_analysis(game_id, db)

        # Fetch fielding setup
        fielding_response = await get_fielding_setup(game_id, db)

        return {
            "status": "success",
            "game_id": game_id,
            "timestamp": "2025-12-19T00:00:00Z",  # Would use datetime.now()
            "suggestions": {
                "best_bowler": best_bowler_response.get("recommendation"),
                "weakness_analysis": weakness_response.get("weakness_analysis"),
                "fielding_setup": fielding_response.get("fielding_setup"),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
