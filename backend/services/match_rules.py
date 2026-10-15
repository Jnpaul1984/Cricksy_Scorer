"""Dormant, versioned match-rule validation and resolution.

This module deliberately has no routes or creation workflow.  It is the one
place later setup and scoring work can use to turn a stored rules snapshot into
effective, match-local rules without deriving player identity from names.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

OFFICIAL_MATCH_PURPOSE = "official"
PRACTICE_MATCH_PURPOSE = "practice"
MATCH_PURPOSES = frozenset({OFFICIAL_MATCH_PURPOSE, PRACTICE_MATCH_PURPOSE})
PRACTICE_RULES_VERSION = 1
DEFAULT_PRACTICE_OVERS = 20
MIN_SIDE_SIZE = 2
MAX_SIDE_SIZE = 11
LEGAL_BALLS_PER_OVER = 6


class MatchRulesValidationError(ValueError):
    """Raised when a persisted or proposed rule snapshot is not trustworthy."""


@dataclass(frozen=True)
class PracticeSideSnapshot:
    """Identity-only side snapshot; display names are intentionally absent."""

    source_squad_id: str
    canonical_player_ids: tuple[str, ...]


@dataclass(frozen=True)
class ResolvedMatchRules:
    """Effective rules used by future scoring consumers.

    Official/legacy games retain their existing ten-wicket semantics.  Practice
    records are never resolved until their complete, versioned snapshot passes
    strict validation.
    """

    match_purpose: str
    version: int | None
    overs: int | None
    balls_per_over: int
    innings_per_side: int
    wicket_limits: Mapping[str, int]
    sides: Mapping[str, PracticeSideSnapshot] | None
    dls_enabled: bool
    predictions_enabled: bool

    def wicket_limit_for(self, side_key: str) -> int:
        try:
            return self.wicket_limits[side_key]
        except KeyError as exc:
            raise MatchRulesValidationError(f"Unknown match-local side: {side_key}") from exc


def _reject_unknown_fields(value: Mapping[str, Any], *, allowed: frozenset[str], path: str) -> None:
    unknown = set(value) - allowed
    if unknown:
        names = ", ".join(sorted(map(str, unknown)))
        raise MatchRulesValidationError(f"{path} contains unsupported field(s): {names}")


def _require_mapping(value: Any, *, path: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise MatchRulesValidationError(f"{path} must be an object")
    return value


def _require_int(value: Any, *, path: str, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise MatchRulesValidationError(f"{path} must be an integer from {minimum} to {maximum}")
    return value


def _require_string(value: Any, *, path: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise MatchRulesValidationError(f"{path} must be a non-empty string")
    return value


def _require_disabled(value: Any, *, path: str) -> None:
    if value is not False:
        raise MatchRulesValidationError(f"{path} must be false for dormant practice rules")


def _parse_side(value: Any, *, side_key: str) -> PracticeSideSnapshot:
    side = _require_mapping(value, path=f"sides.{side_key}")
    _reject_unknown_fields(
        side,
        allowed=frozenset({"source_squad_id", "canonical_player_ids"}),
        path=f"sides.{side_key}",
    )
    if set(side) != {"source_squad_id", "canonical_player_ids"}:
        raise MatchRulesValidationError(
            f"sides.{side_key} must contain its complete identity snapshot"
        )
    source_squad_id = _require_string(
        side["source_squad_id"], path=f"sides.{side_key}.source_squad_id"
    )
    player_ids = side["canonical_player_ids"]
    if not isinstance(player_ids, list):
        raise MatchRulesValidationError(f"sides.{side_key}.canonical_player_ids must be a list")
    if not MIN_SIDE_SIZE <= len(player_ids) <= MAX_SIDE_SIZE:
        raise MatchRulesValidationError(
            f"sides.{side_key}.canonical_player_ids must contain {MIN_SIDE_SIZE}-{MAX_SIDE_SIZE} players"
        )
    canonical_ids = tuple(
        _require_string(player_id, path=f"sides.{side_key}.canonical_player_ids[{index}]")
        for index, player_id in enumerate(player_ids)
    )
    if len(set(canonical_ids)) != len(canonical_ids):
        raise MatchRulesValidationError(f"sides.{side_key} contains a duplicate canonical player")
    return PracticeSideSnapshot(source_squad_id=source_squad_id, canonical_player_ids=canonical_ids)


def resolve_match_rules(*, match_purpose: Any, match_rules: Any) -> ResolvedMatchRules:
    """Validate and resolve persisted rules without mutating the input.

    An explicit practice purpose fails closed: no snapshot, an empty mapping,
    malformed types, unknown fields, unknown versions, or a mismatched frozen
    count/wicket limit all raise rather than falling back to official rules.
    """

    if not isinstance(match_purpose, str) or match_purpose not in MATCH_PURPOSES:
        raise MatchRulesValidationError("match_purpose must be 'official' or 'practice'")

    if match_purpose == OFFICIAL_MATCH_PURPOSE:
        if match_rules is not None:
            raise MatchRulesValidationError("official matches must not carry practice match_rules")
        return ResolvedMatchRules(
            match_purpose=OFFICIAL_MATCH_PURPOSE,
            version=None,
            overs=None,
            balls_per_over=LEGAL_BALLS_PER_OVER,
            innings_per_side=1,
            wicket_limits={"team_a": 10, "team_b": 10},
            sides=None,
            dls_enabled=False,
            predictions_enabled=False,
        )

    rules = _require_mapping(match_rules, path="match_rules")
    _reject_unknown_fields(
        rules,
        allowed=frozenset(
            {
                "version",
                "overs",
                "balls_per_over",
                "innings_per_side",
                "side_sizes",
                "wicket_limits",
                "sides",
                "dls_enabled",
                "predictions_enabled",
            }
        ),
        path="match_rules",
    )
    required = {
        "version",
        "overs",
        "balls_per_over",
        "innings_per_side",
        "side_sizes",
        "wicket_limits",
        "sides",
        "dls_enabled",
        "predictions_enabled",
    }
    if set(rules) != required:
        raise MatchRulesValidationError("match_rules must contain the complete version 1 snapshot")
    _require_int(
        rules["version"],
        path="match_rules.version",
        minimum=PRACTICE_RULES_VERSION,
        maximum=PRACTICE_RULES_VERSION,
    )
    overs = _require_int(rules["overs"], path="match_rules.overs", minimum=1, maximum=120)
    _require_int(
        rules["balls_per_over"],
        path="match_rules.balls_per_over",
        minimum=LEGAL_BALLS_PER_OVER,
        maximum=LEGAL_BALLS_PER_OVER,
    )
    _require_int(
        rules["innings_per_side"],
        path="match_rules.innings_per_side",
        minimum=1,
        maximum=1,
    )
    _require_disabled(rules["dls_enabled"], path="match_rules.dls_enabled")
    _require_disabled(rules["predictions_enabled"], path="match_rules.predictions_enabled")

    sides_value = _require_mapping(rules["sides"], path="match_rules.sides")
    side_sizes = _require_mapping(rules["side_sizes"], path="match_rules.side_sizes")
    wicket_limits = _require_mapping(rules["wicket_limits"], path="match_rules.wicket_limits")
    for name, value in (
        ("sides", sides_value),
        ("side_sizes", side_sizes),
        ("wicket_limits", wicket_limits),
    ):
        _reject_unknown_fields(
            value, allowed=frozenset({"team_a", "team_b"}), path=f"match_rules.{name}"
        )
        if set(value) != {"team_a", "team_b"}:
            raise MatchRulesValidationError(f"match_rules.{name} must use team_a and team_b")

    sides = {
        side_key: _parse_side(sides_value[side_key], side_key=side_key)
        for side_key in ("team_a", "team_b")
    }
    side_size_a = _require_int(
        side_sizes["team_a"],
        path="match_rules.side_sizes.team_a",
        minimum=MIN_SIDE_SIZE,
        maximum=MAX_SIDE_SIZE,
    )
    side_size_b = _require_int(
        side_sizes["team_b"],
        path="match_rules.side_sizes.team_b",
        minimum=MIN_SIDE_SIZE,
        maximum=MAX_SIDE_SIZE,
    )
    if side_size_a != side_size_b:
        raise MatchRulesValidationError("practice sides must have equal frozen side_sizes")
    for side_key, side_size in (("team_a", side_size_a), ("team_b", side_size_b)):
        if len(sides[side_key].canonical_player_ids) != side_size:
            raise MatchRulesValidationError(
                f"match_rules.side_sizes.{side_key} mismatches its player snapshot"
            )
    all_player_ids = sides["team_a"].canonical_player_ids + sides["team_b"].canonical_player_ids
    if len(set(all_player_ids)) != len(all_player_ids):
        raise MatchRulesValidationError("a canonical player cannot appear on both practice sides")

    parsed_wickets = {
        side_key: _require_int(
            wicket_limits[side_key],
            path=f"match_rules.wicket_limits.{side_key}",
            minimum=1,
            maximum=MAX_SIDE_SIZE - 1,
        )
        for side_key in ("team_a", "team_b")
    }
    for side_key, side_size in (("team_a", side_size_a), ("team_b", side_size_b)):
        if parsed_wickets[side_key] != side_size - 1:
            raise MatchRulesValidationError(
                f"match_rules.wicket_limits.{side_key} must equal frozen side size minus one"
            )

    return ResolvedMatchRules(
        match_purpose=PRACTICE_MATCH_PURPOSE,
        version=PRACTICE_RULES_VERSION,
        overs=overs,
        balls_per_over=LEGAL_BALLS_PER_OVER,
        innings_per_side=1,
        wicket_limits=parsed_wickets,
        sides=sides,
        dls_enabled=False,
        predictions_enabled=False,
    )


def serialize_match_rules(resolved: ResolvedMatchRules) -> dict[str, Any] | None:
    """Return the canonical JSON persistence shape for an already-resolved snapshot."""

    if resolved.match_purpose == OFFICIAL_MATCH_PURPOSE:
        return None
    if resolved.match_purpose != PRACTICE_MATCH_PURPOSE or resolved.sides is None:
        raise MatchRulesValidationError("Only resolved practice rules can be serialized")
    result = {
        "version": resolved.version,
        "overs": resolved.overs,
        "balls_per_over": resolved.balls_per_over,
        "innings_per_side": resolved.innings_per_side,
        "side_sizes": {
            side_key: len(resolved.sides[side_key].canonical_player_ids)
            for side_key in ("team_a", "team_b")
        },
        "wicket_limits": dict(resolved.wicket_limits),
        "sides": {
            side_key: {
                "source_squad_id": resolved.sides[side_key].source_squad_id,
                "canonical_player_ids": list(resolved.sides[side_key].canonical_player_ids),
            }
            for side_key in ("team_a", "team_b")
        },
        "dls_enabled": False,
        "predictions_enabled": False,
    }
    # Keep serialization guarded as tightly as input parsing.
    resolve_match_rules(match_purpose=PRACTICE_MATCH_PURPOSE, match_rules=result)
    return result


def build_practice_match_rules(
    *,
    team_a_source_squad_id: str,
    team_a_canonical_player_ids: list[str],
    team_b_source_squad_id: str,
    team_b_canonical_player_ids: list[str],
    overs: int = DEFAULT_PRACTICE_OVERS,
) -> dict[str, Any]:
    """Build the only supported version-1 snapshot for future setup work.

    This keeps the default at 20 without allowing an absent persisted field to
    masquerade as a valid explicit-practice snapshot.
    """

    side_size_a = len(team_a_canonical_player_ids)
    side_size_b = len(team_b_canonical_player_ids)
    proposed = {
        "version": PRACTICE_RULES_VERSION,
        "overs": overs,
        "balls_per_over": LEGAL_BALLS_PER_OVER,
        "innings_per_side": 1,
        "side_sizes": {"team_a": side_size_a, "team_b": side_size_b},
        "wicket_limits": {"team_a": side_size_a - 1, "team_b": side_size_b - 1},
        "sides": {
            "team_a": {
                "source_squad_id": team_a_source_squad_id,
                "canonical_player_ids": list(team_a_canonical_player_ids),
            },
            "team_b": {
                "source_squad_id": team_b_source_squad_id,
                "canonical_player_ids": list(team_b_canonical_player_ids),
            },
        },
        "dls_enabled": False,
        "predictions_enabled": False,
    }
    resolved = resolve_match_rules(match_purpose=PRACTICE_MATCH_PURPOSE, match_rules=proposed)
    serialized = serialize_match_rules(resolved)
    assert serialized is not None
    return serialized
