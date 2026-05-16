from __future__ import annotations

import datetime as dt

import pytest

from backend.security import create_access_token
from backend.sql_app import models

UTC = getattr(dt, "UTC", dt.UTC)


def _token_headers(user: models.User) -> dict[str, str]:
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


async def _seed_route_data(db_session) -> tuple[models.User, models.User, models.User, models.PlayerProfile]:
    assigned_coach = models.User(
        id="coach-route-001",
        email="assigned-coach@example.com",
        hashed_password="hashed",  # noqa: S106
        role=models.RoleEnum.coach_pro,
        org_id="org-route-001",
        is_active=True,
    )
    unassigned_coach = models.User(
        id="coach-route-002",
        email="unassigned-coach@example.com",
        hashed_password="hashed",  # noqa: S106
        role=models.RoleEnum.coach_pro_plus,
        org_id="org-route-001",
        is_active=True,
    )
    other_org_user = models.User(
        id="org-route-999",
        email="other-org@example.com",
        hashed_password="hashed",  # noqa: S106
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


@pytest.mark.asyncio
async def test_assigned_coach_can_generate_and_fetch_draft_plan(async_client, db_session) -> None:
    assigned_coach, _unassigned_coach, _other_org_user, profile = await _seed_route_data(db_session)

    create_response = await async_client.post(
        f"/api/player-development/players/{profile.player_id}/draft-plan",
        headers=_token_headers(assigned_coach),
        json={"additional_evidence_refs": [{"type": "manual", "id": "route-extra-001", "label": "Manual review note"}]},
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
async def test_unassigned_coach_is_blocked_from_generating_player_plan(async_client, db_session) -> None:
    _assigned_coach, unassigned_coach, _other_org_user, profile = await _seed_route_data(db_session)

    response = await async_client.post(
        f"/api/player-development/players/{profile.player_id}/draft-plan",
        headers=_token_headers(unassigned_coach),
        json={},
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Coach not assigned"


@pytest.mark.asyncio
async def test_cross_org_user_cannot_fetch_player_development_plan(async_client, db_session) -> None:
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
