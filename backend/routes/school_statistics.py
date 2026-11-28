"""Organization-scoped School Free statistics, fixtures, and results routes."""

from __future__ import annotations

import datetime as dt
from typing import Annotated, Never

from backend.api.schemas.organization_team_performance import (
    OrganizationTeamCoachReport,
    OrganizationTeamPerformanceReadiness,
    OrganizationTeamPerformanceResponse,
    OrganizationTeamPerformanceTeamOption,
    OrganizationTeamPhaseAnalysis,
    OrganizationTeamRecentForm,
    TeamPerformanceCoverage,
    TeamPhaseBandResponse,
    TeamRecentFormMatch,
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
    require_team_performance_organization_access,
)
from backend.services.school_team_analytics_service import (
    TeamAnalyticsRequest,
    TeamAnalyticsResult,
    TeamAnalyticsScopeTooLargeError,
    calculate_team_limited_overs_analytics,
)
from backend.services.school_team_readiness_service import (
    TeamReadinessRequest,
    calculate_team_phase_analysis,
    calculate_team_recent_form,
    evaluate_team_match_readiness,
)
from backend.services.school_team_report_service import compose_team_coach_report
from backend.sql_app import models
from backend.sql_app.database import get_db
from backend.sql_app.models import User
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["school-statistics"])

NO_LEDGER_CODES = frozenset({"no_usable_ledger"})


@router.get(
    "/api/organizations/{organization_id}/team-performance/teams",
    response_model=list[OrganizationTeamPerformanceTeamOption],
)
async def list_organization_team_performance_teams(
    organization_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> list[OrganizationTeamPerformanceTeamOption]:
    try:
        await require_team_performance_organization_access(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
        )
    except TeamPerformanceAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc

    rows = (
        await db.execute(
            select(models.Team.id, models.Team.name, models.Team.status)
            .where(models.Team.organization_id == organization_id)
            .order_by(models.Team.name, models.Team.id)
        )
    ).all()
    return [OrganizationTeamPerformanceTeamOption.model_validate(row._mapping) for row in rows]


def _safe_team_performance_response(
    result: TeamAnalyticsResult,
) -> OrganizationTeamPerformanceResponse:
    no_ledger_games: set[str] = set()
    invalid_games: set[str] = set()
    invalid_innings: set[tuple[str, int]] = set()
    cohort_counts = result.cohort_exclusion_counts.copy()
    warnings: dict[str, int] = {}
    for exclusion in result.exclusions:
        reason = exclusion.reason_code
        if reason in NO_LEDGER_CODES:
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
    elif result.exclusions or cohort_counts:
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
        excluded_games=sum(cohort_counts.values()) + len(no_ledger_games | invalid_games),
        excluded_innings=len(invalid_innings),
        cohort_excluded_games=sum(cohort_counts.values()),
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
    except OrganizationCapabilityError as exc:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Team Performance is unavailable",
        ) from exc
    except organization_service.OrganizationServiceError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Organization or Team not found",
        ) from exc
    except school_statistics_service.SchoolStatisticsServiceError as exc:
        response_status = (
            status.HTTP_404_NOT_FOUND
            if exc.status_code == status.HTTP_404_NOT_FOUND
            else status.HTTP_403_FORBIDDEN
        )
        raise HTTPException(
            status_code=response_status,
            detail=(
                "Organization or Team not found"
                if response_status == status.HTTP_404_NOT_FOUND
                else "Team Performance is unavailable"
            ),
        ) from exc
    return _safe_team_performance_response(result)


@router.get(
    "/api/organizations/{organization_id}/team-performance/teams/{team_id}/readiness",
    response_model=OrganizationTeamPerformanceReadiness,
)
async def get_organization_team_performance_readiness(
    organization_id: str,
    team_id: str,
    as_of_date: Annotated[str, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    reference_game_id: str | None = Query(default=None, min_length=1),
) -> OrganizationTeamPerformanceReadiness:
    try:
        parsed_as_of_date = dt.date.fromisoformat(as_of_date)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="as_of_date must be an ISO calendar date"
        ) from exc
    try:
        result = await evaluate_team_match_readiness(
            db,
            TeamReadinessRequest(
                actor_user_id=current_user.id,
                organization_id=organization_id,
                team_id=team_id,
                as_of_date=parsed_as_of_date,
                reference_game_id=reference_game_id,
            ),
        )
    except TeamPerformanceAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    return OrganizationTeamPerformanceReadiness(
        organization_id=result.organization_id,
        team_id=result.team_id,
        as_of_date=result.as_of_date,
        required_history=result.required_history,
        usable_prior_match_count=result.usable_prior_match_count,
        remaining_match_count=result.remaining_match_count,
        state=result.state,
        usable_batting_match_count=result.usable_batting_match_count,
        usable_bowling_match_count=result.usable_bowling_match_count,
        exclusion_counts=result.exclusion_counts,
    )


@router.get(
    "/api/organizations/{organization_id}/team-performance/teams/{team_id}/recent-form",
    response_model=OrganizationTeamRecentForm,
)
async def get_organization_team_recent_form(
    organization_id: str,
    team_id: str,
    as_of_date: Annotated[str, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationTeamRecentForm:
    try:
        boundary = dt.date.fromisoformat(as_of_date)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="as_of_date must be an ISO calendar date"
        ) from exc
    try:
        result = await calculate_team_recent_form(
            db,
            TeamReadinessRequest(
                actor_user_id=current_user.id,
                organization_id=organization_id,
                team_id=team_id,
                as_of_date=boundary,
            ),
        )
    except TeamPerformanceAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    readiness = OrganizationTeamPerformanceReadiness(
        organization_id=result.readiness.organization_id,
        team_id=result.readiness.team_id,
        as_of_date=result.readiness.as_of_date,
        required_history=result.readiness.required_history,
        usable_prior_match_count=result.readiness.usable_prior_match_count,
        remaining_match_count=result.readiness.remaining_match_count,
        state=result.readiness.state,
        usable_batting_match_count=result.readiness.usable_batting_match_count,
        usable_bowling_match_count=result.readiness.usable_bowling_match_count,
        exclusion_counts=result.readiness.exclusion_counts,
    )
    return OrganizationTeamRecentForm(
        readiness=readiness,
        sample_size=len(result.matches),
        recorded_delivery_rows=result.recorded_delivery_rows,
        batting=result.batting,
        bowling=result.bowling,
        matches=[
            TeamRecentFormMatch(
                ordinal=index,
                played_date=match.played_date,
                batting=match.batting,
                bowling=match.bowling,
                recorded_delivery_rows=match.recorded_delivery_rows,
            )
            for index, match in enumerate(result.matches, start=1)
        ],
    )


@router.get(
    "/api/organizations/{organization_id}/team-performance/teams/{team_id}/phases",
    response_model=OrganizationTeamPhaseAnalysis,
)
async def get_organization_team_phase_analysis(
    organization_id: str,
    team_id: str,
    as_of_date: Annotated[str, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationTeamPhaseAnalysis:
    try:
        boundary = dt.date.fromisoformat(as_of_date)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="as_of_date must be an ISO calendar date"
        ) from exc
    try:
        result = await calculate_team_phase_analysis(
            db,
            TeamReadinessRequest(
                actor_user_id=current_user.id,
                organization_id=organization_id,
                team_id=team_id,
                as_of_date=boundary,
            ),
        )
    except TeamPerformanceAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    readiness = OrganizationTeamPerformanceReadiness(
        organization_id=result.readiness.organization_id,
        team_id=result.readiness.team_id,
        as_of_date=result.readiness.as_of_date,
        required_history=result.readiness.required_history,
        usable_prior_match_count=result.readiness.usable_prior_match_count,
        remaining_match_count=result.readiness.remaining_match_count,
        state=result.readiness.state,
        usable_batting_match_count=result.readiness.usable_batting_match_count,
        usable_bowling_match_count=result.readiness.usable_bowling_match_count,
        exclusion_counts=result.readiness.exclusion_counts,
    )
    return OrganizationTeamPhaseAnalysis(
        readiness=readiness,
        sample_size=result.sample_size,
        phase_unavailable_matches=result.phase_unavailable_matches,
        phases=[
            TeamPhaseBandResponse(
                name=phase.name,
                start_over=phase.start_over,
                end_over=phase.end_over,
                batting_observed_matches=phase.batting_observed_matches,
                bowling_observed_matches=phase.bowling_observed_matches,
                batting_unavailable_matches=phase.batting_unavailable_matches,
                bowling_unavailable_matches=phase.bowling_unavailable_matches,
                batting_recorded_rows=phase.batting_recorded_rows,
                bowling_recorded_rows=phase.bowling_recorded_rows,
                batting=phase.batting,
                bowling=phase.bowling,
            )
            for phase in result.phases
        ],
    )


@router.get(
    "/api/organizations/{organization_id}/team-performance/teams/{team_id}/coach-report",
    response_model=OrganizationTeamCoachReport,
)
async def get_organization_team_coach_report(
    organization_id: str,
    team_id: str,
    as_of_date: Annotated[str, Query(pattern=r"^\d{4}-\d{2}-\d{2}$")],
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> OrganizationTeamCoachReport:
    try:
        boundary = dt.date.fromisoformat(as_of_date)
    except ValueError as exc:
        raise HTTPException(
            status_code=422, detail="as_of_date must be an ISO calendar date"
        ) from exc
    try:
        report = await compose_team_coach_report(
            db,
            TeamReadinessRequest(current_user.id, organization_id, team_id, boundary),
        )
    except TeamPerformanceAccessError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc
    readiness = OrganizationTeamPerformanceReadiness(
        organization_id=report.readiness.organization_id,
        team_id=report.readiness.team_id,
        as_of_date=report.readiness.as_of_date,
        required_history=report.readiness.required_history,
        usable_prior_match_count=report.readiness.usable_prior_match_count,
        remaining_match_count=report.readiness.remaining_match_count,
        state=report.readiness.state,
        usable_batting_match_count=report.readiness.usable_batting_match_count,
        usable_bowling_match_count=report.readiness.usable_bowling_match_count,
        exclusion_counts=report.readiness.exclusion_counts,
    )
    form, phases = report.form, report.phases
    return OrganizationTeamCoachReport(
        readiness=readiness,
        sample_size=len(form.matches) if form else 0,
        recorded_delivery_rows=form.recorded_delivery_rows if form else 0,
        batting=form.batting if form else None,
        bowling=form.bowling if form else None,
        matches=[
            TeamRecentFormMatch(
                ordinal=index,
                played_date=match.played_date,
                batting=match.batting,
                bowling=match.bowling,
                recorded_delivery_rows=match.recorded_delivery_rows,
            )
            for index, match in enumerate(form.matches, start=1)
        ]
        if form
        else [],
        phase_unavailable_matches=phases.phase_unavailable_matches if phases else 0,
        phases=[
            TeamPhaseBandResponse(
                name=phase.name,
                start_over=phase.start_over,
                end_over=phase.end_over,
                batting_observed_matches=phase.batting_observed_matches,
                bowling_observed_matches=phase.bowling_observed_matches,
                batting_recorded_rows=phase.batting_recorded_rows,
                bowling_recorded_rows=phase.bowling_recorded_rows,
                batting=phase.batting,
                bowling=phase.bowling,
                batting_unavailable_matches=phase.batting_unavailable_matches,
                bowling_unavailable_matches=phase.bowling_unavailable_matches,
            )
            for phase in phases.phases
        ]
        if phases
        else [],
        observations=[observation.__dict__ for observation in report.observations],
    )
