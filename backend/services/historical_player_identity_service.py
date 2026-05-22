from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from typing import Any, TypedDict

from backend.sql_app.models import (
    HistoricalCompetitionRosterEntry,
    HistoricalCompetitionRosterStatus,
    HistoricalPlayerResolutionQueue,
    HistoricalPlayerResolutionState,
    HistoricalSourcePlayerAlias,
    HistoricalSourcePlayerRegistry,
    Player,
)
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

UTC = dt.UTC
_NAME_STRIP_RE = re.compile(r"[^a-z0-9\s]")
_MULTISPACE_RE = re.compile(r"\s+")


@dataclass
class _ResolvedIdentity:
    state: HistoricalPlayerResolutionState
    canonical_player_id: int | None
    confidence_score: float | None
    mapping_method: str | None
    queue_reason: str | None = None


class _RegistrationSummary(TypedDict):
    registered_count: int
    auto_resolved_count: int
    manually_resolved_count: int
    unresolved_count: int
    ambiguous_count: int
    blocked_count: int
    queue_pending_count: int
    source_player_ids: list[str]
    deterministic_methods_used: list[str]
    metadata_fields_recorded: int
    career_profiles_updated: int
    canonical_safe_fills: int
    metadata_conflicts: int
    roster_entries_upserted: int
    roster_conflicts: int
    resolved_count: int
    mapping_records_created: int
    mapping_records_updated: int
    missing_source_id_count: int
    unresolved_reasons: list[dict[str, Any]]
    ambiguous_reasons: list[dict[str, Any]]


def normalize_source_player_name(name: str) -> str:
    value = (name or "").strip().lower()
    if "," in value:
        parts = [part.strip() for part in value.split(",") if part.strip()]
        if len(parts) == 2:
            value = f"{parts[1]} {parts[0]}"
    value = _NAME_STRIP_RE.sub(" ", value)
    value = _MULTISPACE_RE.sub(" ", value).strip()
    return value


def _competition_key(context: dict[str, Any]) -> tuple[str, str]:
    competition_name = str(context.get("competition_name") or "").strip().lower()
    season = str(context.get("season") or "").strip().lower()
    return competition_name, season


def _initials(tokens: list[str]) -> str:
    return "".join(token[0] for token in tokens if token)


def _deterministic_alias_candidates(source_normalized_name: str, players: list[Player]) -> set[int]:
    source_tokens = [token for token in source_normalized_name.split(" ") if token]
    if len(source_tokens) < 2:
        return set()
    source_last = source_tokens[-1]
    source_first_tokens = source_tokens[:-1]
    source_initials = _initials(source_first_tokens)

    candidates: set[int] = set()
    for player in players:
        canonical_tokens = [
            token for token in normalize_source_player_name(player.name).split(" ") if token
        ]
        if len(canonical_tokens) < 2:
            continue
        canonical_last = canonical_tokens[-1]
        if canonical_last != source_last:
            continue
        canonical_first_tokens = canonical_tokens[:-1]
        canonical_initials = _initials(canonical_first_tokens)
        same_first_name = (
            source_first_tokens
            and canonical_first_tokens
            and (source_first_tokens[0] == canonical_first_tokens[0])
        )
        initials_match = bool(source_initials) and (
            canonical_initials == source_initials or canonical_initials.startswith(source_initials)
        )
        if same_first_name or initials_match:
            candidates.add(player.id)
    return candidates


def _extract_roster_entries(
    roster_snapshot: list[dict[str, Any]],
    player_names: list[str],
) -> list[dict[str, Any]]:
    entries_by_key: dict[tuple[str | None, str], dict[str, Any]] = {}
    status_order = {
        "named_squad": 0,
        "playing_xi": 1,
        "substitute": 2,
        "unresolved": 3,
        "unavailable_unknown": 4,
    }

    def _parse_player_entry(player_entry: Any) -> tuple[str | None, dict[str, Any], str]:
        if isinstance(player_entry, str):
            return player_entry.strip() or None, {}, "unknown"
        if isinstance(player_entry, dict):
            player_name = (
                str(
                    player_entry.get("name")
                    or player_entry.get("player_name")
                    or player_entry.get("full_name")
                    or ""
                ).strip()
                or None
            )
            return (
                player_name,
                {
                    "batting_style": player_entry.get("batting_style"),
                    "bowling_style": player_entry.get("bowling_style"),
                    "role": player_entry.get("role") or player_entry.get("player_role"),
                    "batting_innings_count": player_entry.get("batting_innings_count"),
                    "bowling_participation_count": player_entry.get("bowling_participation_count"),
                    "source_player_id": player_entry.get("source_player_id"),
                },
                "source",
            )
        return None, {}, "unknown"

    def _add_entry(
        *,
        player_name: str,
        team_name: str | None,
        roster_status: str,
        metadata: dict[str, Any],
        metadata_source_status: str,
    ) -> None:
        key = (team_name, player_name.casefold())
        existing = entries_by_key.get(key)
        if existing is None:
            existing = {
                "name": player_name,
                "team_name": team_name,
                "metadata": metadata,
                "metadata_source_status": metadata_source_status,
                "roster_statuses": [],
            }
            entries_by_key[key] = existing
        elif (
            existing.get("metadata_source_status") != "source"
            and metadata_source_status == "source"
        ):
            existing["metadata"] = metadata
            existing["metadata_source_status"] = "source"

        roster_statuses = list(existing.get("roster_statuses") or [])
        if roster_status not in roster_statuses:
            roster_statuses.append(roster_status)
            roster_statuses.sort(key=lambda status: status_order.get(status, 999))
            existing["roster_statuses"] = roster_statuses

    for team_entry in roster_snapshot:
        if not isinstance(team_entry, dict):
            continue
        team_name = str(team_entry.get("team_name") or "").strip()
        status_lists: list[tuple[str, Any]] = [
            ("named_squad", team_entry.get("named_squad")),
            ("playing_xi", team_entry.get("playing_xi")),
            ("substitute", team_entry.get("substitutes")),
            ("unresolved", team_entry.get("unresolved_entries")),
        ]
        for status, players in status_lists:
            if not isinstance(players, list):
                continue
            for player_entry in players:
                player_name, entry_metadata, source_status = _parse_player_entry(player_entry)
                if not player_name:
                    continue
                _add_entry(
                    player_name=player_name,
                    team_name=team_name or None,
                    roster_status=status,
                    metadata=entry_metadata,
                    metadata_source_status=source_status,
                )

    for player_name in player_names:
        if not isinstance(player_name, str) or not player_name.strip():
            continue
        normalized_key = player_name.strip().casefold()
        if any(existing_key[1] == normalized_key for existing_key in entries_by_key):
            continue
        _add_entry(
            player_name=player_name.strip(),
            team_name=None,
            roster_status="unavailable_unknown",
            metadata={},
            metadata_source_status="unknown",
        )
    return list(entries_by_key.values())


async def _resolve_identity(
    db: AsyncSession,
    *,
    normalized_name: str,
    source_schema: str,
    source_system: str,
    competition_context: dict[str, Any],
    team_name: str | None,
) -> _ResolvedIdentity:
    if not normalized_name:
        return _ResolvedIdentity(
            state=HistoricalPlayerResolutionState.blocked,
            canonical_player_id=None,
            confidence_score=None,
            mapping_method=None,
            queue_reason="empty_normalized_name",
        )

    exact_result = await db.execute(select(Player).where(Player.name.is_not(None)))
    all_players = exact_result.scalars().all()
    exact_candidates = [
        player
        for player in all_players
        if normalize_source_player_name(player.name) == normalized_name
    ]
    if len(exact_candidates) == 1:
        return _ResolvedIdentity(
            state=HistoricalPlayerResolutionState.auto_resolved,
            canonical_player_id=exact_candidates[0].id,
            confidence_score=1.0,
            mapping_method="normalized_exact_match",
        )
    if len(exact_candidates) > 1:
        return _ResolvedIdentity(
            state=HistoricalPlayerResolutionState.ambiguous,
            canonical_player_id=None,
            confidence_score=None,
            mapping_method=None,
            queue_reason="multiple_exact_candidates",
        )

    deterministic_alias_candidates = _deterministic_alias_candidates(normalized_name, all_players)
    if len(deterministic_alias_candidates) == 1:
        return _ResolvedIdentity(
            state=HistoricalPlayerResolutionState.auto_resolved,
            canonical_player_id=next(iter(deterministic_alias_candidates)),
            confidence_score=0.97,
            mapping_method="alias_match",
        )
    if len(deterministic_alias_candidates) > 1:
        return _ResolvedIdentity(
            state=HistoricalPlayerResolutionState.ambiguous,
            canonical_player_id=None,
            confidence_score=None,
            mapping_method=None,
            queue_reason="multiple_alias_candidates",
        )

    alias_stmt = (
        select(HistoricalSourcePlayerAlias, HistoricalSourcePlayerRegistry)
        .join(
            HistoricalSourcePlayerRegistry,
            HistoricalSourcePlayerRegistry.source_player_id
            == HistoricalSourcePlayerAlias.source_player_id,
        )
        .where(
            HistoricalSourcePlayerAlias.normalized_alias == normalized_name,
            HistoricalSourcePlayerAlias.source_schema == source_schema,
            HistoricalSourcePlayerAlias.source_system == source_system,
            HistoricalSourcePlayerRegistry.canonical_player_id.is_not(None),
        )
    )
    alias_rows = (await db.execute(alias_stmt)).all()
    alias_candidates = {
        registry.canonical_player_id for _, registry in alias_rows if registry.canonical_player_id
    }
    if len(alias_candidates) == 1:
        canonical_player_id = next(iter(alias_candidates))
        return _ResolvedIdentity(
            state=HistoricalPlayerResolutionState.auto_resolved,
            canonical_player_id=canonical_player_id,
            confidence_score=0.99,
            mapping_method="alias_match",
        )
    if len(alias_candidates) > 1:
        return _ResolvedIdentity(
            state=HistoricalPlayerResolutionState.ambiguous,
            canonical_player_id=None,
            confidence_score=None,
            mapping_method=None,
            queue_reason="multiple_alias_candidates",
        )

    comp_name, season = _competition_key(competition_context)
    same_name_stmt = select(HistoricalSourcePlayerRegistry).where(
        HistoricalSourcePlayerRegistry.normalized_name == normalized_name,
        HistoricalSourcePlayerRegistry.source_schema == source_schema,
        HistoricalSourcePlayerRegistry.source_system == source_system,
        HistoricalSourcePlayerRegistry.canonical_player_id.is_not(None),
    )
    prior_registry = (await db.execute(same_name_stmt)).scalars().all()
    comp_candidates: set[int] = set()
    team_candidates: set[int] = set()
    for row in prior_registry:
        if not row.canonical_player_id:
            continue
        for competition_ref in row.competition_references or []:
            if not isinstance(competition_ref, dict):
                continue
            prev_comp = str(competition_ref.get("competition_name") or "").strip().lower()
            prev_season = str(competition_ref.get("season") or "").strip().lower()
            if prev_comp == comp_name and prev_season == season:
                comp_candidates.add(row.canonical_player_id)
            prev_team = str(competition_ref.get("team_name") or "").strip().lower()
            if team_name and prev_team and prev_team == team_name.strip().lower():
                team_candidates.add(row.canonical_player_id)
    if len(comp_candidates) == 1:
        return _ResolvedIdentity(
            state=HistoricalPlayerResolutionState.auto_resolved,
            canonical_player_id=next(iter(comp_candidates)),
            confidence_score=0.96,
            mapping_method="competition_season_roster_overlap",
        )
    if len(team_candidates) == 1:
        return _ResolvedIdentity(
            state=HistoricalPlayerResolutionState.auto_resolved,
            canonical_player_id=next(iter(team_candidates)),
            confidence_score=0.93,
            mapping_method="team_role_overlap",
        )
    if len(comp_candidates) > 1 or len(team_candidates) > 1:
        return _ResolvedIdentity(
            state=HistoricalPlayerResolutionState.ambiguous,
            canonical_player_id=None,
            confidence_score=None,
            mapping_method=None,
            queue_reason="multiple_overlap_candidates",
        )

    return _ResolvedIdentity(
        state=HistoricalPlayerResolutionState.unresolved,
        canonical_player_id=None,
        confidence_score=None,
        mapping_method=None,
        queue_reason="deterministic_rules_no_match",
    )


def _append_unique(sequence: list[Any], item: Any, key: str | None = None) -> list[Any]:
    if key is None:
        if item not in sequence:
            sequence.append(item)
        return sequence
    keys = {str(existing.get(key)) for existing in sequence if isinstance(existing, dict)}
    if isinstance(item, dict) and str(item.get(key)) not in keys:
        sequence.append(item)
    return sequence


def _diagnostic_reason(
    *,
    resolution_state: HistoricalPlayerResolutionState,
    queue_reason: str | None,
    explicit_source_player_id: str | None,
) -> str:
    if resolution_state == HistoricalPlayerResolutionState.ambiguous:
        return "ambiguous_match"
    if resolution_state == HistoricalPlayerResolutionState.blocked:
        return queue_reason or "blocked"
    if not explicit_source_player_id:
        return "missing_source_id"
    if queue_reason == "deterministic_rules_no_match":
        return "no_exact_match"
    if queue_reason and queue_reason.startswith("multiple_"):
        return "ambiguous_match"
    return queue_reason or "no_exact_match"


def _normalize_metadata_value(value: Any) -> str | None:
    if isinstance(value, str):
        normalized = value.strip()
        return normalized or None
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _safe_int(value: Any) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _upsert_metadata_history(
    registry: HistoricalSourcePlayerRegistry,
    *,
    field_name: str,
    value: str | None,
    source_system: str,
    source_schema: str,
    batch_id: str,
    game_id: str,
    source_status: str,
    confidence_status: str,
    now: dt.datetime,
) -> bool:
    history = list(registry.metadata_field_history or [])
    now_iso = now.isoformat()
    for row in history:
        if not isinstance(row, dict):
            continue
        if row.get("field_name") != field_name:
            continue
        if row.get("value") != value:
            continue
        row["last_seen"] = now_iso
        row["source_system"] = source_system
        row["source_schema"] = source_schema
        row["batch_id"] = batch_id
        row["game_id"] = game_id
        row["source_status"] = source_status
        row["confidence_status"] = confidence_status
        registry.metadata_field_history = history
        return False

    history.append(
        {
            "field_name": field_name,
            "value": value,
            "source_system": source_system,
            "source_schema": source_schema,
            "batch_id": batch_id,
            "game_id": game_id,
            "source_status": source_status,
            "confidence_status": confidence_status,
            "first_seen": now_iso,
            "last_seen": now_iso,
        }
    )
    registry.metadata_field_history = history
    return True


def _record_conflict_if_needed(
    registry: HistoricalSourcePlayerRegistry,
    *,
    field_name: str,
    canonical_value: str | None,
    observed_value: str | None,
    source_system: str,
    source_schema: str,
    batch_id: str,
    game_id: str,
    now: dt.datetime,
) -> bool:
    if observed_value is None or canonical_value is None:
        return False
    if canonical_value.strip().casefold() == observed_value.strip().casefold():
        return False

    conflicts = list(registry.metadata_conflicts or [])
    conflict_row = {
        "field_name": field_name,
        "canonical_value": canonical_value,
        "observed_value": observed_value,
        "source_system": source_system,
        "source_schema": source_schema,
        "batch_id": batch_id,
        "game_id": game_id,
        "review_state": "pending_review",
        "detected_at": now.isoformat(),
    }
    if conflict_row not in conflicts:
        conflicts.append(conflict_row)
    registry.metadata_conflicts = conflicts
    registry.review_required = bool(conflicts)
    return True


def _upsert_career_profile_foundation(
    registry: HistoricalSourcePlayerRegistry,
    *,
    competition_context: dict[str, Any],
    team_name: str | None,
    role_value: str | None,
    batting_innings_count: int | None,
    bowling_participation_count: int | None,
    game_id: str,
    batch_id: str,
    source_system: str,
    source_schema: str,
    match_date: str | None,
    now: dt.datetime,
) -> None:
    now_iso = now.isoformat()
    foundation = dict(registry.career_profile_foundation or {})
    competition_name = _normalize_metadata_value(competition_context.get("competition_name"))
    season = _normalize_metadata_value(competition_context.get("season"))
    timeline = list(foundation.get("match_timeline") or [])
    timeline_item = {
        "game_id": game_id,
        "batch_id": batch_id,
        "match_date": match_date,
        "competition_name": competition_name,
        "season": season,
        "team_name": team_name,
        "source_system": source_system,
        "source_schema": source_schema,
        "first_seen": now_iso,
        "last_seen": now_iso,
    }
    found_timeline = False
    for row in timeline:
        if not isinstance(row, dict):
            continue
        if row.get("game_id") != game_id:
            continue
        row["last_seen"] = now_iso
        found_timeline = True
        break
    if not found_timeline:
        timeline.append(timeline_item)
    foundation["match_timeline"] = timeline

    competitions = list(foundation.get("competitions") or [])
    if competition_name:
        existing_comp = next(
            (
                row
                for row in competitions
                if isinstance(row, dict) and row.get("competition_name") == competition_name
            ),
            None,
        )
        if existing_comp is None:
            competitions.append(
                {
                    "competition_name": competition_name,
                    "source_system": source_system,
                    "source_schema": source_schema,
                    "first_seen": now_iso,
                    "last_seen": now_iso,
                }
            )
        else:
            existing_comp["last_seen"] = now_iso
    foundation["competitions"] = competitions

    seasons = list(foundation.get("seasons") or [])
    if season:
        existing_season = next(
            (row for row in seasons if isinstance(row, dict) and row.get("season") == season),
            None,
        )
        if existing_season is None:
            seasons.append(
                {
                    "season": season,
                    "source_system": source_system,
                    "source_schema": source_schema,
                    "first_seen": now_iso,
                    "last_seen": now_iso,
                }
            )
        else:
            existing_season["last_seen"] = now_iso
    foundation["seasons"] = seasons

    teams = list(foundation.get("teams") or [])
    if team_name:
        existing_team = next(
            (
                row
                for row in teams
                if isinstance(row, dict)
                and row.get("team_name") == team_name
                and row.get("competition_name") == competition_name
                and row.get("season") == season
            ),
            None,
        )
        if existing_team is None:
            teams.append(
                {
                    "team_name": team_name,
                    "competition_name": competition_name,
                    "season": season,
                    "source_system": source_system,
                    "source_schema": source_schema,
                    "first_seen": now_iso,
                    "last_seen": now_iso,
                }
            )
        else:
            existing_team["last_seen"] = now_iso
    foundation["teams"] = teams

    role_appearances = dict(foundation.get("role_appearances") or {})
    if role_value:
        role_entry = dict(role_appearances.get(role_value) or {})
        role_entry["count"] = int(role_entry.get("count") or 0) + 1
        role_entry["source_system"] = source_system
        role_entry["source_schema"] = source_schema
        role_entry["first_seen"] = role_entry.get("first_seen") or now_iso
        role_entry["last_seen"] = now_iso
        role_appearances[role_value] = role_entry
    foundation["role_appearances"] = role_appearances

    foundation["matches_played"] = len(
        {
            row.get("game_id")
            for row in timeline
            if isinstance(row, dict) and isinstance(row.get("game_id"), str)
        }
    )
    if batting_innings_count is not None:
        foundation["batting_innings_count"] = batting_innings_count
    else:
        foundation.setdefault("batting_innings_count", None)
    if bowling_participation_count is not None:
        foundation["bowling_participation_count"] = bowling_participation_count
    else:
        foundation.setdefault("bowling_participation_count", None)
    registry.career_profile_foundation = foundation


def _append_unique_dict_by_keys(
    rows: list[dict[str, Any]],
    candidate: dict[str, Any],
    key_fields: tuple[str, ...],
) -> list[dict[str, Any]]:
    for row in rows:
        if not isinstance(row, dict):
            continue
        if all(row.get(field) == candidate.get(field) for field in key_fields):
            return rows
    rows.append(candidate)
    return rows


async def _upsert_competition_roster_entry(
    db: AsyncSession,
    *,
    competition_type: str,
    competition_name: str | None,
    season: str | None,
    team_name: str | None,
    roster_status: HistoricalCompetitionRosterStatus,
    canonical_player_id: int | None,
    source_player_id: str | None,
    source_player_name: str,
    normalized_source_player_name: str,
    source_schema: str,
    source_system: str,
    batch_id: str,
    game_id: str,
    source_provenance: dict[str, Any],
    now: dt.datetime,
) -> tuple[bool, int]:
    filters = [
        HistoricalCompetitionRosterEntry.source_system == source_system,
        HistoricalCompetitionRosterEntry.source_schema == source_schema,
        HistoricalCompetitionRosterEntry.game_id == game_id,
        HistoricalCompetitionRosterEntry.roster_status == roster_status,
        HistoricalCompetitionRosterEntry.normalized_source_player_name
        == normalized_source_player_name,
    ]
    if team_name is None:
        filters.append(HistoricalCompetitionRosterEntry.team_name.is_(None))
    else:
        filters.append(HistoricalCompetitionRosterEntry.team_name == team_name)

    existing = (
        (await db.execute(select(HistoricalCompetitionRosterEntry).where(*filters)))
        .scalars()
        .first()
    )
    provenance_ref = {
        "batch_id": batch_id,
        "game_id": game_id,
        "source_hash_sha256": source_provenance.get("source_hash_sha256"),
        "source_schema": source_schema,
        "source_system": source_system,
    }
    created = False
    if existing is None:
        existing = HistoricalCompetitionRosterEntry(
            competition_type=competition_type,
            competition_name=competition_name,
            season=season,
            team_name=team_name,
            roster_status=roster_status,
            canonical_player_id=canonical_player_id,
            source_player_id=source_player_id,
            source_player_name=source_player_name,
            normalized_source_player_name=normalized_source_player_name,
            source_schema=source_schema,
            source_system=source_system,
            batch_id=batch_id,
            game_id=game_id,
            provenance_references=[provenance_ref],
            conflict_references=[],
            review_required=False,
        )
        db.add(existing)
        await db.flush()
        created = True
    else:
        existing.provenance_references = _append_unique_dict_by_keys(
            list(existing.provenance_references or []),
            provenance_ref,
            ("batch_id", "game_id", "source_hash_sha256"),
        )
        if existing.canonical_player_id is None and canonical_player_id is not None:
            existing.canonical_player_id = canonical_player_id
        if existing.source_player_id is None and source_player_id is not None:
            existing.source_player_id = source_player_id
        if existing.batch_id is None:
            existing.batch_id = batch_id
        db.add(existing)

    conflict_count = 0
    if canonical_player_id is not None and team_name:
        team_conflicts = (
            (
                await db.execute(
                    select(HistoricalCompetitionRosterEntry).where(
                        HistoricalCompetitionRosterEntry.id != existing.id,
                        HistoricalCompetitionRosterEntry.source_system == source_system,
                        HistoricalCompetitionRosterEntry.source_schema == source_schema,
                        HistoricalCompetitionRosterEntry.competition_type == competition_type,
                        HistoricalCompetitionRosterEntry.competition_name == competition_name,
                        HistoricalCompetitionRosterEntry.season == season,
                        HistoricalCompetitionRosterEntry.game_id == game_id,
                        HistoricalCompetitionRosterEntry.canonical_player_id == canonical_player_id,
                        HistoricalCompetitionRosterEntry.team_name.is_not(None),
                        HistoricalCompetitionRosterEntry.team_name != team_name,
                    )
                )
            )
            .scalars()
            .all()
        )
        for conflict_row in team_conflicts:
            conflict_ref = {
                "type": "same_match_multi_team_conflict",
                "conflicting_entry_id": conflict_row.id,
                "canonical_player_id": canonical_player_id,
                "game_id": game_id,
                "competition_name": competition_name,
                "season": season,
                "team_name": team_name,
                "conflicting_team_name": conflict_row.team_name,
                "detected_at": now.isoformat(),
            }
            existing.conflict_references = _append_unique_dict_by_keys(
                list(existing.conflict_references or []),
                conflict_ref,
                ("type", "conflicting_entry_id"),
            )
            conflict_row.conflict_references = _append_unique_dict_by_keys(
                list(conflict_row.conflict_references or []),
                {
                    **conflict_ref,
                    "conflicting_entry_id": existing.id,
                    "team_name": conflict_row.team_name,
                    "conflicting_team_name": team_name,
                },
                ("type", "conflicting_entry_id"),
            )
            existing.review_required = True
            conflict_row.review_required = True
            db.add(conflict_row)
            conflict_count += 1
        if conflict_count:
            db.add(existing)

    return created, conflict_count


async def register_historical_source_players(
    db: AsyncSession,
    *,
    batch_id: str,
    game_id: str,
    source_schema: str,
    source_system: str,
    source_provenance: dict[str, Any],
    competition_context: dict[str, Any],
    roster_snapshot: list[dict[str, Any]],
    player_names: list[str],
    match_date: str | None = None,
) -> _RegistrationSummary:
    now = dt.datetime.now(UTC)
    entries = _extract_roster_entries(roster_snapshot, player_names)
    summary: _RegistrationSummary = {
        "registered_count": 0,
        "auto_resolved_count": 0,
        "manually_resolved_count": 0,
        "unresolved_count": 0,
        "ambiguous_count": 0,
        "blocked_count": 0,
        "queue_pending_count": 0,
        "source_player_ids": [],
        "deterministic_methods_used": [],
        "metadata_fields_recorded": 0,
        "career_profiles_updated": 0,
        "canonical_safe_fills": 0,
        "metadata_conflicts": 0,
        "roster_entries_upserted": 0,
        "roster_conflicts": 0,
        "resolved_count": 0,
        "mapping_records_created": 0,
        "mapping_records_updated": 0,
        "missing_source_id_count": 0,
        "unresolved_reasons": [],
        "ambiguous_reasons": [],
    }

    for entry in entries:
        source_player_name = entry["name"]
        team_name = entry.get("team_name")
        metadata_raw = entry.get("metadata")
        metadata: dict[str, Any] = metadata_raw if isinstance(metadata_raw, dict) else {}
        roster_statuses_raw = entry.get("roster_statuses")
        roster_statuses = (
            [str(item) for item in roster_statuses_raw if isinstance(item, str)]
            if isinstance(roster_statuses_raw, list)
            else ["unavailable_unknown"]
        )
        explicit_source_player_id = _normalize_metadata_value(metadata.get("source_player_id"))
        metadata_source_status = (
            "source"
            if str(entry.get("metadata_source_status") or "unknown") == "source"
            else "unknown"
        )
        batting_style = _normalize_metadata_value(metadata.get("batting_style"))
        bowling_style = _normalize_metadata_value(metadata.get("bowling_style"))
        role_value = _normalize_metadata_value(metadata.get("role"))
        batting_innings_count = _safe_int(metadata.get("batting_innings_count"))
        bowling_participation_count = _safe_int(metadata.get("bowling_participation_count"))
        role_source_status = (
            "source" if (metadata_source_status == "source" and role_value) else "unknown"
        )
        style_source_status = (
            "source"
            if (metadata_source_status == "source" and (batting_style or bowling_style))
            else "unknown"
        )
        role_confidence_status = "high" if role_source_status == "source" else "unknown"
        style_confidence_status = "high" if style_source_status == "source" else "unknown"
        normalized_name = normalize_source_player_name(source_player_name)
        registry: HistoricalSourcePlayerRegistry | None = None
        resolution_reason: str | None = None
        if explicit_source_player_id:
            registry_by_id_stmt = select(HistoricalSourcePlayerRegistry).where(
                HistoricalSourcePlayerRegistry.source_system == source_system,
                HistoricalSourcePlayerRegistry.source_schema == source_schema,
                HistoricalSourcePlayerRegistry.source_player_id == explicit_source_player_id,
            )
            registry = (await db.execute(registry_by_id_stmt)).scalars().first()

        if registry is None:
            registry_stmt = select(HistoricalSourcePlayerRegistry).where(
                HistoricalSourcePlayerRegistry.source_system == source_system,
                HistoricalSourcePlayerRegistry.source_schema == source_schema,
                HistoricalSourcePlayerRegistry.normalized_name == normalized_name,
            )
            registry = (await db.execute(registry_stmt)).scalars().first()
        if registry is None:
            resolved = await _resolve_identity(
                db,
                normalized_name=normalized_name,
                source_schema=source_schema,
                source_system=source_system,
                competition_context=competition_context,
                team_name=team_name,
            )
            resolution_reason = resolved.queue_reason
            create_kwargs: dict[str, Any] = {}
            if explicit_source_player_id:
                create_kwargs["source_player_id"] = explicit_source_player_id
            registry = HistoricalSourcePlayerRegistry(
                source_player_name=source_player_name,
                normalized_name=normalized_name,
                source_schema=source_schema,
                source_system=source_system,
                resolution_state=resolved.state,
                canonical_player_id=resolved.canonical_player_id,
                confidence_score=resolved.confidence_score,
                mapping_method=resolved.mapping_method,
                first_seen=now,
                last_seen=now,
                match_references=[game_id],
                competition_references=[
                    {
                        "competition_name": competition_context.get("competition_name"),
                        "season": competition_context.get("season"),
                        "team_name": team_name,
                    }
                ],
                provenance_references=[
                    {
                        "batch_id": batch_id,
                        "game_id": game_id,
                        "source_schema": source_schema,
                        "source_system": source_system,
                        "source_hash_sha256": source_provenance.get("source_hash_sha256"),
                    }
                ],
                alias_references=[source_player_name],
                metadata_field_history=[],
                metadata_conflicts=[],
                career_profile_foundation={},
                review_required=False,
                **create_kwargs,
            )
            db.add(registry)
            await db.flush()
            summary["registered_count"] += 1
            summary["mapping_records_created"] += 1
        else:
            summary["mapping_records_updated"] += 1
            registry.last_seen = now
            if explicit_source_player_id and registry.source_player_id != explicit_source_player_id:
                registry.alias_references = _append_unique(
                    list(registry.alias_references or []),
                    explicit_source_player_id,
                )
            registry.match_references = _append_unique(
                list(registry.match_references or []), game_id
            )
            registry.competition_references = _append_unique(
                list(registry.competition_references or []),
                {
                    "competition_name": competition_context.get("competition_name"),
                    "season": competition_context.get("season"),
                    "team_name": team_name,
                },
            )
            registry.provenance_references = _append_unique(
                list(registry.provenance_references or []),
                {
                    "batch_id": batch_id,
                    "game_id": game_id,
                    "source_schema": source_schema,
                    "source_system": source_system,
                    "source_hash_sha256": source_provenance.get("source_hash_sha256"),
                },
            )
            registry.alias_references = _append_unique(
                list(registry.alias_references or []), source_player_name
            )
            if not registry.manual_override and registry.canonical_player_id is None:
                refreshed = await _resolve_identity(
                    db,
                    normalized_name=normalized_name,
                    source_schema=source_schema,
                    source_system=source_system,
                    competition_context=competition_context,
                    team_name=team_name,
                )
                resolution_reason = refreshed.queue_reason
                registry.resolution_state = refreshed.state
                registry.canonical_player_id = refreshed.canonical_player_id
                registry.confidence_score = refreshed.confidence_score
                registry.mapping_method = refreshed.mapping_method
            db.add(registry)

        alias_stmt = select(HistoricalSourcePlayerAlias).where(
            HistoricalSourcePlayerAlias.source_player_id == registry.source_player_id,
            HistoricalSourcePlayerAlias.normalized_alias == normalized_name,
            HistoricalSourcePlayerAlias.source_schema == source_schema,
            HistoricalSourcePlayerAlias.source_system == source_system,
        )
        alias = (await db.execute(alias_stmt)).scalars().first()
        alias_provenance = {
            "batch_id": batch_id,
            "game_id": game_id,
            "team_name": team_name,
        }
        if alias is None:
            alias = HistoricalSourcePlayerAlias(
                source_player_id=registry.source_player_id,
                alias_name=source_player_name,
                normalized_alias=normalized_name,
                source_schema=source_schema,
                source_system=source_system,
                provenance_reference=alias_provenance,
                first_seen=now,
                last_seen=now,
            )
            db.add(alias)
        else:
            alias.last_seen = now
            alias.alias_name = source_player_name
            alias.provenance_reference = alias_provenance
            db.add(alias)

        queue_stmt = select(HistoricalPlayerResolutionQueue).where(
            HistoricalPlayerResolutionQueue.source_player_id == registry.source_player_id
        )
        queue_row = (await db.execute(queue_stmt)).scalars().first()
        if registry.resolution_state in {
            HistoricalPlayerResolutionState.unresolved,
            HistoricalPlayerResolutionState.ambiguous,
            HistoricalPlayerResolutionState.blocked,
        }:
            queue_reason = (
                "ambiguous"
                if registry.resolution_state == HistoricalPlayerResolutionState.ambiguous
                else "unresolved"
            )
            if queue_row is None:
                queue_row = HistoricalPlayerResolutionQueue(
                    source_player_id=registry.source_player_id,
                    queue_state="pending",
                    reason=queue_reason,
                    resolution_snapshot={
                        "source_player_name": registry.source_player_name,
                        "normalized_name": registry.normalized_name,
                        "resolution_state": registry.resolution_state.value,
                        "batch_id": batch_id,
                        "game_id": game_id,
                        "team_name": team_name,
                        "resolution_reason": resolution_reason,
                    },
                    last_seen=now,
                )
            else:
                queue_row.queue_state = "pending"
                queue_row.reason = queue_reason
                queue_row.resolution_snapshot = {
                    **(queue_row.resolution_snapshot or {}),
                    "resolution_state": registry.resolution_state.value,
                    "batch_id": batch_id,
                    "game_id": game_id,
                    "team_name": team_name,
                    "resolution_reason": resolution_reason,
                }
                queue_row.last_seen = now
                queue_row.resolved_at = None
            db.add(queue_row)
            summary["queue_pending_count"] += 1
        elif queue_row is not None:
            queue_row.queue_state = "resolved"
            queue_row.reason = "resolved"
            queue_row.last_seen = now
            queue_row.resolved_at = now
            db.add(queue_row)

        if _upsert_metadata_history(
            registry,
            field_name="batting_style",
            value=batting_style,
            source_system=source_system,
            source_schema=source_schema,
            batch_id=batch_id,
            game_id=game_id,
            source_status=style_source_status,
            confidence_status=style_confidence_status,
            now=now,
        ):
            summary["metadata_fields_recorded"] += 1
        if _upsert_metadata_history(
            registry,
            field_name="bowling_style",
            value=bowling_style,
            source_system=source_system,
            source_schema=source_schema,
            batch_id=batch_id,
            game_id=game_id,
            source_status=style_source_status,
            confidence_status=style_confidence_status,
            now=now,
        ):
            summary["metadata_fields_recorded"] += 1
        if _upsert_metadata_history(
            registry,
            field_name="player_role",
            value=role_value,
            source_system=source_system,
            source_schema=source_schema,
            batch_id=batch_id,
            game_id=game_id,
            source_status=role_source_status,
            confidence_status=role_confidence_status,
            now=now,
        ):
            summary["metadata_fields_recorded"] += 1

        canonical_player: Player | None = None
        if registry.canonical_player_id is not None:
            canonical_player = await db.get(Player, registry.canonical_player_id)

        if canonical_player is not None and role_value:
            canonical_role = _normalize_metadata_value(canonical_player.role)
            if canonical_role is None and role_confidence_status == "high":
                canonical_player.role = role_value
                db.add(canonical_player)
                summary["canonical_safe_fills"] += 1
            elif canonical_role is not None and _record_conflict_if_needed(
                registry,
                field_name="player_role",
                canonical_value=canonical_role,
                observed_value=role_value,
                source_system=source_system,
                source_schema=source_schema,
                batch_id=batch_id,
                game_id=game_id,
                now=now,
            ):
                summary["metadata_conflicts"] += 1

        _upsert_career_profile_foundation(
            registry,
            competition_context=competition_context,
            team_name=team_name,
            role_value=role_value,
            batting_innings_count=batting_innings_count,
            bowling_participation_count=bowling_participation_count,
            game_id=game_id,
            batch_id=batch_id,
            source_system=source_system,
            source_schema=source_schema,
            match_date=match_date,
            now=now,
        )
        summary["career_profiles_updated"] += 1

        competition_type = (
            _normalize_metadata_value(competition_context.get("competition_type")) or "unknown"
        )
        competition_name = _normalize_metadata_value(competition_context.get("competition_name"))
        season = _normalize_metadata_value(competition_context.get("season"))
        source_player_ref = (
            None
            if registry.canonical_player_id is not None
            else (explicit_source_player_id or registry.source_player_id)
        )
        for raw_status in roster_statuses:
            try:
                roster_status = HistoricalCompetitionRosterStatus(raw_status)
            except ValueError:
                roster_status = HistoricalCompetitionRosterStatus.unavailable_unknown
            created, conflict_count = await _upsert_competition_roster_entry(
                db,
                competition_type=competition_type,
                competition_name=competition_name,
                season=season,
                team_name=team_name,
                roster_status=roster_status,
                canonical_player_id=registry.canonical_player_id,
                source_player_id=source_player_ref,
                source_player_name=source_player_name,
                normalized_source_player_name=normalized_name,
                source_schema=source_schema,
                source_system=source_system,
                batch_id=batch_id,
                game_id=game_id,
                source_provenance=source_provenance,
                now=now,
            )
            if created:
                summary["roster_entries_upserted"] += 1
            summary["roster_conflicts"] += conflict_count
        db.add(registry)

        summary["source_player_ids"].append(registry.source_player_id)
        if (
            registry.mapping_method
            and registry.mapping_method not in summary["deterministic_methods_used"]
        ):
            summary["deterministic_methods_used"].append(registry.mapping_method)

        if registry.resolution_state == HistoricalPlayerResolutionState.auto_resolved:
            summary["auto_resolved_count"] += 1
        elif registry.resolution_state == HistoricalPlayerResolutionState.manually_resolved:
            summary["manually_resolved_count"] += 1
        elif registry.resolution_state == HistoricalPlayerResolutionState.unresolved:
            summary["unresolved_count"] += 1
            diagnostic_reason = _diagnostic_reason(
                resolution_state=registry.resolution_state,
                queue_reason=resolution_reason,
                explicit_source_player_id=explicit_source_player_id,
            )
            if diagnostic_reason == "missing_source_id":
                summary["missing_source_id_count"] += 1
            summary["unresolved_reasons"].append(
                {
                    "source_player_name": source_player_name,
                    "source_player_id": explicit_source_player_id or registry.source_player_id,
                    "reason": diagnostic_reason,
                    "resolution_state": registry.resolution_state.value,
                }
            )
        elif registry.resolution_state == HistoricalPlayerResolutionState.ambiguous:
            summary["ambiguous_count"] += 1
            summary["ambiguous_reasons"].append(
                {
                    "source_player_name": source_player_name,
                    "source_player_id": explicit_source_player_id or registry.source_player_id,
                    "reason": _diagnostic_reason(
                        resolution_state=registry.resolution_state,
                        queue_reason=resolution_reason,
                        explicit_source_player_id=explicit_source_player_id,
                    ),
                    "resolution_state": registry.resolution_state.value,
                }
            )
        elif registry.resolution_state == HistoricalPlayerResolutionState.blocked:
            summary["blocked_count"] += 1
            diagnostic_reason = _diagnostic_reason(
                resolution_state=registry.resolution_state,
                queue_reason=resolution_reason,
                explicit_source_player_id=explicit_source_player_id,
            )
            if diagnostic_reason == "missing_source_id":
                summary["missing_source_id_count"] += 1
            summary["unresolved_reasons"].append(
                {
                    "source_player_name": source_player_name,
                    "source_player_id": explicit_source_player_id or registry.source_player_id,
                    "reason": diagnostic_reason,
                    "resolution_state": registry.resolution_state.value,
                }
            )

        summary["resolved_count"] = (
            summary["auto_resolved_count"] + summary["manually_resolved_count"]
        )

    return summary


# ---------------------------------------------------------------------------
# Phase 10J - Identity Mapping Review service functions
# ---------------------------------------------------------------------------


async def list_unresolved_players(
    db: AsyncSession,
    *,
    limit: int = 100,
) -> list[HistoricalSourcePlayerRegistry]:
    """Return unresolved/pending source player registry entries for review."""
    stmt = (
        select(HistoricalSourcePlayerRegistry)
        .where(
            HistoricalSourcePlayerRegistry.resolution_state.in_(
                [
                    HistoricalPlayerResolutionState.unresolved,
                    HistoricalPlayerResolutionState.ambiguous,
                ]
            )
        )
        .order_by(HistoricalSourcePlayerRegistry.last_seen.desc())
        .limit(limit)
    )
    return (await db.execute(stmt)).scalars().all()


async def get_player_candidates(
    db: AsyncSession,
    registry: HistoricalSourcePlayerRegistry,
) -> list[Player]:
    """Return deterministic candidate Players for an unresolved source player."""
    all_players = (await db.execute(select(Player).where(Player.name.is_not(None)))).scalars().all()
    candidate_ids = _deterministic_alias_candidates(registry.normalized_name, all_players)
    if not candidate_ids:
        return []
    return [p for p in all_players if p.id in candidate_ids]


async def link_source_player(
    db: AsyncSession,
    *,
    source_player_id: str,
    canonical_player_id: int,
    reviewed_by: str | None = None,
) -> tuple[HistoricalSourcePlayerRegistry | None, bool, str]:
    """Link a source player to an existing canonical Player.

    Returns (registry_row, idempotent, message).
    Raises ValueError on invalid input.
    """
    registry = await db.get(HistoricalSourcePlayerRegistry, source_player_id)
    if registry is None:
        raise ValueError(f"Source player '{source_player_id}' not found.")

    canonical_player = await db.get(Player, canonical_player_id)
    if canonical_player is None:
        raise ValueError(f"Canonical player with id {canonical_player_id} not found.")

    idempotent = False
    if registry.canonical_player_id == canonical_player_id and registry.manual_override:
        idempotent = True
        return registry, idempotent, "Already linked (idempotent)."

    now = dt.datetime.now(UTC)
    registry.canonical_player_id = canonical_player_id
    registry.resolution_state = HistoricalPlayerResolutionState.manually_resolved
    registry.mapping_method = "manual_link"
    registry.manual_override = True
    registry.reviewed_by = reviewed_by
    registry.reviewed_at = now
    registry.last_seen = now
    db.add(registry)

    # Resolve pending queue entry if it exists.
    queue_row = (
        (
            await db.execute(
                select(HistoricalPlayerResolutionQueue).where(
                    HistoricalPlayerResolutionQueue.source_player_id == source_player_id
                )
            )
        )
        .scalars()
        .first()
    )
    if queue_row is not None:
        queue_row.queue_state = "resolved"
        queue_row.resolved_at = now
        queue_row.last_seen = now
        db.add(queue_row)

    await db.flush()
    return registry, idempotent, f"Linked to '{canonical_player.name}' (id={canonical_player_id})."


async def create_player_from_source(
    db: AsyncSession,
    *,
    source_player_id: str,
    name: str,
    country: str | None = None,
    role: str | None = None,
    reviewed_by: str | None = None,
) -> tuple[Player, HistoricalSourcePlayerRegistry | None, bool, str]:
    """Create a new canonical Player from a source player identity.

    Returns (new_player, registry_row, idempotent, message).
    """
    registry = await db.get(HistoricalSourcePlayerRegistry, source_player_id)
    if registry is None:
        raise ValueError(f"Source player '{source_player_id}' not found.")

    # Guard against duplicate: check if a Player with this exact name already exists
    existing_player = (
        (await db.execute(select(Player).where(Player.name == name))).scalars().first()
    )
    if existing_player is not None and registry.canonical_player_id == existing_player.id:
        return existing_player, registry, True, "Player already exists and is linked (idempotent)."

    now = dt.datetime.now(UTC)
    new_player = Player(name=name, country=country, role=role)
    db.add(new_player)
    await db.flush()  # get assigned id

    registry.canonical_player_id = new_player.id
    registry.resolution_state = HistoricalPlayerResolutionState.manually_resolved
    registry.mapping_method = "manual_create"
    registry.manual_override = True
    registry.reviewed_by = reviewed_by
    registry.reviewed_at = now
    registry.last_seen = now
    db.add(registry)

    queue_row = (
        (
            await db.execute(
                select(HistoricalPlayerResolutionQueue).where(
                    HistoricalPlayerResolutionQueue.source_player_id == source_player_id
                )
            )
        )
        .scalars()
        .first()
    )
    if queue_row is not None:
        queue_row.queue_state = "resolved"
        queue_row.resolved_at = now
        queue_row.last_seen = now
        db.add(queue_row)

    await db.flush()
    return new_player, registry, False, f"New player '{name}' created (id={new_player.id})."


async def defer_player_resolution(
    db: AsyncSession,
    *,
    source_player_id: str,
    reason: str = "deferred",
    reviewed_by: str | None = None,
) -> tuple[HistoricalSourcePlayerRegistry | None, bool, str]:
    """Defer resolution of a source player without deleting any records.

    The registry resolution_state is kept as-is; only the queue entry is marked
    deferred so re-running backfill can still pick this player up.

    Returns (registry_row, idempotent, message).
    """
    registry = await db.get(HistoricalSourcePlayerRegistry, source_player_id)
    if registry is None:
        raise ValueError(f"Source player '{source_player_id}' not found.")

    now = dt.datetime.now(UTC)

    queue_row = (
        (
            await db.execute(
                select(HistoricalPlayerResolutionQueue).where(
                    HistoricalPlayerResolutionQueue.source_player_id == source_player_id
                )
            )
        )
        .scalars()
        .first()
    )

    idempotent = False
    if queue_row is not None and queue_row.queue_state == "deferred":
        idempotent = True
        return registry, idempotent, "Already deferred (idempotent)."

    if queue_row is not None:
        queue_row.queue_state = "deferred"
        queue_row.last_seen = now
        db.add(queue_row)

    registry.reviewed_by = reviewed_by
    registry.reviewed_at = now
    registry.last_seen = now
    db.add(registry)

    await db.flush()
    return registry, idempotent, f"Player '{registry.source_player_name}' deferred: {reason}."
