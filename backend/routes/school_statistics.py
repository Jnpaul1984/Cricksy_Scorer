"""Organization-scoped School Free statistics, fixtures, and results routes."""

from __future__ import annotations

from typing import Annotated, Never

from backend.api.schemas.organization_team_performance import (
    OrganizationTeamPerformanceResponse,
    TeamPerformanceCoverage,
)
from backend.api.schemas.school_statistics import (
    SchoolFixtureSummary,
    SchoolMatchResult,
    SchoolPlayerStatistics,
    SchoolTeamStatistics,
)
from backend.security import get_current_active_user
from backend.services import organization_service, school_statistics_service
from backend.services.organization_entitlement_service import OrganizationCapabilityError
from backend.services.organization_team_performance_access import (
    TeamPerformanceAccessError,
    require_team_performance_access,
)
from backend.services.school_team_analytics_service import (
    TeamAnalyticsRequest,
    TeamAnalyticsResult,
    TeamAnalyticsScopeTooLargeError,
    calculate_team_limited_overs_analytics,
)
from backend.sql_app.database import get_db
from backend.sql_app.models import User
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["school-statistics"])

COHORT_EXCLUSION_CODES = frozenset(
    {
        "non_official_match",
        "not_completed",
        "unsupported_match_type",
        "overs_limit_mismatch",
        "multi_day_match",
        "unsupported_match_rules",
    }
)
NO_LEDGER_CODES = frozenset({"no_usable_ledger"})


def _safe_team_performance_response(
    result: TeamAnalyticsResult,
) -> OrganizationTeamPerformanceResponse:
    cohort_games: set[str] = set()
    no_ledger_games: set[str] = set()
    invalid_games: set[str] = set()
    invalid_innings: set[tuple[str, int]] = set()
    cohort_counts: dict[str, int] = {}
    warnings: dict[str, int] = {}
    for exclusion in result.exclusions:
        reason = exclusion.reason_code
        if reason in COHORT_EXCLUSION_CODES:
            cohort_games.add(exclusion.game_id)
            cohort_counts[reason] = cohort_counts.get(reason, 0) + 1
        elif reason in NO_LEDGER_CODES:
            no_ledger_games.add(exclusion.game_id)
        elif exclusion.innings_number is None:
            invalid_games.add(exclusion.game_id)
            warnings[reason] = warnings.get(reason, 0) + 1
        else:
            invalid_innings.add((exclusion.game_id, exclusion.innings_number))
            warnings[reason] = warnings.get(reason, 0) + 1

    invalid_games.update(game_id for game_id, _ in invalid_innings)
    if result.eligible_match_count == 0:
        coverage_status = "no_eligible_games"
    elif result.included_innings_count == 0:
        coverage_status = "no_usable_ledger"
    elif result.exclusions:
        coverage_status = "usable_with_exclusions"
    else:
        coverage_status = "usable_recorded_data"
    coverage = TeamPerformanceCoverage(
        status=coverage_status,
        eligible_games=result.eligible_match_count,
        included_games=result.included_match_count,
        usable_batting_innings=sum(
            item.team_role == "batting" for item in result.innings_attribution
        ),
        usable_bowling_innings=sum(
            item.team_role == "bowling" for item in result.innings_attribution
        ),
        used_delivery_rows=result.included_delivery_count,
        observed_delivery_rows=result.observed_delivery_count,
        excluded_games=len(cohort_games | no_ledger_games | invalid_games),
        excluded_innings=len(invalid_innings),
        cohort_excluded_games=len(cohort_games),
        cohort_exclusion_counts=cohort_counts,
        no_ledger_games=len(no_ledger_games),
        invalid_data_games=len(invalid_games),
        invalid_data_innings=len(invalid_innings),
        warning_counts=warnings,
    )
    return OrganizationTeamPerformanceResponse(
        organization_id=result.organization_id,
        team_id=result.team_id,
        overs_limit=result.overs_limit,
        completeness=result.completeness,
        batting=result.batting,
        bowling=result.bowling,
        coverage=coverage,
    )


def _raise_service_error(exc: Exception) -> Never:
    if isinstance(exc, OrganizationCapabilityError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Organization capability not enabled: {exc.capability}",
        ) from exc
    if isinstance(
        exc,
        organization_service.OrganizationServiceError
        | school_statistics_service.SchoolStatisticsServiceError,
    ):
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    raise exc


SERVICE_ERRORS = (
    organization_service.OrganizationServiceError,
    school_statistics_service.SchoolStatisticsServiceError,
    OrganizationCapabilityError,
)


@router.get(
    "/api/organizations/{organization_id}/statistics/players",
    response_model=list[SchoolPlayerStatistics],
)
async def list_player_statistics(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SchoolPlayerStatistics]:
    try:
        return await school_statistics_service.player_statistics(
            db, organization_id=organization_id, actor_user_id=current_user.id
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.get(
    "/api/organizations/{organization_id}/statistics/players/{player_profile_id}",
    response_model=SchoolPlayerStatistics,
)
async def get_player_statistics(
    organization_id: str,
    player_profile_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SchoolPlayerStatistics:
    try:
        rows = await school_statistics_service.player_statistics(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            player_profile_id=player_profile_id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return rows[0]


@router.get(
    "/api/organizations/{organization_id}/statistics/teams",
    response_model=list[SchoolTeamStatistics],
)
async def list_team_statistics(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SchoolTeamStatistics]:
    try:
        return await school_statistics_service.team_statistics(
            db, organization_id=organization_id, actor_user_id=current_user.id
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.get(
    "/api/organizations/{organization_id}/statistics/teams/{team_id}",
    response_model=SchoolTeamStatistics,
)
async def get_team_statistics(
    organization_id: str,
    team_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SchoolTeamStatistics:
    try:
        rows = await school_statistics_service.team_statistics(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            team_id=team_id,
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)
    return rows[0]


@router.get(
    "/api/organizations/{organization_id}/results",
    response_model=list[SchoolMatchResult],
)
async def list_results(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SchoolMatchResult]:
    try:
        return await school_statistics_service.match_results(
            db, organization_id=organization_id, actor_user_id=current_user.id
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.get(
    "/api/organizations/{organization_id}/fixtures",
    response_model=list[SchoolFixtureSummary],
)
async def list_fixtures(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[SchoolFixtureSummary]:
    try:
        return await school_statistics_service.fixture_summaries(
            db, organization_id=organization_id, actor_user_id=current_user.id
        )
    except SERVICE_ERRORS as exc:
        _raise_service_error(exc)


@router.get(
    "/api/organizations/{organization_id}/team-performance/teams/{team_id}",
    response_model=OrganizationTeamPerformanceResponse,
)
async def get_organization_team_performance(
    organization_id: str,
    team_id: str,
    overs_limit: Annotated[int, Query(ge=1, le=120)],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationTeamPerformanceResponse:
    try:
        await require_team_performance_access(
            db,
            organization_id=organization_id,
            team_id=team_id,
            actor_user_id=current_user.id,
        )
        result = await calculate_team_limited_overs_analytics(
            db,
            TeamAnalyticsRequest(
                actor_user_id=current_user.id,
                organization_id=organization_id,
                team_id=team_id,
                overs_limit=overs_limit,
            ),
        )
    except TeamPerformanceAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    except TeamAnalyticsScopeTooLargeError as exc:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="Selected Team Performance scope is too large; narrow the selected format.",
        ) from exc
    return _safe_team_performance_response(result)
