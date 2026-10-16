"""Atomic persistence for organization-private, unstarted practice drafts.

Dedicated organization routes own creation. Generic Game routes and scoring
remain unavailable to practice records until their consumers are separately
reviewed.
"""

from __future__ import annotations

import uuid
from typing import Any

from backend.services import practice_match_setup_service, school_match_service
from backend.services.match_rules import PRACTICE_MATCH_PURPOSE
from backend.sql_app import models
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

PRACTICE_START_CONTEXT_VERSION = 1
_PRACTICE_START_CONTEXT_KEYS = frozenset({"version", "first_batting_side"})
_PRACTICE_SIDE_KEYS = frozenset({"team_a", "team_b"})


def validate_practice_start_context(context: object) -> str:
    """Return the stable first-batting side or reject malformed stored context."""

    if not isinstance(context, dict) or set(context) != _PRACTICE_START_CONTEXT_KEYS:
        raise school_match_service.SchoolMatchServiceError(
            422, "Practice start context must contain exactly version and first_batting_side"
        )
    version = context.get("version")
    if type(version) is not int or version != PRACTICE_START_CONTEXT_VERSION:
        raise school_match_service.SchoolMatchServiceError(
            422, "Unsupported practice start context version"
        )
    first_batting_side = context.get("first_batting_side")
    if not isinstance(first_batting_side, str) or first_batting_side not in _PRACTICE_SIDE_KEYS:
        raise school_match_service.SchoolMatchServiceError(
            422, "Practice first_batting_side must be team_a or team_b"
        )
    return first_batting_side


def _practice_game_belongs_to_organization(game: models.Game, organization_id: str) -> bool:
    for side in (game.team_a, game.team_b):
        if not isinstance(side, dict):
            return False
        source = side.get("school_source")
        if not isinstance(source, dict) or source.get("organization_id") != organization_id:
            return False
    return True


def _assert_practice_start_ready(game: models.Game) -> None:
    if game.match_purpose != PRACTICE_MATCH_PURPOSE or game.publication_state != "private":
        raise school_match_service.SchoolMatchServiceError(404, "Practice match not found")
    if game.status != models.GameStatus.not_started:
        raise school_match_service.SchoolMatchServiceError(
            409, "Practice match has already started"
        )
    if game.deliveries:
        raise school_match_service.SchoolMatchServiceError(
            409, "Practice start context cannot change after deliveries exist"
        )
    if game.practice_start_context is not None:
        raise school_match_service.SchoolMatchServiceError(
            409, "Practice start context is already set"
        )

    selected_player_ids: list[set[str]] = []
    for side_key, side in (("team_a", game.team_a), ("team_b", game.team_b)):
        if not isinstance(side, dict):
            raise school_match_service.SchoolMatchServiceError(
                422, f"Practice {side_key} is malformed"
            )
        players = side.get("players")
        playing_xi = side.get("playing_xi")
        if not isinstance(players, list) or not isinstance(playing_xi, list):
            raise school_match_service.SchoolMatchServiceError(
                422, f"Practice {side_key} is not ready"
            )
        player_ids = {
            player_id
            for player in players
            if isinstance(player, dict)
            for player_id in (player.get("id"),)
            if isinstance(player_id, str) and player_id
        }
        xi_ids = set(playing_xi)
        if (
            len(player_ids) < 2
            or any(
                isinstance(player, dict)
                and (not isinstance(player.get("id"), str) or not player["id"])
                for player in players
            )
            or not all(isinstance(player_id, str) and player_id for player_id in xi_ids)
            or len(xi_ids) != len(playing_xi)
            or xi_ids != player_ids
        ):
            raise school_match_service.SchoolMatchServiceError(
                422, f"Practice {side_key} is not ready"
            )
        selected_player_ids.append(player_ids)
    if selected_player_ids[0] & selected_player_ids[1]:
        raise school_match_service.SchoolMatchServiceError(
            422, "Practice sides must have distinct participant identities"
        )


async def _snapshot_side(
    db: AsyncSession,
    *,
    organization_id: str,
    side_key: str,
    side: practice_match_setup_service.FrozenPracticeSide,
) -> dict[str, Any]:
    """Revalidate the frozen IDs and build a display-only Game JSON snapshot."""

    selection = practice_match_setup_service.PracticeSideSelection(
        source_squad_id=side.source_squad_id,
        participant_membership_ids=side.school_team_player_membership_ids,
    )
    current = await practice_match_setup_service._freeze_side(
        db, organization_id=organization_id, selection=selection
    )
    if (
        current.source_squad_id != side.source_squad_id
        or current.canonical_player_ids != side.canonical_player_ids
        or current.school_player_membership_ids != side.school_player_membership_ids
        or current.school_team_player_membership_ids != side.school_team_player_membership_ids
    ):
        raise school_match_service.SchoolMatchServiceError(
            409, f"Practice {side_key} roster changed after setup"
        )
    team = await db.scalar(
        select(models.Team).where(
            models.Team.id == side.source_squad_id,
            models.Team.organization_id == organization_id,
        )
    )
    if team is None:
        raise school_match_service.SchoolMatchServiceError(404, "Source squad not found")
    profile_labels = {
        player_id: player_name
        for player_id, player_name in (
            await db.execute(
                select(models.PlayerProfile.player_id, models.PlayerProfile.player_name).where(
                    models.PlayerProfile.player_id.in_(side.canonical_player_ids)
                )
            )
        ).all()
        if isinstance(player_name, str) and player_name.strip()
    }
    # Names are immutable display snapshots. Every relationship is carried by
    # the frozen IDs; a later public projection will still require the
    # participant to remain active before revealing this label.
    return {
        "name": team.name,
        "players": [
            {
                "id": canonical_id,
                "name": profile_labels.get(canonical_id, "Unavailable participant"),
                "player_profile_id": canonical_id,
                "school_player_membership_id": school_membership_id,
                "school_team_player_membership_id": team_membership_id,
            }
            for canonical_id, school_membership_id, team_membership_id in zip(
                side.canonical_player_ids,
                side.school_player_membership_ids,
                side.school_team_player_membership_ids,
                strict=True,
            )
        ],
        "playing_xi": list(side.canonical_player_ids),
        "school_source": {"organization_id": organization_id, "team_id": side.source_squad_id},
    }


async def persist_practice_match_setup(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    setup: practice_match_setup_service.FrozenPracticeMatchSetup,
) -> models.Game:
    """Persist exactly one private, unstarted practice Game or roll back completely."""

    await school_match_service._authorize(
        db, organization_id=organization_id, actor_user_id=actor_user_id
    )
    handoff = practice_match_setup_service.serialize_practice_match_setup(setup)
    team_a = await _snapshot_side(
        db, organization_id=organization_id, side_key="team_a", side=setup.team_a
    )
    team_b = await _snapshot_side(
        db, organization_id=organization_id, side_key="team_b", side=setup.team_b
    )
    rules = handoff["match_rules"]
    assert isinstance(rules, dict)
    game = models.Game(
        id=str(uuid.uuid4()),
        team_a=team_a,
        team_b=team_b,
        match_type="limited",
        match_purpose=PRACTICE_MATCH_PURPOSE,
        match_rules=rules,
        overs_limit=rules["overs"],
        dls_enabled=False,
        interruptions=[],
        publication_state="private",
        created_by_user_id=actor_user_id,
        team_a_captain_id=setup.team_a.captain_canonical_player_id,
        team_a_keeper_id=setup.team_a.wicketkeeper_canonical_player_id,
        team_b_captain_id=setup.team_b.captain_canonical_player_id,
        team_b_keeper_id=setup.team_b.wicketkeeper_canonical_player_id,
    )
    db.add(game)
    try:
        await db.flush()
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    await db.refresh(game)
    return game


async def start_private_practice_match(
    db: AsyncSession,
    *,
    organization_id: str,
    actor_user_id: str,
    game_id: str,
    first_batting_side: str,
) -> models.Game:
    """Persist the one immutable side-key start context for a private practice draft."""

    await school_match_service._authorize(
        db, organization_id=organization_id, actor_user_id=actor_user_id
    )
    if first_batting_side not in _PRACTICE_SIDE_KEYS:
        raise school_match_service.SchoolMatchServiceError(
            422, "Practice first_batting_side must be team_a or team_b"
        )
    game = await db.scalar(select(models.Game).where(models.Game.id == game_id).with_for_update())
    if game is None or not _practice_game_belongs_to_organization(game, organization_id):
        raise school_match_service.SchoolMatchServiceError(404, "Practice match not found")
    if game.practice_start_context is not None:
        persisted_side = validate_practice_start_context(game.practice_start_context)
        if game.status == models.GameStatus.started and persisted_side == first_batting_side:
            return game
        raise school_match_service.SchoolMatchServiceError(
            409, "Practice start context is already set"
        )
    _assert_practice_start_ready(game)
    context = {
        "version": PRACTICE_START_CONTEXT_VERSION,
        "first_batting_side": first_batting_side,
    }
    # The lock serializes PostgreSQL callers. The conditional update is still
    # required because SQLite ignores FOR UPDATE and because it prevents a
    # stale session from overwriting the first side chosen by another request.
    updated = await db.execute(
        update(models.Game)
        .where(
            models.Game.id == game_id,
            models.Game.status == models.GameStatus.not_started,
            models.Game.practice_start_context.is_(None),
        )
        .values(practice_start_context=context, status=models.GameStatus.started)
    )
    if updated.rowcount != 1:
        await db.rollback()
        current = await db.get(models.Game, game_id)
        if current is not None and _practice_game_belongs_to_organization(current, organization_id):
            persisted_context = current.practice_start_context
            if (
                current.status == models.GameStatus.started
                and persisted_context is not None
                and validate_practice_start_context(persisted_context) == first_batting_side
            ):
                return current
        raise school_match_service.SchoolMatchServiceError(
            409, "Practice match has already started"
        )
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    await db.refresh(game)
    validate_practice_start_context(game.practice_start_context)
    return game
