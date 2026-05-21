from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import select

from backend.services.player_development_plan_service import (
    generate_draft_player_development_plan,
    get_draft_plan_by_id,
)
from backend.sql_app import models

UTC = getattr(dt, "UTC", dt.UTC)


def _make_coach(
    *,
    coach_id: str = "coach-plan-001",
    email: str = "coach-plan@example.com",
    role: models.RoleEnum = models.RoleEnum.coach_pro,
    org_id: str = "org-plan-001",
) -> models.User:
    return models.User(
        id=coach_id,
        email=email,
        hashed_password="hashed",
        role=role,
        org_id=org_id,
        is_active=True,
    )


def _make_player_profile(
    *,
    player_id: str = "player-plan-001",
    player_name: str = "Plan Player",
    total_matches: int = 12,
    total_runs_scored: int = 360,
    total_balls_faced: int = 320,
    total_innings_batted: int = 12,
    total_wickets: int = 8,
    total_innings_bowled: int = 6,
) -> models.PlayerProfile:
    return models.PlayerProfile(
        player_id=player_id,
        player_name=player_name,
        total_matches=total_matches,
        total_runs_scored=total_runs_scored,
        total_balls_faced=total_balls_faced,
        total_innings_batted=total_innings_batted,
        total_innings_bowled=total_innings_bowled,
        total_wickets=total_wickets,
        total_runs_conceded=180,
        total_overs_bowled=24.0,
        total_sixes=12,
        total_fours=28,
        times_out=10,
        catches=6,
    )


def _make_form_entry(
    player_id: str,
    *,
    entry_id: str,
    period_end: dt.date,
    runs: int,
    batting_average: float,
    strike_rate: float,
    form_score: float,
) -> models.PlayerForm:
    return models.PlayerForm(
        id=entry_id,
        player_id=player_id,
        period_start=period_end - dt.timedelta(days=30),
        period_end=period_end,
        matches_played=4,
        runs=runs,
        wickets=2,
        batting_average=batting_average,
        strike_rate=strike_rate,
        economy=6.2,
        form_score=form_score,
    )


@pytest.mark.asyncio
async def test_generate_player_development_draft_plan_from_available_evidence(db_session) -> None:
    coach = _make_coach()
    profile = _make_player_profile()
    original_runs = profile.total_runs_scored
    original_wickets = profile.total_wickets

    db_session.add_all(
        [
            coach,
            profile,
            _make_form_entry(
                profile.player_id,
                entry_id="form-plan-001",
                period_end=dt.date(2026, 3, 31),
                runs=180,
                batting_average=45.0,
                strike_rate=134.0,
                form_score=78.0,
            ),
            _make_form_entry(
                profile.player_id,
                entry_id="form-plan-002",
                period_end=dt.date(2026, 4, 30),
                runs=120,
                batting_average=24.0,
                strike_rate=96.0,
                form_score=60.0,
            ),
            models.PlayerCoachingNotes(
                id="note-plan-001",
                player_id=profile.player_id,
                coach_user_id=coach.id,
                strengths="Front-foot driving remains reliable; stays composed in the field",
                weaknesses="Strike rotation slows after the powerplay; short-ball setup needs work",
                action_plan="Prioritize strike-rotation and back-foot options in the next cycle.",
                visibility=models.PlayerCoachingNoteVisibility.private_to_coach,
            ),
            models.CoachingSession(
                id="session-plan-001",
                coach_user_id=coach.id,
                player_profile_id=profile.player_id,
                scheduled_at=dt.datetime(2026, 5, 10, 10, 0, tzinfo=UTC),
                duration_minutes=75,
                focus_area="Batting options against pace",
                notes="Recorded technical session for back-foot decision making.",
                outcome="Review required after another month of tracked form.",
            ),
            models.VideoSession(
                id="video-plan-001",
                owner_type=models.OwnerTypeEnum.coach,
                owner_id=coach.id,
                title="Back-foot review session",
                player_ids=[profile.player_id],
                status=models.VideoSessionStatus.ready,
                min_duration_seconds=360,
                notes="Coach Pro Plus evidence session",
            ),
        ]
    )
    await db_session.commit()

    result = await generate_draft_player_development_plan(
        db=db_session,
        player_profile_id=profile.player_id,
        coach_user=coach,
    )
    plan = await get_draft_plan_by_id(db_session, result.plan_id or "")

    assert result.status == "draft_created"
    assert plan is not None
    assert plan.status == models.PlayerDevelopmentPlanStatus.draft
    assert plan.coach_approved is False
    assert plan.approval_state == models.PlayerDevelopmentApprovalState.pending_review
    assert plan.activated_at is None
    assert plan.confidence_score is not None
    assert plan.ai_metadata["is_official_truth"] is False
    assert plan.ai_metadata["requires_review"] is True
    assert plan.strength_tags
    assert plan.weakness_tags
    assert plan.goals
    assert plan.drill_assignments
    assert plan.progress_checkpoints
    assert any(ref["type"] == "video_session" for ref in plan.evidence_refs)
    assert any(ref["type"] == "coach_note" for ref in plan.evidence_refs)
    assert profile.total_runs_scored == original_runs
    assert profile.total_wickets == original_wickets

    safe_labels = [tag.safe_display_label.lower() for tag in plan.weakness_tags]
    assert any(
        phrase in label
        for label in safe_labels
        for phrase in (
            "development area",
            "growth focus",
            "current focus area",
            "next coaching target",
        )
    )
    assert not any(
        term in label for label in safe_labels for term in ("liability", "weak link", "hopeless")
    )

    drill_names = {drill.drill_name for drill in plan.drill_assignments}
    assert drill_names & {
        "50 Dot Ball Challenge",
        "Fast Bowling Gauntlet",
        "Pace Variation Response",
    }
    assert all(
        checkpoint.progress_status == "planned_review" for checkpoint in plan.progress_checkpoints
    )
    assert all("coach" in checkpoint.summary.lower() for checkpoint in plan.progress_checkpoints)


@pytest.mark.asyncio
async def test_generate_player_development_draft_plan_returns_insufficient_data_when_evidence_missing(
    db_session,
) -> None:
    coach = _make_coach(coach_id="coach-plan-002", email="coach-plan-2@example.com")
    profile = _make_player_profile(
        player_id="player-plan-empty",
        player_name="Empty Player",
        total_matches=0,
        total_runs_scored=0,
        total_balls_faced=0,
        total_innings_batted=0,
        total_wickets=0,
        total_innings_bowled=0,
    )
    db_session.add_all([coach, profile])
    await db_session.commit()

    result = await generate_draft_player_development_plan(
        db=db_session,
        player_profile_id=profile.player_id,
        coach_user=coach,
    )

    assert result.status == "insufficient_data"
    assert result.plan_id is None
    assert result.confidence_score == 0.0
    assert any("Insufficient" in limitation for limitation in result.limitations)

    plans = (
        (
            await db_session.execute(
                select(models.PlayerDevelopmentPlan).where(
                    models.PlayerDevelopmentPlan.player_profile_id == profile.player_id
                )
            )
        )
        .scalars()
        .all()
    )
    assert list(plans) == []
