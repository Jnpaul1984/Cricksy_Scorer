from __future__ import annotations

import datetime as dt
import re
from dataclasses import dataclass
from typing import Any, TypedDict

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.sql_app.models import (
    HistoricalPlayerResolutionQueue,
    HistoricalPlayerResolutionState,
    HistoricalSourcePlayerAlias,
    HistoricalSourcePlayerRegistry,
    Player,
)

UTC = getattr(dt, "UTC", dt.timezone.utc)
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
        canonical_tokens = [token for token in normalize_source_player_name(player.name).split(" ") if token]
        if len(canonical_tokens) < 2:
            continue
        canonical_last = canonical_tokens[-1]
        if canonical_last != source_last:
            continue
        canonical_first_tokens = canonical_tokens[:-1]
        canonical_initials = _initials(canonical_first_tokens)
        same_first_name = source_first_tokens and canonical_first_tokens and (
            source_first_tokens[0] == canonical_first_tokens[0]
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
    entries: list[dict[str, Any]] = []
    seen: set[str] = set()
    for team_entry in roster_snapshot:
        if not isinstance(team_entry, dict):
            continue
        team_name = str(team_entry.get("team_name") or "").strip()
        for player_name in team_entry.get("named_squad") or []:
            if not isinstance(player_name, str) or not player_name.strip():
                continue
            key = player_name.strip().casefold()
            if key in seen:
                continue
            seen.add(key)
            entries.append({"name": player_name.strip(), "team_name": team_name or None})
    for player_name in player_names:
        if not isinstance(player_name, str) or not player_name.strip():
            continue
        key = player_name.strip().casefold()
        if key in seen:
            continue
        seen.add(key)
        entries.append({"name": player_name.strip(), "team_name": None})
    return entries


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
        player for player in all_players if normalize_source_player_name(player.name) == normalized_name
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
            HistoricalSourcePlayerRegistry.source_player_id == HistoricalSourcePlayerAlias.source_player_id,
        )
        .where(
            HistoricalSourcePlayerAlias.normalized_alias == normalized_name,
            HistoricalSourcePlayerAlias.source_schema == source_schema,
            HistoricalSourcePlayerAlias.source_system == source_system,
            HistoricalSourcePlayerRegistry.canonical_player_id.is_not(None),
        )
    )
    alias_rows = (await db.execute(alias_stmt)).all()
    alias_candidates = {registry.canonical_player_id for _, registry in alias_rows if registry.canonical_player_id}
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
    }

    for entry in entries:
        source_player_name = entry["name"]
        team_name = entry.get("team_name")
        normalized_name = normalize_source_player_name(source_player_name)
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
            )
            db.add(registry)
            await db.flush()
            summary["registered_count"] += 1
        else:
            registry.last_seen = now
            registry.match_references = _append_unique(list(registry.match_references or []), game_id)
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

        summary["source_player_ids"].append(registry.source_player_id)
        if registry.mapping_method:
            if registry.mapping_method not in summary["deterministic_methods_used"]:
                summary["deterministic_methods_used"].append(registry.mapping_method)

        if registry.resolution_state == HistoricalPlayerResolutionState.auto_resolved:
            summary["auto_resolved_count"] += 1
        elif registry.resolution_state == HistoricalPlayerResolutionState.manually_resolved:
            summary["manually_resolved_count"] += 1
        elif registry.resolution_state == HistoricalPlayerResolutionState.unresolved:
            summary["unresolved_count"] += 1
        elif registry.resolution_state == HistoricalPlayerResolutionState.ambiguous:
            summary["ambiguous_count"] += 1
        elif registry.resolution_state == HistoricalPlayerResolutionState.blocked:
            summary["blocked_count"] += 1

    return summary
