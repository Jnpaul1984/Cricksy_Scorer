"""
FastAPI router for Match Case Study analytics.

Exposes:
  GET /analytics/matches
  GET /analytics/matches/{match_id}/case-study
  GET /analytics/matches/{match_id}/registry
"""

from datetime import date
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import security
from backend.sql_app.database import get_db
from backend.sql_app.models import Game, GameStatus, HistoricalImportBatch
from backend.api.schemas.analyst_matches import (
    AnalystMatchListItem,
    AnalystMatchListResponse,
    MatchRegistryResponse,
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


@router.get("/{match_id}/registry", response_model=MatchRegistryResponse)
async def get_match_registry(
    match_id: str,
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(get_db),
) -> MatchRegistryResponse:
    """Return registry metadata, source provenance, and training eligibility for a match.

    Phase 5M: exposes the Cricket Data Registry foundation for the Analyst Workspace.

    - For historical imports: returns import-batch linkage, source filename/format,
      validation status, registration status, and training eligibility gating.
    - For live matches: returns is_historical=False with not_applicable status.
    - If the batch record cannot be found: returns partial metadata with
      validation_status="unknown" and training_eligible=False.

    Training eligibility remains False until the import batch is finalized,
    the status is "valid", and error_count is 0 (mirrors the existing
    /api/historical-import/json/batches/{batch_id}/training-status logic).
    """
    stmt = scoped_games_stmt(current_user).where(
        Game.id == match_id,
        Game.status == GameStatus.completed,
    )
    result = await db.execute(stmt)
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Match not found")

    team_a_name = _team_name(game.team_a, "Team A")
    team_b_name = _team_name(game.team_b, "Team B")
    hist_meta = _historical_import_meta(game)

    if not hist_meta:
        return MatchRegistryResponse(
            match_id=match_id,
            is_historical=False,
            teams=f"{team_a_name} vs {team_b_name}",
            validation_status="not_applicable",
            registration_status="not_registered",
            training_eligible=False,
            blocking_reason="not_a_historical_import",
        )

    # Extract counts from stored historical metadata
    phases = game.phases if isinstance(game.phases, dict) else {}
    hist_innings = phases.get("historical_innings_summary") or []
    innings_count = len(hist_innings) if isinstance(hist_innings, list) else 0
    deliveries_imported = bool(hist_meta.get("deliveries_imported"))
    player_names = hist_meta.get("player_names") or []
    player_count = len(player_names) if isinstance(player_names, list) else 0

    # Look up the import batch by batch_id stored in hist_meta
    batch_id: str | None = hist_meta.get("batch_id")
    batch: HistoricalImportBatch | None = None
    if batch_id:
        batch_stmt = select(HistoricalImportBatch).where(HistoricalImportBatch.id == batch_id)
        batch_result = await db.execute(batch_stmt)
        batch = batch_result.scalar_one_or_none()

    if batch is not None:
        # Derive training eligibility (mirrors existing training-status endpoint logic)
        blocking_reason: str | None = None
        if batch.status in {"scanned", "metadata_extracted", "pending_full_import"}:
            blocking_reason = "metadata_only_pending_full_import"
        elif not batch.is_finalized:
            blocking_reason = "batch_not_finalized"
        elif batch.applied_game_id is None:
            blocking_reason = "no_game_applied"
        elif batch.status != "valid":
            blocking_reason = f"invalid_status_{batch.status}"
        elif batch.error_count > 0:
            blocking_reason = "has_errors"

        training_eligible = blocking_reason is None
        registration_status = (
            "registered"
            if (batch.is_finalized and batch.status == "valid" and batch.error_count == 0)
            else "not_registered"
        )

        return MatchRegistryResponse(
            match_id=match_id,
            is_historical=True,
            competition=hist_meta.get("event_name"),
            season=hist_meta.get("season"),
            venue=hist_meta.get("venue"),
            teams=f"{team_a_name} vs {team_b_name}",
            match_number=hist_meta.get("match_number"),
            player_count=player_count,
            innings_count=innings_count,
            has_deliveries=deliveries_imported,
            import_batch_id=batch.id,
            source_filename=batch.source_filename,
            source_format=batch.source_format,
            source_type="json",
            # batch.created_at is when the dry-run/preview batch record was created,
            # i.e. when the import process was initiated by the user.
            imported_at=batch.created_at,
            validation_status=batch.status,
            registration_status=registration_status,
            training_eligible=training_eligible,
            blocking_reason=blocking_reason,
        )

    # Batch record not found — return partial info from hist_meta only
    return MatchRegistryResponse(
        match_id=match_id,
        is_historical=True,
        competition=hist_meta.get("event_name"),
        season=hist_meta.get("season"),
        venue=hist_meta.get("venue"),
        teams=f"{team_a_name} vs {team_b_name}",
        match_number=hist_meta.get("match_number"),
        player_count=player_count,
        innings_count=innings_count,
        has_deliveries=deliveries_imported,
        import_batch_id=batch_id,
        source_filename=None,
        source_format=None,
        source_type="json",
        imported_at=None,
        validation_status="unknown",
        registration_status="not_registered",
        training_eligible=False,
        blocking_reason="batch_record_not_found",
    )
