"""Approved three-Game trial transitions, boundaries and retained evidence."""

from __future__ import annotations

import asyncio
import datetime as dt

import pytest
from sqlalchemy import select

from backend.services import organization_team_performance_trial_service as trial_service
from backend.services.organization_team_performance_access import TeamPerformanceAccessError
from backend.sql_app import models
from backend.tests.school_test_helpers import create_club, create_school, register_user
from backend.tests.test_school_team_analytics import _hand_calculated_deliveries, _seed_team_game


async def _make_game(client, org_id: str, owner_id: str, date: dt.date, team=None):
    team, game, target, opponent = await _seed_team_game(
        client,
        org_id,
        owner_id,
        deliveries=None,
        overs_limit=25,
        reuse_team=team,
    )
    async with client.session_maker() as db:
        saved_team = await db.get(models.Team, team.id)
        saved_game = await db.get(models.Game, game.id)
        assert saved_team is not None and saved_game is not None
        saved_team.status = "active"
        saved_game.deliveries = _hand_calculated_deliveries(target, opponent)
        saved_game.actual_played_date = date
        saved_game.played_date_trust_state = "confirmed"
        saved_game.played_date_source = "staff_confirmed"
        saved_game.original_overs_limit = 25
        saved_game.original_format_trust_state = "setup_capture"
        saved_game.original_format_source = "school_match_setup"
        await db.commit()
    return team, game


@pytest.mark.parametrize("organization_type", ["school", "club"])
def test_trial_is_default_off_then_consumes_three_distinct_verified_games(
    school_client,
    monkeypatch,
    organization_type: str,
) -> None:
    owner = register_user(school_client, f"trial-owner-{organization_type}@example.com")
    operator = register_user(school_client, f"trial-operator-{organization_type}@example.com")
    organization = (create_school if organization_type == "school" else create_club)(
        school_client, owner, "Trial organization"
    )
    org_id = organization["id"]
    clock = {"now": dt.datetime(2026, 11, 28, 12, tzinfo=dt.UTC)}
    monkeypatch.setattr(trial_service, "_now", lambda: clock["now"])

    async def scenario():
        team = None
        games = []
        for day in range(18, 23):
            team, game = await _make_game(
                school_client, org_id, owner.id, dt.date(2026, 11, day), team
            )
            games.append(game)
        assert team is not None
        async with school_client.session_maker() as db:
            user = await db.get(models.User, operator.id)
            assert user is not None
            user.is_superuser = True
            await db.commit()
        async with school_client.session_maker() as db:
            with pytest.raises(TeamPerformanceAccessError):
                await trial_service.activate_trial(
                    db,
                    organization_id=org_id,
                    team_id=team.id,
                    actor_user_id=owner.id,
                    venue_timezone="Etc/UTC",
                    reason="Pilot offer",
                )
            await db.rollback()
            await trial_service.set_trial_availability(
                db,
                organization_id=org_id,
                operator_user_id=operator.id,
                enabled=True,
                reason="Controlled test availability",
            )
            await db.commit()
        async with school_client.session_maker() as db:
            trial = await trial_service.activate_trial(
                db,
                organization_id=org_id,
                team_id=team.id,
                actor_user_id=owner.id,
                venue_timezone="Etc/UTC",
                reason="Five prior matches",
            )
            await db.commit()
            assert trial.activation_local_date == dt.date(2026, 11, 28)
            assert len(trial.prerequisite_sources) == 5
            with pytest.raises(trial_service.TrialTransitionError):
                await trial_service.activate_trial(
                    db,
                    organization_id=org_id,
                    team_id=team.id,
                    actor_user_id=owner.id,
                    venue_timezone="Etc/UTC",
                    reason="Repeat",
                )
        for ordinal, day in enumerate((28, 29, 30), start=1):
            clock["now"] = dt.datetime(2026, 11, day, 17, tzinfo=dt.UTC)
            _, game = await _make_game(
                school_client, org_id, owner.id, dt.date(2026, 11, day), team
            )
            games.append(game)
            async with school_client.session_maker() as db:
                event = await trial_service.record_completion_event(db, game_id=game.id)
                assert event is not None
                await db.commit()
                await trial_service.process_completion_event(db, completion_event_id=event.id)
                await db.commit()
                await trial_service.process_completion_event(db, completion_event_id=event.id)
                await db.commit()
                status = await trial_service.trial_status(
                    db,
                    organization_id=org_id,
                    team_id=team.id,
                    actor_user_id=owner.id,
                )
                assert status["games_used"] == ordinal
                assert status["games_remaining"] == 3 - ordinal
                report = await trial_service.retained_trial_report(
                    db,
                    organization_id=org_id,
                    team_id=team.id,
                    actor_user_id=owner.id,
                )
                assert report["sample_size"] == 5
                snapshot = await db.scalar(
                    select(models.TeamPerformanceTrialSnapshot).where(
                        models.TeamPerformanceTrialSnapshot.trial_id == trial.id,
                        models.TeamPerformanceTrialSnapshot.ordinal == ordinal,
                    )
                )
                assert snapshot is not None
                assert [source["game_id"] for source in snapshot.sources] == [
                    item.id for item in games[ordinal : ordinal + 5]
                ]
        clock["now"] = dt.datetime(2026, 12, 15, 18, tzinfo=dt.UTC)
        async with school_client.session_maker() as db:
            with pytest.raises(TeamPerformanceAccessError):
                await trial_service.retained_trial_report(
                    db,
                    organization_id=org_id,
                    team_id=team.id,
                    actor_user_id=owner.id,
                )

    asyncio.run(scenario())


@pytest.mark.skipif(
    __import__("os").getenv("PHASE7B_POSTGRES_MIGRATED_TESTS") != "1",
    reason="Real migrated PostgreSQL two-writer gate",
)
def test_concurrent_completion_claims_stop_at_three_and_preserve_order(
    school_client,
    monkeypatch,
) -> None:
    owner = register_user(school_client, "trial-concurrent-owner@example.com")
    operator = register_user(school_client, "trial-concurrent-operator@example.com")
    org_id = create_school(school_client, owner, "Concurrent trial")["id"]
    clock = {"now": dt.datetime(2026, 11, 28, 12, tzinfo=dt.UTC)}
    monkeypatch.setattr(trial_service, "_now", lambda: clock["now"])

    async def scenario():
        team = None
        for day in range(18, 23):
            team, _ = await _make_game(
                school_client, org_id, owner.id, dt.date(2026, 11, day), team
            )
        assert team is not None
        async with school_client.session_maker() as db:
            user = await db.get(models.User, operator.id)
            assert user is not None
            user.is_superuser = True
            await db.commit()
            await trial_service.set_trial_availability(
                db,
                organization_id=org_id,
                operator_user_id=operator.id,
                enabled=True,
                reason="Controlled concurrent test",
            )
            await db.commit()
            trial = await trial_service.activate_trial(
                db,
                organization_id=org_id,
                team_id=team.id,
                actor_user_id=owner.id,
                venue_timezone="Etc/UTC",
                reason="Ready",
            )
            await db.commit()
            trial_id = trial.id
        for day in (28, 29):
            clock["now"] = dt.datetime(2026, 11, day, 17, tzinfo=dt.UTC)
            _, game = await _make_game(
                school_client, org_id, owner.id, dt.date(2026, 11, day), team
            )
            async with school_client.session_maker() as db:
                event = await trial_service.record_completion_event(db, game_id=game.id)
                assert event is not None
                await db.commit()
                await trial_service.process_completion_event(db, completion_event_id=event.id)
                await db.commit()
        # Automatic processing must survive the activating owner's departure.
        async with school_client.session_maker() as db:
            activating_owner = await db.get(models.User, owner.id)
            assert activating_owner is not None
            activating_owner.is_active = False
            await db.commit()
        pending = []
        for date in (dt.date(2026, 11, 30), dt.date(2026, 12, 1)):
            clock["now"] = dt.datetime.combine(date, dt.time(17), tzinfo=dt.UTC)
            _, game = await _make_game(school_client, org_id, owner.id, date, team)
            async with school_client.session_maker() as db:
                event = await trial_service.record_completion_event(db, game_id=game.id)
                assert event is not None
                await db.commit()
                pending.append((event.id, game.id))

        async def process(event_id: str):
            async with school_client.session_maker() as db:
                await trial_service.process_completion_event(db, completion_event_id=event_id)
                await db.commit()

        await asyncio.gather(process(pending[1][0]), process(pending[0][0]))
        async with school_client.session_maker() as db:
            rows = (
                await db.scalars(
                    select(models.TeamPerformanceTrialConsumption)
                    .where(models.TeamPerformanceTrialConsumption.trial_id == trial_id)
                    .order_by(models.TeamPerformanceTrialConsumption.played_date)
                )
            ).all()
            assert len(rows) == 3
            assert rows[-1].game_id == pending[0][1]
            assert pending[1][1] not in {row.game_id for row in rows}
            persisted = await db.get(models.TeamPerformanceTrial, trial_id)
            assert persisted is not None and persisted.state == "exhausted"

    asyncio.run(scenario())


def test_trial_activation_authority_timezone_and_revocation(school_client, monkeypatch) -> None:
    from backend.tests.school_test_helpers import add_membership

    owner = register_user(school_client, "trial-access-owner@example.com")
    coach = register_user(school_client, "trial-access-coach@example.com")
    scorer = register_user(school_client, "trial-access-scorer@example.com")
    viewer = register_user(school_client, "trial-access-viewer@example.com")
    operator = register_user(school_client, "trial-access-operator@example.com")
    foreign = register_user(school_client, "trial-access-foreign@example.com")
    org_id = create_school(school_client, owner, "Trial roles")["id"]
    other_org = create_school(school_client, foreign, "Other trial roles")["id"]
    add_membership(school_client, owner, org_id, coach.id, "coach")
    add_membership(school_client, owner, org_id, scorer.id, "scorer")
    add_membership(school_client, owner, org_id, viewer.id, "viewer")
    clock = {"now": dt.datetime(2026, 3, 8, 7, 1, tzinfo=dt.UTC)}
    monkeypatch.setattr(trial_service, "_now", lambda: clock["now"])

    async def prepare():
        team = None
        for day in range(1, 5):
            team, _ = await _make_game(school_client, org_id, owner.id, dt.date(2026, 3, day), team)
        assert team is not None
        async with school_client.session_maker() as db:
            user = await db.get(models.User, operator.id)
            assert user is not None
            user.is_superuser = True
            await db.commit()
        return team

    team = asyncio.run(prepare())
    base = f"/api/organizations/{org_id}/team-performance/teams/{team.id}/trial"
    command = {"venue_timezone": "America/New_York", "reason": "Five prior matches"}
    assert school_client.get(base, headers=owner.headers).status_code == 403
    assert (
        school_client.put(
            f"/api/organizations/{org_id}/team-performance/trial-availability",
            headers=owner.headers,
            json={"enabled": True, "reason": "Cannot self-enable"},
        ).status_code
        == 403
    )
    assert (
        school_client.put(
            f"/api/organizations/{org_id}/team-performance/trial-availability",
            headers=operator.headers,
            json={"enabled": True, "reason": "Approved availability"},
        ).status_code
        == 200
    )
    assert (
        school_client.post(f"{base}/activate", headers=owner.headers, json=command).status_code
        == 409
    )
    assert (
        school_client.post(f"{base}/activate", headers=coach.headers, json=command).status_code
        == 403
    )
    assert school_client.get(base, headers=scorer.headers).status_code == 403
    assert school_client.get(base, headers=viewer.headers).status_code == 403
    assert school_client.get(base, headers=foreign.headers).status_code == 404
    foreign_base = f"/api/organizations/{other_org}/team-performance/teams/{team.id}/trial"
    assert school_client.get(foreign_base, headers=foreign.headers).status_code == 404

    asyncio.run(_make_game(school_client, org_id, owner.id, dt.date(2026, 3, 5), team))
    assert (
        school_client.post(
            f"{base}/activate",
            headers=owner.headers,
            json={"venue_timezone": "Invalid/Timezone", "reason": "Bad"},
        ).status_code
        == 409
    )
    response = school_client.post(f"{base}/activate", headers=owner.headers, json=command)
    assert response.status_code == 200, response.text
    assert response.json()["state"] == "active"
    assert response.json()["games_remaining"] == 3

    async def inspect():
        async with school_client.session_maker() as db:
            trial = await db.scalar(
                select(models.TeamPerformanceTrial).where(
                    models.TeamPerformanceTrial.organization_id == org_id,
                    models.TeamPerformanceTrial.team_id == team.id,
                )
            )
            assert trial is not None
            assert trial.activation_local_date == dt.date(2026, 3, 8)
            assert trial.venue_timezone == "America/New_York"
            assert trial_service._utc(trial.expires_at) == clock["now"] + dt.timedelta(days=90)

    asyncio.run(inspect())
    assert school_client.get(base, headers=coach.headers).status_code == 200

    async def pause_scope():
        async with school_client.session_maker() as db:
            saved_team = await db.get(models.Team, team.id)
            assert saved_team is not None
            saved_team.status = "archived"
            await db.commit()

    asyncio.run(pause_scope())
    assert school_client.get(base, headers=owner.headers).status_code == 403

    async def resume_team_and_pause_org():
        async with school_client.session_maker() as db:
            saved_team = await db.get(models.Team, team.id)
            saved_org = await db.get(models.Organization, org_id)
            assert saved_team is not None and saved_org is not None
            saved_team.status = "active"
            saved_org.status = "suspended"
            await db.commit()

    asyncio.run(resume_team_and_pause_org())
    assert school_client.get(base, headers=owner.headers).status_code == 404

    async def resume_org():
        async with school_client.session_maker() as db:
            saved_org = await db.get(models.Organization, org_id)
            assert saved_org is not None
            saved_org.status = "active"
            await db.commit()

    asyncio.run(resume_org())

    async def disable_coach():
        async with school_client.session_maker() as db:
            membership = await db.scalar(
                select(models.OrganizationMembership).where(
                    models.OrganizationMembership.organization_id == org_id,
                    models.OrganizationMembership.user_id == coach.id,
                )
            )
            assert membership is not None
            membership.status = "disabled"
            await db.commit()

    asyncio.run(disable_coach())
    assert school_client.get(base, headers=coach.headers).status_code == 404
    assert (
        school_client.put(
            f"/api/organizations/{org_id}/team-performance/trial-availability",
            headers=operator.headers,
            json={"enabled": False, "reason": "Revoked"},
        ).status_code
        == 200
    )
    assert school_client.get(base, headers=owner.headers).status_code == 403


def test_invalidated_final_game_requires_operator_reversal_before_replacement(
    school_client,
    monkeypatch,
) -> None:
    owner = register_user(school_client, "trial-correction-owner@example.com")
    operator = register_user(school_client, "trial-correction-operator@example.com")
    org_id = create_club(school_client, owner, "Correction trial")["id"]
    clock = {"now": dt.datetime(2026, 11, 28, 12, tzinfo=dt.UTC)}
    monkeypatch.setattr(trial_service, "_now", lambda: clock["now"])

    async def scenario():
        team = None
        for day in range(18, 23):
            team, _ = await _make_game(
                school_client, org_id, owner.id, dt.date(2026, 11, day), team
            )
        assert team is not None
        async with school_client.session_maker() as db:
            user = await db.get(models.User, operator.id)
            assert user is not None
            user.is_superuser = True
            await db.commit()
            await trial_service.set_trial_availability(
                db,
                organization_id=org_id,
                operator_user_id=operator.id,
                enabled=True,
                reason="Correction test availability",
            )
            await db.commit()
            trial = await trial_service.activate_trial(
                db,
                organization_id=org_id,
                team_id=team.id,
                actor_user_id=owner.id,
                venue_timezone="Etc/UTC",
                reason="Ready",
            )
            await db.commit()
            trial_id = trial.id
        final_game = None
        for day in (28, 29, 30):
            clock["now"] = dt.datetime(2026, 11, day, 17, tzinfo=dt.UTC)
            _, game = await _make_game(
                school_client, org_id, owner.id, dt.date(2026, 11, day), team
            )
            final_game = game
            async with school_client.session_maker() as db:
                event = await trial_service.record_completion_event(db, game_id=game.id)
                assert event is not None
                await db.commit()
                await trial_service.process_completion_event(db, completion_event_id=event.id)
                await db.commit()
        assert final_game is not None
        async with school_client.session_maker() as db:
            assert (
                await trial_service.retained_trial_report(
                    db,
                    organization_id=org_id,
                    team_id=team.id,
                    actor_user_id=owner.id,
                )
            )["sample_size"] == 5
            saved = await db.get(models.Game, final_game.id)
            assert saved is not None
            saved.original_overs_limit = 50
            saved.original_format_trust_state = "staff_corrected"
            saved.original_format_source = "staff_correction"
            saved.team_performance_metadata_revision += 1
            await db.commit()
            status = await trial_service.trial_status(
                db,
                organization_id=org_id,
                team_id=team.id,
                actor_user_id=owner.id,
            )
            assert status["state"] == "review_required"
            with pytest.raises(trial_service.TrialTransitionError):
                await trial_service.retained_trial_report(
                    db,
                    organization_id=org_id,
                    team_id=team.id,
                    actor_user_id=owner.id,
                )
            with pytest.raises(TeamPerformanceAccessError):
                await trial_service.resolve_trial_review(
                    db,
                    organization_id=org_id,
                    team_id=team.id,
                    operator_user_id=owner.id,
                    reason="Not platform operator",
                    reverse_game_id=final_game.id,
                )
            await db.rollback()
            resolved = await trial_service.resolve_trial_review(
                db,
                organization_id=org_id,
                team_id=team.id,
                operator_user_id=operator.id,
                reason="Verified format correction",
                reverse_game_id=final_game.id,
            )
            await db.commit()
            assert resolved.state == "active"
            assert (
                await trial_service.trial_status(
                    db,
                    organization_id=org_id,
                    team_id=team.id,
                    actor_user_id=owner.id,
                )
            )["games_remaining"] == 1
        clock["now"] = dt.datetime(2026, 12, 1, 17, tzinfo=dt.UTC)
        _, replacement = await _make_game(
            school_client, org_id, owner.id, dt.date(2026, 12, 1), team
        )
        async with school_client.session_maker() as db:
            event = await trial_service.record_completion_event(db, game_id=replacement.id)
            assert event is not None
            await db.commit()
            await trial_service.process_completion_event(db, completion_event_id=event.id)
            await db.commit()
            final = await trial_service.trial_status(
                db,
                organization_id=org_id,
                team_id=team.id,
                actor_user_id=owner.id,
            )
            assert final["state"] == "exhausted"
            assert final["games_used"] == 3
            snapshot = await db.scalar(
                select(models.TeamPerformanceTrialSnapshot)
                .where(
                    models.TeamPerformanceTrialSnapshot.trial_id == trial_id,
                    models.TeamPerformanceTrialSnapshot.ordinal == 3,
                )
                .order_by(models.TeamPerformanceTrialSnapshot.created_at.desc())
            )
            assert snapshot is not None
            assert snapshot.sources[-1]["game_id"] == replacement.id
            assert final_game.id not in {source["game_id"] for source in snapshot.sources}
            events = (
                await db.scalars(
                    select(models.TeamPerformanceTrialEvent).where(
                        models.TeamPerformanceTrialEvent.trial_id == trial_id,
                        models.TeamPerformanceTrialEvent.kind == "reversed",
                    )
                )
            ).all()
            assert len(events) == 1

    asyncio.run(scenario())


def test_trial_processor_failure_does_not_break_free_completion_and_is_retriable(
    school_client,
    monkeypatch,
) -> None:
    owner = register_user(school_client, "trial-free-owner@example.com")
    operator = register_user(school_client, "trial-free-operator@example.com")
    org_id = create_school(school_client, owner, "Free completion isolation")["id"]
    clock = {"now": dt.datetime(2026, 11, 28, 12, tzinfo=dt.UTC)}
    monkeypatch.setattr(trial_service, "_now", lambda: clock["now"])

    async def prepare():
        team = None
        for day in range(18, 23):
            team, _ = await _make_game(
                school_client, org_id, owner.id, dt.date(2026, 11, day), team
            )
        assert team is not None
        async with school_client.session_maker() as db:
            user = await db.get(models.User, operator.id)
            assert user is not None
            user.is_superuser = True
            await db.commit()
            await trial_service.set_trial_availability(
                db,
                organization_id=org_id,
                operator_user_id=operator.id,
                enabled=True,
                reason="Free isolation test",
            )
            await db.commit()
            await trial_service.activate_trial(
                db,
                organization_id=org_id,
                team_id=team.id,
                actor_user_id=owner.id,
                venue_timezone="Etc/UTC",
                reason="Ready",
            )
            await db.commit()
        clock["now"] = dt.datetime(2026, 11, 28, 17, tzinfo=dt.UTC)
        _, game = await _make_game(school_client, org_id, owner.id, dt.date(2026, 11, 28), team)
        async with school_client.session_maker() as db:
            persisted = await db.get(models.Game, game.id)
            assert persisted is not None
            persisted.status = models.GameStatus.started
            await db.commit()
        return team, game

    team, game = asyncio.run(prepare())
    original_processor = trial_service.process_completion_event

    async def fail_processor(*_args, **_kwargs):
        raise RuntimeError("Injected trial-only processor failure")

    monkeypatch.setattr(trial_service, "process_completion_event", fail_processor)

    async def complete_free_game():
        async with school_client.session_maker() as db:
            persisted = await db.get(models.Game, game.id)
            assert persisted is not None
            persisted.status = models.GameStatus.completed
            await db.commit()
            await trial_service.handle_completed_game_after_free_commit(db, game.id)
            assert (await db.get(models.Game, game.id)).status == models.GameStatus.completed

    asyncio.run(complete_free_game())
    monkeypatch.setattr(trial_service, "process_completion_event", original_processor)
    status_path = f"/api/organizations/{org_id}/team-performance/teams/{team.id}/trial"
    assert school_client.get(status_path, headers=owner.headers).json()["games_used"] == 0
    verification = school_client.post(
        f"{status_path}/verify?game_id={game.id}",
        headers=owner.headers,
    )
    assert verification.status_code == 200, verification.text
    assert verification.json() == {"verified": True}
    assert school_client.get(status_path, headers=owner.headers).json()["games_used"] == 1
    review = school_client.post(
        f"{status_path}/review?game_id={game.id}",
        json={"reason": "Request evidence review"},
        headers=owner.headers,
    )
    assert review.status_code == 200, review.text
    assert (
        school_client.get(status_path, headers=owner.headers).json()["state"] == "review_required"
    )
    resolved = school_client.post(
        f"{status_path}/resolve",
        json={"reason": "Evidence verified"},
        headers=operator.headers,
    )
    assert resolved.status_code == 200, resolved.text


def test_expiry_continues_during_review_and_fault_extension_is_operator_only(
    school_client,
    monkeypatch,
) -> None:
    owner = register_user(school_client, "trial-expiry-owner@example.com")
    operator = register_user(school_client, "trial-expiry-operator@example.com")
    org_id = create_school(school_client, owner, "Expiry review")["id"]
    started = dt.datetime(2026, 11, 28, 12, tzinfo=dt.UTC)
    clock = {"now": started}
    monkeypatch.setattr(trial_service, "_now", lambda: clock["now"])

    async def scenario():
        team = None
        for day in range(18, 23):
            team, _ = await _make_game(
                school_client, org_id, owner.id, dt.date(2026, 11, day), team
            )
        assert team is not None
        async with school_client.session_maker() as db:
            user = await db.get(models.User, operator.id)
            assert user is not None
            user.is_superuser = True
            await db.commit()
            await trial_service.set_trial_availability(
                db,
                organization_id=org_id,
                operator_user_id=operator.id,
                enabled=True,
                reason="Expiry test",
            )
            await db.commit()
            trial = await trial_service.activate_trial(
                db,
                organization_id=org_id,
                team_id=team.id,
                actor_user_id=owner.id,
                venue_timezone="Etc/UTC",
                reason="Ready",
            )
            trial.state = "review_required"
            await db.commit()
            clock["now"] = started + dt.timedelta(days=91)
            assert (
                await trial_service.trial_status(
                    db,
                    organization_id=org_id,
                    team_id=team.id,
                    actor_user_id=owner.id,
                )
            )["state"] == "expired"
            with pytest.raises(TeamPerformanceAccessError):
                await trial_service.extend_trial_for_system_fault(
                    db,
                    organization_id=org_id,
                    team_id=team.id,
                    operator_user_id=owner.id,
                    reason="Not platform authorized",
                    new_expires_at=started + dt.timedelta(days=95),
                )
            await db.rollback()
            await trial_service.extend_trial_for_system_fault(
                db,
                organization_id=org_id,
                team_id=team.id,
                operator_user_id=operator.id,
                reason="Verified processor outage",
                new_expires_at=started + dt.timedelta(days=95),
            )
            await db.commit()
            assert (
                await trial_service.trial_status(
                    db,
                    organization_id=org_id,
                    team_id=team.id,
                    actor_user_id=owner.id,
                )
            )["state"] == "review_required"
            events = (
                await db.scalars(
                    select(models.TeamPerformanceTrialEvent).where(
                        models.TeamPerformanceTrialEvent.trial_id == trial.id,
                        models.TeamPerformanceTrialEvent.kind == "extended",
                    )
                )
            ).all()
            assert len(events) == 1
            assert events[0].reason == "Verified processor outage"

    asyncio.run(scenario())


def test_ineligible_games_are_not_charged_and_original_25_shortened_game_qualifies(
    school_client,
    monkeypatch,
) -> None:
    owner = register_user(school_client, "trial-eligibility-owner@example.com")
    operator = register_user(school_client, "trial-eligibility-operator@example.com")
    org_id = create_club(school_client, owner, "Eligibility trial")["id"]
    clock = {"now": dt.datetime(2026, 11, 28, 12, tzinfo=dt.UTC)}
    monkeypatch.setattr(trial_service, "_now", lambda: clock["now"])

    async def scenario():
        team = None
        for day in range(18, 23):
            team, _ = await _make_game(
                school_client, org_id, owner.id, dt.date(2026, 11, day), team
            )
        assert team is not None
        async with school_client.session_maker() as db:
            user = await db.get(models.User, operator.id)
            assert user is not None
            user.is_superuser = True
            await db.commit()
            await trial_service.set_trial_availability(
                db,
                organization_id=org_id,
                operator_user_id=operator.id,
                enabled=True,
                reason="Qualification test",
            )
            await db.commit()
            await trial_service.activate_trial(
                db,
                organization_id=org_id,
                team_id=team.id,
                actor_user_id=owner.id,
                venue_timezone="Etc/UTC",
                reason="Ready",
            )
            await db.commit()
        for day, purpose, original, effective in (
            (28, "practice", 25, 25),
            (29, "official", 50, 25),
            (30, "official", 25, 18),
        ):
            clock["now"] = dt.datetime(2026, 11, day, 17, tzinfo=dt.UTC)
            _, game = await _make_game(
                school_client, org_id, owner.id, dt.date(2026, 11, day), team
            )
            async with school_client.session_maker() as db:
                saved = await db.get(models.Game, game.id)
                assert saved is not None
                saved.match_purpose = purpose
                saved.original_overs_limit = original
                saved.overs_limit = effective
                saved.dls_enabled = effective == 18
                await db.commit()
                event = await trial_service.record_completion_event(db, game_id=game.id)
                assert event is not None
                await db.commit()
                await trial_service.process_completion_event(db, completion_event_id=event.id)
                await db.commit()
                status = await trial_service.trial_status(
                    db,
                    organization_id=org_id,
                    team_id=team.id,
                    actor_user_id=owner.id,
                )
                assert status["games_used"] == (1 if day == 30 else 0)
                assert status["state"] == "active"
        # A later metadata confirmation cannot make an earlier untrusted event chargeable.
        clock["now"] = dt.datetime(2026, 12, 1, 17, tzinfo=dt.UTC)
        _, late = await _make_game(school_client, org_id, owner.id, dt.date(2026, 12, 1), team)
        async with school_client.session_maker() as db:
            saved = await db.get(models.Game, late.id)
            assert saved is not None
            saved.actual_played_date = None
            saved.played_date_trust_state = "unknown"
            saved.played_date_source = None
            await db.commit()
            event = await trial_service.record_completion_event(db, game_id=late.id)
            assert event is not None
            await db.commit()
            saved.actual_played_date = dt.date(2026, 12, 1)
            saved.played_date_trust_state = "confirmed"
            saved.played_date_source = "staff_confirmed"
            saved.team_performance_metadata_revision += 1
            await db.commit()
            await trial_service.process_completion_event(db, completion_event_id=event.id)
            await db.commit()
            status = await trial_service.trial_status(
                db,
                organization_id=org_id,
                team_id=team.id,
                actor_user_id=owner.id,
            )
            assert status["games_used"] == 1
            assert status["state"] == "review_required"

    asyncio.run(scenario())


def test_trusted_same_day_completion_order_preserves_rolling_reports(
    school_client,
    monkeypatch,
) -> None:
    owner = register_user(school_client, "trial-same-day-owner@example.com")
    operator = register_user(school_client, "trial-same-day-operator@example.com")
    org_id = create_school(school_client, owner, "Same-day trial")["id"]
    clock = {"now": dt.datetime(2026, 11, 28, 12, tzinfo=dt.UTC)}
    monkeypatch.setattr(trial_service, "_now", lambda: clock["now"])

    async def scenario():
        team = None
        for day in range(18, 23):
            team, _ = await _make_game(
                school_client, org_id, owner.id, dt.date(2026, 11, day), team
            )
        assert team is not None
        async with school_client.session_maker() as db:
            user = await db.get(models.User, operator.id)
            assert user is not None
            user.is_superuser = True
            await db.commit()
            await trial_service.set_trial_availability(
                db,
                organization_id=org_id,
                operator_user_id=operator.id,
                enabled=True,
                reason="Same-day test",
            )
            await db.commit()
            trial = await trial_service.activate_trial(
                db,
                organization_id=org_id,
                team_id=team.id,
                actor_user_id=owner.id,
                venue_timezone="Etc/UTC",
                reason="Ready",
            )
            await db.commit()
            trial_id = trial.id
        ids = []
        for hour in (17, 18):
            clock["now"] = dt.datetime(2026, 11, 28, hour, tzinfo=dt.UTC)
            _, game = await _make_game(school_client, org_id, owner.id, dt.date(2026, 11, 28), team)
            ids.append(game.id)
            async with school_client.session_maker() as db:
                event = await trial_service.record_completion_event(db, game_id=game.id)
                assert event is not None
                await db.commit()
                await trial_service.process_completion_event(db, completion_event_id=event.id)
                await db.commit()
                status = await trial_service.trial_status(
                    db,
                    organization_id=org_id,
                    team_id=team.id,
                    actor_user_id=owner.id,
                )
                assert status["games_used"] == len(ids)
                assert status["state"] == "active"
        async with school_client.session_maker() as db:
            second = await db.scalar(
                select(models.TeamPerformanceTrialSnapshot).where(
                    models.TeamPerformanceTrialSnapshot.trial_id == trial_id,
                    models.TeamPerformanceTrialSnapshot.ordinal == 2,
                )
            )
            assert second is not None
            assert [source["game_id"] for source in second.sources[-2:]] == ids

    asyncio.run(scenario())
