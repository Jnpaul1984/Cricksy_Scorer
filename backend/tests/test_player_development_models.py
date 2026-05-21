from __future__ import annotations

import datetime as dt
import importlib.util
import os
from pathlib import Path

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")

from backend.domain.ai_boundary import OFFICIAL_TRUTH_FIELDS
from backend.services.player_development_state import (
    normalize_player_development_plan_governance,
    validate_player_development_plan_governance,
)
from backend.sql_app import models, schemas


def _make_player_profile() -> models.PlayerProfile:
    return models.PlayerProfile(
        player_id="player-dev-001",
        player_name="Player Dev",
        total_matches=12,
        total_runs_scored=480,
        total_wickets=17,
        total_balls_faced=360,
        total_innings_batted=12,
        total_innings_bowled=10,
        total_runs_conceded=220,
        total_overs_bowled=36.0,
    )


def _make_coach() -> models.User:
    return models.User(
        id="coach-dev-001",
        email="coach-dev@example.com",
        hashed_password="hashed",
        role=models.RoleEnum.coach_pro,
        org_id="org-dev-001",
        is_active=True,
    )


@pytest.mark.asyncio
async def test_player_development_model_relationships_and_ai_defaults(db_session) -> None:
    coach = _make_coach()
    player_profile = _make_player_profile()
    db_session.add_all([coach, player_profile])
    await db_session.commit()

    original_runs = player_profile.total_runs_scored
    original_wickets = player_profile.total_wickets

    plan = models.PlayerDevelopmentPlan(
        player_profile_id=player_profile.player_id,
        coach_user_id=coach.id,
        org_id=coach.org_id or "org-dev-001",
        title="Improve back-foot batting options",
        summary="Evidence-grounded batting development plan.",
        source_type=models.PlayerDevelopmentSourceType.ai_insight,
        evidence_refs=[
            {"type": "match_data", "match_id": "match-001", "metric": "back_foot_scoring"}
        ],
        ai_metadata={"requires_review": True, "grounding_summary": "Based on recent dismissals."},
    )
    plan.goals.append(
        models.PlayerDevelopmentGoal(
            title="Increase back-foot boundary options",
            target_metric="back_foot_boundary_rate",
            baseline_value=0.12,
            target_value=0.2,
            current_value=0.12,
            unit="rate",
            due_date=dt.date(2026, 6, 1),
            evidence_refs=[{"type": "player_form", "player_id": player_profile.player_id}],
        )
    )
    plan.weakness_tags.append(
        models.PlayerWeaknessTag(
            player_profile_id=player_profile.player_id,
            category="batting_footwork",
            label="Late back-foot trigger against short-of-length bowling",
            safe_display_label="Back-foot setup development area",
            severity=models.PlayerDevelopmentSeverity.medium,
            confidence_score=0.74,
            source_type=models.PlayerDevelopmentSourceType.video_analysis,
            evidence_refs=[{"type": "video_report", "report_id": "report-123"}],
            ai_metadata={"limitations": ["single session sample"]},
        )
    )
    plan.strength_tags.append(
        models.PlayerStrengthTag(
            player_profile_id=player_profile.player_id,
            category="front_foot_drives",
            label="Front-foot timing remains a reliable strength",
            confidence_score=0.8,
            source_type=models.PlayerDevelopmentSourceType.match_data,
            evidence_refs=[{"type": "match_data", "match_id": "match-002"}],
            ai_metadata={"source_refs": ["match-002"]},
        )
    )
    plan.interventions.append(
        models.PlayerDevelopmentIntervention(
            coach_user_id=coach.id,
            source_type=models.PlayerDevelopmentSourceType.coach_note,
            intervention_type="technical_session",
            title="Focused batting session",
            notes="Work on initial movement pattern.",
            evidence_refs=[{"type": "coach_note", "note_id": "note-001"}],
        )
    )
    plan.drill_assignments.append(
        models.PlayerDrillAssignment(
            player_profile_id=player_profile.player_id,
            coach_user_id=coach.id,
            drill_category="batting",
            drill_name="Back-foot defense ladder",
            drill_description="Short-length ball machine progression.",
            frequency="3 sessions per week",
            due_date=dt.date(2026, 5, 30),
            evidence_refs=[{"type": "manual", "note": "assigned by coach"}],
        )
    )
    plan.progress_checkpoints.append(
        models.PlayerProgressCheckpoint(
            player_profile_id=player_profile.player_id,
            coach_user_id=coach.id,
            checkpoint_date=dt.date(2026, 5, 25),
            summary="Early signs of improved balance on the back foot.",
            progress_status="on_track",
            confidence_score=0.68,
            evidence_refs=[{"type": "monthly_improvement", "player_id": player_profile.player_id}],
            ai_metadata={"is_official_truth": False},
            coach_notes="Needs more evidence before claiming sustained improvement.",
        )
    )

    db_session.add(plan)
    await db_session.commit()
    await db_session.refresh(player_profile)

    assert plan.status == models.PlayerDevelopmentPlanStatus.draft
    assert plan.coach_approved is False
    assert plan.approval_state == models.PlayerDevelopmentApprovalState.pending_review
    assert len(plan.goals) == 1
    assert len(plan.weakness_tags) == 1
    assert len(plan.strength_tags) == 1
    assert len(plan.interventions) == 1
    assert len(plan.drill_assignments) == 1
    assert len(plan.progress_checkpoints) == 1
    assert plan.weakness_tags[0].safe_display_label != plan.weakness_tags[0].category
    assert player_profile.total_runs_scored == original_runs
    assert player_profile.total_wickets == original_wickets


def test_player_development_schemas_accept_evidence_refs_and_safe_labels() -> None:
    plan = schemas.PlayerDevelopmentPlanCreate(
        player_profile_id="player-dev-001",
        coach_user_id="coach-dev-001",
        org_id="org-dev-001",
        title="Build repeatable batting process",
        summary="Coach-reviewed development plan draft.",
        source_type=models.PlayerDevelopmentSourceType.ai_insight,
        evidence_refs=[
            {"type": "match_data", "match_id": "match-001"},
            {"type": "video_report", "report_id": "video-101"},
        ],
        ai_metadata={"limitations": ["sample size is still small"]},
    )
    weakness = schemas.PlayerWeaknessTagCreate(
        plan_id="plan-001",
        player_profile_id="player-dev-001",
        category="shot_selection",
        label="Over-commits early to the leg side",
        safe_display_label="Shot selection development area",
        severity=models.PlayerDevelopmentSeverity.high,
        confidence_score=0.7,
        source_type=models.PlayerDevelopmentSourceType.video_analysis,
        evidence_refs=[{"type": "video_session", "session_id": "session-1"}],
        ai_metadata={"grounding_summary": "Observed across two review clips."},
    )

    assert plan.status == models.PlayerDevelopmentPlanStatus.draft
    assert plan.coach_approved is False
    assert plan.approval_state == models.PlayerDevelopmentApprovalState.pending_review
    assert isinstance(plan.evidence_refs, list)
    assert weakness.safe_display_label != weakness.category
    assert weakness.safe_display_label == "Shot selection development area"


def test_active_player_development_plan_requires_coach_approval() -> None:
    with pytest.raises(ValueError, match="require coach approval"):
        validate_player_development_plan_governance(
            models.PlayerDevelopmentPlanStatus.active,
            False,
            models.PlayerDevelopmentApprovalState.approved,
        )

    status, coach_approved, approval_state = normalize_player_development_plan_governance(
        models.PlayerDevelopmentSourceType.manual,
        models.PlayerDevelopmentPlanStatus.active,
        True,
        models.PlayerDevelopmentApprovalState.not_required,
    )

    assert status == models.PlayerDevelopmentPlanStatus.active.value
    assert coach_approved is True
    assert approval_state == models.PlayerDevelopmentApprovalState.not_required.value


def test_progress_checkpoint_schema_does_not_overlap_official_truth_fields() -> None:
    checkpoint = schemas.PlayerProgressCheckpointCreate(
        plan_id="plan-001",
        player_profile_id="player-dev-001",
        coach_user_id="coach-dev-001",
        checkpoint_date=dt.date(2026, 5, 25),
        summary="Observed improvement remains advisory until more evidence is recorded.",
        progress_status="needs_more_evidence",
        confidence_score=0.51,
        evidence_refs=[{"type": "coach_note", "note_id": "note-77"}],
        ai_metadata={"is_official_truth": False, "requires_review": True},
        coach_notes="Do not treat this checkpoint as official career stats.",
    )

    overlap = OFFICIAL_TRUTH_FIELDS & set(checkpoint.model_dump().keys())
    assert not overlap


def test_player_development_migration_and_metadata_sanity() -> None:
    expected_tables = {
        "player_development_plans",
        "player_development_goals",
        "player_weakness_tags",
        "player_strength_tags",
        "player_development_interventions",
        "player_drill_assignments",
        "player_progress_checkpoints",
    }
    assert expected_tables.issubset(models.Base.metadata.tables.keys())

    migration_path = (
        Path(__file__).resolve().parents[1]
        / "alembic"
        / "versions"
        / "d9b1c2e3f4a5_add_player_development_tables.py"
    )
    spec = importlib.util.spec_from_file_location(
        "phase9b_player_development_migration", migration_path
    )
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert module.revision == "d9b1c2e3f4a5"
    assert module.down_revision == "c9d8e7f6a5b4"
    assert callable(module.upgrade)
    assert callable(module.downgrade)
