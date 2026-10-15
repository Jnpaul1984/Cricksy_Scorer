from __future__ import annotations

import importlib.util
from pathlib import Path

import pytest
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.exc import IntegrityError

from alembic.migration import MigrationContext
from alembic.operations import Operations
from backend.services.match_rules import (
    DEFAULT_PRACTICE_OVERS,
    PRACTICE_MATCH_PURPOSE,
    MatchRulesValidationError,
    build_practice_match_rules,
    resolve_match_rules,
    serialize_match_rules,
)
from backend.sql_app.models import Game
from backend.sql_app.schemas import Game as GameResponse


def _rules(side_size: int, *, overs: int = DEFAULT_PRACTICE_OVERS) -> dict:
    return {
        "version": 1,
        "overs": overs,
        "balls_per_over": 6,
        "innings_per_side": 1,
        "side_sizes": {"team_a": side_size, "team_b": side_size},
        "wicket_limits": {"team_a": side_size - 1, "team_b": side_size - 1},
        "sides": {
            "team_a": {
                "source_squad_id": "source-squad-a",
                "canonical_player_ids": [f"a-{number}" for number in range(side_size)],
            },
            "team_b": {
                "source_squad_id": "source-squad-b",
                "canonical_player_ids": [f"b-{number}" for number in range(side_size)],
            },
        },
        "dls_enabled": False,
        "predictions_enabled": False,
    }


@pytest.mark.parametrize("side_size", [2, 6, 8, 11])
def test_practice_rules_resolve_frozen_wicket_limits(side_size: int) -> None:
    resolved = resolve_match_rules(
        match_purpose=PRACTICE_MATCH_PURPOSE, match_rules=_rules(side_size)
    )

    assert resolved.overs == 20
    assert resolved.balls_per_over == 6
    assert resolved.innings_per_side == 1
    assert resolved.wicket_limit_for("team_a") == side_size - 1
    assert resolved.wicket_limit_for("team_b") == side_size - 1
    assert resolved.dls_enabled is False
    assert resolved.predictions_enabled is False


def test_practice_rules_round_trip_preserves_identity_only_snapshot() -> None:
    original = _rules(6, overs=12)
    resolved = resolve_match_rules(match_purpose=PRACTICE_MATCH_PURPOSE, match_rules=original)

    serialized = serialize_match_rules(resolved)

    assert serialized == original
    assert "name" not in str(serialized)
    assert (
        resolve_match_rules(match_purpose=PRACTICE_MATCH_PURPOSE, match_rules=serialized)
        == resolved
    )


def test_practice_rule_builder_uses_the_twenty_over_default() -> None:
    built = build_practice_match_rules(
        team_a_source_squad_id="source-squad-a",
        team_a_canonical_player_ids=["a-1", "a-2"],
        team_b_source_squad_id="source-squad-b",
        team_b_canonical_player_ids=["b-1", "b-2"],
    )

    assert built["overs"] == DEFAULT_PRACTICE_OVERS
    assert built["wicket_limits"] == {"team_a": 1, "team_b": 1}


@pytest.mark.parametrize(
    "rules",
    [
        None,
        {},
        {"version": 999},
        {**_rules(6), "unknown": "field"},
        {**_rules(6), "version": True},
        {**_rules(6), "overs": True},
        {**_rules(6), "overs": 20.0},
        {**_rules(6), "balls_per_over": 5},
        {**_rules(6), "balls_per_over": 6.0},
        {**_rules(6), "innings_per_side": 2},
        {**_rules(6), "innings_per_side": True},
        {**_rules(6), "dls_enabled": True},
        {**_rules(6), "predictions_enabled": True},
        {**_rules(6), "side_sizes": {"team_a": 6, "team_b": 5}},
        {**_rules(6), "wicket_limits": {"team_a": 4, "team_b": 5}},
    ],
)
def test_practice_rules_fail_closed_for_missing_malformed_or_inconsistent_snapshots(
    rules: object,
) -> None:
    with pytest.raises(MatchRulesValidationError):
        resolve_match_rules(match_purpose=PRACTICE_MATCH_PURPOSE, match_rules=rules)


def test_practice_rules_reject_duplicate_canonical_identity_across_sides() -> None:
    rules = _rules(2)
    rules["sides"]["team_b"]["canonical_player_ids"][0] = "a-0"

    with pytest.raises(MatchRulesValidationError, match="both practice sides"):
        resolve_match_rules(match_purpose=PRACTICE_MATCH_PURPOSE, match_rules=rules)


def test_legacy_and_official_rules_retain_ten_wicket_defaults() -> None:
    resolved = resolve_match_rules(match_purpose="official", match_rules=None)

    assert resolved.wicket_limits == {"team_a": 10, "team_b": 10}
    assert serialize_match_rules(resolved) is None
    with pytest.raises(MatchRulesValidationError):
        resolve_match_rules(match_purpose="official", match_rules=_rules(11))


def test_model_has_official_server_default_and_database_purpose_constraint() -> None:
    purpose = Game.__table__.c.match_purpose

    assert purpose.default is not None and purpose.default.arg == "official"
    assert purpose.server_default is not None
    assert any(
        constraint.name == "ck_games_match_purpose" for constraint in Game.__table__.constraints
    )


def test_dormant_rules_do_not_expand_existing_game_response_contract() -> None:
    assert "match_purpose" not in GameResponse.model_fields
    assert "match_rules" not in GameResponse.model_fields


def _load_migration_module():
    path = (
        Path(__file__).parents[1]
        / "alembic"
        / "versions"
        / "20261015010000_add_game_match_purpose_and_rules.py"
    )
    spec = importlib.util.spec_from_file_location("b1_match_rules_migration", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_additive_migration_applies_official_default_and_constraint_on_disposable_sqlite() -> None:
    engine = create_engine("sqlite://")
    migration = _load_migration_module()
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE games (id VARCHAR PRIMARY KEY)"))
            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()
            columns = {
                column["name"]: column for column in inspect(connection).get_columns("games")
            }
            assert {"match_purpose", "match_rules"}.issubset(columns)
            connection.execute(text("INSERT INTO games (id) VALUES ('legacy-game')"))
            assert (
                connection.execute(text("SELECT match_purpose FROM games")).scalar_one()
                == "official"
            )
            with pytest.raises(IntegrityError):
                connection.execute(
                    text(
                        "INSERT INTO games (id, match_purpose) VALUES ('invalid-purpose', 'invalid')"
                    )
                )
    finally:
        engine.dispose()


def test_migration_downgrade_refuses_practice_data_without_touching_schema_or_rows() -> None:
    engine = create_engine("sqlite://")
    migration = _load_migration_module()
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE games (id VARCHAR PRIMARY KEY)"))
            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()
            connection.execute(
                text(
                    "INSERT INTO games (id, match_purpose, match_rules) "
                    "VALUES ('practice-game', 'practice', '{\"version\": 1}')"
                )
            )

            with pytest.raises(RuntimeError, match="Cannot downgrade match rules migration"):
                migration.downgrade()

            column_names = {column["name"] for column in inspect(connection).get_columns("games")}
            assert {"match_purpose", "match_rules"}.issubset(column_names)
            assert (
                connection.execute(
                    text("SELECT match_purpose FROM games WHERE id = 'practice-game'")
                ).scalar_one()
                == "practice"
            )
            assert (
                connection.execute(
                    text("SELECT match_rules IS NOT NULL FROM games WHERE id = 'practice-game'")
                ).scalar_one()
                == 1
            )
    finally:
        engine.dispose()


def test_migration_downgrade_and_reupgrade_allow_untouched_official_rows() -> None:
    engine = create_engine("sqlite://")
    migration = _load_migration_module()
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE games (id VARCHAR PRIMARY KEY)"))
            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()
            connection.execute(text("INSERT INTO games (id) VALUES ('official-game')"))

            migration.downgrade()
            assert {column["name"] for column in inspect(connection).get_columns("games")} == {"id"}
            assert connection.execute(text("SELECT id FROM games")).scalar_one() == "official-game"

            migration.upgrade()
            assert connection.execute(
                text("SELECT match_purpose, match_rules FROM games WHERE id = 'official-game'")
            ).one() == ("official", None)
    finally:
        engine.dispose()
