"""Phase 5P — deterministic model-training dataset builder (dataset export only).

Builds a governed dataset artifact from validated historical import records.
No model training occurs here.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass, field
from typing import Any

from backend.services.analyst_access import scoped_games_stmt
from backend.sql_app.models import Game, GameStatus, HistoricalImportBatch
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

_INCOMPLETE_IMPORT_STATUSES: frozenset[str] = frozenset(
    {"scanned", "metadata_extracted", "pending_full_import"}
)
_DATASET_SCHEMA_VERSION = "training_dataset_v1"


@dataclass(frozen=True)
class DatasetBuildFilters:
    """Optional filters for dataset assembly."""

    source_format: str | None = None
    match_type: str | None = None
    season: str | None = None
    competition: str | None = None


@dataclass(frozen=True)
class DatasetBuildRequest:
    """Read-only request for deterministic dataset assembly."""

    filters: DatasetBuildFilters = field(default_factory=DatasetBuildFilters)
    generated_at: dt.datetime | None = None


@dataclass(frozen=True)
class _EligibleMatch:
    game: Game
    batch: HistoricalImportBatch
    hist_meta: dict[str, Any]
    innings_summary: list[dict[str, Any]]


def _historical_meta(game: Game) -> dict[str, Any] | None:
    phases = game.phases if isinstance(game.phases, dict) else {}
    meta = phases.get("historical_import")
    if isinstance(meta, dict) and meta.get("is_historical") is True:
        return meta
    return None


def _to_int(value: Any, *, default: int = 0) -> int:
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


def _to_float(value: Any, *, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _normalize_innings_summary(game: Game) -> list[dict[str, Any]]:
    phases = game.phases if isinstance(game.phases, dict) else {}
    raw = phases.get("historical_innings_summary")
    if not isinstance(raw, list):
        return []

    normalized: list[dict[str, Any]] = []
    for inn in raw:
        if not isinstance(inn, dict):
            continue
        inning_no = _to_int(inn.get("inning_no"), default=-1)
        runs = _to_int(inn.get("runs"), default=-1)
        wickets = _to_int(inn.get("wickets"), default=-1)
        legal_balls = _to_int(inn.get("legal_balls"), default=-1)
        if runs < 0 or wickets < 0:
            return []

        team = inn.get("team")
        if not isinstance(team, str) or not team.strip() or inning_no <= 0 or legal_balls < 0:
            return []

        overs_raw = inn.get("overs")
        default_overs = (legal_balls / 6) if legal_balls > 0 else 0.0
        overs = _to_float(overs_raw, default=default_overs)

        normalized.append(
            {
                "inning_no": inning_no,
                "team": team.strip(),
                "runs": runs,
                "wickets": wickets,
                "legal_balls": legal_balls,
                "overs": overs,
            }
        )

    return sorted(normalized, key=lambda item: int(item["inning_no"]))


def _extras_by_inning(game: Game) -> dict[int, int]:
    extras_totals: dict[int, int] = defaultdict(int)
    deliveries = game.deliveries if isinstance(game.deliveries, list) else []

    for delivery in deliveries:
        if not isinstance(delivery, dict):
            continue
        inning_raw = delivery.get("inning")
        extra_raw = delivery.get("extra_runs")
        try:
            inning_no = _to_int(inning_raw, default=-1)
            extra_runs = _to_int(extra_raw, default=0)
        except (TypeError, ValueError):
            continue
        if inning_no <= 0:
            continue
        extras_totals[inning_no] += extra_runs

    return dict(extras_totals)


def _hash_group_key(batch: HistoricalImportBatch) -> str:
    return str(batch.source_hash_sha256 or "").strip().lower()


def _is_match_eligible(
    game: Game,
    batch: HistoricalImportBatch,
    hist_meta: dict[str, Any],
    innings_summary: list[dict[str, Any]],
) -> str | None:
    if batch.status in _INCOMPLETE_IMPORT_STATUSES:
        return "metadata_only_pending_full_import"
    if not batch.is_finalized:
        return "batch_not_finalized"
    if not batch.applied_game_id:
        return "no_game_applied"
    if batch.applied_game_id != game.id:
        return "batch_game_mismatch"
    if batch.status != "valid":
        return f"invalid_status_{batch.status}"
    if batch.error_count > 0:
        return "has_errors"
    if hist_meta.get("source_unsafe") is True:
        return "source_marked_unsafe"
    repair_log = hist_meta.get("_repair_log")
    if isinstance(repair_log, list) and repair_log:
        return "repaired_not_revalidated"
    if not innings_summary:
        return "missing_required_innings_data"
    return None


def _apply_filters(
    game: Game,
    batch: HistoricalImportBatch,
    hist_meta: dict[str, Any],
    filters: DatasetBuildFilters,
) -> bool:
    if filters.source_format and batch.source_format != filters.source_format:
        return False
    if filters.match_type and (game.match_type or "") != filters.match_type:
        return False
    if filters.season and str(hist_meta.get("season") or "") != filters.season:
        return False
    return (
        filters.competition is None or str(hist_meta.get("event_name") or "") == filters.competition
    )


def _team_name(team_blob: Any) -> str | None:
    if isinstance(team_blob, dict):
        name = team_blob.get("name")
        if isinstance(name, str) and name.strip():
            return name.strip()
    return None


def _build_rows(candidates: list[_EligibleMatch]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    for candidate in sorted(candidates, key=lambda item: item.game.id):
        game = candidate.game
        batch = candidate.batch
        hist_meta = candidate.hist_meta
        team_a = _team_name(game.team_a)
        team_b = _team_name(game.team_b)
        extras = _extras_by_inning(game)

        for inn in candidate.innings_summary:
            batting_team = str(inn["team"])
            bowling_team: str | None = None
            if team_a and team_b:
                if batting_team == team_a:
                    bowling_team = team_b
                elif batting_team == team_b:
                    bowling_team = team_a

            legal_balls = int(inn["legal_balls"])
            runs = int(inn["runs"])
            run_rate = round((runs * 6 / legal_balls), 4) if legal_balls > 0 else 0.0
            inning_no = int(inn["inning_no"])

            rows.append(
                {
                    "match_id": game.id,
                    "innings_number": inning_no,
                    "batting_team_name": batting_team,
                    "bowling_team_name": bowling_team,
                    "match_type": game.match_type,
                    "venue": hist_meta.get("venue"),
                    "season": hist_meta.get("season"),
                    "competition": hist_meta.get("event_name"),
                    "source_format": batch.source_format,
                    "source_hash_sha256": batch.source_hash_sha256,
                    "runs": runs,
                    "wickets": int(inn["wickets"]),
                    "extras": int(extras.get(inning_no, 0)),
                    "legal_balls": legal_balls,
                    "overs": float(inn["overs"]),
                    "run_rate": run_rate,
                    "result": game.result,
                }
            )

    return sorted(rows, key=lambda row: (str(row["match_id"]), int(row["innings_number"])))


def _group_exclusions(excluded: list[dict[str, Any]]) -> dict[str, int]:
    return dict(sorted(Counter(str(item["reason"]) for item in excluded).items()))


def _deterministic_fingerprint(payload: dict[str, Any]) -> str:
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
            "utf-8"
        )
    ).hexdigest()
    return digest


async def build_model_training_dataset(
    db: AsyncSession,
    request: DatasetBuildRequest,
    current_user: Any | None = None,
) -> dict[str, Any]:
    """Build a deterministic, governed model-training dataset artifact.

    Reads only validated historical import records and never mutates official match truth.
    """
    if current_user is None:
        stmt = select(Game).where(Game.status == GameStatus.completed)
    else:
        stmt = scoped_games_stmt(current_user).where(Game.status == GameStatus.completed)

    games_result = await db.execute(stmt)
    games = list(games_result.scalars().all())

    historical_games: list[tuple[Game, dict[str, Any]]] = []
    excluded: list[dict[str, Any]] = []
    for game in games:
        hist_meta = _historical_meta(game)
        if hist_meta is None:
            continue
        historical_games.append((game, hist_meta))

    batch_ids = {
        str(meta.get("batch_id"))
        for _, meta in historical_games
        if isinstance(meta.get("batch_id"), str) and str(meta.get("batch_id")).strip()
    }

    batch_lookup: dict[str, HistoricalImportBatch] = {}
    if batch_ids:
        batch_result = await db.execute(
            select(HistoricalImportBatch).where(HistoricalImportBatch.id.in_(batch_ids))
        )
        for batch in batch_result.scalars().all():
            batch_lookup[batch.id] = batch

    pre_dedupe_candidates: list[_EligibleMatch] = []

    for game, hist_meta in sorted(historical_games, key=lambda item: item[0].id):
        batch_id_raw = hist_meta.get("batch_id")
        batch_id = str(batch_id_raw).strip() if isinstance(batch_id_raw, str) else ""
        if not batch_id:
            excluded.append({"match_id": game.id, "reason": "batch_id_missing"})
            continue

        batch = batch_lookup.get(batch_id)
        if batch is None:
            excluded.append({"match_id": game.id, "reason": "batch_record_not_found"})
            continue

        if not _apply_filters(game, batch, hist_meta, request.filters):
            excluded.append({"match_id": game.id, "reason": "filtered_out"})
            continue

        innings_summary = _normalize_innings_summary(game)
        ineligible_reason = _is_match_eligible(game, batch, hist_meta, innings_summary)
        if ineligible_reason is not None:
            excluded.append({"match_id": game.id, "reason": ineligible_reason})
            continue

        pre_dedupe_candidates.append(
            _EligibleMatch(
                game=game, batch=batch, hist_meta=hist_meta, innings_summary=innings_summary
            )
        )

    included_after_hash: list[_EligibleMatch] = []
    grouped_by_hash: dict[str, list[_EligibleMatch]] = defaultdict(list)
    for candidate in pre_dedupe_candidates:
        grouped_by_hash[_hash_group_key(candidate.batch)].append(candidate)

    for hash_key, candidates in grouped_by_hash.items():
        ranked = sorted(
            candidates,
            key=lambda item: (
                item.batch.created_at or dt.datetime.min.replace(tzinfo=dt.UTC),
                item.game.id,
            ),
        )
        included_after_hash.append(ranked[0])
        if hash_key:
            for duplicate in ranked[1:]:
                excluded.append(
                    {
                        "match_id": duplicate.game.id,
                        "reason": "duplicate_source_hash",
                        "duplicate_of": ranked[0].game.id,
                    }
                )

    final_candidates: list[_EligibleMatch] = []
    grouped_by_semantic: dict[str, list[_EligibleMatch]] = defaultdict(list)
    for candidate in included_after_hash:
        semantic_key = str(candidate.batch.semantic_key or "").strip().lower()
        if semantic_key:
            grouped_by_semantic[semantic_key].append(candidate)
        else:
            final_candidates.append(candidate)

    for semantic_key, candidates in grouped_by_semantic.items():
        ranked = sorted(
            candidates,
            key=lambda item: (
                item.batch.created_at or dt.datetime.min.replace(tzinfo=dt.UTC),
                item.game.id,
            ),
        )
        final_candidates.append(ranked[0])
        if semantic_key:
            for duplicate in ranked[1:]:
                excluded.append(
                    {
                        "match_id": duplicate.game.id,
                        "reason": "duplicate_semantic_key",
                        "duplicate_of": ranked[0].game.id,
                    }
                )

    rows = _build_rows(final_candidates)
    included_match_ids = sorted({candidate.game.id for candidate in final_candidates})

    generated_at = request.generated_at or dt.datetime.now(dt.UTC)
    parameters = {
        "source_format": request.filters.source_format,
        "match_type": request.filters.match_type,
        "season": request.filters.season,
        "competition": request.filters.competition,
    }

    exclusion_reasons = _group_exclusions(excluded)

    fingerprint_payload = {
        "dataset_schema_version": _DATASET_SCHEMA_VERSION,
        "parameters": parameters,
        "included_match_ids": included_match_ids,
        "exclusion_reasons": exclusion_reasons,
        "rows": rows,
    }

    return {
        "dataset_schema_version": _DATASET_SCHEMA_VERSION,
        "generated_at": generated_at.isoformat(),
        "build_fingerprint": _deterministic_fingerprint(fingerprint_payload),
        "parameters": parameters,
        "provenance": {
            "source": "historical_import_registry",
            "eligibility_version": "phase_5p_v1",
            "read_only": True,
        },
        "included_match_count": len(included_match_ids),
        "excluded_match_count": len(excluded),
        "exclusion_reasons": exclusion_reasons,
        "included_match_ids": included_match_ids,
        "excluded_matches": sorted(
            excluded,
            key=lambda item: (str(item.get("match_id", "")), str(item.get("reason", ""))),
        ),
        "row_count": len(rows),
        "rows": rows,
    }
