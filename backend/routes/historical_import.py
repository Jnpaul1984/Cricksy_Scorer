from __future__ import annotations

import datetime as dt
import hashlib
import io
import json
import re
import tempfile
import uuid
import zipfile
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Annotated, Any, Literal, cast

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
    HistoricalImportIssue,
    HistoricalImportRepairRequest,
    HistoricalImportRepairResponse,
    HistoricalImportRollbackRequest,
    HistoricalImportRollbackResponse,
    HistoricalImportTotalsValidation,
    HistoricalImportTrainingStatus,
    HistoricalVenueAliasRecord,
    HistoricalVenueIntelligenceRecord,
    HistoricalVenueResolutionSnapshot,
    HistoricalVenueUnresolvedRecord,
    HistoricalVenueUsageRecord,
    HistoricalOcrDryRunRequest,
    HistoricalOcrDryRunResponse,
    HistoricalOcrExtractionMetadata,
    HistoricalOcrRejectRequest,
    HistoricalOcrReviewCandidateResponse,
    HistoricalOcrReviewStatus,
    HistoricalOcrReviewUpdateRequest,
    HistoricalOcrSourceDocument,
    HistoricalBackfillApplyRequest,
    HistoricalBackfillApplyResponse,
    HistoricalBackfillAuditRequest,
    HistoricalBackfillAuditResponse,
    HistoricalSourcePayloadReattachApplyFileResult,
    HistoricalSourcePayloadReattachApplyResponse,
    HistoricalSourcePayloadReattachDryRunFileResult,
    HistoricalSourcePayloadReattachDryRunResponse,
    HistoricalSourcePayloadReattachMatchCandidate,
    HistoricalSourcePayloadReattachMetadata,
)
from backend.config import settings
from backend.security import get_current_user_optional
from backend.services.historical_import_apply_service import (
    apply_historical_batch,
    apply_historical_deliveries,
    rollback_historical_batch,
)
from backend.services.historical_import_delivery_service import extract_normalized_innings
from backend.services.historical_import_backfill_service import (
    repair_legacy_historical_metadata,
)
from backend.services.historical_import_reprocess_service import (
    apply_delivery_backfill,
    audit_delivery_backfill,
)
from backend.services.historical_import_preview import build_dry_run_response
from backend.services.historical_import_service import (
    create_import_batch,
    find_duplicate_by_hash,
    find_duplicate_by_semantic_key,
    get_import_batch,
    list_import_batches,
)
from backend.services.historical_venue_intelligence_service import (
    list_unresolved_venues,
    list_venue_aliases,
    list_venue_intelligence,
    list_venue_resolution_snapshots,
    list_venue_usage_stats,
    normalize_venue_name,
)
from backend.services.pdf_extraction_service import PdfExtractionResult, extract_text_from_pdf
from backend.services.s3_service import s3_service
from backend.sql_app import models
from backend.sql_app.database import get_db as _base_get_db
from fastapi import APIRouter, Depends, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import JSONResponse
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

import logging

_log = logging.getLogger(__name__)

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


PHASE_5L_MAX_FILES = 2000
PHASE_5L_MAX_FULL_APPLY_FILES = 100
PHASE_5L_MAX_FILE_SIZE_BYTES = 2 * 1024 * 1024
PHASE_5L_MAX_TOTAL_UNCOMPRESSED_BYTES = 100 * 1024 * 1024
PHASE_5L_MAX_TOTAL_COMPRESSED_BYTES = 100 * 1024 * 1024
PHASE_5L_SOURCE_FILENAME_PREFIX_SEPARATOR = "::"
PHASE_10I_CPL_MAX_BATCH_FILES = 25
PHASE_7_MAX_DOCUMENT_BYTES = 10 * 1024 * 1024
PHASE_7_ALLOWED_DOCUMENT_CONTENT_TYPES = frozenset(
    {
        "application/pdf",
        "image/png",
        "image/jpeg",
        "image/jpg",
        "image/webp",
    }
)
PHASE_7_ALLOWED_DOCUMENT_EXTENSIONS = frozenset({".pdf", ".png", ".jpg", ".jpeg", ".webp"})


@dataclass(slots=True)
class _BulkJsonCandidate:
    file_name: str
    dry_run: HistoricalImportDryRunResponse
    status: str
    duplicate_within_zip: bool = False
    duplicate_batch_id: str | None = None
    semantic_duplicate: bool = False


@dataclass(slots=True)
class _SourceReattachCandidate:
    file_name: str
    payload_bytes: bytes
    dry_run: HistoricalImportDryRunResponse
    metadata: HistoricalSourcePayloadReattachMetadata


@dataclass(slots=True)
class _HistoricalMatchTarget:
    batch: models.HistoricalImportBatch
    game: models.Game
    metadata: HistoricalSourcePayloadReattachMetadata
    venue_aliases: set[str]
    competition_aliases: set[str]
    source_dates: set[str]
    innings_runs: tuple[int, ...]


def _is_unsafe_zip_path(entry_name: str) -> bool:
    if "\x00" in entry_name:
        return True
    normalized = entry_name.replace("\\", "/")
    if normalized.startswith(("/", "//")):
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


def _is_controlled_cpl_candidate(candidate: _BulkJsonCandidate) -> bool:
    metadata_event = (candidate.dry_run.metadata_preview.event_name or "").strip().lower()
    competition_name = ""
    tournament_name = ""
    canonical_preview = candidate.dry_run.canonical_preview
    if canonical_preview is not None:
        competition_name = (
            (canonical_preview.competition_context.competition_name or "").strip().lower()
        )
        tournament_name = (
            (canonical_preview.competition_context.tournament_name or "").strip().lower()
        )

    cpl_sources = [metadata_event, competition_name, tournament_name]
    return any(
        ("caribbean premier league" in source) or bool(re.search(r"\bcpl\b", source))
        for source in cpl_sources
        if source
    )


def _validate_controlled_cpl_batch_selection(
    *,
    selected_names: list[str],
    candidates: dict[str, _BulkJsonCandidate],
    total_entries: int,
) -> None:
    selected_cpl: list[tuple[str, _BulkJsonCandidate]] = []
    for file_name in selected_names:
        candidate = candidates.get(file_name)
        if candidate is not None and _is_controlled_cpl_candidate(candidate):
            selected_cpl.append((file_name, candidate))

    if not selected_cpl:
        return

    if total_entries > PHASE_10I_CPL_MAX_BATCH_FILES:
        raise HTTPException(
            status_code=422,
            detail=(
                "Controlled CPL import blocks ZIP-wide scans above 25 entries. "
                "Use staged CPL batches only (1, 3-5, 10, then 20-25)."
            ),
        )

    selected_count = len(selected_cpl)
    in_ladder = (
        selected_count == 1
        or 3 <= selected_count <= 5
        or selected_count == 10
        or 20 <= selected_count <= PHASE_10I_CPL_MAX_BATCH_FILES
    )
    if not in_ladder:
        raise HTTPException(
            status_code=422,
            detail=(
                f"Controlled CPL staged ladder violation: selected {selected_count} CPL files. "
                "Allowed batch sizes are 1, 3-5, 10, or 20-25."
            ),
        )

    duplicate_selected = [
        file_name for file_name, candidate in selected_cpl if candidate.status == "duplicate"
    ]
    if duplicate_selected:
        raise HTTPException(
            status_code=409,
            detail=(
                "Controlled CPL import stopped: duplicate collisions require manual review "
                f"before apply ({', '.join(duplicate_selected)})."
            ),
        )

    invalid_selected = [
        file_name for file_name, candidate in selected_cpl if candidate.status != "valid"
    ]
    if invalid_selected:
        raise HTTPException(
            status_code=422,
            detail=(
                "Controlled CPL import stopped: every selected CPL file must pass dry-run "
                f"as valid before apply ({', '.join(invalid_selected)})."
            ),
        )


def _scan_zip_members(payload_bytes: bytes) -> list[zipfile.ZipInfo]:
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
            for member in members:
                if _is_unsafe_zip_path(member.filename):
                    raise HTTPException(
                        status_code=400,
                        detail=(
                            f"ZIP entry '{member.filename}' is unsafe (path traversal or absolute path)."
                        ),
                    )
                # Symlink entries are disallowed for bulk ZIP safety.
                if (member.external_attr >> 16) & 0o170000 == 0o120000:
                    raise HTTPException(
                        status_code=400,
                        detail=f"ZIP entry '{member.filename}' is unsafe (symlink entries are not allowed).",
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

            return members
    except zipfile.BadZipFile as exc:
        raise HTTPException(
            status_code=415, detail="Only valid .zip uploads are supported."
        ) from exc


def _sanitize_storage_name(file_name: str, source_hash_sha256: str) -> str:
    normalized = file_name.strip().replace("\\", "/")
    collapsed = re.sub(r"[^a-zA-Z0-9._-]+", "_", normalized)
    collapsed = collapsed.lstrip(".").replace("..", "_")
    safe_prefix = collapsed[:120] or "entry"
    return f"{safe_prefix}_{source_hash_sha256[:12]}.json"


def _sanitize_document_name(file_name: str, source_hash_sha256: str) -> str:
    normalized = file_name.strip().replace("\\", "/")
    suffix = Path(normalized).suffix.lower()
    ext = suffix if suffix in PHASE_7_ALLOWED_DOCUMENT_EXTENSIONS else ".bin"
    collapsed = re.sub(r"[^a-zA-Z0-9._-]+", "_", normalized)
    collapsed = collapsed.lstrip(".").replace("..", "_")
    base_name = Path(collapsed).stem[:100] or "source_document"
    return f"{base_name}_{source_hash_sha256[:12]}{ext}"


def _get_ocr_review_payload(batch: models.HistoricalImportBatch) -> dict:
    dry_run_summary = batch.dry_run_summary if isinstance(batch.dry_run_summary, dict) else {}
    review_payload = dry_run_summary.get("ocr_review")
    return review_payload if isinstance(review_payload, dict) else {}


def _as_ocr_issue_list(raw_issues: object) -> list[HistoricalImportIssue]:
    if not isinstance(raw_issues, list):
        return []
    issues: list[HistoricalImportIssue] = []
    for item in raw_issues:
        if not isinstance(item, dict):
            continue
        code = str(item.get("code") or "").strip()
        message = str(item.get("message") or "").strip()
        severity = str(item.get("severity", "error")).strip() or "error"
        if not code or not message:
            continue
        issues.append(
            HistoricalImportIssue(
                code=code,
                message=message,
                severity=severity if severity in {"error", "warning"} else "error",
                path=str(item.get("path") or "") or None,
            )
        )
    return issues


def _ocr_candidate_response(
    *,
    batch: models.HistoricalImportBatch,
    review_payload: dict,
) -> HistoricalOcrReviewCandidateResponse:
    source_document = review_payload.get("source_document")
    if not isinstance(source_document, dict):
        source_document = {}
    extraction = review_payload.get("extraction")
    if not isinstance(extraction, dict):
        extraction = {}
    raw_status = str(review_payload.get("status") or batch.status or "uploaded")
    allowed_statuses: set[str] = {
        "uploaded",
        "extracted",
        "needs_review",
        "reviewed",
        "rejected",
        "ready_for_dry_run",
        "dry_run_failed",
        "dry_run_passed",
        "applied_via_structured_import_only",
    }
    status_value: HistoricalOcrReviewStatus = cast(
        HistoricalOcrReviewStatus,
        raw_status if raw_status in allowed_statuses else "uploaded",
    )
    status_history = review_payload.get("status_history")
    if not isinstance(status_history, list):
        status_history = [status_value]
    status_history_values: list[HistoricalOcrReviewStatus] = []
    for item in status_history:
        text = str(item)
        if text in allowed_statuses:
            status_history_values.append(cast(HistoricalOcrReviewStatus, text))
    if not status_history_values:
        status_history_values = [status_value]
    validation_errors = _as_ocr_issue_list(review_payload.get("validation_errors"))
    dry_run_result = review_payload.get("dry_run_result")
    dry_run_preview = (
        HistoricalImportDryRunResponse.model_validate(dry_run_result)
        if isinstance(dry_run_result, dict)
        else None
    )

    return HistoricalOcrReviewCandidateResponse(
        candidate_id=batch.id,
        batch_id=batch.id,
        status=status_value,
        status_history=status_history_values,
        source_document=HistoricalOcrSourceDocument.model_validate(
            {
                "filename": str(
                    source_document.get("filename") or batch.source_filename or "unknown"
                ),
                "content_type": str(
                    source_document.get("content_type") or "application/octet-stream"
                ),
                "size_bytes": int(source_document.get("size_bytes") or 0),
                "storage": source_document.get("storage") or {},
            }
        ),
        extraction=HistoricalOcrExtractionMetadata.model_validate(
            {
                "method": str(extraction.get("method") or "manual_candidate_json"),
                "confidence": extraction.get("confidence"),
                "uncertainty_flags": extraction.get("uncertainty_flags") or [],
                "ocr_text": extraction.get("ocr_text"),
                "warnings": extraction.get("warnings") or [],
                "non_authoritative_notice": extraction.get("non_authoritative_notice")
                or "OCR/AI extraction is non-authoritative and must be reviewed before historical import.",
            }
        ),
        candidate_json=review_payload.get("candidate_json")
        if isinstance(review_payload.get("candidate_json"), dict)
        else None,
        reviewed_json=review_payload.get("reviewed_json")
        if isinstance(review_payload.get("reviewed_json"), dict)
        else None,
        reviewer_notes=(
            str(review_payload.get("reviewer_notes"))
            if isinstance(review_payload.get("reviewer_notes"), str)
            else None
        ),
        rejection_reason=(
            str(review_payload.get("rejection_reason"))
            if isinstance(review_payload.get("rejection_reason"), str)
            else None
        ),
        validation_errors=validation_errors,
        dry_run_result=dry_run_preview,
        dry_run_batch_id=(
            str(review_payload.get("dry_run_batch_id"))
            if review_payload.get("dry_run_batch_id") is not None
            else None
        ),
    )


def _resolve_intake_owner(owner_user_id: str | None, owner_org_id: str | None) -> str:
    if owner_org_id:
        return f"org_{re.sub(r'[^a-zA-Z0-9._-]+', '_', owner_org_id)}"
    if owner_user_id:
        return f"user_{re.sub(r'[^a-zA-Z0-9._-]+', '_', owner_user_id)}"
    return "anonymous"


def _store_bytes_with_fallback(
    *,
    key: str,
    payload: bytes,
    content_type: str,
) -> dict[str, str]:
    normalized_key = key.strip().replace("\\", "/")
    if _is_unsafe_zip_path(normalized_key):
        raise RuntimeError("Unsafe storage key path.")

    bucket = (settings.S3_COACH_VIDEOS_BUCKET or "").strip()
    if bucket:
        s3_service.upload_file_obj(
            payload, bucket=bucket, key=normalized_key, content_type=content_type
        )
        return {"storage": "s3", "bucket": bucket, "key": normalized_key}

    local_base = Path(tempfile.gettempdir()) / "cricksy_historical_imports"
    digest = hashlib.sha256(normalized_key.encode("utf-8")).hexdigest()
    target_path = local_base / digest[:2] / digest
    target_path.parent.mkdir(parents=True, exist_ok=True)
    target_path.write_bytes(payload)
    return {"storage": "local", "path": str(target_path), "logical_key": normalized_key}


def _normalize_match_text(value: object) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9]+", " ", str(value or "").strip().lower())).strip()


def _source_file_label(file_name: str | None) -> str:
    raw_name = str(file_name or "inline.json").strip().replace("\\", "/")
    if PHASE_5L_SOURCE_FILENAME_PREFIX_SEPARATOR in raw_name:
        raw_name = raw_name.split(PHASE_5L_SOURCE_FILENAME_PREFIX_SEPARATOR, 1)[1]
    return raw_name or "inline.json"


def _source_file_token(file_name: str | None) -> str:
    return Path(_source_file_label(file_name)).name.lower()


def _maybe_int(value: object) -> int | None:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _first_text(*values: object) -> str | None:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return None


def _team_names_from_game(game: models.Game) -> list[str]:
    teams: list[str] = []
    for team_blob in (game.team_a, game.team_b):
        if isinstance(team_blob, dict):
            name = str(team_blob.get("name") or "").strip()
            if name:
                teams.append(name)
    return teams


def _team_signature(teams: list[str]) -> tuple[str, ...]:
    return tuple(
        sorted(_normalize_match_text(team) for team in teams if _normalize_match_text(team))
    )


def _innings_runs_from_preview(innings_preview: list[object]) -> tuple[int, ...]:
    runs: list[int] = []
    for inning in innings_preview:
        if not isinstance(inning, dict):
            continue
        runs_value = _maybe_int(inning.get("runs"))
        if runs_value is not None:
            runs.append(runs_value)
    return tuple(runs)


def _candidate_payload_metadata(
    *,
    file_name: str,
    payload_bytes: bytes,
    dry_run: HistoricalImportDryRunResponse,
) -> HistoricalSourcePayloadReattachMetadata:
    canonical = dry_run.canonical_preview
    competition_context = canonical.competition_context if canonical is not None else None
    venue_context = canonical.venue_context if canonical is not None else None

    expected_deliveries = 0
    expected_wickets = 0
    registry_people_available = False
    parsed_dict: dict[str, Any] | None = None

    try:
        parsed_raw = json.loads(payload_bytes.decode("utf-8"))
        parsed_dict = parsed_raw if isinstance(parsed_raw, dict) else None
        info_raw = parsed_dict.get("info") if parsed_dict is not None else None
        info: dict[str, Any] = info_raw if isinstance(info_raw, dict) else {}
        registry_raw = info.get("registry")
        registry: dict[str, Any] = registry_raw if isinstance(registry_raw, dict) else {}
        people = registry.get("people")
        registry_people_available = bool(people)
    except Exception:
        parsed_dict = None

    try:
        innings = extract_normalized_innings(parsed_dict or {})
        expected_deliveries = sum(len(inn["deliveries"]) for inn in innings)
        expected_wickets = sum(
            1 for inn in innings for delivery in inn["deliveries"] if delivery.get("is_wicket")
        )
    except Exception:
        expected_deliveries = dry_run.delivery_count
        expected_wickets = sum(
            _maybe_int(
                getattr(inning, "wickets", None)
                if not isinstance(inning, dict)
                else inning.get("wickets")
            )
            or 0
            for inning in dry_run.innings_preview
        )

    return HistoricalSourcePayloadReattachMetadata(
        competition_name=_first_text(
            competition_context.competition_name if competition_context is not None else None,
            competition_context.tournament_name if competition_context is not None else None,
            dry_run.metadata_preview.event_name,
        ),
        season=dry_run.metadata_preview.season,
        match_number=dry_run.metadata_preview.match_number,
        date=dry_run.metadata_preview.date,
        teams=list(dry_run.teams_preview),
        venue=_first_text(
            dry_run.metadata_preview.venue,
            venue_context.venue_name if venue_context is not None else None,
        ),
        city=venue_context.city if venue_context is not None else None,
        source_filename=_source_file_label(file_name),
        registry_people_available=registry_people_available,
        expected_deliveries=expected_deliveries,
        expected_wickets=expected_wickets,
    )


async def _load_historical_reattach_targets(
    db: AsyncSession,
) -> list[_HistoricalMatchTarget]:
    rows = (
        await db.execute(
            select(models.HistoricalImportBatch, models.Game).join(
                models.Game, models.HistoricalImportBatch.applied_game_id == models.Game.id
            )
        )
    ).all()

    targets: list[_HistoricalMatchTarget] = []
    for batch, game in rows:
        phases = game.phases if isinstance(game.phases, dict) else {}
        hist_meta_raw = phases.get("historical_import")
        hist_meta: dict[str, Any] = hist_meta_raw if isinstance(hist_meta_raw, dict) else {}
        if not hist_meta.get("is_historical"):
            continue
        venue_context_raw = hist_meta.get("venue_context")
        venue_context: dict[str, Any] = (
            venue_context_raw if isinstance(venue_context_raw, dict) else {}
        )
        venue_resolution_raw = hist_meta.get("venue_resolution")
        venue_resolution: dict[str, Any] = (
            venue_resolution_raw if isinstance(venue_resolution_raw, dict) else {}
        )
        source_dates_raw = hist_meta.get("source_dates")
        source_dates = source_dates_raw if isinstance(source_dates_raw, list) else []
        innings_summary_raw = phases.get("historical_innings_summary")
        innings_summary = innings_summary_raw if isinstance(innings_summary_raw, list) else []
        target_metadata = HistoricalSourcePayloadReattachMetadata(
            competition_name=_first_text(
                hist_meta.get("competition_name"),
                hist_meta.get("event_name"),
                hist_meta.get("tournament_name"),
            ),
            season=_first_text(hist_meta.get("season")),
            match_number=_maybe_int(hist_meta.get("match_number")),
            date=_first_text(hist_meta.get("match_date"), *source_dates),
            teams=_team_names_from_game(game),
            venue=_first_text(hist_meta.get("venue"), venue_context.get("venue_name")),
            city=_first_text(venue_context.get("city")),
            source_filename=batch.source_filename,
            registry_people_available=False,
            expected_deliveries=batch.delivery_count,
            expected_wickets=sum(
                (_maybe_int(inning.get("wickets")) or 0)
                for inning in innings_summary
                if isinstance(inning, dict)
            ),
        )
        venue_aliases = {
            normalize_venue_name(value)
            for value in (
                target_metadata.venue,
                venue_context.get("source_venue_raw"),
                venue_resolution.get("canonical_name"),
            )
            if normalize_venue_name(value)
        }
        competition_aliases = {
            _normalize_match_text(value)
            for value in (
                hist_meta.get("competition_name"),
                hist_meta.get("event_name"),
                hist_meta.get("tournament_name"),
            )
            if _normalize_match_text(value)
        }
        dry_run_summary = batch.dry_run_summary if isinstance(batch.dry_run_summary, dict) else {}
        canonical_preview_raw = dry_run_summary.get("canonical_preview")
        canonical_preview: dict[str, Any] = (
            canonical_preview_raw if isinstance(canonical_preview_raw, dict) else {}
        )
        competition_context_raw = canonical_preview.get("competition_context")
        competition_context: dict[str, Any] = (
            competition_context_raw if isinstance(competition_context_raw, dict) else {}
        )
        for value in (
            competition_context.get("competition_name"),
            competition_context.get("tournament_name"),
        ):
            normalized = _normalize_match_text(value)
            if normalized:
                competition_aliases.add(normalized)
        targets.append(
            _HistoricalMatchTarget(
                batch=batch,
                game=game,
                metadata=target_metadata,
                venue_aliases=venue_aliases,
                competition_aliases=competition_aliases,
                source_dates={
                    str(value).strip()
                    for value in [target_metadata.date, *source_dates]
                    if str(value or "").strip()
                },
                innings_runs=_innings_runs_from_preview(innings_summary),
            )
        )
    return targets


def _build_reattach_match_candidate(
    *,
    candidate: _SourceReattachCandidate,
    target: _HistoricalMatchTarget,
) -> HistoricalSourcePayloadReattachMatchCandidate | None:
    candidate_competition = _normalize_match_text(candidate.metadata.competition_name)
    candidate_season = _normalize_match_text(candidate.metadata.season)
    candidate_date = str(candidate.metadata.date or "").strip()
    candidate_teams = _team_signature(candidate.metadata.teams)
    candidate_venue = normalize_venue_name(candidate.metadata.venue)
    candidate_city = _normalize_match_text(candidate.metadata.city)
    candidate_match_number = candidate.metadata.match_number
    candidate_source_filename = _source_file_token(candidate.file_name)
    candidate_innings_runs = _innings_runs_from_preview(
        [inning.model_dump(mode="python") for inning in candidate.dry_run.innings_preview]
    )

    teams_match = candidate_teams and candidate_teams == _team_signature(target.metadata.teams)
    date_match = bool(candidate_date and candidate_date in target.source_dates)
    competition_match = bool(
        candidate_competition and candidate_competition in target.competition_aliases
    )
    season_match = bool(
        candidate_season and candidate_season == _normalize_match_text(target.metadata.season)
    )
    if not (teams_match and date_match and competition_match and season_match):
        return None

    matched_on = ["date", "teams", "competition", "season"]
    match_number_match = (
        candidate_match_number is not None
        and target.metadata.match_number is not None
        and candidate_match_number == target.metadata.match_number
    )
    venue_match = bool(candidate_venue and candidate_venue in target.venue_aliases)
    source_filename_match = bool(
        candidate_source_filename
        and candidate_source_filename == _source_file_token(target.metadata.source_filename)
    )
    innings_total_match = bool(
        candidate_innings_runs and candidate_innings_runs == target.innings_runs
    )
    city_match = bool(
        candidate_city and candidate_city == _normalize_match_text(target.metadata.city)
    )

    if match_number_match:
        matched_on.append("match_number")
    if venue_match:
        matched_on.append("venue")
    if source_filename_match:
        matched_on.append("source_filename")
    if innings_total_match:
        matched_on.append("innings_totals")
    if city_match:
        matched_on.append("city")

    confidence = "exact_match" if (match_number_match or venue_match) else "likely_match"
    return HistoricalSourcePayloadReattachMatchCandidate(
        match_id=target.game.id,
        batch_id=target.batch.id,
        confidence=cast(Literal["exact_match", "likely_match"], confidence),
        matched_on=matched_on,
        source_json_retained=False,
        metadata=target.metadata,
    )


def _batch_has_retained_source(batch: models.HistoricalImportBatch) -> bool:
    dry_run = batch.dry_run_summary if isinstance(batch.dry_run_summary, dict) else {}
    reattach_raw = dry_run.get("source_payload_reattach")
    reattach: dict[str, Any] = reattach_raw if isinstance(reattach_raw, dict) else {}
    reattach_storage_raw = reattach.get("storage")
    reattach_storage: dict[str, Any] = (
        reattach_storage_raw if isinstance(reattach_storage_raw, dict) else {}
    )
    if isinstance(reattach_storage.get("raw"), dict):
        return True
    intake_raw = dry_run.get("large_zip_intake")
    intake: dict[str, Any] = intake_raw if isinstance(intake_raw, dict) else {}
    storage_raw = intake.get("storage")
    storage: dict[str, Any] = storage_raw if isinstance(storage_raw, dict) else {}
    return isinstance(storage.get("raw"), dict)


def _source_reattach_file_result(
    *,
    file_name: str,
    status: str,
    match_confidence: str,
    message: str,
    metadata: HistoricalSourcePayloadReattachMetadata,
    matched_target: HistoricalSourcePayloadReattachMatchCandidate | None = None,
    candidate_matches: list[HistoricalSourcePayloadReattachMatchCandidate] | None = None,
    warnings: list[str] | None = None,
) -> HistoricalSourcePayloadReattachDryRunFileResult:
    return HistoricalSourcePayloadReattachDryRunFileResult(
        file_name=file_name,
        status=cast(Literal["ready", "invalid", "unsupported", "error"], status),
        match_confidence=cast(
            Literal["exact_match", "likely_match", "ambiguous", "no_match"],
            match_confidence,
        ),
        blocked_from_apply=match_confidence in {"ambiguous", "no_match"} or status != "ready",
        message=message,
        metadata=metadata,
        matched_target=matched_target,
        candidate_matches=candidate_matches or [],
        warnings=warnings or [],
    )


async def _build_source_reattach_preview(
    *,
    payload_bytes: bytes,
    source_filename: str | None,
    db: AsyncSession,
) -> tuple[HistoricalSourcePayloadReattachDryRunResponse, dict[str, _SourceReattachCandidate]]:
    targets = await _load_historical_reattach_targets(db)
    file_results: list[HistoricalSourcePayloadReattachDryRunFileResult] = []
    candidate_lookup: dict[str, _SourceReattachCandidate] = {}

    def _evaluate_candidate(file_name: str, raw_payload: bytes) -> None:
        status_code, dry_run = build_dry_run_response(raw_payload)
        metadata = _candidate_payload_metadata(
            file_name=file_name,
            payload_bytes=raw_payload,
            dry_run=dry_run,
        )
        warnings = [warning.message for warning in dry_run.warnings]
        if status_code >= 400 or dry_run.status != "valid":
            file_results.append(
                _source_reattach_file_result(
                    file_name=file_name,
                    status="unsupported" if dry_run.status == "unsupported" else "invalid",
                    match_confidence="no_match",
                    message=(
                        dry_run.errors[0].message
                        if dry_run.errors
                        else "Source payload could not be parsed for deterministic reattach."
                    ),
                    metadata=metadata,
                    warnings=warnings,
                )
            )
            return

        candidate = _SourceReattachCandidate(
            file_name=file_name,
            payload_bytes=raw_payload,
            dry_run=dry_run,
            metadata=metadata,
        )
        matches = [
            match
            for target in targets
            if (match := _build_reattach_match_candidate(candidate=candidate, target=target))
            is not None
        ]
        matches.sort(
            key=lambda item: (
                1 if item.confidence == "exact_match" else 0,
                len(item.matched_on),
            ),
            reverse=True,
        )
        if not matches:
            file_results.append(
                _source_reattach_file_result(
                    file_name=file_name,
                    status="ready",
                    match_confidence="no_match",
                    message=(
                        "No safe historical match matched date + teams + competition + season."
                    ),
                    metadata=metadata,
                    warnings=warnings,
                )
            )
            candidate_lookup[file_name] = candidate
            return

        top_match = matches[0]
        second_match = matches[1] if len(matches) > 1 else None
        is_ambiguous = bool(
            second_match is not None
            and (
                top_match.confidence == second_match.confidence
                or top_match.confidence == "likely_match"
            )
        )
        if is_ambiguous:
            file_results.append(
                _source_reattach_file_result(
                    file_name=file_name,
                    status="ready",
                    match_confidence="ambiguous",
                    message=(
                        "Multiple historical matches satisfy the deterministic matching rules; "
                        "apply is blocked."
                    ),
                    metadata=metadata,
                    candidate_matches=matches[:5],
                    warnings=warnings,
                )
            )
            candidate_lookup[file_name] = candidate
            return

        top_target_batch = next(
            (target.batch for target in targets if target.batch.id == top_match.batch_id),
            None,
        )
        if top_target_batch is not None:
            top_match.source_json_retained = _batch_has_retained_source(top_target_batch)

        result = _source_reattach_file_result(
            file_name=file_name,
            status="ready",
            match_confidence=top_match.confidence,
            message=(
                "Matching historical record already retains source JSON; overwrite is blocked."
                if top_match.source_json_retained
                else (
                    "Deterministic exact match found."
                    if top_match.confidence == "exact_match"
                    else "Deterministic likely match found; operator confirmation required."
                )
            ),
            metadata=metadata,
            matched_target=top_match,
            candidate_matches=matches[:5],
            warnings=warnings,
        )
        if top_match.source_json_retained:
            result.blocked_from_apply = True
        else:
            result.blocked_from_apply = False
        file_results.append(result)
        candidate_lookup[file_name] = candidate

    is_zip_upload = bool(source_filename and source_filename.lower().endswith(".zip"))
    if not is_zip_upload:
        try:
            is_zip_upload = zipfile.is_zipfile(io.BytesIO(payload_bytes))
        except Exception:
            is_zip_upload = False

    if is_zip_upload:
        members = _scan_zip_members(payload_bytes)
        with zipfile.ZipFile(io.BytesIO(payload_bytes)) as archive:
            for member in members:
                if not member.filename.lower().endswith(".json"):
                    file_results.append(
                        _source_reattach_file_result(
                            file_name=member.filename,
                            status="unsupported",
                            match_confidence="no_match",
                            message="Ignored: only .json entries can be reattached from a ZIP repair payload.",
                            metadata=HistoricalSourcePayloadReattachMetadata(
                                source_filename=_source_file_label(member.filename)
                            ),
                        )
                    )
                    continue
                with archive.open(member, "r") as fp:
                    _evaluate_candidate(member.filename, fp.read(member.file_size))
    else:
        _evaluate_candidate(_source_file_label(source_filename), payload_bytes)

    ready_candidates = sum(
        1
        for item in file_results
        if item.status == "ready"
        and not item.blocked_from_apply
        and item.matched_target is not None
    )
    return (
        HistoricalSourcePayloadReattachDryRunResponse(
            status="preview_ready",
            source_filename=source_filename,
            total_candidates=len(file_results),
            ready_candidates=ready_candidates,
            blocked_candidates=max(len(file_results) - ready_candidates, 0),
            files=file_results,
        ),
        candidate_lookup,
    )


def _parse_source_reattach_selection(selected_mappings: str) -> list[tuple[str, str]]:
    try:
        parsed = json.loads(selected_mappings)
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=422,
            detail="selected_mappings must be a JSON array of {file_name,batch_id} objects.",
        ) from exc
    if not isinstance(parsed, list):
        raise HTTPException(
            status_code=422,
            detail="selected_mappings must be a JSON array of {file_name,batch_id} objects.",
        )

    mappings: list[tuple[str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in parsed:
        if not isinstance(item, dict):
            raise HTTPException(
                status_code=422,
                detail="selected_mappings must contain only objects.",
            )
        file_name = _source_file_label(str(item.get("file_name") or "").strip())
        batch_id = str(item.get("batch_id") or "").strip()
        if not file_name or not batch_id:
            raise HTTPException(
                status_code=422,
                detail="Each selected mapping must include non-empty file_name and batch_id.",
            )
        key = (file_name, batch_id)
        if key in seen:
            continue
        seen.add(key)
        mappings.append(key)

    if not mappings:
        raise HTTPException(
            status_code=422,
            detail="Select at least one exact/likely reattach mapping before apply.",
        )
    return mappings


async def _build_bulk_zip_preview(
    *,
    payload_bytes: bytes,
    source_filename: str | None,
    db: AsyncSession,
    owner_user_id: str | None,
    owner_org_id: str | None,
) -> tuple[HistoricalImportBulkZipDryRunResponse, dict[str, _BulkJsonCandidate]]:
    members = _scan_zip_members(payload_bytes)
    metadata_only_intake_required = len(members) > PHASE_5L_MAX_FULL_APPLY_FILES

    files: list[HistoricalImportBulkZipFilePreview] = []
    candidates: dict[str, _BulkJsonCandidate] = {}
    hash_seen: dict[str, str] = {}
    semantic_seen: dict[str, str] = {}

    with zipfile.ZipFile(io.BytesIO(payload_bytes)) as archive:
        for member in members:
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

            with archive.open(member, "r") as fp:
                entry_payload = fp.read(member.file_size)

            status_code, dry_run = build_dry_run_response(entry_payload)
            if status_code >= 400:
                file_preview = HistoricalImportBulkZipFilePreview(
                    file_name=file_name,
                    status="invalid",
                    message="Invalid JSON payload.",
                    detected_format=dry_run.detected_format,
                    warnings=dry_run.warnings,
                    errors=dry_run.errors,
                    dry_run_preview=None if metadata_only_intake_required else dry_run,
                )
                files.append(file_preview)
                candidates[file_name] = _BulkJsonCandidate(
                    file_name=file_name,
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
                duplicate_reason = (
                    f"Duplicate inside ZIP: same content as '{hash_seen[normalized_hash]}'."
                )
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
                    dry_run_preview=None if metadata_only_intake_required else dry_run,
                )
            )

            candidates[file_name] = _BulkJsonCandidate(
                file_name=file_name,
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
        total_entries=len(members),
        files_scanned=len(members),
        json_entries=len(candidates),
        non_json_entries=len(
            [f for f in files if f.status == "unsupported" and f.dry_run_preview is None]
        ),
        metadata_only_intake_required=metadata_only_intake_required,
        metadata_only_pending_count=(
            summary.get("valid", 0) if metadata_only_intake_required else 0
        ),
        intake_status="scanned",
        cost_control_message=(
            "Large ZIP detected. Stored safely for later processing; full import is deferred."
            if metadata_only_intake_required
            else None
        ),
        full_import_deferred=metadata_only_intake_required,
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
        schema_classification=response.schema_classification,
        canonical_preview=response.canonical_preview,
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


async def _get_ocr_candidate_batch_or_404(
    db: AsyncSession,
    candidate_id: str,
) -> models.HistoricalImportBatch:
    batch = await get_import_batch(db, candidate_id)
    if batch is None or batch.source_format != "ocr_review_candidate":
        raise HTTPException(status_code=404, detail="OCR review candidate not found.")
    return batch


@router.post("/ocr-review/candidates", response_model=HistoricalOcrReviewCandidateResponse)
async def create_historical_ocr_review_candidate(
    file: UploadFile = File(...),
    extraction_method: str = Form("manual_candidate_json"),
    extraction_confidence: float | None = Form(None),
    uncertainty_flags: str | None = Form(None),
    candidate_json: str | None = Form(None),
    ocr_text: str | None = Form(None),
    db: AsyncSession = Depends(_get_import_db),
    current_user: Annotated[models.User | None, Depends(get_current_user_optional)] = None,
) -> HistoricalOcrReviewCandidateResponse:
    filename = file.filename or "document"
    content_type = (file.content_type or "").lower()
    ext = Path(filename).suffix.lower()
    if content_type not in PHASE_7_ALLOWED_DOCUMENT_CONTENT_TYPES and ext not in (
        PHASE_7_ALLOWED_DOCUMENT_EXTENSIONS
    ):
        raise HTTPException(
            status_code=415,
            detail="Only PDF/PNG/JPEG/WEBP scorecard documents are supported.",
        )

    payload = await file.read()
    if not payload:
        raise HTTPException(status_code=422, detail="Uploaded document is empty.")
    if len(payload) > PHASE_7_MAX_DOCUMENT_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"Document exceeds max size ({PHASE_7_MAX_DOCUMENT_BYTES} bytes).",
        )

    if extraction_confidence is not None and not (0 <= extraction_confidence <= 1):
        raise HTTPException(
            status_code=422, detail="extraction_confidence must be between 0 and 1."
        )

    parsed_uncertainty_flags: list[str] = []
    if uncertainty_flags:
        try:
            parsed = json.loads(uncertainty_flags)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=422,
                detail="uncertainty_flags must be a JSON array of strings.",
            ) from exc
        if not isinstance(parsed, list) or any(not isinstance(item, str) for item in parsed):
            raise HTTPException(
                status_code=422,
                detail="uncertainty_flags must be a JSON array of strings.",
            )
        parsed_uncertainty_flags = [item.strip() for item in parsed if item.strip()]

    parsed_candidate_json: dict | None = None
    if candidate_json:
        try:
            parsed_candidate = json.loads(candidate_json)
        except json.JSONDecodeError as exc:
            raise HTTPException(
                status_code=422, detail="candidate_json must be valid JSON."
            ) from exc
        if not isinstance(parsed_candidate, dict):
            raise HTTPException(status_code=422, detail="candidate_json must be a JSON object.")
        parsed_candidate_json = parsed_candidate

    # Phase 7C — optional PDF text extraction.
    # Runs only when extraction_method="pdf_text_extract" and the upload is a PDF.
    # Extraction output is non-authoritative; it populates candidate metadata only.
    # Operator-supplied values (ocr_text, extraction_confidence, uncertainty_flags) always
    # take precedence over auto-extracted values.
    extraction_warnings: list[str] = []
    normalized_method = extraction_method.strip() or "manual_candidate_json"
    is_pdf_upload = content_type == "application/pdf" or ext == ".pdf"
    if normalized_method == "pdf_text_extract" and is_pdf_upload:
        pdf_result: PdfExtractionResult = extract_text_from_pdf(payload)
        extraction_warnings = pdf_result.warnings
        if ocr_text is None or not ocr_text.strip():
            ocr_text = pdf_result.extracted_text
        if extraction_confidence is None:
            extraction_confidence = pdf_result.confidence
        if not parsed_uncertainty_flags:
            parsed_uncertainty_flags = pdf_result.uncertainty_flags

    source_hash = hashlib.sha256(payload).hexdigest()
    owner_scope = _resolve_intake_owner(
        current_user.id if current_user else None,
        current_user.org_id if current_user else None,
    )
    candidate_id = str(uuid.uuid4())
    safe_document_name = _sanitize_document_name(filename, source_hash)
    base_key = f"historical-imports/{owner_scope}/{candidate_id}/ocr-review"
    source_doc_key = f"{base_key}/source/{safe_document_name}"
    source_doc_storage = _store_bytes_with_fallback(
        key=source_doc_key,
        payload=payload,
        content_type=content_type or "application/octet-stream",
    )

    initial_status: HistoricalOcrReviewStatus = "uploaded"
    status_history: list[HistoricalOcrReviewStatus] = ["uploaded"]
    if parsed_candidate_json is not None or (ocr_text or "").strip():
        initial_status = "needs_review"
        status_history.extend(["extracted", "needs_review"])

    review_payload = {
        "status": initial_status,
        "status_history": status_history,
        "source_document": {
            "filename": filename,
            "content_type": content_type or "application/octet-stream",
            "size_bytes": len(payload),
            "storage": source_doc_storage,
        },
        "extraction": {
            "method": normalized_method,
            "confidence": extraction_confidence,
            "uncertainty_flags": parsed_uncertainty_flags,
            "ocr_text": (ocr_text or None),
            "warnings": extraction_warnings,
            "non_authoritative_notice": (
                "OCR/AI extraction is non-authoritative and must be reviewed before historical import."
            ),
        },
        "candidate_json": parsed_candidate_json,
        "reviewed_json": None,
        "reviewer_notes": None,
        "rejection_reason": None,
        "validation_errors": [],
        "dry_run_result": None,
        "dry_run_batch_id": None,
    }

    batch = await create_import_batch(
        db,
        batch_id=candidate_id,
        source_hash_sha256=source_hash,
        source_format="ocr_review_candidate",
        status=initial_status,
        error_count=0,
        warning_count=0,
        innings_count=0,
        delivery_count=0,
        dry_run_summary={"ocr_review": review_payload},
        owner_user_id=current_user.id if current_user else None,
        owner_org_id=current_user.org_id if current_user else None,
        source_filename=filename,
        semantic_key=None,
    )
    return _ocr_candidate_response(batch=batch, review_payload=review_payload)


@router.get(
    "/ocr-review/candidates/{candidate_id}", response_model=HistoricalOcrReviewCandidateResponse
)
async def get_historical_ocr_review_candidate(
    candidate_id: str,
    db: AsyncSession = Depends(_get_import_db),
) -> HistoricalOcrReviewCandidateResponse:
    batch = await _get_ocr_candidate_batch_or_404(db, candidate_id)
    review_payload = _get_ocr_review_payload(batch)
    return _ocr_candidate_response(batch=batch, review_payload=review_payload)


@router.patch(
    "/ocr-review/candidates/{candidate_id}/review",
    response_model=HistoricalOcrReviewCandidateResponse,
)
async def review_historical_ocr_candidate(
    candidate_id: str,
    body: HistoricalOcrReviewUpdateRequest,
    db: AsyncSession = Depends(_get_import_db),
) -> HistoricalOcrReviewCandidateResponse:
    batch = await _get_ocr_candidate_batch_or_404(db, candidate_id)
    review_payload = _get_ocr_review_payload(batch)
    current_status = str(review_payload.get("status") or batch.status or "uploaded")
    if current_status == "rejected":
        raise HTTPException(
            status_code=409, detail="Rejected OCR review candidates cannot be reviewed."
        )

    extraction_payload = review_payload.get("extraction")
    if not isinstance(extraction_payload, dict):
        extraction_payload = {}
    extraction_payload["uncertainty_flags"] = [
        item.strip() for item in body.uncertainty_flags if item.strip()
    ]
    review_payload["extraction"] = extraction_payload
    review_payload["reviewed_json"] = body.reviewed_json
    review_payload["reviewer_notes"] = body.reviewer_notes
    review_payload["status"] = "ready_for_dry_run"

    history = review_payload.get("status_history")
    if not isinstance(history, list):
        history = []
    for marker in ("reviewed", "ready_for_dry_run"):
        if marker not in history:
            history.append(marker)
    review_payload["status_history"] = history

    dry_summary = dict(batch.dry_run_summary) if isinstance(batch.dry_run_summary, dict) else {}
    dry_summary["ocr_review"] = review_payload
    await db.execute(
        update(models.HistoricalImportBatch)
        .where(models.HistoricalImportBatch.id == batch.id)
        .values(
            dry_run_summary=dry_summary,
            status="ready_for_dry_run",
        )
    )
    await db.commit()
    batch = await _get_ocr_candidate_batch_or_404(db, candidate_id)
    return _ocr_candidate_response(batch=batch, review_payload=review_payload)


@router.post(
    "/ocr-review/candidates/{candidate_id}/reject",
    response_model=HistoricalOcrReviewCandidateResponse,
)
async def reject_historical_ocr_candidate(
    candidate_id: str,
    body: HistoricalOcrRejectRequest,
    db: AsyncSession = Depends(_get_import_db),
) -> HistoricalOcrReviewCandidateResponse:
    batch = await _get_ocr_candidate_batch_or_404(db, candidate_id)
    review_payload = _get_ocr_review_payload(batch)
    review_payload["status"] = "rejected"
    review_payload["rejection_reason"] = body.reason.strip()
    history = review_payload.get("status_history")
    if not isinstance(history, list):
        history = []
    if "rejected" not in history:
        history.append("rejected")
    review_payload["status_history"] = history

    dry_summary = dict(batch.dry_run_summary) if isinstance(batch.dry_run_summary, dict) else {}
    dry_summary["ocr_review"] = review_payload
    await db.execute(
        update(models.HistoricalImportBatch)
        .where(models.HistoricalImportBatch.id == batch.id)
        .values(
            dry_run_summary=dry_summary,
            status="rejected",
        )
    )
    await db.commit()
    batch = await _get_ocr_candidate_batch_or_404(db, candidate_id)
    return _ocr_candidate_response(batch=batch, review_payload=review_payload)


@router.post(
    "/ocr-review/candidates/{candidate_id}/dry-run",
    response_model=HistoricalOcrDryRunResponse,
)
async def dry_run_historical_ocr_candidate(
    candidate_id: str,
    body: HistoricalOcrDryRunRequest,
    db: AsyncSession = Depends(_get_import_db),
    current_user: Annotated[models.User | None, Depends(get_current_user_optional)] = None,
) -> HistoricalOcrDryRunResponse:
    candidate_batch = await _get_ocr_candidate_batch_or_404(db, candidate_id)
    review_payload = _get_ocr_review_payload(candidate_batch)
    candidate_status = str(review_payload.get("status") or candidate_batch.status or "uploaded")
    rejection_reason = review_payload.get("rejection_reason")
    if candidate_status == "rejected" or (
        isinstance(rejection_reason, str) and rejection_reason.strip()
    ):
        raise HTTPException(
            status_code=409, detail="Rejected OCR review candidates cannot be dry-run applied."
        )

    reviewed_json = review_payload.get("reviewed_json")
    candidate_json = review_payload.get("candidate_json")
    payload_obj = reviewed_json if isinstance(reviewed_json, dict) else candidate_json
    if not isinstance(payload_obj, dict):
        raise HTTPException(
            status_code=422,
            detail="No reviewed structured JSON is available. Submit review corrections first.",
        )

    payload_bytes = json.dumps(payload_obj, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    status_code, dry_run_result = build_dry_run_response(payload_bytes)
    review_payload["dry_run_result"] = dry_run_result.model_dump()
    review_payload["validation_errors"] = [item.model_dump() for item in dry_run_result.errors]

    if status_code >= 400 or dry_run_result.status != "valid":
        review_payload["status"] = "dry_run_failed"
        history = review_payload.get("status_history")
        if not isinstance(history, list):
            history = []
        if "dry_run_failed" not in history:
            history.append("dry_run_failed")
        review_payload["status_history"] = history

        dry_summary = (
            dict(candidate_batch.dry_run_summary)
            if isinstance(candidate_batch.dry_run_summary, dict)
            else {}
        )
        dry_summary["ocr_review"] = review_payload
        await db.execute(
            update(models.HistoricalImportBatch)
            .where(models.HistoricalImportBatch.id == candidate_batch.id)
            .values(
                dry_run_summary=dry_summary,
                status="dry_run_failed",
            )
        )
        await db.commit()
        return HistoricalOcrDryRunResponse(
            candidate_id=candidate_id,
            status="dry_run_failed",
            dry_run_result=dry_run_result,
            dry_run_batch_id=None,
            message="Dry-run failed. Fix review corrections and retry.",
        )

    handoff_batch_id: str | None = None
    if body.record_preview:
        handoff_summary = dry_run_result.model_dump()
        handoff_summary["ocr_review_handoff"] = {
            "candidate_id": candidate_id,
            "source_batch_id": candidate_batch.id,
            "extraction_non_authoritative": True,
            "requires_human_review": True,
        }
        handoff_batch = await create_import_batch(
            db,
            source_hash_sha256=dry_run_result.duplicate_detection.source_hash_sha256,
            source_format=dry_run_result.detected_format,
            status=dry_run_result.status,
            error_count=len(dry_run_result.errors),
            warning_count=len(dry_run_result.warnings),
            innings_count=dry_run_result.innings_count,
            delivery_count=dry_run_result.delivery_count,
            dry_run_summary=handoff_summary,
            owner_user_id=current_user.id if current_user else None,
            owner_org_id=current_user.org_id if current_user else None,
            source_filename=f"ocr-review::{candidate_batch.source_filename or candidate_id}",
            semantic_key=dry_run_result.duplicate_detection.semantic_key,
        )
        handoff_batch_id = handoff_batch.id

    review_payload["status"] = "dry_run_passed"
    review_payload["dry_run_batch_id"] = handoff_batch_id
    history = review_payload.get("status_history")
    if not isinstance(history, list):
        history = []
    if "dry_run_passed" not in history:
        history.append("dry_run_passed")
    review_payload["status_history"] = history

    dry_summary = (
        dict(candidate_batch.dry_run_summary)
        if isinstance(candidate_batch.dry_run_summary, dict)
        else {}
    )
    dry_summary["ocr_review"] = review_payload
    await db.execute(
        update(models.HistoricalImportBatch)
        .where(models.HistoricalImportBatch.id == candidate_batch.id)
        .values(
            dry_run_summary=dry_summary,
            status="dry_run_passed",
        )
    )
    await db.commit()

    return HistoricalOcrDryRunResponse(
        candidate_id=candidate_id,
        status="dry_run_passed",
        dry_run_result=dry_run_result,
        dry_run_batch_id=handoff_batch_id,
        message=(
            "Dry-run passed. Use /api/historical-import/json/batches/{batch_id}/apply for explicit import apply."
            if handoff_batch_id
            else "Dry-run passed."
        ),
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
        raise HTTPException(
            status_code=415, detail="Only .zip uploads are supported for bulk import."
        )

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
        raise HTTPException(
            status_code=415, detail="Only .zip uploads are supported for bulk import."
        )

    selected_names = _parse_selected_file_names(selected_files)
    if not selected_names:
        raise HTTPException(
            status_code=422, detail="At least one selected file is required for bulk apply."
        )

    payload_bytes = await file.read()
    owner_user_id: str | None = current_user.id if current_user else None
    owner_org_id: str | None = current_user.org_id if current_user else None

    preview, candidates = await _build_bulk_zip_preview(
        payload_bytes=payload_bytes,
        source_filename=file.filename or None,
        db=db,
        owner_user_id=owner_user_id,
        owner_org_id=owner_org_id,
    )
    _validate_controlled_cpl_batch_selection(
        selected_names=selected_names,
        candidates=candidates,
        total_entries=preview.total_entries,
    )

    results: list[HistoricalImportBulkZipApplyFileResult] = []
    metadata_archive = (
        zipfile.ZipFile(io.BytesIO(payload_bytes))
        if preview.metadata_only_intake_required
        else None
    )
    try:
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

            if preview.metadata_only_intake_required:
                source_hash = candidate.dry_run.duplicate_detection.source_hash_sha256
                semantic_key = candidate.dry_run.duplicate_detection.semantic_key
                safe_file_name = _sanitize_storage_name(selected_name, source_hash)
                owner_scope = _resolve_intake_owner(owner_user_id, owner_org_id)
                provisional_batch_id = str(uuid.uuid4())
                base_key = f"historical-imports/{owner_scope}/{provisional_batch_id}"
                raw_key = f"{base_key}/raw/{safe_file_name}"
                manifest_key = f"{base_key}/manifest.json"
                validation_report_key = f"{base_key}/validation_report.json"

                if metadata_archive is None:
                    results.append(
                        HistoricalImportBulkZipApplyFileResult(
                            file_name=selected_name,
                            status="error",
                            message="Metadata intake archive was not available.",
                        )
                    )
                    continue
                selected_member = metadata_archive.getinfo(selected_name)
                with metadata_archive.open(selected_member, "r") as fp:
                    selected_payload = fp.read(selected_member.file_size)

                try:
                    raw_ref = _store_bytes_with_fallback(
                        key=raw_key,
                        payload=selected_payload,
                        content_type="application/json",
                    )
                    manifest_payload = json.dumps(
                        {
                            "batch_id": provisional_batch_id,
                            "source_filename": selected_name,
                            "source_hash_sha256": source_hash,
                            "semantic_key": semantic_key,
                            "intake_status": "pending_full_import",
                        },
                        separators=(",", ":"),
                    ).encode("utf-8")
                    manifest_ref = _store_bytes_with_fallback(
                        key=manifest_key,
                        payload=manifest_payload,
                        content_type="application/json",
                    )
                    validation_payload = json.dumps(
                        {
                            "status": candidate.status,
                            "warnings": [w.model_dump() for w in candidate.dry_run.warnings],
                            "errors": [e.model_dump() for e in candidate.dry_run.errors],
                        },
                        separators=(",", ":"),
                    ).encode("utf-8")
                    validation_ref = _store_bytes_with_fallback(
                        key=validation_report_key,
                        payload=validation_payload,
                        content_type="application/json",
                    )
                except (RuntimeError, OSError, ValueError) as exc:
                    results.append(
                        HistoricalImportBulkZipApplyFileResult(
                            file_name=selected_name,
                            status="error",
                            message=f"Failed to store raw metadata artifacts: {exc!s}",
                        )
                    )
                    continue

                dry_run_summary = candidate.dry_run.model_dump()
                dry_run_summary["large_zip_intake"] = {
                    "intake_mode": "metadata_only",
                    "intake_status": "pending_full_import",
                    "status_history": [
                        "scanned",
                        "metadata_extracted",
                        "pending_full_import",
                    ],
                    "training_eligible": False,
                    "blocking_reason": "metadata_only_pending_full_import",
                    "storage": {
                        "raw": raw_ref,
                        "manifest": manifest_ref,
                        "validation_report": validation_ref,
                    },
                }
                dry_run_summary["training_eligible"] = False
                dry_run_summary["blocking_reason"] = "metadata_only_pending_full_import"

                batch = await create_import_batch(
                    db,
                    source_hash_sha256=source_hash,
                    source_format=candidate.dry_run.detected_format,
                    status="pending_full_import",
                    error_count=len(candidate.dry_run.errors),
                    warning_count=len(candidate.dry_run.warnings),
                    innings_count=candidate.dry_run.innings_count,
                    delivery_count=candidate.dry_run.delivery_count,
                    dry_run_summary=dry_run_summary,
                    owner_user_id=owner_user_id,
                    owner_org_id=owner_org_id,
                    source_filename=(
                        f"{file.filename}{PHASE_5L_SOURCE_FILENAME_PREFIX_SEPARATOR}{selected_name}"
                        if file.filename
                        else selected_name
                    ),
                    semantic_key=semantic_key,
                    batch_id=provisional_batch_id,
                )
                results.append(
                    HistoricalImportBulkZipApplyFileResult(
                        file_name=selected_name,
                        status="metadata_extracted",
                        message=(
                            "Stored safely for later processing. "
                            "Metadata extracted; full import is pending."
                        ),
                        batch_id=batch.id,
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
            duplicate_batch_record: models.HistoricalImportBatch | None = None
            if dup_by_hash is not None:
                duplicate_batch_record = dup_by_hash
            elif dup_by_semantic is not None:
                duplicate_batch_record = dup_by_semantic
            if duplicate_batch_record is not None:
                results.append(
                    HistoricalImportBulkZipApplyFileResult(
                        file_name=selected_name,
                        status="skipped",
                        message=f"Skipped duplicate (existing batch: {duplicate_batch_record.id}).",
                        batch_id=duplicate_batch_record.id,
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
                source_filename=(
                    f"{file.filename}{PHASE_5L_SOURCE_FILENAME_PREFIX_SEPARATOR}{selected_name}"
                    if file.filename
                    else selected_name
                ),
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
    finally:
        if metadata_archive is not None:
            metadata_archive.close()

    applied_count = sum(1 for r in results if r.status == "applied")
    metadata_only_count = sum(1 for r in results if r.status == "metadata_extracted")
    skipped_count = sum(1 for r in results if r.status == "skipped")
    error_count = sum(1 for r in results if r.status == "error")
    if metadata_only_count > 0 and applied_count == 0 and error_count == 0:
        status_value = "metadata_recorded"
    elif applied_count == len(results):
        status_value = "applied"
    elif applied_count == 0 and metadata_only_count == 0:
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
        metadata_only_count=metadata_only_count,
        full_import_deferred=preview.metadata_only_intake_required,
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


@router.get("/venues/intelligence", response_model=list[HistoricalVenueIntelligenceRecord])
async def list_historical_venue_intelligence(
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(_get_import_db),
) -> list[HistoricalVenueIntelligenceRecord]:
    venues = await list_venue_intelligence(db, limit=limit)
    return [
        HistoricalVenueIntelligenceRecord(
            id=row.id,
            canonical_name=row.canonical_name,
            short_name=row.short_name,
            alternate_names=list(row.alternate_names or []),
            city=row.city,
            region=row.region,
            country=row.country,
            latitude=row.latitude,
            longitude=row.longitude,
            timezone=row.timezone,
            venue_type=row.venue_type,
            indoor_outdoor=row.indoor_outdoor,
            verification_status=row.verification_status.value,
            confidence_score=row.confidence_score,
            source_type=row.source_type,
            created_from_import=row.created_from_import,
            notes=row.notes,
            provenance_references=list(row.provenance_references or []),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in venues
    ]


@router.get("/venues/unresolved", response_model=list[HistoricalVenueUnresolvedRecord])
async def list_historical_unresolved_venues(
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(_get_import_db),
) -> list[HistoricalVenueUnresolvedRecord]:
    queue_rows = await list_unresolved_venues(db, limit=limit)
    return [
        HistoricalVenueUnresolvedRecord(
            id=row.id,
            decision_id=row.decision_id,
            raw_imported_value=row.raw_imported_value,
            normalized_raw_value=row.normalized_raw_value,
            source_schema=row.source_schema,
            source_system=row.source_system,
            queue_state=row.queue_state,
            reason=row.reason,
            review_required=row.review_required,
            provenance_references=list(row.provenance_references or []),
            created_at=row.created_at,
            last_seen=row.last_seen,
            resolved_at=row.resolved_at,
        )
        for row in queue_rows
    ]


@router.get("/venues/resolution-snapshots", response_model=list[HistoricalVenueResolutionSnapshot])
async def list_historical_venue_resolution_snapshots(
    limit: int = Query(default=100, ge=1, le=500),
    batch_id: str | None = Query(default=None),
    game_id: str | None = Query(default=None),
    db: AsyncSession = Depends(_get_import_db),
) -> list[HistoricalVenueResolutionSnapshot]:
    rows = await list_venue_resolution_snapshots(
        db,
        limit=limit,
        batch_id=batch_id,
        game_id=game_id,
    )
    return [
        HistoricalVenueResolutionSnapshot(
            id=row.id,
            batch_id=row.batch_id,
            game_id=row.game_id,
            raw_imported_value=row.raw_imported_value,
            normalized_raw_value=row.normalized_raw_value,
            canonical_venue_id=row.canonical_venue_id,
            resolution_state=row.resolution_state.value,
            matched_by=row.matched_by,
            confidence_score=row.confidence_score,
            unresolved_reason=row.unresolved_reason,
            review_required=row.review_required,
            source_schema=row.source_schema,
            source_system=row.source_system,
            competition_name=row.competition_name,
            season=row.season,
            provenance_references=list(row.provenance_references or []),
            resolution_snapshot=dict(row.resolution_snapshot or {}),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in rows
    ]


@router.get("/venues/usage", response_model=list[HistoricalVenueUsageRecord])
async def list_historical_venue_usage(
    limit: int = Query(default=100, ge=1, le=500),
    competition_name: str | None = Query(default=None),
    season: str | None = Query(default=None),
    db: AsyncSession = Depends(_get_import_db),
) -> list[HistoricalVenueUsageRecord]:
    usage_rows = await list_venue_usage_stats(
        db,
        limit=limit,
        competition_name=competition_name,
        season=season,
    )
    return [
        HistoricalVenueUsageRecord(
            id=row.id,
            canonical_venue_id=row.canonical_venue_id,
            competition_name=row.competition_name,
            season=row.season,
            source_schema=row.source_schema,
            source_system=row.source_system,
            matches_count=row.matches_count,
            game_references=list(row.game_references or []),
            provenance_references=list(row.provenance_references or []),
            review_required=row.review_required,
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in usage_rows
    ]


@router.get("/venues/aliases", response_model=list[HistoricalVenueAliasRecord])
async def list_historical_venue_aliases(
    limit: int = Query(default=100, ge=1, le=500),
    venue_id: str | None = Query(default=None),
    db: AsyncSession = Depends(_get_import_db),
) -> list[HistoricalVenueAliasRecord]:
    alias_rows = await list_venue_aliases(db, limit=limit, venue_id=venue_id)
    return [
        HistoricalVenueAliasRecord(
            id=row.id,
            venue_id=row.venue_id,
            alias_name=row.alias_name,
            normalized_alias=row.normalized_alias,
            source_schema=row.source_schema,
            source_system=row.source_system,
            confidence_score=row.confidence_score,
            provenance_reference=dict(row.provenance_reference or {}),
            created_at=row.created_at,
            updated_at=row.updated_at,
        )
        for row in alias_rows
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
    try:
        game, warnings, error_msg = await apply_historical_batch(
            db,
            batch_id=batch_id,
            confirm=body.confirm,
        )
    except Exception as exc:
        # Catch unexpected DB/service errors (e.g. ProgrammingError from a
        # missing migration in production) and convert them to an explicit HTTP
        # 500 so the response still flows through CORSMiddleware and the
        # frontend receives CORS headers rather than a CORS-masked network error.
        _log.exception("apply_historical_import_batch: unexpected error batch_id=%s", batch_id)
        raise HTTPException(
            status_code=500,
            detail=(
                f"Historical import apply encountered an unexpected error "
                f"({type(exc).__name__}). Check server logs for details."
            ),
        )

    if error_msg is not None:
        # Determine appropriate status code from error type
        if "not found" in error_msg.lower():
            raise HTTPException(status_code=404, detail=error_msg)
        if "confirm must be true" in error_msg.lower():
            raise HTTPException(status_code=422, detail=error_msg)
        raise HTTPException(status_code=409, detail=error_msg)

    if game is None:
        raise HTTPException(
            status_code=500,
            detail="Historical import apply failed unexpectedly after validation checks.",
        )

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
        if (
            "totals" in error_msg.lower()
            or "run total" in error_msg.lower()
            or "mismatch" in error_msg.lower()
        ):
            raise HTTPException(status_code=422, detail=error_msg)
        raise HTTPException(status_code=409, detail=error_msg)

    if result_info is None:
        raise RuntimeError(
            "apply_historical_deliveries returned no result without an error message"
        )

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
    if batch.status in {"scanned", "metadata_extracted", "pending_full_import"}:
        exclusion_reason = "metadata_only_pending_full_import"
    elif not batch.is_finalized:
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
    "/backfill-reprocess/audit",
    response_model=HistoricalBackfillAuditResponse,
    summary="Dry-run audit for controlled CPL historical delivery backfill",
)
async def audit_historical_delivery_backfill(
    body: HistoricalBackfillAuditRequest,
    db: AsyncSession = Depends(_get_import_db),
    current_user: Annotated[models.User | None, Depends(get_current_user_optional)] = None,
) -> HistoricalBackfillAuditResponse:
    del current_user
    try:
        report = await audit_delivery_backfill(
            db,
            match_ids=body.match_ids,
            batch_ids=body.batch_ids,
            max_batch_size=body.max_batch_size,
            source_payloads_by_batch=body.source_payloads_by_batch,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return HistoricalBackfillAuditResponse(**report)


@router.post(
    "/backfill-reprocess/apply",
    response_model=HistoricalBackfillApplyResponse,
    summary="Controlled CPL historical delivery backfill + registry reprocess",
)
async def apply_historical_delivery_backfill(
    body: HistoricalBackfillApplyRequest,
    db: AsyncSession = Depends(_get_import_db),
    current_user: Annotated[models.User | None, Depends(get_current_user_optional)] = None,
) -> HistoricalBackfillApplyResponse:
    del current_user
    if not body.confirm:
        raise HTTPException(
            status_code=422,
            detail="confirm must be true to apply controlled delivery backfill.",
        )
    try:
        report = await apply_delivery_backfill(
            db,
            match_ids=body.match_ids,
            batch_ids=body.batch_ids,
            max_batch_size=body.max_batch_size,
            source_payloads_by_batch=body.source_payloads_by_batch,
        )
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return HistoricalBackfillApplyResponse(**report)


@router.post(
    "/source-reattach/dry-run",
    response_model=HistoricalSourcePayloadReattachDryRunResponse,
    summary="Dry-run deterministic historical source payload reattach",
)
async def historical_source_payload_reattach_dry_run(
    request: Request,
    file: UploadFile | None = File(None),
    db: AsyncSession = Depends(_get_import_db),
    current_user: Annotated[models.User | None, Depends(get_current_user_optional)] = None,
) -> HistoricalSourcePayloadReattachDryRunResponse:
    del current_user
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
                detail="Provide application/json payload or multipart JSON/ZIP upload.",
            )
        payload_bytes = await request.body()

    preview, _ = await _build_source_reattach_preview(
        payload_bytes=payload_bytes,
        source_filename=source_filename,
        db=db,
    )
    return preview


@router.post(
    "/source-reattach/apply",
    response_model=HistoricalSourcePayloadReattachApplyResponse,
    summary="Attach retained historical source JSON onto existing imported records",
)
async def historical_source_payload_reattach_apply(
    file: UploadFile = File(...),
    confirm: bool = Form(False),
    selected_mappings: str = Form(...),
    db: AsyncSession = Depends(_get_import_db),
    current_user: Annotated[models.User | None, Depends(get_current_user_optional)] = None,
) -> HistoricalSourcePayloadReattachApplyResponse:
    if not confirm:
        raise HTTPException(
            status_code=422,
            detail="confirm must be true to apply source payload reattach.",
        )

    payload_bytes = await file.read()
    source_filename = file.filename or None
    preview, candidate_lookup = await _build_source_reattach_preview(
        payload_bytes=payload_bytes,
        source_filename=source_filename,
        db=db,
    )
    preview_lookup: dict[str, HistoricalSourcePayloadReattachDryRunFileResult] = {}
    for item in preview.files:
        preview_lookup[item.file_name] = item
        preview_lookup[_source_file_label(item.file_name)] = item
    normalized_candidate_lookup: dict[str, _SourceReattachCandidate] = {}
    for key, lookup_candidate in candidate_lookup.items():
        normalized_candidate_lookup[key] = lookup_candidate
        normalized_candidate_lookup[_source_file_label(key)] = lookup_candidate
    mappings = _parse_source_reattach_selection(selected_mappings)

    for file_name, batch_id in mappings:
        preview_item = preview_lookup.get(file_name)
        if preview_item is None or preview_item.matched_target is None:
            raise HTTPException(
                status_code=422,
                detail=f"Selected file '{file_name}' was not present in the reattach dry-run preview.",
            )
        if preview_item.status != "ready" or preview_item.blocked_from_apply:
            raise HTTPException(
                status_code=422,
                detail=f"Selected file '{file_name}' is blocked from apply ({preview_item.match_confidence}).",
            )
        if preview_item.matched_target.batch_id != batch_id:
            raise HTTPException(
                status_code=422,
                detail=(
                    f"Selected batch '{batch_id}' does not match dry-run target "
                    f"'{preview_item.matched_target.batch_id}' for file '{file_name}'."
                ),
            )

    owner_user_id = current_user.id if current_user else None
    owner_org_id = current_user.org_id if current_user else None
    owner_scope = _resolve_intake_owner(owner_user_id, owner_org_id)
    results: list[HistoricalSourcePayloadReattachApplyFileResult] = []
    reattached_count = 0
    skipped_count = 0
    error_count = 0
    now = dt.datetime.now(dt.UTC).isoformat()

    for file_name, batch_id in mappings:
        preview_item = preview_lookup[file_name]
        candidate: _SourceReattachCandidate | None = normalized_candidate_lookup.get(file_name)
        if candidate is None or preview_item.matched_target is None:
            error_count += 1
            results.append(
                HistoricalSourcePayloadReattachApplyFileResult(
                    file_name=file_name,
                    status="error",
                    message="Dry-run candidate payload was not available for apply.",
                    batch_id=batch_id,
                )
            )
            continue

        batch = await db.scalar(
            select(models.HistoricalImportBatch).where(models.HistoricalImportBatch.id == batch_id)
        )
        if batch is None or not batch.applied_game_id:
            error_count += 1
            results.append(
                HistoricalSourcePayloadReattachApplyFileResult(
                    file_name=file_name,
                    status="error",
                    message="Target historical import batch was not found.",
                    batch_id=batch_id,
                )
            )
            continue

        game = await db.scalar(select(models.Game).where(models.Game.id == batch.applied_game_id))
        if game is None:
            error_count += 1
            results.append(
                HistoricalSourcePayloadReattachApplyFileResult(
                    file_name=file_name,
                    status="error",
                    message="Target historical match was not found.",
                    batch_id=batch_id,
                )
            )
            continue

        if _batch_has_retained_source(batch):
            skipped_count += 1
            results.append(
                HistoricalSourcePayloadReattachApplyFileResult(
                    file_name=file_name,
                    status="skipped",
                    message="Target already retains source JSON; overwrite is blocked.",
                    match_id=game.id,
                    batch_id=batch.id,
                    match_confidence=preview_item.match_confidence,
                )
            )
            continue

        safe_file_name = _sanitize_storage_name(
            file_name,
            candidate.dry_run.duplicate_detection.source_hash_sha256,
        )
        base_key = f"historical-imports/{owner_scope}/{batch.id}/source-reattach"
        raw_ref = _store_bytes_with_fallback(
            key=f"{base_key}/raw/{safe_file_name}",
            payload=candidate.payload_bytes,
            content_type="application/json",
        )
        manifest_ref = _store_bytes_with_fallback(
            key=f"{base_key}/manifest.json",
            payload=json.dumps(
                {
                    "batch_id": batch.id,
                    "match_id": game.id,
                    "selected_file_name": file_name,
                    "source_hash_sha256": candidate.dry_run.duplicate_detection.source_hash_sha256,
                    "match_confidence": preview_item.match_confidence,
                    "matched_on": preview_item.matched_target.matched_on,
                    "attached_at": now,
                },
                separators=(",", ":"),
            ).encode("utf-8"),
            content_type="application/json",
        )

        reattach_summary = {
            "attached_at": now,
            "selected_file_name": file_name,
            "source_hash_sha256": candidate.dry_run.duplicate_detection.source_hash_sha256,
            "match_confidence": preview_item.match_confidence,
            "matched_on": preview_item.matched_target.matched_on,
            "storage": {
                "raw": raw_ref,
                "manifest": manifest_ref,
            },
            "registry_people_available": candidate.metadata.registry_people_available,
            "expected_deliveries": candidate.metadata.expected_deliveries,
            "expected_wickets": candidate.metadata.expected_wickets,
        }

        batch_dry_run = batch.dry_run_summary if isinstance(batch.dry_run_summary, dict) else None
        dry_run_summary: dict[str, Any] = dict(batch_dry_run) if batch_dry_run is not None else {}
        dry_run_summary["source_payload_reattach"] = reattach_summary
        batch.dry_run_summary = dry_run_summary

        phases = game.phases if isinstance(game.phases, dict) else {}
        historical_meta_raw = phases.get("historical_import")
        historical_meta: dict[str, Any] = (
            dict(historical_meta_raw) if isinstance(historical_meta_raw, dict) else {}
        )
        historical_meta["source_payload_reattach"] = {
            **reattach_summary,
            "source_filename": batch.source_filename,
        }
        historical_meta["source_json_retained"] = True
        game.phases = {**phases, "historical_import": historical_meta}

        db.add(batch)
        db.add(game)
        reattached_count += 1
        results.append(
            HistoricalSourcePayloadReattachApplyFileResult(
                file_name=file_name,
                status="reattached",
                message="Source payload reattached. Run delivery backfill/reprocess separately.",
                match_id=game.id,
                batch_id=batch.id,
                match_confidence=preview_item.match_confidence,
            )
        )

    if reattached_count > 0:
        await db.commit()

    status = "applied"
    if error_count > 0 and reattached_count == 0:
        status = "failed"
    elif error_count > 0 or skipped_count > 0:
        status = "partial"

    return HistoricalSourcePayloadReattachApplyResponse(
        status=cast(Literal["applied", "partial", "failed"], status),
        source_filename=source_filename,
        selected_count=len(mappings),
        reattached_count=reattached_count,
        skipped_count=skipped_count,
        error_count=error_count,
        results=results,
        follow_up_message=(
            "Source payload reattach does not run delivery reprocess automatically. "
            "Use Historical Backfill Audit + Reprocess after successful reattach."
        ),
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

    if result is None:
        raise HTTPException(
            status_code=500,
            detail="Historical metadata repair failed unexpectedly after validation checks.",
        )

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
        detail_text = f"Game '{game_id_value}' already has Phase 5J metadata. No changes were made."
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
