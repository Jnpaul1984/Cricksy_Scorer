"""Phase 5N — Historical Stats Aggregation Layer: read-only REST endpoints.

Exposes:
  GET /analytics/historical-stats/summary
      Full deterministic historical stats summary for all eligible imported matches.

  GET /analytics/historical-stats/match/{match_id}
      Single-match aggregate stats for one eligible historical import.

Both endpoints:
  - Require analyst_pro or org_pro role.
  - Apply org-scoping (users see only their own or org-scoped matches).
  - Are strictly read-only — no Game or batch fields are mutated.
  - Exclude metadata-only and invalid/unfinalized records.
  - Return provenance references alongside computed aggregates.

No LLM/AI services, DLS logic, or live scoring truth are touched.
"""

from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend import security
from backend.api.schemas.historical_stats import (
    HistoricalMatchAggregateResponse,
    HistoricalStatsSummaryResponse,
)
from backend.services.historical_stats_aggregation_service import (
    get_historical_stats_summary,
    get_single_match_aggregate,
)
from backend.sql_app.database import get_db as _base_get_db

router = APIRouter(
    prefix="/analytics/historical-stats",
    tags=["historical-stats"],
)

AllowedRoles = ["analyst_pro", "org_pro"]


async def _get_stats_db() -> AsyncGenerator[AsyncSession, None]:
    """Real DB dependency for historical stats aggregation.

    Defined as a local dependency (not ``get_db`` directly) so that FastAPI's
    ``dependency_overrides[get_db] = _FakeSession`` installed by
    ``create_app()`` in ``CRICKSY_IN_MEMORY_DB=1`` mode does NOT replace this
    dependency.  Historical stats aggregation requires real SQLite/Postgres
    Game and HistoricalImportBatch rows — the fake session cannot serve them.

    This mirrors the ``_get_import_db`` pattern in ``routes/historical_import.py``.
    """
    async for db in _base_get_db():
        yield db


@router.get("/summary", response_model=HistoricalStatsSummaryResponse)
async def get_historical_stats_summary_endpoint(
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(_get_stats_db),
) -> HistoricalStatsSummaryResponse:
    """Return a full deterministic historical stats summary.

    Phase 5N: on-demand aggregation across all eligible historical matches.

    Eligible matches are:
    - Fully imported (Phase 5D applied, batch finalized)
    - Validated (batch status = 'valid', error_count = 0)
    - Registered (batch is_finalized = True, applied_game_id set)
    - NOT metadata-only (status not in: scanned, metadata_extracted, pending_full_import)

    Returned aggregates include:
    - Per-match totals (runs, wickets, innings, provenance)
    - Per-player batting/bowling stats (only for Phase 5F delivery-imported games)
    - Per-team averages
    - Per-venue averages
    - Per-competition averages
    - Per-season averages

    Metadata-only imports are excluded and counted separately.
    No official cricket truth is mutated.
    No AI/LLM services are used.
    """
    return await get_historical_stats_summary(db, current_user)


@router.get("/match/{match_id}", response_model=HistoricalMatchAggregateResponse)
async def get_match_historical_aggregate(
    match_id: str,
    current_user: Annotated[Any, Depends(security.require_roles(AllowedRoles))],
    db: AsyncSession = Depends(_get_stats_db),
) -> HistoricalMatchAggregateResponse:
    """Return aggregate stats for a single historical match.

    Phase 5N: on-demand aggregation for one eligible historical game.

    Returns:
    - Match-level aggregate (runs, wickets, innings totals, provenance)
    - Per-player batting/bowling stats (only for Phase 5F delivery-imported games)
    - Full provenance: batch id, source filename, validation status, etc.

    Returns 404 if the match is not found, not historical, not accessible,
    or not eligible for full aggregation (e.g. metadata-only).

    No official cricket truth is mutated.
    """
    aggregate = await get_single_match_aggregate(db, current_user, match_id)
    if aggregate is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=(
                "Match not found, not a historical import, or not eligible "
                "for full aggregation (may be metadata-only or unvalidated)."
            ),
        )
    return aggregate
