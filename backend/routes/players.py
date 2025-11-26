"""
Player profile routes for Cricksy Scorer.
Handles player statistics, achievements, and leaderboards.
"""

import datetime as dt
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import Float, cast, desc, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend import security
from backend.sql_app.database import get_db
from backend.sql_app.models import (
    AchievementType,
    PlayerAchievement,
    PlayerCoachingNoteVisibility,
    PlayerCoachingNotes,
    PlayerForm,
    PlayerProfile,
    PlayerSummary,
    RoleEnum,
    User,
)
from backend.sql_app.schemas import (
    AwardAchievementRequest,
    LeaderboardEntry,
    LeaderboardResponse,
    PlayerAchievementResponse,
    PlayerCoachingNotesCreate,
    PlayerCoachingNotesRead,
    PlayerFormCreate,
    PlayerFormRead,
    PlayerProfileResponse,
    PlayerSummaryRead,
)

UTC = getattr(dt, "UTC", dt.UTC)

router = APIRouter(prefix="/api/players", tags=["players"])


async def _ensure_player_profile(db: AsyncSession, player_id: str) -> PlayerProfile:
    profile = await db.get(PlayerProfile, player_id)
    if profile is None:
        raise HTTPException(status_code=404, detail="Player profile not found")
    return profile


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


@router.get(
    "/{player_id}/form",
    response_model=list[PlayerFormRead],
)
async def list_player_form_entries(
    player_id: str,
    _current_user: Annotated[
        User, Depends(security.require_roles(["coach_pro", "analyst_pro", "org_pro"]))
    ],
    db: AsyncSession = Depends(get_db),
) -> list[PlayerForm]:
    await _ensure_player_profile(db, player_id)
    result = await db.execute(
        select(PlayerForm)
        .where(PlayerForm.player_id == player_id)
        .order_by(desc(PlayerForm.period_end))
    )
    return result.scalars().all()


@router.post(
    "/{player_id}/form",
    response_model=PlayerFormRead,
)
async def create_player_form_entry(
    player_id: str,
    form_data: PlayerFormCreate,
    _current_user: Annotated[User, Depends(security.require_roles(["coach_pro", "org_pro"]))],
    db: AsyncSession = Depends(get_db),
) -> PlayerForm:
    await _ensure_player_profile(db, player_id)
    form_entry = PlayerForm(player_id=player_id, **form_data.model_dump(mode="python"))
    db.add(form_entry)
    await db.commit()
    await db.refresh(form_entry)
    return form_entry


@router.get(
    "/{player_id}/notes",
    response_model=list[PlayerCoachingNotesRead],
)
async def list_player_coaching_notes(
    player_id: str,
    current_user: Annotated[
        User, Depends(security.require_roles(["coach_pro", "analyst_pro", "org_pro"]))
    ],
    db: AsyncSession = Depends(get_db),
) -> list[PlayerCoachingNotes]:
    await _ensure_player_profile(db, player_id)
    stmt = (
        select(PlayerCoachingNotes)
        .where(PlayerCoachingNotes.player_id == player_id)
        .order_by(desc(PlayerCoachingNotes.created_at))
    )
    if current_user.role == RoleEnum.analyst_pro:
        stmt = stmt.where(PlayerCoachingNotes.visibility == PlayerCoachingNoteVisibility.org_only)
    result = await db.execute(stmt)
    return result.scalars().all()


@router.post(
    "/{player_id}/notes",
    response_model=PlayerCoachingNotesRead,
)
async def create_player_coaching_note(
    player_id: str,
    note_data: PlayerCoachingNotesCreate,
    current_user: Annotated[User, Depends(security.require_roles(["coach_pro", "org_pro"]))],
    db: AsyncSession = Depends(get_db),
) -> PlayerCoachingNotes:
    await _ensure_player_profile(db, player_id)
    note = PlayerCoachingNotes(
        player_id=player_id,
        coach_user_id=current_user.id,
        **note_data.model_dump(mode="python"),
    )
    db.add(note)
    await db.commit()
    await db.refresh(note)
    return note


@router.put(
    "/{player_id}/notes/{note_id}",
    response_model=PlayerCoachingNotesRead,
)
async def update_player_coaching_note(
    player_id: str,
    note_id: str,
    note_data: PlayerCoachingNotesCreate,
    _current_user: Annotated[User, Depends(security.require_roles(["coach_pro", "org_pro"]))],
    db: AsyncSession = Depends(get_db),
) -> PlayerCoachingNotes:
    await _ensure_player_profile(db, player_id)
    note = await db.get(PlayerCoachingNotes, note_id)
    if note is None or note.player_id != player_id:
        raise HTTPException(status_code=404, detail="Coaching note not found")
    for field, value in note_data.model_dump(mode="python").items():
        setattr(note, field, value)
    await db.commit()
    await db.refresh(note)
    return note


@router.get(
    "/{player_id}/summary",
    response_model=PlayerSummaryRead,
)
async def get_player_summary(
    player_id: str,
    _current_user: Annotated[
        User,
        Depends(security.require_roles(["player_pro", "coach_pro", "analyst_pro", "org_pro"])),
    ],
    db: AsyncSession = Depends(get_db),
) -> PlayerSummary:
    result = await db.execute(select(PlayerSummary).where(PlayerSummary.player_id == player_id))
    summary = result.scalar_one_or_none()
    if summary is None:
        raise HTTPException(status_code=404, detail="Player summary not found")
    return summary


@router.post(
    "/{player_id}/achievements",
    response_model=PlayerAchievementResponse,
    dependencies=[security.coach_or_org_required],
)
async def award_achievement(
    player_id: str,
    payload: AwardAchievementRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Award an achievement to a player.
    """
    # Verify player profile exists
    result = await db.execute(select(PlayerProfile).where(PlayerProfile.player_id == player_id))
    profile = result.scalar_one_or_none()

    if not profile:
        raise HTTPException(status_code=404, detail="Player profile not found")

    # Validate achievement type
    try:
        achievement_type = AchievementType(payload.achievement_type)
    except ValueError as err:
        raise HTTPException(status_code=400, detail="Invalid achievement type") from err

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


@router.get(
    "/leaderboard",
    response_model=LeaderboardResponse,
    dependencies=[security.analyst_or_org_required],
)
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
        # Cast to Float to preserve decimal precision in sorting
        query = query.where(PlayerProfile.times_out > 0).order_by(
            desc(cast(PlayerProfile.total_runs_scored, Float) / PlayerProfile.times_out)
        )
    elif metric == "strike_rate":
        # Cast to Float to preserve decimal precision in sorting
        query = query.where(PlayerProfile.total_balls_faced > 0).order_by(
            desc(
                (cast(PlayerProfile.total_runs_scored, Float) / PlayerProfile.total_balls_faced)
                * 100
            )
        )
    elif metric == "total_runs":
        query = query.order_by(desc(PlayerProfile.total_runs_scored))
    elif metric == "centuries":
        query = query.order_by(desc(PlayerProfile.centuries))
    elif metric == "bowling_average":
        # Cast to Float to preserve decimal precision in sorting
        query = query.where(PlayerProfile.total_wickets > 0).order_by(
            cast(PlayerProfile.total_runs_conceded, Float) / PlayerProfile.total_wickets
        )
    elif metric == "economy_rate":
        # Cast to Float to preserve decimal precision in sorting
        query = query.where(PlayerProfile.total_overs_bowled > 0).order_by(
            cast(PlayerProfile.total_runs_conceded, Float) / PlayerProfile.total_overs_bowled
        )
    elif metric == "total_wickets":
        query = query.order_by(desc(PlayerProfile.total_wickets))
    elif metric == "five_wickets":
        query = query.order_by(desc(PlayerProfile.five_wicket_hauls))

    query = query.limit(limit)

    result = await db.execute(query)
    profiles = result.scalars().all()

    # Build leaderboard entries
    entries: list[LeaderboardEntry] = []
    for rank, profile in enumerate(profiles, start=1):
        if metric == "batting_average":
            value = profile.batting_average
            additional_stats: dict[str, object] = {
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
