"""
Player profile routes for Cricksy Scorer.
Handles player statistics, achievements, and leaderboards.
"""

import datetime as dt
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.sql_app.database import get_db
from backend.sql_app.models import AchievementType, PlayerAchievement, PlayerProfile
from backend.sql_app.schemas import (
    AwardAchievementRequest,
    LeaderboardEntry,
    LeaderboardResponse,
    PlayerAchievementResponse,
    PlayerProfileResponse,
)

UTC = getattr(dt, "UTC", dt.UTC)

router = APIRouter(prefix="/api/players", tags=["players"])


@router.get("/{player_id}/profile", response_model=PlayerProfileResponse)
async def get_player_profile(
    player_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get comprehensive player profile including statistics and achievements.
    """
    result = await db.execute(
        select(PlayerProfile)
        .where(PlayerProfile.player_id == player_id)
        .options(selectinload(PlayerProfile.achievements))
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="Player profile not found")

    return PlayerProfileResponse(
        player_id=profile.player_id,
        player_name=profile.player_name,
        total_matches=profile.total_matches,
        total_innings_batted=profile.total_innings_batted,
        total_runs_scored=profile.total_runs_scored,
        total_balls_faced=profile.total_balls_faced,
        total_fours=profile.total_fours,
        total_sixes=profile.total_sixes,
        times_out=profile.times_out,
        highest_score=profile.highest_score,
        centuries=profile.centuries,
        half_centuries=profile.half_centuries,
        batting_average=profile.batting_average,
        strike_rate=profile.strike_rate,
        total_innings_bowled=profile.total_innings_bowled,
        total_overs_bowled=profile.total_overs_bowled,
        total_runs_conceded=profile.total_runs_conceded,
        total_wickets=profile.total_wickets,
        best_bowling_figures=profile.best_bowling_figures,
        five_wicket_hauls=profile.five_wicket_hauls,
        maidens=profile.maidens,
        bowling_average=profile.bowling_average,
        economy_rate=profile.economy_rate,
        catches=profile.catches,
        stumpings=profile.stumpings,
        run_outs=profile.run_outs,
        created_at=profile.created_at,
        updated_at=profile.updated_at,
        achievements=[
            PlayerAchievementResponse(
                id=ach.id,
                player_id=ach.player_id,
                game_id=ach.game_id,
                achievement_type=ach.achievement_type.value,
                title=ach.title,
                description=ach.description,
                badge_icon=ach.badge_icon,
                earned_at=ach.earned_at,
                metadata=ach.achievement_metadata,
            )
            for ach in profile.achievements
        ],
    )


@router.get("/{player_id}/achievements", response_model=list[PlayerAchievementResponse])
async def get_player_achievements(
    player_id: str,
    db: AsyncSession = Depends(get_db),
):
    """
    Get all achievements for a specific player.
    """
    result = await db.execute(
        select(PlayerAchievement)
        .where(PlayerAchievement.player_id == player_id)
        .order_by(desc(PlayerAchievement.earned_at))
    )
    achievements = result.scalars().all()

    return [
        PlayerAchievementResponse(
            id=ach.id,
            player_id=ach.player_id,
            game_id=ach.game_id,
            achievement_type=ach.achievement_type.value,
            title=ach.title,
            description=ach.description,
            badge_icon=ach.badge_icon,
            earned_at=ach.earned_at,
            metadata=ach.achievement_metadata,
        )
        for ach in achievements
    ]


@router.post("/{player_id}/achievements", response_model=PlayerAchievementResponse)
async def award_achievement(
    player_id: str,
    payload: AwardAchievementRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Award an achievement to a player.
    """
    # Verify player profile exists
    result = await db.execute(
        select(PlayerProfile).where(PlayerProfile.player_id == player_id)
    )
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="Player profile not found")

    # Validate achievement type
    try:
        achievement_type = AchievementType(payload.achievement_type)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid achievement type")

    # Create new achievement
    new_achievement = PlayerAchievement(
        player_id=player_id,
        game_id=payload.game_id,
        achievement_type=achievement_type,
        title=payload.title,
        description=payload.description,
        badge_icon=payload.badge_icon,
        achievement_metadata=payload.metadata,
    )

    db.add(new_achievement)
    await db.commit()
    await db.refresh(new_achievement)

    return PlayerAchievementResponse(
        id=new_achievement.id,
        player_id=new_achievement.player_id,
        game_id=new_achievement.game_id,
        achievement_type=new_achievement.achievement_type.value,
        title=new_achievement.title,
        description=new_achievement.description,
        badge_icon=new_achievement.badge_icon,
        earned_at=new_achievement.earned_at,
        metadata=new_achievement.achievement_metadata,
    )


@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    metric: Literal[
        "batting_average",
        "strike_rate",
        "total_runs",
        "centuries",
        "bowling_average",
        "economy_rate",
        "total_wickets",
        "five_wickets",
    ] = "total_runs",
    limit: int = 10,
    db: AsyncSession = Depends(get_db),
):
    """
    Get leaderboard for a specific metric.

    Available metrics:
    - batting_average: Best batting averages
    - strike_rate: Highest strike rates
    - total_runs: Most runs scored
    - centuries: Most centuries
    - bowling_average: Best bowling averages
    - economy_rate: Best economy rates
    - total_wickets: Most wickets taken
    - five_wickets: Most 5-wicket hauls
    """
    # Build query based on metric
    query = select(PlayerProfile)

    if metric == "batting_average":
        # Filter players with at least 1 innings and order by average
        query = query.where(PlayerProfile.times_out > 0).order_by(
            desc(PlayerProfile.total_runs_scored / PlayerProfile.times_out)
        )
    elif metric == "strike_rate":
        query = query.where(PlayerProfile.total_balls_faced > 0).order_by(
            desc((PlayerProfile.total_runs_scored / PlayerProfile.total_balls_faced) * 100)
        )
    elif metric == "total_runs":
        query = query.order_by(desc(PlayerProfile.total_runs_scored))
    elif metric == "centuries":
        query = query.order_by(desc(PlayerProfile.centuries))
    elif metric == "bowling_average":
        query = query.where(PlayerProfile.total_wickets > 0).order_by(
            desc(PlayerProfile.total_runs_conceded / PlayerProfile.total_wickets)
        )
    elif metric == "economy_rate":
        query = query.where(PlayerProfile.total_overs_bowled > 0).order_by(
            desc(PlayerProfile.total_runs_conceded / PlayerProfile.total_overs_bowled)
        )
    elif metric == "total_wickets":
        query = query.order_by(desc(PlayerProfile.total_wickets))
    elif metric == "five_wickets":
        query = query.order_by(desc(PlayerProfile.five_wicket_hauls))

    query = query.limit(limit)

    result = await db.execute(query)
    profiles = result.scalars().all()

    # Build leaderboard entries
    entries = []
    for rank, profile in enumerate(profiles, start=1):
        if metric == "batting_average":
            value = profile.batting_average
            additional_stats = {
                "total_runs": profile.total_runs_scored,
                "times_out": profile.times_out,
            }
        elif metric == "strike_rate":
            value = profile.strike_rate
            additional_stats = {
                "total_runs": profile.total_runs_scored,
                "balls_faced": profile.total_balls_faced,
            }
        elif metric == "total_runs":
            value = profile.total_runs_scored
            additional_stats = {
                "batting_average": profile.batting_average,
                "strike_rate": profile.strike_rate,
            }
        elif metric == "centuries":
            value = profile.centuries
            additional_stats = {
                "half_centuries": profile.half_centuries,
                "highest_score": profile.highest_score,
            }
        elif metric == "bowling_average":
            value = profile.bowling_average
            additional_stats = {
                "total_wickets": profile.total_wickets,
                "runs_conceded": profile.total_runs_conceded,
            }
        elif metric == "economy_rate":
            value = profile.economy_rate
            additional_stats = {
                "total_wickets": profile.total_wickets,
                "overs_bowled": profile.total_overs_bowled,
            }
        elif metric == "total_wickets":
            value = profile.total_wickets
            additional_stats = {
                "bowling_average": profile.bowling_average,
                "economy_rate": profile.economy_rate,
            }
        elif metric == "five_wickets":
            value = profile.five_wicket_hauls
            additional_stats = {
                "total_wickets": profile.total_wickets,
                "best_figures": profile.best_bowling_figures or "N/A",
            }
        else:
            value = 0
            additional_stats = {}

        entries.append(
            LeaderboardEntry(
                rank=rank,
                player_id=profile.player_id,
                player_name=profile.player_name,
                value=value,
                additional_stats=additional_stats,
            )
        )

    return LeaderboardResponse(
        metric=metric,
        entries=entries,
        updated_at=dt.datetime.now(UTC),
    )
