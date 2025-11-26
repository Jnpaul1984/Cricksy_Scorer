"""
Snapshot builder service for Cricksy Scorer.

This module provides a single exported function:

    build_snapshot(
        g: GameState,
        last_delivery: Optional[Union[schemas.Delivery, Dict[str, Any]]],
    ) -> Dict[str, Any]

It re-implements the snapshot assembly logic currently in backend/main.py so it can be moved
out of the giant main module. It intentionally only depends on the runtime game object (ORM
row / GameState-like object) and a small set of helpers implemented here to avoid circular imports.

Notes:
- This is an incremental refactor: many helpers are copied/adapted from backend/main.py to keep
  the snapshot implementation self-contained. Later phases can deduplicate helpers into a
  shared helpers/scoring module.
"""

from __future__ import annotations

import datetime as dt
import json
import typing as t
from collections import defaultdict
from collections.abc import Mapping
from pathlib import Path
from typing import TYPE_CHECKING, Any, Literal, cast

from pydantic import BaseModel

from backend import dls as dlsmod
from backend.sql_app import models, schemas

UTC = getattr(dt, "UTC", dt.UTC)


if TYPE_CHECKING:
    from backend.main import GameState  # type: ignore
else:
    GameState = Any  # type: ignore


# -----------------------
# Local helper functions
# -----------------------
def _to_dict(x: Any) -> dict[str, Any] | None:
    """Normalize a value that may be a dict or a Pydantic model to a plain dict[str,Any]."""
    if x is None:
        return None
    if isinstance(x, dict):
        return {str(k): v for k, v in x.items()}
    if isinstance(x, BaseModel):
        try:
            return {str(k): v for k, v in cast(Mapping[str, Any], x.model_dump()).items()}
        except Exception:
            try:
                md = x.dict()  # type: ignore[attr-defined]
                return {str(k): v for k, v in md.items()}
            except Exception:
                return None
    # duck-type
    md_fn = getattr(x, "model_dump", None) or getattr(x, "dict", None)
    if callable(md_fn):
        try:
            md = md_fn()
            if isinstance(md, dict):
                return {str(k): v for k, v in md.items()}
        except Exception:
            return None
    return None


def _norm_extra(x: Any) -> str | None:
    """Normalize to canonical extra codes: None|'wd'|'nb'|'b'|'lb'."""
    if not x:
        return None
    s = (str(x) or "").strip().lower()
    if s in {"wide", "wd"}:
        return "wd"
    if s in {"no_ball", "nb"}:
        return "nb"
    if s in {"b", "bye"}:
        return "b"
    if s in {"lb", "leg_bye", "leg-bye"}:
        return "lb"
    return None


def is_legal_delivery(extra: str | None) -> bool:
    return extra not in {"wd", "nb"}


def _deliveries_for_current_innings(g: GameState) -> list[dict[str, Any]]:
    """
    Return deliveries filtered to the current innings.
    When 'inning' is present; otherwise return as-is.
    Mirrors the behaviour in backend/main._deliveries_for_current_innings.
    """
    raw = getattr(g, "deliveries", []) or []
    rows: list[dict[str, Any]] = []
    has_innings_flag = False

    for d_any in raw:
        d = _to_dict(d_any)
        if d is None:
            continue
        if "inning" in d:
            has_innings_flag = True
        rows.append(d)

    if not has_innings_flag:
        return rows

    cur = int(getattr(g, "current_inning", 1) or 1)
    return [d for d in rows if int(d.get("inning", 1) or 1) == cur]


def _deliveries_for_innings(g: GameState, innings_number: int) -> list[dict[str, Any]]:
    """Return deliveries filtered to a specific innings number."""
    raw = getattr(g, "deliveries", []) or []
    rows: list[dict[str, Any]] = []

    for d_any in raw:
        d = _to_dict(d_any)
        if d is None:
            continue
        if int(d.get("inning", 1) or 1) == innings_number:
            rows.append(d)

    return rows


def _build_innings_breakdown(g: GameState) -> list[dict[str, Any]]:
    """Build innings breakdown with runs, wickets, overs for each completed/current innings."""
    innings_list: list[dict[str, Any]] = []
    current_inning = int(getattr(g, "current_inning", 1) or 1)

    # Build innings 1
    if current_inning >= 1:
        innings_1_deliveries = _deliveries_for_innings(g, 1)
        runs_1 = sum(int(d.get("runs_scored", 0) or 0) for d in innings_1_deliveries)
        wickets_1 = sum(1 for d in innings_1_deliveries if d.get("is_wicket"))
        legal_balls_1 = sum(
            1 for d in innings_1_deliveries if is_legal_delivery(_norm_extra(d.get("extra_type")))
        )
        overs_1 = legal_balls_1 // 6
        balls_1 = legal_balls_1 % 6

        team_a_name = getattr(g, "team_a", {}).get("name")
        team_b_name = getattr(g, "team_b", {}).get("name")
        toss_winner = getattr(g, "toss_winner_team", None)
        decision = getattr(g, "decision", None)

        batting_team_1 = (
            team_a_name if toss_winner == team_a_name and decision == "bat" else team_b_name
        )

        innings_list.append(
            {
                "innings_number": 1,
                "batting_team": batting_team_1,
                "runs": runs_1,
                "wickets": wickets_1,
                "overs": float(f"{overs_1}.{balls_1}"),
                "balls": legal_balls_1,
            }
        )

    # Build innings 2 if in progress or completed
    if current_inning >= 2:
        innings_2_deliveries = _deliveries_for_innings(g, 2)
        runs_2 = sum(int(d.get("runs_scored", 0) or 0) for d in innings_2_deliveries)
        wickets_2 = sum(1 for d in innings_2_deliveries if d.get("is_wicket"))
        legal_balls_2 = sum(
            1 for d in innings_2_deliveries if is_legal_delivery(_norm_extra(d.get("extra_type")))
        )
        overs_2 = legal_balls_2 // 6
        balls_2 = legal_balls_2 % 6

        # Re-fetch names in case they weren't set in block 1 (though they should be)
        team_a_name = getattr(g, "team_a", {}).get("name")
        team_b_name = getattr(g, "team_b", {}).get("name")
        toss_winner = getattr(g, "toss_winner_team", None)
        decision = getattr(g, "decision", None)

        batting_team_2 = (
            team_b_name if toss_winner == team_a_name and decision == "bat" else team_a_name
        )

        innings_list.append(
            {
                "innings_number": 2,
                "batting_team": batting_team_2,
                "runs": runs_2,
                "wickets": wickets_2,
                "overs": float(f"{overs_2}.{balls_2}"),
                "balls": legal_balls_2,
            }
        )

    return innings_list


# Dedup key: (over, ball, subindex) where subindex is int for illegal (wd/nb) or "L" for legal.

BallKey = tuple[int, int, int | t.Literal["L"]]


def _dedup_deliveries(g: GameState) -> list[dict[str, Any]]:
    deliveries = _deliveries_for_current_innings(g)
    if not deliveries:
        return []

    seen: dict[BallKey, dict[str, Any]] = {}
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
            k = (over_no, ball_no, cast(t.Literal["L"], "L"))  # legal

        if k not in seen:
            order.append(k)
        seen[k] = d

    return [seen[k] for k in order]


def _player_name(
    team_a: Mapping[str, Any], team_b: Mapping[str, Any], pid: str | None
) -> str | None:
    """Lookup player name by id across both teams."""
    if not pid:
        return None
    for team in (team_a, team_b):
        for p in team.get("players", []) or []:
            try:
                if p.get("id") == pid:
                    return p.get("name")
            except Exception:
                continue
    return None


def _bat_entry(g: GameState, pid: str | None) -> dict[str, Any]:
    """
    Return batting entry dict for pid (works with BaseModel
    or dict stored on g.batting_scorecard).
    """
    if not pid:
        return {
            "player_id": "",
            "player_name": "",
            "runs": 0,
            "balls_faced": 0,
            "is_out": False,
        }
    bsc = getattr(g, "batting_scorecard", {}) or {}
    e_any = bsc.get(pid)
    if isinstance(e_any, BaseModel):
        try:
            return cast(dict[str, Any], e_any.model_dump())
        except Exception:
            try:
                return cast(dict[str, Any], e_any.dict())  # type: ignore[attr-defined]
            except Exception:
                pass
    if isinstance(e_any, dict):
        return cast(dict[str, Any], e_any)
    # fallback
    return {
        "player_id": pid,
        "player_name": _player_name(g.team_a, g.team_b, pid) or "",
        "runs": 0,
        "balls_faced": 0,
        "is_out": False,
    }


def _compute_snapshot_flags(g: GameState) -> dict[str, bool]:
    """
    Return UI gating flags derived from current runtime state
    (needs_new_batter / needs_new_over).
    """
    need_new_batter = False
    if getattr(g, "current_striker_id", None):
        e = (getattr(g, "batting_scorecard", {}) or {}).get(g.current_striker_id)
        if isinstance(e, BaseModel):
            e = e.model_dump()
        if isinstance(e, dict):
            need_new_batter = bool(e.get("is_out", False))
    if not need_new_batter and getattr(g, "current_non_striker_id", None):
        e2 = (getattr(g, "batting_scorecard", {}) or {}).get(g.current_non_striker_id)
        if isinstance(e2, BaseModel):
            e2 = e2.model_dump()
        if isinstance(e2, dict):
            need_new_batter = bool(e2.get("is_out", False))

    have_any_balls = len(_dedup_deliveries(g)) > 0

    need_new_over = bool(
        getattr(g, "balls_this_over", 0) == 0
        and have_any_balls
        and not getattr(g, "current_bowler_id", None)
    )

    # Safety check: if we are at the end of an over (balls=0) and the current bowler
    # is the same as the last bowler, it means we haven't selected a new bowler yet.
    # This handles cases where the runtime state might not have cleared the bowler ID.
    cur_bowler = getattr(g, "current_bowler_id", None)
    last_bowler = getattr(g, "last_ball_bowler_id", None)
    if (
        getattr(g, "balls_this_over", 0) == 0
        and have_any_balls
        and cur_bowler
        and str(cur_bowler) == str(last_bowler)
    ):
        need_new_over = True

    return {"needs_new_batter": need_new_batter, "needs_new_over": need_new_over}


def _is_game_in_progress(status: object | None) -> bool:
    if isinstance(status, models.GameStatus):
        return status == models.GameStatus.in_progress
    if status is None:
        return False
    return str(status).lower() == models.GameStatus.in_progress.value


def _safe_int(value: object | None) -> int:
    if value is None:
        return 0
    if isinstance(value, (int, float, str)):
        try:
            return int(value)
        except Exception:
            return 0
    return 0


def _extras_breakdown(g: GameState) -> dict[str, int]:
    wides = no_balls = byes = leg_byes = penalty = 0
    for d in _dedup_deliveries(g):
        x = _norm_extra(d.get("extra_type"))
        ex = _safe_int(d.get("extra_runs"))
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


def _fall_of_wickets(g: GameState) -> list[dict[str, Any]]:
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


def _dls_panel_for(g: GameState, base_dir: str | Path | None = None) -> dict[str, Any]:
    """Best-effort DLS panel. Returns {} when not applicable."""
    try:
        if not getattr(g, "dls_enabled", False):
            return {}
        overs_limit_opt = cast(int | None, getattr(g, "overs_limit", None))
        if overs_limit_opt not in (20, 50):
            return {}
        kind = "odi" if overs_limit_opt == 50 else "t20"
        assert kind in ("odi", "t20")
        # Use provided base_dir if present, otherwise fall back to current working dir string
        base_dir_str = str(base_dir) if base_dir is not None else ""
        env = dlsmod.load_env(cast(Literal["odi", "t20"], kind), base_dir_str)

        deliveries_m: list[Mapping[str, Any]] = cast(
            list[Mapping[str, Any]], list(getattr(g, "deliveries", []))
        )
        interruptions = list(getattr(g, "interruptions", []))
        R1_total = dlsmod.total_resources_team1(
            env=env,
            max_overs_initial=int(overs_limit_opt),
            deliveries=deliveries_m,
            interruptions=interruptions,
        )

        S1 = 0
        # prefer a persisted first_inning_summary, otherwise compute from ledger (best-effort)
        fis_any = getattr(g, "first_inning_summary", None)
        if isinstance(fis_any, dict) and "runs" in fis_any:
            try:
                S1 = int(fis_any.get("runs", 0))
            except Exception:
                S1 = 0
        else:
            # naive: sum deliveries in innings 1
            S1 = sum(
                int(d.get("runs_scored") or 0)
                for d in list(getattr(g, "deliveries", []) or [])
                if int(d.get("inning", 1) or 1) == 1
            )

        R_start = env.table.R(float(overs_limit_opt), 0)
        overs_completed = float(getattr(g, "overs_completed", 0) or 0)
        balls_this_over = float(getattr(g, "balls_this_over", 0) or 0)
        wkts_now = int(getattr(g, "total_wickets", 0) or 0)
        team2_overs_left_now = max(
            0.0, float(overs_limit_opt) - (overs_completed + (balls_this_over / 6.0))
        )
        R_remaining = env.table.R(team2_overs_left_now, wkts_now)
        R2_used = max(0.0, R_start - R_remaining)

        target_full = int(dlsmod.revised_target(S1=S1, R1_total=R1_total, R2_total=R_start))
        par_now = int(dlsmod.par_score_now(S1=S1, R1_total=R1_total, R2_used_so_far=R2_used))
        panel: dict[str, Any] = {"method": "DLS", "target": target_full, "par": par_now}
        if int(getattr(g, "current_inning", 1) or 1) >= 2:
            runs_now = int(getattr(g, "total_runs", 0))
            panel["ahead_by"] = runs_now - par_now
        return panel
    except Exception:
        return {}


# -----------------------
# Public API
# -----------------------
def build_snapshot(
    g: GameState,
    last_delivery: schemas.Delivery | dict[str, Any] | None,
    base_dir: str | Path | None = None,
) -> dict[str, Any]:
    """
    Build a snapshot dict suitable for the API from a GameState-like object g.
    This mirrors backend/main._snapshot_from_game but is implemented here so main.py
    can delegate to this service.
    """

    # Prepare last_delivery dict
    if last_delivery is None:
        last_delivery_out = None
    elif isinstance(last_delivery, BaseModel):
        last_delivery_out = cast(dict[str, Any], last_delivery.model_dump())
    else:
        last_delivery_out = cast(dict[str, Any], last_delivery)

    if last_delivery_out is None:
        dl = _dedup_deliveries(g)
        last_delivery_out = dl[-1] if dl else None

    # locate current bowler if not set and we have a ball in progress
    cur_bowler_id: str | None = getattr(g, "current_bowler_id", None)
    if not cur_bowler_id and int(getattr(g, "balls_this_over", 0) or 0) > 0:
        for d in reversed(_dedup_deliveries(g)):
            if is_legal_delivery(_norm_extra(d.get("extra_type"))):
                cur_bowler_id = str(d.get("bowler_id") or "")
                break

    is_break = str(getattr(g, "status", "")).lower() == "innings_break"
    flags = _compute_snapshot_flags(g)
    needs_new_over = False if is_break else flags["needs_new_over"]
    needs_new_batter = flags["needs_new_batter"]
    needs_new_innings = bool(getattr(g, "needs_new_innings", False) or is_break)

    overs_limit_val = _safe_int(getattr(g, "overs_limit", None))
    overs_completed = _safe_int(getattr(g, "overs_completed", 0))
    balls_this_over = _safe_int(getattr(g, "balls_this_over", 0))
    balls_bowled_total_raw = _safe_int(getattr(g, "balls_bowled_total", None))
    balls_bowled = balls_bowled_total_raw or (overs_completed * 6 + balls_this_over)
    balls_limit = overs_limit_val * 6
    all_out = _safe_int(getattr(g, "total_wickets", 0)) >= 10
    overs_exhausted = balls_limit > 0 and balls_bowled >= balls_limit
    status_in_progress = _is_game_in_progress(getattr(g, "status", None))
    current_inning_no = getattr(g, "current_inning", None)
    current_over_exists = (
        getattr(g, "overs_completed", None) is not None
        or getattr(g, "balls_this_over", None) is not None
    )
    current_striker_id = getattr(g, "current_striker_id", None)
    current_non_striker_id = getattr(g, "current_non_striker_id", None)
    can_score = bool(
        status_in_progress
        and current_inning_no is not None
        and current_striker_id is not None
        and current_non_striker_id is not None
        and current_over_exists
        and cur_bowler_id is not None
        and not overs_exhausted
        and not all_out
        and not needs_new_over
        and not needs_new_innings
    )

    extras_totals = _extras_breakdown(g)
    fall_of_wickets = _fall_of_wickets(g)
    innings_breakdown = _build_innings_breakdown(g)

    # Normalize status - should be uppercase for completed games
    status_raw = getattr(g, "status", "")
    if hasattr(status_raw, "value"):
        status_str = str(status_raw.value).upper()
    else:
        status_str = str(status_raw).upper()

    # Map status values to match expected format
    if status_str == "IN_PROGRESS":
        status_str = "IN_PROGRESS"
    elif status_str in ("COMPLETE", "COMPLETED"):
        status_str = "COMPLETED"

    snapshot: dict[str, Any] = {
        "id": getattr(g, "id", None),
        "status": status_str,
        "score": {
            "runs": int(getattr(g, "total_runs", 0)),
            "wickets": int(getattr(g, "total_wickets", 0)),
            "overs": int(getattr(g, "overs_completed", 0)),
        },
        # Add top-level score fields for compatibility
        "total_runs": int(getattr(g, "total_runs", 0)),
        "total_wickets": int(getattr(g, "total_wickets", 0)),
        "overs_completed": int(getattr(g, "overs_completed", 0)),
        "balls_this_over": int(getattr(g, "balls_this_over", 0)),
        "overs": (
            f"{int(getattr(g, 'overs_completed', 0))}." f"{int(getattr(g, 'balls_this_over', 0))}"
        ),
        "balls_bowled_total": int(getattr(g, "overs_completed", 0)) * 6
        + int(getattr(g, "balls_this_over", 0)),
        "batsmen": {
            "striker": {
                "id": getattr(g, "current_striker_id", None),
                "name": _player_name(
                    getattr(g, "team_a", {}),
                    getattr(g, "team_b", {}),
                    getattr(g, "current_striker_id", None),
                ),
                "runs": _bat_entry(g, getattr(g, "current_striker_id", None)).get("runs", 0),
                "balls": _bat_entry(g, getattr(g, "current_striker_id", None)).get(
                    "balls_faced", 0
                ),
                "is_out": _bat_entry(g, getattr(g, "current_striker_id", None)).get(
                    "is_out", False
                ),
            },
            "non_striker": {
                "id": getattr(g, "current_non_striker_id", None),
                "name": _player_name(
                    getattr(g, "team_a", {}),
                    getattr(g, "team_b", {}),
                    getattr(g, "current_non_striker_id", None),
                ),
                "runs": _bat_entry(g, getattr(g, "current_non_striker_id", None)).get("runs", 0),
                "balls": _bat_entry(g, getattr(g, "current_non_striker_id", None)).get(
                    "balls_faced", 0
                ),
                "is_out": _bat_entry(g, getattr(g, "current_non_striker_id", None)).get(
                    "is_out", False
                ),
            },
        },
        "current_bowler": {
            "id": cur_bowler_id,
            "name": _player_name(getattr(g, "team_a", {}), getattr(g, "team_b", {}), cur_bowler_id),
        },
        "extras_totals": extras_totals,
        "fall_of_wickets": fall_of_wickets,
        "last_ball_bowler_id": getattr(g, "last_ball_bowler_id", None),
        "last_delivery": last_delivery_out,
        "batting_scorecard": getattr(g, "batting_scorecard", {}),
        "bowling_scorecard": getattr(g, "bowling_scorecard", {}),
        "current_bowler_id": cur_bowler_id,
        "current_striker_id": getattr(g, "current_striker_id", None),
        "current_non_striker_id": getattr(g, "current_non_striker_id", None),
        "batting_team_name": getattr(g, "batting_team_name", None),
        "bowling_team_name": getattr(g, "bowling_team_name", None),
        "current_inning": getattr(g, "current_inning", None),
        "target": getattr(g, "target", None),
        "first_inning_summary": getattr(g, "first_inning_summary", None),
        "needs_new_over": needs_new_over,
        "needs_new_batter": needs_new_batter,
        "needs_new_innings": needs_new_innings,
        "canScore": can_score,
        "dls": _dls_panel_for(g, base_dir),
        "innings": innings_breakdown,
    }

    # completion/result signals - check both is_game_over flag and COMPLETED status
    # Also check if result is present, as that implies completion
    is_game_over = (
        bool(getattr(g, "is_game_over", False))
        or status_str == "COMPLETED"
        or (getattr(g, "result", None) is not None)
    )

    snapshot["is_game_over"] = is_game_over
    res_any = getattr(g, "result", None)
    if isinstance(res_any, BaseModel):
        result_dict = res_any.model_dump()
    elif isinstance(res_any, str):
        try:
            result_dict = json.loads(res_any)
        except Exception:
            result_dict = {"result_text": res_any}
    elif isinstance(res_any, dict):
        result_dict = res_any
    else:
        result_dict = None

    # Ensure result has required fields when game is over
    if is_game_over and result_dict:
        # Ensure winner_team_name is present
        if "winner_team_name" not in result_dict and "winner_team_id" in result_dict:
            # Try to derive from batting/bowling team
            result_dict["winner_team_name"] = result_dict.get("winner_team_id") or ""

        # Ensure result_text is present
        if "result_text" not in result_dict or not result_dict["result_text"]:
            # Generate basic result text if missing
            winner = result_dict.get("winner_team_name", "")
            method = result_dict.get("method", "")
            margin = result_dict.get("margin", 0)
            if winner and method:
                result_dict["result_text"] = f"{winner} won {method} {margin}"

    snapshot["result"] = result_dict
    snapshot["completed_at"] = getattr(g, "completed_at", None)

    # runtime flags used by UI/tests
    snapshot["pending_new_batter"] = bool(getattr(g, "pending_new_batter", False))
    snapshot["current_striker_id"] = getattr(g, "current_striker_id", None)
    snapshot["current_non_striker_id"] = getattr(g, "current_non_striker_id", None)

    return snapshot
