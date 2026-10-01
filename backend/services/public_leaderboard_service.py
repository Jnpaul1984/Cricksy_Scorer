"""Anonymous public leaderboards derived from canonical statistics."""

from __future__ import annotations

from backend.api.schemas.organization_publication import (
    PublicAnonymousLeaderboardEntry,
    PublicAnonymousLeaderboardsResponse,
)
from backend.services import school_statistics_service
from backend.services.organization_entitlement_service import organization_has_capability
from backend.services.organization_service import ACTIVE_ORGANIZATION_STATUS
from backend.sql_app import models
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

MAX_PUBLIC_LEADERBOARD_ROWS = 10


async def get_public_leaderboards(
    db: AsyncSession, *, organization_id: str
) -> PublicAnonymousLeaderboardsResponse:
    """Return anonymous totals from published competitions' completed final games."""
    if not await organization_has_capability(
        db, organization_id=organization_id, capability="school_live_scorecards"
    ):
        return PublicAnonymousLeaderboardsResponse(runs=[], wickets=[])

    rows = (
        (
            await db.execute(
                select(models.Game)
                .join(models.Fixture, models.Fixture.game_id == models.Game.id)
                .join(models.Tournament, models.Tournament.id == models.Fixture.tournament_id)
                .join(
                    models.OrganizationCompetitionPublication,
                    models.OrganizationCompetitionPublication.competition_id
                    == models.Tournament.id,
                )
                .join(
                    models.Organization, models.Organization.id == models.Tournament.organization_id
                )
                .where(
                    models.Tournament.organization_id == organization_id,
                    models.OrganizationCompetitionPublication.organization_id == organization_id,
                    models.OrganizationCompetitionPublication.publication_state == "published",
                    models.Organization.status == ACTIVE_ORGANIZATION_STATUS,
                    models.Game.status == models.GameStatus.completed,
                    models.Game.publication_state == "published_final",
                )
                .order_by(models.Game.id)
            )
        )
        .scalars()
        .unique()
        .all()
    )

    totals: dict[str, dict[str, int]] = {}
    for game in rows:
        participant_ids: set[str] = set()
        for side in (game.team_a, game.team_b):
            source_organization_id, _ = school_statistics_service._source(side)
            if source_organization_id == organization_id:
                participant_ids.update(school_statistics_service._canonical_xi(side))
        if not participant_ids:
            continue
        game_totals = school_statistics_service._aggregate_players([game], participant_ids)
        for profile_id, values in game_totals.items():
            target = totals.setdefault(profile_id, {"runs": 0, "wickets": 0})
            target["runs"] += int(values["runs"])
            target["wickets"] += int(values["wickets"])
    if not totals:
        return PublicAnonymousLeaderboardsResponse(runs=[], wickets=[])
    return PublicAnonymousLeaderboardsResponse(
        runs=_rank(totals, metric="runs"), wickets=_rank(totals, metric="wickets")
    )


def _rank(
    totals: dict[str, dict[str, int]], *, metric: str
) -> list[PublicAnonymousLeaderboardEntry]:
    """Rank by value with a hidden stable tie-breaker; never emit an identity."""
    ordered = sorted(
        ((profile_id, int(values[metric])) for profile_id, values in totals.items() if int(values[metric]) > 0),
        key=lambda item: (-item[1], item[0]),
    )[:MAX_PUBLIC_LEADERBOARD_ROWS]
    entries: list[PublicAnonymousLeaderboardEntry] = []
    previous_value: int | None = None
    previous_rank = 0
    for position, (_, value) in enumerate(ordered, start=1):
        rank = position if previous_value != value else previous_rank
        entries.append(
            PublicAnonymousLeaderboardEntry(
                rank=rank, participant_label=f"Participant {position}", value=value
            )
        )
        previous_value, previous_rank = value, rank
    return entries
