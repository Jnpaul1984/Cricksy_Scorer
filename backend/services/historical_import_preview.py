from __future__ import annotations

import hashlib
import json
from typing import Any

from backend.api.schemas.historical_import import (
    HistoricalImportDetectedSections,
    HistoricalImportDryRunResponse,
    HistoricalImportDuplicatePreview,
    HistoricalImportInningsPreview,
    HistoricalImportIssue,
    HistoricalImportMetadataPreview,
)
from backend.domain.constants import norm_extra

INNINGS_NODE_KEYS = ("team", "balls", "deliveries", "overs", "runs", "wickets")
DELIVERY_PLAYER_KEYS = ("batsman", "batter", "striker", "non_striker", "bowler")
DUPLICATE_TRACKING_MESSAGE_NO_DB = (
    "Duplicate tracking table is not available in the current schema; "
    "Phase 5C schema work is required for persisted duplicate detection."
)
# Keep old name for backwards compat with any external references
DUPLICATE_TRACKING_MESSAGE = DUPLICATE_TRACKING_MESSAGE_NO_DB


def _hash_payload(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _to_canonical_json_bytes(data: Any) -> bytes:
    return json.dumps(data, separators=(",", ":"), sort_keys=True, ensure_ascii=False).encode(
        "utf-8"
    )


def _derive_semantic_key(
    parsed: dict[str, Any],
    metadata_preview: HistoricalImportMetadataPreview,
    team_names: list[str],
) -> str | None:
    """Derive a stable semantic key for duplicate detection.

    Key format: ``<match_type>|<date>|<team_a>|<team_b>`` (sorted team names).
    Returns None if any required component is missing.
    """
    match_type = metadata_preview.match_type
    date = metadata_preview.date
    if not match_type or not date:
        return None
    if len(team_names) < 2:
        return None
    sorted_teams = sorted(t.strip().lower() for t in team_names)
    return "|".join([match_type.strip().lower(), date.strip(), *sorted_teams])


def _as_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _first_str(values: Any) -> str | None:
    if isinstance(values, list) and values:
        return _as_str(values[0])
    return None


def _safe_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _is_legal_delivery(delivery: dict[str, Any]) -> bool:
    extra_type = norm_extra(_as_str(delivery.get("extra_type")))
    if extra_type in {"wd", "nb"}:
        return False

    extras = delivery.get("extras")
    has_illegal_extras = isinstance(extras, dict) and (
        _safe_int(extras.get("wides")) > 0 or _safe_int(extras.get("noballs")) > 0
    )
    return not has_illegal_extras


def _extract_team_names(payload: dict[str, Any]) -> list[str]:
    names: set[str] = set()
    teams = payload.get("teams")
    if isinstance(teams, list):
        for team in teams:
            if isinstance(team, str) and team.strip():
                names.add(team.strip())
            elif isinstance(team, dict):
                maybe = _as_str(team.get("name"))
                if maybe:
                    names.add(maybe)
    elif isinstance(teams, dict):
        for value in teams.values():
            if isinstance(value, dict):
                maybe = _as_str(value.get("name"))
                if maybe:
                    names.add(maybe)
            elif isinstance(value, str) and value.strip():
                names.add(value.strip())

    for key in ("team_a", "team_b", "teamA", "teamB"):
        value = payload.get(key)
        if isinstance(value, dict):
            maybe = _as_str(value.get("name"))
            if maybe:
                names.add(maybe)
        elif isinstance(value, str) and value.strip():
            names.add(value.strip())

    return sorted(names)


def _extract_players_from_teams(payload: dict[str, Any]) -> set[str]:
    players: set[str] = set()

    def _consume_player_entry(entry: Any) -> None:
        if isinstance(entry, str) and entry.strip():
            players.add(entry.strip())
        elif isinstance(entry, dict):
            for key in ("name", "player", "full_name"):
                maybe = _as_str(entry.get(key))
                if maybe:
                    players.add(maybe)
                    break

    teams = payload.get("teams")
    if isinstance(teams, list):
        for team in teams:
            if isinstance(team, dict):
                team_players = team.get("players")
                if isinstance(team_players, list):
                    for p in team_players:
                        _consume_player_entry(p)

    for key in ("team_a", "team_b"):
        team = payload.get(key)
        if isinstance(team, dict):
            team_players = team.get("players")
            if isinstance(team_players, list):
                for p in team_players:
                    _consume_player_entry(p)

    return players


def _extract_deliveries_from_overs(overs: Any) -> list[dict[str, Any]]:
    deliveries: list[dict[str, Any]] = []
    if not isinstance(overs, list):
        return deliveries
    for over in overs:
        if not isinstance(over, dict):
            continue
        over_deliveries = over.get("deliveries")
        if isinstance(over_deliveries, list):
            deliveries.extend([d for d in over_deliveries if isinstance(d, dict)])
    return deliveries


def _extract_innings_nodes(innings_value: Any) -> list[dict[str, Any]]:
    if not isinstance(innings_value, list):
        return []

    nodes: list[dict[str, Any]] = []
    for inning in innings_value:
        if not isinstance(inning, dict):
            continue
        if any(k in inning for k in INNINGS_NODE_KEYS):
            nodes.append(inning)
            continue
        if len(inning) == 1:
            nested = next(iter(inning.values()))
            if isinstance(nested, dict):
                normalized = dict(nested)
                if "team" not in normalized:
                    normalized["team"] = next(iter(inning.keys()))
                nodes.append(normalized)
    return nodes


def _detect_format(payload: dict[str, Any], innings_nodes: list[dict[str, Any]]) -> str:
    top_keys = set(payload.keys())
    if {"matchType", "teams", "innings"}.issubset(top_keys):
        return "cricksy_fixture"
    if "innings" in top_keys and ("meta" in top_keys or "info" in top_keys):
        for innings_node in innings_nodes:
            if isinstance(innings_node.get("overs"), list):
                return "cricsheet_json"
    return "unknown"


def _derive_innings_preview(
    innings_nodes: list[dict[str, Any]],
) -> tuple[list[HistoricalImportInningsPreview], set[str], list[HistoricalImportIssue]]:
    previews: list[HistoricalImportInningsPreview] = []
    players: set[str] = set()
    warnings: list[HistoricalImportIssue] = []

    for idx, innings in enumerate(innings_nodes, start=1):
        balls = innings.get("balls")
        deliveries = innings.get("deliveries")
        overs = innings.get("overs")

        normalized_deliveries: list[dict[str, Any]] = []
        if isinstance(balls, list):
            normalized_deliveries = [d for d in balls if isinstance(d, dict)]
        elif isinstance(deliveries, list):
            normalized_deliveries = [d for d in deliveries if isinstance(d, dict)]
        else:
            normalized_deliveries = _extract_deliveries_from_overs(overs)

        innings_team = _as_str(innings.get("team"))

        for delivery in normalized_deliveries:
            for key in DELIVERY_PLAYER_KEYS:
                maybe = _as_str(delivery.get(key))
                if maybe:
                    players.add(maybe)

        explicit_runs = innings.get("runs")
        derived_runs: int | None = explicit_runs if isinstance(explicit_runs, int) else None
        if derived_runs is None and normalized_deliveries:
            total = 0
            for delivery in normalized_deliveries:
                runs_obj = delivery.get("runs")
                if isinstance(runs_obj, dict):
                    total += _safe_int(runs_obj.get("total"))
                    continue
                if isinstance(delivery.get("runs"), int):
                    total += _safe_int(delivery.get("runs"))
                    continue
                total += _safe_int(delivery.get("runs_scored"))
                total += _safe_int(delivery.get("extra_runs"))
            derived_runs = total

        explicit_wickets = innings.get("wickets")
        derived_wickets: int | None = (
            explicit_wickets if isinstance(explicit_wickets, int) else None
        )
        if derived_wickets is None and normalized_deliveries:
            wicket_count = 0
            for delivery in normalized_deliveries:
                wicket = delivery.get("wicket")
                if isinstance(wicket, dict) or wicket is True or bool(delivery.get("is_wicket")):
                    wicket_count += 1
            derived_wickets = wicket_count

        balls_count = len(normalized_deliveries)
        legal_balls_count = sum(
            1 for delivery in normalized_deliveries if _is_legal_delivery(delivery)
        )
        overs_float = None
        if legal_balls_count:
            complete_overs = legal_balls_count // 6
            balls_this_over = legal_balls_count % 6
            overs_float = float(f"{complete_overs}.{balls_this_over}")

        if balls_count == 0:
            warnings.append(
                HistoricalImportIssue(
                    code="MISSING_DELIVERIES",
                    message=f"Innings {idx} has no deliveries/balls data.",
                    severity="warning",
                    path=f"innings[{idx - 1}]",
                )
            )

        previews.append(
            HistoricalImportInningsPreview(
                inning_no=idx,
                team=innings_team,
                deliveries=balls_count,
                runs=derived_runs,
                wickets=derived_wickets,
                overs=overs_float,
            )
        )

    return previews, players, warnings


def build_dry_run_response(raw_payload: bytes) -> tuple[int, HistoricalImportDryRunResponse]:
    try:
        decoded = raw_payload.decode("utf-8")
    except UnicodeDecodeError:
        response = HistoricalImportDryRunResponse(
            status="invalid",
            detected_format="unknown",
            top_level_keys=[],
            detected_sections=HistoricalImportDetectedSections(
                teams=False,
                players=False,
                innings=False,
                deliveries=False,
                metadata=False,
            ),
            metadata_preview=HistoricalImportMetadataPreview(),
            errors=[
                HistoricalImportIssue(
                    code="INVALID_ENCODING",
                    message="Payload must be UTF-8 encoded JSON.",
                    severity="error",
                )
            ],
            duplicate_detection=HistoricalImportDuplicatePreview(
                source_hash_sha256=_hash_payload(raw_payload),
                probable_duplicate="unknown",
                tracking_available=False,
                message=DUPLICATE_TRACKING_MESSAGE,
            ),
        )
        return 400, response

    try:
        parsed = json.loads(decoded)
    except json.JSONDecodeError:
        response = HistoricalImportDryRunResponse(
            status="invalid",
            detected_format="unknown",
            top_level_keys=[],
            detected_sections=HistoricalImportDetectedSections(
                teams=False,
                players=False,
                innings=False,
                deliveries=False,
                metadata=False,
            ),
            metadata_preview=HistoricalImportMetadataPreview(),
            errors=[
                HistoricalImportIssue(
                    code="INVALID_JSON",
                    message="Payload is not valid JSON.",
                    severity="error",
                )
            ],
            duplicate_detection=HistoricalImportDuplicatePreview(
                source_hash_sha256=_hash_payload(raw_payload),
                probable_duplicate="unknown",
                tracking_available=False,
                message=DUPLICATE_TRACKING_MESSAGE,
            ),
        )
        return 400, response

    if not isinstance(parsed, dict):
        response = HistoricalImportDryRunResponse(
            status="invalid",
            detected_format="unknown",
            top_level_keys=[],
            detected_sections=HistoricalImportDetectedSections(
                teams=False,
                players=False,
                innings=False,
                deliveries=False,
                metadata=False,
            ),
            metadata_preview=HistoricalImportMetadataPreview(),
            errors=[
                HistoricalImportIssue(
                    code="UNSUPPORTED_JSON_ROOT",
                    message="Top-level JSON must be an object.",
                    severity="error",
                )
            ],
            duplicate_detection=HistoricalImportDuplicatePreview(
                source_hash_sha256=_hash_payload(raw_payload),
                probable_duplicate="unknown",
                tracking_available=False,
                message=DUPLICATE_TRACKING_MESSAGE,
            ),
        )
        return 400, response

    innings_nodes = _extract_innings_nodes(parsed.get("innings"))
    detected_format = _detect_format(parsed, innings_nodes)
    team_names = _extract_team_names(parsed)
    players_from_teams = _extract_players_from_teams(parsed)

    innings_preview, players_from_innings, innings_warnings = _derive_innings_preview(innings_nodes)

    errors: list[HistoricalImportIssue] = []
    warnings = list(innings_warnings)

    if not innings_nodes:
        errors.append(
            HistoricalImportIssue(
                code="MISSING_INNINGS",
                message="Required innings structure is missing or empty.",
                severity="error",
                path="innings",
            )
        )

    total_deliveries = sum(p.deliveries for p in innings_preview)
    if innings_nodes and total_deliveries == 0:
        errors.append(
            HistoricalImportIssue(
                code="MISSING_DELIVERY_EVENTS",
                message="No delivery/ball events were found in innings data.",
                severity="error",
                path="innings",
            )
        )

    if detected_format == "unknown":
        errors.append(
            HistoricalImportIssue(
                code="UNSUPPORTED_FORMAT",
                message="Unsupported historical JSON shape for dry-run preview.",
                severity="error",
            )
        )

    if total_deliveries > 0 and all(p.runs is None for p in innings_preview):
        warnings.append(
            HistoricalImportIssue(
                code="RUN_TOTALS_NOT_DERIVABLE",
                message="Could not derive innings run totals from provided delivery events.",
                severity="warning",
                path="innings",
            )
        )

    info_value = parsed.get("info")
    info_payload: dict[str, Any] = info_value if isinstance(info_value, dict) else {}
    result_value = parsed.get("result")
    result_summary: str | None
    if isinstance(result_value, dict):
        result_summary = _as_str(result_value.get("summary"))
    else:
        result_summary = _as_str(result_value)

    metadata_preview = HistoricalImportMetadataPreview(
        match_type=_as_str(parsed.get("matchType")) or _as_str(info_payload.get("match_type")),
        venue=_as_str(parsed.get("venue")) or _as_str(info_payload.get("venue")),
        date=_as_str(parsed.get("date")) or _first_str(info_payload.get("dates")),
        result=result_summary,
    )

    player_names = sorted(players_from_teams.union(players_from_innings))

    detected_sections = HistoricalImportDetectedSections(
        teams=bool(team_names),
        players=bool(player_names),
        innings=bool(innings_nodes),
        deliveries=total_deliveries > 0,
        metadata=any(
            [
                metadata_preview.match_type,
                metadata_preview.venue,
                metadata_preview.date,
                metadata_preview.result,
            ]
        ),
    )

    if detected_format == "unknown":
        status: str = "unsupported"
    elif errors:
        status = "invalid"
    else:
        status = "valid"

    normalized_hash = _hash_payload(_to_canonical_json_bytes(parsed))
    semantic_key = _derive_semantic_key(parsed, metadata_preview, team_names)

    response = HistoricalImportDryRunResponse(
        status=status,
        detected_format=detected_format,
        top_level_keys=sorted(parsed.keys()),
        detected_sections=detected_sections,
        metadata_preview=metadata_preview,
        teams_preview=team_names,
        innings_count=len(innings_nodes),
        delivery_count=total_deliveries,
        player_names_found=player_names,
        innings_preview=innings_preview,
        warnings=warnings,
        errors=errors,
        duplicate_detection=HistoricalImportDuplicatePreview(
            source_hash_sha256=normalized_hash,
            probable_duplicate="unknown",
            tracking_available=False,
            semantic_key=semantic_key,
            semantic_duplicate=False,
            message=DUPLICATE_TRACKING_MESSAGE,
        ),
        no_persistence=True,
    )
    return 200, response
