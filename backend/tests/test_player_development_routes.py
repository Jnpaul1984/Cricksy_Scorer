from __future__ import annotations

import datetime as dt

import pytest

from backend.security import create_access_token
from backend.sql_app import models

UTC = getattr(dt, "UTC", dt.UTC)


def _token_headers(user: models.User) -> dict[str, str]:
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


async def _seed_route_data(
    db_session,
) -> tuple[models.User, models.User, models.User, models.PlayerProfile]:
    assigned_coach = models.User(
        id="coach-route-001",
        email="assigned-coach@example.com",
        hashed_password="hashed",
        role=models.RoleEnum.coach_pro,
        org_id="org-route-001",
        is_active=True,
    )
    unassigned_coach = models.User(
        id="coach-route-002",
        email="unassigned-coach@example.com",
        hashed_password="hashed",
        role=models.RoleEnum.coach_pro_plus,
        org_id="org-route-001",
        is_active=True,
    )
    other_org_user = models.User(
        id="org-route-999",
        email="other-org@example.com",
        hashed_password="hashed",
        role=models.RoleEnum.org_pro,
        org_id="org-route-999",
        is_active=True,
    )
    profile = models.PlayerProfile(
        player_id="player-route-001",
        player_name="Route Player",
        total_matches=10,
        total_runs_scored=240,
        total_balls_faced=320,
        total_innings_batted=10,
        total_innings_bowled=4,
        total_wickets=4,
        total_runs_conceded=96,
        total_overs_bowled=16.0,
        total_fours=24,
        total_sixes=8,
        times_out=8,
    )
    db_session.add_all(
        [
            assigned_coach,
            unassigned_coach,
            other_org_user,
            profile,
            models.CoachPlayerAssignment(
                id="assignment-route-001",
                coach_user_id=assigned_coach.id,
                player_profile_id=profile.player_id,
                is_active=True,
            ),
            models.PlayerForm(
                id="route-form-001",
                player_id=profile.player_id,
                period_start=dt.date(2026, 3, 1),
                period_end=dt.date(2026, 3, 31),
                matches_played=4,
                runs=170,
                wickets=1,
                batting_average=42.5,
                strike_rate=128.0,
                economy=6.4,
                form_score=75.0,
            ),
            models.PlayerForm(
                id="route-form-002",
                player_id=profile.player_id,
                period_start=dt.date(2026, 4, 1),
                period_end=dt.date(2026, 4, 30),
                matches_played=4,
                runs=105,
                wickets=1,
                batting_average=21.0,
                strike_rate=95.0,
                economy=6.5,
                form_score=58.0,
            ),
            models.PlayerCoachingNotes(
                id="route-note-001",
                player_id=profile.player_id,
                coach_user_id=assigned_coach.id,
                strengths="Reliable fielder",
                weaknesses="Strike rotation slows after the powerplay",
                action_plan="Use quieter overs for singles and twos.",
                visibility=models.PlayerCoachingNoteVisibility.private_to_coach,
            ),
            models.CoachingSession(
                id="route-session-001",
                coach_user_id=assigned_coach.id,
                player_profile_id=profile.player_id,
                scheduled_at=dt.datetime(2026, 5, 8, 9, 0, tzinfo=UTC),
                duration_minutes=60,
                focus_area="Batting tempo",
                notes="Follow-up session booked.",
                outcome="Needs another review period.",
            ),
        ]
    )
    await db_session.commit()
    return assigned_coach, unassigned_coach, other_org_user, profile


async def _create_plan(
    db_session,
    *,
    plan_id: str,
    player_id: str,
    coach_user_id: str,
    org_id: str,
    title: str,
) -> models.PlayerDevelopmentPlan:
    plan = models.PlayerDevelopmentPlan(
        id=plan_id,
        player_profile_id=player_id,
        coach_user_id=coach_user_id,
        org_id=org_id,
        title=title,
        summary="Draft plan for listing scope checks.",
        source_type=models.PlayerDevelopmentSourceType.ai_insight,
        evidence_refs=[
            {"type": "manual", "id": f"evidence-{plan_id}", "label": "Listing test evidence"}
        ],
        ai_metadata={"is_official_truth": False, "requires_review": True},
    )
    db_session.add(plan)
    await db_session.commit()
    return plan


@pytest.mark.asyncio
async def test_assigned_coach_can_generate_and_fetch_draft_plan(async_client, db_session) -> None:
    assigned_coach, _unassigned_coach, _other_org_user, profile = await _seed_route_data(db_session)

    create_response = await async_client.post(
        f"/api/player-development/players/{profile.player_id}/draft-plan",
        headers=_token_headers(assigned_coach),
        json={
            "additional_evidence_refs": [
                {"type": "manual", "id": "route-extra-001", "label": "Manual review note"}
            ]
        },
    )

    assert create_response.status_code == 200, create_response.text
    payload = create_response.json()
    assert payload["status"] == "draft_created"
    assert payload["coach_review_required"] is True
    assert payload["plan"]["plan"]["status"] == "draft"
    assert payload["plan"]["plan"]["coach_approved"] is False
    assert payload["plan"]["plan"]["approval_state"] == "pending_review"
    assert payload["plan"]["weakness_tags"]
    assert payload["plan"]["drill_assignments"]

    plan_id = payload["plan"]["plan"]["id"]
    get_response = await async_client.get(
        f"/api/player-development/plans/{plan_id}",
        headers=_token_headers(assigned_coach),
    )
    assert get_response.status_code == 200, get_response.text
    assert get_response.json()["plan"]["id"] == plan_id


@pytest.mark.asyncio
async def test_unassigned_coach_is_blocked_from_generating_player_plan(
    async_client, db_session
) -> None:
    _assigned_coach, unassigned_coach, _other_org_user, profile = await _seed_route_data(db_session)

    response = await async_client.post(
        f"/api/player-development/players/{profile.player_id}/draft-plan",
        headers=_token_headers(unassigned_coach),
        json={},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Coach not assigned"


@pytest.mark.asyncio
async def test_cross_org_user_cannot_fetch_player_development_plan(
    async_client, db_session
) -> None:
    assigned_coach, _unassigned_coach, other_org_user, profile = await _seed_route_data(db_session)

    create_response = await async_client.post(
        f"/api/player-development/players/{profile.player_id}/draft-plan",
        headers=_token_headers(assigned_coach),
        json={},
    )
    assert create_response.status_code == 200, create_response.text
    plan_id = create_response.json()["plan"]["plan"]["id"]

    response = await async_client.get(
        f"/api/player-development/plans/{plan_id}",
        headers=_token_headers(other_org_user),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied"


@pytest.mark.asyncio
async def test_coach_can_list_only_their_own_draft_plans(async_client, db_session) -> None:
    assigned_coach, unassigned_coach, _other_org_user, profile = await _seed_route_data(db_session)
    await _create_plan(
        db_session,
        plan_id="plan-list-own-001",
        player_id=profile.player_id,
        coach_user_id=assigned_coach.id,
        org_id=assigned_coach.org_id or "org-route-001",
        title="Assigned coach visible plan",
    )
    await _create_plan(
        db_session,
        plan_id="plan-list-own-002",
        player_id=profile.player_id,
        coach_user_id=unassigned_coach.id,
        org_id="unscoped-org",
        title="Other coach unscoped plan",
    )

    response = await async_client.get(
        f"/api/player-development/players/{profile.player_id}/plans",
        headers=_token_headers(assigned_coach),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert [bundle["plan"]["id"] for bundle in payload] == ["plan-list-own-001"]


@pytest.mark.asyncio
async def test_coach_cannot_list_other_coach_unscoped_plans_for_same_player(
    async_client,
    db_session,
) -> None:
    assigned_coach, unassigned_coach, _other_org_user, profile = await _seed_route_data(db_session)
    db_session.add(
        models.CoachPlayerAssignment(
            id="assignment-route-002",
            coach_user_id=unassigned_coach.id,
            player_profile_id=profile.player_id,
            is_active=True,
        )
    )
    await db_session.commit()
    await _create_plan(
        db_session,
        plan_id="plan-list-scope-001",
        player_id=profile.player_id,
        coach_user_id=unassigned_coach.id,
        org_id="unscoped-org",
        title="Unscoped plan owned by other coach",
    )

    response = await async_client.get(
        f"/api/player-development/players/{profile.player_id}/plans",
        headers=_token_headers(assigned_coach),
    )

    assert response.status_code == 200, response.text
    assert response.json() == []


@pytest.mark.asyncio
async def test_org_pro_can_list_org_scoped_plans_only(async_client, db_session) -> None:
    assigned_coach, _unassigned_coach, _other_org_user, profile = await _seed_route_data(db_session)
    org_user = models.User(
        id="org-route-001-user",
        email="org-user@example.com",
        hashed_password="hashed",
        role=models.RoleEnum.org_pro,
        org_id="org-route-001",
        is_active=True,
    )
    db_session.add(org_user)
    await db_session.commit()
    await _create_plan(
        db_session,
        plan_id="plan-org-list-001",
        player_id=profile.player_id,
        coach_user_id=assigned_coach.id,
        org_id="org-route-001",
        title="Org visible plan",
    )
    await _create_plan(
        db_session,
        plan_id="plan-org-list-002",
        player_id=profile.player_id,
        coach_user_id=assigned_coach.id,
        org_id="org-route-999",
        title="Cross-org hidden plan",
    )

    response = await async_client.get(
        f"/api/player-development/players/{profile.player_id}/plans",
        headers=_token_headers(org_user),
    )

    assert response.status_code == 200, response.text
    assert [bundle["plan"]["id"] for bundle in response.json()] == ["plan-org-list-001"]


@pytest.mark.asyncio
async def test_cross_org_plans_are_not_exposed_in_list_results(async_client, db_session) -> None:
    assigned_coach, _unassigned_coach, other_org_user, profile = await _seed_route_data(db_session)
    db_session.add(
        models.CoachPlayerAssignment(
            id="assignment-route-999",
            coach_user_id=other_org_user.id,
            player_profile_id=profile.player_id,
            is_active=True,
        )
    )
    await db_session.commit()
    await _create_plan(
        db_session,
        plan_id="plan-cross-org-001",
        player_id=profile.player_id,
        coach_user_id=assigned_coach.id,
        org_id="org-route-001",
        title="Visible org plan",
    )
    await _create_plan(
        db_session,
        plan_id="plan-cross-org-002",
        player_id=profile.player_id,
        coach_user_id=other_org_user.id,
        org_id="org-route-999",
        title="Hidden cross-org plan",
    )

    response = await async_client.get(
        f"/api/player-development/players/{profile.player_id}/plans",
        headers=_token_headers(other_org_user),
    )

    assert response.status_code == 200, response.text
    assert [bundle["plan"]["id"] for bundle in response.json()] == ["plan-cross-org-002"]
