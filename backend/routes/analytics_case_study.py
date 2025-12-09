"""
FastAPI router for Match Case Study analytics.

Exposes:
  GET /analytics/matches
  GET /analytics/matches/{match_id}/case-study
"""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status

from backend import security
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


@router.get("", response_model=AnalystMatchListResponse)
async def list_analyst_matches(
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
):
    """
    Return a list of matches for the Analyst Workspace.

    Currently returns mock data for m1 and m2.
    """
    # TODO: Replace with actual database query
    items = [
        AnalystMatchListItem(
            id="m1",
            date=date(2025, 11, 28),
            format="T20",
            teams="Lions vs Falcons",
            result="Lions won by 18 runs",
            run_rate=8.9,
            phase_swing="+22 in death",
        ),
        AnalystMatchListItem(
            id="m2",
            date=date(2025, 11, 25),
            format="T20",
            teams="Tigers vs Eagles",
            result="Eagles won by 4 wickets",
            run_rate=7.9,
            phase_swing="-18 in middle",
        ),
    ]

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
