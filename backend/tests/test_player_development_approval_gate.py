from __future__ import annotations

import copy

import pytest

from backend.security import create_access_token
from backend.sql_app import models


def _token_headers(user: models.User) -> dict[str, str]:
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


async def _seed_review_data(db_session) -> dict[str, models.User | models.PlayerDevelopmentPlan]:
    coach_pro_plus = models.User(
        id="coach-review-plus-001",
        email="coach-plus-review@example.com",
        hashed_password="hashed",
        role=models.RoleEnum.coach_pro_plus,
        org_id="org-review-001",
        is_active=True,
    )
    coach_pro = models.User(
        id="coach-review-pro-001",
        email="coach-pro-review@example.com",
        hashed_password="hashed",
        role=models.RoleEnum.coach_pro,
        org_id="org-review-001",
        is_active=True,
    )
    org_pro = models.User(
        id="org-review-001",
        email="org-review@example.com",
        hashed_password="hashed",
        role=models.RoleEnum.org_pro,
        org_id="org-review-001",
        is_active=True,
    )
    org_other = models.User(
        id="org-review-999",
        email="org-review-other@example.com",
        hashed_password="hashed",
        role=models.RoleEnum.org_pro,
        org_id="org-review-999",
        is_active=True,
    )
    player_pro = models.User(
        id="player-review-pro-001",
        email="player-review@example.com",
        hashed_password="hashed",
        role=models.RoleEnum.player_pro,
        org_id="org-review-001",
        is_active=True,
    )
    free_user = models.User(
        id="free-review-001",
        email="free-review@example.com",
        hashed_password="hashed",
        role=models.RoleEnum.free,
        org_id="org-review-001",
        is_active=True,
    )
    analyst_pro = models.User(
        id="analyst-review-001",
        email="analyst-review@example.com",
        hashed_password="hashed",
        role=models.RoleEnum.analyst_pro,
        org_id="org-review-001",
        is_active=True,
    )
    profile = models.PlayerProfile(
        player_id="player-review-001",
        player_name="Review Player",
        total_matches=12,
        total_runs_scored=420,
        total_balls_faced=360,
        total_innings_batted=12,
        total_innings_bowled=5,
        total_wickets=7,
        total_runs_conceded=185,
        total_overs_bowled=22.0,
        total_fours=36,
        total_sixes=18,
        times_out=10,
    )
    assignment = models.CoachPlayerAssignment(
        id="assignment-review-001",
        coach_user_id=coach_pro_plus.id,
        player_profile_id=profile.player_id,
        is_active=True,
    )
    plan = models.PlayerDevelopmentPlan(
        id="plan-review-001",
        player_profile_id=profile.player_id,
        coach_user_id=coach_pro_plus.id,
        org_id="org-review-001",
        title="Video evidence governed plan",
        summary="Pending coach review for video-evidence recommendation.",
        source_type=models.PlayerDevelopmentSourceType.ai_insight,
        evidence_refs=[
            {
                "type": "video_session",
                "id": "video-session-001",
                "label": "Session evidence marker",
            },
            {
                "type": "video_analysis_job",
                "id": "video-job-001",
                "label": "Analysis job evidence marker",
            },
        ],
        ai_metadata={
            "is_official_truth": False,
            "requires_review": True,
            "video_session_id": "video-session-001",
            "video_analysis_job_id": "video-job-001",
        },
    )
    db_session.add_all(
        [
            coach_pro_plus,
            coach_pro,
            org_pro,
            org_other,
            player_pro,
            free_user,
            analyst_pro,
            profile,
            assignment,
            plan,
        ]
    )
    await db_session.commit()
    return {
        "coach_pro_plus": coach_pro_plus,
        "coach_pro": coach_pro,
        "org_pro": org_pro,
        "org_other": org_other,
        "player_pro": player_pro,
        "free_user": free_user,
        "analyst_pro": analyst_pro,
        "plan": plan,
    }


@pytest.mark.asyncio
async def test_coach_pro_plus_can_approve_player_development_plan(async_client, db_session) -> None:
    seeded = await _seed_review_data(db_session)
    coach = seeded["coach_pro_plus"]
    assert isinstance(coach, models.User)
    plan = seeded["plan"]
    assert isinstance(plan, models.PlayerDevelopmentPlan)

    response = await async_client.patch(
        f"/api/player-development/plans/{plan.id}/review",
        headers=_token_headers(coach),
        json={"decision": "approved", "reviewer_notes": "Ready for player discussion."},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["approval_state"] == "approved"
    assert payload["coach_approved"] is True
    assert payload["reviewed_by_user_id"] == coach.id


@pytest.mark.asyncio
async def test_org_pro_can_approve_player_development_plan(async_client, db_session) -> None:
    seeded = await _seed_review_data(db_session)
    org_user = seeded["org_pro"]
    assert isinstance(org_user, models.User)
    plan = seeded["plan"]
    assert isinstance(plan, models.PlayerDevelopmentPlan)

    response = await async_client.patch(
        f"/api/player-development/plans/{plan.id}/review",
        headers=_token_headers(org_user),
        json={"decision": "approved", "reviewer_notes": "Approved at org coaching level."},
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["approval_state"] == "approved"
    assert payload["coach_approved"] is True
    assert payload["reviewed_by_user_id"] == org_user.id


@pytest.mark.asyncio
async def test_review_decision_approved_sets_required_fields(async_client, db_session) -> None:
    seeded = await _seed_review_data(db_session)
    coach = seeded["coach_pro_plus"]
    assert isinstance(coach, models.User)
    plan = seeded["plan"]
    assert isinstance(plan, models.PlayerDevelopmentPlan)

    response = await async_client.patch(
        f"/api/player-development/plans/{plan.id}/review",
        headers=_token_headers(coach),
        json={"decision": "approved"},
    )
    assert response.status_code == 200, response.text
    await db_session.refresh(plan)
    assert plan.approval_state == models.PlayerDevelopmentApprovalState.approved
    assert plan.coach_approved is True


@pytest.mark.asyncio
async def test_review_decision_rejected_sets_required_fields(async_client, db_session) -> None:
    seeded = await _seed_review_data(db_session)
    coach = seeded["coach_pro_plus"]
    assert isinstance(coach, models.User)
    plan = seeded["plan"]
    assert isinstance(plan, models.PlayerDevelopmentPlan)

    response = await async_client.patch(
        f"/api/player-development/plans/{plan.id}/review",
        headers=_token_headers(coach),
        json={"decision": "rejected"},
    )
    assert response.status_code == 200, response.text
    await db_session.refresh(plan)
    assert plan.approval_state == models.PlayerDevelopmentApprovalState.rejected
    assert plan.coach_approved is False


@pytest.mark.asyncio
async def test_review_decision_changes_requested_sets_required_fields(
    async_client,
    db_session,
) -> None:
    seeded = await _seed_review_data(db_session)
    coach = seeded["coach_pro_plus"]
    assert isinstance(coach, models.User)
    plan = seeded["plan"]
    assert isinstance(plan, models.PlayerDevelopmentPlan)

    response = await async_client.patch(
        f"/api/player-development/plans/{plan.id}/review",
        headers=_token_headers(coach),
        json={"decision": "changes_requested", "reviewer_notes": "Need clearer drill sequencing."},
    )
    assert response.status_code == 200, response.text
    await db_session.refresh(plan)
    assert plan.approval_state == models.PlayerDevelopmentApprovalState.changes_requested
    assert plan.coach_approved is False


@pytest.mark.asyncio
async def test_invalid_review_decision_is_rejected(async_client, db_session) -> None:
    seeded = await _seed_review_data(db_session)
    coach = seeded["coach_pro_plus"]
    assert isinstance(coach, models.User)
    plan = seeded["plan"]
    assert isinstance(plan, models.PlayerDevelopmentPlan)

    response = await async_client.patch(
        f"/api/player-development/plans/{plan.id}/review",
        headers=_token_headers(coach),
        json={"decision": "invalid_state"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_unknown_plan_id_returns_not_found(async_client, db_session) -> None:
    seeded = await _seed_review_data(db_session)
    coach = seeded["coach_pro_plus"]
    assert isinstance(coach, models.User)

    response = await async_client.patch(
        "/api/player-development/plans/does-not-exist/review",
        headers=_token_headers(coach),
        json={"decision": "approved"},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Player development plan not found"


@pytest.mark.asyncio
@pytest.mark.parametrize("user_key", ["coach_pro", "player_pro", "free_user", "analyst_pro"])
async def test_unauthorized_roles_cannot_review_player_development_plan(
    async_client,
    db_session,
    user_key: str,
) -> None:
    seeded = await _seed_review_data(db_session)
    user = seeded[user_key]
    assert isinstance(user, models.User)
    plan = seeded["plan"]
    assert isinstance(plan, models.PlayerDevelopmentPlan)

    response = await async_client.patch(
        f"/api/player-development/plans/{plan.id}/review",
        headers=_token_headers(user),
        json={"decision": "approved"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Insufficient role"


@pytest.mark.asyncio
async def test_cross_org_reviewer_access_is_rejected(async_client, db_session) -> None:
    seeded = await _seed_review_data(db_session)
    other_org = seeded["org_other"]
    assert isinstance(other_org, models.User)
    plan = seeded["plan"]
    assert isinstance(plan, models.PlayerDevelopmentPlan)

    response = await async_client.patch(
        f"/api/player-development/plans/{plan.id}/review",
        headers=_token_headers(other_org),
        json={"decision": "approved"},
    )
    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied"


@pytest.mark.asyncio
async def test_archived_plan_cannot_be_reviewed(async_client, db_session) -> None:
    seeded = await _seed_review_data(db_session)
    coach = seeded["coach_pro_plus"]
    assert isinstance(coach, models.User)
    plan = seeded["plan"]
    assert isinstance(plan, models.PlayerDevelopmentPlan)

    plan.status = models.PlayerDevelopmentPlanStatus.archived
    await db_session.commit()

    response = await async_client.patch(
        f"/api/player-development/plans/{plan.id}/review",
        headers=_token_headers(coach),
        json={"decision": "approved"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_review_action_does_not_mutate_evidence_ai_or_truth_fields(
    async_client,
    db_session,
) -> None:
    seeded = await _seed_review_data(db_session)
    coach = seeded["coach_pro_plus"]
    assert isinstance(coach, models.User)
    plan = seeded["plan"]
    assert isinstance(plan, models.PlayerDevelopmentPlan)

    player_profile = await db_session.get(models.PlayerProfile, plan.player_profile_id)
    assert player_profile is not None

    evidence_refs_before = copy.deepcopy(plan.evidence_refs)
    ai_metadata_before = copy.deepcopy(plan.ai_metadata)
    status_before = plan.status
    total_runs_before = player_profile.total_runs_scored
    total_wickets_before = player_profile.total_wickets

    response = await async_client.patch(
        f"/api/player-development/plans/{plan.id}/review",
        headers=_token_headers(coach),
        json={"decision": "approved", "reviewer_notes": "Looks good."},
    )
    assert response.status_code == 200, response.text

    await db_session.refresh(plan)
    await db_session.refresh(player_profile)

    assert plan.evidence_refs == evidence_refs_before
    assert plan.ai_metadata == ai_metadata_before
    assert plan.status == status_before
    assert player_profile.total_runs_scored == total_runs_before
    assert player_profile.total_wickets == total_wickets_before
    assert plan.ai_metadata.get("video_session_id") == "video-session-001"
    assert plan.ai_metadata.get("video_analysis_job_id") == "video-job-001"
