"""Authorized provenance updates for saved-Team match-history metadata."""

from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from backend.services.game_access_service import require_game_mutation_access
from backend.sql_app import models
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class GamePerformanceMetadataError(Exception):
    status_code: int
    detail: str


def _source(side: object) -> tuple[str | None, str | None]:
    if not isinstance(side, dict):
        return None, None
    value = side.get("school_source")
    if not isinstance(value, dict):
        return None, None
    organization_id = value.get("organization_id")
    team_id = value.get("team_id")
    return (
        organization_id if isinstance(organization_id, str) else None,
        team_id if isinstance(team_id, str) else None,
    )


async def update_game_performance_metadata(
    db: AsyncSession,
    *,
    game_id: str,
    actor_user_id: str,
    expected_revision: int,
    reason: str,
    played_date_supplied: bool,
    played_date: dt.date | None,
    original_overs_supplied: bool,
    original_overs_limit: int | None,
) -> models.Game:
    """Confirm/correct only explicitly supplied metadata using revision CAS and audit rows."""
    normalized_reason = reason.strip()
    if not normalized_reason or len(normalized_reason) > 2000:
        raise GamePerformanceMetadataError(422, "A metadata reason of 1 to 2000 characters is required")
    if type(expected_revision) is not int or expected_revision < 1:
        raise GamePerformanceMetadataError(422, "expected_revision must be a positive integer")
    if not played_date_supplied and not original_overs_supplied:
        raise GamePerformanceMetadataError(422, "At least one metadata field must be supplied")
    if played_date_supplied and played_date is not None and type(played_date) is not dt.date:
        raise GamePerformanceMetadataError(422, "played_date must be a calendar date")
    if original_overs_supplied and original_overs_limit is not None and (
        type(original_overs_limit) is not int or not 1 <= original_overs_limit <= 120
    ):
        raise GamePerformanceMetadataError(422, "original_overs_limit must be from 1 to 120")

    actor = await db.scalar(
        select(models.User).where(
            models.User.id == actor_user_id,
            models.User.is_active.is_(True),
        )
    )
    if actor is None:
        raise GamePerformanceMetadataError(404, "Game not found")
    game = await db.scalar(
        select(models.Game).where(models.Game.id == game_id).with_for_update()
    )
    if game is None:
        raise GamePerformanceMetadataError(404, "Game not found")

    await require_game_mutation_access(db, game=game, user=actor)
    sources = (_source(game.team_a), _source(game.team_b))
    owned_sides = [
        (side, team_id)
        for side, (organization_id, team_id) in zip(("team_a", "team_b"), sources, strict=True)
        if organization_id is not None and team_id is not None
    ]
    if len(owned_sides) != 1:
        raise GamePerformanceMetadataError(404, "Game not found")
    organization_id, team_id = sources[0 if owned_sides[0][0] == "team_a" else 1]
    opposite_org_id = sources[1 if owned_sides[0][0] == "team_a" else 0][0]
    if organization_id is None or team_id is None or opposite_org_id not in {None, organization_id}:
        raise GamePerformanceMetadataError(404, "Game not found")
    saved_team = await db.scalar(
        select(models.Team.id).where(
            models.Team.id == team_id,
            models.Team.organization_id == organization_id,
        )
    )
    if saved_team is None:
        raise GamePerformanceMetadataError(404, "Game not found")

    changes: list[tuple[str, object | None, object | None, str]] = []
    values: dict[str, object] = {}
    if played_date_supplied:
        current = game.actual_played_date
        if current != played_date:
            if current is not None and played_date is not None and current != played_date:
                state, source = "confirmed", "staff_confirmed"
            elif played_date is None:
                state, source = "unknown", None
            else:
                state, source = "confirmed", "staff_confirmed"
            changes.append(
                (
                    "actual_played_date",
                    current.isoformat() if current else None,
                    played_date.isoformat() if played_date else None,
                    source or "staff_correction",
                )
            )
            values.update(
                actual_played_date=played_date,
                played_date_trust_state=state,
                played_date_source=source,
            )
    if original_overs_supplied:
        current_overs = game.original_overs_limit
        if current_overs != original_overs_limit:
            if original_overs_limit is None:
                state, source = "unknown", None
            elif game.original_overs_limit is None:
                state, source = "staff_corrected", "staff_correction"
            else:
                state, source = "staff_corrected", "staff_correction"
            changes.append(
                (
                    "original_overs_limit",
                    current_overs,
                    original_overs_limit,
                    source or "staff_correction",
                )
            )
            values.update(
                original_overs_limit=original_overs_limit,
                original_format_trust_state=state,
                original_format_source=source,
            )

    if not changes:
        return game
    if game.team_performance_metadata_revision != expected_revision:
        raise GamePerformanceMetadataError(409, "Game metadata revision is stale")

    next_revision = expected_revision + 1
    result = await db.execute(
        update(models.Game)
        .where(
            models.Game.id == game_id,
            models.Game.team_performance_metadata_revision == expected_revision,
        )
        .values(
            **values,
            team_performance_metadata_revision=next_revision,
        )
    )
    if result.rowcount != 1:
        await db.rollback()
        raise GamePerformanceMetadataError(409, "Game metadata revision is stale")
    for field_name, old_value, new_value, source in changes:
        db.add(
            models.GamePerformanceMetadataAudit(
                game_id=game_id,
                metadata_revision=next_revision,
                field_name=field_name,
                old_value=old_value,
                new_value=new_value,
                source=source,
                reason=normalized_reason,
                actor_user_id=actor_user_id,
                recorded_at=dt.datetime.now(dt.UTC),
            )
        )
    try:
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    await db.refresh(game)
    return game
