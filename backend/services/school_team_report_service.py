"""Private deterministic composition of the same five-match Team evidence."""

from __future__ import annotations

from dataclasses import dataclass, replace
from typing import Literal

from backend.api.schemas.organization_team_performance import (
    OrganizationTeamCoachReport,
    OrganizationTeamPerformanceReadiness,
    TeamCoachReportObservation,
    TeamPhaseBandResponse,
    TeamRecentFormMatch,
)
from backend.services.school_team_readiness_service import (
    TeamPhaseResult,
    TeamReadinessRequest,
    TeamReadinessResult,
    TeamRecentFormResult,
    calculate_team_phase_analysis,
    calculate_team_recent_form,
    evaluate_team_match_readiness,
)
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class ReportObservation:
    subject: Literal["batting", "bowling"]
    earlier_band: str
    later_band: str
    earlier_rate: float
    later_rate: float
    earlier_runs: int
    later_runs: int
    earlier_legal_balls: int
    later_legal_balls: int
    observed_matches: int
    unit: Literal["runs_per_six_legal_balls"] = "runs_per_six_legal_balls"
    evidence_section: Literal["phases"] = "phases"


@dataclass(frozen=True)
class TeamCoachReportResult:
    readiness: TeamReadinessResult
    form: TeamRecentFormResult | None
    phases: TeamPhaseResult | None
    observations: tuple[ReportObservation, ...]


def _observations(phases: TeamPhaseResult) -> tuple[ReportObservation, ...]:
    """Only compare adjacent bands with equal observed match coverage and defined rates."""
    results: list[ReportObservation] = []
    subjects: tuple[Literal["batting", "bowling"], ...] = ("batting", "bowling")
    for earlier, later in zip(phases.phases, phases.phases[1:], strict=False):
        for subject in subjects:
            before = getattr(earlier, subject)
            after = getattr(later, subject)
            count_before = getattr(earlier, f"{subject}_observed_matches")
            count_after = getattr(later, f"{subject}_observed_matches")
            before_sources = getattr(earlier, f"{subject}_source_games")
            after_sources = getattr(later, f"{subject}_source_games")
            if (
                before is None
                or after is None
                or count_before != count_after
                or count_before == 0
                or before_sources != after_sources
                or len(before_sources) != count_before
            ):
                continue
            if subject == "batting":
                before_runs, after_runs = before["team_runs"], after["team_runs"]
            else:
                before_runs = before["opposition_team_runs"]
                after_runs = after["opposition_team_runs"]
            before_balls, after_balls = before["legal_balls"], after["legal_balls"]
            if before_balls == 0 or after_balls == 0:
                continue
            # Cross multiplication prevents rounding from manufacturing a difference.
            if before_runs * after_balls == after_runs * before_balls:
                continue
            earlier_rate = round(before_runs * 6 / before_balls, 2)
            later_rate = round(after_runs * 6 / after_balls, 2)
            if earlier_rate == later_rate:
                continue
            results.append(
                ReportObservation(
                    subject=subject,
                    earlier_band=earlier.name,
                    later_band=later.name,
                    earlier_rate=earlier_rate,
                    later_rate=later_rate,
                    earlier_runs=before_runs,
                    later_runs=after_runs,
                    earlier_legal_balls=before_balls,
                    later_legal_balls=after_balls,
                    observed_matches=count_before,
                )
            )
    return tuple(results)


async def compose_team_coach_report(
    db: AsyncSession, request: TeamReadinessRequest
) -> TeamCoachReportResult:
    form = await calculate_team_recent_form(db, request)
    if form.readiness.state != "ready":
        return TeamCoachReportResult(form.readiness, None, None, ())
    phases = await calculate_team_phase_analysis(db, request, recent_form=form)
    current = await evaluate_team_match_readiness(db, request)
    if (
        phases.readiness.state != "ready"
        or phases.readiness != form.readiness
        or current != form.readiness
        or len(form.matches) != 5
        or phases.sample_size != 5
    ):
        unavailable = replace(form.readiness, state="data_unavailable", selected_sources=())
        return TeamCoachReportResult(unavailable, None, None, ())
    return TeamCoachReportResult(form.readiness, form, phases, _observations(phases))


def safe_coach_report_response(report: TeamCoachReportResult) -> OrganizationTeamCoachReport:
    """Serialize only the approved aggregate fields, without internal Game identities."""
    readiness = report.readiness
    form, phases = report.form, report.phases
    return OrganizationTeamCoachReport(
        readiness=OrganizationTeamPerformanceReadiness(
            organization_id=readiness.organization_id,
            team_id=readiness.team_id,
            as_of_date=readiness.as_of_date,
            required_history=readiness.required_history,
            usable_prior_match_count=readiness.usable_prior_match_count,
            remaining_match_count=readiness.remaining_match_count,
            state=readiness.state,
            usable_batting_match_count=readiness.usable_batting_match_count,
            usable_bowling_match_count=readiness.usable_bowling_match_count,
            exclusion_counts=readiness.exclusion_counts,
        ),
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
                batting_unavailable_matches=phase.batting_unavailable_matches,
                bowling_unavailable_matches=phase.bowling_unavailable_matches,
                batting_recorded_rows=phase.batting_recorded_rows,
                bowling_recorded_rows=phase.bowling_recorded_rows,
                batting=phase.batting,
                bowling=phase.bowling,
            )
            for phase in phases.phases
        ]
        if phases
        else [],
        observations=[
            TeamCoachReportObservation.model_validate(item.__dict__) for item in report.observations
        ],
    )
