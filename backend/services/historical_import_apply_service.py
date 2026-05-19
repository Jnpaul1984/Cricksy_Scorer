"""Phase 5D/5E/5F - Historical Import Apply Service.

Provides:
- ``apply_historical_batch`` (Phase 5D): creates the historical Game shell.
- ``rollback_historical_batch`` (Phase 5E): deletes the Game row safely.
- ``apply_historical_deliveries`` (Phase 5F): imports delivery-level data into
  the historical Game row created by Phase 5D.

Phase 5D conservative design choices:
- Delivery-level records are NOT imported at Phase 5D time.  The
  ``Game.deliveries`` JSON column is the live scoring engine's ledger;
  injecting historical balls there without validation would be unsafe.
  Phase 5F closes this gap.
- No Player/Team ORM rows are created; team names from the dry-run preview
  are stored inline in ``Game.team_a`` / ``Game.team_b`` JSON columns.
- Innings summaries are stored in ``Game.phases`` JSON under the key
  ``historical_innings_summary`` for auditability.
- ``Game.status`` is set to ``GameStatus.completed`` to prevent the scoring
  engine from treating this as a live game.
- ``Game.phases`` receives a ``historical_import`` sub-key with the batch ID.

Phase 5F delivery import:
- Requires the caller to re-provide the raw JSON payload (same file that was
  dry-run'd).  The canonical SHA-256 hash is verified against the stored
  batch hash before any write occurs.
- Totals validation (runs ± 5 tolerance) blocks unsafe imports.
- Idempotent: a second apply-deliveries on an already-imported game returns
  "already_applied" without mutating any data.
- Rollback: the existing Phase 5E rollback endpoint deletes the entire Game
  row, which also removes all imported delivery data stored in JSON columns.
  No separate Phase 5F rollback endpoint is required.

Rollback (Phase 5D/5F combined):
  POST /api/historical-import/json/batches/{batch_id}/rollback with confirm=true
  Deletes the Game row (including all imported deliveries) and resets batch.
"""

from __future__ import annotations

import datetime as dt
import json as _json
import logging
import uuid
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.historical_import_delivery_service import (
    _collect_team_players,
    _derive_batting_scorecard,
    _derive_bowling_scorecard,
    _derive_first_inning_summary,
    extract_normalized_innings,
    is_legal_delivery,
    validate_innings_totals,
    verify_payload_hash,
)
from backend.services.historical_player_identity_service import register_historical_source_players
from backend.services.historical_venue_intelligence_service import resolve_historical_venue
from backend.sql_app.models import Game, GameStatus, HistoricalImportBatch

# Batch statuses from which an apply is allowed.
_APPLICABLE_STATUSES = {"valid"}

_log = logging.getLogger(__name__)


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
            "legal_balls": inn.get("legal_balls"),
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
    canonical_preview: dict[str, Any] = dry_run.get("canonical_preview") or {}
    competition_context: dict[str, Any] = canonical_preview.get("competition_context") or {}
    venue_context: dict[str, Any] = canonical_preview.get("venue_context") or {}
    roster_snapshot: list[dict[str, Any]] = canonical_preview.get("squad_roster_snapshot") or []
    source_provenance: dict[str, Any] = canonical_preview.get("source_provenance") or {}
    schema_classification: dict[str, Any] = dry_run.get("schema_classification") or {}
    teams_preview: list[str] = dry_run.get("teams_preview") or []
    player_names_found: list[str] = dry_run.get("player_names_found") or []

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
            "event_name": metadata.get("event_name"),
            "season": metadata.get("season"),
            "match_number": metadata.get("match_number"),
            "source_dates": metadata.get("source_dates") or [],
            "competition_type": competition_context.get("competition_type"),
            "competition_name": competition_context.get("competition_name"),
            "competition_stage": competition_context.get("competition_stage"),
            "match_format": competition_context.get("match_format"),
            "tournament_name": competition_context.get("tournament_name"),
            "tournament_round": competition_context.get("tournament_round"),
            "venue_context": venue_context,
            "source_schema": source_provenance.get("source_schema")
            or schema_classification.get("source_schema"),
            "source_schema_version": source_provenance.get("source_schema_version")
            or schema_classification.get("source_schema_version"),
            "adapter_id": source_provenance.get("adapter_id")
            or schema_classification.get("adapter_id"),
            "adapter_version": source_provenance.get("adapter_version")
            or schema_classification.get("adapter_version"),
            "roster_snapshot_available": bool(roster_snapshot),
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
        created_by_user_id=batch.owner_user_id,
        phases=phases,
        total_runs=0,
        total_wickets=0,
        overs_completed=0,
        balls_this_over=0,
    )
    db.add(game)

    # Flush to detect constraint violations before finalizing the batch
    await db.flush()

    # Build the mutable historical_meta from the phases blob created above.
    historical_meta = dict(phases.get("historical_import") or {})

    # Phase 10E/10F/10G: Register historical source players.
    # Wrapped in a savepoint so that a missing-table error (production migration
    # not yet applied) does NOT abort the outer transaction that creates the Game
    # row.  A failure here adds a warning and records "skipped: true" in the
    # phases metadata; the game is still persisted successfully.
    _source_schema = (
        source_provenance.get("source_schema")
        or schema_classification.get("source_schema")
        or "unknown"
    )
    try:
        async with db.begin_nested():
            player_identity_registry = await register_historical_source_players(
                db,
                batch_id=batch_id,
                game_id=game_id,
                source_schema=_source_schema,
                source_system="historical_import_json",
                source_provenance=source_provenance,
                competition_context=competition_context,
                roster_snapshot=roster_snapshot,
                player_names=player_names_found,
                match_date=match_date,
            )
        historical_meta["player_identity_registry"] = player_identity_registry
    except Exception as exc:
        _log.warning(
            "historical_import_apply: player identity registration failed; "
            "game will still be created. batch_id=%s error=%s",
            batch_id,
            exc,
        )
        historical_meta["player_identity_registry"] = {
            "skipped": True,
            "error": type(exc).__name__,
        }
        warnings.append(
            "Player identity registration encountered an error and was skipped. "
            "The game record was still created successfully. "
            "Ensure Phase 10E-10G migrations are applied in production."
        )

    # Phase 10H: Resolve historical venue.
    # Same savepoint safety net as above.
    try:
        async with db.begin_nested():
            venue_resolution = await resolve_historical_venue(
                db,
                batch_id=batch_id,
                game_id=game_id,
                source_schema=_source_schema,
                source_system="historical_import_json",
                source_provenance=source_provenance,
                competition_context=competition_context,
                match_date=match_date,
                raw_venue_value=venue,
                venue_context=venue_context,
            )
        historical_meta["venue_resolution"] = venue_resolution
    except Exception as exc:
        _log.warning(
            "historical_import_apply: venue resolution failed; "
            "game will still be created. batch_id=%s error=%s",
            batch_id,
            exc,
        )
        historical_meta["venue_resolution"] = {
            "skipped": True,
            "error": type(exc).__name__,
        }
        warnings.append(
            "Venue intelligence resolution encountered an error and was skipped. "
            "The game record was still created successfully. "
            "Ensure Phase 10H migrations are applied in production."
        )

    game.phases = {**phases, "historical_import": historical_meta}
    db.add(game)

    # Finalize the batch - mark as applied with the created game ID
    batch.is_finalized = True
    batch.applied_game_id = game_id
    db.add(batch)

    await db.commit()
    await db.refresh(game)
    await db.refresh(batch)

    return game, warnings, None


async def rollback_historical_batch(
    db: AsyncSession,
    *,
    batch_id: str,
    confirm: bool,
    requester_user_id: str | None = None,
    requester_org_id: str | None = None,
) -> tuple[str | None, list[str], str | None]:
    """Rollback a finalized historical import batch by deleting its applied Game row.

    Returns:
        (rolled_back_game_id, warnings, error_message)
    """
    warnings: list[str] = []

    if not confirm:
        return None, warnings, "confirm must be true to rollback a batch."

    batch = await get_batch_by_id(db, batch_id)
    if batch is None:
        return None, warnings, f"Batch '{batch_id}' not found."

    if batch.owner_user_id or batch.owner_org_id:
        user_authorized = batch.owner_user_id is None or (
            requester_user_id is not None and requester_user_id == batch.owner_user_id
        )
        org_authorized = batch.owner_org_id is None or (
            requester_org_id is not None and requester_org_id == batch.owner_org_id
        )
        if not (user_authorized and org_authorized):
            return (
                None,
                warnings,
                (f"Batch '{batch_id}' is owned by another user/org. Rollback is not authorized."),
            )

    if not batch.is_finalized:
        return (
            None,
            warnings,
            f"Batch '{batch_id}' is not finalized; rollback is only allowed for applied batches.",
        )

    game_id = batch.applied_game_id
    if not game_id:
        return (
            None,
            warnings,
            f"Batch '{batch_id}' is finalized but has no applied_game_id; rollback is blocked.",
        )

    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalars().first()
    if game is None:
        return (
            None,
            warnings,
            (
                f"Batch '{batch_id}' points to missing game '{game_id}'. "
                "Rollback is blocked to preserve audit safety."
            ),
        )

    phases = game.phases or {}
    historical_meta = phases.get("historical_import") if isinstance(phases, dict) else None
    historical_batch_id = None
    if isinstance(historical_meta, dict):
        historical_batch_id = historical_meta.get("batch_id")

    if game.status != GameStatus.completed:
        return (
            None,
            warnings,
            (
                f"Game '{game_id}' is not completed (status={game.status.value}); "
                "rollback only allows completed historical imports."
            ),
        )

    if historical_batch_id != batch_id:
        return (
            None,
            warnings,
            (
                f"Game '{game_id}' is not a safe historical import for batch '{batch_id}'. "
                "Rollback refused."
            ),
        )

    await db.execute(delete(Game).where(Game.id == game_id))

    dry_run_summary = dict(batch.dry_run_summary) if isinstance(batch.dry_run_summary, dict) else {}
    rollback_log = dry_run_summary.get("_rollback_log")
    if not isinstance(rollback_log, list):
        rollback_log = []
    rollback_log.append(
        {
            "rolled_back_game_id": game_id,
            "rolled_back_at": dt.datetime.now(dt.timezone.utc).isoformat(),
            "by_user_id": requester_user_id,
            "by_org_id": requester_org_id,
        }
    )
    dry_run_summary["_rollback_log"] = rollback_log
    batch.dry_run_summary = dry_run_summary

    batch.is_finalized = False
    batch.applied_game_id = None
    db.add(batch)

    await db.commit()
    await db.refresh(batch)

    return game_id, warnings, None


# ---------------------------------------------------------------------------
# Phase 5F - Delivery-level import
# ---------------------------------------------------------------------------


async def apply_historical_deliveries(
    db: AsyncSession,
    *,
    batch_id: str,
    confirm: bool,
    raw_payload: bytes,
    allow_reprocess: bool = False,
) -> tuple[dict[str, Any] | None, list[str], str | None]:
    """Import delivery-level data into a previously-applied historical Game.

    This is the Phase 5F write path.  It MUST only be called after Phase 5D
    has already applied the batch and created the Game shell.

    Returns:
        (result_info, warnings, error_message)
        - result_info: dict with import stats on success, None on failure.
        - warnings: list of non-fatal warning strings.
        - error_message: reason for failure, or None on success.

    Validation gates:
    1. ``confirm`` must be True.
    2. Batch must exist.
    3. Batch must be finalized (Phase 5D applied).
    4. ``applied_game_id`` must be set on the batch.
    5. Game must exist and must be a historical import (safety guard).
    6. Deliveries must not already be imported (idempotency).
    7. Source hash of ``raw_payload`` must match ``batch.source_hash_sha256``.
    8. Totals validation: derived runs must reconcile with stored preview totals.
    """
    warnings: list[str] = []

    # Gate 1: explicit confirmation
    if not confirm:
        return None, warnings, "confirm must be true to apply deliveries."

    # Gate 2: batch must exist
    batch = await get_batch_by_id(db, batch_id)
    if batch is None:
        return None, warnings, f"Batch '{batch_id}' not found."

    # Gate 3: batch must be finalized (Phase 5D applied first)
    if not batch.is_finalized:
        return (
            None,
            warnings,
            (
                f"Batch '{batch_id}' has not been applied yet (Phase 5D required first). "
                "Apply the batch to create the historical Game shell before importing deliveries."
            ),
        )

    # Gate 4: game must be linked
    game_id = batch.applied_game_id
    if not game_id:
        return (
            None,
            warnings,
            f"Batch '{batch_id}' has no applied_game_id; cannot import deliveries.",
        )

    # Gate 5: game must exist and be a historical import
    result = await db.execute(select(Game).where(Game.id == game_id))
    game = result.scalars().first()
    if game is None:
        return (
            None,
            warnings,
            (
                f"Game '{game_id}' linked by batch '{batch_id}' was not found. "
                "It may have been rolled back. Re-apply the batch (Phase 5D) before importing deliveries."
            ),
        )

    phases = game.phases if isinstance(game.phases, dict) else {}
    hist_meta = phases.get("historical_import") if isinstance(phases, dict) else None
    if not isinstance(hist_meta, dict) or not hist_meta.get("is_historical"):
        return (
            None,
            warnings,
            (
                f"Game '{game_id}' is not a verified historical import. "
                "Delivery import refused to protect live match data."
            ),
        )

    if game.status != GameStatus.completed:
        return (
            None,
            warnings,
            (
                f"Game '{game_id}' is not in completed status (status={game.status.value}). "
                "Delivery import is only allowed for completed historical games."
            ),
        )

    # Gate 6: idempotency - deliveries must not already be imported
    if hist_meta.get("deliveries_imported") is True and not allow_reprocess:
        return (
            None,
            warnings,
            (
                f"Deliveries have already been imported for game '{game_id}' "
                f"(batch '{batch_id}'). Duplicate delivery import is not allowed."
            ),
        )

    # Gate 7: source hash verification
    try:
        actual_hash = verify_payload_hash(raw_payload, batch.source_hash_sha256)
    except (ValueError, _json.JSONDecodeError, UnicodeDecodeError) as exc:
        return (
            None,
            warnings,
            f"Payload could not be parsed for hash verification: {exc}",
        )
    if not actual_hash:
        return (
            None,
            warnings,
            (
                "Source payload hash does not match the stored batch hash. "
                "Ensure you are providing the same JSON file used during the original dry-run."
            ),
        )

    # Parse payload
    try:
        parsed = _json.loads(raw_payload.decode("utf-8"))
    except (ValueError, _json.JSONDecodeError, UnicodeDecodeError) as exc:
        return None, warnings, f"Payload is not valid JSON: {exc}"

    if not isinstance(parsed, dict):
        return None, warnings, "Payload top-level must be a JSON object."

    normalized_innings = extract_normalized_innings(parsed)
    if not normalized_innings:
        return None, warnings, "No innings data found in payload."

    total_deliveries = sum(len(inn["deliveries"]) for inn in normalized_innings)
    if total_deliveries == 0:
        return None, warnings, "No delivery/ball events found in innings data."

    # Gate 8: totals validation
    dry_run: dict[str, Any] = batch.dry_run_summary or {}
    innings_preview: list[dict[str, Any]] = dry_run.get("innings_preview") or []

    totals_validation, validation_warnings, blocking_error = validate_innings_totals(
        normalized_innings, innings_preview
    )
    warnings.extend(validation_warnings)

    if blocking_error is not None:
        return None, warnings, blocking_error

    # -----------------------------------------------------------------------
    # All gates passed - write delivery data
    # -----------------------------------------------------------------------

    teams_preview: list[str] = dry_run.get("teams_preview") or [
        (game.team_a or {}).get("name", "Team A"),
        (game.team_b or {}).get("name", "Team B"),
    ]

    # 1) Normalize all deliveries into a flat list for game.deliveries
    all_deliveries: list[dict[str, Any]] = []
    for inn in normalized_innings:
        all_deliveries.extend(inn["deliveries"])

    # 2) Derive batting/bowling scorecards per innings and merge
    merged_batting: dict[str, dict[str, Any]] = {}
    merged_bowling: dict[str, dict[str, Any]] = {}

    for inn in normalized_innings:
        inning_no = inn["inning_no"]
        batting = _derive_batting_scorecard(all_deliveries, inning_no)
        bowling = _derive_bowling_scorecard(all_deliveries, inning_no)
        merged_batting.update(batting)
        merged_bowling.update(bowling)

    # 3) Derive inline player lists (no ORM rows created)
    team_a_players, team_b_players = _collect_team_players(normalized_innings, teams_preview)

    team_a_json: dict[str, Any] = dict(game.team_a or {})
    team_a_json["players"] = team_a_players
    team_b_json: dict[str, Any] = dict(game.team_b or {})
    team_b_json["players"] = team_b_players

    # 4) First innings summary
    first_inning_summary = None
    if normalized_innings:
        first_inn = normalized_innings[0]
        first_team = first_inn.get("team") or (teams_preview[0] if teams_preview else "Team A")
        first_inning_summary = _derive_first_inning_summary(first_inn, first_team)

    # 5) Second innings totals (for game.total_runs etc.)
    second_innings_runs = 0
    second_innings_wickets = 0
    second_innings_legal_balls = 0
    second_innings_team = game.batting_team_name or (
        teams_preview[1] if len(teams_preview) > 1 else None
    )
    second_innings_bowling_team = teams_preview[0] if teams_preview else game.bowling_team_name
    if len(normalized_innings) >= 2:
        inn2 = normalized_innings[1]
        delivs2 = inn2["deliveries"]
        second_innings_team = inn2.get("team") or second_innings_team
        second_innings_bowling_team = (
            normalized_innings[0].get("team") or second_innings_bowling_team
        )
        second_innings_runs = (
            inn2["runs_explicit"]
            if inn2["runs_explicit"] is not None
            else sum(
                int(d.get("runs_off_bat") or 0) + int(d.get("extra_runs") or 0) for d in delivs2
            )
        )
        second_innings_wickets = (
            inn2["wickets_explicit"]
            if inn2["wickets_explicit"] is not None
            else sum(1 for d in delivs2 if d.get("is_wicket"))
        )
        second_innings_legal_balls = sum(1 for d in delivs2 if is_legal_delivery(d))

    second_innings_overs_completed = second_innings_legal_balls // 6
    second_innings_balls_this_over = second_innings_legal_balls % 6

    def _phase_aggregates(deliveries: list[dict[str, Any]]) -> dict[str, dict[str, Any]]:
        phase_keys = ("powerplay", "middle", "death")
        phase_stats = {
            key: {"runs": 0, "wickets": 0, "legal_balls": 0, "overs": 0.0, "deliveries": 0}
            for key in phase_keys
        }
        for delivery in deliveries:
            phase = str(delivery.get("phase") or "").strip().lower()
            if phase not in phase_stats:
                continue
            phase_stats[phase]["deliveries"] += 1
            phase_stats[phase]["runs"] += int(delivery.get("runs_off_bat") or 0) + int(
                delivery.get("extra_runs") or 0
            )
            phase_stats[phase]["wickets"] += int(bool(delivery.get("is_wicket")))
            if is_legal_delivery(delivery):
                phase_stats[phase]["legal_balls"] += 1

        for phase in phase_keys:
            legal_balls = int(phase_stats[phase]["legal_balls"])
            phase_stats[phase]["overs"] = float(f"{legal_balls // 6}.{legal_balls % 6}")
        return phase_stats

    # 6) Update game phases to mark deliveries as imported (idempotency marker)
    updated_phases: dict[str, Any] = dict(phases)
    updated_hist_meta: dict[str, Any] = dict(hist_meta)
    updated_hist_meta["deliveries_imported"] = True
    updated_hist_meta["delivery_count"] = total_deliveries
    if allow_reprocess:
        updated_hist_meta["deliveries_reprocessed_at"] = dt.datetime.now(
            dt.timezone.utc
        ).isoformat()
    updated_phases["historical_import"] = updated_hist_meta
    phase_stats = _phase_aggregates(all_deliveries)
    for phase_name, stats in phase_stats.items():
        updated_phases[phase_name] = stats

    # 7) Persist all changes in a single transaction
    game.deliveries = all_deliveries
    game.batting_scorecard = merged_batting
    game.bowling_scorecard = merged_bowling
    game.team_a = team_a_json
    game.team_b = team_b_json
    game.first_inning_summary = first_inning_summary
    game.batting_team_name = second_innings_team
    game.bowling_team_name = second_innings_bowling_team
    game.total_runs = second_innings_runs
    game.total_wickets = second_innings_wickets
    game.overs_completed = second_innings_overs_completed
    game.balls_this_over = second_innings_balls_this_over
    game.phases = updated_phases
    db.add(game)

    await db.commit()
    await db.refresh(game)

    result_info = {
        "game_id": game_id,
        "deliveries_imported": total_deliveries,
        "innings_processed": len(normalized_innings),
        "totals_validation": totals_validation,
    }

    return result_info, warnings, None
