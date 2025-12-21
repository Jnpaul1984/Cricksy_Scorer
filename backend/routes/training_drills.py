"""
Training Drills API Routes

Endpoints for generating and managing personalized training drill recommendations.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.sql_app.database import get_db
from backend.services.training_drill_generator import TrainingDrillGenerator

router = APIRouter(prefix="/training", tags=["training_drills"])


@router.get("/players/{player_id}/suggested-drills")
async def get_suggested_drills(
    player_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get personalized training drill suggestions for a player.

    Analyzes player's recent performance and weaknesses to recommend
    targeted drills for skill development.

    Args:
        player_id: Player ID
        db: Database session

    Returns:
        Personalized training drill plan

    Raises:
        404: Player not found
    """
    try:
        from sqlalchemy import select

        # Fetch player
        result = await db.execute(select(Player).where(Player.id == player_id))
        player = result.scalars().first()

        if not player:
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found")

        # Get player's recent match data
        result = await db.execute(
            select(BattingScorecard)
            .where(BattingScorecard.player_id == player_id)
            .order_by(BattingScorecard.id.desc())
            .limit(10)
        )
        recent_matches = result.scalars().all()

        # Build player profile from recent matches
        if recent_matches:
            total_runs = sum(m.runs_scored for m in recent_matches)
            total_deliveries = sum(m.deliveries_faced for m in recent_matches)
            avg_score = total_runs / len(recent_matches) if recent_matches else 0

            # Mock weakness indicators (in real system, these come from Tactical Suggestion Engine)
            player_profile = {
                "player_id": player_id,
                "player_name": player.name,
                "total_runs": total_runs,
                "total_deliveries": total_deliveries,
                "average": avg_score,
                "pace_weakness": 35.0,  # Mock: 0-100 scale
                "spin_weakness": 45.0,
                "dot_ball_weakness": 60.0,  # High weakness
                "yorker_weakness": 70.0,  # High weakness
                "aggressive_weakness": 30.0,
                "boundary_weakness": 25.0,
                "dismissals": sum(1 for m in recent_matches if m.is_dismissed),
            }
        else:
            player_profile = {
                "player_id": player_id,
                "player_name": player.name,
                "total_runs": 0,
                "total_deliveries": 0,
                "average": 0,
                "pace_weakness": 40.0,
                "spin_weakness": 35.0,
                "dot_ball_weakness": 50.0,
                "yorker_weakness": 45.0,
                "aggressive_weakness": 30.0,
                "boundary_weakness": 25.0,
                "dismissals": 0,
            }

        # Generate drill plan
        drill_plan = TrainingDrillGenerator.generate_drills_for_player(
            player_id=player_id,
            player_name=player.name,
            player_profile=player_profile,
            recent_dismissals=[],
        )

        return {
            "status": "success",
            "player_id": player_id,
            "player_name": player.name,
            "drill_plan": {
                "drills": [
                    {
                        "drill_id": d.drill_id,
                        "category": d.category.value,
                        "name": d.name,
                        "description": d.description,
                        "reason": d.reason,
                        "severity": d.severity.value,
                        "reps_or_count": d.reps_or_count,
                        "duration_minutes": d.duration_minutes,
                        "focus_area": d.focus_area,
                        "difficulty": d.difficulty,
                        "recommended_frequency": d.recommended_frequency,
                        "expected_improvement": d.expected_improvement,
                        "weakness_score": d.weakness_score,
                        "confidence": d.confidence,
                    }
                    for d in drill_plan.drills
                ],
                "summary": {
                    "total_drills": len(drill_plan.drills),
                    "high_priority": drill_plan.high_priority_count,
                    "medium_priority": drill_plan.medium_priority_count,
                    "low_priority": drill_plan.low_priority_count,
                    "total_weekly_hours": drill_plan.total_weekly_hours,
                    "focus_areas": drill_plan.focus_areas,
                },
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating drills: {e!s}")


@router.get("/games/{game_id}/team-{team_side}/suggested-drills")
async def get_team_drills(
    game_id: str,
    team_side: str,  # "a" or "b"
    db: AsyncSession = Depends(get_db),
):
    """
    Get training drill suggestions for all players in a team after a match.

    Analyzes match performance and generates team-wide drill recommendations.

    Args:
        game_id: Game ID
        team_side: "a" or "b" for team side
        db: Database session

    Returns:
        Drill plans for all players

    Raises:
        404: Game not found
    """
    try:
        from sqlalchemy import select

        # Fetch game
        result = await db.execute(select(Game).where(Game.id == game_id))
        game = result.scalars().first()

        if not game:
            raise HTTPException(status_code=404, detail=f"Game {game_id} not found")

        # Get batting scorecards for the team
        inning_number = 1 if team_side == "a" else 2
        result = await db.execute(
            select(BattingScorecard).where(
                (BattingScorecard.game_id == game_id)
                & (BattingScorecard.inning_number == inning_number)
            )
        )
        scorecards = result.scalars().all()

        if not scorecards:
            raise HTTPException(status_code=400, detail=f"No batting data for team {team_side}")

        # Generate drills for each player
        team_drills = []
        for scorecard in scorecards:
            player = scorecard.player
            player_profile = {
                "player_id": player.id,
                "player_name": player.name,
                "runs": scorecard.runs_scored,
                "deliveries": scorecard.deliveries_faced,
                "is_dismissed": scorecard.is_dismissed,
                "dismissal_type": scorecard.dismissal_type,
                "pace_weakness": 40.0 if scorecard.runs_scored < 20 else 25.0,
                "spin_weakness": 35.0 if scorecard.runs_scored < 20 else 20.0,
                "dot_ball_weakness": 50.0 if scorecard.deliveries_faced > 30 else 30.0,
                "yorker_weakness": 45.0 if scorecard.is_dismissed else 30.0,
                "aggressive_weakness": 30.0,
                "boundary_weakness": 25.0 if scorecard.runs_scored < 30 else 10.0,
            }

            plan = TrainingDrillGenerator.generate_drills_for_player(
                player_id=player.id,
                player_name=player.name,
                player_profile=player_profile,
            )

            team_drills.append(
                {
                    "player_id": player.id,
                    "player_name": player.name,
                    "performance": {
                        "runs": scorecard.runs_scored,
                        "deliveries": scorecard.deliveries_faced,
                        "is_dismissed": scorecard.is_dismissed,
                    },
                    "drill_plan": {
                        "total_drills": len(plan.drills),
                        "high_priority": plan.high_priority_count,
                        "medium_priority": plan.medium_priority_count,
                        "total_weekly_hours": plan.total_weekly_hours,
                        "drills": [
                            {
                                "name": d.name,
                                "category": d.category.value,
                                "severity": d.severity.value,
                                "focus_area": d.focus_area,
                                "recommended_frequency": d.recommended_frequency,
                            }
                            for d in plan.drills[:3]  # Top 3 drills
                        ],
                    },
                }
            )

        return {
            "status": "success",
            "game_id": game_id,
            "team_side": team_side,
            "players_count": len(team_drills),
            "team_drills": team_drills,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating team drills: {e!s}")


@router.get("/drills/categories")
async def get_drill_categories():
    """
    Get list of all drill categories and examples.

    Returns:
        Available drill categories and templates
    """
    categories = {}
    for category, templates in TrainingDrillGenerator.DRILL_TEMPLATES.items():
        categories[category.value] = {
            "name": category.value.replace("_", " ").title(),
            "template_count": len(templates),
            "templates": [
                {
                    "name": t.name,
                    "description": t.description,
                    "duration": t.duration_minutes,
                    "difficulty": t.difficulty,
                    "focus": t.focus_area,
                }
                for t in templates
            ],
        }

    return {
        "status": "success",
        "categories": categories,
        "total_categories": len(categories),
    }
