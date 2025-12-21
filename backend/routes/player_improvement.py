"""
Player Improvement Routes

REST API endpoints for player improvement tracking:
- GET /players/{player_id}/improvement-trend: Month-over-month trend analysis
- GET /players/{player_id}/monthly-stats: Aggregated monthly statistics
- GET /players/{player_id}/improvement-summary: Comprehensive improvement analysis
"""

from typing import Any
from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_
from datetime import datetime, timedelta

from backend.services.player_improvement_tracker import (
    PlayerImprovementTracker,
)

router = APIRouter(prefix="/player-analytics", tags=["player_improvement"])


@router.get("/players/{player_id}/monthly-stats")
async def get_monthly_stats(
    player_id: str,
    limit_months: int = 6,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    Get aggregated monthly statistics for a player.

    Returns:
    {
        "player_id": str,
        "months": [
            {
                "month": "2024-12",
                "total_runs": 150,
                "total_deliveries": 180,
                "matches_played": 4,
                "innings_played": 4,
                "dismissals": 1,
                "boundaries_4": 8,
                "boundaries_6": 2,
                "batting_average": 37.5,
                "strike_rate": 83.33,
                "consistency_score": 75.2,
                "role": "middle_order",
            },
            ...
        ],
    }
    """
    if not db:
        raise HTTPException(status_code=500, detail="Database session not available")

    try:
        # Fetch player
        stmt = select(Player).where(Player.id == player_id)
        result = await db.execute(stmt)
        player = result.scalars().first()

        if not player:
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found")

        # Fetch batting scorecards for this player (last N months)
        cutoff_date = datetime.now() - timedelta(days=30 * limit_months)
        stmt = (
            select(BattingScorecard)
            .where(
                and_(
                    BattingScorecard.player_id == player_id,
                    BattingScorecard.created_at >= cutoff_date,
                )
            )
            .order_by(BattingScorecard.created_at.desc())
        )
        result = await db.execute(stmt)
        scorecards = result.scalars().all()

        # Group by month
        monthly_data: dict[str, list] = {}
        for scorecard in scorecards:
            month = scorecard.created_at.strftime("%Y-%m")
            if month not in monthly_data:
                monthly_data[month] = []
            monthly_data[month].append(
                {
                    "runs_scored": scorecard.runs,
                    "deliveries_faced": scorecard.balls_faced,
                    "is_dismissed": scorecard.is_out,
                    "boundaries_4": scorecard.fours or 0,
                    "boundaries_6": scorecard.sixes or 0,
                    "role": scorecard.role or "unknown",
                }
            )

        # Calculate monthly stats
        monthly_stats = []
        for month in sorted(monthly_data.keys(), reverse=True):
            stats = PlayerImprovementTracker.calculate_monthly_stats(
                monthly_data[month],
                month=month,
            )
            if stats:
                monthly_stats.append(
                    {
                        "month": stats.month,
                        "total_runs": stats.total_runs,
                        "total_deliveries": stats.total_deliveries,
                        "matches_played": stats.matches_played,
                        "innings_played": stats.innings_played,
                        "dismissals": stats.dismissals,
                        "boundaries_4": stats.boundaries_4,
                        "boundaries_6": stats.boundaries_6,
                        "batting_average": round(stats.batting_average, 2),
                        "strike_rate": round(stats.strike_rate, 2),
                        "consistency_score": round(stats.consistency_score, 1),
                        "role": stats.role,
                    }
                )

        return {
            "player_id": player_id,
            "player_name": player.name if player else "Unknown",
            "months": monthly_stats,
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Monthly stats error: {e!s}")


@router.get("/players/{player_id}/improvement-trend")
async def get_improvement_trend(
    player_id: str,
    months: int = 3,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    Get improvement trend (month-over-month changes).

    Returns:
    {
        "player_id": str,
        "trend_periods": [
            {
                "from_month": "2024-10",
                "to_month": "2024-11",
                "metrics": {
                    "batting_average": {
                        "metric_name": "Batting Average",
                        "previous_value": 35.2,
                        "current_value": 37.5,
                        "absolute_change": 2.3,
                        "percentage_change": 6.5,
                        "trend": "improving",
                        "confidence": 0.8,
                    },
                    ...
                },
            },
            ...
        ],
        "overall_improvement_score": 75.0,  # 0-100
    }
    """
    if not db:
        raise HTTPException(status_code=500, detail="Database session not available")

    try:
        # Fetch player
        stmt = select(Player).where(Player.id == player_id)
        result = await db.execute(stmt)
        player = result.scalars().first()

        if not player:
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found")

        # Fetch batting scorecards
        cutoff_date = datetime.now() - timedelta(days=30 * (months + 1))
        stmt = (
            select(BattingScorecard)
            .where(
                and_(
                    BattingScorecard.player_id == player_id,
                    BattingScorecard.created_at >= cutoff_date,
                )
            )
            .order_by(BattingScorecard.created_at.desc())
        )
        result = await db.execute(stmt)
        scorecards = result.scalars().all()

        # Group by month
        monthly_data: dict[str, list] = {}
        for scorecard in scorecards:
            month = scorecard.created_at.strftime("%Y-%m")
            if month not in monthly_data:
                monthly_data[month] = []
            monthly_data[month].append(
                {
                    "runs_scored": scorecard.runs,
                    "deliveries_faced": scorecard.balls_faced,
                    "is_dismissed": scorecard.is_out,
                    "boundaries_4": scorecard.fours or 0,
                    "boundaries_6": scorecard.sixes or 0,
                    "role": scorecard.role or "unknown",
                }
            )

        # Calculate monthly stats
        monthly_stats = []
        for month in sorted(monthly_data.keys(), reverse=True)[: months + 1]:
            stats = PlayerImprovementTracker.calculate_monthly_stats(
                monthly_data[month],
                month=month,
            )
            if stats:
                monthly_stats.append(stats)

        monthly_stats.reverse()  # Oldest first

        # Calculate trends
        trend_periods = []
        improving_count = 0
        for i in range(1, len(monthly_stats)):
            metrics = PlayerImprovementTracker.calculate_improvement_metrics(
                monthly_stats[i - 1],
                monthly_stats[i],
            )

            trend_periods.append(
                {
                    "from_month": monthly_stats[i - 1].month,
                    "to_month": monthly_stats[i].month,
                    "metrics": {
                        k: {
                            "metric_name": v.metric_name,
                            "previous_value": v.previous_value,
                            "current_value": v.current_value,
                            "absolute_change": v.absolute_change,
                            "percentage_change": v.percentage_change,
                            "trend": v.trend,
                            "confidence": round(v.confidence, 2),
                        }
                        for k, v in metrics.items()
                    },
                }
            )

            # Count improving metrics
            for metric in metrics.values():
                if metric.trend == "improving":
                    improving_count += 1

        # Overall score (0-100)
        total_metrics = len(trend_periods) * 5 if trend_periods else 1
        overall_score = (improving_count / total_metrics) * 100 if total_metrics > 0 else 0

        return {
            "player_id": player_id,
            "player_name": player.name if player else "Unknown",
            "trend_periods": trend_periods,
            "overall_improvement_score": round(overall_score, 1),
            "periods_analyzed": len(trend_periods),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Improvement trend error: {e!s}")


@router.get("/players/{player_id}/improvement-summary")
async def get_improvement_summary(
    player_id: str,
    months: int = 6,
    db: AsyncSession | None = None,
) -> dict[str, Any]:
    """
    Get comprehensive improvement summary with highlights and recommendations.

    Returns:
    {
        "player_id": str,
        "status": "success",
        "overall_trend": "accelerating" | "stable" | "declining",
        "improvement_score": 75.0,  # 0-100
        "latest_month": "2024-12",
        "months_analyzed": 6,
        "latest_stats": {
            "batting_average": 37.5,
            "strike_rate": 83.33,
            "consistency_score": 75.2,
            "matches_played": 4,
            "innings_played": 4,
            "role": "middle_order",
        },
        "highlights": [
            "📈 Batting average improved 6.5% to 37.5",
            "⚡ Strike rate improved to 83.33 (+3.2%)",
            ...
        ],
        "latest_improvements": { ... },
        "historical_improvements": [ ... ],
    }
    """
    if not db:
        raise HTTPException(status_code=500, detail="Database session not available")

    try:
        # Fetch player
        stmt = select(Player).where(Player.id == player_id)
        result = await db.execute(stmt)
        player = result.scalars().first()

        if not player:
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found")

        # Fetch batting scorecards
        cutoff_date = datetime.now() - timedelta(days=30 * months)
        stmt = (
            select(BattingScorecard)
            .where(
                and_(
                    BattingScorecard.player_id == player_id,
                    BattingScorecard.created_at >= cutoff_date,
                )
            )
            .order_by(BattingScorecard.created_at.desc())
        )
        result = await db.execute(stmt)
        scorecards = result.scalars().all()

        # Group by month
        monthly_data: dict[str, list] = {}
        for scorecard in scorecards:
            month = scorecard.created_at.strftime("%Y-%m")
            if month not in monthly_data:
                monthly_data[month] = []
            monthly_data[month].append(
                {
                    "runs_scored": scorecard.runs,
                    "deliveries_faced": scorecard.balls_faced,
                    "is_dismissed": scorecard.is_out,
                    "boundaries_4": scorecard.fours or 0,
                    "boundaries_6": scorecard.sixes or 0,
                    "role": scorecard.role or "unknown",
                }
            )

        # Calculate monthly stats
        monthly_stats = []
        for month in sorted(monthly_data.keys(), reverse=True):
            stats = PlayerImprovementTracker.calculate_monthly_stats(
                monthly_data[month],
                month=month,
            )
            if stats:
                monthly_stats.append(stats)

        monthly_stats.reverse()  # Oldest first

        # Get summary
        summary = PlayerImprovementTracker.get_improvement_summary(monthly_stats)

        # Format response
        return {
            "player_id": player_id,
            "player_name": player.name if player else "Unknown",
            "status": summary.get("status", "success"),
            "overall_trend": summary.get("overall_trend", "stable"),
            "improvement_score": summary.get("improvement_score", 0),
            "latest_month": summary.get("latest_month", ""),
            "months_analyzed": summary.get("months_analyzed", 0),
            "latest_stats": summary.get("latest_stats", {}),
            "highlights": summary.get("highlights", []),
            "latest_improvements": {
                k: {
                    "metric_name": v.metric_name,
                    "previous_value": v.previous_value,
                    "current_value": v.current_value,
                    "absolute_change": v.absolute_change,
                    "percentage_change": v.percentage_change,
                    "trend": v.trend,
                    "confidence": round(v.confidence, 2),
                }
                for k, v in summary.get("latest_improvements", {}).items()
            },
            "historical_improvements": summary.get("historical_improvements", []),
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Improvement summary error: {e!s}")
