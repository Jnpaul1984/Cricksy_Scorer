"""
Dismissal Patterns API Routes

REST endpoints for dismissal pattern analysis and insights.
"""

from fastapi import APIRouter, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.services.dismissal_pattern_analyzer import (
    DismissalPatternAnalyzer,
    DismissalRecord,
    MatchPhase,
)

router = APIRouter(prefix="/dismissal-patterns", tags=["dismissal_patterns"])


@router.get("/players/{player_id}/analysis")
async def get_player_dismissal_analysis(
    player_id: str,
    db: AsyncSession,
):
    """
    Get comprehensive dismissal pattern analysis for a player.

    Analyzes all dismissals from batting scorecards to identify
    recurring vulnerabilities and patterns.
    """
    try:
        # Fetch player
        result = await db.execute(select(Player).where(Player.id == player_id))
        player = result.scalars().first()
        if not result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player {player_id} not found",
            )

        # Fetch batting scorecards (all dismissals)
        result = await db.execute(
            select(BattingScorecard)
            .where(BattingScorecard.player_id == player_id)
            .where(BattingScorecard.is_dismissed == True)
            .order_by(BattingScorecard.created_at.desc())
        )
        scorecards = result.scalars().all()

        # Convert to dismissal records
        dismissals = []
        for sc in scorecards:
            # Determine match phase from overs
            overs_faced = sc.deliveries_faced // 6
            if overs_faced <= 6:
                phase = MatchPhase.POWERPLAY
            elif overs_faced <= 15:
                phase = MatchPhase.MIDDLE_OVERS
            else:
                phase = MatchPhase.DEATH_OVERS

            dismissal = DismissalRecord(
                dismissal_id=sc.id,
                dismissal_type=sc.dismissal_type or "unknown",
                bowler_name=sc.bowler_name if hasattr(sc, "bowler_name") else None,
                bowler_id=None,
                delivery_type=None,  # Would need additional data
                line=None,  # Would need additional data
                length=None,  # Would need additional data
                match_phase=phase,
                runs_at_dismissal=sc.runs_scored or 0,
                deliveries_faced=sc.deliveries_faced or 0,
                boundary_attempt=False,  # Would need additional data
                aggressive=False,  # Would need additional data
            )
            dismissals.append(dismissal)

        # Analyze
        profile = DismissalPatternAnalyzer.analyze_player_dismissals(
            player_id=player_id,
            player_name=player.name if player else "Unknown",
            dismissals=dismissals,
        )

        return {
            "status": "success",
            "player_id": player_id,
            "player_name": player.name if player else "Unknown",
            "analysis": {
                "total_dismissals": profile.total_dismissals,
                "dismissals_by_type": profile.dismissals_by_type,
                "dismissals_by_phase": profile.dismissals_by_phase,
                "dismissals_by_delivery": profile.dismissals_by_delivery,
                "overall_vulnerability_score": profile.overall_vulnerability_score,
                "primary_vulnerability": profile.primary_vulnerability,
                "secondary_vulnerabilities": profile.secondary_vulnerabilities,
                "top_patterns": [
                    {
                        "pattern_name": p.pattern_name,
                        "pattern_type": p.pattern_type,
                        "dismissal_count": p.dismissal_count,
                        "dismissal_percentage": p.dismissal_percentage,
                        "severity": p.severity,
                        "context": p.context,
                        "recommendation": p.recommendation,
                    }
                    for p in profile.top_patterns
                ],
                "critical_situations": [
                    {
                        "situation_type": s.situation_type,
                        "dismissal_count": s.dismissal_count,
                        "risk_level": s.risk_level,
                        "scenario_description": s.scenario_description,
                    }
                    for s in profile.critical_situations
                ],
                "improvement_areas": profile.improvement_areas,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing dismissal patterns: {e!s}",
        )


@router.get("/games/{game_id}/team-{team_side}/analysis")
async def get_team_dismissal_analysis(
    game_id: str,
    team_side: str,
    db: AsyncSession,
):
    """
    Get team-level dismissal pattern analysis post-match.

    Analyzes all team members' dismissal patterns from a specific match.
    Identifies vulnerable players and common team weaknesses.
    """
    try:
        # Validate team_side
        if team_side not in ["a", "b"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="team_side must be 'a' or 'b'",
            )

        # Fetch game
        result = await db.execute(select(Game).where(Game.id == game_id))
        game = result.scalars().first()
        if not game:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Game {game_id} not found",
            )

        # Fetch batting scorecards for team
        inning_number = 1 if team_side == "a" else 2
        result = await db.execute(
            select(BattingScorecard)
            .where(BattingScorecard.game_id == game_id)
            .where(BattingScorecard.inning_number == inning_number)
            .where(BattingScorecard.is_dismissed == True)
        )
        scorecards = result.scalars().all()

        if not scorecards:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No dismissal data found for team in this game",
            )

        # Group by player
        players_dismissals: dict[str, list] = {}
        player_names: dict[str, str] = {}

        for sc in scorecards:
            if sc.player_id not in players_dismissals:
                players_dismissals[sc.player_id] = []
                player_names[sc.player_id] = sc.player_name or "Unknown"

            overs_faced = sc.deliveries_faced // 6
            if overs_faced <= 6:
                phase = MatchPhase.POWERPLAY
            elif overs_faced <= 15:
                phase = MatchPhase.MIDDLE_OVERS
            else:
                phase = MatchPhase.DEATH_OVERS

            dismissal = DismissalRecord(
                dismissal_id=sc.id,
                dismissal_type=sc.dismissal_type or "unknown",
                match_phase=phase,
                runs_at_dismissal=sc.runs_scored or 0,
                deliveries_faced=sc.deliveries_faced or 0,
            )
            players_dismissals[sc.player_id].append(dismissal)

        # Analyze each player
        team_profiles = []
        for player_id, dismissals in players_dismissals.items():
            profile = DismissalPatternAnalyzer.analyze_player_dismissals(
                player_id=player_id,
                player_name=player_names.get(player_id, "Unknown"),
                dismissals=dismissals,
            )
            team_profiles.append(profile)

        # Analyze team context
        team_context = DismissalPatternAnalyzer.analyze_team_dismissals(
            team_id=team_side,
            team_name=f"Team {team_side.upper()}",
            player_profiles=team_profiles,
        )

        return {
            "status": "success",
            "game_id": game_id,
            "team_side": team_side,
            "team_analysis": {
                "total_team_dismissals": team_context.total_team_dismissals,
                "vulnerable_players": [
                    {"player_name": name, "vulnerability_score": score}
                    for name, score in team_context.vulnerable_players
                ],
                "phase_vulnerability": team_context.phase_vulnerability,
                "team_recommendations": team_context.team_recommendations,
            },
            "player_details": [
                {
                    "player_name": p.player_name,
                    "total_dismissals": p.total_dismissals,
                    "vulnerability_score": p.overall_vulnerability_score,
                    "primary_vulnerability": p.primary_vulnerability,
                    "top_patterns": [
                        {
                            "pattern_name": pat.pattern_name,
                            "severity": pat.severity,
                            "dismissal_count": pat.dismissal_count,
                        }
                        for pat in p.top_patterns[:2]
                    ],
                }
                for p in team_profiles
            ],
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error analyzing team dismissal patterns: {e!s}",
        )


@router.get("/players/{player_id}/vulnerability-score")
async def get_player_vulnerability_score(
    player_id: str,
    db: AsyncSession,
):
    """
    Get quick vulnerability score for a player.

    Returns a 0-100 score indicating overall dismissal vulnerability.
    """
    try:
        # Fetch player
        result = await db.execute(select(Player).where(Player.id == player_id))
        player = result.scalars().first()
        if not player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player {player_id} not found",
            )

        # Fetch dismissals
        result = await db.execute(
            select(BattingScorecard)
            .where(BattingScorecard.player_id == player_id)
            .where(BattingScorecard.is_dismissed == True)
        )
        scorecards = result.scalars().all()

        if not scorecards:
            return {
                "status": "success",
                "player_id": player_id,
                "player_name": player.name,
                "vulnerability_score": 0.0,
                "risk_level": "low",
                "message": "No dismissal data available",
            }

        # Build dismissal records
        dismissals = []
        for sc in scorecards:
            overs_faced = sc.deliveries_faced // 6
            if overs_faced <= 6:
                phase = MatchPhase.POWERPLAY
            elif overs_faced <= 15:
                phase = MatchPhase.MIDDLE_OVERS
            else:
                phase = MatchPhase.DEATH_OVERS

            dismissal = DismissalRecord(
                dismissal_id=sc.id,
                dismissal_type=sc.dismissal_type or "unknown",
                match_phase=phase,
                runs_at_dismissal=sc.runs_scored or 0,
                deliveries_faced=sc.deliveries_faced or 0,
            )
            dismissals.append(dismissal)

        # Analyze
        profile = DismissalPatternAnalyzer.analyze_player_dismissals(
            player_id=player_id,
            player_name=player.name,
            dismissals=dismissals,
        )

        # Risk level
        if profile.overall_vulnerability_score >= 70:
            risk_level = "critical"
        elif profile.overall_vulnerability_score >= 50:
            risk_level = "high"
        elif profile.overall_vulnerability_score >= 30:
            risk_level = "medium"
        else:
            risk_level = "low"

        return {
            "status": "success",
            "player_id": player_id,
            "player_name": player.name,
            "vulnerability_score": profile.overall_vulnerability_score,
            "risk_level": risk_level,
            "primary_vulnerability": profile.primary_vulnerability,
            "total_dismissals": profile.total_dismissals,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating vulnerability score: {e!s}",
        )


@router.get("/players/{player_id}/trend")
async def get_player_dismissal_trend(
    player_id: str,
    period: str = "last_10",
    db: AsyncSession = None,
):
    """
    Get dismissal trend for a player over recent matches.

    Helps identify if dismissal patterns are improving or declining.
    """
    try:
        if period not in ["last_5", "last_10", "last_20"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="period must be 'last_5', 'last_10', or 'last_20'",
            )

        # Fetch player
        result = await db.execute(select(Player).where(Player.id == player_id))
        player = result.scalars().first()
        if not player:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Player {player_id} not found",
            )

        # Fetch dismissals
        result = await db.execute(
            select(BattingScorecard)
            .where(BattingScorecard.player_id == player_id)
            .where(BattingScorecard.is_dismissed == True)
            .order_by(BattingScorecard.created_at.desc())
        )
        scorecards = result.scalars().all()

        dismissals = [
            DismissalRecord(
                dismissal_id=sc.id,
                dismissal_type=sc.dismissal_type or "unknown",
                runs_at_dismissal=sc.runs_scored or 0,
                deliveries_faced=sc.deliveries_faced or 0,
            )
            for sc in scorecards
        ]

        # Get trend
        trend = DismissalPatternAnalyzer.get_dismissal_trend(dismissals, period)

        return {
            "status": "success",
            "player_id": player_id,
            "player_name": player.name,
            "trend": {
                "period": trend.period,
                "dismissal_count": trend.dismissal_count,
                "average_runs_at_dismissal": trend.average_runs_at_dismissal,
                "average_deliveries_faced": trend.average_deliveries_faced,
                "trend_direction": trend.trend_direction,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error calculating dismissal trend: {e!s}",
        )
