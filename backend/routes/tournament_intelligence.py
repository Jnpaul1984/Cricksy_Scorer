"""Phase 10S.1 / 10S.2 — Tournament Intelligence: read-only REST endpoints.

Exposes:
  GET /analytics/tournament-intelligence/groups
      Lists all discoverable tournament/season groups from the historical archive.

  GET /analytics/tournament-intelligence/summary
      Returns a full tournament intelligence summary for a specified group.

  GET /analytics/tournament-intelligence/team-journey
      Returns a team's journey within a competition/season.

  GET /analytics/tournament-intelligence/podcast-rundown
      Returns a deterministic tournament podcast rundown (Phase 10S.2).

All endpoints:
  - Require analyst_pro or org_pro role.
  - Apply org-scoping (users see only their own or org-scoped matches).
  - Are strictly read-only — no Game or batch fields are mutated.
  - Return deterministic, clearly labeled derived intelligence.
  - Never fabricate official standings or championship claims.

No LLM/AI services, DLS logic, or live scoring truth are touched.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status

from backend import security
from backend.api.schemas.tournament_intelligence import (
    HistoricalArchiveExplorerResponse,
    TeamJourneyResponse,
    TournamentGroupsResponse,
    TournamentPodcastRundown,
    TournamentSummaryResponse,
)
from backend.services.tournament_intelligence_service import (
    get_team_journey,
    get_historical_archive_explorer,
    get_tournament_groups,
    get_tournament_podcast_rundown,
    get_tournament_summary,
)
from backend.sql_app.database import get_db as _base_get_db
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(
    prefix="/analytics/tournament-intelligence",
    tags=["tournament-intelligence"],
)

AllowedRoles = ["analyst_pro", "org_pro"]


async def _get_ti_db() -> AsyncGenerator[AsyncSession, None]:
    """Real DB dependency for tournament intelligence.

    Defined as a local dependency so that FastAPI's in-memory override
    in tests does NOT replace it. Mirrors the pattern in historical_stats.py.
    """
    async for db in _base_get_db():
        yield db


@router.get("/groups", response_model=TournamentGroupsResponse)
async def list_tournament_groups(
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(_get_ti_db),
) -> TournamentGroupsResponse:
    """Return all discoverable tournament/season groups from the historical archive.

    Phase 10S.1: on-demand grouping across all eligible historical matches.

    Groups are keyed by:
    - competition_code (from Phase 10S classification)
    - competition_name (canonical label)
    - season (from match metadata or derived from match date)
    - gender_category
    - format_family (T20 / ODI / TEST / unknown)

    Matches with incomplete classification appear in 'unknown' groups.
    Returns an empty groups list if no eligible matches are found.
    """
    return await get_tournament_groups(db, current_user)


@router.get("/summary", response_model=TournamentSummaryResponse)
async def get_tournament_summary_endpoint(
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(_get_ti_db),
    competition_code: str = Query(
        ..., description="Competition code, e.g. CPL_MEN, WCPL, ONE_DAY_CUP"
    ),
    season: str | None = Query(None, description="Season label, e.g. 2023 or '2023/24'"),
    gender_category: str = Query("unknown", description="Gender: men | women | mixed | unknown"),
) -> TournamentSummaryResponse:
    """Return a full tournament intelligence summary for a specific group.

    Phase 10S.1: on-demand aggregation for one competition/season/gender group.

    Returned data includes:
    - Match counts, teams, venues
    - Run/wicket aggregates
    - Highest/lowest team totals (where available)
    - Biggest wins and closest matches
    - Top run scorer and wicket taker (where delivery data exists)
    - Derived standings table (non-official, estimated)
    - Knockout/finals context (from Phase 10O detection where available)
    - Data completeness summary and confidence labels
    - Podcast-ready talking-point facts

    Returns 404 if no matches are found for the specified group.
    No official cricket standings or championship data are mutated.
    """
    result = await get_tournament_summary(
        db, current_user, competition_code, season, gender_category
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No eligible matches found for competition_code='{competition_code}', "
                f"season='{season}', gender_category='{gender_category}'. "
                "Import historical matches or adjust the filter parameters."
            ),
        )
    return result


@router.get("/team-journey", response_model=TeamJourneyResponse)
async def get_team_journey_endpoint(
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(_get_ti_db),
    competition_code: str = Query(..., description="Competition code"),
    season: str | None = Query(None, description="Season label"),
    gender_category: str = Query("unknown", description="Gender category"),
    team_name: str = Query(..., description="Team name as it appears in match data"),
) -> TeamJourneyResponse:
    """Return a team's tournament journey within a competition/season.

    Phase 10S.1: team-specific journey view for analyst/podcast preparation.

    Returns:
    - Match list in date order
    - Win/loss/tie/no-result breakdown
    - Runs for/against
    - Key match highlights: best win, worst defeat, closest match
    - Top player contributions (where delivery data exists)

    Returns 404 if no matches are found for the specified team/group combination.
    """
    result = await get_team_journey(
        db, current_user, competition_code, season, gender_category, team_name
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No eligible matches found for team='{team_name}' in "
                f"competition_code='{competition_code}', season='{season}'."
            ),
        )
    return result


@router.get("/podcast-rundown", response_model=TournamentPodcastRundown)
async def get_tournament_podcast_rundown_endpoint(
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(_get_ti_db),
    competition_code: str = Query(
        ..., description="Competition code, e.g. CPL_MEN, WCPL, ONE_DAY_CUP"
    ),
    season: str | None = Query(None, description="Season label, e.g. 2023 or '2023/24'"),
    gender_category: str = Query("unknown", description="Gender: men | women | mixed | unknown"),
) -> TournamentPodcastRundown:
    """Return a deterministic tournament podcast rundown for a specific group.

    Phase 10S.2: presenter-ready tournament narrative sections derived from the
    same deterministic tournament summary data as the /summary endpoint.

    Returned data includes:
    - Season review narrative
    - Champion journey block (when champion data exists)
    - Road-to-final block (when finalist context exists)
    - Ordered podcast rundown sections:
        opening_hook, tournament_setup, champion_story, final_context,
        standings_story, team_spotlight, key_matches, player_storylines,
        venue_patterns, tactical_themes, debate_questions, data_trust_note
    - Overall confidence label
    - Source/trust note

    All values are derived from imported match data and labeled with their
    derivation source. No official standings or championship claims are fabricated.

    Returns 404 if no matches are found for the specified group.
    """
    result = await get_tournament_podcast_rundown(
        db, current_user, competition_code, season, gender_category
    )
    if result is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No eligible matches found for competition_code='{competition_code}', "
                f"season='{season}', gender_category='{gender_category}'. "
                "Import historical matches or adjust the filter parameters."
            ),
        )
    return result


@router.get("/archive-explorer", response_model=HistoricalArchiveExplorerResponse)
async def get_historical_archive_explorer_endpoint(
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(_get_ti_db),
    competition_code: str | None = Query(None, description="Optional competition code filter"),
    season_start: int | None = Query(None, description="Optional inclusive season-year start"),
    season_end: int | None = Query(None, description="Optional inclusive season-year end"),
    format_family: str | None = Query(None, description="Optional format filter: T20 | ODI | TEST"),
    gender_category: str | None = Query(
        None, description="Optional gender filter: men | women | mixed | unknown"
    ),
    minimum_matches: int = Query(1, ge=1, description="Minimum matches required per season row"),
    include_incomplete: bool = Query(
        True, description="Whether to keep seasons with incomplete result coverage"
    ),
) -> HistoricalArchiveExplorerResponse:
    """Return archive-level historical comparisons across imported tournament seasons.

    Phase 10S.3: deterministic, read-only archive explorer for analyst research,
    champion history, era comparisons, venue trends, and podcast-ready copy.

    All values are derived from imported match data and explicitly marked as
    non-official. Wicket trends use delivery-derived dismissal records only
    where available.
    """
    return await get_historical_archive_explorer(
        db=db,
        current_user=current_user,
        competition_code=competition_code,
        season_start=season_start,
        season_end=season_end,
        format_family=format_family,
        gender_category=gender_category,
        minimum_matches=minimum_matches,
        include_incomplete=include_incomplete,
    )
