"""Dormant School/Club Free practice-match setup preparation.

This service validates and freezes a setup handoff only.  It intentionally
does not create a Game, expose a route, or enable scoring.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType
from typing import Any, cast

from backend.services import school_match_service
from backend.services.match_rules import (
    PRACTICE_MATCH_PURPOSE,
    MatchRulesValidationError,
    build_practice_match_rules,
)
from backend.sql_app import models
from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class PracticeSideSelection:
    """One match-local side drawn from an existing organization squad."""

    source_squad_id: str
    participant_membership_ids: tuple[str, ...]
    captain_membership_id: str | None = None
    wicketkeeper_membership_id: str | None = None


@dataclass(frozen=True)
class FrozenPracticeSide:
    """Identity-only setup handoff; display names cannot be used as identity."""

    source_squad_id: str
    canonical_player_ids: tuple[str, ...]
    school_player_membership_ids: tuple[str, ...]
    school_team_player_membership_ids: tuple[str, ...]
    captain_canonical_player_id: str | None
    wicketkeeper_canonical_player_id: str | None


@dataclass(frozen=True)
class FrozenPracticeMatchSetup:
    """Validated handoff for a future creation/scoring slice, not a Game."""

    match_purpose: str
    match_rules: Mapping[str, object]
    team_a: FrozenPracticeSide
    team_b: FrozenPracticeSide


def _invalid(detail: str) -> school_match_service.SchoolMatchServiceError:
    return school_match_service.SchoolMatchServiceError(422, detail)


def _validate_selection_shape(
    selection: object,
) -> tuple[PracticeSideSelection, tuple[str, ...]]:
    if not isinstance(selection, PracticeSideSelection):
        raise _invalid("Practice side selection must be a PracticeSideSelection")
    if not isinstance(selection.source_squad_id, str) or not selection.source_squad_id.strip():
        raise _invalid("Practice source squad is required")
    participant_ids = selection.participant_membership_ids
    if not isinstance(participant_ids, tuple) or not all(
        isinstance(membership_id, str) and membership_id.strip()
        for membership_id in participant_ids
    ):
        raise _invalid("Practice participant memberships must be non-empty string IDs")
    if not 2 <= len(participant_ids) <= 11:
        raise _invalid("Practice sides must contain 2 to 11 selected roster memberships")
    if len(set(participant_ids)) != len(participant_ids):
        raise _invalid("Practice side cannot contain duplicate roster memberships")
    for role_id in (selection.captain_membership_id, selection.wicketkeeper_membership_id):
        if role_id is not None and (not isinstance(role_id, str) or not role_id.strip()):
            raise _invalid("Practice match-day roles must be membership IDs or null")
    return selection, participant_ids


def _deep_freeze(value: Any) -> object:
    """Make the persisted-rule handoff immutable through every nested level."""

    if isinstance(value, Mapping):
        return MappingProxyType({key: _deep_freeze(item) for key, item in value.items()})
    if isinstance(value, list | tuple):
        return tuple(_deep_freeze(item) for item in value)
    return value


async def _freeze_side(
    db: AsyncSession,
    *,
    organization_id: str,
    selection: object,
) -> FrozenPracticeSide:
    selection, participant_ids = _validate_selection_shape(selection)
    team = await db.scalar(
        select(models.Team).where(
            models.Team.id == selection.source_squad_id,
            models.Team.organization_id == organization_id,
        )
    )
    if team is None:
        raise school_match_service.SchoolMatchServiceError(404, "Source squad not found")
    if team.status != "active":
        raise school_match_service.SchoolMatchServiceError(
            409, "Archived source squad cannot be used for practice setup"
        )

    result = await db.execute(
        select(
            models.SchoolTeamPlayerMembership,
            models.SchoolPlayerMembership,
            models.PlayerProfile,
        )
        .join(
            models.SchoolPlayerMembership,
            and_(
                models.SchoolPlayerMembership.id
                == models.SchoolTeamPlayerMembership.school_player_membership_id,
                models.SchoolPlayerMembership.organization_id
                == models.SchoolTeamPlayerMembership.organization_id,
            ),
        )
        .join(
            models.PlayerProfile,
            models.PlayerProfile.player_id == models.SchoolPlayerMembership.player_profile_id,
        )
        .where(
            models.SchoolTeamPlayerMembership.id.in_(set(participant_ids)),
            models.SchoolTeamPlayerMembership.organization_id == organization_id,
            models.SchoolTeamPlayerMembership.team_id == selection.source_squad_id,
        )
    )
    rows = result.tuples().all()
    by_membership_id = {row[0].id: row for row in rows}
    if set(by_membership_id) != set(participant_ids):
        raise _invalid("One or more practice participants are not eligible for the source squad")
    ordered_rows = tuple(by_membership_id[membership_id] for membership_id in participant_ids)
    if any(
        team_membership.status != "active"
        or school_membership.status != "active"
        or team_membership.organization_id != organization_id
        or school_membership.organization_id != organization_id
        for team_membership, school_membership, _profile in ordered_rows
    ):
        raise _invalid("One or more practice participants are inactive or outside the organization")

    canonical_player_ids = tuple(profile.player_id for _team, _school, profile in ordered_rows)
    if len(set(canonical_player_ids)) != len(canonical_player_ids):
        raise _invalid("Practice side cannot contain a duplicate canonical player")
    profile_by_membership_id = {
        team_membership.id: profile.player_id
        for team_membership, _school_membership, profile in ordered_rows
    }
    # Deselecting a player clears that role; captain and keeper may deliberately
    # resolve to the same canonical player.
    captain_id = profile_by_membership_id.get(selection.captain_membership_id)
    keeper_id = profile_by_membership_id.get(selection.wicketkeeper_membership_id)
    return FrozenPracticeSide(
        source_squad_id=selection.source_squad_id,
        canonical_player_ids=canonical_player_ids,
        school_player_membership_ids=tuple(
            school_membership.id for _team, school_membership, _profile in ordered_rows
        ),
        school_team_player_membership_ids=participant_ids,
        captain_canonical_player_id=captain_id,
        wicketkeeper_canonical_player_id=keeper_id,
    )


async def prepare_practice_match_setup(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    team_a: PracticeSideSelection,
    team_b: PracticeSideSelection,
    overs: int = 20,
) -> FrozenPracticeMatchSetup:
    """Authorize, validate, and freeze dormant practice setup data.

    A shared source squad is valid (a split-squad practice match); distinct
    source squads are also valid.  No persistent Team, PlayerProfile, Game, or
    scoring state is created here.
    """

    await school_match_service._authorize(
        db,
        organization_id=organization_id,
        actor_user_id=actor_user_id,
    )
    frozen_a = await _freeze_side(db, organization_id=organization_id, selection=team_a)
    frozen_b = await _freeze_side(db, organization_id=organization_id, selection=team_b)
    if set(frozen_a.canonical_player_ids) & set(frozen_b.canonical_player_ids):
        raise _invalid("A canonical player cannot participate on both practice sides")
    try:
        rules = build_practice_match_rules(
            team_a_source_squad_id=frozen_a.source_squad_id,
            team_a_canonical_player_ids=list(frozen_a.canonical_player_ids),
            team_b_source_squad_id=frozen_b.source_squad_id,
            team_b_canonical_player_ids=list(frozen_b.canonical_player_ids),
            overs=overs,
        )
    except MatchRulesValidationError as exc:
        raise _invalid(str(exc)) from exc
    frozen_rules = cast(Mapping[str, object], _deep_freeze(rules))
    return FrozenPracticeMatchSetup(
        match_purpose=PRACTICE_MATCH_PURPOSE,
        match_rules=frozen_rules,
        team_a=frozen_a,
        team_b=frozen_b,
    )
