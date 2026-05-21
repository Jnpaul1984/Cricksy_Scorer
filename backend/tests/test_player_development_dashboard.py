from __future__ import annotations

import datetime as dt

import pytest
from sqlalchemy import select

from backend.security import create_access_token
from backend.sql_app import models

UTC = getattr(dt, "UTC", dt.UTC)


def _token_headers(user: models.User) -> dict[str, str]:
    token = create_access_token({"sub": user.id, "email": user.email, "role": user.role.value})
    return {"Authorization": f"Bearer {token}"}


async def _seed_dashboard_data(
    db_session,
) -> tuple[models.User, models.User, models.User, models.User]:
    coach_user = models.User(
        id="coach-dashboard-001",
        email="coach-dashboard@example.com",
        hashed_password="hashed",
        role=models.RoleEnum.coach_pro,
        org_id="org-dashboard-001",
        is_active=True,
    )
    org_user = models.User(
        id="org-dashboard-001-user",
        email="org-dashboard@example.com",
        hashed_password="hashed",
        role=models.RoleEnum.org_pro,
        org_id="org-dashboard-001",
        is_active=True,
    )
    org_coach_two = models.User(
        id="coach-dashboard-002",
        email="coach-dashboard-two@example.com",
        hashed_password="hashed",
        role=models.RoleEnum.coach_pro_plus,
        org_id="org-dashboard-001",
        is_active=True,
    )
    other_org_user = models.User(
        id="coach-dashboard-999",
        email="coach-dashboard-other@example.com",
        hashed_password="hashed",
        role=models.RoleEnum.org_pro,
        org_id="org-dashboard-999",
        is_active=True,
    )

    player_one = models.PlayerProfile(
        player_id="player-dashboard-001",
        player_name="Ava Support",
        total_matches=8,
        total_runs_scored=240,
        total_balls_faced=220,
        total_innings_batted=8,
        total_innings_bowled=2,
        total_wickets=1,
        total_runs_conceded=48,
        total_overs_bowled=8.0,
        total_fours=28,
        total_sixes=4,
        times_out=7,
    )
    player_two = models.PlayerProfile(
        player_id="player-dashboard-002",
        player_name="Ben Builder",
        total_matches=2,
        total_runs_scored=40,
        total_balls_faced=54,
        total_innings_batted=2,
        total_innings_bowled=0,
        total_wickets=0,
        total_runs_conceded=0,
        total_overs_bowled=0.0,
        total_fours=4,
        total_sixes=0,
        times_out=2,
    )
    player_three = models.PlayerProfile(
        player_id="player-dashboard-003",
        player_name="Cara Growth",
        total_matches=12,
        total_runs_scored=330,
        total_balls_faced=290,
        total_innings_batted=12,
        total_innings_bowled=6,
        total_wickets=7,
        total_runs_conceded=120,
        total_overs_bowled=20.0,
        total_fours=34,
        total_sixes=9,
        times_out=10,
    )
    player_four = models.PlayerProfile(
        player_id="player-dashboard-004",
        player_name="Dina Crossorg",
        total_matches=9,
        total_runs_scored=180,
        total_balls_faced=175,
        total_innings_batted=9,
        total_innings_bowled=3,
        total_wickets=3,
        total_runs_conceded=72,
        total_overs_bowled=10.0,
        total_fours=16,
        total_sixes=6,
        times_out=8,
    )

    db_session.add_all(
        [
            coach_user,
            org_user,
            org_coach_two,
            other_org_user,
            player_one,
            player_two,
            player_three,
            player_four,
            models.CoachPlayerAssignment(
                id="assignment-dashboard-001",
                coach_user_id=coach_user.id,
                player_profile_id=player_one.player_id,
                is_active=True,
            ),
            models.CoachPlayerAssignment(
                id="assignment-dashboard-002",
                coach_user_id=coach_user.id,
                player_profile_id=player_two.player_id,
                is_active=True,
            ),
            models.CoachPlayerAssignment(
                id="assignment-dashboard-003",
                coach_user_id=org_coach_two.id,
                player_profile_id=player_three.player_id,
                is_active=True,
            ),
            models.CoachPlayerAssignment(
                id="assignment-dashboard-999",
                coach_user_id=other_org_user.id,
                player_profile_id=player_four.player_id,
                is_active=True,
            ),
        ]
    )
    await db_session.commit()

    plan_one = models.PlayerDevelopmentPlan(
        id="plan-dashboard-001",
        player_profile_id=player_one.player_id,
        coach_user_id=coach_user.id,
        org_id="org-dashboard-001",
        title="Ava draft plan",
        summary="Constructive batting and review plan.",
        status=models.PlayerDevelopmentPlanStatus.draft,
        source_type=models.PlayerDevelopmentSourceType.ai_insight,
        coach_approved=False,
        approval_state=models.PlayerDevelopmentApprovalState.pending_review,
        confidence_score=0.78,
        evidence_refs=[{"type": "form", "id": "form-ava", "label": "Recent form"}],
        ai_metadata={
            "is_official_truth": False,
            "requires_review": True,
            "limitations": [],
        },
        created_at=dt.datetime(2026, 5, 1, 9, 0, tzinfo=UTC),
        updated_at=dt.datetime(2026, 5, 7, 12, 0, tzinfo=UTC),
    )
    plan_one.goals.extend(
        [
            models.PlayerDevelopmentGoal(
                id="goal-dashboard-001",
                plan_id=plan_one.id,
                title="Rotate strike early",
                status=models.PlayerDevelopmentPlanStatus.draft,
                due_date=dt.date(2026, 6, 1),
                created_at=dt.datetime(2026, 5, 1, 9, 5, tzinfo=UTC),
                updated_at=dt.datetime(2026, 5, 1, 9, 5, tzinfo=UTC),
            )
        ]
    )
    plan_one.weakness_tags.extend(
        [
            models.PlayerWeaknessTag(
                id="weak-dashboard-001",
                plan_id=plan_one.id,
                player_profile_id=player_one.player_id,
                category="batting",
                label="batting tempo",
                safe_display_label="Batting tempo",
                severity=models.PlayerDevelopmentSeverity.medium,
                confidence_score=0.78,
                source_type=models.PlayerDevelopmentSourceType.ai_insight,
                evidence_refs=plan_one.evidence_refs,
                ai_metadata=plan_one.ai_metadata,
                created_at=dt.datetime(2026, 5, 1, 9, 10, tzinfo=UTC),
                updated_at=dt.datetime(2026, 5, 1, 9, 10, tzinfo=UTC),
            )
        ]
    )
    plan_one.drill_assignments.extend(
        [
            models.PlayerDrillAssignment(
                id="drill-dashboard-001",
                plan_id=plan_one.id,
                player_profile_id=player_one.player_id,
                coach_user_id=coach_user.id,
                drill_category="batting",
                drill_name="Tempo ladder",
                status=models.PlayerDevelopmentPlanStatus.draft,
                due_date=dt.date(2026, 5, 25),
                evidence_refs=plan_one.evidence_refs,
                created_at=dt.datetime(2026, 5, 1, 9, 15, tzinfo=UTC),
                updated_at=dt.datetime(2026, 5, 2, 10, 0, tzinfo=UTC),
            ),
            models.PlayerDrillAssignment(
                id="drill-dashboard-002",
                plan_id=plan_one.id,
                player_profile_id=player_one.player_id,
                coach_user_id=coach_user.id,
                drill_category="fielding",
                drill_name="Reaction catches",
                status=models.PlayerDevelopmentPlanStatus.completed,
                due_date=dt.date(2026, 5, 10),
                completed_at=dt.datetime(2026, 5, 8, 9, 0, tzinfo=UTC),
                evidence_refs=plan_one.evidence_refs,
                created_at=dt.datetime(2026, 5, 1, 9, 20, tzinfo=UTC),
                updated_at=dt.datetime(2026, 5, 8, 9, 0, tzinfo=UTC),
            ),
        ]
    )
    plan_one.progress_checkpoints.extend(
        [
            models.PlayerProgressCheckpoint(
                id="checkpoint-dashboard-001",
                plan_id=plan_one.id,
                player_profile_id=player_one.player_id,
                coach_user_id=coach_user.id,
                checkpoint_date=dt.date.today() - dt.timedelta(days=2),
                summary="Review strike rotation choices.",
                progress_status="needs_review",
                confidence_score=0.71,
                evidence_refs=plan_one.evidence_refs,
                ai_metadata=plan_one.ai_metadata,
                coach_notes="Bring match clips for review.",
                created_at=dt.datetime(2026, 5, 2, 11, 0, tzinfo=UTC),
                updated_at=dt.datetime(2026, 5, 6, 11, 0, tzinfo=UTC),
            ),
            models.PlayerProgressCheckpoint(
                id="checkpoint-dashboard-002",
                plan_id=plan_one.id,
                player_profile_id=player_one.player_id,
                coach_user_id=coach_user.id,
                checkpoint_date=dt.date.today() + dt.timedelta(days=3),
                summary="Check progress against tempo goal.",
                progress_status="scheduled",
                confidence_score=0.71,
                evidence_refs=plan_one.evidence_refs,
                ai_metadata=plan_one.ai_metadata,
                coach_notes=None,
                created_at=dt.datetime(2026, 5, 2, 11, 15, tzinfo=UTC),
                updated_at=dt.datetime(2026, 5, 2, 11, 15, tzinfo=UTC),
            ),
        ]
    )

    plan_three = models.PlayerDevelopmentPlan(
        id="plan-dashboard-003",
        player_profile_id=player_three.player_id,
        coach_user_id=org_coach_two.id,
        org_id="org-dashboard-001",
        title="Cara support plan",
        summary="Focus on confidence through repeatable batting routines.",
        status=models.PlayerDevelopmentPlanStatus.paused,
        source_type=models.PlayerDevelopmentSourceType.ai_insight,
        coach_approved=False,
        approval_state=models.PlayerDevelopmentApprovalState.pending_review,
        confidence_score=0.45,
        evidence_refs=[{"type": "note", "id": "note-cara", "label": "Coach note"}],
        ai_metadata={
            "is_official_truth": False,
            "requires_review": True,
            "limitations": ["More recent match evidence would strengthen this draft."],
        },
        created_at=dt.datetime(2026, 5, 3, 10, 0, tzinfo=UTC),
        updated_at=dt.datetime(2026, 5, 9, 13, 0, tzinfo=UTC),
    )
    plan_three.goals.extend(
        [
            models.PlayerDevelopmentGoal(
                id="goal-dashboard-003",
                plan_id=plan_three.id,
                title="Build repeatable setup",
                status=models.PlayerDevelopmentPlanStatus.active,
                due_date=dt.date(2026, 6, 3),
                created_at=dt.datetime(2026, 5, 3, 10, 5, tzinfo=UTC),
                updated_at=dt.datetime(2026, 5, 3, 10, 5, tzinfo=UTC),
            )
        ]
    )
    plan_three.weakness_tags.extend(
        [
            models.PlayerWeaknessTag(
                id="weak-dashboard-003",
                plan_id=plan_three.id,
                player_profile_id=player_three.player_id,
                category="batting",
                label="batting tempo",
                safe_display_label="Batting tempo",
                severity=models.PlayerDevelopmentSeverity.medium,
                confidence_score=0.45,
                source_type=models.PlayerDevelopmentSourceType.ai_insight,
                evidence_refs=plan_three.evidence_refs,
                ai_metadata=plan_three.ai_metadata,
                created_at=dt.datetime(2026, 5, 3, 10, 10, tzinfo=UTC),
                updated_at=dt.datetime(2026, 5, 3, 10, 10, tzinfo=UTC),
            ),
            models.PlayerWeaknessTag(
                id="weak-dashboard-004",
                plan_id=plan_three.id,
                player_profile_id=player_three.player_id,
                category="mindset",
                label="confidence reset",
                safe_display_label="Reset between balls",
                severity=models.PlayerDevelopmentSeverity.low,
                confidence_score=0.45,
                source_type=models.PlayerDevelopmentSourceType.ai_insight,
                evidence_refs=plan_three.evidence_refs,
                ai_metadata=plan_three.ai_metadata,
                created_at=dt.datetime(2026, 5, 3, 10, 12, tzinfo=UTC),
                updated_at=dt.datetime(2026, 5, 3, 10, 12, tzinfo=UTC),
            ),
        ]
    )
    plan_three.drill_assignments.extend(
        [
            models.PlayerDrillAssignment(
                id="drill-dashboard-003",
                plan_id=plan_three.id,
                player_profile_id=player_three.player_id,
                coach_user_id=org_coach_two.id,
                drill_category="mindset",
                drill_name="Reset routine",
                status=models.PlayerDevelopmentPlanStatus.active,
                due_date=dt.date(2026, 5, 28),
                evidence_refs=plan_three.evidence_refs,
                created_at=dt.datetime(2026, 5, 3, 10, 15, tzinfo=UTC),
                updated_at=dt.datetime(2026, 5, 9, 13, 0, tzinfo=UTC),
            )
        ]
    )
    plan_three.progress_checkpoints.extend(
        [
            models.PlayerProgressCheckpoint(
                id="checkpoint-dashboard-003",
                plan_id=plan_three.id,
                player_profile_id=player_three.player_id,
                coach_user_id=org_coach_two.id,
                checkpoint_date=dt.date.today() + dt.timedelta(days=5),
                summary="Review reset routine consistency.",
                progress_status="planned",
                confidence_score=0.45,
                evidence_refs=plan_three.evidence_refs,
                ai_metadata=plan_three.ai_metadata,
                coach_notes=None,
                created_at=dt.datetime(2026, 5, 3, 10, 20, tzinfo=UTC),
                updated_at=dt.datetime(2026, 5, 9, 13, 0, tzinfo=UTC),
            )
        ]
    )

    cross_org_plan = models.PlayerDevelopmentPlan(
        id="plan-dashboard-999",
        player_profile_id=player_four.player_id,
        coach_user_id=other_org_user.id,
        org_id="org-dashboard-999",
        title="Hidden cross-org plan",
        summary="Must never leak into org one.",
        status=models.PlayerDevelopmentPlanStatus.draft,
        source_type=models.PlayerDevelopmentSourceType.ai_insight,
        coach_approved=False,
        approval_state=models.PlayerDevelopmentApprovalState.pending_review,
        confidence_score=0.82,
        evidence_refs=[{"type": "manual", "id": "hidden", "label": "Hidden"}],
        ai_metadata={"is_official_truth": False, "requires_review": True, "limitations": []},
        created_at=dt.datetime(2026, 5, 4, 10, 0, tzinfo=UTC),
        updated_at=dt.datetime(2026, 5, 4, 10, 0, tzinfo=UTC),
    )

    db_session.add_all([plan_one, plan_three, cross_org_plan])
    await db_session.commit()
    return coach_user, org_user, org_coach_two, other_org_user


@pytest.mark.asyncio
async def test_coach_dashboard_only_shows_assigned_players(async_client, db_session) -> None:
    coach_user, _org_user, _org_coach_two, _other_org_user = await _seed_dashboard_data(db_session)

    response = await async_client.get(
        "/api/player-development/dashboard/team-overview",
        headers=_token_headers(coach_user),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total_assigned_players"] == 2
    assert payload["players_with_draft_plans"] == 1
    assert payload["players_without_plans"] == 1
    assert payload["plans_requiring_review"] == 1
    assert payload["players_without_plan_details"] == [
        {"player_profile_id": "player-dashboard-002", "player_name": "Ben Builder"}
    ]
    assert [player["player_name"] for player in payload["review_required_players"]] == [
        "Ava Support"
    ]
    assert [theme["safe_display_label"] for theme in payload["common_development_areas"]] == [
        "Batting tempo"
    ]


@pytest.mark.asyncio
async def test_org_dashboard_only_shows_org_scoped_data(async_client, db_session) -> None:
    _coach_user, org_user, _org_coach_two, _other_org_user = await _seed_dashboard_data(db_session)

    response = await async_client.get(
        "/api/player-development/dashboard/team-overview",
        headers=_token_headers(org_user),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total_assigned_players"] == 3
    assert payload["players_with_draft_plans"] == 2
    assert payload["players_without_plans"] == 1
    assert payload["plans_requiring_review"] == 2
    assert {player["player_name"] for player in payload["review_required_players"]} == {
        "Ava Support",
        "Cara Growth",
    }
    assert "Dina Crossorg" not in response.text


@pytest.mark.asyncio
async def test_cross_org_dashboard_data_is_blocked(async_client, db_session) -> None:
    _coach_user, _org_user, _org_coach_two, other_org_user = await _seed_dashboard_data(db_session)

    response = await async_client.get(
        "/api/player-development/dashboard/team-overview",
        headers=_token_headers(other_org_user),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["total_assigned_players"] == 1
    assert payload["players_with_draft_plans"] == 1
    assert payload["players_without_plans"] == 0
    assert "Ava Support" not in response.text
    assert "Cara Growth" not in response.text


@pytest.mark.asyncio
async def test_dashboard_aggregation_counts_real_plan_data(async_client, db_session) -> None:
    _coach_user, org_user, _org_coach_two, _other_org_user = await _seed_dashboard_data(db_session)

    response = await async_client.get(
        "/api/player-development/dashboard/team-overview",
        headers=_token_headers(org_user),
    )

    assert response.status_code == 200, response.text
    payload = response.json()
    assert payload["players_with_goals"] == 2
    assert payload["players_with_drills"] == 2
    assert payload["players_with_checkpoints"] == 2
    assert payload["plans_by_status"] == [
        {"status": "draft", "count": 1},
        {"status": "paused", "count": 1},
    ]
    assert payload["drill_assignment_summary"]["total_assignments"] == 3
    assert payload["drill_assignment_summary"]["by_status"] == [
        {"status": "active", "count": 1},
        {"status": "completed", "count": 1},
        {"status": "draft", "count": 1},
    ]
    assert payload["drill_assignment_summary"]["by_category"] == [
        {"category": "batting", "count": 1},
        {"category": "fielding", "count": 1},
        {"category": "mindset", "count": 1},
    ]
    assert payload["evidence_coverage_summary"]["players_with_confident_recommendations"] == 1
    assert payload["evidence_coverage_summary"]["players_needing_more_evidence"] == 1
    assert payload["evidence_coverage_summary"]["players_needing_more_evidence_details"] == [
        {
            "player_profile_id": "player-dashboard-003",
            "player_name": "Cara Growth",
            "plan_id": "plan-dashboard-003",
            "plan_status": "paused",
            "confidence_score": 0.45,
            "advisory_note": "More recent match evidence would strengthen this draft.",
        }
    ]
    assert payload["common_development_areas"] == [
        {"category": "batting", "safe_display_label": "Batting tempo", "player_count": 2},
        {"category": "mindset", "safe_display_label": "Reset between balls", "player_count": 1},
    ]
    assert len(payload["upcoming_checkpoints"]) == 3
    assert payload["upcoming_checkpoints"][0]["is_overdue"] is True
    assert payload["upcoming_checkpoints"][0]["advisory_label"] == "Review overdue"


@pytest.mark.asyncio
async def test_dashboard_route_is_read_only_for_plans(async_client, db_session) -> None:
    coach_user, _org_user, _org_coach_two, _other_org_user = await _seed_dashboard_data(db_session)
    before = await db_session.execute(
        select(models.PlayerDevelopmentPlan).where(
            models.PlayerDevelopmentPlan.id == "plan-dashboard-001"
        )
    )
    plan_before = before.scalar_one()
    before_status = plan_before.status
    before_approved = plan_before.coach_approved
    before_updated_at = plan_before.updated_at

    response = await async_client.get(
        "/api/player-development/dashboard/team-overview",
        headers=_token_headers(coach_user),
    )

    assert response.status_code == 200, response.text
    await db_session.refresh(plan_before)
    assert plan_before.status == before_status
    assert plan_before.coach_approved == before_approved
    assert plan_before.updated_at.replace(tzinfo=None) == before_updated_at.replace(tzinfo=None)


@pytest.mark.asyncio
async def test_dashboard_route_does_not_mutate_official_player_stats(
    async_client, db_session
) -> None:
    coach_user, _org_user, _org_coach_two, _other_org_user = await _seed_dashboard_data(db_session)
    profile = await db_session.get(models.PlayerProfile, "player-dashboard-001")
    assert profile is not None
    before_runs = profile.total_runs_scored
    before_matches = profile.total_matches

    response = await async_client.get(
        "/api/player-development/dashboard/team-overview",
        headers=_token_headers(coach_user),
    )

    assert response.status_code == 200, response.text
    await db_session.refresh(profile)
    assert profile.total_runs_scored == before_runs
    assert profile.total_matches == before_matches


@pytest.mark.asyncio
async def test_empty_dashboard_response_is_safe(async_client, db_session) -> None:
    coach_user = models.User(
        id="coach-dashboard-empty",
        email="coach-empty@example.com",
        hashed_password="hashed",
        role=models.RoleEnum.coach_pro_plus,
        org_id="org-dashboard-empty",
        is_active=True,
    )
    db_session.add(coach_user)
    await db_session.commit()

    response = await async_client.get(
        "/api/player-development/dashboard/team-overview",
        headers=_token_headers(coach_user),
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "total_assigned_players": 0,
        "players_with_draft_plans": 0,
        "players_without_plans": 0,
        "plans_requiring_review": 0,
        "players_with_goals": 0,
        "players_with_drills": 0,
        "players_with_checkpoints": 0,
        "plans_by_status": [],
        "players_without_plan_details": [],
        "review_required_players": [],
        "common_development_areas": [],
        "drill_assignment_summary": {"total_assignments": 0, "by_status": [], "by_category": []},
        "evidence_coverage_summary": {
            "players_with_confident_recommendations": 0,
            "players_needing_more_evidence": 0,
            "players_needing_more_evidence_details": [],
        },
        "upcoming_checkpoints": [],
        "most_recent_development_activity_at": None,
    }
