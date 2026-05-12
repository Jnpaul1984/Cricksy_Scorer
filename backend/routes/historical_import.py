from __future__ import annotations

import io
import json
import re
import zipfile
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Annotated

from backend.api.schemas.historical_import import (
    HistoricalImportApplyDeliveriesResponse,
    HistoricalImportApplyRequest,
    HistoricalImportApplyResponse,
    HistoricalImportBatchRecord,
    HistoricalImportBulkZipApplyFileResult,
    HistoricalImportBulkZipApplyResponse,
    HistoricalImportBulkZipDryRunResponse,
    HistoricalImportBulkZipFilePreview,
    HistoricalImportDryRunResponse,
    HistoricalImportRepairRequest,
    HistoricalImportRepairResponse,
    HistoricalImportRollbackRequest,
    HistoricalImportRollbackResponse,
    HistoricalImportTotalsValidation,
    HistoricalImportTrainingStatus,
)
from backend.security import get_current_user_optional
from backend.services.historical_import_apply_service import (
    apply_historical_batch,
    apply_historical_deliveries,
    rollback_historical_batch,
)
from backend.services.historical_import_backfill_service import (
    repair_legacy_historical_metadata,
)
from backend.services.historical_import_preview import build_dry_run_response
from backend.services.historical_import_service import (
    create_import_batch,
    find_duplicate_by_hash,
    find_duplicate_by_semantic_key,
    get_import_batch,
    list_import_batches,
)
from backend.sql_app import models
from backend.sql_app.database import get_db as _base_get_db
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
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


PHASE_5L_MAX_FILES = 100
PHASE_5L_MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024
PHASE_5L_MAX_TOTAL_UNCOMPRESSED_BYTES = 20 * 1024 * 1024
PHASE_5L_MAX_TOTAL_COMPRESSED_BYTES = 20 * 1024 * 1024


@dataclass(slots=True)
class _BulkJsonCandidate:
    file_name: str
    payload: bytes
    dry_run: HistoricalImportDryRunResponse
    status: str
    duplicate_within_zip: bool = False
    duplicate_batch_id: str | None = None
    semantic_duplicate: bool = False


def _is_unsafe_zip_path(entry_name: str) -> bool:
    normalized = entry_name.replace("\\", "/")
    if normalized.startswith("/") or normalized.startswith("//"):
        return True
    if re.match(r"^[a-zA-Z]:/", normalized):
        return True

    path_obj = PurePosixPath(normalized)
    return any(part == ".." for part in path_obj.parts)


def _parse_selected_file_names(selected_files: str) -> list[str]:
    try:
        parsed = json.loads(selected_files)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=422,
            detail="selected_files must be a JSON array of ZIP entry names.",
        ) from exc

    if not isinstance(parsed, list) or any(not isinstance(item, str) for item in parsed):
        raise HTTPException(
            status_code=422,
            detail="selected_files must be a JSON array of ZIP entry names.",
        )

    unique_names: list[str] = []
    seen: set[str] = set()
    for name in parsed:
        normalized_name = name.strip()
        if not normalized_name or normalized_name in seen:
            continue
        seen.add(normalized_name)
        unique_names.append(normalized_name)
    return unique_names


def _read_zip_entries(payload_bytes: bytes) -> list[tuple[zipfile.ZipInfo, bytes]]:
    try:
        with zipfile.ZipFile(io.BytesIO(payload_bytes)) as archive:
            members = [m for m in archive.infolist() if not m.is_dir()]
            if len(members) > PHASE_5L_MAX_FILES:
                raise HTTPException(
                    status_code=422,
                    detail=(
                        f"ZIP contains too many files ({len(members)}). "
                        f"Maximum supported is {PHASE_5L_MAX_FILES}."
                    ),
                )

            total_uncompressed = 0
            total_compressed = 0
            output: list[tuple[zipfile.ZipInfo, bytes]] = []

            for member in members:
                if _is_unsafe_zip_path(member.filename):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"ZIP entry '{member.filename}' is unsafe (path traversal or absolute path)."
                        ),
                    )

                if member.file_size > PHASE_5L_MAX_FILE_SIZE_BYTES:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            f"ZIP entry '{member.filename}' exceeds max size "
                            f"({PHASE_5L_MAX_FILE_SIZE_BYTES} bytes)."
                        ),
                    )

                total_uncompressed += member.file_size
                total_compressed += member.compress_size
                if total_uncompressed > PHASE_5L_MAX_TOTAL_UNCOMPRESSED_BYTES:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            "ZIP uncompressed payload exceeds limit "
                            f"({PHASE_5L_MAX_TOTAL_UNCOMPRESSED_BYTES} bytes)."
                        ),
                    )
                if total_compressed > PHASE_5L_MAX_TOTAL_COMPRESSED_BYTES:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            "ZIP compressed payload exceeds limit "
                            f"({PHASE_5L_MAX_TOTAL_COMPRESSED_BYTES} bytes)."
                        ),
                    )

                with archive.open(member, "r") as fp:
                    content = fp.read(PHASE_5L_MAX_FILE_SIZE_BYTES + 1)
                if len(content) > PHASE_5L_MAX_FILE_SIZE_BYTES:
                    raise HTTPException(
                        status_code=422,
                        detail=(
                            f"ZIP entry '{member.filename}' exceeds max size "
                            f"({PHASE_5L_MAX_FILE_SIZE_BYTES} bytes)."
                        ),
                    )
                output.append((member, content))

            return output
    except zipfile.BadZipFile as exc:
        raise HTTPException(status_code=415, detail="Only valid .zip uploads are supported.") from exc


async def _build_bulk_zip_preview(
    *,
    payload_bytes: bytes,
    source_filename: str | None,
    db: AsyncSession,
    owner_user_id: str | None,
    owner_org_id: str | None,
) -> tuple[HistoricalImportBulkZipDryRunResponse, dict[str, _BulkJsonCandidate]]:
    entries = _read_zip_entries(payload_bytes)

    files: list[HistoricalImportBulkZipFilePreview] = []
    candidates: dict[str, _BulkJsonCandidate] = {}
    hash_seen: dict[str, str] = {}
    semantic_seen: dict[str, str] = {}

    for member, entry_payload in entries:
        file_name = member.filename
        if not file_name.lower().endswith(".json"):
            files.append(
                HistoricalImportBulkZipFilePreview(
                    file_name=file_name,
                    status="unsupported",
                    message="Ignored: only .json entries are processed from the ZIP.",
                )
            )
            continue

        status_code, dry_run = build_dry_run_response(entry_payload)
        if status_code >= 400:
            file_preview = HistoricalImportBulkZipFilePreview(
                file_name=file_name,
                status="invalid",
                message="Invalid JSON payload.",
                detected_format=dry_run.detected_format,
                warnings=dry_run.warnings,
                errors=dry_run.errors,
                dry_run_preview=dry_run,
            )
            files.append(file_preview)
            candidates[file_name] = _BulkJsonCandidate(
                file_name=file_name,
                payload=entry_payload,
                dry_run=dry_run,
                status="invalid",
            )
            continue

        normalized_hash = dry_run.duplicate_detection.source_hash_sha256
        semantic_key = dry_run.duplicate_detection.semantic_key
        duplicate_within_zip = False
        duplicate_reason = ""

        if normalized_hash in hash_seen:
            duplicate_within_zip = True
            duplicate_reason = f"Duplicate inside ZIP: same content as '{hash_seen[normalized_hash]}'."
        elif semantic_key and semantic_key in semantic_seen:
            duplicate_within_zip = True
            duplicate_reason = f"Duplicate inside ZIP: same semantic match key as '{semantic_seen[semantic_key]}'."

        if not duplicate_within_zip:
            hash_seen[normalized_hash] = file_name
            if semantic_key:
                semantic_seen[semantic_key] = file_name

        duplicate_batch_id: str | None = None
        semantic_duplicate = False
        if not duplicate_within_zip:
            dup_by_hash = await find_duplicate_by_hash(
                db, normalized_hash, owner_user_id, owner_org_id
            )
            dup_by_semantic: models.HistoricalImportBatch | None = None
            if semantic_key:
                dup_by_semantic = await find_duplicate_by_semantic_key(
                    db, semantic_key, owner_user_id, owner_org_id
                )
            if dup_by_hash is not None:
                duplicate_batch_id = dup_by_hash.id
            elif dup_by_semantic is not None:
                duplicate_batch_id = dup_by_semantic.id
                semantic_duplicate = True

        status = "valid"
        message = "Valid JSON preview ready."
        if dry_run.status == "unsupported":
            status = "unsupported"
            message = "Unsupported historical JSON shape."
        elif dry_run.status != "valid":
            status = "invalid"
            message = "JSON preview found validation issues."
        elif duplicate_within_zip or duplicate_batch_id is not None:
            status = "duplicate"
            message = (
                duplicate_reason
                if duplicate_within_zip
                else (
                    "Duplicate against previously recorded imports (source hash or semantic key)."
                )
            )

        files.append(
            HistoricalImportBulkZipFilePreview(
                file_name=file_name,
                status=status,
                message=message,
                duplicate_within_zip=duplicate_within_zip,
                duplicate_batch_id=duplicate_batch_id,
                semantic_duplicate=semantic_duplicate,
                detected_format=dry_run.detected_format,
                warnings=dry_run.warnings,
                errors=dry_run.errors,
                dry_run_preview=dry_run,
            )
        )

        candidates[file_name] = _BulkJsonCandidate(
            file_name=file_name,
            payload=entry_payload,
            dry_run=dry_run,
            status=status,
            duplicate_within_zip=duplicate_within_zip,
            duplicate_batch_id=duplicate_batch_id,
            semantic_duplicate=semantic_duplicate,
        )

    summary = {
        "valid": sum(1 for f in files if f.status == "valid"),
        "invalid": sum(1 for f in files if f.status == "invalid"),
        "duplicate": sum(1 for f in files if f.status == "duplicate"),
        "unsupported": sum(1 for f in files if f.status == "unsupported"),
        "error": sum(1 for f in files if f.status == "error"),
    }

    preview = HistoricalImportBulkZipDryRunResponse(
        status="preview_ready",
        source_filename=source_filename,
        total_entries=len(entries),
        json_entries=len(candidates),
        non_json_entries=len([f for f in files if f.status == "unsupported" and f.dry_run_preview is None]),
        selected_apply_requires_confirm=True,
        max_files=PHASE_5L_MAX_FILES,
        max_file_size_bytes=PHASE_5L_MAX_FILE_SIZE_BYTES,
        max_total_uncompressed_bytes=PHASE_5L_MAX_TOTAL_UNCOMPRESSED_BYTES,
        max_total_compressed_bytes=PHASE_5L_MAX_TOTAL_COMPRESSED_BYTES,
        summary=summary,
        files=files,
    )
    return preview, candidates


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


@router.post("/bulk-zip/dry-run", response_model=HistoricalImportBulkZipDryRunResponse)
async def historical_json_bulk_zip_dry_run(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(_get_import_db),
    current_user: Annotated[models.User | None, Depends(get_current_user_optional)] = None,
) -> HistoricalImportBulkZipDryRunResponse:
    """Phase 5L: safe dry-run preview for a ZIP with multiple historical JSON files."""
    filename = file.filename or ""
    content_type = (file.content_type or "").lower()
    if not filename.lower().endswith(".zip") and content_type not in {
        "application/zip",
        "application/x-zip-compressed",
        "multipart/x-zip",
    }:
        raise HTTPException(status_code=415, detail="Only .zip uploads are supported for bulk import.")

    payload_bytes = await file.read()
    owner_user_id: str | None = current_user.id if current_user else None
    owner_org_id: str | None = current_user.org_id if current_user else None

    preview, _ = await _build_bulk_zip_preview(
        payload_bytes=payload_bytes,
        source_filename=file.filename or None,
        db=db,
        owner_user_id=owner_user_id,
        owner_org_id=owner_org_id,
    )
    return preview


@router.post("/bulk-zip/apply", response_model=HistoricalImportBulkZipApplyResponse)
async def historical_json_bulk_zip_apply(
    file: UploadFile = File(...),
    confirm: bool = Form(False),
    selected_files: str = Form(...),
    db: AsyncSession = Depends(_get_import_db),
    current_user: Annotated[models.User | None, Depends(get_current_user_optional)] = None,
) -> HistoricalImportBulkZipApplyResponse:
    """Phase 5L: apply selected safe files from a ZIP after explicit confirmation."""
    if not confirm:
        raise HTTPException(status_code=422, detail="confirm must be true for bulk apply.")

    filename = file.filename or ""
    content_type = (file.content_type or "").lower()
    if not filename.lower().endswith(".zip") and content_type not in {
        "application/zip",
        "application/x-zip-compressed",
        "multipart/x-zip",
    }:
        raise HTTPException(status_code=415, detail="Only .zip uploads are supported for bulk import.")

    selected_names = _parse_selected_file_names(selected_files)
    if not selected_names:
        raise HTTPException(status_code=422, detail="At least one selected file is required for bulk apply.")

    payload_bytes = await file.read()
    owner_user_id: str | None = current_user.id if current_user else None
    owner_org_id: str | None = current_user.org_id if current_user else None

    _, candidates = await _build_bulk_zip_preview(
        payload_bytes=payload_bytes,
        source_filename=file.filename or None,
        db=db,
        owner_user_id=owner_user_id,
        owner_org_id=owner_org_id,
    )

    results: list[HistoricalImportBulkZipApplyFileResult] = []
    for selected_name in selected_names:
        candidate = candidates.get(selected_name)
        if candidate is None:
            results.append(
                HistoricalImportBulkZipApplyFileResult(
                    file_name=selected_name,
                    status="error",
                    message="Selected file was not found in ZIP JSON entries.",
                )
            )
            continue

        if candidate.status != "valid":
            results.append(
                HistoricalImportBulkZipApplyFileResult(
                    file_name=selected_name,
                    status="skipped",
                    message=f"Skipped because file status is '{candidate.status}' in dry-run preview.",
                )
            )
            continue

        source_hash = candidate.dry_run.duplicate_detection.source_hash_sha256
        semantic_key = candidate.dry_run.duplicate_detection.semantic_key
        dup_by_hash = await find_duplicate_by_hash(db, source_hash, owner_user_id, owner_org_id)
        dup_by_semantic: models.HistoricalImportBatch | None = None
        if semantic_key:
            dup_by_semantic = await find_duplicate_by_semantic_key(
                db, semantic_key, owner_user_id, owner_org_id
            )
        if dup_by_hash is not None or dup_by_semantic is not None:
            duplicate_batch_id = dup_by_hash.id if dup_by_hash is not None else dup_by_semantic.id
            results.append(
                HistoricalImportBulkZipApplyFileResult(
                    file_name=selected_name,
                    status="skipped",
                    message=f"Skipped duplicate (existing batch: {duplicate_batch_id}).",
                    batch_id=duplicate_batch_id,
                )
            )
            continue

        batch = await create_import_batch(
            db,
            source_hash_sha256=source_hash,
            source_format=candidate.dry_run.detected_format,
            status=candidate.dry_run.status,
            error_count=len(candidate.dry_run.errors),
            warning_count=len(candidate.dry_run.warnings),
            innings_count=candidate.dry_run.innings_count,
            delivery_count=candidate.dry_run.delivery_count,
            dry_run_summary=candidate.dry_run.model_dump(),
            owner_user_id=owner_user_id,
            owner_org_id=owner_org_id,
            source_filename=f"{file.filename}:{selected_name}" if file.filename else selected_name,
            semantic_key=semantic_key,
        )
        game, _, error_msg = await apply_historical_batch(db, batch_id=batch.id, confirm=True)
        if error_msg is not None or game is None:
            results.append(
                HistoricalImportBulkZipApplyFileResult(
                    file_name=selected_name,
                    status="error",
                    message=error_msg or "Apply failed.",
                    batch_id=batch.id,
                )
            )
            continue

        results.append(
            HistoricalImportBulkZipApplyFileResult(
                file_name=selected_name,
                status="applied",
                message="Applied successfully.",
                batch_id=batch.id,
                applied_game_id=game.id,
            )
        )

    applied_count = sum(1 for r in results if r.status == "applied")
    skipped_count = sum(1 for r in results if r.status == "skipped")
    error_count = sum(1 for r in results if r.status == "error")
    if applied_count == len(results):
        status_value = "applied"
    elif applied_count == 0:
        status_value = "failed"
    else:
        status_value = "partial"

    return HistoricalImportBulkZipApplyResponse(
        status=status_value,
        source_filename=file.filename or None,
        selected_count=len(selected_names),
        applied_count=applied_count,
        skipped_count=skipped_count,
        error_count=error_count,
        selected_apply_requires_confirm=True,
        results=results,
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
    rolled_back_game_id, warnings, error_msg = await rollback_historical_batch(
        db,
        batch_id=batch_id,
        confirm=body.confirm,
        requester_user_id=(current_user.id if current_user else None),
        requester_org_id=(current_user.org_id if current_user else None),
    )

    if error_msg is not None:
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        if "confirm must be true" in error_msg.lower():
            raise HTTPException(status_code=422, detail=error_msg)
        if "not authorized" in error_msg.lower():
            raise HTTPException(status_code=403, detail=error_msg)
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


@router.get(
    "/batches/{batch_id}/training-status",
    response_model=HistoricalImportTrainingStatus,
    summary="Get training dataset readiness status for an import batch (Phase 5I)",
    description=(
        "Returns training-dataset eligibility metadata for a historical import batch. "
        "Eligibility is derived from existing batch fields — no DB migration required. "
        "Raw source JSON is NOT retained in Phase 5I (raw retention is deferred). "
        "Use this endpoint to check whether a batch can be registered in a future "
        "ML dataset registry/export phase."
    ),
)
async def get_historical_import_training_status(
    batch_id: str,
    db: AsyncSession = Depends(_get_import_db),
    current_user: Annotated[models.User | None, Depends(get_current_user_optional)] = None,
) -> HistoricalImportTrainingStatus:
    """Return training dataset readiness status for an import batch."""
    del current_user  # reserved for ownership scoping in future phases

    batch = await get_import_batch(db, batch_id)
    if batch is None:
        raise HTTPException(status_code=404, detail=f"Import batch '{batch_id}' not found.")

    # Derive training eligibility from existing fields — no migration needed
    exclusion_reason: str | None = None
    if not batch.is_finalized:
        exclusion_reason = "batch_not_finalized"
    elif batch.applied_game_id is None:
        exclusion_reason = "no_game_applied"
    elif batch.status != "valid":
        exclusion_reason = f"invalid_status:{batch.status}"
    elif batch.error_count > 0:
        exclusion_reason = "has_errors"

    training_eligible = exclusion_reason is None

    return HistoricalImportTrainingStatus(
        batch_id=batch.id,
        source_format=batch.source_format,
        source_hash_sha256=batch.source_hash_sha256,
        source_filename=batch.source_filename,
        semantic_key=batch.semantic_key,
        applied_game_id=batch.applied_game_id,
        imported_at=batch.created_at,
        innings_count=batch.innings_count,
        delivery_count=batch.delivery_count,
        training_eligible=training_eligible,
        exclusion_reason=exclusion_reason,
        raw_json_retained=False,
        training_registry_phase="deferred",
    )


@router.post(
    "/batches/{batch_id}/repair-metadata",
    response_model=HistoricalImportRepairResponse,
    summary="Backfill Phase 5J metadata onto a legacy historical import (Phase 5K)",
    description=(
        "Phase 5K: Safely repairs a legacy historical Game row that is missing "
        "Phase 5J metadata fields (event_name, season, match_number, source_dates). "
        "Requires explicit confirm=true. "
        "Only repairs completed historical import games. "
        "Never mutates live or in-progress matches. "
        "Never overwrites valid Phase 5J metadata already present. "
        "Refuses repair when the batch dry_run_summary does not contain the missing "
        "fields — callers must reimport in that case. "
        "All successful repairs are recorded in an audit log inside "
        "game.phases['historical_import']['_repair_log']."
    ),
)
async def repair_historical_import_metadata(
    batch_id: str,
    body: HistoricalImportRepairRequest,
    db: AsyncSession = Depends(_get_import_db),
    current_user: Annotated[models.User | None, Depends(get_current_user_optional)] = None,
) -> HistoricalImportRepairResponse:
    """Backfill Phase 5J metadata onto a legacy historical imported Game row."""
    del current_user  # reserved for ownership scoping in future phases

    result, warnings, error_msg = await repair_legacy_historical_metadata(
        db,
        batch_id=batch_id,
        confirm=body.confirm,
    )

    if error_msg is not None:
        # Determine appropriate HTTP status code from error type
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        if "confirm must be true" in error_msg.lower():
            raise HTTPException(status_code=422, detail=error_msg)
        if "reimport" in error_msg.lower():
            # Repair refused — business logic refusal (409 Conflict is appropriate)
            raise HTTPException(status_code=409, detail=error_msg)
        raise HTTPException(status_code=409, detail=error_msg)

    assert result is not None  # noqa: S101 - guaranteed by non-None error_msg check

    status_value = result.get("status", "refused")
    game_id_value: str | None = result.get("game_id")
    fields_added: list[str] = result.get("fields_added", [])

    # Validate status_value is a known literal before passing to Pydantic
    _valid_statuses = {"repaired", "already_complete", "refused"}
    if status_value not in _valid_statuses:
        status_value = "refused"

    detail_text: str
    if status_value == "repaired":
        detail_text = (
            f"Legacy metadata repaired for game '{game_id_value}'. "
            f"Fields added: {', '.join(fields_added) if fields_added else 'none'}."
        )
    elif status_value == "already_complete":
        detail_text = (
            f"Game '{game_id_value}' already has Phase 5J metadata. No changes were made."
        )
    else:
        detail_text = "Repair was not required."

    from typing import Literal, cast

    valid_status = cast(Literal["repaired", "already_complete", "refused"], status_value)
    return HistoricalImportRepairResponse(
        batch_id=batch_id,
        game_id=game_id_value,
        status=valid_status,
        fields_added=fields_added,
        warnings=warnings,
        detail=detail_text,
    )
