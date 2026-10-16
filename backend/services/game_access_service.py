"""Per-Game access checks shared by legacy Game routes outside the gameplay router.

Reads follow the established Game privacy policy (the same check used by
``GET /games/{id}``): School/Club Games are visible only to active members of the
owning organization, and legacy Games without an organization keep their
existing behavior.

Unauthenticated collection routes list legacy Games plus only those School/Club
Games that are deliberately published (the public scorecard rule).

Writes always require an authenticated, active user (enforced by the
``get_current_active_user`` dependency before the Game is loaded) and then:

* School/Club Games: the contextual scorer authority used by the scoring routes.
* School/Club Games whose ownership is unresolved (malformed source or sides naming
  different organizations): denied, never treated as legacy.
* Legacy Games with a recorded creator: the creator, a ``scorer`` contributor,
  or a superuser.
* Legacy Games without a recorded creator: superusers only (owner-approved
  fail-closed policy). Creators are recorded server-side at creation; existing
  rows are not backfilled.
"""

from __future__ import annotations

from collections.abc import Iterable

import structlog
from backend.services import school_competition_service
from backend.sql_app import models
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

logger = structlog.get_logger(__name__)


async def require_game_read_access(
    db: AsyncSession, *, game: models.Game, user: models.User | None
) -> None:
    """Apply the established Game privacy policy for read-only routes."""
    if not school_competition_service.is_generic_official_game(game):
        raise HTTPException(status_code=404, detail="Game not found")
    try:
        await school_competition_service.require_school_game_member(db, game=game, user=user)
    except school_competition_service.SchoolCompetitionServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


async def publicly_listable_games(
    db: AsyncSession, games: Iterable[models.Game]
) -> list[models.Game]:
    """Drop School/Club Games that are not deliberately published."""
    listable: list[models.Game] = []
    for game in games:
        if not school_competition_service.is_generic_official_game(game):
            continue
        if not school_competition_service.is_organization_game(game) or (
            await school_competition_service.public_school_game_organization(db, game) is not None
        ):
            listable.append(game)
    return listable


async def require_game_mutation_access(
    db: AsyncSession, *, game: models.Game, user: models.User
) -> None:
    """Allow a Game mutation only for an actor authorized to score this Game."""
    if not school_competition_service.is_generic_official_game(game):
        raise HTTPException(status_code=404, detail="Game not found")
    try:
        (
            organization_id,
            can_score,
        ) = await school_competition_service.school_game_scoring_authorization(
            db, game=game, user=user
        )
    except school_competition_service.SchoolCompetitionServiceError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    if organization_id is not None:
        if not can_score:
            logger.warning(
                "game.mutation_denied",
                game_id=game.id,
                organization_id=organization_id,
                actor_user_id=user.id,
            )
            raise HTTPException(status_code=403, detail="Insufficient organization role")
        return

    if user.is_superuser:
        return
    if game.created_by_user_id is None:
        logger.warning("game.mutation_denied_unowned", game_id=game.id, actor_user_id=user.id)
        raise HTTPException(status_code=403, detail="Game has no recorded owner")
    if game.created_by_user_id == user.id:
        return
    contributor_id = await db.scalar(
        select(models.GameContributor.id).where(
            models.GameContributor.game_id == game.id,
            models.GameContributor.user_id == user.id,
            models.GameContributor.role == models.GameContributorRoleEnum.scorer,
        )
    )
    if contributor_id is None:
        logger.warning("game.mutation_denied", game_id=game.id, actor_user_id=user.id)
        raise HTTPException(status_code=403, detail="Not authorized to modify this game")
