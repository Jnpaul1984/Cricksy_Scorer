from __future__ import annotations

import os
import uuid
from collections import defaultdict
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
    TypedDict,
    Callable,
    TypeVar,
    Union,
    cast,
    Literal,
    Mapping,
    runtime_checkable,
)
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, or_, and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm.attributes import flag_modified
from fastapi import UploadFile, File, Form
from datetime import datetime, timezone
import json
import dls as dlsmod
from routes.games_router import router as games_router
from routes.games_dls import router as games_dls_router
from routes.interruptions import router as interruptions_router
# ---- App modules ----
from sql_app import crud, schemas, models
from sql_app.database import SessionLocal

# Socket.IO (no first-party type stubs; we keep our own Protocol below)
import socketio  # type: ignore[import-not-found]
import logging
logger = logging.getLogger(__name__)
F = TypeVar("F", bound=Callable[..., Any])

# ================================================================
# Socket.IO Protocol (extended with enter_room/leave_room)
# ================================================================
class SocketIOServer(Protocol):
    async def emit(
        self,
        event: str,
        data: Any | None = None,
        *,
        to: Optional[str] = ...,
        room: Optional[str] = ...,
        skip_sid: Optional[str] = ...,
        namespace: Optional[str] = ...,
        callback: Optional[Callable[..., Any]] = ...,
        ignore_queue: bool = False,
    ) -> None: ...

    def event(self, f: F) -> F: ...
    async def enter_room(self, sid: str, room: str, namespace: Optional[str] = ...) -> None: ...
    async def leave_room(self, sid: str, room: str, namespace: Optional[str] = ...) -> None: ...

# ================================================================
# Types & Protocols
# ================================================================
Number = Union[int, float]

class PlayerDict(TypedDict):
    id: str
    name: str

class TeamDict(TypedDict):
    name: str
    players: List[PlayerDict]

# Required keys (fixes TypedDict optional access warnings)
class BattingEntryDict(TypedDict):
    player_id: str
    player_name: str
    runs: int
    balls_faced: int
    is_out: bool

class BowlingEntryDict(TypedDict):
    player_id: str
    player_name: str
    overs_bowled: float
    runs_conceded: int
    wickets_taken: int

class DeliveryDict(TypedDict, total=False):
    over_number: int
    ball_number: int
    bowler_id: str
    striker_id: str
    non_striker_id: str
    runs_off_bat: int
    runs_scored: int
    is_extra: bool
    extra_type: Optional[schemas.ExtraCode]
    extra_runs: int
    is_wicket: bool
    dismissal_type: Optional[str]
    dismissed_player_id: Optional[str]
    commentary: Optional[str]
    fielder_id: Optional[str]

# Strongly-typed kwargs for constructing schemas.Delivery(**kwargs)
class DeliveryKwargs(TypedDict):
    over_number: int
    ball_number: int
    bowler_id: str
    striker_id: str
    non_striker_id: str
    runs_off_bat: int
    runs_scored: int
    is_extra: bool
    extra_type: Optional[schemas.ExtraCode]
    extra_runs: int
    is_wicket: bool
    dismissal_type: Optional[str]
    dismissed_player_id: Optional[str]
    commentary: Optional[str]
    fielder_id: Optional[str]

class InterruptionRec(TypedDict, total=False):
    id: str
    inning: int
    kind: str
    note: Optional[str]
    started_at: str          # ISO-8601
    ended_at: Optional[str]  # ISO-8601
    overs_reduced_to: Optional[int]

class DLSRequest(BaseModel):
    kind: Literal["odi", "t20"] = "odi"      # which table to use
    innings: Literal[1, 2] = 2               # compute for which innings perspective
    # Optional override if not using g.overs_limit:
    max_overs: Optional[int] = None

class DLSRevisedOut(BaseModel):
    R1_total: float
    R2_total: float
    S1: int
    target: int

class DLSParOut(BaseModel):
    R1_total: float
    R2_used: float
    S1: int
    par: int
    ahead_by: int

class DlsPanel(TypedDict, total=False):
    method: Literal["DLS"]
    par: int
    target: int
    ahead_by: int

class GameState(Protocol):
    # ids & teams
    id: str
    team_a: TeamDict
    team_b: TeamDict

    # config
    match_type: str
    overs_limit: Optional[int]
    days_limit: Optional[int]
    dls_enabled: bool
    interruptions: List[InterruptionRec]

    toss_winner_team: str
    decision: str
    batting_team_name: str
    bowling_team_name: str

    # status
    status: str
    current_inning: int
    total_runs: int
    total_wickets: int
    overs_completed: int
    balls_this_over: int
    current_striker_id: Optional[str]
    current_non_striker_id: Optional[str]
    target: Optional[int]
    result: Optional[str]
    current_bowler_id: Optional[str]
    last_ball_bowler_id: Optional[str]
    current_over_balls: int
    mid_over_change_used: bool
    pending_new_batter: bool
    pending_new_over: bool
    # team roles
    team_a_captain_id: Optional[str]
    team_a_keeper_id: Optional[str]
    team_b_captain_id: Optional[str]
    team_b_keeper_id: Optional[str]

    # timelines & scorecards (JSON-safe)
    deliveries: Sequence[Any] 
    batting_scorecard: Dict[str, BattingEntryDict]
    bowling_scorecard: Dict[str, BowlingEntryDict]

class StartOverBody(BaseModel):
    bowler_id: str

class MidOverChangeBody(BaseModel):
    new_bowler_id: str
    reason: Literal["injury", "other"] = "injury"

from typing import List, Literal, TypedDict

# If you're on Python < 3.11:
# from typing_extensions import TypedDict, NotRequired
# class SponsorItem(TypedDict, total=False):
#     ...

class SponsorItem(TypedDict, total=False):
    name: str
    logoUrl: str
    clickUrl: str
    image_url: str
    img: str
    link_url: str
    url: str
    alt: str
    rail: Literal["left", "right", "badge"]
    maxPx: int | str
    size: int | str

class SponsorsManifest(TypedDict):
    items: List[SponsorItem]



# ================================================================
# FastAPI + Socket.IO wiring
# ================================================================
_sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")  # type: ignore[call-arg]
sio: SocketIOServer = cast(SocketIOServer, _sio)
_fastapi = FastAPI(title="Cricksy Scorer API")
_fastapi.state.sio = sio
app = socketio.ASGIApp(sio, other_asgi_app=_fastapi)


_fastapi.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "*",
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- PR 7: Static files for logos/sponsors ---
# Resolve to backend/static
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = Path(__file__).parent / "static" / "sponsors"

BASE = Path("backend/static/sponsors")
# Create if missing (avoids RuntimeError)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

_fastapi.mount("/sponsors", StaticFiles(directory=STATIC_DIR), name="sponsors")

# Keep your separate games router mounted
_fastapi.include_router(games_router, prefix="/legacy")
_fastapi.include_router(games_dls_router)
_fastapi.include_router(interruptions_router)
# ================================================================
# DB dependency (async)
# ================================================================
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:  # type: ignore[misc]
        yield session

# ================================================================
# Helpers: core utilities
# ================================================================
def _mk_players(names: List[str]) -> List[PlayerDict]:
    """Create ephemeral player dicts with UUIDs for a brand-new match context."""
    return [{"id": str(uuid.uuid4()), "name": n} for n in names]

def _mk_batting_scorecard(team: TeamDict) -> Dict[str, BattingEntryDict]:
    return {
        p["id"]: {
            "player_id": p["id"],
            "player_name": p["name"],
            "runs": 0,
            "balls_faced": 0,
            "is_out": False,
        }
        for p in team["players"]
    }

def _mk_bowling_scorecard(team: TeamDict) -> Dict[str, BowlingEntryDict]:
    return {
        p["id"]: {
            "player_id": p["id"],
            "player_name": p["name"],
            "overs_bowled": 0.0,
            "runs_conceded": 0,
            "wickets_taken": 0,
        }
        for p in team["players"]
    }



def _bowling_balls_to_overs(balls: int) -> float:
    """
    Convert legal ball count to cricket-style decimal overs (X.Y),
    where Y is the balls remainder [0..5]. Never round.
    """
    return float(f"{balls // 6}.{balls % 6}")

# AFTER
def _player_name(team_a: TeamDict, team_b: TeamDict, pid: Optional[str]) -> Optional[str]:
    if not pid:
        return None
    for team in (team_a, team_b):
        for p in team["players"]:
            if p["id"] == pid:
                return p["name"]
    return None

def _id_by_name(team_a: TeamDict, team_b: TeamDict, name: Optional[str]) -> Optional[str]:
    if not name:
        return None
    n = name.strip().lower()
    for team in (team_a, team_b):
        for p in team["players"]:
            if p["name"].strip().lower() == n:
                return p["id"]
    return None


def _mini_batting_card(g: GameState) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
    bsc = getattr(g, "batting_scorecard", {}) or {}
    for _pid, e in bsc.items():
        balls = int(e.get("balls_faced", 0))
        was_out = bool(e.get("is_out", False))
        if balls == 0 and not was_out:
            continue
        row: Dict[str, Any] = {
            "name": e.get("player_name", ""),
            "runs": int(e.get("runs", 0)),
            "balls": balls,
            "status": "out" if was_out else "not out",
        }
        out.append(row)

    last_dismiss_for: Dict[str, Dict[str, Optional[str]]] = {}
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

def _mini_bowling_card(g: GameState) -> List[Dict[str, Any]]:
    out: List[Dict[str, Any]] = []
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

# ================================================================
# Helpers: bowling constraints
# ================================================================
def _can_start_over(g: GameState, bowler_id: str) -> Optional[str]:
    if g.current_over_balls not in (0, None) or g.balls_this_over != 0:
        return "Cannot start a new over while an over is in progress."
    last_id = getattr(g, "last_ball_bowler_id", None)
    if last_id and bowler_id == last_id:
        return "Selected bowler delivered the last ball of the previous over and cannot bowl consecutive overs."
    return None


def _compute_snapshot_flags(g: GameState) -> Dict[str, bool]:
    """Return UI gating flags derived from current runtime state."""
    # Identify if one of the current batters is out and must be replaced
    need_new_batter = False
    if g.current_striker_id:
        e = g.batting_scorecard.get(g.current_striker_id) or {}
        if isinstance(e, BaseModel):
            e = e.model_dump()
        need_new_batter = bool(e.get("is_out", False))
    if not need_new_batter and g.current_non_striker_id:
        e2 = g.batting_scorecard.get(g.current_non_striker_id) or {}
        if isinstance(e2, BaseModel):
            e2 = e2.model_dump()
        need_new_batter = bool(e2.get("is_out", False))

    # New over is required when over just ended (balls_this_over == 0)
    # and there was at least one ball previously AND no active bowler selected
    have_any_balls = (len(_dedup_deliveries(g)) > 0)
    need_new_over = bool(g.balls_this_over == 0 and have_any_balls and not getattr(g, "current_bowler_id", None))

    return {"needs_new_batter": need_new_batter, "needs_new_over": need_new_over}

# ================================================================
# Helpers: dismissal / extras rules
# ================================================================
# Bowler gets credit for these modes:
_CREDIT_BOWLER = {"bowled", "caught", "lbw", "stumped", "hit_wicket"}

# Team wicket only (no bowler credit):
_CREDIT_TEAM = {
    "run_out",
    "obstructing_the_field",
    "hit_ball_twice",
    "timed_out",
    "retired_out",
    "handled_ball",
}

# On a NO-BALL, these cannot result in out:
_INVALID_ON_NO_BALL = {"bowled", "caught", "lbw", "stumped", "hit_wicket"}
# On a WIDE, these are invalid (stumped *is allowed* on a wide):
_INVALID_ON_WIDE = {"bowled", "lbw"}

def is_legal_delivery(extra: Optional[schemas.ExtraCode]) -> bool:
    return extra not in {"wd", "nb"}



def _rotate_strike_on_runs(runs: int) -> bool: # type: ignore
    return (runs % 2) == 1

# ================================================================
# NEW: normalization + dedupe + totals recompute
# ================================================================
def _norm_extra(x: Any) -> Optional[schemas.ExtraCode]:
    """
    Normalize to: None | 'wd' | 'nb' | 'b' | 'lb'
    """
    if not x:
        return None
    s = (str(x) or "").strip().lower()
    if s in {"wide", "wd"}:
        return cast(schemas.ExtraCode, "wd")
    if s in {"no_ball", "nb"}:
        return cast(schemas.ExtraCode, "nb")
    if s in {"b", "bye"}:
        return cast(schemas.ExtraCode, "b")
    if s in {"lb", "leg_bye", "leg-bye"}:
        return cast(schemas.ExtraCode, "lb")
    return None

def _dedup_deliveries(g: GameState) -> List[Dict[str, Any]]:
    """
    Collapse duplicates by (over_number, ball_number), keeping the last occurrence, preserving order.
    Useful if client double-sends or an undo/redo races.
    """
    if not g.deliveries:
        return []
    deliveries: Sequence[Union[BaseModel, Mapping[str, Any]]] = cast(
        Sequence[Union[BaseModel, Mapping[str, Any]]],
        g.deliveries,
    )
    seen: Dict[tuple[int, int], Dict[str, Any]] = {}
    order: List[tuple[int, int]] = []
    for d_any in deliveries:
        d: Dict[str, Any] = (
            d_any.model_dump()
            if isinstance(d_any, BaseModel)
            else dict(d_any)
        )
        over_no = int(d.get("over_number") or 0)
        ball_no = int(d.get("ball_number") or 0)
        k = (over_no, ball_no)
        if k not in seen:
            order.append(k)
        seen[k] = d  # last write wins
    return [seen[k] for k in order]

def _recompute_totals_and_runtime(g: GameState) -> None:
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

    # Preserve any bowler that was explicitly selected via /overs/start
    preselected_bowler: Optional[str] = getattr(g, "current_bowler_id", None)

    total_runs: int = 0
    total_wkts: int = 0
    legal_balls: int = 0
    cur_over_bowler: Optional[str] = None
    last_legal_bowler: Optional[str] = None


    

    deliveries2: Sequence[Union[BaseModel, Mapping[str, Any]]] = cast(
        Sequence[Union[BaseModel, Mapping[str, Any]]],
        getattr(g, "deliveries", []) or [],
    )
    for d_any in deliveries2:
        d = d_any.model_dump() if isinstance(d_any, BaseModel) else dict(d_any)
        x = _norm_extra(d.get("extra_type"))
        off = int(d.get("runs_off_bat") or 0)
        ex  = int(d.get("extra_runs") or 0)

        if x == "wd":
            total_runs += max(1, ex or 1)  # wides are illegal; must be >=1
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

       
    # Overs/balls derived from legal deliveries
    g.overs_completed = legal_balls // 6
    g.balls_this_over = legal_balls % 6
    g.current_over_balls = g.balls_this_over

    g.total_runs = total_runs
    g.total_wickets = total_wkts

    # Bowler pointers:
    g.last_ball_bowler_id = last_legal_bowler
    # If an over is in progress, DO NOT overwrite a server-selected/mid-over-changed bowler.
    # Prefer an existing current_bowler_id; otherwise fall back to last legal ball's bowler.
    if g.balls_this_over > 0:
        g.current_bowler_id = getattr(g, "current_bowler_id", None) or cur_over_bowler
    else:
        g.current_bowler_id = preselected_bowler


def _extras_breakdown(g: GameState) -> Dict[str,int]:
    wides = no_balls = byes = leg_byes = penalty = 0

    deliveries3: Sequence[Union[BaseModel, Mapping[str, Any]]] = cast(
        Sequence[Union[BaseModel, Mapping[str, Any]]],
        getattr(g, "deliveries", []) or [],
    )
    for d_any in deliveries3:
        d: Dict[str, Any] = (
            d_any.model_dump() if isinstance(d_any, BaseModel) else dict(d_any)
        )
        x = _norm_extra(d.get("extra_type"))
        ex = int(d.get("extra_runs") or 0)

        if x == "wd":
            # wides are extras only; must be >= 1
            wides += max(1, ex or 1)
        elif x == "nb":
            # only the 1-penalty is an extra on nb
            no_balls += 1
        elif x == "b":
            byes += ex
        elif x == "lb":
            leg_byes += ex

    total = wides + no_balls + byes + leg_byes + penalty
    return {"wides": wides, "no_balls": no_balls, "byes": byes, "leg_byes": leg_byes, "penalty": penalty, "total": total}

def _fall_of_wickets(g: GameState) -> List[Dict[str, Any]]:
    """
    Build fall-of-wickets from the authoritative (deduped) ledger.
    Each entry: score at fall, wicket number, batter, over-ball, bowler, dismissal, fielder.
    """
    fow: List[Dict[str, Any]] = []
    cum = 0
    dl = _dedup_deliveries(g)
    for d in dl:
        # score after this ball
        cum += int(d.get("runs_scored") or 0)

        is_out = bool(d.get("is_wicket"))
        dismissal = (d.get("dismissal_type") or "").strip().lower() or None
        if not (is_out and dismissal):
            continue

        over_no = int(d.get("over_number") or 0)
        ball_no = int(d.get("ball_number") or 0)
        out_pid = str(d.get("dismissed_player_id") or d.get("striker_id") or "")

        fow.append({
            "score": cum,                                 # team score at the moment of wicket
            "wicket": len(fow) + 1,                       # ordinal of this wicket
            "batter_id": out_pid,
            "batter_name": _player_name(g.team_a, g.team_b, out_pid) or "",
            "over": f"{over_no}.{ball_no}",               # over.ball of dismissal
            "dismissal_type": dismissal,
            "bowler_id": d.get("bowler_id"),
            "bowler_name": _player_name(g.team_a, g.team_b, d.get("bowler_id")),
            "fielder_id": d.get("fielder_id"),
            "fielder_name": _player_name(g.team_a, g.team_b, d.get("fielder_id")),
        })
    return fow


# ================================================================
# Ensure/Coerce entries
# ================================================================
def _ensure_batting_entry(g: GameState, batter_id: str) -> BattingEntryDict:
    e_any: Any = g.batting_scorecard.get(batter_id)
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
        }

    if "player_id" not in e:
        e["player_id"] = batter_id
    if "player_name" not in e:
        e["player_name"] = _player_name(g.team_a, g.team_b, batter_id) or ""
    if "runs" not in e:
        e["runs"] = 0
    if "balls_faced" not in e:
        e["balls_faced"] = 0
    if "is_out" not in e:
        e["is_out"] = False

    g.batting_scorecard[batter_id] = e
    return e

def _ensure_bowling_entry(g: GameState, bowler_id: str) -> BowlingEntryDict:
    e_any: Any = g.bowling_scorecard.get(bowler_id)
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

    if "player_id" not in e:
        e["player_id"] = bowler_id
    if "player_name" not in e:
        e["player_name"] = _player_name(g.team_a, g.team_b, bowler_id) or ""
    if "overs_bowled" not in e:
        e["overs_bowled"] = 0.0
    if "runs_conceded" not in e:
        e["runs_conceded"] = 0
    if "wickets_taken" not in e:
        e["wickets_taken"] = 0

    g.bowling_scorecard[bowler_id] = e
    return e

def _coerce_batting_entry(  # pyright: ignore[reportUnusedFunction]
    x: Any, team_a: TeamDict, team_b: TeamDict
) -> schemas.BattingScorecardEntry:
    if isinstance(x, schemas.BattingScorecardEntry):
        return x
    if isinstance(x, dict):
        x_dict: Dict[str, Any] = cast(Dict[str, Any], x)
        pid = str(x_dict.get("player_id", ""))
        return schemas.BattingScorecardEntry(
            player_id=pid,
            player_name=str(x_dict.get("player_name") or _player_name(team_a, team_b, pid)),
            runs=int(x_dict.get("runs", 0)),
            balls_faced=int(x_dict.get("balls_faced", x_dict.get("balls", 0))),
            is_out=bool(x_dict.get("is_out", False)),
        )
    return schemas.BattingScorecardEntry(player_id="", player_name="", runs=0, balls_faced=0, is_out=False)

def _coerce_bowling_entry(  # pyright: ignore[reportUnusedFunction]
    x: Any, team_a: TeamDict, team_b: TeamDict
) -> schemas.BowlingScorecardEntry:
    if isinstance(x, schemas.BowlingScorecardEntry):
        return x
    if isinstance(x, dict):
        x_dict: Dict[str, Any] = cast(Dict[str, Any], x)
        pid = str(x_dict.get("player_id", ""))
        overs_val: Any = x_dict.get("overs_bowled", x_dict.get("overs", 0.0))
        try:
            overs_num = float(overs_val)
        except Exception:
            overs_num = 0.0
        return schemas.BowlingScorecardEntry(
            player_id=pid,
            player_name=str(x_dict.get("player_name") or _player_name(team_a, team_b, pid)),
            overs_bowled=overs_num,
            runs_conceded=int(x_dict.get("runs_conceded", x_dict.get("runs", 0))),
            wickets_taken=int(x_dict.get("wickets_taken", x_dict.get("wickets", 0))),
        )
    return schemas.BowlingScorecardEntry(player_id="", player_name="", overs_bowled=0.0, runs_conceded=0, wickets_taken=0)

# ================================================================
# Rebuild scorecards FROM LEDGER (authoritative)
# ================================================================
def _rebuild_scorecards_from_deliveries(g: GameState) -> None:
    batting_team = g.team_a if g.batting_team_name == g.team_a["name"] else g.team_b
    bowling_team = g.team_b if batting_team is g.team_a else g.team_a

    bat = _mk_batting_scorecard(batting_team)
    bowl = _mk_bowling_scorecard(bowling_team)

    balls_by_bowler: Dict[str, int] = defaultdict(int)

    deliveries4: Sequence[Union[BaseModel, Mapping[str, Any]]] = cast(
        Sequence[Union[BaseModel, Mapping[str, Any]]],
        g.deliveries or [],
    )
    for d_any in deliveries4:
        d: Dict[str, Any] = (
            d_any.model_dump()
            if isinstance(d_any, BaseModel)
            else dict(d_any)
        )

        striker = d.get("striker_id")
        bowler  = d.get("bowler_id")
        x   = _norm_extra(d.get("extra_type"))
        off = int(d.get("runs_off_bat") or 0)
        ex  = int(d.get("extra_runs") or 0)
        wicket  = bool(d.get("is_wicket"))
        dismissal_type = (d.get("dismissal_type") or "").strip().lower() or None

        # --- Batter updates ---
        if striker in bat:
            if x not in ("wd", "nb"):
                bat[striker]["balls_faced"] += 1
            # credit only off-the-bat runs
            bat[striker]["runs"] += off


        # Mark dismissed player out on scorecard
        if wicket and dismissal_type:
            out_pid = str(d.get("dismissed_player_id") or striker or "")
            if out_pid in bat:
                bat[out_pid]["is_out"] = True

        # --- Bowler updates ---
        if bowler in bowl:
            if x not in ("wd","nb"):
                balls_by_bowler[bowler] += 1
            if x == "wd":
                bowl[bowler]["runs_conceded"] += max(1, ex or 1)
            elif x == "nb":
                bowl[bowler]["runs_conceded"] += 1 + off
            elif x is None:
                bowl[bowler]["runs_conceded"] += off
            # b/lb don't add to bowler runs
            if wicket and dismissal_type in _CREDIT_BOWLER:
                bowl[bowler]["wickets_taken"] += 1

    for bid, balls in balls_by_bowler.items():
        bowl[bid]["overs_bowled"] = _bowling_balls_to_overs(balls)

    g.batting_scorecard = bat
    g.bowling_scorecard = bowl



# ================================================================
# Misc helpers
# ================================================================
MAX_UPLOAD_BYTES = 5 * 1024 * 1024  # 5MB

def _detect_image_ext(data: bytes, content_type: Optional[str], filename: Optional[str]) -> Optional[str]:
    """Return 'svg' | 'png' | 'webp' if valid, else None."""
    ct = (content_type or "").lower()
    ext = (os.path.splitext(filename or "")[1].lower())
    head = data[:256]

    # SVG
    if ct == "image/svg+xml" or ext == ".svg" or b"<svg" in head.lower():
        return "svg"
    # PNG
    if ct == "image/png" or ext == ".png" or data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    # WEBP
    if ct == "image/webp" or ext == ".webp" or (data[:4] == b"RIFF" and data[8:12] == b"WEBP"):
        return "webp"
    return None

def _parse_iso_dt(s: Optional[str]) -> Optional[datetime]:
    """Parse ISO-8601; assume UTC if naive."""
    if not s:
        return None
    s = s.strip()
    try:
        if s.endswith("Z"):
            return datetime.fromisoformat(s[:-1]).replace(tzinfo=timezone.utc)
        dt = datetime.fromisoformat(s)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except Exception:
        return None

def _iso_or_none(dt: Any) -> Optional[str]:
    """Return isoformat string if dt is a datetime (or None if not)."""
    return dt.isoformat() if isinstance(dt, datetime) else None

# ================================================================
# Request models (wrapper for your schemas)
# ================================================================
class CreateGameRequest(BaseModel):
    team_a_name: str
    team_b_name: str
    players_a: List[str] = Field(..., min_length=2)
    players_b: List[str] = Field(..., min_length=2)

    match_type: Literal["limited", "multi_day", "custom"] = "limited"
    overs_limit: Optional[int] = Field(None, ge=1, le=120)
    days_limit: Optional[int] = Field(None, ge=1, le=7)
    overs_per_day: Optional[int] = Field(None, ge=1, le=120)
    dls_enabled: bool = False
    interruptions: List[Dict[str, Optional[str]]] = Field(default_factory=list)

    toss_winner_team: str
    decision: Literal["bat", "bowl"]

class OversLimitBody(BaseModel):
    overs_limit: int

class NextBatterBody(BaseModel):
    batter_id: str

# ------- PR 10: Sponsor Impression logging -------
class SponsorImpressionIn(BaseModel):
    game_id: str
    sponsor_id: str
    at: Optional[str] = None  # ISO-8601; defaults to now(UTC) when omitted

class SponsorImpressionsOut(BaseModel):
    inserted: int
    ids: List[int]

# ================================================================
# Core helpers for scoring, replay, and snapshot
# ================================================================
def _bat_entry(g: GameState, pid: Optional[str]) -> BattingEntryDict:
    if not pid:
        return {"player_id": "", "player_name": "", "runs": 0, "balls_faced": 0, "is_out": False}
    e_any: Any = g.batting_scorecard.get(pid)
    if isinstance(e_any, BaseModel):
        return cast(BattingEntryDict, e_any.model_dump())
    if isinstance(e_any, dict):
        return cast(BattingEntryDict, e_any)
    return {
        "player_id": pid,
        "player_name": _player_name(g.team_a, g.team_b, pid) or "",
        "runs": 0,
        "balls_faced": 0,
        "is_out": False,
    }
def _reset_runtime_and_scorecards(g: GameState) -> None:
    g.total_runs = 0
    g.total_wickets = 0
    g.overs_completed = 0
    g.balls_this_over = 0
    g.current_striker_id = None
    g.current_non_striker_id = None

    batting_team = g.team_a if g.batting_team_name == g.team_a["name"] else g.team_b
    bowling_team = g.team_b if batting_team is g.team_a else g.team_a

    g.batting_scorecard = _mk_batting_scorecard(batting_team)
    g.bowling_scorecard = _mk_bowling_scorecard(bowling_team)

# ------------------------------------------------
# Close an over: clear current bowler and mark last
# ------------------------------------------------
def _complete_over_runtime(g: GameState, bowler_id: Optional[str]) -> None:
    """
    Called exactly when an over finishes (after ball 6 of the over).
    - Records who bowled the last legal ball of the finished over
    - Clears current_bowler_id to force selection for the next over
    - Resets per-over bookkeeping
    """
    # last legal ball’s bowler is the over’s bowler
    if bowler_id:
        g.last_ball_bowler_id = bowler_id

    # over is finished -> next over requires explicit bowler
    g.current_bowler_id = None
    g.current_over_balls = 0
    g.mid_over_change_used = False


def _score_one(
    g: GameState,
    *,
    striker_id: str,
    non_striker_id: str,
    bowler_id: str,
    runs_scored: int,
    extra: Optional[schemas.ExtraCode],
    is_wicket: bool,
    dismissal_type: Optional[str],
    dismissed_player_id: Optional[str],
) -> DeliveryKwargs:
    # Ensure runtime fields exist
    if g.current_striker_id is None:
        g.current_striker_id = striker_id
    if g.current_non_striker_id is None:
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

    # 👇 Normalize extra to canonical codes: None|'wd'|'nb'|'b'|'lb'
    extra_norm = _norm_extra(extra)
    is_nb = (extra_norm == "nb")
    is_wd = (extra_norm == "wd")
    legal = not (is_nb or is_wd)

    off_bat_runs = 0
    extra_runs = 0

    if extra_norm is None:                # legal ball
        off_bat_runs = runs_scored
    elif extra_norm == "nb":              # no-ball
        off_bat_runs = runs_scored        # caller passed runs_off_bat -> we already mapped to runs_scored for this call
    elif extra_norm in ("wd", "b", "lb"): # wides/byes/leg-byes
        extra_runs = runs_scored

    # team totals increment (runtime)
    team_add = off_bat_runs + (1 if is_nb else 0) + (extra_runs if extra_norm in ("wd","b","lb") else 0)
    g.total_runs += team_add
    # capture the display over/ball *before* we mutate runtime
    delivery_over_number = int(g.overs_completed)
    delivery_ball_number = int(g.balls_this_over + (1 if legal else 0))

    # --- Batting runtime (only what scorecards need immediately) ---
    bs = _ensure_batting_entry(g, striker_id)
    if legal:
        bs["balls_faced"] = int(bs.get("balls_faced", 0) + 1)
    if extra_norm is None:
        bs["runs"] = int(bs.get("runs", 0) + runs)
    elif is_nb:
        bs["runs"] = int(bs.get("runs", 0) + runs)


    # --- Bowling runtime (overs for current bowler on legal balls) ---
    bw = _ensure_bowling_entry(g, bowler_id)
    if legal:
        prev_balls = int(round(float(bw.get("overs_bowled", 0.0)) * 6))
        bw["overs_bowled"] = _bowling_balls_to_overs(prev_balls + 1)
        g.current_over_balls = int(getattr(g, "current_over_balls", 0) + 1)
        g.last_ball_bowler_id = bowler_id  # ✅ track who bowled the last legal ball

    # --- Dismissal normalization ---
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
        # Block next ball until a new batter is provided
        g.pending_new_batter = True
        if dismissal in _CREDIT_BOWLER:
            bw2 = _ensure_bowling_entry(g, bowler_id)
            bw2["wickets_taken"] = int(bw2.get("wickets_taken", 0) + 1)

    # --- Strike rotation + over progression (runtime only) ---
    swap = False
    if extra_norm is None:
        # legal ball: rotate on odd off-bat runs
        swap = (off_bat_runs % 2) == 1
    elif extra_norm == "nb":
        # no-ball: rotate only on odd off-bat runs (the +1 penalty doesn't rotate)
        swap = (off_bat_runs % 2) == 1
    elif extra_norm in ("b", "lb"):
        # byes/leg-byes: rotate on odd extras
        swap = (extra_runs % 2) == 1
    elif extra_norm == "wd":
        # wides: rotate only if they RAN (i.e., extras > 1), and it's odd
        swap = (extra_runs > 1) and (extra_runs % 2 == 1)

    if swap:
        g.current_striker_id, g.current_non_striker_id = (
            g.current_non_striker_id,
            g.current_striker_id,
        )

    if legal:
        g.balls_this_over = int(g.balls_this_over + 1)
        if g.balls_this_over >= 6:
            g.overs_completed = int(g.overs_completed + 1)
            g.balls_this_over = 0
            g.pending_new_over = True
            g.current_bowler_id = None
            # swap ends at over end
            g.current_striker_id, g.current_non_striker_id = (
                g.current_non_striker_id,
                g.current_striker_id,
            )
            _complete_over_runtime(g, bowler_id)

    return {
        "over_number": delivery_over_number,
        "ball_number": delivery_ball_number,
        "bowler_id": str(bowler_id),
        # IMPORTANT: ledger records who actually faced this ball
        "striker_id": str(pre_striker),
        "non_striker_id": str(pre_non_striker),

        "runs_off_bat": int(off_bat_runs),
        "extra_type": extra_norm,
        "extra_runs": int(extra_runs),
        "runs_scored": int(team_add),

        "is_extra": extra_norm is not None,
        "is_wicket": out_happened,
        "dismissal_type": dismissal,
        "dismissed_player_id": out_player_id if out_happened else None,
        "commentary": None,
        "fielder_id": None,
    }
def _dls_panel_for(g: GameState) -> DlsPanel:
    """
    Best-effort DLS panel.
    Shows:
      - target: full chase target for inns 2
      - par: current par at this exact moment
      - ahead_by: Team 2 runs minus par (only during inns 2)
    Returns {} when DLS is disabled or format is not a standard DLS format.
    """
    try:
        if not getattr(g, "dls_enabled", False):
            return {}

        overs_limit_opt = cast(Optional[int], getattr(g, "overs_limit", None))
        if overs_limit_opt not in (20, 50):
            return {}

        kind = "odi" if overs_limit_opt == 50 else "t20"
        env = dlsmod.load_env(kind, str(BASE_DIR))

        deliveries_m: List[Mapping[str, Any]] = cast(
            List[Mapping[str, Any]],
            list(getattr(g, "deliveries", [])),
        )
        interruptions = list(getattr(g, "interruptions", []))

        # Team 1 total resources (from ledger + interruptions)
        R1_total = dlsmod.total_resources_team1(
            env=env,
            max_overs_initial=int(overs_limit_opt),
            deliveries=deliveries_m,
            interruptions=interruptions,
        )

        # NOTE: If you later store inns-1 score separately, prefer that.
        S1 = int(getattr(g, "total_runs", 0))

        # Team 2 resource start (for target) and live used (for par)
        R_start = env.table.R(float(overs_limit_opt), 0)

        # Live used now:
        overs_completed = float(getattr(g, "overs_completed", 0) or 0)
        balls_this_over = float(getattr(g, "balls_this_over", 0) or 0)
        wkts_now = int(getattr(g, "total_wickets", 0) or 0)

        team2_overs_left_now = max(0.0, float(overs_limit_opt) - (overs_completed + (balls_this_over / 6.0)))
        R_remaining = env.table.R(team2_overs_left_now, wkts_now)
        R2_used = max(0.0, R_start - R_remaining)

        target_full = int(dlsmod.revised_target(S1=S1, R1_total=R1_total, R2_total=R_start))
        par_now     = int(dlsmod.par_score_now(S1=S1, R1_total=R1_total, R2_used_so_far=R2_used))

        panel: DlsPanel = {"method": "DLS", "target": target_full, "par": par_now}

        # Only show 'ahead_by' in innings 2
        if int(getattr(g, "current_inning", 1) or 1) >= 2:
            runs_now = int(getattr(g, "total_runs", 0))
            panel["ahead_by"] = runs_now - par_now

        return panel
    except Exception:
        return {}


def _snapshot_from_game(
    g: GameState,
    last_delivery: Optional[Union[schemas.Delivery, Dict[str, Any]]],
) -> Dict[str, Any]:
    # Prepare last_delivery dict
    if last_delivery is None:
        last_delivery_out = None
    elif isinstance(last_delivery, BaseModel):
        last_delivery_out = last_delivery.model_dump()
    else:
        last_delivery_out = last_delivery

    # Default last_delivery to last entry in deduped ledger if still None
    if last_delivery_out is None:
        dl = _dedup_deliveries(g)
        last_delivery_out = dl[-1] if dl else None

    # Enrich last_delivery with totals
    if last_delivery_out is not None:
        ld: Mapping[str, Any] = cast(Mapping[str, Any], last_delivery_out)
        last_delivery_out = {
            **dict(ld),
            "ball_total": int(ld.get("runs_scored") or 0),
            "runs_off_bat": int(ld.get("runs_off_bat") or 0),
            "extra_runs": int(ld.get("extra_runs") or 0),
        }

    # If there is an over in progress, current bowler ...
    cur_bowler_id: Optional[str] = getattr(g, "current_bowler_id", None)
    if not cur_bowler_id and g.balls_this_over > 0:
        for d in reversed(_dedup_deliveries(g)):
            if is_legal_delivery(_norm_extra(d.get("extra_type"))):
                cur_bowler_id = str(d.get("bowler_id") or "")
                break

    flags = _compute_snapshot_flags(g)
    needs_new_over = flags["needs_new_over"]
    needs_new_batter = flags["needs_new_batter"]

    # Analyst bits
    extras_totals = _extras_breakdown(g)
    fall_of_wickets = _fall_of_wickets(g)

    snapshot: Dict[str, Any] = {
        "id": g.id,
        "status": g.status,
        "score": {
            "runs": g.total_runs,
            "wickets": g.total_wickets,
            "overs": g.overs_completed,
        },
        "overs": f"{g.overs_completed}.{g.balls_this_over}",
        "batsmen": {
            "striker": {
                "id": g.current_striker_id,
                "name": _player_name(g.team_a, g.team_b, g.current_striker_id),
                "runs": _bat_entry(g, g.current_striker_id).get("runs", 0),
                "balls": _bat_entry(g, g.current_striker_id).get("balls_faced", 0),
                "is_out": _bat_entry(g, g.current_striker_id).get("is_out", False),
            },
            "non_striker": {
                "id": g.current_non_striker_id,
                "name": _player_name(g.team_a, g.team_b, g.current_non_striker_id),
                "runs": _bat_entry(g, g.current_non_striker_id).get("runs", 0),
                "balls": _bat_entry(g, g.current_non_striker_id).get("balls_faced", 0),
                "is_out": _bat_entry(g, g.current_non_striker_id).get("is_out", False),
            },
        },
        "current_bowler": {
            "id": cur_bowler_id,
            "name": _player_name(g.team_a, g.team_b, cur_bowler_id),
        },

        # Analyst-grade fields
        "extras_totals": extras_totals,
        "fall_of_wickets": fall_of_wickets,
        "last_ball_bowler_id": getattr(g, "last_ball_bowler_id", None),

        # Original fields
        "last_delivery": last_delivery_out,
        "batting_scorecard": g.batting_scorecard,
        "bowling_scorecard": g.bowling_scorecard,
        "current_bowler_id": cur_bowler_id,
        "batting_team_name": g.batting_team_name,
        "bowling_team_name": g.bowling_team_name,
        "current_inning": g.current_inning,

        # UI flags
        "needs_new_over": needs_new_over,
        "needs_new_batter": needs_new_batter,

        # DLS panel
        "dls": _dls_panel_for(g),
    }
    return snapshot


# ================================================================
# Routes — Games
# ================================================================
@_fastapi.options("/games")
async def options_games() -> Dict[str, str]:
    payload: Dict[str, str] = {"message": "OK"}
    return payload

@_fastapi.post("/games", response_model=schemas.Game)  # type: ignore[name-defined]
async def create_game(
    payload: CreateGameRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new game with flexible format parameters and pre-seeded scorecards.
    Toss winner & decision determine the first batting side.
    """
    team_a: TeamDict = {"name": payload.team_a_name, "players": _mk_players(payload.players_a)}
    team_b: TeamDict = {"name": payload.team_b_name, "players": _mk_players(payload.players_b)}

    # Determine initial batting side from toss
    toss = payload.toss_winner_team.strip()
    if toss == payload.team_a_name:
        batting_team_name = payload.team_a_name if payload.decision == "bat" else payload.team_b_name
    elif toss == payload.team_b_name:
        batting_team_name = payload.team_b_name if payload.decision == "bat" else payload.team_a_name
    else:
        batting_team_name = payload.team_a_name  # safety fallback

    bowling_team_name = payload.team_b_name if batting_team_name == payload.team_a_name else payload.team_a_name

    # Pre-seed scorecards
    batting_scorecard = _mk_batting_scorecard(team_a if batting_team_name == payload.team_a_name else team_b)
    bowling_scorecard = _mk_bowling_scorecard(team_b if batting_team_name == payload.team_a_name else team_a)

    game_create = schemas.GameCreate(
        team_a_name=payload.team_a_name,
        team_b_name=payload.team_b_name,
        players_a=payload.players_a,
        players_b=payload.players_b,
        match_type=payload.match_type,
        overs_limit=payload.overs_limit,
        days_limit=payload.days_limit,
        overs_per_day=payload.overs_per_day,
        dls_enabled=payload.dls_enabled,
        interruptions=payload.interruptions,
        toss_winner_team=payload.toss_winner_team,
        decision=payload.decision,
    )

    game_id = str(uuid.uuid4())

    db_game = await crud.create_game(
        db=db,
        game=game_create,
        game_id=game_id,
        batting_team=batting_team_name,
        bowling_team=bowling_team_name,
        team_a=cast(Dict[str, Any], team_a),
        team_b=cast(Dict[str, Any], team_b),
        batting_scorecard=cast(Dict[str, Any], batting_scorecard),
        bowling_scorecard=cast(Dict[str, Any], bowling_scorecard),
    )

    return db_game  # Pydantic orm_mode -> schemas.Game

@_fastapi.get("/games/{game_id}", response_model=schemas.Game)  # type: ignore[name-defined]
async def get_game(game_id: str, db: AsyncSession = Depends(get_db)):
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")
    return db_game

# ------------------------------------------------
# Start a new over with selected bowler
# ------------------------------------------------
@_fastapi.post("/games/{game_id}/overs/start")
async def start_over(
    game_id: str,
    body: StartOverBody,
    db: AsyncSession = Depends(get_db),
):
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g = cast(GameState, db_game)
    if getattr(g, "current_over_balls", None) is None:
        g.current_over_balls = 0
    if getattr(g, "mid_over_change_used", None) is None:
        g.mid_over_change_used = False
    if not hasattr(g, "current_bowler_id"):
        g.current_bowler_id = None
    if not hasattr(g, "last_ball_bowler_id"):
        g.last_ball_bowler_id = None
    if getattr(g, "pending_new_over", None) is None:
        g.pending_new_over = False

    err = _can_start_over(g, body.bowler_id)
    if err:
        raise HTTPException(status_code=400, detail=err)

    g.current_bowler_id = body.bowler_id
    g.current_over_balls = 0
    g.mid_over_change_used = False
    g.pending_new_over = False

    _rebuild_scorecards_from_deliveries(g)
    _recompute_totals_and_runtime(g)

    updated = await crud.update_game(db, game_model=db_game)
    u = cast(GameState, updated)
    snap = _snapshot_from_game(u, None)
    await sio.emit("state:update", {"id": game_id, "snapshot": snap}, room=game_id)
    return {"ok": True, "current_bowler_id": g.current_bowler_id}


# ------------------------------------------------
# Mid-over bowler replacement (injury, etc.)
# ------------------------------------------------
@_fastapi.post("/games/{game_id}/overs/change_bowler")
async def change_bowler_mid_over(
    game_id: str,
    body: MidOverChangeBody,  # expects: { "new_bowler_id": "<uuid>", "reason": "injury" }
    db: AsyncSession = Depends(get_db),
):
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g = cast(GameState, db_game)

    # --- Ensure runtime attrs exist on legacy rows
    if getattr(g, "current_over_balls", None) is None:
        g.current_over_balls = 0
    if getattr(g, "mid_over_change_used", None) is None:
        g.mid_over_change_used = False
    if not hasattr(g, "current_bowler_id"):
        g.current_bowler_id = None
    if not hasattr(g, "last_ball_bowler_id"):
        g.last_ball_bowler_id = None

    # --- Rebuild runtime (sets current_bowler_id/current_over_balls correctly)
    _rebuild_scorecards_from_deliveries(g)
    _recompute_totals_and_runtime(g)
    # --- Validate state (use 409 for state conflicts)
    status_ok = str(getattr(g, "status", "in_progress")) in {"in_progress", "live", "started"}
    if not status_ok:
        raise HTTPException(status_code=409, detail=f"Game is {getattr(g, 'status', 'unknown')}")

    balls_this_over = int(getattr(g, "current_over_balls", 0) or 0)
    current = getattr(g, "current_bowler_id", None)

    # No active bowler yet or over not in progress -> ask client to use /overs/start
    if not current or balls_this_over <= 0:
        raise HTTPException(status_code=409, detail="Over not in progress; use /overs/start")

    if getattr(g, "mid_over_change_used", False):
        raise HTTPException(status_code=409, detail="Mid-over change already used this over")

    if str(body.new_bowler_id) == str(current):
        raise HTTPException(status_code=409, detail="New bowler is already the current bowler")

    # Must belong to the bowling team
    # Must belong to the bowling team
    bowling_team_name = getattr(g, "bowling_team_name", None)
    team_a = cast(TeamDict, getattr(g, "team_a"))
    team_b = cast(TeamDict, getattr(g, "team_b"))
    if not (bowling_team_name and team_a and team_b):
        raise HTTPException(status_code=500, detail="Teams not initialized on game")

    bowling_team: TeamDict = team_a if team_a["name"] == bowling_team_name else team_b
    allowed = {str(p["id"]) for p in (bowling_team.get("players", []) or [])}
    if str(body.new_bowler_id) not in allowed:
        raise HTTPException(status_code=409, detail="Bowler is not in the bowling team")

    # --- Apply change (do NOT touch last_ball_bowler_id; that’s an over-boundary concept)
    g.current_bowler_id = str(body.new_bowler_id)
    g.mid_over_change_used = True

    # Recompute & persist
    _recompute_totals_and_runtime(g)
    updated = await crud.update_game(db, game_model=db_game)
    u = cast(GameState, updated)

    # Build/augment snapshot so UI has everything it needs immediately
    snap = _snapshot_from_game(u, None)
    # Ensure runtime keys are present in snapshot payload:
    snap["current_bowler_id"] = g.current_bowler_id
    snap["last_ball_bowler_id"] = g.last_ball_bowler_id
    snap["current_over_balls"] = g.current_over_balls
    snap["mid_over_change_used"] = g.mid_over_change_used
    snap["needs_new_over"] = bool(getattr(g, "needs_new_over", False))

    await sio.emit("state:update", {"id": game_id, "snapshot": snap}, room=game_id)
    return snap  # return full snapshot, not just {"ok": true}

# ================================================================
# PR 1 — Record a delivery (with dismissal rules)
# ================================================================
@_fastapi.post("/games/{game_id}/deliveries")
async def add_delivery(
    game_id: str,
    delivery: schemas.ScoreDelivery,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    print("main.add_delivery handler active", flush=True)

    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g = cast(GameState, db_game)

    # --- Debug: incoming payload ------------------------------------------------
    print(
        "add_delivery> payload",
        dict(
            striker_id=delivery.striker_id,
            non_striker_id=delivery.non_striker_id,
            bowler_id=delivery.bowler_id,
            extra=str(delivery.extra or None),
            runs_scored=delivery.runs_scored,
            runs_off_bat=delivery.runs_off_bat,
            is_wicket=delivery.is_wicket,
        ),
        flush=True,
    )

    # --- BEFORE rebuild snapshot ------------------------------------------------
    print(
        "add_delivery> BEFORE rebuild",
        dict(
            cbi=getattr(g, "current_bowler_id", None),
            lbi=getattr(g, "last_ball_bowler_id", None),
            bto=getattr(g, "balls_this_over", None),
            oc=getattr(g, "overs_completed", None),
        ),
        flush=True,
    )

    # Preserve selections made by /overs/start or earlier API calls
    active_bowler_id = getattr(g, "current_bowler_id", None)
    mid_over_change_used = getattr(g, "mid_over_change_used", False)

    # --- Rebuild from authoritative ledger -------------------------------------
    _rebuild_scorecards_from_deliveries(g)
    _recompute_totals_and_runtime(g)

    # --- AFTER rebuild snapshot -------------------------------------------------
    print(
        "add_delivery> AFTER rebuild",
        dict(
            cbi=getattr(g, "current_bowler_id", None),
            lbi=getattr(g, "last_ball_bowler_id", None),
            bto=getattr(g, "balls_this_over", None),
            oc=getattr(g, "overs_completed", None),
        ),
        flush=True,
    )

    # --- Mid-over bowler change (fallback if frontend sends a different bowler) -
    if int(getattr(g, "balls_this_over", 0)) > 0:
        cur = getattr(g, "current_bowler_id", None)
        incoming = str(delivery.bowler_id)
        if cur and incoming != cur:
            if getattr(g, "mid_over_change_used", False):
                raise HTTPException(status_code=409, detail="Mid-over change already used this over")

            # Optional safety: ensure incoming is a member of the bowling team
            bowling_team_name = getattr(g, "bowling_team_name", None)
            team_a = cast(TeamDict, getattr(g, "team_a"))
            team_b = cast(TeamDict, getattr(g, "team_b"))
            bowling_team: TeamDict = team_a if team_a["name"] == bowling_team_name else team_b
            allowed = {str(p["id"]) for p in (bowling_team.get("players", []) or [])}
            if incoming not in allowed:
                raise HTTPException(status_code=409, detail="Bowler is not in the bowling team")

            g.current_bowler_id = incoming
            g.mid_over_change_used = True

    # --- Start-of-over handling -------------------------------------------------
    # If we’re at the very start of a fresh over (0 balls), keep any chosen bowler
    if active_bowler_id and int(getattr(g, "balls_this_over", 0)) == 0:
        g.current_bowler_id = active_bowler_id
        g.mid_over_change_used = mid_over_change_used
    if not delivery.bowler_id and delivery.bowler_name:
        resolved = _id_by_name(g.team_a, g.team_b, delivery.bowler_name)
        if not resolved:
            raise HTTPException(status_code=404, detail="Unknown bowler name")
        delivery.bowler_id = resolved

    # If still none set at ball 0, take the payload bowler (first ball)
    if int(getattr(g, "balls_this_over", 0)) == 0 and not getattr(g, "current_bowler_id", None):
        g.current_bowler_id = delivery.bowler_id
        g.mid_over_change_used = False
        print("add_delivery> injected cbi from payload at ball 0:", g.current_bowler_id, flush=True)

    needs_fielder = bool(delivery.is_wicket and str(getattr(delivery, "dismissal_type", "")).lower() in {"caught", "run_out", "stumped"})
    if needs_fielder and not delivery.fielder_id and delivery.fielder_name:
        resolved = _id_by_name(g.team_a, g.team_b, delivery.fielder_name)
        if not resolved:
            raise HTTPException(status_code=404, detail="Unknown fielder name")
        delivery.fielder_id = resolved
    # --- UI gating flags & guards ----------------------------------------------
    flags = _compute_snapshot_flags(g)

    # If a bowler is set and we're at ball 0, never demand "new over" again
    if getattr(g, "current_bowler_id", None) and int(getattr(g, "balls_this_over", 0)) == 0:
        print("add_delivery> soft-bypass needs_new_over (have cbi at ball 0)", flush=True)
        flags["needs_new_over"] = False

    print("add_delivery> FLAGS", flags, flush=True)

    if flags.get("needs_new_batter"):
        print("add_delivery> BLOCK 409: needs_new_batter", flush=True)
        raise HTTPException(status_code=409, detail="Select a new batter before scoring the next ball.")

    if flags.get("needs_new_over"):
        msg = (
            f"Start a new over and select a bowler before scoring. "
            f"(debug bto={g.balls_this_over}, cbi={g.current_bowler_id}, lbi={getattr(g,'last_ball_bowler_id',None)})"
        )
        print("add_delivery> BLOCK 409:", msg, flush=True)
        raise HTTPException(status_code=409, detail=msg)

    # --- No consecutive overs by same bowler when a new over starts -------------
    last_id = getattr(g, "last_ball_bowler_id", None)
    eff_bowler = getattr(g, "current_bowler_id", None) or delivery.bowler_id
    if int(getattr(g, "balls_this_over", 0)) == 0 and last_id and eff_bowler == last_id:
        raise HTTPException(status_code=400, detail="Bowler cannot bowl consecutive overs")

    # --- Normalize delivery + score one ball -----------------------------------
    x = _norm_extra(delivery.extra)
    kwargs: DeliveryKwargs

    if x == "nb":
        off_bat = int(delivery.runs_off_bat or 0)
        kwargs = _score_one(
            g,
            striker_id=delivery.striker_id,
            non_striker_id=delivery.non_striker_id,
            bowler_id=delivery.bowler_id,
            runs_scored=off_bat,       # off-bat on no-ball
            extra="nb",
            is_wicket=bool(delivery.is_wicket),
            dismissal_type=delivery.dismissal_type,
            dismissed_player_id=delivery.dismissed_player_id,
        )
    elif x in ("wd", "b", "lb"):
        extra_runs = int(delivery.runs_scored or 0)
        kwargs = _score_one(
            g,
            striker_id=delivery.striker_id,
            non_striker_id=delivery.non_striker_id,
            bowler_id=delivery.bowler_id,
            runs_scored=extra_runs,    # extras count
            extra=x,
            is_wicket=bool(delivery.is_wicket),
            dismissal_type=delivery.dismissal_type,
            dismissed_player_id=delivery.dismissed_player_id,
        )
    else:
        batter_runs = int(delivery.runs_scored or 0)
        kwargs = _score_one(
            g,
            striker_id=delivery.striker_id,
            non_striker_id=delivery.non_striker_id,
            bowler_id=delivery.bowler_id,
            runs_scored=batter_runs,   # off-bat for legal ball
            extra=None,
            is_wicket=bool(delivery.is_wicket),
            dismissal_type=delivery.dismissal_type,
            dismissed_player_id=delivery.dismissed_player_id,
        )

    # --- Append to ledger once --------------------------------------------------
    del_dict: Dict[str, Any] = schemas.Delivery(**kwargs).model_dump()
    if not isinstance(g.deliveries, list):  # type: ignore
        g.deliveries = []  # type: ignore[assignment]
        flag_modified(db_game, "deliveries")
    g.deliveries.append(del_dict)

    # Ensure runtime attrs always exist
    if getattr(g, "current_over_balls", None) is None:
        g.current_over_balls = 0
    if getattr(g, "mid_over_change_used", None) is None:
        g.mid_over_change_used = False
    if not hasattr(g, "current_bowler_id"):
        g.current_bowler_id = None
    if not hasattr(g, "last_ball_bowler_id"):
        g.last_ball_bowler_id = None

    flag_modified(db_game, "deliveries")

    # --- Rebuild scorecards from authoritative ledger --------------------------
    _rebuild_scorecards_from_deliveries(g)
    _recompute_totals_and_runtime(g)
    flag_modified(db_game, "batting_scorecard")
    flag_modified(db_game, "bowling_scorecard")

    # --- Persist ----------------------------------------------------------------
    updated = await crud.update_game(db, game_model=db_game)
    u = cast(GameState, updated)

    # --- Build snapshot + final flags ------------------------------------------
    last = u.deliveries[-1] if u.deliveries else None
    snap = _snapshot_from_game(u, last)
    final_flags = _compute_snapshot_flags(u)
    snap["needs_new_batter"] = final_flags["needs_new_batter"]
    snap["needs_new_over"] = final_flags["needs_new_over"]

    # Ensure ID fields present for frontend
    cur_bowler_from_obj: Optional[str] = None
    cb_any = snap.get("current_bowler")
    if isinstance(cb_any, dict):
        cb_map: Mapping[str, Any] = cast(Mapping[str, Any], cb_any)
        cur_bowler_from_obj = cast(Optional[str], cb_map.get("id"))

    snap["current_bowler_id"] = cast(
        Optional[str],
        snap.get("current_bowler_id") or cur_bowler_from_obj or getattr(u, "current_bowler_id", None),
    )
    snap["last_ball_bowler_id"] = cast(
        Optional[str],
        snap.get("last_ball_bowler_id") or getattr(u, "last_ball_bowler_id", None),
    )

    await sio.emit("state:update", {"id": game_id, "snapshot": snap}, room=game_id)
    return snap




class ReplaceBatterBody(BaseModel):
    new_batter_id: str

@_fastapi.post("/games/{game_id}/batters/replace")
async def replace_batter(
    game_id: str,
    body: ReplaceBatterBody,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")
    g = cast(GameState, db_game)

    # Ensure latest state
    _rebuild_scorecards_from_deliveries(g)
    _recompute_totals_and_runtime(g)

    # Determine which current batter is out
    def _is_out(pid: Optional[str]) -> bool:
        if not pid:
            return False
        e = g.batting_scorecard.get(pid) or {}
        if isinstance(e, BaseModel):
            e = e.model_dump()
        return bool(e.get("is_out", False))

    if _is_out(g.current_striker_id):
        g.current_striker_id = body.new_batter_id
    elif _is_out(g.current_non_striker_id):
        g.current_non_striker_id = body.new_batter_id
    else:
        raise HTTPException(status_code=409, detail="No striker or non-striker requires replacement.")

    # Ensure scorecard entry exists for the incoming batter
    _ensure_batting_entry(g, body.new_batter_id)

    flag_modified(db_game, "batting_scorecard")
    updated = await crud.update_game(db, game_model=db_game)
    u = cast(GameState, updated)

    # Respond with fresh snapshot + flags
    last = _dedup_deliveries(u)[-1] if u.deliveries else None
    snap = _snapshot_from_game(u, last)
    flags = _compute_snapshot_flags(u)
    snap["needs_new_batter"] = flags["needs_new_batter"]
    snap["needs_new_over"] = flags["needs_new_over"]

    await sio.emit("state:update", {"id": game_id, "snapshot": snap}, room=game_id)
    return snap


@_fastapi.post("/games/{game_id}/next-batter")
async def set_next_batter(
    game_id: str,
    body: NextBatterBody,
    db: AsyncSession = Depends(get_db),
):
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g = cast(GameState, db_game)
    if getattr(g, "pending_new_batter", None) is None:
        g.pending_new_batter = False

    # If no replacement is required, no-op
    if not g.pending_new_batter:
        return {"ok": True, "message": "No replacement batter required"}

    # Choose where to insert the new batter:
    # Convention: new batter always becomes the striker after a wicket
    g.current_striker_id = body.batter_id

    # make sure entry exists
    _ensure_batting_entry(g, body.batter_id)

    g.pending_new_batter = False

    _rebuild_scorecards_from_deliveries(g)
    _recompute_totals_and_runtime(g)

    updated = await crud.update_game(db, game_model=db_game)
    u = cast(GameState, updated)
    snap = _snapshot_from_game(u, None)
    await sio.emit("state:update", {"id": game_id, "snapshot": snap}, room=game_id)
    return {"ok": True, "current_striker_id": g.current_striker_id}



# ================================================================
# PR 2 — Undo last ball (full state recompute from ledger)
# ================================================================
@_fastapi.post("/games/{game_id}/undo-last")
async def undo_last_delivery(game_id: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g = cast(GameState, db_game)
    if not g.deliveries:
        raise HTTPException(status_code=409, detail="Nothing to undo")

    g.deliveries = g.deliveries[:-1]  # type: ignore[assignment]
    _reset_runtime_and_scorecards(g)
    deliveries5: Sequence[Union[BaseModel, Mapping[str, Any]]] = cast(
        Sequence[Union[BaseModel, Mapping[str, Any]]],
        g.deliveries,
    )
    for d_any in deliveries5:
        d = d_any.model_dump() if isinstance(d_any, BaseModel) else dict(d_any)

        x = _norm_extra(d.get("extra_type"))
        if x == "nb":
            rs = int(d.get("runs_off_bat") or 0)   # off-bat only
        elif x in ("wd", "b", "lb"):
            rs = int(d.get("extra_runs") or 0)     # extras count
        else:
            rs = int(d.get("runs_off_bat") or 0)   # legal ball off-bat

        _ = _score_one(
            g,
            striker_id=str(d.get("striker_id", "")),
            non_striker_id=str(d.get("non_striker_id", "")),
            bowler_id=str(d.get("bowler_id", "")),
            runs_scored=rs,
            extra=x,
            is_wicket=bool(d.get("is_wicket")),
            dismissal_type=d.get("dismissal_type"),
            dismissed_player_id=d.get("dismissed_player_id"),
        )

    updated = await crud.update_game(db, game_model=db_game)  # <-- pass ORM row
    u = cast(GameState, updated)
    _rebuild_scorecards_from_deliveries(u)
    last = u.deliveries[-1] if u.deliveries else None
    snapshot = _snapshot_from_game(u, last)

    await sio.emit("state:update", {"id": game_id, "snapshot": snapshot}, room=game_id)
    return snapshot



# ================================================================
# PR 4 — Rain control: adjust overs limit mid-match
# ================================================================
@_fastapi.post("/games/{game_id}/dls/revised-target", response_model=DLSRevisedOut)
async def dls_revised_target(game_id: str, body: DLSRequest, db: AsyncSession = Depends(get_db)):
    game = await crud.get_game(db, game_id=game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    
    # allow attribute access without tripping strict type checkers
    g = cast(Any, game)

    # Load env
    env = dlsmod.load_env(body.kind, str(BASE_DIR))

    # Team 1 runs are just g.total_runs at end of inns 1; if called mid‑match, use snapshot
    # We infer from deliveries in innings 1:
    # total_resources_team1 expects List[Mapping[str, Any]] (list is invariant)
    deliveries_m: List[Mapping[str, Any]] = cast(
        List[Mapping[str, Any]],
        list(getattr(g, "deliveries", []))
    )
    # In this simple model you keep a single combined ledger; if you split per-innings, adjust here.

    # Team 1 resources
    M1 = int(body.max_overs or (g.overs_limit or (50 if body.kind == "odi" else 20)))
    interruptions = list(getattr(g, "interruptions", []))
    R1_total = dlsmod.total_resources_team1(
        env=env,
        max_overs_initial=M1,
        deliveries=deliveries_m,
        interruptions=interruptions,
    )

    # Team 1 score (at the end of inns 1 you’ll pass actual S1; if called earlier, use current)
    S1 = int(getattr(g, "total_runs", 0))

    # Team 2 resources (available) = R(u,w) at start (w=0, u=M2)
    M2 = int(body.max_overs or (g.overs_limit or (50 if body.kind == "odi" else 20)))
    R2_total = env.table.R(M2, 0)

    target = dlsmod.revised_target(S1=S1, R1_total=R1_total, R2_total=R2_total)
    return DLSRevisedOut(R1_total=R1_total, R2_total=R2_total, S1=S1, target=target)

@_fastapi.post("/games/{game_id}/dls/par", response_model=DLSParOut)
async def dls_par_now(game_id: str, body: DLSRequest, db: AsyncSession = Depends(get_db)):
    game = await crud.get_game(db, game_id=game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    g = cast(Any, game)
    env = dlsmod.load_env(body.kind, str(BASE_DIR))

    # Inputs from state
    deliveries_m: List[Mapping[str, Any]] = cast(
        List[Mapping[str, Any]],
        list(getattr(g, "deliveries", []))
    )
    M = int(body.max_overs or (g.overs_limit or (50 if body.kind == "odi" else 20)))

    # Team 1 resources (as above)
    R1_total = dlsmod.total_resources_team1(
        env=env,
        max_overs_initial=M,
        deliveries=deliveries_m,
        interruptions=list(getattr(g, "interruptions", [])),
    )
    S1 = int(getattr(g, "total_runs", 0))  # score to chase

    # Team 2 “used so far” during chase
    # Use current (balls bowled, wickets) from runtime fields:
    balls_so_far = int(getattr(g, "overs_completed", 0)) * 6 + int(getattr(g, "balls_this_over", 0))
    wkts_so_far = int(getattr(g, "total_wickets", 0))  # second innings wickets at the moment

    # Resources used = R(start) - R(remaining)
    R_start = env.table.R(M, 0)
    R_remaining = env.table.R(max(0.0, M - (balls_so_far / 6.0)), wkts_so_far)
    R2_used = max(0.0, R_start - R_remaining)

    par = dlsmod.par_score_now(S1=S1, R1_total=R1_total, R2_used_so_far=R2_used)
    # Team 2 current runs live (from g.total_runs if you switch this route only during inns 2).
    runs_now = int(getattr(g, "total_runs", 0))
    return DLSParOut(R1_total=R1_total, R2_used=R2_used, S1=S1, par=par, ahead_by=runs_now - par)

@_fastapi.post("/games/{game_id}/overs-limit")
async def set_overs_limit(
    game_id: str,
    body: OversLimitBody,
    db: AsyncSession = Depends(get_db),
):
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g = cast(GameState, db_game)
    bowled_balls = g.overs_completed * 6 + g.balls_this_over
    new_limit_balls = int(body.overs_limit) * 6
    if new_limit_balls < bowled_balls:
        raise HTTPException(status_code=400, detail="New limit is less than overs already bowled")

    # First, set the new limit (validated above), then (optionally) compute DLS off the NEW limit
    g.overs_limit = int(body.overs_limit)
    # DLS computation only when Team 1 completed or reduced between innings, and Team 2 innings in play
    
        
    try:
        interruptions = list(getattr(g, "interruptions", []))
    except Exception:
        interruptions = []
    interruptions.append({
        "type": "overs_reduction",
        "at_delivery_index": len(getattr(g, "deliveries", []) or []),
        "new_overs_limit": int(body.overs_limit),
    })
    g.interruptions = interruptions  # persist

    g.overs_limit = int(body.overs_limit)
    updated = await crud.update_game(db, game_model=db_game)

    # (Nice to have) emit a fresh snapshot so viewers update immediately
    u = cast(GameState, updated)
    last = _dedup_deliveries(u)[-1] if u.deliveries else None
    snap = _snapshot_from_game(u, last)
    await sio.emit("state:update", {"id": game_id, "snapshot": snap}, room=game_id)

    return {"id": game_id, "overs_limit": cast(GameState, updated).overs_limit}
# ================================================================
# PR 5 — GET game snapshot (viewer bootstrap)
# ================================================================
@_fastapi.get("/games/{game_id}/snapshot")
async def get_snapshot(game_id: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    game = await crud.get_game(db, game_id=game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    g = cast(GameState, game)
    # Ensure runtime fields exist
    if getattr(g, "current_over_balls", None) is None:
        g.current_over_balls = 0
    if getattr(g, "mid_over_change_used", None) is None:
        g.mid_over_change_used = False
    if not hasattr(g, "current_bowler_id"):
        g.current_bowler_id = None
    if not hasattr(g, "last_ball_bowler_id"):
        g.last_ball_bowler_id = None

    # Always rebuild from ledger BEFORE any derived panels (ensures fresh totals)
    _rebuild_scorecards_from_deliveries(g)
    _recompute_totals_and_runtime(g)

    last = _dedup_deliveries(g)[-1] if g.deliveries else None
    snap = _snapshot_from_game(g, last)

    # UI gating flags
    flags = _compute_snapshot_flags(g)
    snap["needs_new_batter"] = flags["needs_new_batter"]
    snap["needs_new_over"] = flags["needs_new_over"]

    # Interruption records + mini cards
    snap["interruptions"] = cast(List[InterruptionRec], getattr(g, "interruptions", []) or [])
    snap["mini_batting_card"] = _mini_batting_card(g)
    snap["mini_bowling_card"] = _mini_bowling_card(g)

    # DLS panel (best-effort; compute AFTER totals)
    snap_dls: DlsPanel = {}
    try:
        overs_limit_opt = cast(Optional[int], getattr(g, "overs_limit", None))
        current_innings = int(getattr(g, "current_inning", 1) or 1)
        if isinstance(overs_limit_opt, int) and current_innings >= 2 and overs_limit_opt in (20, 50):
            format_overs = int(overs_limit_opt)
            kind = "odi" if format_overs >= 40 else "t20"
            env = dlsmod.load_env(kind, str(BASE_DIR))

            deliveries_m: List[Mapping[str, Any]] = cast(
                List[Mapping[str, Any]],
                list(getattr(g, "deliveries", []))
            )
            interruptions = list(getattr(g, "interruptions", []))

            # Team 1 resources from ledger + interruptions
            R1_total = dlsmod.total_resources_team1(
                env=env,
                max_overs_initial=format_overs,
                deliveries=deliveries_m,
                interruptions=interruptions,
            )
            # Team 1 score (best-effort; assumes S1 available as total_runs at innings break)
            S1 = int(getattr(g, "total_runs", 0))

            # Team 2 live usage for a quick par
            overs_completed = float(getattr(g, "overs_completed", 0.0) or 0.0)
            balls_this_over = float(getattr(g, "balls_this_over", 0.0) or 0.0)
            team2_overs_left_now = max(0.0, float(format_overs) - (overs_completed + (balls_this_over / 6.0)))
            team2_wkts_now = int(getattr(g, "total_wickets", 0)) if current_innings == 2 else 0

            R_start = env.table.R(format_overs, 0)
            R_remaining = env.table.R(team2_overs_left_now, team2_wkts_now)
            R2_used = max(0.0, R_start - R_remaining)

            par_now = int(dlsmod.par_score_now(S1=S1, R1_total=R1_total, R2_used_so_far=R2_used))
            target_full = int(dlsmod.revised_target(S1=S1, R1_total=R1_total, R2_total=R_start))

            snap_dls = {"method": "DLS", "par": par_now, "target": target_full}
    except Exception:
        snap_dls = {}

    snap["dls"] = snap_dls

    # Enrich for bootstrap (team names + player lists)
    snap["teams"] = {
        "batting": {"name": g.batting_team_name},
        "bowling": {"name": g.bowling_team_name},
    }
    snap["players"] = {
        "batting": [{"id": p["id"], "name": p["name"]} for p in (g.team_a if g.batting_team_name == g.team_a["name"] else g.team_b)["players"]],
        "bowling": [{"id": p["id"], "name": p["name"]} for p in (g.team_b if g.batting_team_name == g.team_a["name"] else g.team_a)["players"]],
    }
    return snap

@runtime_checkable
class _SupportsModelDump(Protocol):
    def model_dump(self) -> Mapping[str, Any]: ...

@runtime_checkable
class _SupportsDict(Protocol):
    def dict(self) -> Mapping[str, Any]: ...

def _to_str_any_dict(d: Mapping[Any, Any]) -> Dict[str, Any]:
    """Coerce any mapping (any key type) to Dict[str, Any]."""
    return {str(k): v for k, v in d.items()}

def _model_to_dict(x: Any) -> Optional[Dict[str, Any]]:
    # Already a dict-like object
    if isinstance(x, dict):
        # dict[str, Any] is a Mapping[Any, Any] at runtime; let helper normalize keys
        return _to_str_any_dict(cast(Mapping[Any, Any], x))

    # Pydantic v2 first
    if isinstance(x, BaseModel):
        try:
            md = x.model_dump()  # -> Mapping[str, Any]
            return _to_str_any_dict(md)
        except Exception:
            # v1 fallback
            try:
                md = x.dict()  # type: ignore[attr-defined]
                return _to_str_any_dict(md)
            except Exception:
                return None

    # Duck-typed objects with typed model_dump()/dict()
    if isinstance(x, _SupportsModelDump):
        try:
            md = x.model_dump()
            return _to_str_any_dict(md)
        except Exception:
            return None

    if isinstance(x, _SupportsDict):
        try:
            md = x.dict()
            return _to_str_any_dict(md)
        except Exception:
            return None

    # Last-resort getattr path
    for attr in ("model_dump", "dict"):
        fn = getattr(x, attr, None)
        if callable(fn):
            try:
                data = fn()
                if isinstance(data, dict):
                    # Accept any key type, normalize to str keys
                    return _to_str_any_dict(cast(Mapping[Any, Any], data))
                return None
            except Exception:
                return None

    return None



    


@_fastapi.get("/games/{game_id}/recent_deliveries")
async def get_recent_deliveries(
    game_id: str,
    limit: int = Query(10, ge=1, le=50, description="Max number of most recent deliveries"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns the most-recent `limit` deliveries for a game, newest-first.
    Each delivery matches schemas.Delivery (wire-safe dict).
    """
    game = await crud.get_game(db, game_id=game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    g = cast(GameState, game)

    # Slice last N from the authoritative ledger, newest-first
    raw_seq: Sequence[Any] = getattr(g, "deliveries", []) or []
    tail: List[Any] = list(raw_seq)[-limit:][::-1]

    # Normalize each item to a dict
    ledger: List[Dict[str, Any]] = []
    for item in tail:
        d = _model_to_dict(item)
        if d is not None:
            ledger.append(d)

    # Validate/shape with Pydantic; help Pylance via a cast to DeliveryKwargs
    out: List[Dict[str, Any]] = []
    for d_any in ledger:
        try:
            d_kw = cast(DeliveryKwargs, d_any)            # <-- silences “unknown argument type”
            model = schemas.Delivery(**d_kw)
            out.append(model.model_dump())                # Pydantic v2
        except Exception:
            # Optional Pydantic v1 fallback:
            try:
                model = schemas.Delivery(**d_any)         # type: ignore[call-arg]
                out.append(model.dict())                  # type: ignore[attr-defined]
            except Exception:
                continue

    # Enrich with names
    for row in out:
        row["striker_name"] = _player_name(g.team_a, g.team_b, row.get("striker_id"))
        row["non_striker_name"] = _player_name(g.team_a, g.team_b, row.get("non_striker_id"))
        row["bowler_name"] = _player_name(g.team_a, g.team_b, row.get("bowler_id"))

    return {
        "game_id": game_id,
        "count": len(out),
        "deliveries": out,  # newest-first
    }




# ================================================================
# OPTIONAL — Explicitly set openers (quality-of-life)
# ================================================================
@_fastapi.post("/games/{game_id}/openers")
async def set_openers(
    game_id: str,
    body: Dict[str, str],
    db: AsyncSession = Depends(get_db),
):
    # Fetch ORM row
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Cast for cricket-logic ergonomics (same object instance)
    g = cast(GameState, db_game)

    striker_id = str(body.get("striker_id") or "")
    non_striker_id = str(body.get("non_striker_id") or "")

    g.current_striker_id = striker_id
    g.current_non_striker_id = non_striker_id

    # IMPORTANT: pass the ORM object to CRUD, not the GameState-typed alias
    updated = await crud.update_game(db, game_model=db_game)

    # Cast the updated ORM row back to GameState for snapshotting
    u = cast(GameState, updated)

    _rebuild_scorecards_from_deliveries(u)
    _recompute_totals_and_runtime(u)

    snap = _snapshot_from_game(u, None)
    await sio.emit("state:update", {"id": game_id, "snapshot": snap}, room=game_id)
    return snap


# ================================================================
# Team Roles (captain / wicket-keeper)
# ================================================================
@_fastapi.post("/games/{game_id}/team-roles")
async def set_team_roles(
    game_id: str,
    payload: schemas.TeamRoleUpdate,
    db: AsyncSession = Depends(get_db),
):
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g = cast(GameState, db_game)
    players = (g.team_a.get("players", []) if payload.side == schemas.TeamSide.A else g.team_b.get("players", []))
    player_ids = {p["id"] for p in players}

    if payload.captain_id and payload.captain_id not in player_ids:
        raise HTTPException(status_code=400, detail="captain_id not in team players")
    if payload.wicket_keeper_id and payload.wicket_keeper_id not in player_ids:
        raise HTTPException(status_code=400, detail="wicket_keeper_id not in team players")

    if payload.side == schemas.TeamSide.A:
        g.team_a_captain_id = payload.captain_id
        g.team_a_keeper_id = payload.wicket_keeper_id
    else:
        g.team_b_captain_id = payload.captain_id
        g.team_b_keeper_id = payload.wicket_keeper_id

    await crud.update_game(db, game_model=db_game)  # <-- pass ORM row
    return {
        "ok": True,
        "team_roles": {
            "A": {"captain_id": g.team_a_captain_id, "wicket_keeper_id": g.team_a_keeper_id},
            "B": {"captain_id": g.team_b_captain_id, "wicket_keeper_id": g.team_b_keeper_id},
        },
    }

# ================================================================
# PR 8 — Sponsor upload endpoint
# ================================================================
@_fastapi.post("/sponsors")
async def create_sponsor(
    name: str = Form(...),
    logo: UploadFile = File(...),
    click_url: Optional[str] = Form(None),
    weight: int = Form(1),
    surfaces: Optional[str] = Form(None),   # JSON array as string, e.g. '["all"]'
    start_at: Optional[str] = Form(None),   # ISO-8601, e.g. '2025-08-11T14:00:00Z'
    end_at: Optional[str] = Form(None),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    # Validate weight
    if weight < 1 or weight > 5:
        raise HTTPException(status_code=400, detail="weight must be between 1 and 5")

    # Read file (limit 5MB)
    data = await logo.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="File exceeds 5MB limit")

    ext = _detect_image_ext(data, logo.content_type, logo.filename)
    if ext is None:
        raise HTTPException(status_code=400, detail="Only SVG, PNG or WebP images are allowed")

    # Surfaces parsing — ensure a list[str]
    try:
        parsed_any: Any = json.loads(surfaces) if surfaces else ["all"]
    except Exception:
        raise HTTPException(status_code=400, detail="surfaces must be a JSON array of strings")

    if not isinstance(parsed_any, list):
        raise HTTPException(status_code=400, detail="surfaces must be a JSON array of strings")

    parsed_list: List[Any] = cast(List[Any], parsed_any)
    for itm in parsed_list:
        if not isinstance(itm, str):
            raise HTTPException(status_code=400, detail="surfaces must be a JSON array of strings")
    surfaces_list: List[str] = [str(itm) for itm in parsed_list] or ["all"]

    # Date parsing
    start_dt = _parse_iso_dt(start_at)
    end_dt = _parse_iso_dt(end_at)

    # Save to static/sponsors/<uuid>.<ext>
    sponsors_dir = os.path.join(STATIC_DIR, "sponsors")
    os.makedirs(sponsors_dir, exist_ok=True)

    fid = str(uuid.uuid4())
    filename = f"{fid}.{ext}"
    fpath = os.path.join(sponsors_dir, filename)
    with open(fpath, "wb") as f:
        f.write(data)

    # Persist DB row
    rec = models.Sponsor(
        name=name,
        logo_path=f"sponsors/{filename}",
        click_url=click_url,
        weight=int(weight),
        surfaces=surfaces_list,
        start_at=start_dt,
        end_at=end_dt,
    )
    db.add(rec)
    await db.commit()
    await db.refresh(rec)

    # Public URL (served by PR 7 static mount)
    logo_url = f"/static/{rec.logo_path}"

    return {
        "id": rec.id,
        "name": rec.name,
        "logo_url": logo_url,
        "click_url": rec.click_url,
        "weight": rec.weight,
        "surfaces": rec.surfaces,
        "start_at": _iso_or_none(rec.start_at),
        "end_at": _iso_or_none(rec.end_at),
        "created_at": _iso_or_none(rec.created_at),
        "updated_at": _iso_or_none(rec.updated_at),
    }

# ================================================================
# PR 9 — Per-game sponsors lineup (time-gated, v1 global)
# ================================================================
@_fastapi.get("/games/{game_id}/sponsors")
async def get_game_sponsors(
    game_id: str,
    db: AsyncSession = Depends(get_db),
) -> List[Dict[str, Any]]:
    """
    Return all *active* sponsors at the current time window.
    v1: global pool (ignores league/season/game assignment).
    """
    # Ensure the game exists (keeps semantics per-game)
    game = await crud.get_game(db, game_id=game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    now = datetime.now(timezone.utc)

    Sponsor = models.Sponsor
    conditions = [
        or_(Sponsor.start_at.is_(None), Sponsor.start_at <= now),
        or_(Sponsor.end_at.is_(None), Sponsor.end_at >= now),
    ]
    if hasattr(Sponsor, "is_active"):
        conditions.append(getattr(Sponsor, "is_active") == True)  # noqa: E712

    stmt = (
        select(Sponsor)
        .where(and_(*conditions))
        .order_by(Sponsor.weight.desc(), Sponsor.created_at.desc())
    )
    res = await db.execute(stmt)
    # ...
    rows = res.scalars().all()

    out: List[Dict[str, Any]] = []
    for r in rows:
        rid: int = int(r.id)
        name: str = str(r.name)
        logo_path: str = str(r.logo_path)
        click_url: Optional[str] = str(r.click_url) if r.click_url is not None else None
        weight: int = int(r.weight)

        raw_surfaces_any: Any = getattr(r, "surfaces", None)
        if isinstance(raw_surfaces_any, (list, tuple)):
            # item is Any (not Unknown), so str(item) is fine for Pylance
            surfaces: List[str] = (r.surfaces or ["all"])
        else:
            surfaces = ["all"]

        out.append(
            {
                "id": rid,
                "name": name,
                "logoUrl": f"/static/{logo_path}",
                "clickUrl": click_url,
                "weight": weight,
                "surfaces": surfaces,
            }
        )
    return out

@_fastapi.get("/static/sponsors/{brand}/manifest.json")
def sponsors_manifest(brand: str) -> SponsorsManifest:
    items: List[SponsorItem] = [
        {"logoUrl": f"/static/sponsors/{brand}/Cricksy.png",       "alt": "Cricksy",           "rail": "left",  "maxPx": 120},
        {"logoUrl": f"/static/sponsors/{brand}/Cricksy_no_bg.png", "alt": "Cricksy (no bg)",   "rail": "right", "maxPx": 140},
        {"logoUrl": f"/static/sponsors/{brand}/Cricksy_mono.png",  "alt": "Presented by Cricksy"},
        { "logoUrl": "/static/sponsors/cricksy/Cricksy_outline.png",         "alt": "Cricksy outline" },
        { "logoUrl": "/static/sponsors/cricksy/Cricksy_Black_&_white.png",   "alt": "Cricksy B/W" },
        { "logoUrl": "/static/sponsors/cricksy/Cricksy_colored_circle.png",  "alt": "Cricksy circle" },
    ]
    return {"items": items}
# ================================================================
# PR 10 — Impression logging (proof-of-play)
# ================================================================
@_fastapi.post("/sponsor_impressions", response_model=SponsorImpressionsOut)
async def log_sponsor_impressions(
    body: Union[SponsorImpressionIn, List[SponsorImpressionIn]],
    db: AsyncSession = Depends(get_db),
):
    # Normalize to list, enforce batch limit
    items: List[SponsorImpressionIn]
    if isinstance(body, list):
        items = body
    else:
        items = [body]

    if len(items) == 0:
        raise HTTPException(status_code=400, detail="Empty payload")
    if len(items) > 20:
        raise HTTPException(status_code=400, detail="Batch too large; max 20")

    # Optional referential checks (cheap existence validation)
    # Collect distinct ids to reduce queries
    game_ids = {it.game_id for it in items}
    sponsor_ids = {it.sponsor_id for it in items}

    # Validate games
    res_games = await db.execute(select(models.Game.id).where(models.Game.id.in_(list(game_ids))))
    found_games = {g for (g,) in res_games.all()}
    missing_games = [g for g in game_ids if g not in found_games]
    if missing_games:
        raise HTTPException(status_code=400, detail=f"Unknown game_id(s): {missing_games}")

    # Validate sponsors
    res_sps = await db.execute(select(models.Sponsor.id).where(models.Sponsor.id.in_(list(sponsor_ids))))
    found_sps = {s for (s,) in res_sps.all()}
    missing_sps = [s for s in sponsor_ids if s not in found_sps]
    if missing_sps:
        raise HTTPException(status_code=400, detail=f"Unknown sponsor_id(s): {missing_sps}")

    # Prepare rows
    rows: List[models.SponsorImpression] = []
    now = datetime.now(timezone.utc)
    for it in items:
        at_dt = _parse_iso_dt(it.at) or now
        rows.append(
            models.SponsorImpression(
                game_id=it.game_id,
                sponsor_id=it.sponsor_id,
                at=at_dt,
            )
        )

    # Bulk insert
    db.add_all(rows)
    await db.commit()

    # Refresh to get PKs (SQLAlchemy omits PKs for bulk unless refreshed)
    for r in rows:
        await db.refresh(r)

    return SponsorImpressionsOut(
        inserted=len(rows),
        ids=[int(r.id) for r in rows],
    )


# ================================================================
# Game Contributors (scorer / commentary / analytics)
# ================================================================
@_fastapi.post("/games/{game_id}/contributors", response_model=schemas.GameContributor)
async def add_contributor(
    game_id: str,
    body: schemas.GameContributorIn,
    db: AsyncSession = Depends(get_db),
):
    # Ensure game exists
    game = await crud.get_game(db, game_id=game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    # Upsert by unique (game_id, user_id, role)
    rec = models.GameContributor(
        game_id=game_id,
        user_id=body.user_id,
        role=body.role.value if hasattr(body.role, "value") else str(body.role),
        display_name=body.display_name,
    )
    try:
        db.add(rec)
        await db.commit()
        await db.refresh(rec)
    except IntegrityError:
        await db.rollback()
        # Update existing display_name if provided
        stmt = (
            update(models.GameContributor)
            .where(
                models.GameContributor.game_id == game_id,
                models.GameContributor.user_id == body.user_id,
                models.GameContributor.role == (body.role.value if hasattr(body.role, "value") else str(body.role)),
            )
            .values(display_name=body.display_name)
            .returning(models.GameContributor)
        )
        res = await db.execute(stmt)
        rec = res.scalar_one()
        await db.commit()

    # Cast fields so Pylance stops complaining about Column[...] typing
    return schemas.GameContributor(
        id=int(rec.id),
        game_id=str(rec.game_id),
        user_id=str(rec.user_id),
        role=schemas.GameContributorRole(str(rec.role)),
        display_name=(str(rec.display_name) if rec.display_name is not None else None),
    )


@_fastapi.get("/games/{game_id}/contributors", response_model=List[schemas.GameContributor])
async def list_contributors(
    game_id: str,
    db: AsyncSession = Depends(get_db),
):
    stmt = select(models.GameContributor).where(models.GameContributor.game_id == game_id)
    res = await db.execute(stmt)
    rows = res.scalars().all()

    return [
        schemas.GameContributor(
            id=int(r.id),
            game_id=str(r.game_id),
            user_id=str(r.user_id),
            role=schemas.GameContributorRole(str(r.role)),
            display_name=(str(r.display_name) if r.display_name is not None else None),
        )
        for r in rows
    ]


@_fastapi.delete("/games/{game_id}/contributors/{contrib_id}")
async def remove_contributor(
    game_id: str,
    contrib_id: int,
    db: AsyncSession = Depends(get_db),
):
    """Remove a contributor from a game by (game_id, contrib_id)."""
    stmt = delete(models.GameContributor).where(
        models.GameContributor.game_id == game_id,
        models.GameContributor.id == contrib_id,
    )
    res = await db.execute(stmt)
    await db.commit()

    # Some DB drivers don’t populate rowcount; handle defensively.
    if not getattr(res, "rowcount", 0):  # type: ignore[attr-defined]
        raise HTTPException(status_code=404, detail="Contributor not found")

    return {"ok": True}

# ================================================================
# Presence store + join/leave handlers
# ================================================================
# game_id -> { sid -> {"sid": str, "role": str, "name": str} }
_ROOM_PRESENCE: Dict[str, Dict[str, Dict[str, str]]] = defaultdict(dict)
_SID_ROOMS: Dict[str, set[str]] = defaultdict(set)

def _room_snapshot(game_id: str) -> List[Dict[str, str]]:
    return list(_ROOM_PRESENCE.get(game_id, {}).values())

@sio.event
async def connect(sid: str, environ: Dict[str, Any], auth: Optional[Any]) -> None:
    # Keep connection open; auth/JWT (if any) can be validated on 'join'
    return None

@sio.event
async def join(sid: str, data: Optional[Dict[str, Any]]) -> None:
    """
    data: { game_id: str, role?: "SCORER"|"COMMENTATOR"|"ANALYST"|"VIEWER", name?: str }
    """
    payload = data or {}
    game_id = cast(Optional[str], payload.get("game_id"))
    if not game_id:
        return None
    role = str(payload.get("role") or "VIEWER")
    name = str(payload.get("name") or role)

    await sio.enter_room(sid, game_id)
    _SID_ROOMS[sid].add(game_id)
    _ROOM_PRESENCE[game_id][sid] = {"sid": sid, "role": role, "name": name}

    # Tell this client who’s here, then broadcast updated presence to the room
    await sio.emit("presence:init", {"game_id": game_id, "members": _room_snapshot(game_id)}, room=sid)
    await sio.emit("presence:update", {"game_id": game_id, "members": _room_snapshot(game_id)}, room=game_id)
    return None

@sio.event
async def leave(sid: str, data: Optional[Dict[str, Any]]) -> None:
    payload = data or {}
    game_id = cast(Optional[str], payload.get("game_id"))
    if not game_id:
        return None
    await sio.leave_room(sid, game_id)
    _SID_ROOMS[sid].discard(game_id)
    _ROOM_PRESENCE.get(game_id, {}).pop(sid, None)
    await sio.emit("presence:update", {"game_id": game_id, "members": _room_snapshot(game_id)}, room=game_id)
    return None

@sio.event
async def disconnect(sid: str) -> None:
    # Remove from all rooms we know about
    for game_id in list(_SID_ROOMS.get(sid, set())):
        _ROOM_PRESENCE.get(game_id, {}).pop(sid, None)
        await sio.emit("presence:update", {"game_id": game_id, "members": _room_snapshot(game_id)}, room=game_id)
    _SID_ROOMS.pop(sid, None)
    return None

# ================================================================
# Health
# ================================================================
@_fastapi.get("/healthz")
async def healthz() -> Dict[str, str]:
    return {"status": "ok"}

# ================================================================
# Local dev entrypoint (optional)
# ================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)  # pyright: ignore[reportUnknownMemberType]
