"""
Game helpers extracted from backend/main.py.

This module contains pure/impure helpers used by route handlers to build
snapshots, rebuild scorecards from the ledger, compute runtime totals, and
derive UI flags. It's a direct extraction of the functions previously living
in backend/main.py so route modules can import them without creating
circular imports.

Note: This module intentionally operates on "GameState-like" objects (ORM rows
or plain dict-like game state used by tests). It keeps the same semantics as
the originals in main.py.
"""

from __future__ import annotations

import datetime as dt
from collections import defaultdict
from collections.abc import Mapping, Sequence
from typing import Any, Literal, cast

from pydantic import BaseModel

from backend import helpers as _local_helpers  # contains overs_str_from_balls
from backend.domain.constants import (
    CREDIT_BOWLER,
)
from backend.domain.constants import (
    norm_extra as _norm_extra,  # keep public name the same
)
from backend.sql_app import models, schemas

UTC = getattr(dt, "UTC", dt.UTC)

# Local type aliases
PlayerDict = dict[str, str]
BattingEntryDict = dict[str, Any]
BowlingEntryDict = dict[str, Any]
DeliveryDict = dict[str, Any]
BallKey = tuple[int, int, int | Literal["L"]]


# -------------------------
# Normalization helpers
# -------------------------
# _norm_extra is delegated to backend.domain.constants via import above


def is_legal_delivery(extra: str | None) -> bool:
    """
    A delivery is legal if it's not a wide or no-ball.
    Uses local _norm_extra normalization.
    """
    x = _norm_extra(extra)
    return x not in {"wd", "nb"}


def _can_start_over(g: Any, bowler_id: str) -> str | None:
    """
    Validate whether a new over can start with the specified bowler.
    - Must not be mid-over.
    - New over bowler cannot be the same as the last over's last-ball bowler.
    Returns error message string or None if OK.
    """
    if (
        getattr(g, "current_over_balls", None) not in (0, None)
        or int(getattr(g, "balls_this_over", 0)) != 0
    ):
        return "Cannot start a new over while an over is in progress."
    last_id = getattr(g, "last_ball_bowler_id", None)
    if last_id and str(bowler_id) == str(last_id):
        return (
            "Selected bowler delivered the last ball of the previous over and "
            "cannot bowl consecutive overs."
        )
    return None


def _first_innings_summary(g: Any) -> dict[str, Any]:
    """
    Compact summary for innings 1: runs, wickets, overs(float), balls.
    """
    r, w, b = _runs_wkts_balls_for_innings(g, 1)
    return {
        "runs": r,
        "wickets": w,
        "overs": float(f"{b // 6}.{b % 6}"),
        "balls": b,
    }


def _complete_over_runtime(g: Any, bowler_id: str | None) -> None:
    """
    Called exactly when an over finishes (after ball 6 of the over).
    - Records who bowled the last legal ball of the finished over
    - Clears current_bowler_id to force selection for the next over
    - Resets per-over bookkeeping
    """
    if bowler_id:
        g.last_ball_bowler_id = bowler_id
    g.current_bowler_id = None
    g.current_over_balls = 0
    g.mid_over_change_used = False


def _complete_game_by_result(g: Any) -> bool:
    """
    Mutates g to completed if a result is known. Returns True if status changed.
    Applies to limited-overs with two innings.
    """
    # Already complete?
    if str(getattr(g, "status", "")).lower() == "completed" or bool(
        getattr(g, "is_game_over", False)
    ):
        return False

    # Only finalize once we're in the chase
    current_inning = int(getattr(g, "current_inning", 1) or 1)
    if current_inning < 2:
        return False

    # Ensure target is set (r1 + 1)
    _ensure_target_if_chasing(g)
    target: int | None = cast(int | None, getattr(g, "target", None))
    if target is None:
        return False

    # Live scoreboard
    current_runs: int = int(getattr(g, "total_runs", 0))
    wkts: int = int(getattr(g, "total_wickets", 0))
    overs_done: int = int(getattr(g, "overs_completed", 0))
    balls_this_over: int = int(getattr(g, "balls_this_over", 0))
    overs_limit: int = int(getattr(g, "overs_limit", 0) or 0)

    # 1) Chasing side has reached or surpassed the target â†' win by wickets
    if current_runs >= target:
        margin = max(1, 10 - wkts)
        method_typed: schemas.MatchMethod | None = cast(schemas.MatchMethod, "by wickets")
        result_text = f"{getattr(g, 'batting_team_name', '')} won by {margin} wickets"
        g.result = schemas.MatchResult(
            winner_team_name=str(getattr(g, "batting_team_name", "")),
            method=method_typed,
            margin=margin,
            result_text=result_text,
            completed_at=dt.datetime.now(UTC),
        )
        g.status = models.GameStatus.completed
        # g.is_game_over is a computed property based on status
        g.completed_at = g.result.completed_at
        return True

    # 2) If second-innings is over (all out or allocated overs exhausted), decide by runs or tie.
    all_out = wkts >= 10
    second_innings_balls_exhausted = bool(
        overs_limit and overs_done >= overs_limit and balls_this_over == 0
    )
    if all_out or second_innings_balls_exhausted:
        # target == r1 + 1, so tie when current_runs == target - 1
        if current_runs == (target - 1):
            method_typed = cast(schemas.MatchMethod, "tie")
            g.result = schemas.MatchResult(
                method=method_typed,
                margin=0,
                result_text="Match tied",
                completed_at=dt.datetime.now(UTC),
            )
            g.status = models.GameStatus.completed
            # g.is_game_over is a computed property based on status
            g.completed_at = g.result.completed_at
            return True

        # Otherwise the defending side wins by runs
        margin = max(1, (target - 1) - current_runs)
        method_typed = cast(schemas.MatchMethod, "by runs")
        result_text = f"{getattr(g, 'bowling_team_name', '')} won by {margin} runs"
        g.result = schemas.MatchResult(
            winner_team_name=str(getattr(g, "bowling_team_name", "")),
            method=method_typed,
            margin=margin,
            result_text=result_text,
            completed_at=dt.datetime.now(UTC),
        )
        g.status = models.GameStatus.completed
        # g.is_game_over is a computed property based on status
        g.completed_at = g.result.completed_at
        return True

    return False


# -------------------------
# Delivery ledger helpers
# -------------------------
def _deliveries_for_current_innings(g: Any) -> list[DeliveryDict]:
    """
    Return deliveries filtered to the current innings when 'inning' is present;
    otherwise return as-is.
    """
    raw = getattr(g, "deliveries", []) or []
    rows: list[DeliveryDict] = []
    has_innings_flag = False

    for d_any in raw:
        d = d_any.model_dump() if isinstance(d_any, BaseModel) else dict(d_any)
        if "inning" in d:
            has_innings_flag = True
        rows.append(d)

    if not has_innings_flag:
        # Legacy (no innings info anywhere): use all rows
        return rows

    cur = int(getattr(g, "current_inning", 1) or 1)
    # IMPORTANT: only include deliveries that EXPLICITLY match the current innings.
    # Treat missing 'inning' as legacy â†' inns 1, so they won't bleed into inns 2+.
    return [d for d in rows if int(d.get("inning") or 1) == cur]


def _dedup_deliveries(g: Any) -> list[DeliveryDict]:
    """
    Return a de-duplicated, ordered list of deliveries for the current innings.
    Uses key: (over_number, ball_number, subindex) where subindex separates illegal
    duplicates (wides/no-balls) from legal deliveries.
    """
    deliveries = _deliveries_for_current_innings(g)
    if not deliveries:
        return []

    seen: dict[BallKey, DeliveryDict] = {}
    order: list[BallKey] = []
    illegal_seq: dict[tuple[int, int], int] = defaultdict(int)

    for d in deliveries:
        over_no = int(d.get("over_number") or 0)
        ball_no = int(d.get("ball_number") or 0)
        x = _norm_extra(d.get("extra_type"))

        k: BallKey
        if x in ("wd", "nb"):
            k = (over_no, ball_no, illegal_seq[(over_no, ball_no)])
            illegal_seq[(over_no, ball_no)] += 1
        else:
            k = (over_no, ball_no, cast(Literal["L"], "L"))  # legal

        if k not in seen:
            order.append(k)
        seen[k] = d

    return [seen[k] for k in order]


def _legal_balls_count(g: Any) -> int:
    """Count legal deliveries (excludes wides/no-balls) across the *current innings*."""
    cnt = 0
    for d in _dedup_deliveries(g):
        x = _norm_extra(d.get("extra_type"))
        if x not in ("wd", "nb"):
            cnt += 1
    return cnt


def _overs_string_from_ledger(g: Any) -> str:
    balls = _legal_balls_count(g)
    return f"{balls // 6}.{balls % 6}"


# -------------------------
# Player / lookup helpers
# -------------------------
def _player_name(
    team_a: Mapping[str, Any], team_b: Mapping[str, Any], pid: str | None
) -> str | None:
    """Lookup player name by id across both teams."""
    if not pid:
        return None
    for team in (team_a, team_b):
        for p in team.get("players", []) or []:
            if p.get("id") == pid:
                return p.get("name")
    return None


def _player_team_name(
    team_a: Mapping[str, Any], team_b: Mapping[str, Any], pid: str | None
) -> str | None:
    if not pid:
        return None
    for team in (team_a, team_b):
        for p in team.get("players", []) or []:
            if p.get("id") == pid:
                return team.get("name")
    return None


def _id_by_name(
    team_a: Mapping[str, Any], team_b: Mapping[str, Any], name: str | None
) -> str | None:
    if not name:
        return None
    n = name.strip().lower()
    for team in (team_a, team_b):
        for p in team.get("players", []) or []:
            if p.get("name", "").strip().lower() == n:
                return p.get("id")
    return None


# -------------------------
# Scorecard builders
# -------------------------
def _mk_batting_scorecard(team: Mapping[str, Any]) -> dict[str, BattingEntryDict]:
    return {
        p["id"]: {
            "player_id": p["id"],
            "player_name": p["name"],
            "runs": 0,
            "balls_faced": 0,
            "is_out": False,
            "fours": 0,
            "sixes": 0,
            "how_out": "",
        }
        for p in team.get("players", [])
    }


def _mk_bowling_scorecard(team: Mapping[str, Any]) -> dict[str, BowlingEntryDict]:
    return {
        p["id"]: {
            "player_id": p["id"],
            "player_name": p["name"],
            "overs_bowled": 0.0,
            "runs_conceded": 0,
            "wickets_taken": 0,
        }
        for p in team.get("players", [])
    }


def _ensure_batting_entry(g: Any, batter_id: str) -> BattingEntryDict:
    e_any: Any = (getattr(g, "batting_scorecard", {}) or {}).get(batter_id)
    if isinstance(e_any, BaseModel):
        e: BattingEntryDict = cast(BattingEntryDict, e_any.model_dump())
    elif isinstance(e_any, dict):
        e = cast(BattingEntryDict, {**e_any})
    else:
        e = {
            "player_id": batter_id,
            "player_name": _player_name(g.team_a, g.team_b, batter_id) or "",
            "runs": 0,
            "balls_faced": 0,
            "is_out": False,
            "fours": 0,
            "sixes": 0,
            "how_out": "",
        }

    # ensure keys
    e.setdefault("player_id", batter_id)
    e.setdefault("player_name", _player_name(g.team_a, g.team_b, batter_id) or "")
    e.setdefault("runs", 0)
    e.setdefault("balls_faced", 0)
    e.setdefault("is_out", False)
    e.setdefault("fours", 0)
    e.setdefault("sixes", 0)
    e.setdefault("how_out", "")

    # mutate game scorecard
    bsc = getattr(g, "batting_scorecard", {}) or {}
    bsc[batter_id] = e
    g.batting_scorecard = bsc
    return e


def _ensure_bowling_entry(g: Any, bowler_id: str) -> BowlingEntryDict:
    e_any: Any = (getattr(g, "bowling_scorecard", {}) or {}).get(bowler_id)
    if isinstance(e_any, BaseModel):
        e: BowlingEntryDict = cast(BowlingEntryDict, e_any.model_dump())
    elif isinstance(e_any, dict):
        e = cast(BowlingEntryDict, {**e_any})
    else:
        e = {
            "player_id": bowler_id,
            "player_name": _player_name(g.team_a, g.team_b, bowler_id) or "",
            "overs_bowled": 0.0,
            "runs_conceded": 0,
            "wickets_taken": 0,
        }

    e.setdefault("player_id", bowler_id)
    e.setdefault("player_name", _player_name(g.team_a, g.team_b, bowler_id) or "")
    e.setdefault("overs_bowled", 0.0)
    e.setdefault("runs_conceded", 0)
    e.setdefault("wickets_taken", 0)

    bosc = getattr(g, "bowling_scorecard", {}) or {}
    bosc[bowler_id] = e
    g.bowling_scorecard = bosc
    return e


def _bowling_balls_to_overs(balls: int) -> float:
    overs = balls // 6
    rem = balls % 6
    return overs + rem / 10.0


# -------------------------
# Rebuild scorecards & totals from ledger
# -------------------------
def _rebuild_scorecards_from_deliveries(g: Any) -> None:
    deliveries = _dedup_deliveries(g)

    inferred_team_name: str | None = None
    for d in deliveries:
        for key in ("striker_id", "non_striker_id", "dismissed_player_id"):
            team_name = _player_team_name(g.team_a, g.team_b, d.get(key))
            if team_name:
                inferred_team_name = team_name
                break
        if inferred_team_name:
            break

    if inferred_team_name and inferred_team_name != g.batting_team_name:
        g.batting_team_name = inferred_team_name
        if inferred_team_name == g.team_a["name"]:
            g.bowling_team_name = g.team_b["name"]
        elif inferred_team_name == g.team_b["name"]:
            g.bowling_team_name = g.team_a["name"]

    batting_team = g.team_a if g.batting_team_name == g.team_a["name"] else g.team_b
    bowling_team = g.team_b if batting_team is g.team_a else g.team_a

    bat = _mk_batting_scorecard(batting_team)
    bowl = _mk_bowling_scorecard(bowling_team)

    def ensure_batter(pid: str | None) -> str | None:
        if not pid:
            return None
        pid_str = str(pid)
        if not pid_str:
            return None
        if _player_team_name(g.team_a, g.team_b, pid_str) not in {
            None,
            g.batting_team_name,
        }:
            return None
        if pid_str not in bat:
            bat[pid_str] = {
                "player_id": pid_str,
                "player_name": _player_name(g.team_a, g.team_b, pid_str) or "",
                "runs": 0,
                "balls_faced": 0,
                "is_out": False,
                "fours": 0,
                "sixes": 0,
                "how_out": "",
            }
        return pid_str

    def ensure_bowler(pid: str | None) -> str | None:
        if not pid:
            return None
        pid_str = str(pid)
        if not pid_str:
            return None
        if _player_team_name(g.team_a, g.team_b, pid_str) not in {
            None,
            g.bowling_team_name,
        }:
            return None
        if pid_str not in bowl:
            bowl[pid_str] = {
                "player_id": pid_str,
                "player_name": _player_name(g.team_a, g.team_b, pid_str) or "",
                "overs_bowled": 0.0,
                "runs_conceded": 0,
                "wickets_taken": 0,
            }
        return pid_str

    balls_by_bowler: dict[str, int] = defaultdict(int)

    for d in deliveries:
        striker = ensure_batter(d.get("striker_id"))
        bowler = ensure_bowler(d.get("bowler_id"))
        x = _norm_extra(d.get("extra_type"))
        off = int(d.get("runs_off_bat") or 0)
        ex = int(d.get("extra_runs") or 0)
        wicket = bool(d.get("is_wicket"))
        dismissal_type = (d.get("dismissal_type") or "").strip().lower() or None

        if striker and striker in bat:
            if x not in ("wd", "nb"):
                bat[striker]["balls_faced"] += 1
            bat[striker]["runs"] += off
            if off == 4:
                bat[striker]["fours"] = int(bat[striker].get("fours", 0)) + 1
            if off == 6:
                bat[striker]["sixes"] = int(bat[striker].get("sixes", 0)) + 1

        if wicket and dismissal_type:
            dismissed_raw = d.get("dismissed_player_id") or striker
            out_pid = ensure_batter(dismissed_raw)
            if out_pid and out_pid in bat:
                bat[out_pid]["is_out"] = True
                fld = _player_name(g.team_a, g.team_b, d.get("fielder_id")) or ""
                blr = _player_name(g.team_a, g.team_b, bowler) or ""
                if dismissal_type == "caught":
                    bat[out_pid]["how_out"] = f"c {fld} b {blr}".strip()
                elif dismissal_type == "lbw":
                    bat[out_pid]["how_out"] = f"lbw b {blr}".strip()
                elif dismissal_type == "bowled":
                    bat[out_pid]["how_out"] = f"b {blr}".strip()
                elif dismissal_type == "stumped":
                    bat[out_pid]["how_out"] = f"st {fld} b {blr}".strip()
                elif dismissal_type == "run_out":
                    bat[out_pid]["how_out"] = f"run out ({fld})".strip()
                else:
                    bat[out_pid]["how_out"] = dismissal_type

        if bowler and bowler in bowl:
            if x not in ("wd", "nb"):
                balls_by_bowler[bowler] += 1
            if x == "wd":
                bowl[bowler]["runs_conceded"] += max(1, ex or 1)
            elif x == "nb":
                bowl[bowler]["runs_conceded"] += 1 + off
            elif x is None:
                bowl[bowler]["runs_conceded"] += off
            if wicket and dismissal_type in CREDIT_BOWLER:
                bowl[bowler]["wickets_taken"] += 1

    for bid, balls in balls_by_bowler.items():
        bowl[bid]["balls_bowled"] = int(balls)
        bowl[bid]["overs_bowled_str"] = _local_helpers.overs_str_from_balls(int(balls))
        bowl[bid]["overs_bowled"] = _bowling_balls_to_overs(int(balls))

    g.batting_scorecard = bat
    g.bowling_scorecard = bowl


# -------------------------
# Totals recompute (idempotent)
# -------------------------
def _recompute_totals_and_runtime(g: Any) -> None:
    """
    Recompute totals and runtime-only fields from the deliveries ledger,
    without assuming the ORM instance already has runtime attributes.
    This function is idempotent and safe on a bare models.Game row.
    """
    # ---- Ensure required runtime attributes exist (for legacy rows) ----
    if not hasattr(g, "total_runs"):
        g.total_runs = 0
    if not hasattr(g, "total_wickets"):
        g.total_wickets = 0
    if not hasattr(g, "overs_completed"):
        g.overs_completed = 0
    if not hasattr(g, "balls_this_over"):
        g.balls_this_over = 0
    if not hasattr(g, "current_over_balls"):
        g.current_over_balls = 0
    if not hasattr(g, "mid_over_change_used"):
        g.mid_over_change_used = False
    if not hasattr(g, "current_bowler_id"):
        g.current_bowler_id = None
    if not hasattr(g, "last_ball_bowler_id"):
        g.last_ball_bowler_id = None
    if not hasattr(g, "balls_bowled_total"):
        g.balls_bowled_total = 0

    preselected_bowler: str | None = getattr(g, "current_bowler_id", None)

    total_runs: int = 0
    total_wkts: int = 0
    legal_balls: int = 0
    cur_over_bowler: str | None = None
    last_legal_bowler: str | None = None

    for d in _dedup_deliveries(g):
        x = _norm_extra(d.get("extra_type"))
        off = int(d.get("runs_off_bat") or 0)
        ex = int(d.get("extra_runs") or 0)

        if x == "wd":
            total_runs += max(1, ex or 1)
        elif x == "nb":
            total_runs += 1 + off
        elif x in ("b", "lb"):
            total_runs += ex
            legal_balls += 1
            cur_over_bowler = d.get("bowler_id")
            last_legal_bowler = cur_over_bowler
        else:
            total_runs += off
            legal_balls += 1
            cur_over_bowler = d.get("bowler_id")
            last_legal_bowler = cur_over_bowler

        if d.get("is_wicket") and (d.get("dismissal_type") or "").strip():
            total_wkts += 1

    g.overs_completed = legal_balls // 6
    g.balls_this_over = legal_balls % 6
    g.current_over_balls = g.balls_this_over
    g.balls_bowled_total = legal_balls

    g.total_runs = total_runs
    g.total_wickets = total_wkts

    g.last_ball_bowler_id = last_legal_bowler

    if g.balls_this_over > 0:
        g.current_bowler_id = getattr(g, "current_bowler_id", None) or cur_over_bowler
    else:
        if legal_balls > 0 and str(preselected_bowler or "") == str(last_legal_bowler or ""):
            g.current_bowler_id = None
        else:
            g.current_bowler_id = preselected_bowler


# -------------------------
# Analyst & UI helpers
# -------------------------
def _extras_breakdown(g: Any) -> dict[str, int]:
    wides = no_balls = byes = leg_byes = penalty = 0

    for d in _dedup_deliveries(g):
        x = _norm_extra(d.get("extra_type"))
        ex = int(d.get("extra_runs") or 0)

        if x == "wd":
            wides += max(1, ex or 1)
        elif x == "nb":
            no_balls += 1
        elif x == "b":
            byes += ex
        elif x == "lb":
            leg_byes += ex

    total = wides + no_balls + byes + leg_byes + penalty
    return {
        "wides": wides,
        "no_balls": no_balls,
        "byes": byes,
        "leg_byes": leg_byes,
        "penalty": penalty,
        "total": total,
    }


def _fall_of_wickets(g: Any) -> list[dict[str, Any]]:
    fow: list[dict[str, Any]] = []
    cum = 0
    for d in _dedup_deliveries(g):
        cum += int(d.get("runs_scored") or 0)

        is_out = bool(d.get("is_wicket"))
        dismissal = (d.get("dismissal_type") or "").strip().lower() or None
        if not (is_out and dismissal):
            continue

        over_no = int(d.get("over_number") or 0)
        ball_no = int(d.get("ball_number") or 0)
        out_pid = str(d.get("dismissed_player_id") or d.get("striker_id") or "")

        fow.append(
            {
                "score": cum,
                "wicket": len(fow) + 1,
                "batter_id": out_pid,
                "batter_name": _player_name(g.team_a, g.team_b, out_pid) or "",
                "over": f"{over_no}.{ball_no}",
                "dismissal_type": dismissal,
                "bowler_id": d.get("bowler_id"),
                "bowler_name": _player_name(g.team_a, g.team_b, d.get("bowler_id")),
                "fielder_id": d.get("fielder_id"),
                "fielder_name": _player_name(g.team_a, g.team_b, d.get("fielder_id")),
            }
        )
    return fow


def _compute_snapshot_flags(g: Any) -> dict[str, bool]:
    """Return UI gating flags derived from current runtime state."""
    need_new_batter = False
    if getattr(g, "current_striker_id", None):
        e = g.batting_scorecard.get(g.current_striker_id) or {}
        if isinstance(e, BaseModel):
            e = e.model_dump()
        need_new_batter = bool(e.get("is_out", False))
    if not need_new_batter and getattr(g, "current_non_striker_id", None):
        e2 = g.batting_scorecard.get(g.current_non_striker_id) or {}
        if isinstance(e2, BaseModel):
            e2 = e2.model_dump()
        need_new_batter = bool(e2.get("is_out", False))

    have_any_balls = len(_dedup_deliveries(g)) > 0

    need_new_over = bool(
        getattr(g, "balls_this_over", 0) == 0
        and have_any_balls
        and not getattr(g, "current_bowler_id", None)
    )

    return {"needs_new_batter": need_new_batter, "needs_new_over": need_new_over}


def _mini_batting_card(g: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    bsc = getattr(g, "batting_scorecard", {}) or {}
    for _pid, e in bsc.items():
        balls = int(e.get("balls_faced", 0))
        was_out = bool(e.get("is_out", False))
        if balls == 0 and not was_out:
            continue
        row: dict[str, Any] = {
            "name": e.get("player_name", ""),
            "runs": int(e.get("runs", 0)),
            "balls": balls,
            "status": "out" if was_out else "not out",
        }
        out.append(row)

    last_dismiss_for: dict[str, dict[str, str | None]] = {}
    for d in _dedup_deliveries(g):
        if d.get("is_wicket") and d.get("dismissed_player_id"):
            last_dismiss_for[str(d["dismissed_player_id"])] = {
                "type": d.get("dismissal_type"),
                "bowler": _player_name(g.team_a, g.team_b, d.get("bowler_id")) or "",
                "fielder": _player_name(g.team_a, g.team_b, d.get("fielder_id")) or "",
            }

    pid_by_name = {e.get("player_name"): pid for pid, e in bsc.items()}
    for row in out:
        pid = pid_by_name.get(row["name"])
        if pid and pid in last_dismiss_for:
            row["dismissal"] = last_dismiss_for[pid]
    return out


def _mini_bowling_card(g: Any) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    bosc = getattr(g, "bowling_scorecard", {}) or {}
    for _pid, e in bosc.items():
        overs = float(e.get("overs_bowled", 0.0))
        if overs <= 0.0:
            continue
        out.append(
            {
                "name": e.get("player_name", ""),
                "overs": overs,
                "runs": int(e.get("runs_conceded", 0)),
                "wkts": int(e.get("wickets_taken", 0)),
            }
        )
    return out


def _ensure_target_if_chasing(g: Any) -> None:
    if int(getattr(g, "current_inning", 1)) >= 2 and getattr(g, "target", None) is None:
        r1, _w1, _b1 = _runs_wkts_balls_for_innings(g, 1)
        g.target = r1 + 1


def _runs_wkts_balls_for_innings(g: Any, inning: int) -> tuple[int, int, int]:
    runs: int = 0
    wkts: int = 0
    balls: int = 0

    ledger: Sequence[Mapping[str, Any]] = cast(Sequence[Mapping[str, Any]], (g.deliveries or []))

    for d in ledger:
        if int(d.get("inning", 1) or 1) != int(inning):
            continue

        runs += int(d.get("runs_scored") or 0)
        if bool(d.get("is_wicket")):
            wkts += 1

        extra: str | None = cast(str | None, d.get("extra_type"))
        if extra is None or extra not in {"wd", "nb"}:
            balls += 1

    return runs, wkts, balls


def _maybe_finalize_match(g: Any) -> None:
    """
    Decide completion after each delivery in innings 2, or when overs end, etc.
    Sets g.status='completed' and g.result (winner/method) where possible.
    """
    inning = int(getattr(g, "current_inning", 1))
    if inning < 2:
        return  # only finalize during/after chase

    _ensure_target_if_chasing(g)
    target = getattr(g, "target", None)

    r1, _w1, _b1 = _runs_wkts_balls_for_innings(g, 1)
    r2, w2, b2 = _runs_wkts_balls_for_innings(g, 2)

    overs_limit = getattr(g, "overs_limit", None)
    balls_limit = overs_limit * 6 if overs_limit else None

    def _team_name_from_json(team_obj: Any) -> str | None:
        if isinstance(team_obj, Mapping):
            name = team_obj.get("name")
            if isinstance(name, str) and name:
                return name
        return None

    team_a_name = _team_name_from_json(getattr(g, "team_a", {}))
    team_b_name = _team_name_from_json(getattr(g, "team_b", {}))

    batting_name = getattr(g, "batting_team_name", None)
    if not batting_name:
        batting_name = getattr(g, "batting_team_name", None)
        if not batting_name:
            batting_name = (
                team_b_name if inning >= 2 and team_b_name else team_a_name or team_b_name
            )

    bowling_name = getattr(g, "bowling_team_name", None)
    if not bowling_name:
        if batting_name and team_a_name and team_b_name:
            bowling_name = team_b_name if batting_name == team_a_name else team_a_name
        else:
            bowling_name = team_b_name or team_a_name

    chasing_done: bool = False
    method: schemas.MatchMethod | None = None
    margin: int | None = None
    winner_name: str | None = None

    if target is not None:
        if r2 >= target:
            chasing_done = True
            method = schemas.MatchMethod.by_wickets
            margin = max(1, 10 - w2)
            winner_name = batting_name  # batting in 2nd = chaser
        else:
            balls_exhausted = balls_limit is not None and b2 >= balls_limit
            all_out = w2 >= 10
            if balls_exhausted or all_out:
                chasing_done = True
                if r1 > r2:
                    method = schemas.MatchMethod.by_runs
                    margin = r1 - r2
                    winner_name = bowling_name
                elif r1 == r2:
                    method = schemas.MatchMethod.tie
                    margin = 0
                    winner_name = None
                else:
                    method = schemas.MatchMethod.by_wickets
                    margin = max(1, 10 - w2)
                    winner_name = batting_name

    if chasing_done:
        if getattr(g, "first_inning_summary", None) is None:
            g.first_inning_summary = {
                "runs": r1,
                "wickets": _w1,
                "overs": float(f"{_b1 // 6}.{_b1 % 6}"),
                "balls": _b1,
            }

        margin_i = max(0, int(margin or 0))
        if method == schemas.MatchMethod.by_wickets and not winner_name:
            winner_name = batting_name or bowling_name
        if method == schemas.MatchMethod.by_runs and not winner_name:
            winner_name = bowling_name or batting_name

        if method == schemas.MatchMethod.tie:
            result_text = "Match tied"
        elif method == schemas.MatchMethod.by_wickets and winner_name:
            if margin_i <= 0:
                margin_i = 1
            result_text = f"{winner_name} won by {margin_i} wickets"
        elif method == schemas.MatchMethod.by_runs and winner_name:
            result_text = f"{winner_name} won by {margin_i} runs"
        else:
            result_text = "Match completed"

        g.result = schemas.MatchResult(
            winner_team_name=winner_name,
            method=method,
            margin=margin_i,
            result_text=result_text,
            completed_at=dt.datetime.now(UTC),
        )
        g.status = models.GameStatus.completed
        # g.is_game_over is a computed property based on status
        g.completed_at = g.result.completed_at
