from __future__ import annotations

import asyncio
import importlib.util
import uuid
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import create_engine, inspect, text

from alembic.migration import MigrationContext
from alembic.operations import Operations
from backend.api.schemas.organizations import OrganizationCreate
from backend.api.schemas.school_matches import PracticeMatchStart
from backend.routes.school_matches import (
    start_private_practice_match as start_private_practice_route,
)
from backend.services import organization_service
from backend.services.practice_match_persistence_service import (
    PRACTICE_START_CONTEXT_VERSION,
    persist_practice_match_setup,
    start_private_practice_match,
    validate_practice_start_context,
)
from backend.services.practice_match_setup_service import (
    PracticeSideSelection,
    prepare_practice_match_setup,
)
from backend.sql_app.database import SessionLocal
from backend.sql_app.models import Game, User
from backend.tests.test_practice_match_persistence import _side


async def _draft(
    *, same_display_name: bool = False, organization_type: str = "school"
) -> tuple[str, str, str]:
    async with SessionLocal() as session:
        owner = User(
            id=str(uuid.uuid4()),
            email=f"practice-start-{uuid.uuid4()}@example.test",
            hashed_password="test-only",
        )
        session.add(owner)
        await session.commit()
        organization, _ = await organization_service.create_organization(
            session,
            payload=OrganizationCreate(name="Practice start", organization_type=organization_type),
            actor=owner,
        )
        if same_display_name:
            shared = await _side(
                session,
                organization_id=organization.id,
                owner_id=owner.id,
                prefix="Shared",
                player_count=4,
            )
            team_a = PracticeSideSelection(
                source_squad_id=shared.source_squad_id,
                participant_membership_ids=shared.participant_membership_ids[:2],
            )
            team_b = PracticeSideSelection(
                source_squad_id=shared.source_squad_id,
                participant_membership_ids=shared.participant_membership_ids[2:],
            )
        else:
            team_a = await _side(
                session, organization_id=organization.id, owner_id=owner.id, prefix="A"
            )
            team_b = await _side(
                session, organization_id=organization.id, owner_id=owner.id, prefix="B"
            )
        setup = await prepare_practice_match_setup(
            session,
            organization_id=organization.id,
            actor_user_id=owner.id,
            team_a=team_a,
            team_b=team_b,
        )
        game = await persist_practice_match_setup(
            session,
            organization_id=organization.id,
            actor_user_id=owner.id,
            setup=setup,
        )
        return organization.id, owner.id, game.id


@pytest.mark.parametrize("first_batting_side", ["team_a", "team_b"])
async def test_private_start_persists_both_side_orders_across_reload(
    first_batting_side: str,
) -> None:
    organization_id, owner_id, game_id = await _draft(same_display_name=True)
    async with SessionLocal() as session:
        game = await session.get(Game, game_id)
        assert game is not None
        assert game.team_a["name"] == game.team_b["name"]
        assert game.practice_start_context is None
        started = await start_private_practice_match(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            first_batting_side=first_batting_side,
        )
        assert started.status.value == "started"
        assert started.practice_start_context == {
            "version": PRACTICE_START_CONTEXT_VERSION,
            "first_batting_side": first_batting_side,
        }
    async with SessionLocal() as session:
        reloaded = await session.get(Game, game_id)
        assert reloaded is not None
        assert validate_practice_start_context(reloaded.practice_start_context) == first_batting_side
        assert reloaded.team_a["name"] == reloaded.team_b["name"]


@pytest.mark.parametrize(
    "context",
    [
        None,
        {"version": 2, "first_batting_side": "team_a"},
        {"version": True, "first_batting_side": "team_a"},
        {"version": 1, "first_batting_side": "team_c"},
        {"version": 1, "first_batting_side": ["team_a"]},
        {"version": 1, "first_batting_side": "team_a", "extra": True},
    ],
)
def test_practice_start_context_validation_is_strict(context: object) -> None:
    with pytest.raises(Exception) as exc_info:
        validate_practice_start_context(context)
    assert getattr(exc_info.value, "status_code", None) == 422
    with pytest.raises(ValidationError):
        PracticeMatchStart.model_validate({"first_batting_side": "not-a-side"})


async def test_practice_start_is_immutable_after_start_or_delivery() -> None:
    organization_id, owner_id, game_id = await _draft()
    async with SessionLocal() as session:
        await start_private_practice_match(
            session,
            organization_id=organization_id,
            actor_user_id=owner_id,
            game_id=game_id,
            first_batting_side="team_a",
        )
        with pytest.raises(Exception) as exc_info:
            await start_private_practice_match(
                session,
                organization_id=organization_id,
                actor_user_id=owner_id,
                game_id=game_id,
                first_batting_side="team_b",
            )
        assert getattr(exc_info.value, "status_code", None) == 409

    organization_id, owner_id, delivery_game_id = await _draft()
    async with SessionLocal() as session:
        game = await session.get(Game, delivery_game_id)
        assert game is not None
        game.deliveries = [{"synthetic": True}]
        await session.commit()
        with pytest.raises(Exception) as exc_info:
            await start_private_practice_match(
                session,
                organization_id=organization_id,
                actor_user_id=owner_id,
                game_id=delivery_game_id,
                first_batting_side="team_a",
            )
        assert getattr(exc_info.value, "status_code", None) == 409


async def test_practice_start_concurrent_sessions_choose_once_and_retry_idempotently() -> None:
    organization_id, owner_id, game_id = await _draft()

    async def attempt(side: str) -> tuple[str, str | int]:
        async with SessionLocal() as session:
            try:
                game = await start_private_practice_match(
                    session,
                    organization_id=organization_id,
                    actor_user_id=owner_id,
                    game_id=game_id,
                    first_batting_side=side,
                )
            except Exception as exc:
                return "error", getattr(exc, "status_code", 500)
            assert game.practice_start_context is not None
            return "started", game.practice_start_context["first_batting_side"]

    attempts = await asyncio.gather(attempt("team_a"), attempt("team_b"))
    successes = [result for result in attempts if result[0] == "started"]
    conflicts = [result for result in attempts if result == ("error", 409)]
    assert len(successes) == len(conflicts) == 1
    chosen_side = str(successes[0][1])

    assert await attempt(chosen_side) == ("started", chosen_side)
    async with SessionLocal() as session:
        reloaded = await session.get(Game, game_id)
        assert reloaded is not None
        assert reloaded.practice_start_context == {
            "version": PRACTICE_START_CONTEXT_VERSION,
            "first_batting_side": chosen_side,
        }


async def test_practice_start_reauthorizes_the_organization_actor() -> None:
    organization_id, _owner_id, game_id = await _draft()
    async with SessionLocal() as session:
        outsider = User(
            id=str(uuid.uuid4()),
            email=f"practice-start-outsider-{uuid.uuid4()}@example.test",
            hashed_password="test-only",
        )
        session.add(outsider)
        await session.commit()
        with pytest.raises(organization_service.OrganizationServiceError):
            await start_private_practice_match(
                session,
                organization_id=organization_id,
                actor_user_id=outsider.id,
                game_id=game_id,
                first_batting_side="team_a",
            )


async def test_dedicated_practice_start_route_returns_versioned_context() -> None:
    organization_id, owner_id, game_id = await _draft()
    async with SessionLocal() as session:
        owner = await session.get(User, owner_id)
        assert owner is not None
        response = await start_private_practice_route(
            organization_id=organization_id,
            game_id=game_id,
            payload=PracticeMatchStart(first_batting_side="team_b"),
            current_user=owner,
            db=session,
        )
        assert response.status == "started"
        assert response.practice_start_context == {
            "version": PRACTICE_START_CONTEXT_VERSION,
            "first_batting_side": "team_b",
        }


async def test_official_games_keep_null_practice_start_context() -> None:
    async with SessionLocal() as session:
        game = Game(
            id=str(uuid.uuid4()),
            team_a={"name": "Official A", "players": []},
            team_b={"name": "Official B", "players": []},
            interruptions=[],
        )
        session.add(game)
        await session.commit()
        await session.refresh(game)
        assert game.match_purpose == "official"
        assert game.practice_start_context is None


def _migration_module() -> object:
    path = Path(__file__).parents[1] / "alembic" / "versions" / "20261016010000_add_practice_start_context.py"
    spec = importlib.util.spec_from_file_location("b5_practice_start_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _workflow_migration_module() -> object:
    path = Path(__file__).parents[1] / "alembic" / "versions" / "20261016020000_add_practice_workflow_revision.py"
    spec = importlib.util.spec_from_file_location("b5_practice_workflow_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_practice_start_context_migration_preserves_existing_rows_and_guards_downgrade() -> None:
    migration = _migration_module()
    engine = create_engine("sqlite:///:memory:")
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE games (id VARCHAR PRIMARY KEY)"))
            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()
            assert "practice_start_context" in {
                column["name"] for column in inspect(connection).get_columns("games")
            }
            connection.execute(text("INSERT INTO games (id) VALUES ('legacy-official')"))
            assert connection.execute(
                text("SELECT practice_start_context FROM games WHERE id = 'legacy-official'")
            ).scalar_one() is None
            migration.downgrade()
            assert "practice_start_context" not in {
                column["name"] for column in inspect(connection).get_columns("games")
            }
            assert connection.execute(
                text("SELECT id FROM games WHERE id = 'legacy-official'")
            ).scalar_one() == "legacy-official"

            migration.upgrade()
            connection.execute(
                text(
                    "INSERT INTO games (id, practice_start_context) VALUES "
                    "('practice-started', '{\"version\": 1, \"first_batting_side\": \"team_b\"}')"
                )
            )
            with pytest.raises(RuntimeError, match="Cannot downgrade practice start context"):
                migration.downgrade()
    finally:
        engine.dispose()


def test_practice_workflow_migration_reverses_only_without_live_workflow_data() -> None:
    migration = _workflow_migration_module()
    engine = create_engine("sqlite:///:memory:")
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE games (id VARCHAR PRIMARY KEY)"))
            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()
            assert {"practice_workflow_revision", "practice_innings_history"} <= {
                column["name"] for column in inspect(connection).get_columns("games")
            }
            connection.execute(text("INSERT INTO games (id) VALUES ('clean-draft')"))
            migration.downgrade()
            assert not {"practice_workflow_revision", "practice_innings_history"} & {
                column["name"] for column in inspect(connection).get_columns("games")
            }

            migration.upgrade()
            connection.execute(
                text(
                    "INSERT INTO games (id, practice_workflow_revision, practice_innings_history) "
                    "VALUES ('live-workflow', 2, '[]')"
                )
            )
            with pytest.raises(RuntimeError, match="Cannot downgrade practice workflow revision"):
                migration.downgrade()
    finally:
        engine.dispose()
