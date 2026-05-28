from __future__ import annotations

import hashlib
import json
import re
from typing import Any

from backend.api.schemas.historical_import import (
    HistoricalImportCanonicalPreview,
    HistoricalImportCompetitionContext,
    HistoricalImportDetectedSections,
    HistoricalImportDryRunResponse,
    HistoricalImportDuplicatePreview,
    HistoricalImportInningsPreview,
    HistoricalImportIssue,
    HistoricalImportMetadataPreview,
    HistoricalImportRosterTeamSnapshot,
    HistoricalImportSchemaClassification,
    HistoricalImportVenueContext,
)
from backend.domain.constants import norm_extra
from backend.services.analyst_registry_service import classify_age_category, classify_gender
from backend.services.cpl_team_alias_registry import canonicalize_team_name, is_known_team_alias
from backend.services.cpl_venue_alias_registry import canonicalize_venue_name, is_known_venue_alias

INNINGS_NODE_KEYS = ("team", "balls", "deliveries", "overs", "runs", "wickets")
DELIVERY_PLAYER_KEYS = ("batsman", "batter", "striker", "non_striker", "bowler")
DUPLICATE_TRACKING_MESSAGE_NO_DB = (
    "Duplicate tracking table is not available in the current schema; "
    "Phase 5C schema work is required for persisted duplicate detection."
)
# Keep old name for backwards compat with any external references
DUPLICATE_TRACKING_MESSAGE = DUPLICATE_TRACKING_MESSAGE_NO_DB
ADAPTER_ID = "historical_json_competition_adapter"
ADAPTER_VERSION = "10b.1"
_INTERNATIONAL_TEAM_HINTS = {
    "india",
    "australia",
    "england",
    "new zealand",
    "south africa",
    "pakistan",
    "sri lanka",
    "bangladesh",
    "afghanistan",
    "west indies",
    "ireland",
    "zimbabwe",
    "netherlands",
    "scotland",
}
_WOMEN_KEYWORDS = re.compile(r"\bwomen\b|\bfemale\b|\bgirl\b|\bwcpl\b", re.I)
_YOUTH_KEYWORDS = re.compile(r"\bu-?1[59]\b|\byouth\b|\bjunior\b|\bacademy\b", re.I)
_SCHOOL_KEYWORDS = re.compile(r"\bschool\b|\bschools\b|\bcollege\b", re.I)


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
    competition_context: HistoricalImportCompetitionContext,
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
    competition_name = (competition_context.competition_name or "").strip().lower()
    season = (competition_context.season or "").strip().lower()
    return "|".join(
        [
            competition_context.competition_type,
            competition_name,
            season,
            match_type.strip().lower(),
            date.strip(),
            *sorted_teams,
        ]
    )


def _as_str(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _first_str(values: Any) -> str | None:
    if isinstance(values, list) and values:
        return _as_str(values[0])
    return None


def _stringify_scalar(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return _as_str(value)
    if isinstance(value, (int, float)):
        return str(value)
    return None


def _safe_int(value: Any) -> int:
    if value is None:
        return 0
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _optional_int(value: Any) -> int | None:
    if value is None or value == "":
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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
    names: list[str] = []
    seen: set[str] = set()

    def _add_name(value: Any) -> None:
        maybe = _as_str(value)
        if maybe is None:
            return
        key = maybe.casefold()
        if key in seen:
            return
        seen.add(key)
        names.append(maybe)

    info_payload = payload.get("info")
    if isinstance(info_payload, dict):
        info_teams = info_payload.get("teams")
        if isinstance(info_teams, list):
            for team in info_teams:
                if isinstance(team, str) and team.strip():
                    _add_name(team)
                elif isinstance(team, dict):
                    _add_name(team.get("name"))

    teams = payload.get("teams")
    if isinstance(teams, list):
        for team in teams:
            if isinstance(team, str) and team.strip():
                _add_name(team)
            elif isinstance(team, dict):
                _add_name(team.get("name"))
    elif isinstance(teams, dict):
        for value in teams.values():
            if isinstance(value, dict):
                _add_name(value.get("name"))
            elif isinstance(value, str) and value.strip():
                _add_name(value)

    for key in ("team_a", "team_b", "teamA", "teamB"):
        value = payload.get(key)
        if isinstance(value, dict):
            _add_name(value.get("name"))
        elif isinstance(value, str) and value.strip():
            _add_name(value)

    return names


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


def _extract_registry_people_map(payload: dict[str, Any]) -> dict[str, str]:
    info_payload = payload.get("info")
    info = info_payload if isinstance(info_payload, dict) else {}
    registry_payload = info.get("registry")
    registry = registry_payload if isinstance(registry_payload, dict) else {}
    people_payload = registry.get("people")
    people = people_payload if isinstance(people_payload, dict) else {}

    mapping: dict[str, str] = {}
    for name, source_id in people.items():
        name_text = _as_str(name)
        source_text = _as_str(source_id)
        if name_text and source_text:
            mapping[name_text] = source_text
    return mapping


def _extract_roster_snapshot(
    payload: dict[str, Any], team_names: list[str], registry_people_map: dict[str, str]
) -> list[HistoricalImportRosterTeamSnapshot]:
    info_payload = payload.get("info")
    info = info_payload if isinstance(info_payload, dict) else {}
    info_players = info.get("players")
    players_map = info_players if isinstance(info_players, dict) else {}
    snapshots: list[HistoricalImportRosterTeamSnapshot] = []

    for team_name in team_names:
        roster_raw = players_map.get(team_name)
        roster_names = (
            [p.strip() for p in roster_raw if isinstance(p, str) and p.strip()]
            if isinstance(roster_raw, list)
            else []
        )
        roster: list[str | dict[str, object]] = []
        for player_name in roster_names:
            source_player_id = registry_people_map.get(player_name)
            if source_player_id:
                roster.append(
                    {
                        "name": player_name,
                        "source_player_id": source_player_id,
                    }
                )
            else:
                roster.append(player_name)
        snapshots.append(
            HistoricalImportRosterTeamSnapshot(
                team_name=team_name,
                playing_xi=list(roster),
                named_squad=list(roster),
                substitutes=[],
                unresolved_entries=[],
                mapping_confidence="high" if roster else "unknown",
            )
        )
    return snapshots


def _collect_team_players(payload: dict[str, Any], team_names: list[str]) -> dict[str, set[str]]:
    info_payload = payload.get("info")
    info = info_payload if isinstance(info_payload, dict) else {}
    info_players = info.get("players")
    players_map = info_players if isinstance(info_players, dict) else {}
    team_players: dict[str, set[str]] = {team_name: set() for team_name in team_names}

    for team_name in team_names:
        roster_raw = players_map.get(team_name)
        if isinstance(roster_raw, list):
            for player in roster_raw:
                player_name = _as_str(player)
                if player_name:
                    team_players.setdefault(team_name, set()).add(player_name)

    teams_payload = payload.get("teams")
    if isinstance(teams_payload, list):
        for team in teams_payload:
            if not isinstance(team, dict):
                continue
            team_name = _as_str(team.get("name"))
            if not team_name:
                continue
            players_raw = team.get("players")
            if isinstance(players_raw, list):
                for player in players_raw:
                    if isinstance(player, dict):
                        player_name = (
                            _as_str(player.get("name"))
                            or _as_str(player.get("player"))
                            or _as_str(player.get("full_name"))
                        )
                    else:
                        player_name = _as_str(player)
                    if player_name:
                        team_players.setdefault(team_name, set()).add(player_name)

    return team_players


def _name_signature(value: str) -> tuple[str, str] | None:
    tokens = [token for token in re.split(r"[^A-Za-z]+", value) if token]
    if len(tokens) < 2:
        return None
    return tokens[-1].lower(), tokens[0][0].lower()


def _classify_match_format(
    raw_match_type: str | None,
    innings_count: int,
    source_dates: list[str],
) -> tuple[str, str]:
    match_type = (raw_match_type or "").strip().lower()
    if not match_type:
        if innings_count > 2 or len(source_dates) > 1:
            return "First-class / multi-day", "inferred"
        return "unknown", "unknown"
    if match_type in {"t20", "t20i", "twenty20", "20_over"}:
        return "T20", "source"
    if match_type in {"odi", "one-day", "one day", "list a"}:
        return "ODI", "source"
    if match_type in {"test", "test match"}:
        return "Test", "source"
    if match_type in {"first-class", "first class", "multi_day", "multi-day"}:
        return "First-class / multi-day", "source"
    if innings_count > 2 or len(source_dates) > 1:
        return "First-class / multi-day", "inferred"
    return "custom", "source"


def _classify_age_category_hint(event_name: str | None, team_names: list[str]) -> tuple[str, str]:
    meta = classify_age_category({"age_category": event_name}) if event_name else "unknown"
    if meta != "unknown":
        return meta, "source"
    haystacks = [event_name or "", *team_names]
    if any(_SCHOOL_KEYWORDS.search(value) for value in haystacks):
        return "school", "inferred"
    if any(_YOUTH_KEYWORDS.search(value) for value in haystacks):
        return "youth", "inferred"
    return "unknown", "unknown"


def _classify_competition_code(
    event_name: str | None,
    team_names: list[str],
    format_category: str,
    age_category: str,
) -> tuple[str, str]:
    lowered = (event_name or "").strip().lower()
    normalized_teams = {team.strip().lower() for team in team_names if team.strip()}
    if not lowered:
        return "UNKNOWN", "unknown"
    if "wcpl" in lowered or (
        "caribbean premier league" in lowered and _WOMEN_KEYWORDS.search(lowered)
    ):
        return "WCPL", "inferred"
    if "caribbean premier league" in lowered or re.search(r"\bcpl\b", lowered):
        return "CPL_MEN", "inferred"
    if age_category == "school":
        return "SCHOOL_CRICKET", "inferred"
    if any(token in lowered for token in ("barbados cricket", "barbados", "bca", "barbadian")):
        return "LOCAL_BARBADOS", "inferred"
    if format_category == "Test":
        return "INTERNATIONAL_TEST", "inferred"
    if format_category == "ODI" and (
        "icc" in lowered or "international" in lowered or "world cup" in lowered
    ):
        return "INTERNATIONAL_ODI", "inferred"
    if format_category == "T20" and (
        "icc" in lowered
        or "international" in lowered
        or "world cup" in lowered
        or normalized_teams.issubset(_INTERNATIONAL_TEAM_HINTS)
    ):
        return "INTERNATIONAL_T20", "inferred"
    if format_category in {"Test", "First-class / multi-day"}:
        return "DOMESTIC_MULTI_DAY", "inferred"
    if any(token in lowered for token in ("custom", "exhibition", "friendly", "festival")):
        return "CUSTOM", "source"
    return "UNKNOWN", "unknown"


def _classify_gender_category(
    event_name: str | None,
    payload: dict[str, Any],
    competition_code: str,
    team_names: list[str],
) -> tuple[str, str]:
    info_payload = payload.get("info")
    info = info_payload if isinstance(info_payload, dict) else {}
    gender_hint = _as_str(info.get("gender")) or _as_str(payload.get("gender"))
    gender_category = classify_gender(competition_code, gender_hint)
    if gender_category != "unknown":
        return gender_category, "source" if gender_hint else "inferred"
    haystacks = [event_name or "", *team_names]
    if any(_WOMEN_KEYWORDS.search(value) for value in haystacks):
        return "women", "inferred"
    return "unknown", "unknown"


def _estimate_completeness_grade(
    innings_preview: list[HistoricalImportInningsPreview],
    innings_nodes: list[dict[str, Any]],
    format_category: str,
) -> str:
    if not innings_preview:
        return "unknown"
    has_deliveries = all(inning.deliveries > 0 for inning in innings_preview)
    has_totals = all(inning.runs is not None for inning in innings_preview)
    has_phase_data = any(isinstance(inning.get("phases"), (dict, list)) for inning in innings_nodes)
    is_multi_day = (
        format_category in {"Test", "First-class / multi-day"} or len(innings_preview) > 2
    )
    if is_multi_day:
        if has_deliveries and has_totals and len(innings_preview) >= 3:
            return "multi_day_complete"
        return "multi_day_partial"
    if has_deliveries:
        return "delivery_complete"
    if has_phase_data:
        return "phase_level"
    if has_totals:
        return "innings_totals"
    if any(
        inning.team or inning.runs is not None or inning.wickets is not None
        for inning in innings_preview
    ):
        return "metadata_only"
    return "unknown"


def _build_team_diagnostics(
    team_names: list[str],
    competition_code: str,
) -> dict[str, object]:
    alias_groups: dict[str, dict[str, object]] = {}
    unknown_team_names: list[str] = []
    for team_name in team_names:
        canonical_name, alias_key = canonicalize_team_name(team_name)
        normalized_key = alias_key or team_name.casefold()
        group = alias_groups.setdefault(
            normalized_key,
            {
                "canonical_name": canonical_name or team_name,
                "alias_key": normalized_key,
                "raw_aliases": [],
                "confidence": "high" if is_known_team_alias(team_name) else "low",
            },
        )
        group["raw_aliases"].append(team_name)
        if competition_code in {"CPL_MEN", "WCPL"} and not is_known_team_alias(team_name):
            unknown_team_names.append(team_name)

    canonical_matches = [
        {
            **group,
            "raw_aliases": sorted(set(group["raw_aliases"])),
        }
        for group in alias_groups.values()
    ]
    possible_duplicate_aliases = [
        group for group in canonical_matches if len(group["raw_aliases"]) > 1
    ]
    return {
        "canonical_matches": canonical_matches,
        "unknown_team_names": sorted(set(unknown_team_names)),
        "possible_duplicate_team_aliases": possible_duplicate_aliases,
    }


def _build_player_diagnostics(
    payload: dict[str, Any],
    team_names: list[str],
    player_names: list[str],
    registry_people_map: dict[str, str],
    gender_category: str,
) -> dict[str, object]:
    team_players = _collect_team_players(payload, team_names)
    player_to_teams: dict[str, set[str]] = {}
    for team_name, players in team_players.items():
        for player_name in players:
            player_to_teams.setdefault(player_name, set()).add(team_name)

    missing_player_ids = [
        player_name for player_name in player_names if player_name not in registry_people_map
    ]
    cross_team_conflicts = [
        {"player_name": name, "teams": sorted(teams)}
        for name, teams in player_to_teams.items()
        if len(teams) > 1
    ]
    signature_map: dict[tuple[str, str], list[str]] = {}
    for player_name in player_names:
        signature = _name_signature(player_name)
        if signature is not None:
            signature_map.setdefault(signature, []).append(player_name)
    initial_variants = [
        {"signature": f"{surname}:{initial}", "variants": sorted(set(names))}
        for (surname, initial), names in signature_map.items()
        if len(set(names)) > 1
    ]
    return {
        "mapping_status": "registry_ids_present" if registry_people_map else "source_names_only",
        "missing_player_ids": missing_player_ids,
        "unknown_player_records": missing_player_ids,
        "duplicate_player_candidates": initial_variants,
        "cross_team_name_conflicts": cross_team_conflicts,
        "gender_category": gender_category,
    }


def _build_venue_diagnostics(venue_name: str | None) -> dict[str, object]:
    canonical_name, alias_key = canonicalize_venue_name(venue_name)
    is_known = is_known_venue_alias(venue_name)
    unknown_venues = [venue_name] if venue_name and not is_known else []
    return {
        "raw_venue_names": [venue_name] if venue_name else [],
        "canonical_venue_name": canonical_name,
        "alias_key": alias_key,
        "unknown_venues": unknown_venues,
        "possible_duplicate_venues": (
            [
                {
                    "canonical_name": canonical_name,
                    "raw_alias": venue_name,
                    "alias_key": alias_key,
                }
            ]
            if venue_name and canonical_name and canonical_name != venue_name
            else []
        ),
        "missing_venue_data": venue_name is None,
    }


def _build_multi_day_diagnostics(
    metadata_preview: HistoricalImportMetadataPreview,
    innings_preview: list[HistoricalImportInningsPreview],
    innings_nodes: list[dict[str, Any]],
    format_category: str,
) -> dict[str, object]:
    innings_order = [inning.team for inning in innings_preview]
    repeated_team_sequence = any(
        innings_order[idx] and innings_order[idx] == innings_order[idx - 1]
        for idx in range(1, len(innings_order))
    )
    source_dates = metadata_preview.source_dates
    outcome_text = (metadata_preview.result or "").lower()
    if "draw" in outcome_text:
        outcome = "draw"
    elif "tie" in outcome_text:
        outcome = "tie"
    elif "no result" in outcome_text or "abandoned" in outcome_text:
        outcome = "no_result"
    else:
        outcome = "result_declared" if metadata_preview.result else "unknown"

    day_session_available = False
    for innings in innings_nodes:
        if _as_str(innings.get("day")) or _as_str(innings.get("session")):
            day_session_available = True
            break
        for delivery in _extract_deliveries_from_overs(innings.get("overs")):
            if _as_str(delivery.get("day")) or _as_str(delivery.get("session")):
                day_session_available = True
                break
        if day_session_available:
            break

    missing_totals = [
        inning.inning_no
        for inning in innings_preview
        if inning.runs is None or inning.wickets is None
    ]
    incomplete_scorecards = [
        inning.inning_no for inning in innings_preview if inning.deliveries == 0
    ]
    is_multi_day = (
        format_category in {"Test", "First-class / multi-day"} or len(innings_preview) > 2
    )
    return {
        "is_multi_day": is_multi_day,
        "innings_count": len(innings_preview),
        "innings_order": innings_order,
        "follow_on_or_unusual_order_detected": repeated_team_sequence,
        "date_range": {
            "start": source_dates[0] if source_dates else metadata_preview.date,
            "end": source_dates[-1] if source_dates else metadata_preview.date,
            "day_count": len(source_dates) if source_dates else (1 if metadata_preview.date else 0),
        },
        "outcome_type": outcome,
        "day_session_metadata_available": day_session_available,
        "missing_innings_totals": missing_totals,
        "incomplete_scorecards": incomplete_scorecards,
    }


def _classify_competition_type(
    event_name: str | None,
    teams: list[str],
) -> tuple[str, str]:
    if event_name:
        lowered = event_name.lower()
        if any(token in lowered for token in ("premier league", "ipl", "cpl", "sa20", "hundred")):
            return "franchise", "inferred"
        if any(token in lowered for token in ("academy",)):
            return "academy", "inferred"
        if any(token in lowered for token in ("school", "u-19 school", "schools")):
            return "school", "inferred"
        if any(token in lowered for token in ("club", "county", "domestic", "ranji", "super50")):
            return "domestic", "inferred"
        if any(
            token in lowered for token in ("world cup", "icc", "international", "test championship")
        ):
            return "international", "inferred"

    normalized_teams = {team.strip().lower() for team in teams if team.strip()}
    if normalized_teams and normalized_teams.issubset(_INTERNATIONAL_TEAM_HINTS):
        return "international", "inferred"

    return "unknown", "unknown"


def _classify_schema(
    detected_format: str, competition_type: str, source_schema_version: str | None = None
) -> HistoricalImportSchemaClassification:
    if detected_format == "cricksy_fixture":
        category = "cricksy_internal_json"
    elif detected_format == "cricsheet_json":
        if competition_type == "franchise":
            category = "franchise_tournament_json"
        elif competition_type == "international":
            category = "international_match_json"
        elif competition_type in {"domestic", "club"}:
            category = "domestic_club_match_json"
        elif competition_type in {"school", "academy"}:
            category = "school_academy_match_json"
        else:
            category = "cricsheet_style_json"
    else:
        category = "unknown_unsupported_json"

    return HistoricalImportSchemaClassification(
        source_schema_category=category,
        source_schema=detected_format,
        source_schema_version=source_schema_version,
        adapter_id=ADAPTER_ID,
        adapter_version=ADAPTER_VERSION,
    )


def _build_validation_diagnostics(
    *,
    parsed: dict[str, Any],
    metadata_preview: HistoricalImportMetadataPreview,
    team_names: list[str],
    innings_preview: list[HistoricalImportInningsPreview],
    innings_nodes: list[dict[str, Any]],
    detected_format: str,
    source_filename: str | None = None,
) -> dict[str, object]:
    registry_people_map = _extract_registry_people_map(parsed)
    competition_type, competition_type_status = _classify_competition_type(
        metadata_preview.event_name, team_names
    )
    format_category, format_status = _classify_match_format(
        metadata_preview.match_type, len(innings_preview), metadata_preview.source_dates
    )
    age_category, age_status = _classify_age_category_hint(metadata_preview.event_name, team_names)
    competition_code, competition_code_status = _classify_competition_code(
        metadata_preview.event_name, team_names, format_category, age_category
    )
    gender_category, gender_status = _classify_gender_category(
        metadata_preview.event_name, parsed, competition_code, team_names
    )
    completeness_grade = _estimate_completeness_grade(
        innings_preview, innings_nodes, format_category
    )
    analysis_readiness = (
        "limited"
        if completeness_grade in {"multi_day_partial", "multi_day_complete"}
        else ("full" if completeness_grade == "delivery_complete" else "limited")
    )
    team_diagnostics = _build_team_diagnostics(team_names, competition_code)
    player_names = sorted(
        _extract_players_from_teams(parsed)
        .union(_extract_registry_people_map(parsed).keys())
        .union(
            {
                player
                for innings in innings_nodes
                for delivery in _extract_deliveries_from_overs(innings.get("overs"))
                for player in (
                    _as_str(delivery.get("batter")),
                    _as_str(delivery.get("batsman")),
                    _as_str(delivery.get("striker")),
                    _as_str(delivery.get("non_striker")),
                    _as_str(delivery.get("bowler")),
                )
                if player
            }
        )
    )
    player_diagnostics = _build_player_diagnostics(
        parsed, team_names, player_names, registry_people_map, gender_category
    )
    venue_diagnostics = _build_venue_diagnostics(metadata_preview.venue)
    multi_day_diagnostics = _build_multi_day_diagnostics(
        metadata_preview, innings_preview, innings_nodes, format_category
    )
    return {
        "scan_summary": {
            "files_scanned": 1,
            "files_recognized": 1 if detected_format != "unknown" else 0,
            "files_skipped": 0,
            "expected_matches": 1 if detected_format != "unknown" else 0,
            "parse_failures": 0,
            "source_filename": source_filename,
        },
        "classification": {
            "competition_code": competition_code,
            "competition_code_status": competition_code_status,
            "competition_type": competition_type,
            "competition_type_status": competition_type_status,
            "format_category": format_category,
            "format_status": format_status,
            "gender_category": gender_category,
            "gender_status": gender_status,
            "age_category": age_category,
            "age_status": age_status,
            "completeness_grade": completeness_grade,
            "analysis_readiness": analysis_readiness,
        },
        "multi_day": multi_day_diagnostics,
        "team_alias_check": team_diagnostics,
        "player_identity_risks": player_diagnostics,
        "venue_check": venue_diagnostics,
        "batch_traceability": {
            "batch_id": None,
            "source_path": source_filename,
            "source_file_name": source_filename,
            "import_timestamp": None,
            "traceable_on_apply": True,
            "records_created_updated_skipped_available_on_apply": True,
            "validation_warnings_available": True,
        },
    }


def _build_canonical_preview(
    parsed: dict[str, Any],
    metadata_preview: HistoricalImportMetadataPreview,
    team_names: list[str],
    innings_preview: list[HistoricalImportInningsPreview],
    detected_format: str,
    source_hash: str,
    warnings: list[HistoricalImportIssue],
    errors: list[HistoricalImportIssue],
    diagnostics: dict[str, object],
) -> tuple[HistoricalImportCanonicalPreview, HistoricalImportCompetitionContext]:
    info_payload = parsed.get("info")
    info = info_payload if isinstance(info_payload, dict) else {}
    meta_payload = parsed.get("meta")
    meta = meta_payload if isinstance(meta_payload, dict) else {}
    source_schema_version = _as_str(meta.get("data_version"))
    event_raw = info.get("event")
    event_payload = event_raw if isinstance(event_raw, dict) else {}
    event_name = metadata_preview.event_name

    classification = diagnostics.get("classification", {})
    competition_type = str(classification.get("competition_type") or "unknown")
    competition_type_status = str(classification.get("competition_type_status") or "unknown")
    competition_context = HistoricalImportCompetitionContext(
        competition_code=str(classification.get("competition_code") or "UNKNOWN"),
        competition_type=competition_type,  # type: ignore[arg-type]
        competition_name=event_name,
        competition_stage=_as_str(event_payload.get("stage")),
        season=metadata_preview.season,
        match_format=(metadata_preview.match_type or "unknown").lower(),
        format_category=str(classification.get("format_category") or "unknown"),
        gender_category=str(classification.get("gender_category") or "unknown"),
        age_category=str(classification.get("age_category") or "unknown"),
        analysis_readiness=str(classification.get("analysis_readiness") or "unknown"),
        tournament_name=event_name,
        tournament_round=_stringify_scalar(event_payload.get("match_number"))
        or _as_str(event_payload.get("group"))
        or _as_str(event_payload.get("round")),
        value_status={
            "competition_type": competition_type_status,  # type: ignore[dict-item]
            "competition_name": "source" if event_name else "missing",
            "season": "source" if metadata_preview.season else "missing",
            "match_format": "source" if metadata_preview.match_type else "unknown",
            "format_category": str(classification.get("format_status") or "unknown"),  # type: ignore[dict-item]
            "gender_category": str(classification.get("gender_status") or "unknown"),  # type: ignore[dict-item]
            "age_category": str(classification.get("age_status") or "unknown"),  # type: ignore[dict-item]
        },
    )

    venue_raw = _as_str(parsed.get("venue")) or _as_str(info.get("venue"))
    venue_check = diagnostics.get("venue_check", {})
    venue_context = HistoricalImportVenueContext(
        venue_name=_as_str(venue_check.get("canonical_venue_name")) or venue_raw,
        source_venue_raw=venue_raw,
        ground_code=_as_str(venue_check.get("alias_key")),
        venue_resolution_status=(
            "resolved"
            if venue_raw and not venue_check.get("unknown_venues")
            else ("unresolved" if venue_raw else "unknown")
        ),
    )
    if venue_raw is None:
        warnings.append(
            HistoricalImportIssue(
                code="VENUE_UNKNOWN",
                message="Venue metadata is missing; venue context remains unknown.",
                severity="warning",
                path="venue_context",
            )
        )

    registry_people_map = _extract_registry_people_map(parsed)
    roster_snapshot = _extract_roster_snapshot(parsed, team_names, registry_people_map)
    player_risks = diagnostics.get("player_identity_risks", {})
    if not any(team.playing_xi for team in roster_snapshot):
        warnings.append(
            HistoricalImportIssue(
                code="ROSTER_SNAPSHOT_MISSING",
                message="Roster snapshot was not present in source payload.",
                severity="warning",
                path="squad_roster_snapshot",
            )
        )
    if competition_type == "unknown":
        warnings.append(
            HistoricalImportIssue(
                code="COMPETITION_TYPE_UNKNOWN",
                message="Competition type could not be deterministically resolved from source.",
                severity="warning",
                path="competition_context.competition_type",
            )
        )

    schema_classification = _classify_schema(
        detected_format, competition_type, source_schema_version=source_schema_version
    )
    canonical = HistoricalImportCanonicalPreview(
        match_metadata={
            "match_type": metadata_preview.match_type,
            "match_date": metadata_preview.date,
            "teams": team_names,
        },
        competition_context=competition_context,
        tournament_season_context={
            "season": metadata_preview.season,
            "tournament_name": event_name,
            "tournament_round": competition_context.tournament_round,
        },
        venue_context=venue_context,
        team_context={"teams": team_names},
        squad_roster_snapshot=roster_snapshot,
        player_identity_mapping={
            "mapping_status": str(player_risks.get("mapping_status") or "source_names_only"),
            "unresolved_entries": player_risks.get("unknown_player_records", []),
            "deterministic_blocking": False,
        },
        innings_summaries=[inning.model_dump(mode="python") for inning in innings_preview],
        delivery_events={"count": sum(inn.deliveries for inn in innings_preview)},
        result_metadata={"result": metadata_preview.result},
        source_provenance={
            "source_schema": schema_classification.source_schema,
            "source_schema_version": schema_classification.source_schema_version,
            "adapter_id": schema_classification.adapter_id,
            "adapter_version": schema_classification.adapter_version,
            "source_hash_sha256": source_hash,
            "raw_competition_name": event_name,
            "raw_match_type": metadata_preview.match_type,
            "raw_dates": metadata_preview.source_dates,
            "source_venue_raw": venue_raw,
        },
        validation_report={
            "warning_count": len(warnings),
            "error_count": len(errors),
            "issues": [issue.model_dump(mode="python") for issue in [*warnings, *errors]],
            **diagnostics,
        },
    )
    return canonical, competition_context


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


def _derive_result_summary(parsed: dict[str, Any], info_payload: dict[str, Any]) -> str | None:
    result_value = parsed.get("result")
    if isinstance(result_value, dict):
        summary = _as_str(result_value.get("summary"))
        if summary:
            return summary
    else:
        summary = _as_str(result_value)
        if summary:
            return summary

    outcome_value = info_payload.get("outcome")
    if not isinstance(outcome_value, dict):
        return None
    outcome: dict[str, Any] = outcome_value

    winner = _as_str(outcome.get("winner"))
    margin = outcome.get("by")
    if winner:
        if isinstance(margin, dict):
            innings = _optional_int(margin.get("innings"))
            runs = _optional_int(margin.get("runs"))
            wickets = _optional_int(margin.get("wickets"))
            if innings and runs:
                return f"{winner} won by {innings} innings and {runs} runs"
            if runs:
                return f"{winner} won by {runs} runs"
            if wickets:
                return f"{winner} won by {wickets} wickets"
        return f"{winner} won"

    return _as_str(outcome.get("result"))


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
                legal_balls=legal_balls_count,
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
        source_hash = _hash_payload(raw_payload)
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
            diagnostics={
                "scan_summary": {
                    "files_scanned": 1,
                    "files_recognized": 0,
                    "files_skipped": 1,
                    "expected_matches": 0,
                    "parse_failures": 1,
                }
            },
            duplicate_detection=HistoricalImportDuplicatePreview(
                source_hash_sha256=source_hash,
                probable_duplicate="unknown",
                tracking_available=False,
                message=DUPLICATE_TRACKING_MESSAGE,
            ),
            schema_classification=_classify_schema("unknown", "unknown"),
        )
        return 400, response

    try:
        parsed = json.loads(decoded)
    except json.JSONDecodeError:
        source_hash = _hash_payload(raw_payload)
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
            diagnostics={
                "scan_summary": {
                    "files_scanned": 1,
                    "files_recognized": 0,
                    "files_skipped": 1,
                    "expected_matches": 0,
                    "parse_failures": 1,
                }
            },
            duplicate_detection=HistoricalImportDuplicatePreview(
                source_hash_sha256=source_hash,
                probable_duplicate="unknown",
                tracking_available=False,
                message=DUPLICATE_TRACKING_MESSAGE,
            ),
            schema_classification=_classify_schema("unknown", "unknown"),
        )
        return 400, response

    if not isinstance(parsed, dict):
        source_hash = _hash_payload(raw_payload)
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
            diagnostics={
                "scan_summary": {
                    "files_scanned": 1,
                    "files_recognized": 0,
                    "files_skipped": 1,
                    "expected_matches": 0,
                    "parse_failures": 1,
                }
            },
            duplicate_detection=HistoricalImportDuplicatePreview(
                source_hash_sha256=source_hash,
                probable_duplicate="unknown",
                tracking_available=False,
                message=DUPLICATE_TRACKING_MESSAGE,
            ),
            schema_classification=_classify_schema("unknown", "unknown"),
        )
        return 400, response

    innings_nodes = _extract_innings_nodes(parsed.get("innings"))
    detected_format = _detect_format(parsed, innings_nodes)
    team_names = _extract_team_names(parsed)
    players_from_teams = _extract_players_from_teams(parsed)
    players_from_registry = set(_extract_registry_people_map(parsed).keys())

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

    if len(team_names) < 2:
        errors.append(
            HistoricalImportIssue(
                code="MISSING_TEAMS",
                message="At least two teams are required in historical match metadata.",
                severity="error",
                path="teams",
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
    event_value = info_payload.get("event")
    event_payload: dict[str, Any] = event_value if isinstance(event_value, dict) else {}
    source_dates = [
        date_value.strip()
        for date_value in info_payload.get("dates", [])
        if isinstance(date_value, str) and date_value.strip()
    ]
    result_summary = _derive_result_summary(parsed, info_payload)

    metadata_preview = HistoricalImportMetadataPreview(
        match_type=_as_str(parsed.get("matchType")) or _as_str(info_payload.get("match_type")),
        venue=_as_str(parsed.get("venue")) or _as_str(info_payload.get("venue")),
        date=_as_str(parsed.get("date")) or _first_str(info_payload.get("dates")),
        result=result_summary,
        event_name=_as_str(event_payload.get("name")),
        season=_as_str(info_payload.get("season")) or _as_str(parsed.get("season")),
        match_number=_optional_int(event_payload.get("match_number"))
        or _optional_int(parsed.get("match_number")),
        source_dates=source_dates,
    )

    player_names = sorted(
        players_from_teams.union(players_from_innings).union(players_from_registry)
    )
    diagnostics = _build_validation_diagnostics(
        parsed=parsed,
        metadata_preview=metadata_preview,
        team_names=team_names,
        innings_preview=innings_preview,
        innings_nodes=innings_nodes,
        detected_format=detected_format,
    )
    classification = diagnostics.get("classification", {})
    team_alias_check = diagnostics.get("team_alias_check", {})
    venue_check = diagnostics.get("venue_check", {})
    multi_day = diagnostics.get("multi_day", {})

    if not metadata_preview.date:
        warnings.append(
            HistoricalImportIssue(
                code="MISSING_DATE",
                message="Match date is missing from the historical payload.",
                severity="warning",
                path="metadata_preview.date",
            )
        )
    if classification.get("competition_code") == "UNKNOWN":
        warnings.append(
            HistoricalImportIssue(
                code="UNKNOWN_COMPETITION",
                message="Competition could not be safely classified from the source metadata.",
                severity="warning",
                path="diagnostics.classification.competition_code",
            )
        )
    if classification.get("format_category") == "unknown":
        warnings.append(
            HistoricalImportIssue(
                code="UNKNOWN_FORMAT",
                message="Match format could not be classified conservatively.",
                severity="warning",
                path="diagnostics.classification.format_category",
            )
        )
    if classification.get("gender_category") == "unknown":
        warnings.append(
            HistoricalImportIssue(
                code="UNKNOWN_GENDER_CATEGORY",
                message="Gender/category could not be safely inferred from source metadata.",
                severity="warning",
                path="diagnostics.classification.gender_category",
            )
        )
    unknown_team_names = team_alias_check.get("unknown_team_names", [])
    if isinstance(unknown_team_names, list) and unknown_team_names:
        warnings.append(
            HistoricalImportIssue(
                code="UNKNOWN_TEAM_ALIASES",
                message="One or more team names were not resolved to a known canonical alias set.",
                severity="warning",
                path="diagnostics.team_alias_check.unknown_team_names",
            )
        )
    unknown_venues = venue_check.get("unknown_venues", [])
    if isinstance(unknown_venues, list) and unknown_venues:
        warnings.append(
            HistoricalImportIssue(
                code="UNKNOWN_VENUE_ALIAS",
                message="Venue name was preserved but not resolved to a known canonical venue alias.",
                severity="warning",
                path="diagnostics.venue_check.unknown_venues",
            )
        )
    missing_innings_totals = multi_day.get("missing_innings_totals", [])
    if isinstance(missing_innings_totals, list) and missing_innings_totals:
        warnings.append(
            HistoricalImportIssue(
                code="MISSING_INNINGS_TOTALS",
                message="One or more innings totals are incomplete or missing.",
                severity="warning",
                path="diagnostics.multi_day.missing_innings_totals",
            )
        )
    incomplete_scorecards = multi_day.get("incomplete_scorecards", [])
    if isinstance(incomplete_scorecards, list) and incomplete_scorecards:
        warnings.append(
            HistoricalImportIssue(
                code="INCOMPLETE_SCORECARD",
                message="One or more innings scorecards are incomplete.",
                severity="warning",
                path="diagnostics.multi_day.incomplete_scorecards",
            )
        )
    if multi_day.get("is_multi_day") and classification.get("analysis_readiness") == "limited":
        warnings.append(
            HistoricalImportIssue(
                code="LIMITED_MULTI_DAY_ANALYSIS_READY",
                message="Multi-day/Test match detected; import is safe but downstream analysis remains limited.",
                severity="warning",
                path="diagnostics.classification.analysis_readiness",
            )
        )

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
                metadata_preview.event_name,
                metadata_preview.season,
                metadata_preview.match_number,
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
    canonical_preview, competition_context = _build_canonical_preview(
        parsed,
        metadata_preview,
        team_names,
        innings_preview,
        detected_format,
        normalized_hash,
        warnings,
        errors,
        diagnostics,
    )
    meta_payload = parsed.get("meta")
    meta = meta_payload if isinstance(meta_payload, dict) else {}
    source_schema_version = _as_str(meta.get("data_version"))
    schema_classification = _classify_schema(
        detected_format,
        canonical_preview.competition_context.competition_type,
        source_schema_version=source_schema_version,
    )
    canonical_preview_out = canonical_preview if status == "valid" else None
    semantic_key = _derive_semantic_key(parsed, metadata_preview, team_names, competition_context)

    response = HistoricalImportDryRunResponse(
        status=status,
        detected_format=detected_format,
        top_level_keys=sorted(parsed.keys()),
        detected_sections=detected_sections,
        metadata_preview=metadata_preview,
        schema_classification=schema_classification,
        canonical_preview=canonical_preview_out,
        teams_preview=team_names,
        innings_count=len(innings_nodes),
        delivery_count=total_deliveries,
        player_names_found=player_names,
        innings_preview=innings_preview,
        warnings=warnings,
        errors=errors,
        diagnostics=canonical_preview.validation_report,
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
