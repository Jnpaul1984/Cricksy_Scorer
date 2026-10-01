"""Anonymous public leaderboards derived from the canonical statistics aggregator.

This projection deliberately never resolves player profiles or roster memberships.  The
only internal values used are frozen match snapshot IDs, and they are discarded before
the response is formed.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.organization_publication import (
    PublicAnonymousLeaderboardEntry,
    PublicAnonymousLeaderboardsResponse,
)
from backend.services import school_statistics_service
from backend.services.organization_entitlement_service import organization_has_capability
from backend.services.organization_service import ACTIVE_ORGANIZATION_STATUS
from backend.sql_app import models

MAX_PUBLIC_LEADERBOARD_ROWS = 10


async def get_public_leaderboards(
    db: AsyncSession, *, organization_id: str
) -> PublicAnonymousLeaderboardsResponse:
    """Return totals from published competitions' completed, final-public games.

    Competition publication is the governing scope.  A scorecard's final-public state
    is required as additional authoritative evidence, but is not used to disclose a
    name or create a player profile.
    """
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
        # Never infer eligibility from a fixture link alone.  Only frozen sides that
        # explicitly declare this organization contribute participant totals.
        game_participant_ids: set[str] = set()
        for side in (game.team_a, game.team_b):
            source_organization_id, _ = school_statistics_service._source(side)
            if source_organization_id == organization_id:
                game_participant_ids.update(school_statistics_service._canonical_xi(side))
        if not game_participant_ids:
            continue
        # Scope IDs before each canonical aggregation. A profile ID that appears in
        # another tenant's frozen snapshot must never make that game's deliveries
        # eligible through a global cross-game participant set.
        game_totals = school_statistics_service._aggregate_players([game], game_participant_ids)
        for profile_id, values in game_totals.items():
            target = totals.setdefault(profile_id, {"runs": 0, "wickets": 0})
            target["runs"] += int(values["runs"])
            target["wickets"] += int(values["wickets"])
    if not totals:
        return PublicAnonymousLeaderboardsResponse(runs=[], wickets=[])
    return PublicAnonymousLeaderboardsResponse(
        runs=_rank(totals, metric="runs"),
        wickets=_rank(totals, metric="wickets"),
    )


def _rank(
    totals: dict[str, dict[str, int]], *, metric: str
) -> list[PublicAnonymousLeaderboardEntry]:
    """Rank by value, with a hidden stable secondary key and no identity output."""
    ordered = sorted(
        (
            (profile_id, int(values[metric]))
            for profile_id, values in totals.items()
            if int(values[metric]) > 0
        ),
        key=lambda item: (-item[1], item[0]),
    )[:MAX_PUBLIC_LEADERBOARD_ROWS]
    entries: list[PublicAnonymousLeaderboardEntry] = []
    previous_value: int | None = None
    previous_rank = 0
    for position, (_, value) in enumerate(ordered, start=1):
        rank = position if previous_value != value else previous_rank
        entries.append(
            PublicAnonymousLeaderboardEntry(
                rank=rank,
                # This position-only label is not a durable player identifier.
                participant_label=f"Participant {position}",
                value=value,
            )
        )
        previous_value, previous_rank = value, rank
    return entries
