"""Deterministic, bounded five-match readiness evidence for a saved School/Club Team."""

from __future__ import annotations

import datetime as dt
import hashlib
import json
from dataclasses import dataclass
from typing import Literal

from backend.services.organization_team_performance_access import (
    TeamPerformanceAccessError,
    require_team_performance_access,
)
from backend.services.school_team_analytics_service import (
    _delivery_error,
    _delivery_payload_byte_length,
    _frozen_side_ids,
)
from backend.sql_app import models
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

REQUIRED_PRIOR_MATCHES = 5
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


def _candidate_clause(request: TeamReadinessRequest):
    org_a = models.Game.team_a["school_source"]["organization_id"].as_string()
    team_a = models.Game.team_a["school_source"]["team_id"].as_string()
    org_b = models.Game.team_b["school_source"]["organization_id"].as_string()
    team_b = models.Game.team_b["school_source"]["team_id"].as_string()
    return or_(
        and_(org_a == request.organization_id, team_a == request.team_id),
        and_(org_b == request.organization_id, team_b == request.team_id),
    )


async def _validate_game_ledger(
    game: models.Game,
    *,
    organization_id: str,
    team_id: str,
) -> tuple[str | None, str | None]:
    if not isinstance(game.team_a, dict) or not isinstance(game.team_b, dict):
        return "ambiguous_team_attribution", None
    sources = (_source(game.team_a), _source(game.team_b))
    team_sides = [
        side
        for side, (source_org, source_team) in zip(("team_a", "team_b"), sources, strict=True)
        if source_org == organization_id and source_team == team_id
    ]
    if len(team_sides) != 1:
        return "ambiguous_team_attribution", None
    target_side: Literal["team_a", "team_b"] = team_sides[0]  # type: ignore[assignment]
    opposite_org_id = sources[1 if target_side == "team_a" else 0][0]
    if opposite_org_id not in {None, organization_id}:
        return "ambiguous_team_attribution", None

    ids_a = _frozen_side_ids(game.team_a, require_canonical=target_side == "team_a")
    ids_b = _frozen_side_ids(game.team_b, require_canonical=target_side == "team_b")
    if not ids_a or not ids_b or ids_a.intersection(ids_b):
        return "ambiguous_team_attribution", None
    side_ids = {"team_a": ids_a, "team_b": ids_b}

    raw_deliveries = game.deliveries
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
        inferred_sides: set[str] = set()
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

    candidate_clause = _candidate_clause(request)
    byte_length = _delivery_payload_byte_length(db.get_bind().dialect.name)
    metadata_rows = (
        await db.execute(
            select(
                models.Game.id,
                models.Game.actual_played_date,
                models.Game.played_date_trust_state,
                models.Game.original_overs_limit,
                models.Game.original_format_trust_state,
                models.Game.team_performance_metadata_revision,
                byte_length,
            )
            .where(candidate_clause)
            .order_by(models.Game.id)
            .limit(MAX_CANDIDATE_GAMES + 1)
        )
    ).all()
    counts = _empty_counts()
    if len(metadata_rows) > MAX_CANDIDATE_GAMES or sum(row[-1] or 0 for row in metadata_rows) > (
        MAX_DELIVERY_PAYLOAD_BYTES
    ):
        counts["scope_too_large"] = 1
        return _summary(request, state="data_unavailable", counts=counts)

    game_ids = {row[0] for row in metadata_rows}
    games = list(
        (
            await db.scalars(
                select(models.Game)
                .where(models.Game.id.in_(game_ids))
                .order_by(models.Game.id)
            )
        ).all()
    ) if game_ids else []
    by_id = {game.id: game for game in games}
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
    for game in games:
        if game.id == request.reference_game_id:
            counts["reference_game"] += 1
            continue
        reason: str | None = None
        if game.match_purpose != "official":
            reason = "non_official_match"
        elif game.status != models.GameStatus.completed:
            reason = "not_completed"
        elif game.match_type != "limited":
            reason = "unsupported_match_type"
        elif game.days_limit is not None:
            reason = "multi_day_match"
        elif game.match_rules is not None:
            reason = "unsupported_match_rules"
        elif (
            game.original_format_trust_state == "unknown"
            or game.original_overs_limit is None
        ):
            reason = "unknown_original_format"
        elif game.original_overs_limit != SUPPORTED_ORIGINAL_OVERS:
            reason = "wrong_original_format"
        elif (
            game.played_date_trust_state != "confirmed"
            or game.actual_played_date is None
        ):
            reason = "unknown_played_date"
        elif game.actual_played_date >= request.as_of_date:
            reason = "not_prior_to_boundary"
        if reason is None:
            reason, digest = await _validate_game_ledger(
                game,
                organization_id=request.organization_id,
                team_id=request.team_id,
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
    state: Literal["ready", "not_ready"] = (
        "ready" if usable_count >= REQUIRED_PRIOR_MATCHES else "not_ready"
    )
    return _summary(
        request,
        state=state,
        counts=counts,
        selected=selected,
        usable_count=usable_count,
        batting_count=usable_count,
        bowling_count=usable_count,
    )
