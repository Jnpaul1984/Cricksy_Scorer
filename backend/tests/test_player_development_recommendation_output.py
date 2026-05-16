"""Phase 9H.4 — Player Development Recommendation Output tests.

Validates player-facing visibility enforcement:
- Approved plans (coach_approved=True, approval_state=approved) appear in
  player-facing output.
- Pending / rejected / changes_requested plans are hidden from player-facing
  output.
- Coach/internal output can still see non-approved plans.
- Raw ai_metadata and raw evidence marker JSON are not exposed player-facing.
- Safe recommendation content is preserved for approved player-facing output.
- Output filtering does not mutate plans, evidence_refs, video IDs, or
  official cricket truth fields.
"""
from __future__ import annotations

import copy
import datetime as dt

import pytest
from sqlalchemy import select

from backend.security import create_access_token
from backend.sql_app import models


def _token_headers(user: models.User) -> dict[str, str]:
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Seed helpers
# ---------------------------------------------------------------------------

async def _seed_output_data(
    db_session,
) -> tuple[models.User, models.User, models.PlayerProfile, dict[str, models.PlayerDevelopmentPlan]]:
    """Seed a coach, an org user, a player profile, and four plans with distinct
    approval states (approved, pending_review, rejected, changes_requested).
    """
    coach = models.User(
        id="coach-output-001",
        email="coach-output@example.com",
        hashed_password="hashed",  # noqa: S106
        role=models.RoleEnum.coach_pro_plus,
        org_id="org-output-001",
        is_active=True,
    )
    org_user = models.User(
        id="org-output-001",
        email="org-output@example.com",
        hashed_password="hashed",  # noqa: S106
        role=models.RoleEnum.org_pro,
        org_id="org-output-001",
        is_active=True,
    )
    player = models.PlayerProfile(
        player_id="player-output-001",
        player_name="Output Test Player",
        total_matches=15,
        total_runs_scored=450,
        total_balls_faced=380,
        total_innings_batted=15,
        total_innings_bowled=3,
        total_wickets=4,
        total_runs_conceded=90,
        total_overs_bowled=12.0,
        total_fours=38,
        total_sixes=10,
        times_out=12,
    )
    assignment = models.CoachPlayerAssignment(
        id="assignment-output-001",
        coach_user_id=coach.id,
        player_profile_id=player.player_id,
        is_active=True,
    )

    _EVIDENCE = [
        {"type": "form", "id": "form-output-001", "label": "Recent form evidence"},
        {
            "type": "video_session",
            "id": "video-session-output-001",
            "label": "Video session marker",
            "raw_marker_payload": {"pose_keypoints": [0.1, 0.2]},
        },
    ]
    _AI_META = {
        "is_official_truth": False,
        "requires_review": True,
        "video_session_id": "video-session-output-001",
        "video_analysis_job_id": "video-job-output-001",
        "limitations": ["More match evidence needed.", "Sample size is limited."],
        "internal_reviewer_notes": "Check posture in delivery stride.",
    }

    # Approved plan — player-facing safe
    approved_plan = models.PlayerDevelopmentPlan(
        id="plan-output-approved",
        player_profile_id=player.player_id,
        coach_user_id=coach.id,
        org_id="org-output-001",
        title="Approved Development Plan",
        summary="Ready for player view.",
        source_type=models.PlayerDevelopmentSourceType.ai_insight,
        coach_approved=True,
        approval_state=models.PlayerDevelopmentApprovalState.approved,
        confidence_score=0.75,
        evidence_refs=list(_EVIDENCE),
        ai_metadata=dict(_AI_META),
    )
    approved_plan.strength_tags.append(
        models.PlayerStrengthTag(
            id="strength-output-001",
            plan_id=approved_plan.id,
            player_profile_id=player.player_id,
            category="batting",
            label="Strong on-drive technique",
            confidence_score=0.78,
            source_type=models.PlayerDevelopmentSourceType.ai_insight,
            evidence_refs=list(_EVIDENCE),
            ai_metadata=dict(_AI_META),
            created_at=dt.datetime(2026, 5, 10, 9, 0),
            updated_at=dt.datetime(2026, 5, 10, 9, 0),
        )
    )
    approved_plan.progress_checkpoints.append(
        models.PlayerProgressCheckpoint(
            id="checkpoint-output-001",
            plan_id=approved_plan.id,
            player_profile_id=player.player_id,
            coach_user_id=coach.id,
            checkpoint_date=dt.date.today(),
            summary="First review checkpoint.",
            progress_status="scheduled",
            confidence_score=0.75,
            evidence_refs=list(_EVIDENCE),
            ai_metadata=dict(_AI_META),
            coach_notes="Internal note: watch front-foot movement.",
        )
    )

    # Pending-review plan — must NOT appear player-facing
    pending_plan = models.PlayerDevelopmentPlan(
        id="plan-output-pending",
        player_profile_id=player.player_id,
        coach_user_id=coach.id,
        org_id="org-output-001",
        title="Pending Review Plan",
        source_type=models.PlayerDevelopmentSourceType.ai_insight,
        coach_approved=False,
        approval_state=models.PlayerDevelopmentApprovalState.pending_review,
        confidence_score=0.55,
        evidence_refs=list(_EVIDENCE),
        ai_metadata=dict(_AI_META),
    )

    # Rejected plan — must NOT appear player-facing
    rejected_plan = models.PlayerDevelopmentPlan(
        id="plan-output-rejected",
        player_profile_id=player.player_id,
        coach_user_id=coach.id,
        org_id="org-output-001",
        title="Rejected Plan",
        source_type=models.PlayerDevelopmentSourceType.ai_insight,
        coach_approved=False,
        approval_state=models.PlayerDevelopmentApprovalState.rejected,
        confidence_score=0.40,
        evidence_refs=list(_EVIDENCE),
        ai_metadata=dict(_AI_META),
    )

    # Changes-requested plan — must NOT appear player-facing
    changes_plan = models.PlayerDevelopmentPlan(
        id="plan-output-changes",
        player_profile_id=player.player_id,
        coach_user_id=coach.id,
        org_id="org-output-001",
        title="Changes Requested Plan",
        source_type=models.PlayerDevelopmentSourceType.ai_insight,
        coach_approved=False,
        approval_state=models.PlayerDevelopmentApprovalState.changes_requested,
        confidence_score=0.60,
        evidence_refs=list(_EVIDENCE),
        ai_metadata=dict(_AI_META),
    )

    db_session.add_all(
        [
            coach,
            org_user,
            player,
            assignment,
            approved_plan,
            pending_plan,
            rejected_plan,
            changes_plan,
        ]
    )
    await db_session.commit()

    plans = {
        "approved": approved_plan,
        "pending": pending_plan,
        "rejected": rejected_plan,
        "changes_requested": changes_plan,
    }
    return coach, org_user, player, plans


# ---------------------------------------------------------------------------
# Tests — Player-facing approval gate
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_approved_plan_appears_in_player_facing_output(async_client, db_session) -> None:
    """Requirement 1: An approved plan appears in player-facing report output."""
    coach, _org, player, plans = await _seed_output_data(db_session)

    response = await async_client.get(
        f"/api/player-development/reports/plans/{plans['approved'].id}",
        headers=_token_headers(coach),
        params={"audience": "player"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["plan_id"] == plans["approved"].id
    assert payload["coach_approved"] is True
    assert payload["approval_state"] == "approved"


@pytest.mark.asyncio
async def test_pending_plan_is_hidden_from_player_facing_output(async_client, db_session) -> None:
    """Requirement 2: A pending-review plan does not appear in player-facing output."""
    coach, _org, player, plans = await _seed_output_data(db_session)

    response = await async_client.get(
        f"/api/player-development/reports/plans/{plans['pending'].id}",
        headers=_token_headers(coach),
        params={"audience": "player"},
    )

    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_rejected_plan_is_hidden_from_player_facing_output(async_client, db_session) -> None:
    """Requirement 3: A rejected plan does not appear in player-facing output."""
    coach, _org, player, plans = await _seed_output_data(db_session)

    response = await async_client.get(
        f"/api/player-development/reports/plans/{plans['rejected'].id}",
        headers=_token_headers(coach),
        params={"audience": "player"},
    )

    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_changes_requested_plan_is_hidden_from_player_facing_output(
    async_client, db_session
) -> None:
    """Requirement 4: A changes-requested plan does not appear in player-facing output."""
    coach, _org, player, plans = await _seed_output_data(db_session)

    response = await async_client.get(
        f"/api/player-development/reports/plans/{plans['changes_requested'].id}",
        headers=_token_headers(coach),
        params={"audience": "player"},
    )

    assert response.status_code == 404, response.text


@pytest.mark.asyncio
async def test_coach_output_can_see_non_approved_plans(async_client, db_session) -> None:
    """Requirement 5: Coach/internal output can still see non-approved plans."""
    coach, _org, player, plans = await _seed_output_data(db_session)

    for state, plan in plans.items():
        response = await async_client.get(
            f"/api/player-development/reports/plans/{plan.id}",
            headers=_token_headers(coach),
            params={"audience": "coach"},
        )
        assert response.status_code == 200, f"state={state}: {response.text}"
        payload = response.json()
        assert payload["plan_id"] == plan.id


@pytest.mark.asyncio
async def test_player_facing_output_does_not_expose_raw_ai_metadata(
    async_client, db_session
) -> None:
    """Requirement 6: Player-facing output does not expose raw ai_metadata."""
    coach, _org, player, plans = await _seed_output_data(db_session)

    response = await async_client.get(
        f"/api/player-development/reports/plans/{plans['approved'].id}",
        headers=_token_headers(coach),
        params={"audience": "player"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    # The report schema must not include any ai_metadata key.
    assert "ai_metadata" not in payload
    # Also confirm raw internal fields from ai_metadata are absent.
    response_text = response.text
    assert "internal_reviewer_notes" not in response_text
    assert "pose_keypoints" not in response_text


@pytest.mark.asyncio
async def test_player_facing_output_does_not_expose_raw_evidence_marker_json(
    async_client, db_session
) -> None:
    """Requirement 7: Player-facing output does not expose raw evidence marker JSON.

    Evidence refs are stripped to ``{type, label}`` only — internal IDs and
    extra payload fields such as ``raw_marker_payload`` are removed.
    """
    coach, _org, player, plans = await _seed_output_data(db_session)

    response = await async_client.get(
        f"/api/player-development/reports/plans/{plans['approved'].id}",
        headers=_token_headers(coach),
        params={"audience": "player"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()

    # Top-level plan evidence_refs must contain only {type, label}.
    for ref in payload.get("evidence_refs", []):
        assert set(ref.keys()) == {"type", "label"}, f"Unexpected keys in ref: {ref}"
        assert ref.get("id") is None  # id is stripped

    # Strength evidence_refs must also be stripped.
    for strength in payload.get("strengths", []):
        for ref in strength.get("evidence_refs", []):
            assert set(ref.keys()) == {"type", "label"}, f"Unexpected keys in strength ref: {ref}"

    # Raw payload field from seed data must not appear anywhere.
    assert "raw_marker_payload" not in response.text
    assert "pose_keypoints" not in response.text


@pytest.mark.asyncio
async def test_player_facing_output_preserves_safe_approved_recommendation_info(
    async_client, db_session
) -> None:
    """Requirement 8: Player-facing output preserves safe approved recommendation information.

    Confidence score, limitations, advisory disclaimer, player name, plan ID,
    and strength labels must be present.
    """
    coach, _org, player, plans = await _seed_output_data(db_session)

    response = await async_client.get(
        f"/api/player-development/reports/plans/{plans['approved'].id}",
        headers=_token_headers(coach),
        params={"audience": "player"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["player_name"] == "Output Test Player"
    assert payload["plan_id"] == plans["approved"].id
    assert payload["confidence_score"] == pytest.approx(0.75)
    assert len(payload["limitations"]) > 0
    assert "Advisory development report only" in payload["advisory_disclaimer"]
    assert any("Strong on-drive technique" in s["label"] for s in payload["strengths"])


@pytest.mark.asyncio
async def test_coach_output_exposes_approval_state_and_coach_approved(
    async_client, db_session
) -> None:
    """Requirement 9: Approval state and coach_approved are visible in coach/internal output."""
    coach, _org, player, plans = await _seed_output_data(db_session)

    expected = {
        "approved": ("approved", True),
        "pending": ("pending_review", False),
        "rejected": ("rejected", False),
        "changes_requested": ("changes_requested", False),
    }

    for state_key, (expected_state, expected_approved) in expected.items():
        response = await async_client.get(
            f"/api/player-development/reports/plans/{plans[state_key].id}",
            headers=_token_headers(coach),
            params={"audience": "coach"},
        )
        assert response.status_code == 200, f"state={state_key}: {response.text}"
        payload = response.json()
        assert payload["approval_state"] == expected_state, f"state={state_key}"
        assert payload["coach_approved"] is expected_approved, f"state={state_key}"


@pytest.mark.asyncio
async def test_player_facing_output_does_not_mutate_plan_or_cricket_truth_fields(
    async_client, db_session
) -> None:
    """Requirement 10: Output filtering does not mutate plans, evidence_refs,
    video IDs, or official cricket truth fields.
    """
    coach, _org, player, plans = await _seed_output_data(db_session)
    approved_plan = plans["approved"]

    await db_session.refresh(approved_plan)
    evidence_refs_before = copy.deepcopy(approved_plan.evidence_refs)
    ai_metadata_before = copy.deepcopy(approved_plan.ai_metadata)
    status_before = approved_plan.status
    coach_approved_before = approved_plan.coach_approved
    approval_state_before = approved_plan.approval_state
    updated_at_before = approved_plan.updated_at

    await db_session.refresh(player)
    runs_before = player.total_runs_scored
    wickets_before = player.total_wickets

    response = await async_client.get(
        f"/api/player-development/reports/plans/{approved_plan.id}",
        headers=_token_headers(coach),
        params={"audience": "player"},
    )
    assert response.status_code == 200, response.text

    # Refresh and verify no mutation occurred.
    await db_session.refresh(approved_plan)
    await db_session.refresh(player)

    assert approved_plan.evidence_refs == evidence_refs_before
    assert approved_plan.ai_metadata == ai_metadata_before
    assert approved_plan.status == status_before
    assert approved_plan.coach_approved == coach_approved_before
    assert approved_plan.approval_state == approval_state_before
    assert approved_plan.updated_at.replace(tzinfo=None) == updated_at_before.replace(tzinfo=None)
    assert player.total_runs_scored == runs_before
    assert player.total_wickets == wickets_before
    # Video IDs in ai_metadata must be unchanged.
    assert approved_plan.ai_metadata.get("video_session_id") == "video-session-output-001"
    assert approved_plan.ai_metadata.get("video_analysis_job_id") == "video-job-output-001"


@pytest.mark.asyncio
async def test_player_facing_output_strips_internal_coach_notes(
    async_client, db_session
) -> None:
    """Internal coach_notes on checkpoints must be stripped for player audience."""
    coach, _org, player, plans = await _seed_output_data(db_session)

    response = await async_client.get(
        f"/api/player-development/reports/plans/{plans['approved'].id}",
        headers=_token_headers(coach),
        params={"audience": "player"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    checkpoints = payload["checkpoint_review_summary"]["checkpoints"]
    for checkpoint in checkpoints:
        assert checkpoint.get("coach_notes") is None, (
            "coach_notes must not be exposed in player-facing output"
        )
    # The raw note text must not appear anywhere in the response.
    assert "watch front-foot movement" not in response.text


@pytest.mark.asyncio
async def test_player_facing_output_has_empty_next_coach_actions(
    async_client, db_session
) -> None:
    """Internal coach workflow actions must not be surfaced to player audience."""
    coach, _org, player, plans = await _seed_output_data(db_session)

    response = await async_client.get(
        f"/api/player-development/reports/plans/{plans['approved'].id}",
        headers=_token_headers(coach),
        params={"audience": "player"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["next_coach_actions"] == []


@pytest.mark.asyncio
async def test_coach_output_exposes_full_evidence_refs_with_ids(
    async_client, db_session
) -> None:
    """Coach audience evidence_refs may retain internal IDs for coaching review."""
    coach, _org, player, plans = await _seed_output_data(db_session)

    response = await async_client.get(
        f"/api/player-development/reports/plans/{plans['approved'].id}",
        headers=_token_headers(coach),
        params={"audience": "coach"},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    # At least one evidence ref should carry an id field (as seeded).
    refs = payload.get("evidence_refs", [])
    assert any("id" in r for r in refs), "Coach output must retain evidence ref IDs"
