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
)
from pathlib import Path
from fastapi import Depends, FastAPI, HTTPException
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

from routes.games_router import router as games_router

# ---- App modules ----
from sql_app import crud, schemas, models
from sql_app.database import SessionLocal

# Socket.IO (no first-party type stubs; we keep our own Protocol below)
import socketio  # type: ignore[import-not-found]

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
    runs_scored: int
    is_extra: bool
    extra_type: Optional[str]
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
    runs_scored: int
    is_extra: bool
    extra_type: Optional[str]
    is_wicket: bool
    dismissal_type: Optional[str]
    dismissed_player_id: Optional[str]
    commentary: Optional[str]
    fielder_id: Optional[str]

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
    interruptions: List[Dict[str, Optional[str]]]

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
    deliveries: List[Dict[str, Any]]
    batting_scorecard: Dict[str, BattingEntryDict]
    bowling_scorecard: Dict[str, BowlingEntryDict]

class StartOverBody(BaseModel):
    bowler_id: str

class MidOverChangeBody(BaseModel):
    new_bowler_id: str
    reason: Literal["injury", "other"] = "injury"

# ================================================================
# FastAPI + Socket.IO wiring
# ================================================================
_sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins="*")  # type: ignore[call-arg]
sio: SocketIOServer = cast(SocketIOServer, _sio)
_fastapi = FastAPI(title="Cricksy Scorer API")
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
STATIC_DIR = Path(os.getenv("STATIC_DIR", BASE_DIR / "static")).resolve()

# Create if missing (avoids RuntimeError)
STATIC_DIR.mkdir(parents=True, exist_ok=True)

_fastapi.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Keep your separate games router mounted
_fastapi.include_router(games_router)

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

def _player_name(team_a: TeamDict, team_b: TeamDict, pid: Optional[str]) -> str:
    """Look up a player's display name across both team lists."""
    if not pid:
        return ""
    for team in (team_a, team_b):
        for p in team["players"]:
            if p["id"] == pid:
                return p["name"]
    return ""

def _bowling_balls_to_overs(balls: int) -> float:
    """
    Convert legal ball count to cricket-style decimal overs (X.Y),
    where Y is the balls remainder [0..5]. Never round.
    """
    return float(f"{balls // 6}.{balls % 6}")

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

def _apply_mid_over_change(g: GameState, new_bowler_id: str) -> Optional[str]:
    if not g.current_bowler_id:
        return "No active bowler to replace."
    if g.mid_over_change_used:
        return "Mid-over change already used once this over."
    if new_bowler_id == g.current_bowler_id:
        return "Replacement bowler must be different."
    if g.balls_this_over >= 6:
        return "Over is already complete."
    g.current_bowler_id = new_bowler_id
    g.mid_over_change_used = True
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

def _is_no_ball(extra: Optional[str]) -> bool:
    return (extra or "").strip().lower() in {"no_ball", "nb"}

def _is_wide(extra: Optional[str]) -> bool:
    return (extra or "").strip().lower() in {"wide", "wd"}

def is_legal_delivery(extra: Optional[str]) -> bool:
    x: str = (extra or "").strip().lower()
    return x not in {"wide", "wd", "no_ball", "nb"}

def _rotate_strike_on_runs(runs: int) -> bool: # type: ignore
    return (runs % 2) == 1

# ================================================================
# NEW: normalization + dedupe + totals recompute
# ================================================================
def _norm_extra(x: Optional[str]) -> Optional[str]: # type: ignore
    """
    Normalize extra types to: None | 'wd' | 'nb' | 'b' | 'lb'
    """
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

    total_runs: int = 0
    total_wkts: int = 0
    legal_balls: int = 0
    cur_over_bowler: Optional[str] = None
    last_legal_bowler: Optional[str] = None


    # ---- Walk the (possibly mixed) ledger safely ----
    deliveries2: Sequence[Union[BaseModel, Mapping[str, Any]]] = cast(
        Sequence[Union[BaseModel, Mapping[str, Any]]],
        getattr(g, "deliveries", []) or [],
    )
    for d_any in deliveries2:
        d: Dict[str, Any] = (
            d_any.model_dump()
            if isinstance(d_any, BaseModel)
            else dict(d_any)
        )
        runs: int = int(d.get("runs_scored") or 0)
        raw_extra: Optional[Any] = d.get("extra_type")
        x: Optional[str] = _norm_extra(raw_extra)


        # Team total:
        # wd/nb: 1 penalty + any bat runs
        # b/lb: just those runs (legal ball)
        # None: pure bat runs (legal ball)
        if x == "wd":
            total_runs += 1 + runs
        elif x == "nb":
            total_runs += 1 + runs
        elif x in ("b", "lb"):
            total_runs += runs
            legal_balls += 1
            cur_over_bowler = d.get("bowler_id")
            last_legal_bowler = cur_over_bowler
        else:
            total_runs += runs
            legal_balls += 1
            cur_over_bowler = d.get("bowler_id")
            last_legal_bowler = cur_over_bowler

        # Wickets count only if a dismissal type string is present
        if d.get("is_wicket") and (d.get("dismissal_type") or "").strip():
            total_wkts += 1

    # Overs/balls derived from legal deliveries
    g.overs_completed = legal_balls // 6
    g.balls_this_over = legal_balls % 6
    g.current_over_balls = g.balls_this_over

    g.total_runs = total_runs
    g.total_wickets = total_wkts

    # Bowler pointers
    g.last_ball_bowler_id = last_legal_bowler
    g.current_bowler_id = cur_over_bowler if g.balls_this_over > 0 else None

def _extras_breakdown(g: GameState) -> Dict[str, int]:
    """Return wides / no_balls / byes / leg_byes / penalty / total from the ledger."""
    wides = no_balls = byes = leg_byes = penalty = 0
    deliveries3: Sequence[Union[BaseModel, Mapping[str, Any]]] = cast(
        Sequence[Union[BaseModel, Mapping[str, Any]]],
        getattr(g, "deliveries", []) or [],
    )
    for d_any in deliveries3:
        d: Dict[str, Any] = (
            d_any.model_dump()
            if isinstance(d_any, BaseModel)
            else dict(d_any)
        )
        x = _norm_extra(d.get("extra_type"))
        r = int(d.get("runs_scored") or 0)
        if x == "wd":
            # wides are all extras; r may be 1..5 (boundary wides, overthrows on a wide, etc.)
            wides += max(1, r) if r else 1
        elif x == "nb":
            # the "1" no-ball penalty; off-bat runs are *not* extras
            no_balls += 1
        elif x == "b":
            byes += r
        elif x == "lb":
            leg_byes += r
    total = wides + no_balls + byes + leg_byes + penalty
    return {
        "wides": wides,
        "no_balls": no_balls,
        "byes": byes,
        "leg_byes": leg_byes,
        "penalty": penalty,
        "total": total,
    }



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
            "player_name": _player_name(g.team_a, g.team_b, batter_id),
            "runs": 0,
            "balls_faced": 0,
            "is_out": False,
        }

    if "player_id" not in e:
        e["player_id"] = batter_id
    if "player_name" not in e:
        e["player_name"] = _player_name(g.team_a, g.team_b, batter_id)
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
            "player_name": _player_name(g.team_a, g.team_b, bowler_id),
            "overs_bowled": 0.0,
            "runs_conceded": 0,
            "wickets_taken": 0,
        }

    if "player_id" not in e:
        e["player_id"] = bowler_id
    if "player_name" not in e:
        e["player_name"] = _player_name(g.team_a, g.team_b, bowler_id)
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
        runs    = int(d.get("runs_scored") or 0)
        x       = _norm_extra(d.get("extra_type"))
        wicket  = bool(d.get("is_wicket"))
        dismissal_type = (d.get("dismissal_type") or "").strip().lower() or None

        # --- Batter updates ---
        if striker in bat:
            if x not in ("wd", "nb"):
                bat[striker]["balls_faced"] += 1
            # CREDIT runs to batter
            if x is None:
                bat[striker]["runs"] += runs
            elif x == "nb":
                bat[striker]["runs"] += runs

        # If a wicket fell, mark the dismissed player out
        if wicket and dismissal_type:
            out_pid = str(d.get("dismissed_player_id") or striker or "")
            if out_pid in bat:
                bat[out_pid]["is_out"] = True

        # --- Bowler updates ---
        if bowler in bowl:
            if x not in ("wd", "nb"):
                balls_by_bowler[bowler] += 1
            # wides / no-balls: 1 penalty + bat runs; plain bat runs otherwise
            if x in ("wd", "nb"):
                bowl[bowler]["runs_conceded"] += 1 + runs
            elif x is None:
                bowl[bowler]["runs_conceded"] += runs
            # b/lb don't add to bowler
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
    return {"player_id": pid, "player_name": _player_name(g.team_a, g.team_b, pid), "runs": 0, "balls_faced": 0, "is_out": False}

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
    extra: Optional[str],
    is_wicket: bool,
    dismissal_type: Optional[str],
    dismissed_player_id: Optional[str],
) -> DeliveryKwargs:
    # Ensure runtime fields exist
    if g.current_striker_id is None:
        g.current_striker_id = striker_id
    if g.current_non_striker_id is None:
        g.current_non_striker_id = non_striker_id
    if getattr(g, "current_bowler_id", None) is None:
        g.current_bowler_id = bowler_id
    if not hasattr(g, "pending_new_batter"):
        g.pending_new_batter = False
    if not hasattr(g, "pending_new_over"):
        g.pending_new_over = False

    bowler_id = g.current_bowler_id or bowler_id
    runs = int(runs_scored or 0)
    is_nb = _is_no_ball(extra)
    is_wd = _is_wide(extra)
    legal = not (is_nb or is_wd)

    # capture the display over/ball *before* we mutate runtime
    delivery_over_number = int(g.overs_completed)
    delivery_ball_number = int(g.balls_this_over + (1 if legal else 0))

    # --- Batting runtime (only what scorecards need immediately) ---
    bs = _ensure_batting_entry(g, striker_id)
    if legal:
        bs["balls_faced"] = int(bs.get("balls_faced", 0) + 1)
    if extra is None:
        bs["runs"] = int(bs.get("runs", 0) + runs)
    elif is_nb:
        # Off-bat runs on a no-ball go to the batter; ball does NOT count
        bs["runs"] = int(bs.get("runs", 0) + runs)

    # --- Bowling runtime (overs for current bowler on legal balls) ---
    bw = _ensure_bowling_entry(g, bowler_id)
    if legal:
        prev_balls = int(round(float(bw.get("overs_bowled", 0.0)) * 6))
        bw["overs_bowled"] = _bowling_balls_to_overs(prev_balls + 1)
        g.current_over_balls = int(getattr(g, "current_over_balls", 0) + 1)

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
    rotate_runs = 0
    if extra is None:
        rotate_runs = runs
    elif extra in ("b", "lb"):
        rotate_runs = runs
    elif is_nb:
        rotate_runs = runs
    elif is_wd:
        rotate_runs = runs

    if (rotate_runs % 2) == 1:
        g.current_striker_id, g.current_non_striker_id = g.current_non_striker_id, g.current_striker_id

    if legal:
        g.balls_this_over = int(g.balls_this_over + 1)
        if g.balls_this_over >= 6:
            g.overs_completed = int(g.overs_completed + 1)
            g.balls_this_over = 0
            # End of over -> force new over selection
            g.pending_new_over = True
            # clear current bowler so client must pick one
            g.current_bowler_id = None
            # swap strike at end of over
            g.current_striker_id, g.current_non_striker_id = g.current_non_striker_id, g.current_striker_id
            _complete_over_runtime(g, bowler_id)

    return {
        "over_number": delivery_over_number,
        "ball_number": delivery_ball_number,
        "bowler_id": str(bowler_id),
        "striker_id": str(striker_id),
        "non_striker_id": str(non_striker_id),
        "runs_scored": int(runs),
        "is_extra": extra is not None,
        "extra_type": (extra or None),
        "is_wicket": out_happened,
        "dismissal_type": dismissal,
        "dismissed_player_id": out_player_id if out_happened else None,
        "commentary": None,
        "fielder_id": None,
    }


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

    # If there is an over in progress, current bowler is the last legal bowler we saw.
    # If not, keep it None so the UI prompts to start the next over.
    cur_bowler_id: Optional[str] = None
    if g.balls_this_over > 0:
        # use whatever runtime computed
        cur_bowler_id = getattr(g, "current_bowler_id", None)
        if not cur_bowler_id:
            # fallback to last legal ball
            for d in reversed(_dedup_deliveries(g)):
                if is_legal_delivery(d.get("extra_type")):
                    cur_bowler_id = str(d.get("bowler_id") or "")
                    break

    # Prompt flags for the UI
    needs_new_over = (g.balls_this_over == 0 and (g.overs_completed > 0 or (g.deliveries or [])))
    # If a wicket just fell and the dismissed player is currently in one of the striker slots,
    # we need a replacement batter selection.
    cur_striker_out = _bat_entry(g, g.current_striker_id).get("is_out", False)
    cur_non_striker_out = _bat_entry(g, g.current_non_striker_id).get("is_out", False)
    needs_new_batter = bool(cur_striker_out or cur_non_striker_out)

    snapshot: Dict[str, Any] = {
        "id": g.id,
        "status": g.status,
        "score": {"runs": g.total_runs, "wickets": g.total_wickets, "overs": g.overs_completed},
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
        "overs": f"{g.overs_completed}.{g.balls_this_over}",
        "last_delivery": last_delivery_out,
        "batting_scorecard": g.batting_scorecard,
        "bowling_scorecard": g.bowling_scorecard,
        "extras": _extras_breakdown(g),
        "batting_team_name": g.batting_team_name,
        "bowling_team_name": g.bowling_team_name,
        "current_inning": g.current_inning,
        # NEW hints to drive UI prompts:
        "needs_new_over": needs_new_over,
        "needs_new_batter": needs_new_batter,
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
    body: MidOverChangeBody,
    db: AsyncSession = Depends(get_db),
):
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g = cast(GameState, db_game)
    if not g.current_bowler_id:
        raise HTTPException(status_code=400, detail="No active bowler for this over")

    err = _apply_mid_over_change(g, body.new_bowler_id)
    if err:
        raise HTTPException(status_code=400, detail=err)

    updated = await crud.update_game(db, game_model=db_game)  # <-- pass ORM row
    u = cast(GameState, updated)
    snap = _snapshot_from_game(u, None)
    await sio.emit("state:update", {"id": game_id, "snapshot": snap}, room=game_id)
    return {"ok": True, "current_bowler_id": g.current_bowler_id}

# ================================================================
# PR 1 — Record a delivery (with dismissal rules)
# ================================================================
@_fastapi.post("/games/{game_id}/deliveries")
async def add_delivery(
    game_id: str,
    delivery: schemas.ScoreDelivery,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g = cast(GameState, db_game)

    # Rebuild runtime from ledger to make correct gating decisions
    _rebuild_scorecards_from_deliveries(g)
    _recompute_totals_and_runtime(g)
    flags = _compute_snapshot_flags(g)

    # UI/State guards
    if flags["needs_new_batter"]:
        raise HTTPException(status_code=409, detail="Select a new batter before scoring the next ball.")
    if flags["needs_new_over"]:
        raise HTTPException(status_code=409, detail="Start a new over and select a bowler before scoring.")

    # No consecutive overs by same bowler (when over has just started)
    last_id = getattr(g, "last_ball_bowler_id", None)
    if g.balls_this_over == 0 and last_id and delivery.bowler_id == last_id:
        raise HTTPException(status_code=400, detail="Bowler cannot bowl consecutive overs")

    off_bat = getattr(delivery, "runs_off_bat", None)
    runs_scored = int(off_bat) if off_bat is not None else int(delivery.runs_scored or 0)

    # Score one ball (runtime update)
    kwargs: DeliveryKwargs = _score_one(
        g,
        striker_id=delivery.striker_id,
        non_striker_id=delivery.non_striker_id,
        bowler_id=delivery.bowler_id,
        runs_scored=runs_scored,
        extra=getattr(delivery, "extra", None),
        is_wicket=bool(getattr(delivery, "is_wicket", False)),
        dismissal_type=getattr(delivery, "dismissal_type", None),
        dismissed_player_id=getattr(delivery, "dismissed_player_id", None),
    )

    # Append once
    del_dict: Dict[str, Any] = schemas.Delivery(**kwargs).model_dump()
    if not isinstance(g.deliveries, list):  # type: ignore
        g.deliveries = []  # type: ignore[assignment]
        flag_modified(db_game, "deliveries")
    g.deliveries.append(del_dict)
    if getattr(g, "current_over_balls", None) is None:
        g.current_over_balls = 0
    if getattr(g, "mid_over_change_used", None) is None:
        g.mid_over_change_used = False
    if not hasattr(g, "current_bowler_id"):
        g.current_bowler_id = None
    if not hasattr(g, "last_ball_bowler_id"):
        g.last_ball_bowler_id = None
    flag_modified(db_game, "deliveries")

    # Rebuild scorecards from the authoritative ledger
    _rebuild_scorecards_from_deliveries(g)
    _recompute_totals_and_runtime(g)
    flag_modified(db_game, "batting_scorecard")
    flag_modified(db_game, "bowling_scorecard")

    # Persist
    updated = await crud.update_game(db, game_model=db_game)
    u = cast(GameState, updated)

    # Build snapshot from the persisted row + flags
    last = u.deliveries[-1] if u.deliveries else None
    snap = _snapshot_from_game(u, last)
    final_flags = _compute_snapshot_flags(u)
    snap["needs_new_batter"] = final_flags["needs_new_batter"]
    snap["needs_new_over"] = final_flags["needs_new_over"]

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
        d: Dict[str, Any] = (
            d_any.model_dump()
            if isinstance(d_any, BaseModel)
            else dict(d_any)
        )
        _ = _score_one(
            g,
            striker_id=str(d.get("striker_id", "")),
            non_striker_id=str(d.get("non_striker_id", "")),
            bowler_id=str(d.get("bowler_id", "")),
            runs_scored=int(d.get("runs_scored", 0)),
            extra=d.get("extra_type"),
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

    g.overs_limit = int(body.overs_limit)
    updated = await crud.update_game(db, game_model=db_game)  # <-- pass ORM row
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

    # Always rebuild from ledger
    _rebuild_scorecards_from_deliveries(g)
    _recompute_totals_and_runtime(g)

    last = _dedup_deliveries(g)[-1] if g.deliveries else None
    snap = _snapshot_from_game(g, last)

    # UI gating flags
    flags = _compute_snapshot_flags(g)
    snap["needs_new_batter"] = flags["needs_new_batter"]
    snap["needs_new_over"] = flags["needs_new_over"]

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
    rows = res.scalars().all()

    out: List[Dict[str, Any]] = []
    for r in rows:
        rid = cast(int, r.id) if isinstance(r.id, int) else r.id
        name = cast(str, r.name)
        logo_path = cast(str, r.logo_path)
        click_url = cast(Optional[str], r.click_url)
        weight = int(cast(int, r.weight))
        raw_surfaces: Any = getattr(r, "surfaces", None)
        if isinstance(raw_surfaces, (list, tuple)):
            seq: Sequence[object] = cast(Sequence[object], raw_surfaces)
            surfaces: List[str] = [str(item) for item in seq] or ["all"]
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
        ids=[cast(int, r.id) for r in rows],
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
        id=cast(int, rec.id),
        game_id=cast(str, rec.game_id),
        user_id=cast(str, rec.user_id),
        role=schemas.GameContributorRole(cast(str, rec.role)),
        display_name=cast(Optional[str], rec.display_name),
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
            id=cast(int, r.id),
            game_id=cast(str, r.game_id),
            user_id=cast(str, r.user_id),
            role=schemas.GameContributorRole(cast(str, r.role)),
            display_name=cast(Optional[str], r.display_name),
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
