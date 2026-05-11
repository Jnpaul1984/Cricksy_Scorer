from __future__ import annotations

from collections.abc import AsyncGenerator
from typing import Annotated

from backend.api.schemas.historical_import import (
    HistoricalImportApplyDeliveriesResponse,
    HistoricalImportApplyRequest,
    HistoricalImportApplyResponse,
    HistoricalImportBatchRecord,
    HistoricalImportDryRunResponse,
    HistoricalImportRollbackRequest,
    HistoricalImportRollbackResponse,
    HistoricalImportTotalsValidation,
)
from backend.security import get_current_user_optional
from backend.services.historical_import_apply_service import (
    apply_historical_batch,
    apply_historical_deliveries,
    rollback_historical_batch,
)
from backend.services.historical_import_preview import build_dry_run_response
from backend.services.historical_import_service import (
    create_import_batch,
    find_duplicate_by_hash,
    find_duplicate_by_semantic_key,
    list_import_batches,
)
from backend.sql_app import models
from backend.sql_app.database import get_db as _base_get_db
from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/historical-import/json", tags=["historical-import"])


async def _get_import_db() -> AsyncGenerator[AsyncSession, None]:
    """Real DB dependency for historical import batch tracking.

    This wrapper bypasses the ``_FakeSession`` override that ``create_app``
    installs for in-memory/test mode (which only overrides
    ``backend.sql_app.database.get_db``).  Historical import batch tracking
    requires real SQLite/Postgres persistence in all environments.
    """
    async for db in _base_get_db():
        yield db


@router.post("/dry-run", response_model=HistoricalImportDryRunResponse)
async def historical_json_dry_run(
    request: Request,
    file: UploadFile | None = File(None),
    record_preview: bool = Query(
        default=False,
        description=(
            "When true, persist import batch metadata to the database. "
            "Default is false (no DB writes). "
            "Does NOT create Game/Delivery/Player/Team rows."
        ),
    ),
    db: AsyncSession = Depends(_get_import_db),
    current_user: Annotated[models.User | None, Depends(get_current_user_optional)] = None,
) -> HistoricalImportDryRunResponse | JSONResponse:
    payload_bytes: bytes
    source_filename: str | None = None

    if file is not None:
        payload_bytes = await file.read()
        source_filename = file.filename or None
    else:
        content_type = request.headers.get("content-type", "").lower()
        if "application/json" not in content_type:
            raise HTTPException(
                status_code=415,
                detail="Provide application/json payload or multipart file upload.",
            )
        payload_bytes = await request.body()

    status_code, response = build_dry_run_response(payload_bytes)
    if status_code >= 400:
        return JSONResponse(status_code=status_code, content=response.model_dump())

    # Resolve owner context from authenticated user (if any)
    owner_user_id: str | None = current_user.id if current_user else None
    owner_org_id: str | None = current_user.org_id if current_user else None

    source_hash = response.duplicate_detection.source_hash_sha256
    semantic_key = response.duplicate_detection.semantic_key

    # Duplicate detection (always performed when tracking is available)
    dup_by_hash = await find_duplicate_by_hash(db, source_hash, owner_user_id, owner_org_id)
    dup_by_semantic: models.HistoricalImportBatch | None = None
    if semantic_key:
        dup_by_semantic = await find_duplicate_by_semantic_key(
            db, semantic_key, owner_user_id, owner_org_id
        )

    probable_duplicate = "not_duplicate"
    dup_batch_id: str | None = None
    semantic_dup = False

    if dup_by_hash is not None:
        probable_duplicate = "likely_duplicate"
        dup_batch_id = dup_by_hash.id
    elif dup_by_semantic is not None:
        probable_duplicate = "likely_duplicate"
        dup_batch_id = dup_by_semantic.id
        semantic_dup = True

    dup_msg = (
        "Exact duplicate detected: a previous import batch matched this source hash."
        if dup_by_hash
        else (
            "Semantic duplicate detected: a previous import batch matched the same match key."
            if dup_by_semantic
            else "No duplicate detected for this source hash or semantic key."
        )
    )

    record_id: str | None = None
    no_persistence = True

    if record_preview:
        # Persist batch metadata only - no Game/Delivery/Player/Team writes
        batch = await create_import_batch(
            db,
            source_hash_sha256=source_hash,
            source_format=response.detected_format,
            status=response.status,
            error_count=len(response.errors),
            warning_count=len(response.warnings),
            innings_count=response.innings_count,
            delivery_count=response.delivery_count,
            dry_run_summary=response.model_dump(),
            owner_user_id=owner_user_id,
            owner_org_id=owner_org_id,
            source_filename=source_filename,
            semantic_key=semantic_key,
        )
        record_id = batch.id
        no_persistence = False

    return HistoricalImportDryRunResponse(
        status=response.status,
        detected_format=response.detected_format,
        top_level_keys=response.top_level_keys,
        detected_sections=response.detected_sections,
        metadata_preview=response.metadata_preview,
        teams_preview=response.teams_preview,
        innings_count=response.innings_count,
        delivery_count=response.delivery_count,
        player_names_found=response.player_names_found,
        innings_preview=response.innings_preview,
        warnings=response.warnings,
        errors=response.errors,
        duplicate_detection=response.duplicate_detection.model_copy(
            update={
                "probable_duplicate": probable_duplicate,
                "tracking_available": True,
                "duplicate_batch_id": dup_batch_id,
                "semantic_duplicate": semantic_dup,
                "message": dup_msg,
            }
        ),
        no_persistence=no_persistence,
        record_id=record_id,
    )


@router.get("/batches", response_model=list[HistoricalImportBatchRecord])
async def list_historical_import_batches(
    limit: int = Query(default=20, ge=1, le=200, description="Maximum number of records to return"),
    db: AsyncSession = Depends(_get_import_db),
    current_user: Annotated[models.User | None, Depends(get_current_user_optional)] = None,
) -> list[HistoricalImportBatchRecord]:
    """List historical import batch records scoped to the current user or org."""
    owner_user_id: str | None = current_user.id if current_user else None
    owner_org_id: str | None = current_user.org_id if current_user else None

    batches = await list_import_batches(db, owner_user_id, owner_org_id, limit=limit)
    return [
        HistoricalImportBatchRecord(
            id=b.id,
            owner_user_id=b.owner_user_id,
            owner_org_id=b.owner_org_id,
            source_filename=b.source_filename,
            source_format=b.source_format,
            source_hash_sha256=b.source_hash_sha256,
            semantic_key=b.semantic_key,
            status=b.status,
            error_count=b.error_count,
            warning_count=b.warning_count,
            innings_count=b.innings_count,
            delivery_count=b.delivery_count,
            is_finalized=b.is_finalized,
            applied_game_id=b.applied_game_id,
            created_at=b.created_at,
            updated_at=b.updated_at,
        )
        for b in batches
    ]


@router.post(
    "/batches/{batch_id}/apply",
    response_model=HistoricalImportApplyResponse,
    summary="Apply a validated historical import batch (Phase 5D)",
    description=(
        "Creates a historical Game record from a previously validated dry-run batch. "
        "Requires explicit confirm=true. "
        "Refuses already-finalized batches and batches with errors or non-valid status. "
        "Does NOT import delivery records (Phase 5E follow-up). "
        "Does NOT mutate live or in-progress matches."
    ),
)
async def apply_historical_import_batch(
    batch_id: str,
    body: HistoricalImportApplyRequest,
    db: AsyncSession = Depends(_get_import_db),
    current_user: Annotated[models.User | None, Depends(get_current_user_optional)] = None,
) -> HistoricalImportApplyResponse:
    """Apply a validated historical import batch and create a historical Game row."""
    game, warnings, error_msg = await apply_historical_batch(
        db,
        batch_id=batch_id,
        confirm=body.confirm,
    )

    if error_msg is not None:
        # Determine appropriate status code from error type
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        if "confirm must be true" in error_msg.lower():
            raise HTTPException(status_code=422, detail=error_msg)
        raise HTTPException(status_code=409, detail=error_msg)

    assert game is not None  # noqa: S101 - guaranteed by non-None error_msg check above

    rollback_info = (
        "To rollback via API: POST "
        f"'/api/historical-import/json/batches/{batch_id}/rollback' with "
        "{'confirm': true}. This deletes only applied_game_id="
        f"'{game.id}' after safety checks and resets batch finalize markers."
    )

    return HistoricalImportApplyResponse(
        batch_id=batch_id,
        applied_game_id=game.id,
        records_created=1,
        status="applied",
        warnings=warnings,
        rollback_info=rollback_info,
    )


@router.post(
    "/batches/{batch_id}/rollback",
    response_model=HistoricalImportRollbackResponse,
    summary="Rollback a finalized historical import batch (Phase 5E)",
    description=(
        "Deletes only the historical Game row created by this batch, if and only if "
        "the game can be verified as a safe imported historical record. "
        "Requires explicit confirm=true. "
        "Also removes any delivery-level data imported during Phase 5F, since "
        "delivery data is stored inside the Game row's JSON columns."
    ),
)
async def rollback_historical_import_batch(
    batch_id: str,
    body: HistoricalImportRollbackRequest,
    db: AsyncSession = Depends(_get_import_db),
    current_user: Annotated[models.User | None, Depends(get_current_user_optional)] = None,
) -> HistoricalImportRollbackResponse:
    """Rollback a finalized historical import batch with strict safety checks."""
    del current_user  # currently unused; reserved for ownership scoping in future phases

    rolled_back_game_id, warnings, error_msg = await rollback_historical_batch(
        db,
        batch_id=batch_id,
        confirm=body.confirm,
    )

    if error_msg is not None:
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        if "confirm must be true" in error_msg.lower():
            raise HTTPException(status_code=422, detail=error_msg)
        raise HTTPException(status_code=409, detail=error_msg)

    return HistoricalImportRollbackResponse(
        batch_id=batch_id,
        rolled_back_game_id=rolled_back_game_id,
        records_deleted=1,
        status="rolled_back",
        warnings=warnings,
    )


@router.post(
    "/batches/{batch_id}/apply-deliveries",
    response_model=HistoricalImportApplyDeliveriesResponse,
    summary="Import delivery-level data into a historical game (Phase 5F)",
    description=(
        "Phase 5F: imports ball-by-ball delivery data from the original JSON payload "
        "into the historical Game row created by Phase 5D apply. "
        "Requires explicit confirm=true query parameter. "
        "Requires the same JSON file that was used for the original dry-run (hash-verified). "
        "Validates innings totals before any write; blocks if totals are irreconcilable. "
        "Idempotent: a second call returns 'already_applied' without modifying data. "
        "Rollback: use the Phase 5E rollback endpoint to remove the entire Game row "
        "(including all imported delivery data)."
    ),
)
async def apply_historical_import_deliveries(
    batch_id: str,
    request: Request,
    file: UploadFile | None = File(None),
    confirm: bool = Query(
        default=False,
        description="Must be true to proceed with delivery import.",
    ),
    db: AsyncSession = Depends(_get_import_db),
    current_user: Annotated[models.User | None, Depends(get_current_user_optional)] = None,
) -> HistoricalImportApplyDeliveriesResponse:
    """Import delivery-level data into a previously-applied historical Game (Phase 5F)."""
    del current_user  # reserved for ownership scoping in future phases

    # Read the payload (same as dry-run: accept file upload or raw JSON body)
    if file is not None:
        raw_payload: bytes = await file.read()
    else:
        content_type = request.headers.get("content-type", "").lower()
        if "application/json" not in content_type:
            raise HTTPException(
                status_code=415,
                detail=(
                    "Provide application/json payload or multipart file upload "
                    "containing the original match JSON."
                ),
            )
        raw_payload = await request.body()

    result_info, warnings, error_msg = await apply_historical_deliveries(
        db,
        batch_id=batch_id,
        confirm=confirm,
        raw_payload=raw_payload,
    )

    if error_msg is not None:
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        if "confirm must be true" in error_msg.lower():
            raise HTTPException(status_code=422, detail=error_msg)
        if "already been imported" in error_msg.lower() or "already_applied" in error_msg.lower():
            raise HTTPException(status_code=409, detail=error_msg)
        if "does not match" in error_msg.lower() or "hash" in error_msg.lower():
            raise HTTPException(status_code=422, detail=error_msg)
        if "totals" in error_msg.lower() or "run total" in error_msg.lower() or "mismatch" in error_msg.lower():
            raise HTTPException(status_code=422, detail=error_msg)
        raise HTTPException(status_code=409, detail=error_msg)

    if result_info is None:
        raise RuntimeError("apply_historical_deliveries returned no result without an error message")

    game_id: str = result_info["game_id"]
    deliveries_imported: int = result_info["deliveries_imported"]
    innings_processed: int = result_info["innings_processed"]
    raw_totals = result_info["totals_validation"]

    totals_validation = [
        HistoricalImportTotalsValidation(
            inning_no=t["inning_no"],
            team=t.get("team"),
            derived_runs=t["derived_runs"],
            expected_runs=t.get("expected_runs"),
            derived_wickets=t["derived_wickets"],
            expected_wickets=t.get("expected_wickets"),
            legal_balls=t["legal_balls"],
            status=t["status"],
            notes=t.get("notes", ""),
        )
        for t in raw_totals
    ]

    rollback_info = (
        f"To rollback all historical data for batch '{batch_id}': POST "
        f"'/api/historical-import/json/batches/{batch_id}/rollback' with "
        "{'confirm': true}. "
        f"This deletes game '{game_id}' (including all imported deliveries) "
        "and resets batch finalize markers."
    )

    return HistoricalImportApplyDeliveriesResponse(
        batch_id=batch_id,
        applied_game_id=game_id,
        deliveries_imported=deliveries_imported,
        innings_processed=innings_processed,
        status="deliveries_applied",
        totals_validation=totals_validation,
        warnings=warnings,
        rollback_info=rollback_info,
    )
