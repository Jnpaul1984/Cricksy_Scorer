from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import select

from backend.security import create_access_token
from backend.sql_app import models

def _token_headers(user: models.User) -> dict[str, str]:
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


async def _seed_report_data(
    db_session,
) -> tuple[models.User, models.User, models.User, models.User, models.PlayerProfile]:
    assigned_coach = models.User(
        id="coach-report-001",
        email="coach-report@example.com",
        hashed_password="hashed",  # noqa: S106
        role=models.RoleEnum.coach_pro,
        org_id="org-report-001",
        is_active=True,
    )
    unassigned_coach = models.User(
        id="coach-report-002",
        email="coach-report-unassigned@example.com",
        hashed_password="hashed",  # noqa: S106
        role=models.RoleEnum.coach_pro_plus,
        org_id="org-report-001",
        is_active=True,
    )
    org_user = models.User(
        id="org-report-001-user",
        email="org-report@example.com",
        hashed_password="hashed",  # noqa: S106
        role=models.RoleEnum.org_pro,
        org_id="org-report-001",
        is_active=True,
    )
    other_org_user = models.User(
        id="org-report-999-user",
        email="org-report-other@example.com",
        hashed_password="hashed",  # noqa: S106
        role=models.RoleEnum.org_pro,
        org_id="org-report-999",
        is_active=True,
    )

    player = models.PlayerProfile(
        player_id="player-report-001",
        player_name="Ava Support",
        total_matches=9,
        total_runs_scored=210,
        total_balls_faced=240,
        total_innings_batted=9,
        total_innings_bowled=2,
        total_wickets=1,
        total_runs_conceded=42,
        total_overs_bowled=7.0,
        total_fours=20,
        total_sixes=5,
        times_out=7,
    )
    cross_org_player = models.PlayerProfile(
        player_id="player-report-999",
        player_name="Nia Other",
        total_matches=5,
        total_runs_scored=88,
        total_balls_faced=120,
        total_innings_batted=5,
        total_innings_bowled=1,
        total_wickets=0,
        total_runs_conceded=24,
        total_overs_bowled=4.0,
        total_fours=8,
        total_sixes=2,
        times_out=5,
    )
    db_session.add_all(
        [
            assigned_coach,
            unassigned_coach,
            org_user,
            other_org_user,
            player,
            cross_org_player,
            models.CoachPlayerAssignment(
                id="assignment-report-001",
                coach_user_id=assigned_coach.id,
                player_profile_id=player.player_id,
                is_active=True,
            ),
            models.CoachPlayerAssignment(
                id="assignment-report-999",
                coach_user_id=other_org_user.id,
                player_profile_id=cross_org_player.player_id,
                is_active=True,
            ),
        ]
    )
    await db_session.commit()

    plan = models.PlayerDevelopmentPlan(
        id="plan-report-001",
        player_profile_id=player.player_id,
        coach_user_id=assigned_coach.id,
        org_id="org-report-001",
        title="Ava support plan",
        summary="Advisory support plan.",
        source_type=models.PlayerDevelopmentSourceType.ai_insight,
        coach_approved=False,
        approval_state=models.PlayerDevelopmentApprovalState.pending_review,
        confidence_score=0.48,
        evidence_refs=[{"type": "form", "id": "form-001", "label": "Recent form"}],
        ai_metadata={
            "is_official_truth": False,
            "requires_review": True,
            "limitations": ["More evidence would strengthen this recommendation."],
        },
    )
    plan.strength_tags.append(
        models.PlayerStrengthTag(
            id="strength-report-001",
            plan_id=plan.id,
            player_profile_id=player.player_id,
            category="batting",
            label="Strong off-side rotation",
            confidence_score=0.62,
            source_type=models.PlayerDevelopmentSourceType.ai_insight,
            evidence_refs=plan.evidence_refs,
            ai_metadata=plan.ai_metadata,
            created_at=dt.datetime(2026, 5, 4, 10, 0),
            updated_at=dt.datetime(2026, 5, 4, 10, 0),
        )
    )
    plan.weakness_tags.append(
        models.PlayerWeaknessTag(
            id="weakness-report-001",
            plan_id=plan.id,
            player_profile_id=player.player_id,
            category="mindset",
            label="weakest player under pressure",
            safe_display_label="Pressure response support",
            severity=models.PlayerDevelopmentSeverity.medium,
            confidence_score=0.48,
            source_type=models.PlayerDevelopmentSourceType.ai_insight,
            evidence_refs=plan.evidence_refs,
            ai_metadata=plan.ai_metadata,
            created_at=dt.datetime(2026, 5, 4, 10, 5),
            updated_at=dt.datetime(2026, 5, 4, 10, 5),
        )
    )
    plan.goals.append(
        models.PlayerDevelopmentGoal(
            id="goal-report-001",
            plan_id=plan.id,
            title="Build repeatable reset routine",
            status=models.PlayerDevelopmentPlanStatus.draft,
            due_date=dt.date(2026, 6, 15),
            evidence_refs=plan.evidence_refs,
        )
    )
    plan.drill_assignments.append(
        models.PlayerDrillAssignment(
            id="drill-report-001",
            plan_id=plan.id,
            player_profile_id=player.player_id,
            coach_user_id=assigned_coach.id,
            drill_category="mindset",
            drill_name="Reset breath routine",
            status=models.PlayerDevelopmentPlanStatus.active,
            due_date=dt.date(2026, 5, 30),
            evidence_refs=plan.evidence_refs,
        )
    )
    plan.progress_checkpoints.extend(
        [
            models.PlayerProgressCheckpoint(
                id="checkpoint-report-001",
                plan_id=plan.id,
                player_profile_id=player.player_id,
                coach_user_id=assigned_coach.id,
                checkpoint_date=dt.date.today(),
                summary="Review rhythm changes.",
                progress_status="improved rhythm",
                confidence_score=0.41,
                evidence_refs=[],
                ai_metadata=plan.ai_metadata,
                coach_notes="weakest player response needs support",
            ),
            models.PlayerProgressCheckpoint(
                id="checkpoint-report-002",
                plan_id=plan.id,
                player_profile_id=player.player_id,
                coach_user_id=assigned_coach.id,
                checkpoint_date=dt.date.today() + dt.timedelta(days=7),
                summary="Planned review checkpoint.",
                progress_status="scheduled",
                confidence_score=0.48,
                evidence_refs=plan.evidence_refs,
                ai_metadata=plan.ai_metadata,
                coach_notes="Evidence-backed coaching note",
            ),
        ]
    )

    cross_org_plan = models.PlayerDevelopmentPlan(
        id="plan-report-999",
        player_profile_id=cross_org_player.player_id,
        coach_user_id=other_org_user.id,
        org_id="org-report-999",
        title="Other org plan",
        source_type=models.PlayerDevelopmentSourceType.ai_insight,
        confidence_score=0.72,
        evidence_refs=[{"type": "manual", "id": "hidden", "label": "Hidden"}],
        ai_metadata={"is_official_truth": False, "requires_review": True, "limitations": []},
    )

    db_session.add_all([plan, cross_org_plan])
    await db_session.commit()
    return assigned_coach, unassigned_coach, org_user, other_org_user, player


@pytest.mark.asyncio
async def test_assigned_coach_can_generate_player_report(async_client, db_session) -> None:
    assigned_coach, _unassigned_coach, _org_user, _other_org_user, player = await _seed_report_data(
        db_session
    )

    response = await async_client.get(
        f"/api/player-development/reports/players/{player.player_id}",
        headers=_token_headers(assigned_coach),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["player_name"] == "Ava Support"
    assert payload["plan_id"] == "plan-report-001"
    assert payload["checkpoint_review_summary"]["checkpoints"]


@pytest.mark.asyncio
async def test_unassigned_coach_is_blocked_from_player_report(async_client, db_session) -> None:
    _assigned_coach, unassigned_coach, _org_user, _other_org_user, player = await _seed_report_data(
        db_session
    )

    response = await async_client.get(
        f"/api/player-development/reports/players/{player.player_id}",
        headers=_token_headers(unassigned_coach),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Coach not assigned"


@pytest.mark.asyncio
async def test_org_user_can_generate_org_scoped_report(async_client, db_session) -> None:
    _assigned_coach, _unassigned_coach, org_user, _other_org_user, _player = await _seed_report_data(
        db_session
    )

    response = await async_client.get(
        "/api/player-development/reports/team-summary",
        headers=_token_headers(org_user),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total_assigned_players"] == 1
    assert payload["players_with_plans"] == 1


@pytest.mark.asyncio
async def test_cross_org_report_access_is_blocked(async_client, db_session) -> None:
    _assigned_coach, _unassigned_coach, org_user, _other_org_user, _player = await _seed_report_data(
        db_session
    )

    response = await async_client.get(
        "/api/player-development/reports/plans/plan-report-999",
        headers=_token_headers(org_user),
    )

    assert response.status_code == 403
    assert response.json()["detail"] == "Access denied"


@pytest.mark.asyncio
async def test_report_routes_are_read_only_and_do_not_mutate_stats(async_client, db_session) -> None:
    assigned_coach, _unassigned_coach, _org_user, _other_org_user, player = await _seed_report_data(
        db_session
    )
    before_plan = await db_session.execute(
        select(models.PlayerDevelopmentPlan).where(models.PlayerDevelopmentPlan.id == "plan-report-001")
    )
    plan = before_plan.scalar_one()
    before_status = plan.status
    before_approved = plan.coach_approved
    before_updated_at = plan.updated_at
    before_runs = player.total_runs_scored

    response = await async_client.get(
        "/api/player-development/reports/plans/plan-report-001",
        headers=_token_headers(assigned_coach),
    )

    assert response.status_code == 200, response.text
    await db_session.refresh(plan)
    await db_session.refresh(player)
    assert plan.status == before_status
    assert plan.coach_approved == before_approved
    assert plan.updated_at.replace(tzinfo=None) == before_updated_at.replace(tzinfo=None)
    assert player.total_runs_scored == before_runs


@pytest.mark.asyncio
async def test_report_includes_advisory_disclaimer(async_client, db_session) -> None:
    assigned_coach, _unassigned_coach, _org_user, _other_org_user, player = await _seed_report_data(
        db_session
    )

    response = await async_client.get(
        f"/api/player-development/reports/players/{player.player_id}",
        headers=_token_headers(assigned_coach),
    )

    assert response.status_code == 200, response.text
    assert "Advisory development report only" in response.json()["advisory_disclaimer"]


@pytest.mark.asyncio
async def test_report_uses_safe_development_labels(async_client, db_session) -> None:
    assigned_coach, _unassigned_coach, _org_user, _other_org_user, player = await _seed_report_data(
        db_session
    )

    response = await async_client.get(
        f"/api/player-development/reports/players/{player.player_id}",
        headers=_token_headers(assigned_coach),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["safe_development_areas"][0]["safe_display_label"] == "Pressure response support"
    assert "weakest player" not in response.text.lower()


@pytest.mark.asyncio
async def test_report_includes_evidence_confidence_and_limitations(async_client, db_session) -> None:
    assigned_coach, _unassigned_coach, _org_user, _other_org_user, player = await _seed_report_data(
        db_session
    )

    response = await async_client.get(
        f"/api/player-development/reports/players/{player.player_id}",
        headers=_token_headers(assigned_coach),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["confidence_score"] == 0.48
    assert payload["limitations"] == ["More evidence would strengthen this recommendation."]
    assert payload["evidence_refs"]


@pytest.mark.asyncio
async def test_report_blocks_unsupported_improvement_claim_without_evidence(
    async_client,
    db_session,
) -> None:
    assigned_coach, _unassigned_coach, _org_user, _other_org_user, player = await _seed_report_data(
        db_session
    )

    response = await async_client.get(
        f"/api/player-development/reports/players/{player.player_id}",
        headers=_token_headers(assigned_coach),
    )

    assert response.status_code == 200, response.text
    checkpoints = response.json()["checkpoint_review_summary"]["checkpoints"]
    assert checkpoints[0]["progress_status"] == "needs_evidence_review"
    assert "More evidence would strengthen this recommendation" in checkpoints[0]["progress_statement"]


@pytest.mark.asyncio
async def test_team_summary_report_stays_scoped_to_visible_assignments(async_client, db_session) -> None:
    _assigned_coach, _unassigned_coach, _org_user, other_org_user, _player = await _seed_report_data(
        db_session
    )

    response = await async_client.get(
        "/api/player-development/reports/team-summary",
        headers=_token_headers(other_org_user),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total_assigned_players"] == 1
    assert payload["players_with_plans"] == 1
    assert "Ava Support" not in response.text
