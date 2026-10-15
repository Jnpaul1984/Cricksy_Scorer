from __future__ import annotations

from collections import deque
from unittest.mock import ANY, AsyncMock

import pytest

from backend.services import practice_match_setup_service
from backend.services.practice_match_setup_service import (
    PracticeSideSelection,
    prepare_practice_match_setup,
)
from backend.sql_app import models


class _Result:
    def __init__(self, rows: list[tuple[object, object, object]]) -> None:
        self._rows = rows

    def tuples(self) -> _Result:
        return self

    def all(self) -> list[tuple[object, object, object]]:
        return self._rows


class _FakeSession:
    def __init__(
        self,
        teams: list[models.Team],
        row_sets: list[list[tuple[object, object, object]]],
    ) -> None:
        self._teams = deque(teams)
        self._row_sets = deque(row_sets)

    async def scalar(self, _statement: object) -> models.Team | None:
        return self._teams.popleft()

    async def execute(self, _statement: object) -> _Result:
        return _Result(self._row_sets.popleft())


def _side_rows(
    *,
    organization_id: str,
    squad_id: str,
    prefix: str,
    size: int,
    inactive_index: int | None = None,
) -> tuple[PracticeSideSelection, list[tuple[object, object, object]]]:
    member_ids = tuple(f"{prefix}-team-membership-{index}" for index in range(size))
    selection = PracticeSideSelection(
        source_squad_id=squad_id,
        participant_membership_ids=member_ids,
        captain_membership_id=member_ids[0],
        wicketkeeper_membership_id=member_ids[0],
    )
    rows: list[tuple[object, object, object]] = []
    for index, member_id in enumerate(member_ids):
        school_member = models.SchoolPlayerMembership(
            id=f"{prefix}-school-membership-{index}",
            organization_id=organization_id,
            player_profile_id=f"{prefix}-player-{index}",
            status="active",
        )
        team_member = models.SchoolTeamPlayerMembership(
            id=member_id,
            organization_id=organization_id,
            team_id=squad_id,
            school_player_membership_id=school_member.id,
            status="inactive" if inactive_index == index else "active",
        )
        profile = models.PlayerProfile(
            player_id=school_member.player_profile_id,
            player_name=f"Ignored identity display {prefix} {index}",
        )
        rows.append((team_member, school_member, profile))
    return selection, rows


def _team(squad_id: str, organization_id: str) -> models.Team:
    return models.Team(id=squad_id, organization_id=organization_id, name=squad_id, status="active")


@pytest.mark.asyncio
async def test_prepares_equal_sides_with_dual_role_and_frozen_b1_rules(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organization_id = "organization-a"
    side_a, rows_a = _side_rows(
        organization_id=organization_id, squad_id="squad-a", prefix="a", size=2
    )
    side_b, rows_b = _side_rows(
        organization_id=organization_id, squad_id="squad-b", prefix="b", size=2
    )
    authorize = AsyncMock()
    monkeypatch.setattr(practice_match_setup_service.school_match_service, "_authorize", authorize)
    setup = await prepare_practice_match_setup(
        _FakeSession(
            [_team("squad-a", organization_id), _team("squad-b", organization_id)], [rows_a, rows_b]
        ),  # type: ignore[arg-type]
        organization_id=organization_id,
        actor_user_id="authorized-coach",
        team_a=side_a,
        team_b=side_b,
    )

    authorize.assert_awaited_once_with(
        ANY, organization_id=organization_id, actor_user_id="authorized-coach"
    )
    assert setup.match_purpose == "practice"
    assert setup.match_rules["overs"] == 20
    assert setup.match_rules["wicket_limits"] == {"team_a": 1, "team_b": 1}
    assert setup.team_a.captain_canonical_player_id == setup.team_a.wicketkeeper_canonical_player_id
    assert "Ignored identity display" not in str(setup)

    with pytest.raises(TypeError):
        setup.match_rules["wicket_limits"]["team_a"] = 99  # type: ignore[index]
    assert setup.match_rules["wicket_limits"]["team_a"] == 1
    assert setup.match_rules["sides"]["team_a"]["canonical_player_ids"] == (
        "a-player-0",
        "a-player-1",
    )  # type: ignore[index]


@pytest.mark.asyncio
async def test_allows_one_source_squad_to_be_split_and_clears_deselected_roles(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organization_id = "organization-a"
    side_a, rows_a = _side_rows(
        organization_id=organization_id, squad_id="shared-squad", prefix="a", size=6
    )
    side_b, rows_b = _side_rows(
        organization_id=organization_id, squad_id="shared-squad", prefix="b", size=6
    )
    side_a = PracticeSideSelection(
        source_squad_id=side_a.source_squad_id,
        participant_membership_ids=side_a.participant_membership_ids,
        captain_membership_id="deselected-player",
        wicketkeeper_membership_id=None,
    )
    monkeypatch.setattr(
        practice_match_setup_service.school_match_service, "_authorize", AsyncMock()
    )
    setup = await prepare_practice_match_setup(
        _FakeSession(
            [_team("shared-squad", organization_id), _team("shared-squad", organization_id)],
            [rows_a, rows_b],
        ),  # type: ignore[arg-type]
        organization_id=organization_id,
        actor_user_id="authorized-coach",
        team_a=side_a,
        team_b=side_b,
        overs=12,
    )

    assert setup.team_a.source_squad_id == setup.team_b.source_squad_id == "shared-squad"
    assert setup.team_a.captain_canonical_player_id is None
    assert setup.team_a.wicketkeeper_canonical_player_id is None
    assert setup.match_rules["overs"] == 12
    assert setup.match_rules["wicket_limits"] == {"team_a": 5, "team_b": 5}


@pytest.mark.asyncio
@pytest.mark.parametrize("side_size", [2, 6, 8, 11])
async def test_rejects_unequal_sides_before_any_persistent_match_exists(
    monkeypatch: pytest.MonkeyPatch, side_size: int
) -> None:
    organization_id = "organization-a"
    side_a, rows_a = _side_rows(
        organization_id=organization_id, squad_id="squad-a", prefix="a", size=side_size
    )
    side_b, rows_b = _side_rows(
        organization_id=organization_id, squad_id="squad-b", prefix="b", size=side_size - 1
    )
    monkeypatch.setattr(
        practice_match_setup_service.school_match_service, "_authorize", AsyncMock()
    )
    with pytest.raises(practice_match_setup_service.school_match_service.SchoolMatchServiceError):
        await prepare_practice_match_setup(
            _FakeSession(
                [_team("squad-a", organization_id), _team("squad-b", organization_id)],
                [rows_a, rows_b],
            ),  # type: ignore[arg-type]
            organization_id=organization_id,
            actor_user_id="authorized-coach",
            team_a=side_a,
            team_b=side_b,
        )


@pytest.mark.asyncio
async def test_rejects_duplicate_canonical_player_across_practice_sides(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    organization_id = "organization-a"
    side_a, rows_a = _side_rows(
        organization_id=organization_id, squad_id="squad-a", prefix="a", size=2
    )
    side_b, rows_b = _side_rows(
        organization_id=organization_id, squad_id="squad-b", prefix="b", size=2
    )
    rows_b[0][2].player_id = rows_a[0][2].player_id  # type: ignore[index,union-attr]
    monkeypatch.setattr(
        practice_match_setup_service.school_match_service, "_authorize", AsyncMock()
    )
    with pytest.raises(practice_match_setup_service.school_match_service.SchoolMatchServiceError):
        await prepare_practice_match_setup(
            _FakeSession(
                [_team("squad-a", organization_id), _team("squad-b", organization_id)],
                [rows_a, rows_b],
            ),  # type: ignore[arg-type]
            organization_id=organization_id,
            actor_user_id="authorized-coach",
            team_a=side_a,
            team_b=side_b,
        )


@pytest.mark.asyncio
async def test_rejects_inactive_practice_membership(monkeypatch: pytest.MonkeyPatch) -> None:
    organization_id = "organization-a"
    side_a, rows_a = _side_rows(
        organization_id=organization_id, squad_id="squad-a", prefix="a", size=2
    )
    side_b, rows_b = _side_rows(
        organization_id=organization_id, squad_id="squad-b", prefix="b", size=2, inactive_index=1
    )
    monkeypatch.setattr(
        practice_match_setup_service.school_match_service, "_authorize", AsyncMock()
    )
    with pytest.raises(practice_match_setup_service.school_match_service.SchoolMatchServiceError):
        await prepare_practice_match_setup(
            _FakeSession(
                [_team("squad-a", organization_id), _team("squad-b", organization_id)],
                [rows_a, rows_b],
            ),  # type: ignore[arg-type]
            organization_id=organization_id,
            actor_user_id="authorized-coach",
            team_a=side_a,
            team_b=side_b,
        )


@pytest.mark.asyncio
@pytest.mark.parametrize("invalid_side", [None, {"source_squad_id": "squad-a"}])
async def test_rejects_malformed_side_objects_with_a_controlled_error(
    monkeypatch: pytest.MonkeyPatch, invalid_side: object
) -> None:
    organization_id = "organization-a"
    valid_side, _unused_rows = _side_rows(
        organization_id=organization_id, squad_id="squad-b", prefix="b", size=2
    )
    authorize = AsyncMock()
    monkeypatch.setattr(practice_match_setup_service.school_match_service, "_authorize", authorize)
    fake_db = _FakeSession([], [])

    with pytest.raises(
        practice_match_setup_service.school_match_service.SchoolMatchServiceError,
        match="Practice side selection",
    ) as raised:
        await prepare_practice_match_setup(
            fake_db,  # type: ignore[arg-type]
            organization_id=organization_id,
            actor_user_id="authorized-coach",
            team_a=invalid_side,  # type: ignore[arg-type]
            team_b=valid_side,
        )

    assert raised.value.status_code == 422
    authorize.assert_awaited_once()
