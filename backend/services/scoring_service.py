"""
Scoring service: encapsulates per-ball scoring logic.

This module provides score_one(g, ...) which mutates the GameState-like object g
and returns a dict suitable for schemas.Delivery. It is a direct extraction of
the previous main._score_one implementation, with minimal helper helpers copied
over so the module is self-contained and avoids circular imports.
"""

from __future__ import annotations

from typing import Any, cast

from pydantic import BaseModel

# Centralized constants/rules
from backend.domain.constants import CREDIT_BOWLER as _CREDIT_BOWLER
from backend.domain.constants import INVALID_ON_NO_BALL as _INVALID_ON_NO_BALL
from backend.domain.constants import INVALID_ON_WIDE as _INVALID_ON_WIDE
from backend.domain.constants import as_extra_code as _as_extra_code
from backend.domain.constants import norm_extra as _norm_extra


def _complete_over_runtime(g: Any, bowler_id: str | None) -> None:
    # minimal semantics copied from main._complete_over_runtime
    if bowler_id:
        g.last_ball_bowler_id = bowler_id
    g.current_bowler_id = None
    g.current_over_balls = 0
    g.mid_over_change_used = False


def _ensure_batting_entry(g: Any, batter_id: str) -> dict[str, Any]:
    e_any = (getattr(g, "batting_scorecard", {}) or {}).get(batter_id)
    if isinstance(e_any, BaseModel):
        try:
            e = cast(dict[str, Any], e_any.model_dump())
        except Exception:
            try:
                e = cast(dict[str, Any], e_any.dict())  # type: ignore[attr-defined]
            except Exception:
                e = {}
    elif isinstance(e_any, dict):
        e = dict(e_any)
    else:
        e = {
            "player_id": batter_id,
            "player_name": None,
            "runs": 0,
            "balls_faced": 0,
            "is_out": False,
            "fours": 0,
            "sixes": 0,
            "how_out": "",
        }
    e.setdefault("player_id", batter_id)
    e.setdefault("player_name", None)
    e.setdefault("runs", 0)
    e.setdefault("balls_faced", 0)
    e.setdefault("is_out", False)
    e.setdefault("fours", 0)
    e.setdefault("sixes", 0)
    e.setdefault("how_out", "")
    # Mutate the scorecard on the game object
    batting = getattr(g, "batting_scorecard", {}) or {}
    batting[batter_id] = e
    g.batting_scorecard = batting
    return e


def _ensure_bowling_entry(g: Any, bowler_id: str) -> dict[str, Any]:
    e_any = (getattr(g, "bowling_scorecard", {}) or {}).get(bowler_id)
    if isinstance(e_any, BaseModel):
        try:
            e = cast(dict[str, Any], e_any.model_dump())
        except Exception:
            try:
                e = cast(dict[str, Any], e_any.dict())  # type: ignore[attr-defined]
            except Exception:
                e = {}
    elif isinstance(e_any, dict):
        e = dict(e_any)
    else:
        e = {
            "player_id": bowler_id,
            "player_name": None,
            "overs_bowled": 0.0,
            "runs_conceded": 0,
            "wickets_taken": 0,
        }
    e.setdefault("player_id", bowler_id)
    e.setdefault("player_name", None)
    e.setdefault("overs_bowled", 0.0)
    e.setdefault("runs_conceded", 0)
    e.setdefault("wickets_taken", 0)
    bowling = getattr(g, "bowling_scorecard", {}) or {}
    bowling[bowler_id] = e
    g.bowling_scorecard = bowling
    return e


def score_one(
    g: Any,
    *,
    striker_id: str,
    non_striker_id: str,
    bowler_id: str,
    runs_scored: int,
    extra: str | None,
    is_wicket: bool,
    dismissal_type: str | None,
    dismissed_player_id: str | None,
) -> dict[str, Any]:
    """
    Mutates GameState-like object `g` and returns DeliveryKwargs dict.
    Behaviour matches the original implementation in main._score_one.
    """
    # Ensure runtime fields exist
    if getattr(g, "current_striker_id", None) is None:
        g.current_striker_id = striker_id
    if getattr(g, "current_non_striker_id", None) is None:
        g.current_non_striker_id = non_striker_id
    pre_striker = g.current_striker_id
    pre_non_striker = g.current_non_striker_id

    if getattr(g, "current_bowler_id", None) is None:
        g.current_bowler_id = bowler_id
    if not hasattr(g, "pending_new_batter"):
        g.pending_new_batter = False
    if not hasattr(g, "pending_new_over"):
        g.pending_new_over = False

    bowler_id = g.current_bowler_id or bowler_id
    runs = int(runs_scored or 0)

    extra_norm = _norm_extra(extra)
    is_nb = extra_norm == "nb"
    is_wd = extra_norm == "wd"
    legal = not (is_nb or is_wd)

    off_bat_runs = 0
    extra_runs = 0

    if extra_norm is None or extra_norm == "nb":
        off_bat_runs = runs_scored
    elif extra_norm in ("wd", "b", "lb"):
        extra_runs = runs_scored

    team_add = (
        off_bat_runs + (1 if is_nb else 0) + (extra_runs if extra_norm in ("wd", "b", "lb") else 0)
    )
    g.total_runs = int(getattr(g, "total_runs", 0)) + team_add

    delivery_over_number = int(getattr(g, "overs_completed", 0))
    delivery_ball_number = int(getattr(g, "balls_this_over", 0) + 1)

    bs = _ensure_batting_entry(g, striker_id)
    if legal:
        bs["balls_faced"] = int(bs.get("balls_faced", 0) + 1)
    if extra_norm is None or is_nb:
        bs["runs"] = int(bs.get("runs", 0) + runs)

    _ensure_bowling_entry(g, bowler_id)
    if legal:
        g.current_over_balls = int(getattr(g, "current_over_balls", 0) + 1)
        g.last_ball_bowler_id = bowler_id

    dismissal = (dismissal_type or "").strip().lower() or None
    if dismissal:
        if is_nb and dismissal in _INVALID_ON_NO_BALL:
            dismissal = None
        if is_wd and dismissal in _INVALID_ON_WIDE:
            dismissal = None

    out_happened = bool(is_wicket and dismissal)
    out_player_id = dismissed_player_id or striker_id
    if out_happened and out_player_id:
        out_entry = _ensure_batting_entry(g, out_player_id)
        out_entry["is_out"] = True
        g.pending_new_batter = True
        if dismissal in _CREDIT_BOWLER:
            bw2 = _ensure_bowling_entry(g, bowler_id)
            bw2["wickets_taken"] = int(bw2.get("wickets_taken", 0) + 1)

    # Strike rotation rules
    swap = False
    if extra_norm is None or extra_norm == "nb":
        swap = (off_bat_runs % 2) == 1
    elif extra_norm in ("b", "lb"):
        swap = (extra_runs % 2) == 1
    elif extra_norm == "wd":
        swap = (extra_runs > 1) and (extra_runs % 2 == 1)

    if swap:
        g.current_striker_id, g.current_non_striker_id = (
            g.current_non_striker_id,
            g.current_striker_id,
        )

    if legal:
        g.balls_this_over = int(getattr(g, "balls_this_over", 0) + 1)
        if g.balls_this_over >= 6:
            g.overs_completed = int(getattr(g, "overs_completed", 0) + 1)
            g.balls_this_over = 0
            g.pending_new_over = True
            g.current_bowler_id = None
            # swap ends on over completion
            g.current_striker_id, g.current_non_striker_id = (
                g.current_non_striker_id,
                g.current_striker_id,
            )
            _complete_over_runtime(g, bowler_id)

    return {
        "over_number": delivery_over_number,
        "ball_number": delivery_ball_number,
        "bowler_id": str(bowler_id),
        "striker_id": str(pre_striker),
        "non_striker_id": str(pre_non_striker),
        "runs_off_bat": int(off_bat_runs),
        "extra_type": _as_extra_code(extra_norm),
        "extra_runs": int(extra_runs),
        "runs_scored": int(team_add),
        "is_extra": extra_norm is not None,
        "is_wicket": out_happened,
        "dismissal_type": dismissal,
        "dismissed_player_id": out_player_id if out_happened else None,
        "commentary": None,
        "fielder_id": None,
    }
