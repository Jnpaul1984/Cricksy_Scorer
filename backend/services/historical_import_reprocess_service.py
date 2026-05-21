from __future__ import annotations

# mypy: ignore-errors
import datetime as dt
import json
import logging
from contextlib import suppress
from pathlib import Path
from typing import Any

from backend.services.historical_import_apply_service import apply_historical_deliveries
from backend.services.historical_import_delivery_service import extract_normalized_innings
from backend.services.historical_player_identity_service import register_historical_source_players
from backend.services.s3_service import s3_service
from backend.sql_app.models import Game, HistoricalImportBatch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_log = logging.getLogger(__name__)


def _completeness(game: Game) -> str:
    phases = game.phases if isinstance(game.phases, dict) else {}
    hist_meta = (
        phases.get("historical_import") if isinstance(phases.get("historical_import"), dict) else {}
    )
    has_innings = bool(phases.get("historical_innings_summary"))
    deliveries = game.deliveries if isinstance(game.deliveries, list) else []
    has_deliveries = bool(hist_meta.get("deliveries_imported")) or bool(deliveries)
    if not has_innings:
        return "metadata_only"
    if not has_deliveries:
        return "innings_totals_only"
    has_wickets = any(bool(d.get("is_wicket")) for d in deliveries if isinstance(d, dict))
    if not has_wickets:
        return "delivery_data_available"
    has_phase = any(
        isinstance(phases.get(phase_name), dict) and bool(phases.get(phase_name))
        for phase_name in ("powerplay", "middle", "death")
    ) or any(bool(d.get("phase")) for d in deliveries if isinstance(d, dict))
    return "phase_analytics_available" if has_phase else "wicket_data_available"


def _is_cpl(batch: HistoricalImportBatch, game: Game) -> bool:
    phases = game.phases if isinstance(game.phases, dict) else {}
    hist_meta = (
        phases.get("historical_import") if isinstance(phases.get("historical_import"), dict) else {}
    )
    dry_run = batch.dry_run_summary if isinstance(batch.dry_run_summary, dict) else {}
    canonical = (
        dry_run.get("canonical_preview")
        if isinstance(dry_run.get("canonical_preview"), dict)
        else {}
    )
    comp = (
        str(hist_meta.get("event_name") or "").lower(),
        str(hist_meta.get("competition_name") or "").lower(),
        str(canonical.get("competition_context", {}).get("competition_name") or "").lower()
        if isinstance(canonical.get("competition_context"), dict)
        else "",
        str(canonical.get("competition_context", {}).get("tournament_name") or "").lower()
        if isinstance(canonical.get("competition_context"), dict)
        else "",
        str(batch.source_filename or "").lower(),
    )
    return any(("caribbean premier league" in value) or ("cpl" in value) for value in comp if value)


def _import_origin(batch: HistoricalImportBatch) -> str:
    source_filename = str(batch.source_filename or "")
    dry_run = batch.dry_run_summary if isinstance(batch.dry_run_summary, dict) else {}
    if "::" in source_filename or "large_zip_intake" in dry_run:
        return "bulk_zip_apply"
    if source_filename:
        return "single_json_apply"
    return "unknown"


def _registry_people(parsed: dict[str, Any]) -> dict[str, str]:
    info = parsed.get("info") if isinstance(parsed.get("info"), dict) else {}
    registry = info.get("registry") if isinstance(info.get("registry"), dict) else {}
    people = registry.get("people") if isinstance(registry.get("people"), dict) else {}
    return {
        str(name).strip(): str(source_id).strip()
        for name, source_id in people.items()
        if str(name).strip() and str(source_id or "").strip()
    }


def _extract_source_identity_inputs(parsed: dict[str, Any]) -> dict[str, Any]:
    innings = extract_normalized_innings(parsed)
    unique_players: set[str] = set()
    for innings_row in innings:
        deliveries = innings_row.get("deliveries")
        if not isinstance(deliveries, list):
            continue
        for delivery in deliveries:
            if not isinstance(delivery, dict):
                continue
            for key in ("batter", "bowler", "non_striker", "player_out"):
                value = str(delivery.get(key) or "").strip()
                if value:
                    unique_players.add(value)
            fielders = delivery.get("fielders")
            if isinstance(fielders, list):
                for fielder in fielders:
                    if isinstance(fielder, str):
                        value = fielder.strip()
                    elif isinstance(fielder, dict):
                        value = str(fielder.get("name") or "").strip()
                    else:
                        value = ""
                    if value:
                        unique_players.add(value)

    info = parsed.get("info") if isinstance(parsed.get("info"), dict) else {}
    source_venue_name = str(info.get("venue") or "").strip() or None
    return {
        "unique_players": sorted(unique_players),
        "source_registry_people": _registry_people(parsed),
        "source_venue_name": source_venue_name,
    }


def _delivery_path_candidates(parsed: dict[str, Any]) -> tuple[bool, list[str]]:
    innings_raw = parsed.get("innings")
    if not isinstance(innings_raw, list):
        return False, []

    candidates: set[str] = set()
    for innings in innings_raw:
        if not isinstance(innings, dict):
            continue

        if isinstance(innings.get("deliveries"), list):
            candidates.add("innings[].deliveries[]")
        if isinstance(innings.get("balls"), list):
            candidates.add("innings[].balls[]")

        overs = innings.get("overs")
        if isinstance(overs, list) and any(
            isinstance(over, dict) and isinstance(over.get("deliveries"), list) for over in overs
        ):
            candidates.add("innings[].overs[].deliveries[]")

        if len(innings) == 1:
            nested = next(iter(innings.values()))
            if isinstance(nested, dict):
                if isinstance(nested.get("deliveries"), list):
                    candidates.add("innings[].<team>.deliveries[]")
                if isinstance(nested.get("balls"), list):
                    candidates.add("innings[].<team>.balls[]")
                nested_overs = nested.get("overs")
                if isinstance(nested_overs, list) and any(
                    isinstance(over, dict) and isinstance(over.get("deliveries"), list)
                    for over in nested_overs
                ):
                    candidates.add("innings[].<team>.overs[].deliveries[]")

    return True, sorted(candidates)


def _choose_detected_delivery_path(candidates: list[str]) -> str | None:
    priority = [
        "innings[].overs[].deliveries[]",
        "innings[].deliveries[]",
        "innings[].balls[]",
        "innings[].<team>.overs[].deliveries[]",
        "innings[].<team>.deliveries[]",
        "innings[].<team>.balls[]",
    ]
    for path in priority:
        if path in candidates:
            return path
    return candidates[0] if candidates else None


def _detect_schema_type(
    *,
    innings_path_detected: bool,
    detected_delivery_path: str | None,
) -> str:
    if not innings_path_detected:
        return "unknown_delivery_schema"
    if detected_delivery_path == "innings[].overs[].deliveries[]":
        return "overs_deliveries_schema"
    if detected_delivery_path in {"innings[].deliveries[]", "innings[].balls[]"}:
        return "flat_innings_deliveries_schema"
    if detected_delivery_path in {
        "innings[].<team>.overs[].deliveries[]",
        "innings[].<team>.deliveries[]",
        "innings[].<team>.balls[]",
    }:
        return "cricsheet_nested_innings_schema"
    return "unknown_delivery_schema"


def _expected_wickets_from_innings(parsed: dict[str, Any]) -> int:
    innings_raw = parsed.get("innings")
    if not isinstance(innings_raw, list):
        return 0

    total = 0
    for innings in innings_raw:
        if not isinstance(innings, dict):
            continue
        innings_obj = innings
        if len(innings_obj) == 1 and not any(
            key in innings_obj for key in ("balls", "deliveries", "overs", "runs", "wickets")
        ):
            nested = next(iter(innings_obj.values()))
            if isinstance(nested, dict):
                innings_obj = nested
        wickets = innings_obj.get("wickets")
        if isinstance(wickets, int):
            total += wickets
    return total


def _recommended_next_action(reason: str | None, safely_reprocessable: bool) -> str:
    if reason == "missing_source_json":
        return "Source JSON missing. Reattach original JSON before delivery diagnosis or reprocess can run."
    if reason == "invalid_retained_source_json":
        return "Retained source JSON is invalid. Reattach original JSON and rerun diagnosis."
    if reason == "no_innings_path_detected":
        return "JSON does not expose an innings list. Confirm source format before reprocess."
    if reason == "no_delivery_path_detected":
        return "No delivery path detected. Add parser support or provide canonical source JSON."
    if reason == "unknown_delivery_schema":
        return "Unknown delivery schema. Extend parser rules before controlled reprocess."
    if reason == "missing_required_delivery_fields":
        return "Delivery entries are present but required fields are missing. Validate schema mapping first."
    if safely_reprocessable:
        return "Diagnosis indicates delivery extraction is possible. Keep controlled apply gate and proceed in staged batches."
    return "Diagnosis incomplete. Review source JSON and parser compatibility before reprocess."


def _clean_text(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def _team_name(team_blob: Any) -> str | None:
    if not isinstance(team_blob, dict):
        return None
    return _clean_text(team_blob.get("name"))


def _formatted_match_date(value: Any) -> str | None:
    if isinstance(value, dt.datetime):
        return value.date().isoformat()
    if isinstance(value, dt.date):
        return value.isoformat()
    text = _clean_text(value)
    if text is None:
        return None
    if "T" in text:
        return text.split("T", 1)[0] or text
    return text


def _summarize_innings(innings: Any) -> str | None:
    if not isinstance(innings, dict):
        return None
    team = _clean_text(innings.get("team"))
    runs = innings.get("runs")
    wickets = innings.get("wickets")
    overs = innings.get("overs")

    score_parts: list[str] = []
    if isinstance(runs, int):
        score_parts.append(str(runs))
        if isinstance(wickets, int):
            score_parts[-1] = f"{score_parts[-1]}/{wickets}"
    elif isinstance(wickets, int):
        score_parts.append(f"-/{wickets}")

    details: list[str] = []
    if team:
        details.append(team)
    if score_parts:
        details.append(score_parts[0])
    if overs is not None and _clean_text(overs) is not None:
        details.append(f"({_clean_text(overs)} ov)")
    return " ".join(details) if details else None


def _match_identity(batch: HistoricalImportBatch, game: Game) -> dict[str, str | None]:
    phases = game.phases if isinstance(game.phases, dict) else {}
    hist_meta = (
        phases.get("historical_import") if isinstance(phases.get("historical_import"), dict) else {}
    )
    innings_summary = (
        phases.get("historical_innings_summary")
        if isinstance(phases.get("historical_innings_summary"), list)
        else []
    )
    inning_1 = innings_summary[0] if len(innings_summary) > 0 else None
    inning_2 = innings_summary[1] if len(innings_summary) > 1 else None

    match_date = _formatted_match_date(
        hist_meta.get("match_date")
        or (
            hist_meta.get("source_dates")[0]
            if isinstance(hist_meta.get("source_dates"), list) and hist_meta.get("source_dates")
            else None
        )
    )
    competition = _clean_text(
        hist_meta.get("competition_name")
        or hist_meta.get("tournament_name")
        or hist_meta.get("event_name")
    )
    season = _clean_text(hist_meta.get("season"))
    team_1 = _team_name(game.team_a) or _clean_text(game.batting_team_name)
    team_2 = _team_name(game.team_b) or _clean_text(game.bowling_team_name)
    venue_context = (
        hist_meta.get("venue_context") if isinstance(hist_meta.get("venue_context"), dict) else {}
    )
    venue = _clean_text(hist_meta.get("venue") or venue_context.get("raw_venue"))
    result = _clean_text(game.result)
    status = _clean_text(getattr(game.status, "value", game.status))
    innings_1_summary = _summarize_innings(
        inning_1 if isinstance(inning_1, dict) else game.first_inning_summary
    )
    innings_2_summary = _summarize_innings(inning_2 if isinstance(inning_2, dict) else None)
    known_score_summary = (
        " | ".join(summary for summary in (innings_1_summary, innings_2_summary) if summary) or None
    )
    original_filename = _clean_text(batch.source_filename)
    reattach = (
        batch.dry_run_summary.get("source_payload_reattach")
        if isinstance(batch.dry_run_summary, dict)
        and isinstance(batch.dry_run_summary.get("source_payload_reattach"), dict)
        else {}
    )
    upload_filename = _clean_text(reattach.get("uploaded_filename"))
    source_file_hint = _clean_text(
        hist_meta.get("source_file_hint") or original_filename or upload_filename
    )
    label_parts = [
        part
        for part in (f"{team_1} vs {team_2}" if team_1 and team_2 else None, match_date, venue)
        if part
    ]
    match_identity_label = " — ".join(label_parts) if label_parts else None
    return {
        "match_date": match_date,
        "competition": competition,
        "season": season,
        "team_1": team_1,
        "team_2": team_2,
        "venue": venue,
        "result": result,
        "status": status,
        "innings_1_summary": innings_1_summary,
        "innings_2_summary": innings_2_summary,
        "known_score_summary": known_score_summary,
        "original_filename": original_filename,
        "upload_filename": upload_filename,
        "source_file_hint": source_file_hint,
        "match_identity_label": match_identity_label,
    }


def _load_storage_ref(batch: HistoricalImportBatch) -> dict[str, Any] | None:
    dry_run = batch.dry_run_summary if isinstance(batch.dry_run_summary, dict) else {}
    reattach = (
        dry_run.get("source_payload_reattach")
        if isinstance(dry_run.get("source_payload_reattach"), dict)
        else {}
    )
    reattach_storage = reattach.get("storage") if isinstance(reattach.get("storage"), dict) else {}
    raw = reattach_storage.get("raw") if isinstance(reattach_storage.get("raw"), dict) else None
    if raw is not None:
        return raw
    intake = (
        dry_run.get("large_zip_intake") if isinstance(dry_run.get("large_zip_intake"), dict) else {}
    )
    storage = intake.get("storage") if isinstance(intake.get("storage"), dict) else {}
    raw = storage.get("raw") if isinstance(storage.get("raw"), dict) else None
    return raw


def _load_retained_payload(batch: HistoricalImportBatch) -> tuple[bytes | None, str | None]:
    raw_ref = _load_storage_ref(batch)
    if not isinstance(raw_ref, dict):
        return None, "missing_source_json"

    storage = str(raw_ref.get("storage") or "").strip().lower()
    if storage == "local":
        path = str(raw_ref.get("path") or "").strip()
        if not path:
            return None, "missing_source_json"
        target = Path(path)
        if not target.exists():
            return None, "missing_source_json"
        return target.read_bytes(), None

    if storage == "s3":
        bucket = str(raw_ref.get("bucket") or "").strip()
        key = str(raw_ref.get("key") or "").strip()
        if not bucket or not key:
            return None, "missing_source_json"
        try:
            body = s3_service.s3_client.get_object(Bucket=bucket, Key=key)["Body"].read()
        except Exception:
            return None, "missing_source_json"
        return body, None

    return None, "missing_source_json"


def _selection_allowed(size: int) -> bool:
    return size == 1 or 3 <= size <= 5 or size == 10 or 20 <= size <= 25


async def _resolve_selected_pairs(
    db: AsyncSession,
    *,
    match_ids: list[str],
    batch_ids: list[str],
) -> list[tuple[HistoricalImportBatch, Game]]:
    pairs: list[tuple[HistoricalImportBatch, Game]] = []
    seen: set[tuple[str, str]] = set()

    if match_ids:
        game_rows = (
            (await db.execute(select(Game).where(Game.id.in_(match_ids)))).scalars().all()  # type: ignore[arg-type]
        )
    else:
        game_rows = []
    for game in game_rows:
        phases = game.phases if isinstance(game.phases, dict) else {}
        hist_meta = (
            phases.get("historical_import")
            if isinstance(phases.get("historical_import"), dict)
            else {}
        )
        batch_id = str(hist_meta.get("batch_id") or "").strip()
        if not batch_id:
            continue
        batch = await db.scalar(
            select(HistoricalImportBatch).where(HistoricalImportBatch.id == batch_id)
        )
        if batch is None:
            continue
        key = (batch.id, game.id)
        if key not in seen:
            seen.add(key)
            pairs.append((batch, game))

    if batch_ids:
        batch_rows = (
            (
                await db.execute(
                    select(HistoricalImportBatch).where(HistoricalImportBatch.id.in_(batch_ids))
                )
            )
            .scalars()
            .all()  # type: ignore[arg-type]
        )
        for batch in batch_rows:
            if not batch.applied_game_id:
                continue
            game = await db.scalar(select(Game).where(Game.id == batch.applied_game_id))
            if game is None:
                continue
            key = (batch.id, game.id)
            if key not in seen:
                seen.add(key)
                pairs.append((batch, game))

    if not match_ids and not batch_ids:
        rows = (
            await db.execute(
                select(HistoricalImportBatch, Game).join(
                    Game, HistoricalImportBatch.applied_game_id == Game.id
                )
            )
        ).all()
        for batch, game in rows:
            key = (batch.id, game.id)
            if key not in seen:
                seen.add(key)
                pairs.append((batch, game))

    return pairs


def _selected_cpl_pairs(
    pairs: list[tuple[HistoricalImportBatch, Game]],
    *,
    match_ids: list[str],
    batch_ids: list[str],
) -> tuple[list[tuple[HistoricalImportBatch, Game]], bool]:
    filtered_to_cpl = not match_ids and not batch_ids
    cpl_pairs = (
        [(batch, game) for batch, game in pairs if _is_cpl(batch, game)]
        if filtered_to_cpl
        else pairs
    )
    return cpl_pairs, filtered_to_cpl


def _validate_selection_size(selected_size: int, max_batch_size: int) -> None:
    if selected_size > max_batch_size:
        raise ValueError(f"Controlled batch size exceeded ({selected_size} > {max_batch_size}).")
    if selected_size > 0 and not _selection_allowed(selected_size):
        raise ValueError(
            "Controlled CPL staged ladder violation. Allowed sizes: 1, 3-5, 10, or 20-25."
        )


async def diagnose_delivery_backfill(
    db: AsyncSession,
    *,
    match_ids: list[str],
    batch_ids: list[str],
    max_batch_size: int,
    source_payloads_by_batch: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    pairs = await _resolve_selected_pairs(db, match_ids=match_ids, batch_ids=batch_ids)
    cpl_pairs, _filtered_to_cpl = _selected_cpl_pairs(
        pairs, match_ids=match_ids, batch_ids=batch_ids
    )
    _validate_selection_size(len(cpl_pairs), max_batch_size)

    payload_overrides = source_payloads_by_batch or {}
    records: list[dict[str, Any]] = []
    blocked = 0

    for batch, game in cpl_pairs:
        completeness = _completeness(game)
        origin = _import_origin(batch)
        override_payload = payload_overrides.get(batch.id)
        if isinstance(override_payload, dict):
            payload = json.dumps(override_payload, separators=(",", ":")).encode("utf-8")
            load_error = None
        else:
            payload, load_error = _load_retained_payload(batch)

        registry_available = False
        expected_deliveries = 0
        expected_wickets = 0
        innings_path_detected = False
        delivery_path_candidates: list[str] = []
        detected_delivery_path: str | None = None
        schema_detected = "unknown_delivery_schema"
        batter_field_detected = False
        bowler_field_detected = False
        non_striker_field_detected = False
        runs_field_detected = False
        extras_field_detected = False
        wicket_field_detected = False
        reason = load_error

        if payload is not None:
            try:
                parsed_any = json.loads(payload.decode("utf-8"))
                parsed = parsed_any if isinstance(parsed_any, dict) else {}
                innings_path_detected, delivery_path_candidates = _delivery_path_candidates(parsed)
                detected_delivery_path = _choose_detected_delivery_path(delivery_path_candidates)
                schema_detected = _detect_schema_type(
                    innings_path_detected=innings_path_detected,
                    detected_delivery_path=detected_delivery_path,
                )

                innings = extract_normalized_innings(parsed)
                normalized_deliveries = [
                    delivery
                    for inn in innings
                    for delivery in inn.get("deliveries", [])
                    if isinstance(delivery, dict)
                ]
                expected_deliveries = len(normalized_deliveries)
                expected_wickets = sum(
                    1 for delivery in normalized_deliveries if delivery.get("is_wicket")
                )
                if expected_wickets == 0:
                    expected_wickets = _expected_wickets_from_innings(parsed)
                registry_available = len(_registry_people(parsed)) > 0

                batter_field_detected = any(
                    str(delivery.get("batter") or "").strip() for delivery in normalized_deliveries
                )
                bowler_field_detected = any(
                    str(delivery.get("bowler") or "").strip() for delivery in normalized_deliveries
                )
                non_striker_field_detected = any(
                    str(delivery.get("non_striker") or "").strip()
                    for delivery in normalized_deliveries
                )
                runs_field_detected = any(
                    isinstance(delivery.get("runs_off_bat"), int)
                    or isinstance(delivery.get("extra_runs"), int)
                    for delivery in normalized_deliveries
                )
                extras_field_detected = any(
                    bool(delivery.get("extra_type")) or int(delivery.get("extra_runs") or 0) > 0
                    for delivery in normalized_deliveries
                )
                wicket_field_detected = (
                    any(
                        bool(delivery.get("is_wicket"))
                        or bool(delivery.get("dismissal_kind"))
                        or bool(delivery.get("player_out"))
                        for delivery in normalized_deliveries
                    )
                    or expected_wickets > 0
                )

                if not innings_path_detected:
                    reason = "no_innings_path_detected"
                elif not delivery_path_candidates:
                    reason = "no_delivery_path_detected"
                elif expected_deliveries == 0:
                    reason = "unknown_delivery_schema"
                elif not (
                    batter_field_detected
                    and bowler_field_detected
                    and non_striker_field_detected
                    and runs_field_detected
                ):
                    reason = "missing_required_delivery_fields"
                else:
                    reason = None
            except Exception:
                reason = "invalid_retained_source_json"

        safely_reprocessable = payload is not None and reason is None and expected_deliveries > 0
        row = {
            "match_id": game.id,
            "batch_id": batch.id,
            "import_source": origin,
            "completeness": completeness,
            "source_json_retained": payload is not None,
            "source_json_required": payload is None,
            "schema_detected": schema_detected,
            "innings_path_detected": innings_path_detected,
            "delivery_path_detected": detected_delivery_path is not None
            and expected_deliveries > 0,
            "detected_delivery_path": detected_delivery_path,
            "delivery_path_candidates": delivery_path_candidates,
            "expected_deliveries": expected_deliveries,
            "expected_wickets": expected_wickets,
            "registry_people_available": registry_available,
            "batter_field_detected": batter_field_detected,
            "bowler_field_detected": bowler_field_detected,
            "non_striker_field_detected": non_striker_field_detected,
            "runs_field_detected": runs_field_detected,
            "extras_field_detected": extras_field_detected,
            "wicket_field_detected": wicket_field_detected,
            "skip_or_failure_reason": reason,
            "safely_reprocessable": safely_reprocessable,
            "recommended_next_action": _recommended_next_action(reason, safely_reprocessable),
        }
        if reason is not None:
            blocked += 1
        records.append(row)

    return {
        "total_imported_cpl_matches": len(cpl_pairs),
        "selected_matches": len(cpl_pairs),
        "blocked_matches": blocked,
        "records": records,
    }


async def audit_delivery_backfill(
    db: AsyncSession,
    *,
    match_ids: list[str],
    batch_ids: list[str],
    max_batch_size: int,
    source_payloads_by_batch: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    pairs = await _resolve_selected_pairs(db, match_ids=match_ids, batch_ids=batch_ids)
    cpl_pairs, _filtered_to_cpl = _selected_cpl_pairs(
        pairs, match_ids=match_ids, batch_ids=batch_ids
    )
    payload_overrides = source_payloads_by_batch or {}

    _validate_selection_size(len(cpl_pairs), max_batch_size)

    completeness_counts = {
        "metadata_only": 0,
        "innings_totals_only": 0,
        "delivery_data_available": 0,
        "wicket_data_available": 0,
        "phase_analytics_available": 0,
    }
    import_origin_counts = {"single_json_apply": 0, "bulk_zip_apply": 0, "unknown": 0}
    records: list[dict[str, Any]] = []
    eligible = 0
    blocked = 0

    for batch, game in cpl_pairs:
        completeness = _completeness(game)
        completeness_counts[completeness] = completeness_counts.get(completeness, 0) + 1

        origin = _import_origin(batch)
        import_origin_counts[origin] = import_origin_counts.get(origin, 0) + 1

        phases = game.phases if isinstance(game.phases, dict) else {}
        hist_meta = (
            phases.get("historical_import")
            if isinstance(phases.get("historical_import"), dict)
            else {}
        )
        deliveries = game.deliveries if isinstance(game.deliveries, list) else []
        duplicate_risk = bool(deliveries) or bool(hist_meta.get("deliveries_imported"))

        override_payload = payload_overrides.get(batch.id)
        if isinstance(override_payload, dict):
            payload = json.dumps(override_payload, separators=(",", ":")).encode("utf-8")
            load_error = None
        else:
            payload, load_error = _load_retained_payload(batch)
        blocked_reason = load_error
        expected_deliveries = 0
        expected_wickets = 0
        expected_players = 0
        registry_count = 0
        players_without_source_ids = 0
        registry_available = False
        if payload is not None:
            try:
                parsed = json.loads(payload.decode("utf-8"))
                innings = extract_normalized_innings(parsed)
                expected_deliveries = sum(len(inn["deliveries"]) for inn in innings)
                expected_wickets = sum(
                    1
                    for inn in innings
                    for delivery in inn["deliveries"]
                    if delivery.get("is_wicket")
                )
                unique_players = {
                    str(delivery.get(key)).strip()
                    for inn in innings
                    for delivery in inn["deliveries"]
                    for key in ("batter", "bowler", "non_striker")
                    if str(delivery.get(key) or "").strip()
                }
                expected_players = len(unique_players)
                registry = _registry_people(parsed if isinstance(parsed, dict) else {})
                registry_count = len(registry)
                registry_available = registry_count > 0
                players_without_source_ids = len(
                    [name for name in unique_players if name not in registry]
                )
                if expected_deliveries == 0:
                    blocked_reason = "source_has_no_deliveries"
            except Exception:
                blocked_reason = "invalid_retained_source_json"

        row = {
            "match_id": game.id,
            "batch_id": batch.id,
            "import_source": origin,
            "completeness": completeness,
            "eligible": blocked_reason is None and expected_deliveries > 0,
            "blocked_reason": blocked_reason,
            "missing_source_json": blocked_reason == "missing_source_json",
            "duplicate_delivery_risk": duplicate_risk,
            "apply_deliveries_previously_run": bool(hist_meta.get("deliveries_imported")),
            "source_json_retained": payload is not None,
            "registry_people_available": registry_available,
            "registry_people_count": registry_count,
            "players_without_source_ids": players_without_source_ids,
            "expected_deliveries": expected_deliveries,
            "expected_wickets": expected_wickets,
            "expected_players": expected_players,
        }
        row.update(_match_identity(batch, game))
        if row["eligible"]:
            eligible += 1
        else:
            blocked += 1
        records.append(row)

    return {
        "total_imported_cpl_matches": len(cpl_pairs),
        "completeness_counts": completeness_counts,
        "import_origin_counts": import_origin_counts,
        "player_aggregate_scope": "delivery-complete matches only",
        "rollback_feasibility": (
            "Per-batch game rollback is supported via /api/historical-import/json/batches/{batch_id}/rollback. "
            "Derived before/after snapshots are recorded in historical_import._delivery_backfill_log."
        ),
        "eligible_matches": eligible,
        "blocked_matches": blocked,
        "selected_matches": len(cpl_pairs),
        "records": records,
    }


async def apply_delivery_backfill(
    db: AsyncSession,
    *,
    match_ids: list[str],
    batch_ids: list[str],
    max_batch_size: int,
    source_payloads_by_batch: dict[str, dict[str, Any]] | None = None,
) -> dict[str, Any]:
    audit = await audit_delivery_backfill(
        db,
        match_ids=match_ids,
        batch_ids=batch_ids,
        max_batch_size=max_batch_size,
        source_payloads_by_batch=source_payloads_by_batch,
    )

    results: list[dict[str, Any]] = []
    changed_match_ids: list[str] = []
    blocked_records: list[dict[str, str]] = []
    deliveries_rebuilt = 0
    wickets_rebuilt = 0
    mappings_updated = 0
    mapping_records_updated = 0
    mappings_created = 0
    resolved_players = 0
    unresolved_players = 0
    ambiguous_players = 0
    resolved_venues = 0
    unresolved_venues = 0
    processed = 0
    skipped = 0
    failed = 0

    record_lookup = {row["batch_id"]: row for row in audit["records"]}
    for row in audit["records"]:
        if not row["eligible"]:
            skipped += 1
            blocked_records.append(
                {
                    "match_id": row["match_id"],
                    "batch_id": row["batch_id"],
                    "reason": row.get("blocked_reason") or "blocked",
                }
            )

    batch_ids_to_process = [row["batch_id"] for row in audit["records"] if row["eligible"]]
    for batch_id in batch_ids_to_process:
        batch = await db.scalar(
            select(HistoricalImportBatch).where(HistoricalImportBatch.id == batch_id)
        )
        if batch is None or not batch.applied_game_id:
            failed += 1
            blocked_records.append(
                {"match_id": "", "batch_id": batch_id, "reason": "batch_or_game_not_found"}
            )
            continue
        game = await db.scalar(select(Game).where(Game.id == batch.applied_game_id))
        if game is None:
            failed += 1
            blocked_records.append(
                {"match_id": "", "batch_id": batch_id, "reason": "batch_or_game_not_found"}
            )
            continue

        payload_override = (source_payloads_by_batch or {}).get(batch.id)
        if isinstance(payload_override, dict):
            payload = json.dumps(payload_override, separators=(",", ":")).encode("utf-8")
            load_error = None
        else:
            payload, load_error = _load_retained_payload(batch)
        if payload is None:
            failed += 1
            blocked_records.append(
                {
                    "match_id": game.id,
                    "batch_id": batch_id,
                    "reason": load_error or "missing_source_json",
                }
            )
            continue

        before_deliveries = len(game.deliveries) if isinstance(game.deliveries, list) else 0
        before_wickets = (
            sum(1 for d in (game.deliveries or []) if isinstance(d, dict) and d.get("is_wicket"))
            if isinstance(game.deliveries, list)
            else 0
        )
        before_completeness = _completeness(game)
        game_id_for_result = game.id

        try:
            _, warnings, error = await apply_historical_deliveries(
                db,
                batch_id=batch_id,
                confirm=True,
                raw_payload=payload,
                allow_reprocess=True,
            )
            if error is not None:
                failed += 1
                results.append(
                    {
                        "match_id": game_id_for_result,
                        "batch_id": batch_id,
                        "status": "failed",
                        "reason": error,
                        "completeness_before": before_completeness,
                        "completeness_after": before_completeness,
                        "deliveries_before": before_deliveries,
                        "deliveries_after": before_deliveries,
                        "wickets_before": before_wickets,
                        "wickets_after": before_wickets,
                        "player_mappings_updated": 0,
                        "unresolved_players": 0,
                        "unresolved_venues": 0,
                    }
                )
                continue

            game = await db.scalar(select(Game).where(Game.id == batch.applied_game_id))
            if game is None:
                failed += 1
                results.append(
                    {
                        "match_id": game_id_for_result,
                        "batch_id": batch_id,
                        "status": "failed",
                        "reason": "game_not_found_after_apply",
                        "completeness_before": before_completeness,
                        "completeness_after": before_completeness,
                        "deliveries_before": before_deliveries,
                        "deliveries_after": before_deliveries,
                        "wickets_before": before_wickets,
                        "wickets_after": before_wickets,
                        "player_mappings_updated": 0,
                        "unresolved_players": 0,
                        "unresolved_venues": 0,
                    }
                )
                continue

            dry_run = batch.dry_run_summary if isinstance(batch.dry_run_summary, dict) else {}
            canonical_preview = (
                dry_run.get("canonical_preview")
                if isinstance(dry_run.get("canonical_preview"), dict)
                else {}
            )
            source_provenance = (
                canonical_preview.get("source_provenance")
                if isinstance(canonical_preview.get("source_provenance"), dict)
                else {}
            )
            competition_context = (
                canonical_preview.get("competition_context")
                if isinstance(canonical_preview.get("competition_context"), dict)
                else {}
            )
            roster_snapshot = (
                canonical_preview.get("squad_roster_snapshot")
                if isinstance(canonical_preview.get("squad_roster_snapshot"), list)
                else []
            )
            metadata_preview = (
                dry_run.get("metadata_preview")
                if isinstance(dry_run.get("metadata_preview"), dict)
                else {}
            )
            player_names = (
                dry_run.get("player_names_found")
                if isinstance(dry_run.get("player_names_found"), list)
                else []
            )
            parsed_payload: dict[str, Any] = {}
            try:
                parsed_any = json.loads(payload.decode("utf-8"))
                if isinstance(parsed_any, dict):
                    parsed_payload = parsed_any
            except Exception:
                parsed_payload = {}
            source_identity_inputs = _extract_source_identity_inputs(parsed_payload)
            source_registry_people = (
                source_identity_inputs.get("source_registry_people")
                if isinstance(source_identity_inputs.get("source_registry_people"), dict)
                else {}
            )
            payload_player_names = (
                source_identity_inputs.get("unique_players")
                if isinstance(source_identity_inputs.get("unique_players"), list)
                else []
            )
            source_venue_name = source_identity_inputs.get("source_venue_name")
            combined_player_names = sorted(
                {
                    str(name).strip()
                    for name in [*player_names, *payload_player_names]
                    if isinstance(name, str) and str(name).strip()
                }
            )

            registry_summary = await register_historical_source_players(
                db,
                batch_id=batch.id,
                game_id=game.id,
                source_schema=str(source_provenance.get("source_schema") or "unknown"),
                source_system="historical_import_json",
                source_provenance=source_provenance,
                competition_context=competition_context,
                roster_snapshot=roster_snapshot,
                player_names=combined_player_names,
                match_date=str(metadata_preview.get("date") or ""),
            )
            mappings_updated += int(registry_summary.get("resolved_count") or 0)
            mapping_records_updated += int(registry_summary.get("mapping_records_updated") or 0)
            mappings_created += int(registry_summary.get("mapping_records_created") or 0)
            resolved_players += int(registry_summary.get("resolved_count") or 0)
            unresolved_players += int(registry_summary.get("unresolved_count") or 0)
            ambiguous_players += int(registry_summary.get("ambiguous_count") or 0)

            phases = game.phases if isinstance(game.phases, dict) else {}
            hist_meta = (
                phases.get("historical_import")
                if isinstance(phases.get("historical_import"), dict)
                else {}
            )
            venue_resolution = (
                hist_meta.get("venue_resolution")
                if isinstance(hist_meta.get("venue_resolution"), dict)
                else {}
            )
            resolved_venue = int(bool(venue_resolution.get("canonical_venue_id")))
            unresolved_venue = int(not bool(resolved_venue))
            resolved_venues += resolved_venue
            unresolved_venues += unresolved_venue
            unresolved_player_reasons = []
            for item in registry_summary.get("unresolved_reasons") or []:
                if not isinstance(item, dict):
                    continue
                source_name = str(item.get("source_player_name") or "").strip()
                reason = str(item.get("reason") or "").strip() or "no_exact_match"
                if (
                    not source_registry_people.get(source_name)
                    and reason == "no_exact_match"
                ):
                    reason = "missing_source_id"
                unresolved_player_reasons.append(
                    {
                        "source_player_name": source_name,
                        "source_player_id": item.get("source_player_id"),
                        "reason": reason,
                        "resolution_state": item.get("resolution_state"),
                    }
                )
            ambiguous_player_reasons = [
                item
                for item in (registry_summary.get("ambiguous_reasons") or [])
                if isinstance(item, dict)
            ]
            unresolved_venue_reasons = []
            if unresolved_venue:
                unresolved_venue_reasons.append(
                    {
                        "source_venue_name": source_venue_name
                        or metadata_preview.get("venue")
                        or venue_resolution.get("raw_imported_value"),
                        "reason": venue_resolution.get("unresolved_reason")
                        or "venue_alias_missing",
                    }
                )

            after_deliveries = len(game.deliveries) if isinstance(game.deliveries, list) else 0
            after_wickets = (
                sum(
                    1
                    for d in (game.deliveries or [])
                    if isinstance(d, dict) and d.get("is_wicket")
                )
                if isinstance(game.deliveries, list)
                else 0
            )
            after_completeness = _completeness(game)

            log = hist_meta.get("_delivery_backfill_log")
            log_entries = list(log) if isinstance(log, list) else []
            log_entries.append(
                {
                    "batch_id": batch.id,
                    "processed_at": dt.datetime.now(dt.UTC).isoformat(),
                    "before": {
                        "completeness": before_completeness,
                        "deliveries": before_deliveries,
                        "wickets": before_wickets,
                    },
                    "after": {
                        "completeness": after_completeness,
                        "deliveries": after_deliveries,
                        "wickets": after_wickets,
                    },
                    "warnings": warnings,
                }
            )
            hist_meta["_delivery_backfill_log"] = log_entries
            hist_meta["player_identity_registry"] = registry_summary
            phases["historical_import"] = hist_meta
            game.phases = phases
            db.add(game)
            await db.commit()

            deliveries_rebuilt += max(after_deliveries - before_deliveries, 0)
            wickets_rebuilt += max(after_wickets - before_wickets, 0)
            changed_match_ids.append(game.id)
            processed += 1
            results.append(
                {
                    "match_id": game.id,
                    "batch_id": batch.id,
                    "status": "processed",
                    "reason": None,
                    "completeness_before": before_completeness,
                    "completeness_after": after_completeness,
                    "deliveries_before": before_deliveries,
                    "deliveries_after": after_deliveries,
                    "wickets_before": before_wickets,
                    "wickets_after": after_wickets,
                    "player_mappings_updated": int(
                        registry_summary.get("resolved_count") or 0
                    ),
                    "mappings_updated": int(registry_summary.get("mapping_records_updated") or 0),
                    "mappings_created": int(registry_summary.get("mapping_records_created") or 0),
                    "resolved_players": int(registry_summary.get("resolved_count") or 0),
                    "unresolved_players": int(registry_summary.get("unresolved_count") or 0),
                    "ambiguous_players": int(registry_summary.get("ambiguous_count") or 0),
                    "resolved_venues": resolved_venue,
                    "unresolved_venues": unresolved_venue,
                    "unresolved_player_reasons": unresolved_player_reasons,
                    "ambiguous_player_reasons": ambiguous_player_reasons,
                    "unresolved_venue_reasons": unresolved_venue_reasons,
                }
            )

        except Exception:
            _log.exception(
                "apply_delivery_backfill: unexpected error for batch",
                extra={"batch_id": batch_id},
            )
            failed += 1
            with suppress(Exception):
                await db.rollback()
            results.append(
                {
                    "match_id": game_id_for_result,
                    "batch_id": batch_id,
                    "status": "failed",
                    "reason": "internal_error",
                    "completeness_before": before_completeness,
                    "completeness_after": before_completeness,
                    "deliveries_before": before_deliveries,
                    "deliveries_after": before_deliveries,
                    "wickets_before": before_wickets,
                    "wickets_after": before_wickets,
                    "player_mappings_updated": 0,
                    "mappings_created": 0,
                    "resolved_players": 0,
                    "unresolved_players": 0,
                    "ambiguous_players": 0,
                    "resolved_venues": 0,
                    "unresolved_venues": 0,
                    "unresolved_player_reasons": [],
                    "ambiguous_player_reasons": [],
                    "unresolved_venue_reasons": [],
                }
            )

    if processed > 0 and failed == 0:
        status = "applied"
    elif processed > 0:
        status = "partial"
    else:
        status = "failed"

    return {
        "status": status,
        "processed_matches": processed,
        "skipped_matches": skipped,
        "failed_matches": failed,
        "deliveries_rebuilt": deliveries_rebuilt,
        "wickets_rebuilt": wickets_rebuilt,
        "player_mappings_updated": mappings_updated,
        "mappings_updated": mapping_records_updated,
        "mappings_created": mappings_created,
        "resolved_players": resolved_players,
        "unresolved_players": unresolved_players,
        "ambiguous_players": ambiguous_players,
        "resolved_venues": resolved_venues,
        "unresolved_venues": unresolved_venues,
        "changed_match_ids": changed_match_ids,
        "blocked_records": blocked_records,
        "results": results,
        "rollback_info": (
            "Use /api/historical-import/json/batches/{batch_id}/rollback with confirm=true "
            "to remove a batch-applied game. Backfill snapshots are stored in "
            "game.phases.historical_import._delivery_backfill_log."
        ),
        "audit_snapshot": record_lookup,
    }
