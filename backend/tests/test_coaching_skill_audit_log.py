from __future__ import annotations

import copy
import json

import pytest
from sqlalchemy import select

from backend.sql_app import models
from backend.tests.test_player_development_approval_gate import (
    _seed_review_data,
    _token_headers,
)


async def _fetch_audit_events(
    db_session,
) -> list[models.CoachingSkillAuditLog]:
    result = await db_session.execute(
        select(models.CoachingSkillAuditLog).order_by(models.CoachingSkillAuditLog.created_at.asc())
    )
    return list(result.scalars().all())


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("decision", "event_type", "approval_state", "coach_approved"),
    [
        ("approved", "review_approved", "approved", True),
        ("rejected", "review_rejected", "rejected", False),
        ("changes_requested", "review_changes_requested", "changes_requested", False),
    ],
)
async def test_review_decisions_write_governed_audit_events(
    async_client,
    db_session,
    decision: str,
    event_type: str,
    approval_state: str,
    coach_approved: bool,
) -> None:
    seeded = await _seed_review_data(db_session)
    coach = seeded["coach_pro_plus"]
    assert isinstance(coach, models.User)
    plan = seeded["plan"]
    assert isinstance(plan, models.PlayerDevelopmentPlan)

    response = await async_client.patch(
        f"/api/player-development/plans/{plan.id}/review",
        headers=_token_headers(coach),
        json={"decision": decision, "reviewer_notes": "Internal review note that must not persist."},
    )

    assert response.status_code == 200, response.text
    events = await _fetch_audit_events(db_session)
    assert len(events) == 1
    event = events[0]
    assert event.event_type == event_type
    assert event.skill_id == "coaching_video_evidence_skill.v1"
    assert event.skill_version == "1.0.0"
    assert event.triggered_by_user_id == coach.id
    assert event.reviewed_by_user_id == coach.id
    assert event.player_profile_id == plan.player_profile_id
    assert event.plan_id == plan.id
    assert event.video_session_id == "video-session-001"
    assert event.video_analysis_job_id == "video-job-001"
    assert event.approval_decision == decision
    assert event.approval_state_after == approval_state
    assert event.coach_approved_after is coach_approved
    assert event.organization_id == plan.org_id
    assert event.input_summary["reviewer_notes_present"] is True
    assert event.output_summary["approval_state_after"] == approval_state
    assert event.output_summary["coach_approved_after"] is coach_approved


@pytest.mark.asyncio
async def test_audit_event_sanitizes_unsafe_payloads_without_mutating_plan_or_truth(
    async_client,
    db_session,
) -> None:
    seeded = await _seed_review_data(db_session)
    coach = seeded["coach_pro_plus"]
    assert isinstance(coach, models.User)
    plan = seeded["plan"]
    assert isinstance(plan, models.PlayerDevelopmentPlan)

    plan.evidence_refs = [
        *copy.deepcopy(plan.evidence_refs),
        {
            "type": "video_session",
            "id": "video-session-001",
            "label": "Unsafe marker payload",
            "raw_marker_payload": {"pose_keypoints": [0.1, 0.2]},
            "raw_frames": ["frame-a", "frame-b"],
        },
    ]
    plan.ai_metadata = {
        **copy.deepcopy(plan.ai_metadata),
        "skill_id": "coaching_video_evidence_skill.v1",
        "skill_version": "1.0.0",
        "prompt_text": "never persist this prompt",
        "token": "secret-token",
        "private_psychological_note": "never persist this note",
        "raw_frames": ["frame-a"],
        "source_refs": [
            {
                "type": "video_session",
                "id": "video-session-001",
                "label": "Video marker",
                "raw_payload": {"frame": 12},
            }
        ],
    }
    evidence_refs_before = copy.deepcopy(plan.evidence_refs)
    ai_metadata_before = copy.deepcopy(plan.ai_metadata)
    player_profile = await db_session.get(models.PlayerProfile, plan.player_profile_id)
    assert player_profile is not None
    total_runs_before = player_profile.total_runs_scored
    total_wickets_before = player_profile.total_wickets
    await db_session.commit()

    response = await async_client.patch(
        f"/api/player-development/plans/{plan.id}/review",
        headers=_token_headers(coach),
        json={"decision": "approved", "reviewer_notes": "Keep this internal."},
    )

    assert response.status_code == 200, response.text
    await db_session.refresh(plan)
    await db_session.refresh(player_profile)

    events = await _fetch_audit_events(db_session)
    assert len(events) == 1
    event = events[0]
    serialized_event = json.dumps(
        {
            "input_summary": event.input_summary,
            "output_summary": event.output_summary,
            "video_session_id": event.video_session_id,
            "video_analysis_job_id": event.video_analysis_job_id,
        }
    )
    assert event.video_session_id == "video-session-001"
    assert event.video_analysis_job_id == "video-job-001"
    assert set(event.input_summary["unsafe_fields_removed"]) == {
        "frame",
        "pose_keypoints",
        "private_psychological_note",
        "prompt_text",
        "raw_frames",
        "raw_marker_payload",
        "raw_payload",
        "token",
    }
    assert "Keep this internal." not in serialized_event
    assert "pose_keypoints" in serialized_event
    assert "frame-a" not in serialized_event
    assert "never persist this prompt" not in serialized_event
    assert "secret-token" not in serialized_event
    assert plan.evidence_refs == evidence_refs_before
    assert plan.ai_metadata == ai_metadata_before
    assert player_profile.total_runs_scored == total_runs_before
    assert player_profile.total_wickets == total_wickets_before


@pytest.mark.asyncio
async def test_audit_persistence_failure_does_not_silently_approve_plan(
    async_client,
    db_session,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seeded = await _seed_review_data(db_session)
    coach = seeded["coach_pro_plus"]
    assert isinstance(coach, models.User)
    plan = seeded["plan"]
    assert isinstance(plan, models.PlayerDevelopmentPlan)
    approval_state_before = plan.approval_state
    coach_approved_before = plan.coach_approved

    async def _boom(**_: object) -> None:
        raise RuntimeError("audit unavailable")

    monkeypatch.setattr(
        "backend.routes.player_development.write_player_development_review_audit_event",
        _boom,
    )

    response = await async_client.patch(
        f"/api/player-development/plans/{plan.id}/review",
        headers=_token_headers(coach),
        json={"decision": "approved"},
    )

    assert response.status_code == 500, response.text
    assert response.json()["detail"] == "Unable to persist governed audit record for review action"
    await db_session.refresh(plan)
    assert plan.approval_state == approval_state_before
    assert plan.coach_approved == coach_approved_before
    assert await _fetch_audit_events(db_session) == []
