"""Behavior tests for the dedicated private practice workflow."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError
from sqlalchemy import select

from backend.api.schemas.school_competitions import SchoolPublicationUpdate
from backend.api.schemas.school_matches import PracticeDelivery
from backend.routes.school_matches import _practice_workflow_state
from backend.services import school_competition_service
from backend.services.practice_match_persistence_service import start_private_practice_match
from backend.services.practice_match_workflow_service import (
    _persist,
    read_practice_workflow,
    score_practice_delivery,
    start_practice_innings,
    undo_last_practice_delivery,
)
from backend.sql_app.database import SessionLocal
from backend.sql_app.models import (
    Game,
    OrganizationMembership,
    PlayerProfile,
    SchoolPlayerMembership,
    User,
)
from backend.tests.test_practice_start_context import _draft


def _ids(game: Game, side: str) -> list[str]:
    team = game.team_a if side == "team_a" else game.team_b
    return [str(player["id"]) for player in team["players"]]


@pytest.mark.parametrize("invalid_zone", [0, 9, -1, "6", 6.0, True, False])
def test_private_field_zone_contract_requires_a_strict_integer_in_range(invalid_zone: object) -> None:
    with pytest.raises(ValidationError):
        PracticeDelivery(
            expected_revision=1,
            striker_id="striker",
            non_striker_id="non-striker",
            bowler_id="bowler",
            runs_scored=0,
            field_zone=invalid_zone,
        )


async def test_private_workflow_response_resolves_frozen_profile_labels_after_reload() -> None:
    organization_id, owner_id, game_id = await _draft(same_display_name=True)
    async with SessionLocal() as session:
        game = await start_private_practice_match(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            first_batting_side="team_a",
        )
        frozen_ids = _ids(game, "team_a") + _ids(game, "team_b")
        profiles = {
            profile.player_id: profile.player_name
            for profile in (
                await session.execute(
                    select(PlayerProfile).where(PlayerProfile.player_id.in_(frozen_ids))
                )
            ).scalars()
        }
        assert set(profiles) == set(frozen_ids)

    async with SessionLocal() as session:
        game, snapshot = await read_practice_workflow(
            session, organization_id=organization_id, actor_user_id=owner_id, game_id=game_id
        )
        response = await _practice_workflow_state(session, game, organization_id, snapshot)
        assert [player["label"] for player in response.frozen_sides["team_a"]] == [
            profiles[player_id] for player_id in _ids(game, "team_a")
        ]
        assert [player["label"] for player in response.frozen_sides["team_b"]] == [
            profiles[player_id] for player_id in _ids(game, "team_b")
        ]

        # A roster may later deactivate or delete a profile.  Frozen IDs must
        # remain usable and the private response must not manufacture a name.
        missing_id = _ids(game, "team_a")[0]
        missing = await session.get(PlayerProfile, missing_id)
        assert missing is not None
        await session.delete(missing)
        await session.commit()
        reloaded, reloaded_snapshot = await read_practice_workflow(
            session, organization_id=organization_id, actor_user_id=owner_id, game_id=game_id
        )
        response = await _practice_workflow_state(
            session, reloaded, organization_id, reloaded_snapshot
        )
        assert response.frozen_sides["team_a"][0] == {
            "id": missing_id,
            "label": "Unavailable participant",
        }


@pytest.mark.parametrize("organization_type", ["school", "club"])
async def test_private_field_zone_persists_through_reload_and_undo_without_official_projection(
    organization_type: str,
) -> None:
    organization_id, owner_id, game_id = await _draft(organization_type=organization_type)
    field_zone = 6
    async with SessionLocal() as session:
        game = await start_private_practice_match(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            first_batting_side="team_a",
        )
        batting, bowling = _ids(game, "team_a"), _ids(game, "team_b")
        game, _ = await start_practice_innings(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            expected_revision=game.practice_workflow_revision,
            striker_id=batting[0],
            non_striker_id=batting[1],
            opening_bowler_id=bowling[0],
        )
        game, snapshot = await score_practice_delivery(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            expected_revision=game.practice_workflow_revision,
            striker_id=batting[0],
            non_striker_id=batting[1],
            bowler_id=bowling[0],
            runs_scored=4,
            extra=None,
            is_wicket=False,
            dismissal_type=None,
            dismissed_player_id=None,
            field_zone=field_zone,
        )
        assert game.deliveries[-1]["field_zone"] == field_zone
        assert snapshot["last_delivery"]["field_zone"] == field_zone
        reloaded, reloaded_snapshot = await read_practice_workflow(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
        )
        assert reloaded.deliveries[-1]["field_zone"] == field_zone
        assert reloaded_snapshot["last_delivery"]["field_zone"] == field_zone
        with pytest.raises(Exception) as official_error:
            await school_competition_service.public_scorecard(session, game_id=game_id)
        assert getattr(official_error.value, "status_code", None) == 404
        game, _ = await undo_last_practice_delivery(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            expected_revision=game.practice_workflow_revision,
        )
        assert game.deliveries == []


@pytest.mark.parametrize(
    ("organization_type", "first_side"),
    [("school", "team_a"), ("club", "team_b")],
)
async def test_private_workflow_scores_two_short_innings_and_undoes(
    organization_type: str, first_side: str
) -> None:
    organization_id, owner_id, game_id = await _draft(
        same_display_name=True, organization_type=organization_type
    )
    async with SessionLocal() as session:
        game = await start_private_practice_match(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            first_batting_side=first_side,
        )
        game.overs_limit = 1
        await session.commit()
        batting = _ids(game, first_side)
        bowling = _ids(game, "team_b" if first_side == "team_a" else "team_a")
        game, state = await start_practice_innings(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            expected_revision=game.practice_workflow_revision,
            striker_id=batting[0],
            non_striker_id=batting[1],
            opening_bowler_id=bowling[0],
        )
        assert state["wicket_limit"] == 1
        game, state = await score_practice_delivery(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            expected_revision=game.practice_workflow_revision,
            striker_id=batting[0],
            non_striker_id=batting[1],
            bowler_id=bowling[0],
            runs_scored=0,
            extra=None,
            is_wicket=True,
            dismissal_type="bowled",
            dismissed_player_id=batting[0],
        )
        assert game.status.value == "innings_break"

        next_batting = bowling
        next_bowling = batting
        game, _ = await start_practice_innings(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            expected_revision=game.practice_workflow_revision,
            striker_id=next_batting[0],
            non_striker_id=next_batting[1],
            opening_bowler_id=next_bowling[0],
        )
        game, _ = await score_practice_delivery(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            expected_revision=game.practice_workflow_revision,
            striker_id=next_batting[0],
            non_striker_id=next_batting[1],
            bowler_id=next_bowling[0],
            runs_scored=0,
            extra=None,
            is_wicket=True,
            dismissal_type="bowled",
            dismissed_player_id=next_batting[0],
        )
        assert game.status.value in {"innings_break", "completed"}
        game, state = await undo_last_practice_delivery(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            expected_revision=game.practice_workflow_revision,
        )
        assert game.status.value == "in_progress"
        assert state["total_wickets"] == 0
        assert len(game.practice_innings_history or []) == 1

    async with SessionLocal() as session:
        game, state = await read_practice_workflow(
            session, organization_id=organization_id, actor_user_id=owner_id, game_id=game_id
        )
        assert game.practice_workflow_revision == state["practice_workflow_revision"]
        assert game.practice_start_context == {"version": 1, "first_batting_side": first_side}


async def test_private_workflow_rejects_stale_revision_and_foreign_runtime_before_mutation() -> (
    None
):
    organization_id, owner_id, game_id = await _draft()
    async with SessionLocal() as session:
        game = await start_private_practice_match(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            first_batting_side="team_a",
        )
        batting, bowling = _ids(game, "team_a"), _ids(game, "team_b")
        game, _ = await start_practice_innings(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            expected_revision=game.practice_workflow_revision,
            striker_id=batting[0],
            non_striker_id=batting[1],
            opening_bowler_id=bowling[0],
        )
        before = (list(game.deliveries), game.total_runs, game.total_wickets)
        with pytest.raises(Exception) as exc_info:
            await score_practice_delivery(
                session,
                organization_id=organization_id,
                actor_user_id=owner_id,
                game_id=game_id,
                expected_revision=game.practice_workflow_revision,
                striker_id=batting[0],
                non_striker_id=batting[1],
                bowler_id=batting[0],
                runs_scored=1,
                extra=None,
                is_wicket=False,
                dismissal_type=None,
                dismissed_player_id=None,
            )
        assert getattr(exc_info.value, "status_code", None) == 409
        assert (game.deliveries, game.total_runs, game.total_wickets) == before
        with pytest.raises(Exception) as exc_info:
            await undo_last_practice_delivery(
                session,
                organization_id=organization_id,
                actor_user_id=owner_id,
                game_id=game_id,
                expected_revision=game.practice_workflow_revision - 1,
            )
        assert getattr(exc_info.value, "status_code", None) == 409


@pytest.mark.parametrize("organization_type", ["school", "club"])
async def test_published_practice_preserves_snapshot_labels_and_private_scoring(
    organization_type: str,
) -> None:
    organization_id, owner_id, game_id = await _draft(organization_type=organization_type)
    async with SessionLocal() as session:
        game = await start_private_practice_match(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            first_batting_side="team_a",
        )
        batting, bowling = _ids(game, "team_a"), _ids(game, "team_b")
        snapshot_names = {
            player["id"]: player["name"]
            for team in (game.team_a, game.team_b)
            for player in team["players"]
        }
        membership_ids = {
            player["id"]: player["school_player_membership_id"]
            for team in (game.team_a, game.team_b)
            for player in team["players"]
        }
        game, _ = await start_practice_innings(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            expected_revision=game.practice_workflow_revision,
            striker_id=batting[0],
            non_striker_id=batting[1],
            opening_bowler_id=bowling[0],
        )
        game, publication_state = await school_competition_service.publication(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            payload=SchoolPublicationUpdate(publication_state="published_live"),
        )
        assert publication_state == "published_live"

        projection = await school_competition_service.public_practice_scorecard(
            session, game_id=game_id
        )
        assert projection.game_id == game_id
        assert projection.organization_type == organization_type
        assert projection.publication_state == "published_live"
        assert [player.name for player in projection.team_a.players] == [
            snapshot_names[player_id] for player_id in batting
        ]
        assert projection.batting_scorecard
        assert projection.bowling_scorecard
        public_payload = json.dumps(projection.model_dump(mode="json"))
        for player_id, membership_id in membership_ids.items():
            assert player_id not in public_payload
            assert membership_id not in public_payload

        # A renamed live profile must not rewrite the published roster-era
        # label. The scorer remains available while publication is live.
        profile = await session.get(PlayerProfile, batting[0])
        assert profile is not None
        profile.player_name = "Renamed after practice setup"
        await session.commit()
        projection = await school_competition_service.public_practice_scorecard(
            session, game_id=game_id
        )
        assert projection.team_a.players[0].name == snapshot_names[batting[0]]
        private_field_zone = 3
        game, _ = await score_practice_delivery(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            expected_revision=game.practice_workflow_revision,
            striker_id=batting[0],
            non_striker_id=batting[1],
            bowler_id=bowling[0],
            runs_scored=1,
            extra=None,
            is_wicket=False,
            dismissal_type=None,
            dismissed_player_id=None,
            field_zone=private_field_zone,
        )
        public_projection = await school_competition_service.public_practice_scorecard(
            session, game_id=game_id
        )
        assert "field_zone" not in json.dumps(public_projection.model_dump(mode="json"))
        game, _ = await undo_last_practice_delivery(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            expected_revision=game.practice_workflow_revision,
        )
        reloaded, _ = await read_practice_workflow(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
        )
        assert reloaded.id == game.id

        # Inactive or deleted profiles become a neutral label. Current names
        # are never a public fallback for the frozen practice roster.
        inactive_membership = await session.get(SchoolPlayerMembership, membership_ids[batting[0]])
        assert inactive_membership is not None
        inactive_membership.status = "inactive"
        deleted_profile = await session.get(PlayerProfile, batting[1])
        assert deleted_profile is not None
        await session.delete(deleted_profile)
        await session.commit()
        projection = await school_competition_service.public_practice_scorecard(
            session, game_id=game_id
        )
        assert [player.name for player in projection.team_a.players[:2]] == [
            "Unavailable participant",
            "Unavailable participant",
        ]
        assert {row.player_name for row in projection.batting_scorecard} <= {
            "Unavailable participant",
            snapshot_names[batting[0]],
            snapshot_names[batting[1]],
        }

        # Practice must never leak through the official scorecard endpoint.
        with pytest.raises(Exception) as official_error:
            await school_competition_service.public_scorecard(session, game_id=game_id)
        assert getattr(official_error.value, "status_code", None) == 404

        _, private_state = await school_competition_service.publication(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            payload=SchoolPublicationUpdate(publication_state="private"),
        )
        assert private_state == "private"
        with pytest.raises(Exception) as revoked_error:
            await school_competition_service.public_practice_scorecard(session, game_id=game_id)
        assert getattr(revoked_error.value, "status_code", None) == 404


async def test_private_workflow_denies_viewer_and_disabled_membership() -> None:
    organization_id, owner_id, game_id = await _draft()
    async with SessionLocal() as session:
        await start_private_practice_match(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            first_batting_side="team_a",
        )
        await school_competition_service.publication(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            payload=SchoolPublicationUpdate(publication_state="published_live"),
        )
        viewer = User(email="practice-workflow-viewer@example.test", hashed_password="test-only")
        session.add(viewer)
        await session.flush()
        membership = OrganizationMembership(
            organization_id=organization_id,
            user_id=viewer.id,
            role="viewer",
            status="active",
            created_by_user_id=owner_id,
        )
        session.add(membership)
        await session.commit()
        with pytest.raises(Exception) as exc_info:
            await read_practice_workflow(
                session,
                organization_id=organization_id,
                actor_user_id=viewer.id,
                game_id=game_id,
            )
        assert getattr(exc_info.value, "status_code", None) == 403
        membership.status = "disabled"
        await session.commit()
        with pytest.raises(Exception) as exc_info:
            await read_practice_workflow(
                session,
                organization_id=organization_id,
                actor_user_id=viewer.id,
                game_id=game_id,
            )
        assert getattr(exc_info.value, "status_code", None) == 404


async def test_private_workflow_rejects_foreign_organization_get_and_mutation() -> None:
    organization_id, owner_id, game_id = await _draft()
    foreign_organization_id, foreign_owner_id, _ = await _draft()
    async with SessionLocal() as session:
        game = await start_private_practice_match(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            first_batting_side="team_a",
        )
        await school_competition_service.publication(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            payload=SchoolPublicationUpdate(publication_state="published_live"),
        )
        batting, bowling = _ids(game, "team_a"), _ids(game, "team_b")
        game, _ = await start_practice_innings(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            expected_revision=game.practice_workflow_revision,
            striker_id=batting[0],
            non_striker_id=batting[1],
            opening_bowler_id=bowling[0],
        )
        before = (game.practice_workflow_revision, list(game.deliveries), game.total_runs)
        with pytest.raises(Exception) as exc_info:
            await read_practice_workflow(
                session,
                organization_id=foreign_organization_id,
                actor_user_id=foreign_owner_id,
                game_id=game_id,
            )
        assert getattr(exc_info.value, "status_code", None) == 404
        with pytest.raises(Exception) as exc_info:
            await score_practice_delivery(
                session,
                organization_id=foreign_organization_id,
                actor_user_id=foreign_owner_id,
                game_id=game_id,
                expected_revision=game.practice_workflow_revision,
                striker_id=batting[0],
                non_striker_id=batting[1],
                bowler_id=bowling[0],
                runs_scored=1,
                extra=None,
                is_wicket=False,
                dismissal_type=None,
                dismissed_player_id=None,
            )
        assert getattr(exc_info.value, "status_code", None) == 404
        assert (game.practice_workflow_revision, game.deliveries, game.total_runs) == before


async def test_private_workflow_finishes_a_winning_chase_before_all_out_or_overs() -> None:
    organization_id, owner_id, game_id = await _draft(same_display_name=True)
    async with SessionLocal() as session:
        game = await start_private_practice_match(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            first_batting_side="team_a",
        )
        game.overs_limit = 2
        await session.commit()
        first_batting, first_bowling = _ids(game, "team_a"), _ids(game, "team_b")
        game, _ = await start_practice_innings(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            expected_revision=game.practice_workflow_revision,
            striker_id=first_batting[0],
            non_striker_id=first_batting[1],
            opening_bowler_id=first_bowling[0],
        )
        game, _ = await score_practice_delivery(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            expected_revision=game.practice_workflow_revision,
            striker_id=first_batting[0],
            non_striker_id=first_batting[1],
            bowler_id=first_bowling[0],
            runs_scored=0,
            extra=None,
            is_wicket=True,
            dismissal_type="bowled",
            dismissed_player_id=first_batting[0],
        )
        assert game.status.value == "innings_break"
        game, state = await start_practice_innings(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            expected_revision=game.practice_workflow_revision,
            striker_id=first_bowling[0],
            non_striker_id=first_bowling[1],
            opening_bowler_id=first_batting[0],
        )
        assert state["target"] == 1
        game, _ = await score_practice_delivery(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            expected_revision=game.practice_workflow_revision,
            striker_id=first_bowling[0],
            non_striker_id=first_bowling[1],
            bowler_id=first_batting[0],
            runs_scored=1,
            extra=None,
            is_wicket=False,
            dismissal_type=None,
            dismissed_player_id=None,
        )
        assert game.status.value == "completed"
        assert game.total_wickets == 0
        assert game.overs_completed == 0 and game.balls_this_over == 1
        assert len([d for d in game.deliveries if d["inning"] == 2]) == 1


async def test_private_workflow_conditional_revision_blocks_a_second_session_stale_write() -> None:
    organization_id, owner_id, game_id = await _draft()
    async with SessionLocal() as session:
        game = await start_private_practice_match(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            first_batting_side="team_a",
        )
        batting, bowling = _ids(game, "team_a"), _ids(game, "team_b")
        game, _ = await start_practice_innings(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            expected_revision=game.practice_workflow_revision,
            striker_id=batting[0],
            non_striker_id=batting[1],
            opening_bowler_id=bowling[0],
        )
        revision = game.practice_workflow_revision

    async with SessionLocal() as stale_session:
        stale_game = await stale_session.get(Game, game_id)
        assert stale_game is not None

    async with SessionLocal() as winning_session:
        game, _ = await score_practice_delivery(
            winning_session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            expected_revision=revision,
            striker_id=batting[0],
            non_striker_id=batting[1],
            bowler_id=bowling[0],
            runs_scored=1,
            extra=None,
            is_wicket=False,
            dismissal_type=None,
            dismissed_player_id=None,
        )
        assert game.practice_workflow_revision == revision + 1

    async with SessionLocal() as stale_write_session:
        stale_game.total_runs = 99
        stale_write_session.add(stale_game)
        with pytest.raises(Exception) as exc_info:
            await _persist(stale_write_session, stale_game, expected_revision=revision)
        assert getattr(exc_info.value, "status_code", None) == 409
    async with SessionLocal() as session:
        reloaded = await session.get(Game, game_id)
        assert reloaded is not None
        assert reloaded.practice_workflow_revision == revision + 1
        assert len(reloaded.deliveries) == 1
        assert reloaded.total_runs == 1
