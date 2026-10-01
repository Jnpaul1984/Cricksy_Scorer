"""Fresh public-subject resolution for staff favorites; never use fan favorites."""

from __future__ import annotations

from dataclasses import dataclass

from backend.services import organization_publication_service
from backend.services.organization_publication_service import (
    PUBLIC_COMPETITION_KEY_PATTERN,
    PUBLIC_IDENTIFIER_PATTERN,
)
from backend.services.organization_service import ACTIVE_MEMBERSHIP_STATUS
from backend.sql_app import models
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

STAFF_ROLES = frozenset({"owner", "admin", "coach", "scorer"})


@dataclass(frozen=True)
class ResolvedPublicSubject:
    kind: str
    public_key: str
    display_name: str
    canonical_path: str


async def require_active_staff(db: AsyncSession, *, user_id: str) -> None:
    membership = await db.scalar(
        select(models.OrganizationMembership.id)
        .where(
            models.OrganizationMembership.user_id == user_id,
            models.OrganizationMembership.status == ACTIVE_MEMBERSHIP_STATUS,
            models.OrganizationMembership.role.in_(STAFF_ROLES),
        )
        .limit(1)
    )
    if membership is None:
        raise PermissionError("An active staff membership is required")


async def resolve_public_subject(
    db: AsyncSession, *, kind: str, public_key: str
) -> ResolvedPublicSubject | None:
    """Resolve fresh publication state on every operation; falsey means safe 404."""
    if kind == "organization" and PUBLIC_IDENTIFIER_PATTERN.fullmatch(public_key):
        row = (
            await db.execute(
                select(
                    models.OrganizationPublicSettings.public_identifier, models.Organization.name
                )
                .join(
                    models.Organization,
                    models.Organization.id == models.OrganizationPublicSettings.organization_id,
                )
                .where(
                    models.OrganizationPublicSettings.public_identifier == public_key,
                    models.OrganizationPublicSettings.publication_state == "published",
                    models.Organization.status == "active",
                )
                .limit(1)
            )
        ).one_or_none()
        return (
            None
            if row is None
            else ResolvedPublicSubject(kind, row[0], row[1], f"/community/{row[0]}")
        )
    if kind == "competition" and PUBLIC_COMPETITION_KEY_PATTERN.fullmatch(public_key):
        row = (
            await db.execute(
                select(
                    models.OrganizationCompetitionPublication.public_key,
                    models.Tournament.name,
                    models.OrganizationPublicSettings.public_identifier,
                )
                .join(
                    models.Tournament,
                    models.Tournament.id
                    == models.OrganizationCompetitionPublication.competition_id,
                )
                .join(
                    models.Organization, models.Organization.id == models.Tournament.organization_id
                )
                .join(
                    models.OrganizationPublicSettings,
                    models.OrganizationPublicSettings.organization_id == models.Organization.id,
                )
                .where(
                    models.OrganizationCompetitionPublication.public_key == public_key,
                    models.OrganizationCompetitionPublication.publication_state == "published",
                    models.Organization.status == "active",
                    models.OrganizationPublicSettings.publication_state == "published",
                )
                .limit(1)
            )
        ).one_or_none()
        # The hash is a stable public reference, never the raw tournament identifier.
        return (
            None
            if row is None
            else ResolvedPublicSubject(
                kind, row[0], row[1], f"/community/{row[2]}#competition-{row[0]}"
            )
        )
    if kind == "team" and __import__("re").fullmatch(r"team_[0-9a-f]{24}", public_key):
        row = (
            await db.execute(
                select(models.OrganizationPublicSettings.public_identifier)
                .join(
                    models.OrganizationTeamPublication,
                    models.OrganizationTeamPublication.organization_id
                    == models.OrganizationPublicSettings.organization_id,
                )
                .join(models.Team, models.Team.id == models.OrganizationTeamPublication.team_id)
                .join(
                    models.Organization,
                    models.Organization.id == models.OrganizationTeamPublication.organization_id,
                )
                .where(
                    models.OrganizationTeamPublication.public_identifier == public_key,
                    models.OrganizationTeamPublication.publication_state == "published",
                    models.Team.status == "active",
                    models.OrganizationPublicSettings.publication_state == "published",
                    models.Organization.status == "active",
                )
                .limit(1)
            )
        ).scalar_one_or_none()
        if row is None:
            return None
        # Re-use Team's complete resolver so its own publication and aggregate policy remains authoritative.
        projection = await organization_publication_service.get_public_team(
            db, organization_public_identifier=row, team_public_identifier=public_key
        )
        return (
            None
            if projection is None
            else ResolvedPublicSubject(
                kind,
                public_key,
                str(projection["display_name"]),
                f"/community/{row}/teams/{public_key}",
            )
        )
    return None
