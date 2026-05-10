"""
FastAPI router for Match Case Study analytics.

Exposes:
  GET /analytics/matches
  GET /analytics/matches/{match_id}/case-study
"""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import Select, and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import security
from backend.sql_app.database import get_db
from backend.sql_app.models import Game, GameStatus, User
from backend.api.schemas.analyst_matches import (
    AnalystMatchListItem,
    AnalystMatchListResponse,
)
from backend.api.schemas.case_study import MatchCaseStudyResponse
from backend.services.ai_match_summary import MatchAiSummary, build_match_ai_summary
from backend.services.analytics_case_study import build_match_case_study

router = APIRouter(
    prefix="/analytics/matches",
    tags=["analytics-case-study"],
)

AllowedRoles = ["analyst_pro", "org_pro"]


def _match_access_clause(current_user: Any):
    role_value = getattr(getattr(current_user, "role", None), "value", getattr(current_user, "role", None))
    user_id = str(current_user.id)
    org_id = getattr(current_user, "org_id", None)
    if org_id:
        org_clause = and_(Game.created_by_user_id.isnot(None), User.org_id == str(org_id))
        if role_value == "org_pro":
            return or_(Game.created_by_user_id == user_id, org_clause)
        return org_clause
    return Game.created_by_user_id == user_id


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
        first_overs = float(game.first_inning_summary.get("overs") or 0.0)
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


def _apply_match_query_scope(stmt: Select[Any], current_user: Any) -> Select[Any]:
    return stmt.outerjoin(User, User.id == Game.created_by_user_id).where(_match_access_clause(current_user))


@router.get("", response_model=AnalystMatchListResponse)
async def list_analyst_matches(
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
):
    """
    Return a list of matches for the Analyst Workspace.
    """
    stmt = _apply_match_query_scope(
        select(Game).where(Game.status == GameStatus.completed).order_by(Game.id.desc()),
        current_user,
    )
    result = await db.execute(stmt)
    games = result.scalars().all()

    items = []
    for game in games:
        team_a_name = _team_name(game.team_a, "Team A")
        team_b_name = _team_name(game.team_b, "Team B")
        created_at = getattr(game, "created_at", None)
        match_date = created_at.date() if created_at else date.today()
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
                venue=None,
                match_datetime=created_at,
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
