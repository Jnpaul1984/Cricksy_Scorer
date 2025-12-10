from __future__ import annotations

import csv
import datetime as dt
import io
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from backend import security
from backend.sql_app.database import get_db
from backend.sql_app.models import (
    CoachingSession,
    Game,
    PlayerForm,
    PlayerProfile,
    PlayerSummary,
)
from backend.sql_app.schemas import AnalyticsQuery, AnalyticsResult
from backend.sql_app.match_ai import MatchAiSummaryResponse
from backend.services.match_ai_service import MatchAiService
from backend.services.match_context_service import (
    generate_match_context_package,
    MatchContextPackage,
)

router = APIRouter(prefix="/api/analyst", tags=["analyst_pro"])

AllowedRoles = ["analyst_pro", "org_pro"]
UTC = getattr(dt, "UTC", dt.UTC)


def _serialize_value(value: Any) -> Any:
    if isinstance(value, (dt.datetime, dt.date)):
        return value.isoformat()
    return value


def _csv_response(
    rows: list[dict[str, Any]],
    headers: list[str],
    filename: str,
) -> StreamingResponse:
    buffer = io.StringIO()
    writer = csv.DictWriter(buffer, fieldnames=headers)
    writer.writeheader()
    for row in rows:
        writer.writerow({header: _serialize_value(row.get(header, "")) for header in headers})
    buffer.seek(0)
    response = StreamingResponse(iter([buffer.getvalue()]), media_type="text/csv")
    response.headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


def _format_export(
    rows: list[dict[str, Any]],
    headers: list[str],
    export_format: Literal["json", "csv"],
    filename: str,
):
    if export_format == "csv":
        return _csv_response(rows, headers, filename)
    return [{key: _serialize_value(value) for key, value in row.items()} for row in rows]


@router.get("/players/export")
async def export_players(
    _current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    export_format: Literal["json", "csv"] = Query("json", alias="format"),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(PlayerProfile)
        .options(joinedload(PlayerProfile.summary))
        .order_by(PlayerProfile.player_name)
    )
    result = await db.execute(stmt)
    profiles = result.scalars().all()
    rows: list[dict[str, Any]] = []
    for profile in profiles:
        summary = profile.summary
        rows.append(
            {
                "player_id": profile.player_id,
                "player_name": profile.player_name,
                "total_matches": summary.total_matches if summary else None,
                "total_runs": summary.total_runs if summary else None,
                "total_wickets": summary.total_wickets if summary else None,
                "batting_average": summary.batting_average if summary else None,
                "strike_rate": summary.strike_rate if summary else None,
                "bowling_average": summary.bowling_average if summary else None,
            }
        )
    headers = [
        "player_id",
        "player_name",
        "total_matches",
        "total_runs",
        "total_wickets",
        "batting_average",
        "strike_rate",
        "bowling_average",
    ]
    return _format_export(rows, headers, export_format, "players_export.csv")


@router.get("/matches/export")
async def export_matches(
    _current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    export_format: Literal["json", "csv"] = Query("json", alias="format"),
    db: AsyncSession = Depends(get_db),
):
    stmt = select(Game).order_by(Game.id)
    result = await db.execute(stmt)
    games = result.scalars().all()

    rows: list[dict[str, Any]] = []
    for game in games:
        team_a_name = game.team_a.get("name") if isinstance(game.team_a, dict) else None
        team_b_name = game.team_b.get("name") if isinstance(game.team_b, dict) else None
        rows.append(
            {
                "game_id": game.id,
                "match_type": game.match_type,
                "status": (game.status.value if hasattr(game.status, "value") else game.status),
                "team_a": team_a_name,
                "team_b": team_b_name,
                "overs_limit": game.overs_limit,
                "days_limit": game.days_limit,
                "toss_winner": game.toss_winner_team,
                "decision": game.decision,
                "result": game.result,
            }
        )
    headers = [
        "game_id",
        "match_type",
        "status",
        "team_a",
        "team_b",
        "overs_limit",
        "days_limit",
        "toss_winner",
        "decision",
        "result",
    ]
    return _format_export(rows, headers, export_format, "matches_export.csv")


@router.get("/player-form/export")
async def export_player_form(
    _current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    export_format: Literal["json", "csv"] = Query("json", alias="format"),
    db: AsyncSession = Depends(get_db),
):
    stmt = (
        select(PlayerForm, PlayerProfile.player_name)
        .join(PlayerProfile, PlayerProfile.player_id == PlayerForm.player_id)
        .order_by(PlayerForm.period_end.desc())
    )
    result = await db.execute(stmt)
    rows: list[dict[str, Any]] = []
    for form_entry, player_name in result.all():
        rows.append(
            {
                "form_id": form_entry.id,
                "player_id": form_entry.player_id,
                "player_name": player_name,
                "period_start": form_entry.period_start,
                "period_end": form_entry.period_end,
                "matches_played": form_entry.matches_played,
                "runs": form_entry.runs,
                "wickets": form_entry.wickets,
                "batting_average": form_entry.batting_average,
                "strike_rate": form_entry.strike_rate,
                "economy": form_entry.economy,
                "form_score": form_entry.form_score,
            }
        )
    headers = [
        "form_id",
        "player_id",
        "player_name",
        "period_start",
        "period_end",
        "matches_played",
        "runs",
        "wickets",
        "batting_average",
        "strike_rate",
        "economy",
        "form_score",
    ]
    return _format_export(rows, headers, export_format, "player_form_export.csv")


async def _scalar(db: AsyncSession, stmt):
    result = await db.execute(stmt)
    return result.scalar() or 0


def _apply_form_filters(stmt, query: AnalyticsQuery):
    if query.player_id:
        stmt = stmt.where(PlayerForm.player_id == query.player_id)
    if query.from_date:
        stmt = stmt.where(PlayerForm.period_end >= query.from_date)
    if query.to_date:
        stmt = stmt.where(PlayerForm.period_start <= query.to_date)
    return stmt


def _apply_session_filters(stmt, query: AnalyticsQuery):
    if query.player_id:
        stmt = stmt.where(CoachingSession.player_profile_id == query.player_id)
    if query.from_date:
        start_dt = dt.datetime.combine(query.from_date, dt.time.min, tzinfo=UTC)
        stmt = stmt.where(CoachingSession.scheduled_at >= start_dt)
    if query.to_date:
        end_dt = dt.datetime.combine(query.to_date, dt.time.max, tzinfo=UTC)
        stmt = stmt.where(CoachingSession.scheduled_at <= end_dt)
    return stmt


@router.post("/query", response_model=AnalyticsResult)
async def run_analytics_query(
    query: AnalyticsQuery,
    _current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
) -> AnalyticsResult:
    summary_stats: dict[str, Any] = {}
    sample_rows: list[dict[str, Any]] = []

    if query.entity == "players":
        total_players = await _scalar(db, select(func.count(PlayerProfile.player_id)))
        total_summaries = await _scalar(db, select(func.count(PlayerSummary.id)))
        sample_result = await db.execute(
            select(PlayerProfile).order_by(PlayerProfile.player_name).limit(20)
        )
        sample_rows = [
            {"player_id": profile.player_id, "player_name": profile.player_name}
            for profile in sample_result.scalars().all()
        ]
        summary_stats = {
            "player_count": total_players,
            "summary_count": total_summaries,
        }
    elif query.entity == "matches":
        total_games = await _scalar(db, select(func.count(Game.id)))
        sample_result = await db.execute(select(Game).order_by(Game.id).limit(20))
        sample_rows = [
            {
                "game_id": game.id,
                "team_a": (game.team_a.get("name") if isinstance(game.team_a, dict) else None),
                "team_b": (game.team_b.get("name") if isinstance(game.team_b, dict) else None),
                "status": (game.status.value if hasattr(game.status, "value") else game.status),
            }
            for game in sample_result.scalars().all()
        ]
        summary_stats = {"match_count": total_games}
    elif query.entity == "form":
        count_stmt = _apply_form_filters(select(func.count(PlayerForm.id)), query)
        runs_stmt = _apply_form_filters(select(func.coalesce(func.sum(PlayerForm.runs), 0)), query)
        wickets_stmt = _apply_form_filters(
            select(func.coalesce(func.sum(PlayerForm.wickets), 0)), query
        )
        total_form = await _scalar(db, count_stmt)
        total_runs = await _scalar(db, runs_stmt)
        total_wickets = await _scalar(db, wickets_stmt)
        sample_result = await db.execute(
            _apply_form_filters(
                select(PlayerForm, PlayerProfile.player_name)
                .join(PlayerProfile, PlayerProfile.player_id == PlayerForm.player_id)
                .order_by(PlayerForm.period_end.desc())
                .limit(20),
                query,
            )
        )
        sample_rows = [
            {
                "player_id": form.player_id,
                "player_name": player_name,
                "period_start": form.period_start.isoformat(),
                "period_end": form.period_end.isoformat(),
                "runs": form.runs,
                "wickets": form.wickets,
            }
            for form, player_name in sample_result.all()
        ]
        summary_stats = {
            "form_entries": total_form,
            "total_runs": total_runs,
            "total_wickets": total_wickets,
        }
    elif query.entity == "sessions":
        count_stmt = _apply_session_filters(select(func.count(CoachingSession.id)), query)
        duration_stmt = _apply_session_filters(
            select(func.coalesce(func.sum(CoachingSession.duration_minutes), 0)),
            query,
        )
        total_sessions = await _scalar(db, count_stmt)
        total_minutes = await _scalar(db, duration_stmt)
        sample_result = await db.execute(
            _apply_session_filters(
                select(CoachingSession).order_by(CoachingSession.scheduled_at.desc()).limit(20),
                query,
            )
        )
        sample_rows = [
            {
                "session_id": session.id,
                "player_id": session.player_profile_id,
                "coach_user_id": session.coach_user_id,
                "scheduled_at": session.scheduled_at.isoformat(),
                "duration_minutes": session.duration_minutes,
            }
            for session in sample_result.scalars().all()
        ]
        summary_stats = {
            "session_count": total_sessions,
            "total_minutes": total_minutes,
        }
    else:
        raise HTTPException(status_code=400, detail="Unsupported entity")

    return AnalyticsResult(query=query, summary_stats=summary_stats, sample_rows=sample_rows)


# ---------------------------------------------------------------------------
# Match AI Summary Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/matches/{match_id}/ai-summary",
    response_model=MatchAiSummaryResponse,
    summary="Get AI-style summary for a match case study",
    tags=["analyst_pro", "ai"],
)
async def get_match_ai_summary(
    match_id: str,
    _current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
) -> MatchAiSummaryResponse:
    """
    Generate an AI-style structured summary for a match.

    This is a MOCK implementation that generates deterministic summaries
    based on match data. No actual LLM calls are made.

    Returns structured data including:
    - Team summaries with results and key stats
    - Decisive phases (powerplay, middle, death)
    - Momentum shifts based on wicket clusters
    - Player highlights
    - Key themes identified in the match
    - Overall natural language summary
    """
    service = MatchAiService(db)
    try:
        return await service.build_match_ai_summary(match_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e


# ---------------------------------------------------------------------------
# Match Context Package Endpoint
# ---------------------------------------------------------------------------


@router.get(
    "/matches/{match_id}/context-package",
    response_model=None,  # Returns dict (MatchContextPackage TypedDict)
    summary="Get comprehensive match context package for AI/LLM consumption",
    tags=["analyst_pro", "ai"],
)
async def get_match_context_package(
    match_id: str,
    _current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
) -> MatchContextPackage:
    """
    Generate a comprehensive match context package for AI/LLM consumption.

    This endpoint provides a structured JSON representation of a match including:
    - Match metadata (format, venue, teams, toss, result)
    - Per-innings phase breakdowns (powerplay, middle, death) with:
      - Label, team, over range, score summary
      - Notable events (boundaries, wickets)
    - Player performances with:
      - Name, team, role
      - Batting/bowling stats
      - Impact scores
      - Tags (e.g., "death_overs_anchor", "early_wickets", "collapse_trigger")
    - High-level match callouts for AI insights

    This is ideal for feeding into LLM prompts for match analysis.
    """
    try:
        return await generate_match_context_package(match_id, db)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
