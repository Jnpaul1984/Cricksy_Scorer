"""Phase 5D - Historical Import Apply Service.

Provides ``apply_historical_batch`` which, given a validated
``HistoricalImportBatch`` ID and an explicit confirmation, creates a
historical Game record and marks the batch as finalized.

Conservative design choices:
- Delivery-level records are NOT imported.  The ``Game.deliveries`` JSON
  column is the live scoring engine's ledger; injecting historical balls
  there would be unsafe in Phase 5D.  Match metadata only is imported.
  Phase 5E will address delivery-level import if the schema supports it.
- No Player/Team ORM rows are created; team names from the dry-run preview
  are stored inline in ``Game.team_a`` / ``Game.team_b`` JSON columns, which
  is the same pattern used by the live scoring engine.
- Innings summaries are stored in ``Game.phases`` JSON under the key
  ``historical_innings_summary`` for auditability without touching the live
  scoring engine's innings state columns.
- ``Game.status`` is set to ``GameStatus.completed`` to prevent the scoring
  engine from treating this as a live game.
- ``Game.phases`` receives a ``historical_import`` sub-key with the batch ID
  so that any scan of the games table can identify imported records even
  though there is no dedicated ``is_historical`` column in Phase 5D.

Rollback:
  To undo a Phase 5D apply:
    1. Delete the Game row identified by ``HistoricalImportBatch.applied_game_id``.
    2. Set ``HistoricalImportBatch.is_finalized = False`` and
       ``HistoricalImportBatch.applied_game_id = None`` on the batch.
  This can be done manually via the database or via a future Phase 5E
  rollback endpoint.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.sql_app.models import Game, GameStatus, HistoricalImportBatch

# Batch statuses from which an apply is allowed.
_APPLICABLE_STATUSES = {"valid"}


async def get_batch_by_id(
    db: AsyncSession,
    batch_id: str,
) -> HistoricalImportBatch | None:
    """Fetch a single ``HistoricalImportBatch`` by primary key."""
    result = await db.execute(
        select(HistoricalImportBatch).where(HistoricalImportBatch.id == batch_id)
    )
    return result.scalars().first()


def _build_team_json(team_name: str) -> dict[str, Any]:
    """Return a minimal team JSON blob in the same shape as the live scoring engine."""
    return {"name": team_name, "players": []}


def _build_empty_scorecard() -> dict[str, Any]:
    """Return an empty scorecard dict matching the Game column defaults."""
    return {}


def _extract_innings_summary(dry_run_summary: dict[str, Any]) -> list[dict[str, Any]]:
    """Pull innings preview data from the dry-run summary for historical storage."""
    innings_preview = dry_run_summary.get("innings_preview") or []
    return [
        {
            "inning_no": inn.get("inning_no"),
            "team": inn.get("team"),
            "deliveries": inn.get("deliveries", 0),
            "runs": inn.get("runs"),
            "wickets": inn.get("wickets"),
            "overs": inn.get("overs"),
        }
        for inn in innings_preview
        if isinstance(inn, dict)
    ]


async def apply_historical_batch(
    db: AsyncSession,
    *,
    batch_id: str,
    confirm: bool,
) -> tuple[Game | None, list[str], str | None]:
    """Apply a validated historical import batch by creating a historical Game row.

    Returns:
        (game, warnings, error_message)
        - game: the created Game ORM row on success, None on failure.
        - warnings: list of non-fatal warning strings.
        - error_message: human-readable reason for failure, or None on success.

    Validation gates (all must pass before any DB write):
    1. ``confirm`` must be True.
    2. Batch must exist.
    3. Batch must not already be finalized (no duplicate apply).
    4. Batch dry-run status must be ``valid`` (only valid batches may be applied).
    5. Batch must have no errors recorded (error_count == 0).
    6. Batch must have teams data (teams_preview not empty).
    7. Source hash must be non-empty (provenance integrity).
    """
    warnings: list[str] = []

    # Gate 1: explicit confirmation
    if not confirm:
        return None, warnings, "confirm must be true to apply a batch."

    # Gate 2: batch must exist
    batch = await get_batch_by_id(db, batch_id)
    if batch is None:
        return None, warnings, f"Batch '{batch_id}' not found."

    # Gate 3: no duplicate apply
    if batch.is_finalized:
        existing_game_id = batch.applied_game_id or "unknown"
        return (
            None,
            warnings,
            (
                f"Batch '{batch_id}' has already been applied "
                f"(applied_game_id={existing_game_id}). "
                "Duplicate apply is not allowed in Phase 5D."
            ),
        )

    # Gate 4: dry-run status must be valid
    if batch.status not in _APPLICABLE_STATUSES:
        return (
            None,
            warnings,
            (
                f"Batch '{batch_id}' has status '{batch.status}'; "
                "only 'valid' batches may be applied."
            ),
        )

    # Gate 5: no errors
    if batch.error_count > 0:
        return (
            None,
            warnings,
            (
                f"Batch '{batch_id}' recorded {batch.error_count} error(s) during dry-run. "
                "Fix the source data and re-submit a new dry-run before applying."
            ),
        )

    # Gate 6: source hash integrity
    if not batch.source_hash_sha256:
        return (
            None,
            warnings,
            f"Batch '{batch_id}' has no source hash; provenance cannot be verified.",
        )

    # Extract metadata from the stored dry-run summary
    dry_run: dict[str, Any] = batch.dry_run_summary or {}
    metadata: dict[str, Any] = dry_run.get("metadata_preview") or {}
    teams_preview: list[str] = dry_run.get("teams_preview") or []

    # Gate 7: teams must be derivable
    if len(teams_preview) < 2:
        return (
            None,
            warnings,
            (
                f"Batch '{batch_id}' has fewer than 2 teams in the dry-run preview "
                f"({len(teams_preview)} found). Cannot create a historical game record."
            ),
        )

    match_type_raw: str = metadata.get("match_type") or "custom"
    venue: str | None = metadata.get("venue")
    match_date: str | None = metadata.get("date")
    result_text: str | None = metadata.get("result")

    team_a_name = teams_preview[0]
    team_b_name = teams_preview[1]

    if batch.warning_count > 0:
        warnings.append(
            f"Batch had {batch.warning_count} warning(s) during dry-run; "
            "review the dry-run summary before using this record."
        )

    innings_summary = _extract_innings_summary(dry_run)

    # Derive toss winner from innings summary if possible, otherwise leave as
    # team_a_name (the first batting side from the preview).  This is a best-effort
    # heuristic for historical data; toss information is rarely encoded in the JSON.
    toss_winner: str = team_a_name
    toss_decision: str = "bat"
    if innings_summary:
        first_innings_team = innings_summary[0].get("team")
        if first_innings_team:
            # The team that batted first in innings 1 most likely won the toss and chose to bat.
            toss_winner = first_innings_team
            toss_decision = "bat"

    # Build the historical phases metadata blob.
    # Using Game.phases (existing nullable JSON column) avoids a schema change for
    # the Game table.  The ``historical_import`` sub-key allows downstream code
    # to identify imported records without a dedicated is_historical column.
    phases: dict[str, Any] = {
        "historical_import": {
            "batch_id": batch_id,
            "source_hash_sha256": batch.source_hash_sha256,
            "source_filename": batch.source_filename,
            "source_format": batch.source_format,
            "match_date": match_date,
            "venue": venue,
            "is_historical": True,
        },
        "historical_innings_summary": innings_summary,
    }

    game_id = str(uuid.uuid4())

    # Determine a stable match_type string for the Game column.
    # The Game.match_type column is a plain String (not an Enum) so any value is safe.
    match_type_str = match_type_raw.strip().lower() if match_type_raw else "custom"

    # Build minimal team JSON blobs (no player rows created)
    team_a = _build_team_json(team_a_name)
    team_b = _build_team_json(team_b_name)

    # Create the Game row directly (bypasses the live scoring engine)
    game = Game(
        id=game_id,
        team_a=team_a,
        team_b=team_b,
        match_type=match_type_str,
        overs_limit=None,
        dls_enabled=False,
        interruptions=[],
        toss_winner_team=toss_winner,
        decision=toss_decision,
        batting_team_name=toss_winner,
        bowling_team_name=(team_b_name if toss_winner == team_a_name else team_a_name),
        batting_scorecard=_build_empty_scorecard(),
        bowling_scorecard=_build_empty_scorecard(),
        current_inning=0,
        status=GameStatus.completed,
        result=result_text,
        phases=phases,
        total_runs=0,
        total_wickets=0,
        overs_completed=0,
        balls_this_over=0,
    )
    db.add(game)

    # Flush to detect constraint violations before finalizing the batch
    await db.flush()

    # Finalize the batch - mark as applied with the created game ID
    batch.is_finalized = True
    batch.applied_game_id = game_id
    db.add(batch)

    await db.commit()
    await db.refresh(game)
    await db.refresh(batch)

    return game, warnings, None
