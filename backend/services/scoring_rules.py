"""Read-only bridge from stored match rules to the live scoring engine.

The setup workflow owns creation and persistence of practice snapshots.  This
module only resolves an already-stored snapshot and exposes the small set of
match-local decisions the scoring engine needs.  Keeping that boundary here
prevents a short-sided practice game from silently inheriting 11-a-side rules.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from backend.services.match_rules import (
    OFFICIAL_MATCH_PURPOSE,
    PRACTICE_MATCH_PURPOSE,
    MatchRulesValidationError,
    ResolvedMatchRules,
    resolve_match_rules,
)


def resolved_rules_for_game(game: Any) -> ResolvedMatchRules:
    """Resolve the immutable rules snapshot attached to ``game``.

    Legacy rows without a purpose are official by definition.  Explicit
    practice rows intentionally fail closed when their snapshot is absent or
    malformed; using ten wickets for those rows would be incorrect.
    """

    purpose = getattr(game, "match_purpose", None) or OFFICIAL_MATCH_PURPOSE
    return resolve_match_rules(match_purpose=purpose, match_rules=getattr(game, "match_rules", None))


def _practice_first_batting_side(game: Any) -> str:
    """Read the creation-owned, persisted first-innings side discriminator.

    The creation contract persists this under
    ``practice_start_context.first_batting_side``.  Absent or malformed metadata is
    never inferred from display names, toss names, or player order.
    """

    context = getattr(game, "practice_start_context", None)
    if not isinstance(context, Mapping) or set(context) != {"version", "first_batting_side"}:
        raise MatchRulesValidationError("practice_start_context must be the complete version 1 object")
    if type(context.get("version")) is not int or context.get("version") != 1:
        raise MatchRulesValidationError("practice_start_context.version must be 1")
    value = context.get("first_batting_side")
    if value not in {"team_a", "team_b"}:
        raise MatchRulesValidationError("practice_start_context.first_batting_side must be team_a or team_b")
    return value


def batting_side_key(game: Any) -> str:
    """Return the stable rule side key for the side currently batting."""

    rules = resolved_rules_for_game(game)
    if rules.match_purpose == PRACTICE_MATCH_PURPOSE:
        inning = int(getattr(game, "current_inning", 0) or 0)
        first = _practice_first_batting_side(game)
        if inning == 1:
            return first
        if inning == 2:
            return "team_b" if first == "team_a" else "team_a"
        raise MatchRulesValidationError("practice scoring supports only innings 1 or 2")

    # Official/legacy behavior remains name-based.
    batting_name = getattr(game, "batting_team_name", None)
    team_a = getattr(game, "team_a", {}) or {}
    team_b = getattr(game, "team_b", {}) or {}
    if batting_name == team_a.get("name"):
        return "team_a"
    if batting_name == team_b.get("name"):
        return "team_b"
    raise MatchRulesValidationError("cannot resolve the current batting side from the game teams")


def team_for_current_batting_side(game: Any) -> Mapping[str, Any]:
    """Return a roster filtered to the immutable active practice side."""

    rules = resolved_rules_for_game(game)
    if rules.match_purpose != PRACTICE_MATCH_PURPOSE:
        batting_name = getattr(game, "batting_team_name", None)
        team_a = getattr(game, "team_a", {}) or {}
        return team_a if batting_name == team_a.get("name") else getattr(game, "team_b", {}) or {}
    assert rules.sides is not None
    side = batting_side_key(game)
    ids = set(rules.sides[side].canonical_player_ids)
    players = [
        player
        for team in (getattr(game, "team_a", {}) or {}, getattr(game, "team_b", {}) or {})
        for player in team.get("players", []) or []
        if str(player.get("id")) in ids
    ]
    if len(players) != len(ids):
        raise MatchRulesValidationError("practice roster no longer matches its frozen side snapshot")
    return {"name": getattr(game, "batting_team_name", None), "players": players}


def team_for_current_bowling_side(game: Any) -> Mapping[str, Any]:
    rules = resolved_rules_for_game(game)
    if rules.match_purpose != PRACTICE_MATCH_PURPOSE:
        batting = team_for_current_batting_side(game)
        team_a = getattr(game, "team_a", {}) or {}
        return getattr(game, "team_b", {}) or {} if batting is team_a else team_a
    assert rules.sides is not None
    side = "team_b" if batting_side_key(game) == "team_a" else "team_a"
    ids = set(rules.sides[side].canonical_player_ids)
    players = [
        player
        for team in (getattr(game, "team_a", {}) or {}, getattr(game, "team_b", {}) or {})
        for player in team.get("players", []) or []
        if str(player.get("id")) in ids
    ]
    if len(players) != len(ids):
        raise MatchRulesValidationError("practice roster no longer matches its frozen side snapshot")
    return {"name": getattr(game, "bowling_team_name", None), "players": players}


def wicket_limit_for_current_innings(game: Any) -> int:
    rules = resolved_rules_for_game(game)
    if rules.match_purpose == OFFICIAL_MATCH_PURPOSE:
        return 10
    return rules.wicket_limit_for(batting_side_key(game))


def innings_is_all_out(game: Any, wickets: int | None = None) -> bool:
    wickets_lost = int(getattr(game, "total_wickets", 0) if wickets is None else wickets)
    return wickets_lost >= wicket_limit_for_current_innings(game)


def practice_features_enabled(game: Any) -> tuple[bool, bool]:
    """Return the DLS and prediction permissions for this match instance."""

    rules = resolved_rules_for_game(game)
    return rules.dls_enabled, rules.predictions_enabled


def is_practice_game(game: Any) -> bool:
    return resolved_rules_for_game(game).match_purpose == PRACTICE_MATCH_PURPOSE


def validate_incoming_batter(game: Any, batter_id: str) -> None:
    """Reject a practice replacement outside its frozen batting-side snapshot."""

    rules = resolved_rules_for_game(game)
    if rules.match_purpose != PRACTICE_MATCH_PURPOSE:
        return
    assert rules.sides is not None
    if str(batter_id) not in rules.sides[batting_side_key(game)].canonical_player_ids:
        raise MatchRulesValidationError("replacement batter is not in the frozen practice batting side")


def validate_delivery_participants(
    game: Any, *, striker_id: str, non_striker_id: str, bowler_id: str, dismissed_player_id: str | None
) -> None:
    """Fail before mutation when a practice delivery names a foreign player."""

    rules = resolved_rules_for_game(game)
    if rules.match_purpose != PRACTICE_MATCH_PURPOSE:
        return
    assert rules.sides is not None
    batting = set(rules.sides[batting_side_key(game)].canonical_player_ids)
    bowling_side = "team_b" if batting_side_key(game) == "team_a" else "team_a"
    bowling = set(rules.sides[bowling_side].canonical_player_ids)
    if striker_id == non_striker_id:
        raise MatchRulesValidationError("practice striker and non-striker must be distinct")
    if striker_id not in batting or non_striker_id not in batting:
        raise MatchRulesValidationError("practice batters must belong to the frozen batting side")
    if bowler_id not in bowling:
        raise MatchRulesValidationError("practice bowler must belong to the frozen bowling side")
    if dismissed_player_id is not None and dismissed_player_id not in batting:
        raise MatchRulesValidationError("practice dismissed player must belong to the frozen batting side")
