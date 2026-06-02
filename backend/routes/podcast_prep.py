"""Phase 10T — Podcast Prep Studio: FastAPI routes.

Exposes:
  POST /api/podcast-prep/match          → generate match research pack
  POST /api/podcast-prep/tournament     → generate tournament research pack
  POST /api/podcast-prep/archive        → generate archive research pack
  POST /api/podcast-prep/roster         → generate roster research pack

  POST   /api/podcast-prep/reports      → save report
  GET    /api/podcast-prep/reports      → list reports
  GET    /api/podcast-prep/reports/{id} → get report
  PATCH  /api/podcast-prep/reports/{id} → update report

All generation endpoints:
- Require analyst_pro or org_pro role.
- Are strictly read-only (no match/import data mutated).
- Return deterministic research packs with trust notes.
- Never invent player statistics or official standings.
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend import security
from backend.api.schemas.podcast_prep import (
    ArchivePodcastPackRequest,
    MatchPodcastPackRequest,
    PodcastPrepReportCreate,
    PodcastPrepReportListResponse,
    PodcastPrepReportResponse,
    PodcastPrepReportUpdate,
    PodcastResearchPack,
    RosterPodcastPackRequest,
    TournamentPodcastPackRequest,
)
from backend.services.cpl_roster_service import list_players, list_teams
from backend.services.podcast_prep_service import (
    build_archive_research_pack,
    build_match_research_pack,
    build_roster_research_pack,
    build_tournament_research_pack,
    create_podcast_prep_report,
    get_podcast_prep_report,
    list_podcast_prep_reports,
    update_podcast_prep_report,
)
from backend.sql_app.database import get_db

router = APIRouter(prefix="/api/podcast-prep", tags=["podcast-prep"])

AllowedRoles = ["analyst_pro", "org_pro"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _load_case_study_data(
    match_id: str,
    current_user: Any,
    db: AsyncSession,
) -> dict[str, Any]:
    """Load match case study data for a given match_id.

    Returns a simplified dict derived from the Game record and its
    innings/delivery data. If the match is not found, returns empty dict.
    """
    from backend.services.analytics_case_study import build_match_case_study

    user_id: str | int = str(
        getattr(current_user, "id", None) or getattr(current_user, "user_id", "") or ""
    )
    try:
        case_study = await build_match_case_study(match_id, user_id)
        return case_study.model_dump() if case_study else {}
    except Exception:
        return {}


async def _load_tournament_summary(
    competition_code: str,
    season: str | None,
    gender_category: str,
    current_user: Any,
    db: AsyncSession,
) -> dict[str, Any] | None:
    """Load tournament summary data."""
    from backend.services.tournament_intelligence_service import get_tournament_summary

    result = await get_tournament_summary(
        db, current_user, competition_code, season, gender_category
    )
    if result is None:
        return None
    return result.model_dump()


async def _load_archive_data(
    request: ArchivePodcastPackRequest,
    current_user: Any,
    db: AsyncSession,
) -> dict[str, Any]:
    """Load archive explorer data."""
    from backend.services.tournament_intelligence_service import get_historical_archive_explorer

    result = await get_historical_archive_explorer(
        db=db,
        current_user=current_user,
        competition_code=request.competition_code,
        season_start=request.season_start,
        season_end=request.season_end,
        format_family=request.format_family,
        gender_category=request.gender_category,
        minimum_matches=1,
        include_incomplete=True,
    )
    return result.model_dump()


# ---------------------------------------------------------------------------
# Research pack generation endpoints
# ---------------------------------------------------------------------------


@router.post("/match", response_model=PodcastResearchPack)
async def generate_match_podcast_pack(
    body: MatchPodcastPackRequest,
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
) -> PodcastResearchPack:
    """Generate a deterministic podcast research pack for a single match.

    Derived from imported match data. Trust note always present.
    No invented stats.
    """
    match_data = await _load_case_study_data(body.match_id, current_user, db)
    if not match_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"Match '{body.match_id}' not found or no data available. "
                "Import the match or check the match_id."
            ),
        )
    return build_match_research_pack(body.match_id, match_data)


@router.post("/tournament", response_model=PodcastResearchPack)
async def generate_tournament_podcast_pack(
    body: TournamentPodcastPackRequest,
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
) -> PodcastResearchPack:
    """Generate a deterministic podcast research pack for a tournament/season.

    Derived from tournament intelligence data. Trust note always present.
    Derived standings are labeled non-official.
    """
    summary = await _load_tournament_summary(
        body.competition_code, body.season, body.gender_category, current_user, db
    )
    if summary is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                f"No matches found for competition_code='{body.competition_code}', "
                f"season='{body.season}'. Import match data or adjust parameters."
            ),
        )
    return build_tournament_research_pack(
        body.competition_code, body.season, body.gender_category, summary
    )


@router.post("/archive", response_model=PodcastResearchPack)
async def generate_archive_podcast_pack(
    body: ArchivePodcastPackRequest,
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
) -> PodcastResearchPack:
    """Generate a deterministic podcast research pack from archive comparisons.

    Derived from historical archive explorer data. Trust note always present.
    Champion history labeled as derived — not official trophy records.
    """
    archive_data = await _load_archive_data(body, current_user, db)
    return build_archive_research_pack(archive_data, body)


@router.post("/roster", response_model=PodcastResearchPack)
async def generate_roster_podcast_pack(
    body: RosterPodcastPackRequest,
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
) -> PodcastResearchPack:
    """Generate a podcast research pack from current-season CPL roster data.

    Uses user-maintained roster registry. Trust note always present.
    Player statistics are not available for roster-only entries.
    """
    players_response = await list_players(
        db,
        competition_code=body.competition_code,
        season=body.season,
        team_name=body.team_name,
    )
    teams_response = await list_teams(
        db,
        competition_code=body.competition_code,
        season=body.season,
    )
    return build_roster_research_pack(
        competition_code=body.competition_code,
        season=body.season,
        team_name=body.team_name,
        players=[p.model_dump() for p in players_response.players],
        teams=[t.model_dump() for t in teams_response.teams],
    )


# ---------------------------------------------------------------------------
# Saved report endpoints
# ---------------------------------------------------------------------------


@router.post("/reports", response_model=PodcastPrepReportResponse, status_code=201)
async def save_podcast_prep_report(
    body: PodcastPrepReportCreate,
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
) -> PodcastPrepReportResponse:
    """Save a new podcast prep report."""
    user_id = getattr(current_user, "id", None) or getattr(current_user, "sub", None)
    report = await create_podcast_prep_report(db, body, created_by_id=user_id)
    return PodcastPrepReportResponse.model_validate(report)


@router.get("/reports", response_model=PodcastPrepReportListResponse)
async def get_podcast_prep_reports(
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
    topic_type: str | None = Query(None),
    report_status: str | None = Query(None, alias="status"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
) -> PodcastPrepReportListResponse:
    """List saved podcast prep reports (scoped to current user)."""
    user_id = getattr(current_user, "id", None) or getattr(current_user, "sub", None)
    reports, total = await list_podcast_prep_reports(
        db,
        created_by_id=user_id,
        topic_type=topic_type,
        status=report_status,
        limit=limit,
        offset=offset,
    )
    return PodcastPrepReportListResponse(
        reports=[PodcastPrepReportResponse.model_validate(r) for r in reports],
        total=total,
    )


@router.get("/reports/{report_id}", response_model=PodcastPrepReportResponse)
async def get_podcast_prep_report_endpoint(
    report_id: str,
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
) -> PodcastPrepReportResponse:
    """Get a single saved podcast prep report by ID."""
    report = await get_podcast_prep_report(db, report_id)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Podcast prep report '{report_id}' not found.",
        )
    return PodcastPrepReportResponse.model_validate(report)


@router.patch("/reports/{report_id}", response_model=PodcastPrepReportResponse)
async def update_podcast_prep_report_endpoint(
    report_id: str,
    body: PodcastPrepReportUpdate,
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
) -> PodcastPrepReportResponse:
    """Update an existing saved podcast prep report."""
    report = await update_podcast_prep_report(db, report_id, body)
    if report is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Podcast prep report '{report_id}' not found.",
        )
    return PodcastPrepReportResponse.model_validate(report)
