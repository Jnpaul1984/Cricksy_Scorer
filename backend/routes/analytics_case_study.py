"""
FastAPI router for Match Case Study analytics.

Exposes:
  GET /analytics/matches
  GET /analytics/matches/{match_id}/case-study
"""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import security
from backend.sql_app.database import get_db
from backend.sql_app.models import Game, GameStatus
from backend.api.schemas.analyst_matches import (
    AnalystMatchListItem,
    AnalystMatchListResponse,
)
from backend.api.schemas.case_study import MatchCaseStudyResponse
from backend.services.analyst_access import scoped_games_stmt
from backend.services.ai_match_summary import MatchAiSummary, build_match_ai_summary
from backend.services.historical_import_delivery_service import cricket_overs_to_legal_balls
from backend.services.analytics_case_study import build_match_case_study

router = APIRouter(
    prefix="/analytics/matches",
    tags=["analytics-case-study"],
)

AllowedRoles = ["analyst_pro", "org_pro"]


def _team_name(team_data: Any, fallback: str) -> str:
    if isinstance(team_data, dict):
        name = team_data.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return fallback


def _compute_run_rate(game: Game) -> float:
    first_runs = 0
    first_overs = 0.0
    if isinstance(game.first_inning_summary, dict):
        first_runs = int(game.first_inning_summary.get("runs") or 0)
        first_overs = cricket_overs_to_legal_balls(game.first_inning_summary.get("overs")) / 6.0
    second_overs = float(game.overs_completed) + (float(game.balls_this_over) / 6.0)
    total_runs = first_runs + int(game.total_runs)
    total_overs = first_overs + second_overs
    if total_overs <= 0:
        return 0.0
    return round(total_runs / total_overs, 2)


def _phase_swing(game: Game) -> str:
    phases = game.phases if isinstance(game.phases, dict) else {}
    for phase_name in ("death", "middle", "powerplay"):
        phase_data = phases.get(phase_name)
        if isinstance(phase_data, dict):
            net = phase_data.get("net_swing_vs_par")
            if isinstance(net, (int, float)):
                direction = "+" if net >= 0 else ""
                return f"{direction}{int(round(net))} in {phase_name}"
    return "n/a"


def _historical_import_meta(game: Game) -> dict[str, Any] | None:
    phases = game.phases if isinstance(game.phases, dict) else {}
    hist = phases.get("historical_import")
    if isinstance(hist, dict) and bool(hist.get("is_historical")):
        return hist
    return None


@router.get("", response_model=AnalystMatchListResponse)
async def list_analyst_matches(
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
):
    """
    Return a list of matches for the Analyst Workspace.
    """
    stmt = scoped_games_stmt(current_user).where(Game.status == GameStatus.completed).order_by(Game.id.desc())
    result = await db.execute(stmt)
    games = result.scalars().all()

    items = []
    for game in games:
        team_a_name = _team_name(game.team_a, "Team A")
        team_b_name = _team_name(game.team_b, "Team B")
        hist_meta = _historical_import_meta(game)
        historical_date = None
        if hist_meta:
            raw_date = hist_meta.get("match_date")
            if isinstance(raw_date, str) and raw_date.strip():
                try:
                    historical_date = date.fromisoformat(raw_date.strip())
                except ValueError:
                    historical_date = None
        created_at = getattr(game, "created_at", None)
        match_date = historical_date or (created_at.date() if created_at else date(1970, 1, 1))
        status_value = game.status.value if hasattr(game.status, "value") else str(game.status)
        items.append(
            AnalystMatchListItem(
                id=game.id,
                date=match_date,
                format=(game.match_type or "custom").upper(),
                teams=f"{team_a_name} vs {team_b_name}",
                result=game.result or "Completed",
                run_rate=_compute_run_rate(game),
                phase_swing=_phase_swing(game),
                status=status_value,
                venue=hist_meta.get("venue") if hist_meta else None,
                event_name=hist_meta.get("event_name") if hist_meta else None,
                season=hist_meta.get("season") if hist_meta else None,
                match_number=hist_meta.get("match_number") if hist_meta else None,
                source_dates=hist_meta.get("source_dates") if hist_meta else [],
                match_datetime=created_at,
                is_historical=bool(hist_meta),
                source="historical_import" if hist_meta else "live",
                historical_batch_id=hist_meta.get("batch_id") if hist_meta else None,
            )
        )

    return AnalystMatchListResponse(items=items, total=len(items))


@router.get("/{match_id}/case-study", response_model=MatchCaseStudyResponse)
async def get_match_case_study(
    match_id: str,
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
):
    """
    Return a full case-study summary for a single match.

    Includes:
    - Match header (date, format, teams, result, innings summary)
    - Momentum summary
    - Key phase identification
    - Phase breakdown (powerplay / middle / death)
    - Key players with impact analysis
    - Dismissal pattern summary
    - AI-generated match summary
    """
    try:
        case_study = await build_match_case_study(
            match_id=match_id,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc) or "Match not found",
        ) from None

    return case_study


@router.get("/{match_id}/ai-summary", response_model=MatchAiSummary)
async def get_match_ai_summary(
    match_id: str,
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
) -> MatchAiSummary:
    """
    Return an AI-generated narrative summary for a match.

    Provides:
    - Headline (1-sentence overview)
    - Narrative (2-4 sentence summary)
    - Tactical themes (phase-based insights)
    - Player highlights (standout performances)
    - Tags (categorical labels)

    This is a rule-based V1 implementation. Future versions will use
    LLM integration for richer, more natural language summaries.
    """
    try:
        return await build_match_ai_summary(
            match_id=match_id,
            user_id=current_user.id,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(exc) or "Match not found",
        ) from None
