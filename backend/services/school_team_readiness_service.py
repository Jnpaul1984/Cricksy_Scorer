"""Deterministic, bounded five-match readiness evidence for a saved School/Club Team."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import and_, case, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import defer

from backend.services.organization_team_performance_access import (
    TeamPerformanceAccessError,
    require_team_performance_access,
)
from backend.services.school_team_analytics_service import (
    TeamAnalyticsRequest,
    _delivery_error,
    _delivery_payload_byte_length,
    _frozen_side_ids,
    _team_scope_clause,
)
from backend.sql_app import models

REQUIRED_PRIOR_MATCHES: Literal[5] = 5
SUPPORTED_ORIGINAL_OVERS = 25
MAX_CANDIDATE_GAMES = 250
MAX_DELIVERY_PAYLOAD_BYTES = 5 * 1024 * 1024
_REASONS = (
    "non_official_match",
    "not_completed",
    "unsupported_match_type",
    "multi_day_match",
    "unsupported_match_rules",
    "unknown_original_format",
    "wrong_original_format",
    "unknown_played_date",
    "ambiguous_team_attribution",
    "missing_ledger",
    "invalid_ledger",
    "unsupported_innings",
    "insufficient_batting_bowling_coverage",
    "reference_game",
    "reference_date_unavailable",
    "not_prior_to_boundary",
    "same_date_ambiguous",
    "scope_too_large",
)
_SUPPORTED_INNINGS = frozenset({1, 2})


@dataclass(frozen=True)
class TeamReadinessRequest:
    actor_user_id: str
    organization_id: str
    team_id: str
    as_of_date: dt.date
    reference_game_id: str | None = None


@dataclass(frozen=True)
class SelectedReadinessSource:
    game_id: str
    played_date: dt.date
    metadata_revision: int
    ledger_digest: str


@dataclass(frozen=True)
class TeamReadinessResult:
    organization_id: str
    team_id: str
    as_of_date: dt.date
    required_history: Literal[5]
    usable_prior_match_count: int
    remaining_match_count: int
    state: Literal["ready", "not_ready", "data_unavailable"]
    usable_batting_match_count: int
    usable_bowling_match_count: int
    exclusion_counts: dict[str, int]
    selected_sources: tuple[SelectedReadinessSource, ...]


def _empty_counts() -> dict[str, int]:
    return dict.fromkeys(_REASONS, 0)


def _source(side: object) -> tuple[str | None, str | None]:
    if not isinstance(side, dict):
        return None, None
    value = side.get("school_source")
    if not isinstance(value, dict):
        return None, None
    organization_id = value.get("organization_id")
    team_id = value.get("team_id")
    return (
        organization_id if isinstance(organization_id, str) else None,
        team_id if isinstance(team_id, str) else None,
    )


def _valid_opponent_boundary(side: object, organization_id: str) -> bool:
    if not isinstance(side, dict):
        return False
    if "school_source" not in side:
        return True
    source = side["school_source"]
    return (
        isinstance(source, dict)
        and isinstance(source.get("organization_id"), str)
        and bool(source["organization_id"].strip())
        and isinstance(source.get("team_id"), str)
        and bool(source["team_id"].strip())
        and source["organization_id"] == organization_id
    )


def _candidate_clause(request: TeamReadinessRequest):
    return _team_scope_clause(
        TeamAnalyticsRequest(
            actor_user_id=request.actor_user_id,
            organization_id=request.organization_id,
            team_id=request.team_id,
            overs_limit=SUPPORTED_ORIGINAL_OVERS,
        )
    )


def _readiness_candidates_stmt(request: TeamReadinessRequest, dialect_name: str):
    byte_length = _delivery_payload_byte_length(dialect_name)
    candidate_metrics = (
        select(
            models.Game.id.label("game_id"),
            byte_length.label("payload_bytes"),
        )
        .where(_candidate_clause(request))
        .order_by(models.Game.id)
        .limit(MAX_CANDIDATE_GAMES + 1)
        .cte("readiness_candidate_metrics")
    )
    bounded_metrics = select(
        candidate_metrics.c.game_id,
        candidate_metrics.c.payload_bytes,
        func.count().over().label("candidate_count"),
        func.sum(func.coalesce(candidate_metrics.c.payload_bytes, 0))
        .over()
        .label("candidate_payload_bytes"),
    ).cte("bounded_readiness_metrics")
    within_limits = and_(
        bounded_metrics.c.candidate_count <= MAX_CANDIDATE_GAMES,
        bounded_metrics.c.candidate_payload_bytes <= MAX_DELIVERY_PAYLOAD_BYTES,
    )
    return (
        select(
            models.Game,
            case((within_limits, models.Game.deliveries), else_=None).label("bounded_deliveries"),
            bounded_metrics.c.candidate_count,
            bounded_metrics.c.candidate_payload_bytes,
        )
        .join(bounded_metrics, bounded_metrics.c.game_id == models.Game.id)
        .order_by(models.Game.id)
        .options(defer(models.Game.deliveries))
        .execution_options(populate_existing=True)
    )


async def _validate_game_ledger(
    game: models.Game,
    raw_deliveries: object,
    *,
    organization_id: str,
    team_id: str,
    existing_team_ids: set[str],
) -> tuple[str | None, str | None]:
    if not isinstance(game.team_a, dict) or not isinstance(game.team_b, dict):
        return "ambiguous_team_attribution", None
    sources = (_source(game.team_a), _source(game.team_b))
    side_names: tuple[Literal["team_a", "team_b"], Literal["team_a", "team_b"]] = (
        "team_a",
        "team_b",
    )
    team_sides = [
        side
        for side, (source_org, source_team) in zip(side_names, sources, strict=True)
        if source_org == organization_id and source_team == team_id
    ]
    if len(team_sides) != 1:
        return "ambiguous_team_attribution", None
    target_side = team_sides[0]
    opposite_side = game.team_b if target_side == "team_a" else game.team_a
    if not _valid_opponent_boundary(opposite_side, organization_id):
        return "ambiguous_team_attribution", None
    for side, (source_org, source_team) in zip((game.team_a, game.team_b), sources, strict=True):
        if "school_source" in side and (
            source_org != organization_id
            or source_team is None
            or source_team not in existing_team_ids
        ):
            return "ambiguous_team_attribution", None

    ids_a = _frozen_side_ids(game.team_a, require_canonical=target_side == "team_a")
    ids_b = _frozen_side_ids(game.team_b, require_canonical=target_side == "team_b")
    if not ids_a or not ids_b or ids_a.intersection(ids_b):
        return "ambiguous_team_attribution", None
    side_ids: dict[Literal["team_a", "team_b"], set[str]] = {
        "team_a": ids_a,
        "team_b": ids_b,
    }

    if not isinstance(raw_deliveries, list) or not raw_deliveries:
        return "missing_ledger", None
    grouped: dict[int, list[dict]] = {}
    for row in raw_deliveries:
        if not isinstance(row, dict):
            return "invalid_ledger", None
        inning = row.get("inning")
        if type(inning) is not int or inning < 1:
            return "invalid_ledger", None
        if inning not in _SUPPORTED_INNINGS:
            return "unsupported_innings", None
        grouped.setdefault(inning, []).append(row)

    team_roles: set[str] = set()
    for _, deliveries in sorted(grouped.items()):
        inferred_sides: set[Literal["team_a", "team_b"]] = set()
        for row in deliveries:
            striker = row.get("striker_id")
            matching = (
                [side for side, player_ids in side_ids.items() if striker in player_ids]
                if isinstance(striker, str)
                else []
            )
            if len(matching) != 1:
                return "invalid_ledger", None
            inferred_sides.add(matching[0])
        batting_side = next(iter(inferred_sides)) if len(inferred_sides) == 1 else None
        if any(
            _delivery_error(row, batting_side=batting_side, side_ids=side_ids) is not None
            for row in deliveries
        ):
            return "invalid_ledger", None
        team_roles.add("batting" if batting_side == target_side else "bowling")
    if team_roles != {"batting", "bowling"}:
        return "insufficient_batting_bowling_coverage", None
    digest = hashlib.sha256(
        json.dumps(raw_deliveries, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return None, digest


def _summary(
    request: TeamReadinessRequest,
    *,
    state: Literal["ready", "not_ready", "data_unavailable"],
    counts: dict[str, int],
    selected: tuple[SelectedReadinessSource, ...] = (),
    usable_count: int = 0,
    batting_count: int = 0,
    bowling_count: int = 0,
) -> TeamReadinessResult:
    return TeamReadinessResult(
        organization_id=request.organization_id,
        team_id=request.team_id,
        as_of_date=request.as_of_date,
        required_history=REQUIRED_PRIOR_MATCHES,
        usable_prior_match_count=usable_count,
        remaining_match_count=max(REQUIRED_PRIOR_MATCHES - usable_count, 0),
        state=state,
        usable_batting_match_count=batting_count,
        usable_bowling_match_count=bowling_count,
        exclusion_counts=counts,
        selected_sources=selected,
    )


async def evaluate_team_match_readiness(
    db: AsyncSession,
    request: TeamReadinessRequest,
) -> TeamReadinessResult:
    """Return a safe summary while retaining the deterministic latest-five lineage internally."""
    if type(request.as_of_date) is not dt.date:
        raise ValueError("as_of_date must be a calendar date")
    await require_team_performance_access(
        db,
        organization_id=request.organization_id,
        team_id=request.team_id,
        actor_user_id=request.actor_user_id,
    )

    candidates = (
        await db.execute(_readiness_candidates_stmt(request, db.get_bind().dialect.name))
    ).all()
    counts = _empty_counts()
    if candidates and (
        candidates[0][2] > MAX_CANDIDATE_GAMES or candidates[0][3] > MAX_DELIVERY_PAYLOAD_BYTES
    ):
        counts["scope_too_large"] = 1
        return _summary(request, state="data_unavailable", counts=counts)
    games_and_deliveries = [(row[0], row[1]) for row in candidates]
    games = [game for game, _ in games_and_deliveries]
    by_id = {game.id: game for game in games}
    candidate_team_ids: set[str] = set()
    for game, _raw_deliveries in games_and_deliveries:
        for side in (game.team_a, game.team_b):
            if not isinstance(side, dict) or "school_source" not in side:
                continue
            source_org, source_team = _source(side)
            if source_org == request.organization_id and source_team is not None:
                candidate_team_ids.add(source_team)
    existing_team_ids = (
        set(
            (
                await db.scalars(
                    select(models.Team.id).where(
                        models.Team.id.in_(candidate_team_ids),
                        models.Team.organization_id == request.organization_id,
                    )
                )
            ).all()
        )
        if candidate_team_ids
        else set()
    )
    if request.reference_game_id is not None:
        reference = by_id.get(request.reference_game_id)
        if reference is None:
            raise TeamPerformanceAccessError(404, "Game not found")
        if (
            reference.played_date_trust_state != "confirmed"
            or reference.actual_played_date is None
            or reference.actual_played_date != request.as_of_date
        ):
            counts["reference_date_unavailable"] = 1
            return _summary(request, state="data_unavailable", counts=counts)
        reference_sides = [
            (org_id, saved_team_id)
            for org_id, saved_team_id in (_source(reference.team_a), _source(reference.team_b))
            if org_id == request.organization_id and saved_team_id == request.team_id
        ]
        if len(reference_sides) != 1:
            counts["reference_date_unavailable"] = 1
            return _summary(request, state="data_unavailable", counts=counts)

    eligible: list[tuple[models.Game, str]] = []
    delivery_payloads = {game.id: payload for game, payload in games_and_deliveries}
    for game in games:
        if game.id == request.reference_game_id:
            counts["reference_game"] += 1
            continue
        reason: str | None = None
        if game.match_purpose != "official":
            reason = "non_official_match"
        elif game.status != models.GameStatus.completed:
            reason = "not_completed"
        elif game.match_type == "multi_day" or game.days_limit is not None:
            reason = "multi_day_match"
        elif game.match_type != "limited":
            reason = "unsupported_match_type"
        elif game.match_rules is not None:
            reason = "unsupported_match_rules"
        elif (
            game.original_format_trust_state not in {"setup_capture", "staff_corrected"}
            or game.original_overs_limit is None
            or game.original_format_source not in {"school_match_setup", "staff_correction"}
        ):
            reason = "unknown_original_format"
        elif game.original_overs_limit != SUPPORTED_ORIGINAL_OVERS:
            reason = "wrong_original_format"
        elif (
            game.played_date_trust_state != "confirmed"
            or game.actual_played_date is None
            or game.played_date_source != "staff_confirmed"
        ):
            reason = "unknown_played_date"
        elif game.actual_played_date >= request.as_of_date:
            reason = "not_prior_to_boundary"
        if reason is None:
            reason, digest = await _validate_game_ledger(
                game,
                delivery_payloads[game.id],
                organization_id=request.organization_id,
                team_id=request.team_id,
                existing_team_ids=existing_team_ids,
            )
            if reason is None:
                assert digest is not None
                eligible.append((game, digest))
        if reason is not None:
            counts[reason] += 1

    date_counts: dict[dt.date, int] = {}
    for game, _ in eligible:
        assert game.actual_played_date is not None
        date_counts[game.actual_played_date] = date_counts.get(game.actual_played_date, 0) + 1
    ambiguous_dates = {played_date for played_date, count in date_counts.items() if count > 1}
    chronologically_usable: list[tuple[models.Game, str]] = []
    for game, digest in eligible:
        assert game.actual_played_date is not None
        if date_counts[game.actual_played_date] > 1:
            counts["same_date_ambiguous"] += 1
        else:
            chronologically_usable.append((game, digest))

    chronologically_usable.sort(
        key=lambda item: item[0].actual_played_date or dt.date.min,
        reverse=True,
    )
    usable_count = len(chronologically_usable)
    selected = tuple(
        SelectedReadinessSource(
            game_id=game.id,
            played_date=game.actual_played_date,
            metadata_revision=game.team_performance_metadata_revision,
            ledger_digest=digest,
        )
        for game, digest in chronologically_usable[:REQUIRED_PRIOR_MATCHES]
        if game.actual_played_date is not None
    )
    cutoff_date = (
        chronologically_usable[REQUIRED_PRIOR_MATCHES - 1][0].actual_played_date
        if usable_count >= REQUIRED_PRIOR_MATCHES
        else None
    )
    chronology_unavailable = cutoff_date is not None and any(
        ambiguous_date >= cutoff_date for ambiguous_date in ambiguous_dates
    )
    if chronology_unavailable:
        state: Literal["ready", "not_ready", "data_unavailable"] = "data_unavailable"
    elif usable_count >= REQUIRED_PRIOR_MATCHES:
        state = "ready"
    else:
        state = "not_ready"
    return _summary(
        request,
        state=state,
        counts=counts,
        selected=() if chronology_unavailable else selected,
        usable_count=usable_count,
        batting_count=usable_count,
        bowling_count=usable_count,
    )
