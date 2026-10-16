"""Generic Game routes must not expose private or unresolved-purpose records."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

from backend.services import school_competition_service
from backend.sql_app.models import Game


def _team(organization_id: str | None = None) -> dict[str, Any]:
    team: dict[str, Any] = {"name": "Synthetic", "players": []}
    if organization_id is not None:
        team["school_source"] = {"organization_id": organization_id, "team_id": "team-id"}
    return team


def _game(purpose: str | None, organization_id: str | None = None) -> Game:
    return cast(
        Game,
        SimpleNamespace(
            match_purpose=purpose,
            team_a=_team(organization_id),
            team_b=_team(organization_id),
        ),
    )


def test_generic_routes_only_accept_missing_purpose_for_legacy_games() -> None:
    """A pre-migration purpose is compatible only with source-free legacy data."""
    assert school_competition_service.is_generic_official_game(_game(None))
    assert school_competition_service.is_generic_official_game(_game("official"))
    assert not school_competition_service.is_generic_official_game(_game("practice"))
    assert not school_competition_service.is_generic_official_game(_game("unexpected"))
    assert not school_competition_service.is_generic_official_game(_game(None, "school-id"))
