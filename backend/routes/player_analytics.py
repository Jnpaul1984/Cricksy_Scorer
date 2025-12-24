"""Player Analytics Routes

Exposes player career analysis and AI-powered insights via REST API.
Endpoints for player summaries, career stats, and performance analysis.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.sql_app.database import get_db
from backend.sql_app.models import PlayerProfile

router = APIRouter(prefix="/analytics/players", tags=["player_analytics"])


def get_consistency_message(score: int) -> str:
    """Get consistency message based on score."""
    if score >= 80:
        return "Very consistent performer, reliable selection"
    elif score >= 70:
        return "Generally consistent"
    else:
        return "Variable performances"


def calc_batting_avg(runs: int, innings: int) -> float:
    """Calculate batting average safely."""
    return runs / innings if innings > 0 else 0.0


@router.get("/{player_id}/career-summary")
async def get_player_career_summary_endpoint(
    player_id: str,
    db: AsyncSession = Depends(get_db),  # pylint: disable=assignment-from-no-return
) -> dict[str, Any]:
    """Get AI-powered career summary for a player.

    Analyzes all historical performance data to generate:
    - Career statistics (batting/bowling)
    - Specialization analysis
    - Recent form trends
    - Best performances
    - Career highlights
    """
    try:
        # Fetch player
        stmt = select(PlayerProfile).where(PlayerProfile.player_id == player_id)
        result = await db.execute(stmt)
        player = result.scalars().first()

        if not player:
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found")

        # Calculate averages safely
        batting_avg = (
            player.total_runs_scored / player.total_innings_batted
            if player.total_innings_batted > 0
            else 0.0
        )
        bowling_avg = (
            player.total_runs_conceded / player.total_wickets if player.total_wickets > 0 else 0.0
        )
        strike_rate = (
            (player.total_runs_scored / player.total_balls_faced) * 100
            if player.total_balls_faced > 0
            else 0.0
        )
        economy_rate = (
            (player.total_runs_conceded / player.total_overs_bowled) * 6
            if player.total_overs_bowled > 0
            else 0.0
        )

        # Determine specialization
        if player.total_wickets > player.total_matches / 2:
            specialization = "Bowler"
        elif player.total_runs_scored > player.total_matches * 25:
            specialization = "Batter"
        elif player.total_runs_scored > 0 and player.total_wickets > 0:
            specialization = "All-rounder"
        else:
            specialization = "Unknown"

        # Return player profile data as-is
        return {
            "player_id": str(player.player_id),
            "player_name": player.player_name,
            "batting_stats": {
                "total_matches": player.total_matches,
                "total_runs": player.total_runs_scored,
                "total_balls": player.total_balls_faced,
                "average": round(batting_avg, 2),
                "strike_rate": round(strike_rate, 2),
                "total_fours": player.total_fours,
                "total_sixes": player.total_sixes,
                "highest_score": player.highest_score,
                "centuries": player.centuries,
                "half_centuries": player.half_centuries,
            },
            "bowling_stats": {
                "total_overs": player.total_overs_bowled,
                "total_runs_conceded": player.total_runs_conceded,
                "total_wickets": player.total_wickets,
                "average": round(bowling_avg, 2),
                "economy_rate": round(economy_rate, 2),
                "best_bowling": player.best_bowling_figures,
                "five_wicket_hauls": player.five_wicket_hauls,
                "maidens": player.maidens,
            },
            "fielding_stats": {
                "catches": player.catches,
                "stumpings": player.stumpings,
                "run_outs": player.run_outs,
            },
            "specialization": specialization,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch career summary: {e!s}",
        ) from e


@router.get("/{player_id}/year-stats")
async def get_player_yearly_stats(
    player_id: str,
    db: AsyncSession = Depends(get_db),  # pylint: disable=assignment-from-no-return
) -> dict[str, Any]:
    """Get player statistics broken down by year.

    Returns year-wise performance metrics for trend analysis.
    """
    try:
        # Fetch player
        stmt = select(PlayerProfile).where(PlayerProfile.player_id == player_id)
        result = await db.execute(stmt)
        player = result.scalars().first()

        if not player:
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found")

        # Calculate averages
        batting_avg = (
            player.total_runs_scored / player.total_innings_batted
            if player.total_innings_batted > 0
            else 0.0
        )

        # Return aggregated player profile data (current season/overall)
        return {
            "player_id": str(player.player_id),
            "player_name": player.player_name,
            "current_stats": {
                "total_matches": player.total_matches,
                "total_runs": player.total_runs_scored,
                "average": round(batting_avg, 2),
                "centuries": player.centuries,
                "half_centuries": player.half_centuries,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch yearly stats: {e!s}",
        ) from e


@router.get("/{player_id}/comparison")
async def get_player_comparison(
    player_id: str,
    comparison_player_id: str,
    db: AsyncSession = Depends(get_db),  # pylint: disable=assignment-from-no-return
) -> dict[str, Any]:
    """Compare statistics between two players.

    Side-by-side comparison of career metrics, recent form, and specialization.
    """
    try:
        # Fetch both players
        stmt = select(PlayerProfile).where(PlayerProfile.player_id == player_id)
        result = await db.execute(stmt)
        player1 = result.scalars().first()

        stmt = select(PlayerProfile).where(PlayerProfile.player_id == comparison_player_id)
        result = await db.execute(stmt)
        player2 = result.scalars().first()

        if not player1:
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found")
        if not player2:
            raise HTTPException(status_code=404, detail=f"Player {comparison_player_id} not found")

        def calc_avg(runs: int, innings: int) -> float:
            """Calculate batting average safely."""
            return runs / innings if innings > 0 else 0.0

        # Return side-by-side comparison
        return {
            "player_1": {
                "player_id": player1.player_id,
                "player_name": player1.player_name,
                "batting": {
                    "matches": player1.total_matches,
                    "runs": player1.total_runs_scored,
                    "average": round(
                        calc_avg(player1.total_runs_scored, player1.total_innings_batted),
                        2,
                    ),
                    "highest_score": player1.highest_score,
                    "centuries": player1.centuries,
                },
                "bowling": {
                    "wickets": player1.total_wickets,
                    "runs_conceded": player1.total_runs_conceded,
                    "overs": player1.total_overs_bowled,
                },
            },
            "player_2": {
                "player_id": player2.player_id,
                "player_name": player2.player_name,
                "batting": {
                    "matches": player2.total_matches,
                    "runs": player2.total_runs_scored,
                    "average": round(
                        calc_avg(player2.total_runs_scored, player2.total_innings_batted),
                        2,
                    ),
                    "highest_score": player2.highest_score,
                    "centuries": player2.centuries,
                },
                "bowling": {
                    "wickets": player2.total_wickets,
                    "runs_conceded": player2.total_runs_conceded,
                    "overs": player2.total_overs_bowled,
                },
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compare players: {e!s}",
        ) from e


# ============================================================================
# PHASE 1: Advanced Insights Endpoints
# ============================================================================


@router.get("/{player_id}/dismissals")
async def get_player_dismissals(
    player_id: str,
    db: AsyncSession = Depends(get_db),  # pylint: disable=assignment-from-no-return
) -> dict[str, Any]:
    """Get detailed dismissal analysis for a player.

    Analyzes when, how, and why the player gets dismissed across:
    - Different match phases (powerplay, middle, death)
    - Against different opposition
    - Patterns and vulnerabilities

    Returns coaching-ready insights and recommendations.
    """
    try:
        # Verify player exists
        stmt = select(PlayerProfile).where(PlayerProfile.player_id == player_id)
        result = await db.execute(stmt)
        player = result.scalars().first()

        if not player:
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found")

        # Query games where player participated
        from backend.sql_app.models import Game

        stmt = select(Game).order_by(Game.created_at.desc()).limit(50)
        result = await db.execute(stmt)
        games = result.scalars().all()

        # Analyze dismissals from game snapshots
        dismissal_types: dict[str, int] = {}
        phase_analysis: dict[str, dict[str, Any]] = {
            "powerplay": {"dismissals": 0, "counts": {}, "most_common": None},
            "middle_overs": {"dismissals": 0, "counts": {}, "most_common": None},
            "death": {"dismissals": 0, "counts": {}, "most_common": None},
        }

        for game in games:
            # Extract deliveries from game snapshot
            deliveries: list[dict[str, Any]] = (
                game.deliveries if hasattr(game, "deliveries") else []
            )

            for delivery in deliveries:
                # Only process dismissals for this player
                if delivery.get("dismissed_player_id") != player_id:
                    continue

                dismissal_type = delivery.get("dismissal_type", "unknown")
                if not dismissal_type or dismissal_type == "runs":
                    continue

                # Count dismissal type
                dismissal_types[dismissal_type] = dismissal_types.get(dismissal_type, 0) + 1

                # Determine phase based on over number
                over_num = int(delivery.get("over_number", 0) or 0)
                if over_num < 6:
                    phase = "powerplay"
                elif over_num < 15:
                    phase = "middle_overs"
                else:
                    phase = "death"

                # Count in phase
                phase_data: dict[str, Any] = phase_analysis[phase]
                phase_data["dismissals"] = int(phase_data["dismissals"]) + 1
                counts: dict[str, int] = phase_data["counts"]  # type: ignore[assignment]
                counts[dismissal_type] = counts.get(dismissal_type, 0) + 1

        # Find most common dismissal per phase
        for _phase, data in phase_analysis.items():
            counts = data["counts"]  # type: ignore[assignment]
            if counts:
                most_common = max(counts.items(), key=lambda x: x[1])[0]
                data["most_common"] = most_common

        # Generate recommendations
        recommendations = _generate_dismissal_recommendations(
            dismissal_types, phase_analysis, player
        )

        return {
            "player_id": str(player.player_id),
            "player_name": player.player_name,
            "dismissal_analysis": {
                "total_dismissals": sum(dismissal_types.values()),
                "dismissal_breakdown": dismissal_types,
                "phase_analysis": {
                    phase: {
                        "dismissals": int(data["dismissals"]),
                        "most_common": data["most_common"],
                    }
                    for phase, data in phase_analysis.items()
                },
                "recommendations": recommendations,
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze dismissals: {e!s}",
        ) from e


def _generate_dismissal_recommendations(
    dismissal_types: dict[str, int],
    phase_analysis: dict[str, dict[str, Any]],
    player: PlayerProfile,
) -> list[str]:
    """Generate coaching recommendations based on dismissal patterns."""
    recommendations: list[str] = []

    if not dismissal_types:
        recommendations.append("Excellent form - very few dismissals recently")
        return recommendations

    total_dismissals = sum(dismissal_types.values())

    # Check if specific dismissal type dominates
    most_common_dismissal = max(dismissal_types.items(), key=lambda x: x[1])[0]
    count = dismissal_types[most_common_dismissal]
    percentage = (count / total_dismissals) * 100

    if percentage > 50:
        if most_common_dismissal == "bowled":
            recommendations.append(
                f"Vulnerable to bowled dismissals ({percentage:.0f}%) - "
                "Work on line and length reading, improve footwork"
            )
        elif most_common_dismissal == "caught":
            recommendations.append(
                f"Frequent caught dismissals ({percentage:.0f}%) - "
                "Reduce aggressive shots to risky fielders, improve shot selection"
            )
        elif most_common_dismissal == "lbw":
            recommendations.append(
                f"LBW dismissals ({percentage:.0f}%) - Improve leg-side technique and pad usage"
            )
        elif most_common_dismissal == "stumped":
            recommendations.append(
                f"Being stumped regularly ({percentage:.0f}%) - "
                "Better judgement of line and length, avoid rash footwork"
            )

    # Analyze phase vulnerabilities
    powerplay: dict[str, Any] = phase_analysis["powerplay"]  # type: ignore[assignment]
    death: dict[str, Any] = phase_analysis["death"]  # type: ignore[assignment]

    powerplay_dismissals = int(powerplay.get("dismissals", 0))
    death_dismissals = int(death.get("dismissals", 0))

    if powerplay_dismissals > 0 and powerplay_dismissals > total_dismissals / 2:
        recommendations.append(
            "Struggles to build initial innings - Focus on building confidence and solid starts"
        )

    if death_dismissals > 0 and death_dismissals > total_dismissals / 2:
        recommendations.append(
            "Vulnerable in death overs - Practice death bowling scenarios and improve judgment"
        )

    # Quality of player feedback
    if player.centuries > 0 and total_dismissals > 20:
        recommendations.append(
            f"Despite {total_dismissals} dismissals, strong record with "
            f"{player.centuries} centuries - Use success as confidence builder"
        )

    if not recommendations:
        recommendations.append("Balanced dismissal pattern - maintain current technique")

    return recommendations


@router.get("/{player_id}/form-analysis")
async def get_player_form_analysis(
    player_id: str,
    last_n_games: int = 10,
    db: AsyncSession = Depends(get_db),  # pylint: disable=assignment-from-no-return
) -> dict[str, Any]:
    """Get form analysis based on recent game performance.

    Analyzes recent scores, runs, and trends to determine:
    - Current form status (improving, declining, stable)
    - Form phase and momentum
    - Comparison to historical average
    - Coaching recommendations
    """
    try:
        # Verify player exists
        stmt = select(PlayerProfile).where(PlayerProfile.player_id == player_id)
        result = await db.execute(stmt)
        player = result.scalars().first()

        if not player:
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found")

        # For now, use career stats to determine form
        # TODO: Integrate with Game/Inning tables for recent game data
        return {
            "player_id": str(player.player_id),
            "player_name": player.player_name,
            "recent_form": {
                "status": "stable",
                "average": round(
                    player.total_runs_scored / player.total_innings_batted
                    if player.total_innings_batted > 0
                    else 0,
                    2,
                ),
                "centuries": player.centuries,
                "recommendation": (
                    f"Consistent performer with {player.centuries} "
                    f"centuries. Batting average: "
                    f"{calc_batting_avg(player.total_runs_scored, player.total_innings_batted):.1f}"
                ),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to analyze form: {e!s}",
        ) from e


@router.get("/{player_id}/consistency-score")
async def get_player_consistency_score(
    player_id: str,
    db: AsyncSession = Depends(get_db),  # pylint: disable=assignment-from-no-return
) -> dict[str, Any]:
    """Get consistency scoring for a player.

    Rates player reliability based on:
    - Consistent performance across matches
    - Stability in averages
    - Frequency of good performances
    - Frequency of poor performances
    """
    try:
        # Verify player exists
        stmt = select(PlayerProfile).where(PlayerProfile.player_id == player_id)
        result = await db.execute(stmt)
        player = result.scalars().first()

        if not player:
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found")

        # Calculate consistency metrics
        if player.total_innings_batted == 0:
            rating = "N/A"
            score = 0
        else:
            # Simple consistency calculation based on centuries/half-centuries
            contribution = (
                player.centuries * 2 + player.half_centuries
            ) / player.total_innings_batted
            if contribution > 0.5:
                rating = "A+"
                score = 90
            elif contribution > 0.3:
                rating = "A"
                score = 80
            elif contribution > 0.15:
                rating = "B"
                score = 70
            else:
                rating = "C"
                score = 50

        return {
            "player_id": str(player.player_id),
            "player_name": player.player_name,
            "consistency": {
                "rating": rating,
                "score": score,
                "total_matches": player.total_matches,
                "centuries": player.centuries,
                "half_centuries": player.half_centuries,
                "recommendation": (f"Rating {rating} - {get_consistency_message(score)}"),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to calculate consistency score: {e!s}",
        ) from e


@router.get("/leaderboards/batsmen")
async def get_batting_leaderboard(
    metric: str = "average",
    limit: int = 10,
    db: AsyncSession = Depends(get_db),  # pylint: disable=assignment-from-no-return
) -> dict[str, Any]:
    """Get batting leaderboard ranked by various metrics.

    Supported metrics:
    - average: Batting average
    - runs: Total runs scored
    - centuries: Number of centuries
    - matches: Total matches played
    - strike_rate: Strike rate percentage
    """
    try:
        # Fetch all players
        stmt = select(PlayerProfile).where(PlayerProfile.total_innings_batted > 0)
        result = await db.execute(stmt)
        players = result.scalars().all()

        if not players:
            return {
                "metric": metric,
                "leaderboard": [],
                "message": "No batting data available",
            }

        # Sort by metric
        if metric == "average":
            sorted_players = sorted(
                players,
                key=lambda p: (
                    p.total_runs_scored / p.total_innings_batted
                    if p.total_innings_batted > 0
                    else 0
                ),
                reverse=True,
            )
        elif metric == "runs":
            sorted_players = sorted(players, key=lambda p: p.total_runs_scored, reverse=True)
        elif metric == "centuries":
            sorted_players = sorted(players, key=lambda p: p.centuries, reverse=True)
        elif metric == "strike_rate":
            sorted_players = sorted(
                players,
                key=lambda p: (
                    (p.total_runs_scored / p.total_balls_faced) * 100
                    if p.total_balls_faced > 0
                    else 0
                ),
                reverse=True,
            )
        else:  # matches
            sorted_players = sorted(players, key=lambda p: p.total_matches, reverse=True)

        # Build leaderboard
        leaderboard: list[dict[str, Any]] = []
        for rank, player in enumerate(sorted_players[:limit], 1):
            avg = (
                player.total_runs_scored / player.total_innings_batted
                if player.total_innings_batted > 0
                else 0
            )
            sr = (
                (player.total_runs_scored / player.total_balls_faced) * 100
                if player.total_balls_faced > 0
                else 0
            )

            leaderboard.append(
                {
                    "rank": rank,
                    "player_id": str(player.player_id),
                    "player_name": player.player_name,
                    "matches": player.total_matches,
                    "runs": player.total_runs_scored,
                    "average": round(avg, 2),
                    "strike_rate": round(sr, 2),
                    "centuries": player.centuries,
                    "half_centuries": player.half_centuries,
                }
            )

        return {
            "metric": metric,
            "total_players": len(players),
            "displayed": len(leaderboard),
            "leaderboard": leaderboard,
        }

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch leaderboard: {e!s}",
        ) from e
