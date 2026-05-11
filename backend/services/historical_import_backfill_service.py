"""Phase 5K — Historical Import Metadata Backfill Service.

Provides a controlled, safe repair path for legacy historical imported Game rows
that are missing Phase 5J metadata fields (``event_name``, ``season``,
``match_number``, ``source_dates``).

Design choices (Phase 5K):
- Only historical-import completed games may be repaired.
- Live / in-progress games are never touched.
- Phase 5J metadata already present is NEVER overwritten.
- Repair is sourced from the batch's stored ``dry_run_summary`` only; no data
  is fabricated.
- If the batch dry_run_summary does not contain the missing fields the repair
  is refused and the caller is told to reimport.
- All repairs are idempotent: a second repair call on an already-complete game
  returns ``already_complete`` without modifying data.
- Every successful repair writes an audit entry into
  ``game.phases["historical_import"]["_repair_log"]``.
"""

from __future__ import annotations

import datetime as dt
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.historical_import_apply_service import get_batch_by_id
from backend.sql_app.models import Game, GameStatus

# Phase 5J fields that were added to historical_import metadata.
# A legacy game is one that is missing ALL of these keys.
_PHASE_5J_FIELDS: frozenset[str] = frozenset(
    {"event_name", "season", "match_number", "source_dates"}
)


def _is_legacy_game(historical_meta: dict[str, Any]) -> bool:
    """Return True if the historical_import metadata is missing Phase 5J fields."""
    return not any(field in historical_meta for field in _PHASE_5J_FIELDS)


def _has_phase_5j_metadata(historical_meta: dict[str, Any]) -> bool:
    """Return True if the metadata already has at least one Phase 5J field present.

    Presence of any key means Phase 5J already populated the data; we must not
    overwrite it even partially.
    """
    return any(field in historical_meta for field in _PHASE_5J_FIELDS)


async def _fetch_game(db: AsyncSession, game_id: str) -> Game | None:
    result = await db.execute(select(Game).where(Game.id == game_id))
    return result.scalars().first()


async def repair_legacy_historical_metadata(
    db: AsyncSession,
    *,
    batch_id: str,
    confirm: bool,
) -> tuple[dict[str, Any] | None, list[str], str | None]:
    """Attempt to backfill Phase 5J metadata onto a legacy historical Game row.

    Returns:
        (result, warnings, error_message)
        - result: on success a dict describing what was repaired; None on failure
          or when repair was unnecessary.
        - warnings: list of non-fatal warning strings.
        - error_message: human-readable failure reason, or None on success.

    Safety gates (all must pass before any DB write):
    1. ``confirm`` must be True.
    2. Batch must exist.
    3. Batch must be finalized (apply was called) with a non-null applied_game_id.
    4. The linked Game must exist.
    5. Game status must be ``completed`` (never repair live/in-progress matches).
    6. Game must have ``phases["historical_import"]`` (must be a historical import).
    7. Phase 5J fields must NOT already be present (do not overwrite valid data).
    8. Batch dry_run_summary must contain metadata_preview with at least one of the
       missing Phase 5J fields; otherwise reimport is required.
    """
    warnings: list[str] = []

    # Gate 1: explicit confirmation
    if not confirm:
        return None, warnings, "confirm must be true to run a metadata repair."

    # Gate 2: batch must exist
    batch = await get_batch_by_id(db, batch_id)
    if batch is None:
        return None, warnings, f"Batch '{batch_id}' not found."

    # Gate 3: batch must be finalized and have a linked game
    if not batch.is_finalized or not batch.applied_game_id:
        return (
            None,
            warnings,
            (
                f"Batch '{batch_id}' has not been applied yet "
                "(is_finalized=False or applied_game_id is null). "
                "Only applied batches with a linked historical game may be repaired."
            ),
        )

    game_id: str = batch.applied_game_id

    # Gate 4: game must exist
    game = await _fetch_game(db, game_id)
    if game is None:
        return (
            None,
            warnings,
            (
                f"Historical Game '{game_id}' linked to batch '{batch_id}' was not found. "
                "The game may have been rolled back. Reimport is required."
            ),
        )

    # Gate 5: game must be completed (not live)
    if game.status != GameStatus.completed:
        return (
            None,
            warnings,
            (
                f"Game '{game_id}' has status '{game.status.value}'; "
                "only completed historical games may be repaired. "
                "Live and in-progress games are never mutated by the repair service."
            ),
        )

    # Gate 6: game must be a historical import
    phases: dict[str, Any] = game.phases or {}
    if not isinstance(phases, dict) or "historical_import" not in phases:
        return (
            None,
            warnings,
            (
                f"Game '{game_id}' does not have a 'historical_import' phases key. "
                "This game was not created by the historical import pipeline; "
                "repair is not applicable."
            ),
        )

    historical_meta: dict[str, Any] = phases["historical_import"]
    if not isinstance(historical_meta, dict):
        return (
            None,
            warnings,
            (
                f"Game '{game_id}' has a malformed 'historical_import' phases entry. "
                "Manual inspection is required before repair."
            ),
        )

    # Gate 7: do not overwrite valid Phase 5J metadata — return "already_complete"
    if not _is_legacy_game(historical_meta):
        return (
            {"status": "already_complete", "game_id": game_id, "batch_id": batch_id},
            warnings,
            None,
        )

    # Gate 8: dry_run_summary must carry metadata_preview with at least one Phase 5J field
    dry_run: dict[str, Any] = batch.dry_run_summary or {}
    metadata_preview: dict[str, Any] = dry_run.get("metadata_preview") or {}

    sourced_fields: dict[str, Any] = {}
    for field in _PHASE_5J_FIELDS:
        if field in metadata_preview:
            sourced_fields[field] = metadata_preview[field]

    if not sourced_fields:
        return (
            None,
            warnings,
            (
                f"Batch '{batch_id}' dry_run_summary does not contain any Phase 5J "
                "metadata fields (event_name, season, match_number, source_dates). "
                "Automatic repair is not possible. "
                "Reimport the match using the current importer to obtain accurate metadata."
            ),
        )

    # --- Safe to repair ---
    # Merge sourced fields into the existing historical_import dict (no overwrite)
    updated_meta = {**historical_meta}
    for field, value in sourced_fields.items():
        if field not in updated_meta:
            updated_meta[field] = value

    # Write an audit entry
    repair_log = updated_meta.get("_repair_log") or []
    repair_log.append(
        {
            "phase": "5K",
            "repaired_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "fields_added": sorted(sourced_fields.keys()),
            "source": "dry_run_summary.metadata_preview",
        }
    )
    updated_meta["_repair_log"] = repair_log

    # Write back to game.phases (SQLAlchemy JSON column — must replace the whole dict)
    updated_phases = {**phases, "historical_import": updated_meta}
    game.phases = updated_phases
    await db.commit()
    await db.refresh(game)

    fields_added = sorted(sourced_fields.keys())
    if batch.warning_count > 0:
        warnings.append(
            f"Batch had {batch.warning_count} warning(s) during the original dry-run; "
            "verify repaired metadata is correct."
        )

    return (
        {
            "status": "repaired",
            "game_id": game_id,
            "batch_id": batch_id,
            "fields_added": fields_added,
        },
        warnings,
        None,
    )
