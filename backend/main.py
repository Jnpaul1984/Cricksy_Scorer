from __future__ import annotations

import os
import uuid
from collections import defaultdict
import typing as t
from typing import (
    Any,
    AsyncGenerator,
    Dict,
    List,
    Optional,
    Protocol,
    Sequence,
    Callable,
    TypeVar,
    Union,
    cast,
    Literal,
    Mapping,
    runtime_checkable,
    Tuple,
    TypeAlias,
)
from typing_extensions import TypedDict, NotRequired
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
import datetime as dt
UTC = getattr(dt, "UTC", dt.UTC)
import json
from backend import dls as dlsmod
from backend.routes.games_router import router as games_router
from backend.routes.games_dls import router as games_dls_router
from backend.routes.interruptions import router as interruptions_router
from backend.routes.gameplay import router as gameplay_router
from backend.routes.dls import router as dls_router
from backend.routes.game_admin import router as game_admin_router
from backend.routes.health import router as health_router
from backend.routes.sponsors import router as sponsors_router
from backend.services.game_service import create_game as _create_game_service
from backend.services.scoring_service import score_one as _score_one
from backend.services.delivery_service import apply_scoring_and_persist as _apply_scoring_and_persist
# ---- App modules ----
from backend.sql_app import crud, schemas, models
from backend.sql_app.database import SessionLocal
from backend.services import validation as validation_helpers
from backend.routes import games as _games_impl
# Socket.IO (no first-party type stubs; we keep our own Protocol below)
import socketio  # type: ignore[import-not-found]
import logging
from backend.config import settings

# initialize logging early (before creating loggers)
logging.basicConfig(
    level=getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO),
    format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
)

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
BALLS_PER_OVER = 6
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
    fours: NotRequired[int]
    sixes: NotRequired[int]
    how_out: NotRequired[str]

class BowlingEntryDict(TypedDict):
    player_id: str
    player_name: str
    overs_bowled: float
    runs_conceded: int
    wickets_taken: int
    # optional, runtime/derived fields (safe for Pylance)
    balls_bowled: NotRequired[int]
    overs_bowled_str: NotRequired[str]
    maidens: NotRequired[int]
    economy: NotRequired[float]

class DeliveryDict(TypedDict, total=False):
    over_number: int
    ball_number: int
    bowler_id: str
    striker_id: str
    non_striker_id: str
    runs_off_bat: int
    runs_scored: int
    is_extra: bool
    extra_type: Optional[str]
    extra_runs: int
    is_wicket: bool
    dismissal_type: Optional[str]
    dismissed_player_id: Optional[str]
    commentary: Optional[str]
    fielder_id: Optional[str]
    shot_map: Optional[str]

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
    shot_map: NotRequired[Optional[str]]

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
    status: Union[str, models.GameStatus]
    current_inning: int
    total_runs: int
    total_wickets: int
    overs_completed: int
    balls_this_over: int
    current_striker_id: Optional[str]
    current_non_striker_id: Optional[str]
    target: Optional[int]
    first_inning_summary: Optional[dict[str, Any]]
    result: Optional[Union[str, schemas.MatchResult]]
    current_bowler_id: Optional[str]
    last_ball_bowler_id: Optional[str]
    current_over_balls: int
    mid_over_change_used: bool
    pending_new_batter: bool
    pending_new_over: bool

    # âœ… missing runtime fields
    balls_bowled_total: int
    innings_history: List[dict[str, Any]]
    needs_new_innings: bool
    needs_new_over: bool
    needs_new_batter: bool
    innings_start_at: Optional[datetime]    # <-- add this
    is_game_over: bool
    completed_at: Optional[datetime]

    # team roles
    team_a_captain_id: Optional[str]
    team_a_keeper_id: Optional[str]
    team_b_captain_id: Optional[str]
    team_b_keeper_id: Optional[str]

    # timelines & scorecards (JSON-safe)
    deliveries: Sequence[Any]
    batting_scorecard: dict[str, BattingEntryDict]
    bowling_scorecard: dict[str, BowlingEntryDict]

    # âœ… persistence
    async def save(self) -> None: ...

class ConcreteGameState:
    def __init__(self, id: str, team_a: TeamDict, team_b: TeamDict):
        self.id = id
        self.team_a = team_a
        self.team_b = team_b
        # Initialize other attributes with default values
        self.match_type = "limited"
        self.status = "SCHEDULED"
        self.current_inning = 1
        self.total_runs = 0
        self.total_wickets = 0
        self.overs_completed = 0
        self.balls_this_over = 0
        self.is_game_over = False
        self.deliveries = []
        self.batting_scorecard = {}
        self.bowling_scorecard = {}
        # Initialize other necessary attributes

    async def save(self):
        # Implement the logic to save the game state
        pass

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
_sio = socketio.AsyncServer(async_mode="asgi", cors_allowed_origins=settings.SIO_CORS_ALLOWED_ORIGINS)  # type: ignore[call-arg]
sio: SocketIOServer = cast(SocketIOServer, _sio)
_fastapi = FastAPI(title="Cricksy Scorer API")

BASE_DIR = Path(__file__).resolve().parent
STATIC_ROOT = settings.STATIC_ROOT
SPONSORS_DIR = settings.SPONSORS_DIR
SPONSORS_DIR.mkdir(parents=True, exist_ok=True)
_fastapi.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")
# Expose the FastAPI instance for tests and external tooling.
fastapi_app = _fastapi
_fastapi.state.sio = sio
app = socketio.ASGIApp(sio, other_asgi_app=_fastapi)

from backend.socket_handlers import register_sio  # existing
register_sio(sio)  # existing

# ADD these two lines right after register_sio(sio):
from backend.services.live_bus import set_socketio_server as _set_bus_sio
_set_bus_sio(sio)

_fastapi.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:4173",
        "http://127.0.0.1:4173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ================================================================
# DB dependency (async)
# ================================================================
from sqlalchemy.ext.asyncio import AsyncSession
from backend.sql_app.database import SessionLocal

async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:  # type: ignore[misc]
        yield session

# In-memory mode for tests/dev (use centralized setting)
from backend.config import settings

if settings.IN_MEMORY_DB:
    from backend.testsupport.in_memory_crud import InMemoryCrudRepository, enable_in_memory_crud

    _memory_repo = InMemoryCrudRepository()

    async def _in_memory_get_db() -> AsyncGenerator[object, None]:
        yield object()

    # Override FastAPI dependency to return a dummy object (CRUD uses in-memory repo)
    _fastapi.dependency_overrides[get_db] = _in_memory_get_db  # type: ignore[assignment]
    enable_in_memory_crud(_memory_repo)

# Keep your separate games router mounted

_fastapi.include_router(games_dls_router)   # existing (can coexist; different endpoints)
_fastapi.include_router(interruptions_router)
_fastapi.include_router(games_router)
_fastapi.include_router(gameplay_router)
_fastapi.include_router(dls_router)         # new: revised-target / par
_fastapi.include_router(game_admin_router)  # new: overs-limit / team-roles
_fastapi.include_router(health_router)      # new: health endpoints
_fastapi.include_router(sponsors_router)



# ================================================================
# Helpers: core utilities
# ================================================================
try:
    from backend.services import game_helpers as _gh  # type: ignore
    # Delegate core ledger/scorecard helpers to the extracted module.
    _deliveries_for_current_innings = _gh._deliveries_for_current_innings
    _dedup_deliveries = _gh._dedup_deliveries
    _legal_balls_count = _gh._legal_balls_count
    _overs_string_from_ledger = _gh._overs_string_from_ledger

    _player_name = _gh._player_name
    _player_team_name = _gh._player_team_name
    _id_by_name = _gh._id_by_name

    _mk_batting_scorecard = _gh._mk_batting_scorecard
    _mk_bowling_scorecard = _gh._mk_bowling_scorecard

    _ensure_batting_entry = _gh._ensure_batting_entry
    _ensure_bowling_entry = _gh._ensure_bowling_entry

    _rebuild_scorecards_from_deliveries = _gh._rebuild_scorecards_from_deliveries
    _recompute_totals_and_runtime = _gh._recompute_totals_and_runtime

    _extras_breakdown = _gh._extras_breakdown
    _fall_of_wickets = _gh._fall_of_wickets
    _compute_snapshot_flags = _gh._compute_snapshot_flags
    _mini_batting_card = _gh._mini_batting_card
    _mini_bowling_card = _gh._mini_bowling_card

    _ensure_target_if_chasing = _gh._ensure_target_if_chasing
    _runs_wkts_balls_for_innings = _gh._runs_wkts_balls_for_innings
    _maybe_finalize_match = _gh._maybe_finalize_match

    _can_start_over = _gh._can_start_over
    _first_innings_summary = _gh._first_innings_summary
    _complete_game_by_result = _gh._complete_game_by_result
    is_legal_delivery = _gh.is_legal_delivery
    _complete_over_runtime = getattr(_gh, "_complete_over_runtime", None)

    # Small normalization / conversion helpers also used across main.py
    _norm_extra = _gh._norm_extra
    _as_extra_code = getattr(_gh, "_as_extra_code", None)
    _bowling_balls_to_overs = getattr(_gh, "_bowling_balls_to_overs", None)
    _complete_over_runtime = getattr(_gh, "_complete_over_runtime", None)
except Exception:
    # Keep local implementations if the extracted module isn't available yet.
    _gh = None

from backend.helpers import overs_str_from_balls as _overs_str_from_balls

# --- API status mapping (internal -> wire enum) ---
def _api_status(v: Any) -> str:
    # unwrap Enum if needed
    if hasattr(v, "value"):
        v = v.value
    s = str(v).strip().lower()
    mapping = {
        "not_started":   "SCHEDULED",
        "scheduled":     "SCHEDULED",
        "started":       "IN_PROGRESS",
        "live":          "IN_PROGRESS",
        "in_progress":   "IN_PROGRESS",
        "innings_break": "INNINGS_BREAK",
        "completed":     "COMPLETED",
        "abandoned":     "ABANDONED",
    }
    return mapping.get(s, "IN_PROGRESS")

# --- helpers ---------------------------------------------------------
def _coerce_match_type(raw: str) -> schemas.MatchType:
    try:
        return schemas.MatchType(raw)  # exact enum match
    except Exception:
        return schemas.MatchType.limited  # safe default

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

def _rotate_strike_on_runs(runs: int) -> bool: # type: ignore
    return (runs % 2) == 1

# --- Type narrowing for extras (fixes Pylance str|None â†’ ExtraCode|None) ---
ExtraCode = schemas.ExtraCode  # alias for readability

_EXTRA_MAP: Mapping[str, ExtraCode] = {
    "wd": "wd",
    "nb": "nb",
    "b":  "b",
    "lb": "lb",
}

def _as_extra_code(x: Optional[str]) -> Optional[ExtraCode]:
    if x is None:
        return None
    return _EXTRA_MAP.get(x)

# ================================================================
# NEW: normalization + dedupe + totals recompute
# ================================================================

def _is_blank(x: object) -> bool:
    return x is None or (isinstance(x, str) and x.strip() == "")

def _sum_runs_for_innings(g: GameState, inning: int) -> int:
    total = 0
    inning_no = int(inning)
    for d_any in getattr(g, "deliveries", []) or []:
        d = d_any.model_dump() if isinstance(d_any, BaseModel) else dict(d_any)
        try:
            inn = int(d.get("inning", 1))
        except Exception:
            inn = 1
        if inn != inning_no:
            continue

        extra = _norm_extra(d.get("extra_type") or d.get("extra"))
        runs_scored = int(d.get("runs_scored") or 0)
        off_bat = int(d.get("runs_off_bat") or d.get("runs") or 0)
        extra_runs = int(d.get("extra_runs") or 0)

        if extra == "wd":
            total += runs_scored or max(1, extra_runs or 1)
        elif extra == "nb":
            total += runs_scored or (1 + off_bat)
        elif extra in ("b", "lb"):
            total += runs_scored or extra_runs
        else:
            total += runs_scored or off_bat
    return total

def _team1_runs(g: GameState) -> int:
    fis_any: Any = getattr(g, "first_inning_summary", None)
    if isinstance(fis_any, dict) and "runs" in fis_any:
        try:
            return int(cast(Any, fis_any["runs"]))
        except Exception:
            pass
    return _sum_runs_for_innings(g, 1)

async def _maybe_close_innings(g: GameState) -> None:
    """Close the current innings if overs exhausted or all out."""
    balls_limit = (g.overs_limit or 0) * 6
    balls_bowled = int(getattr(g, "balls_bowled_total", None) or (
        int(getattr(g, "overs_completed", 0)) * 6 + int(getattr(g, "balls_this_over", 0))
    ))

    if g.status == models.GameStatus.innings_break:
        return

    all_out = (g.total_wickets >= 10)
    overs_exhausted = (balls_limit > 0 and balls_bowled >= balls_limit)

    if all_out or overs_exhausted:
        if not hasattr(g, "innings_history"):
            g.innings_history = []

        # âœ… Only archive if not already archived
        already_archived = any(
            inn.get("inning_no") == g.current_inning for inn in g.innings_history
        )
        if not already_archived:
            g.innings_history.append({
                "inning_no": g.current_inning or 1,
                "batting_team": g.batting_team_name,
                "bowling_team": g.bowling_team_name,
                "runs": g.total_runs,
                "wickets": g.total_wickets,
                "overs": _overs_string_from_ledger(g),
                "batting_scorecard": g.batting_scorecard,
                "bowling_scorecard": g.bowling_scorecard,
                "deliveries": g.deliveries,
                "closed_at": dt.datetime.now(UTC).isoformat(),  # âœ… TZ-aware
            })

        g.status = models.GameStatus.innings_break
        g.needs_new_innings = True
        g.needs_new_over = False
        g.needs_new_batter = False
        g.current_striker_id = None
        g.current_non_striker_id = None
        g.current_bowler_id = None

# Key used in _dedup_deliveries: (over, ball, subindex) where subindex is int for illegal (wd/nb) or "L" for legal.
BallKey: TypeAlias = Tuple[int, int, Union[int, Literal["L"]]]
# Allowed match-result method values (use at module scope so Pylance is happy)
AllowedMethod: TypeAlias = Literal["by runs", "by wickets", "tie", "no result"]

def _coerce_batting_entry(  # pyright: ignore[reportUnusedFunction]
    x: Any, team_a: TeamDict, team_b: TeamDict
) -> schemas.BattingScorecardEntry:
    if isinstance(x, schemas.BattingScorecardEntry):
        return x
    if isinstance(x, dict):
        x_dict: dict[str, Any] = dict(x)
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
        x_dict: dict[str, Any] = dict(x)
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
# Request models (wrapper for your schemas)
# ================================================================
class CreateGameRequest(BaseModel):
    team_a_name: str
    team_b_name: str
    # Allow either explicit player lists OR a players_per_team count for tests/clients
    players_a: Optional[List[str]] = Field(None, min_length=0)
    players_b: Optional[List[str]] = Field(None, min_length=0)
    players_per_team: Optional[int] = Field(None, ge=1)

    match_type: Literal["limited", "multi_day", "custom"] = "limited"
    overs_limit: Optional[int] = Field(None, ge=1, le=120)
    days_limit: Optional[int] = Field(None, ge=1, le=7)
    overs_per_day: Optional[int] = Field(None, ge=1, le=120)
    dls_enabled: bool = False
    interruptions: List[Dict[str, Optional[str]]] = Field(default_factory=list)

    # Make toss / decision optional for simpler test payloads; default behavior is safe
    toss_winner_team: Optional[str] = None
    decision: Optional[Literal["bat", "bowl"]] = None

class OversLimitBody(BaseModel):
    overs_limit: int

class StartInningsBody(BaseModel):
    striker_id: Optional[str] = None
    non_striker_id: Optional[str] = None
    opening_bowler_id: Optional[str] = None

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

        # Team 1 score (use persisted summary or compute from innings 1).
        S1 = _team1_runs(g)

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

from backend.services.snapshot_service import build_snapshot as _snapshot_from_game

# ================================================================
# Routes â€” Games
# ================================================================
@_fastapi.options("/games")
async def options_games() -> dict[str, str]:
    payload: dict[str, str] = {"message": "OK"}
    return payload

@_fastapi.post("/games", response_model=schemas.Game)  # type: ignore[name-defined]
async def create_game(
    payload: CreateGameRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Delegate game creation to backend.routes.games.create_game_impl
    """
    db_game = await _games_impl.create_game_impl(payload, db)
    return db_game

@_fastapi.get("/games/{game_id}", response_model=schemas.Game)  # type: ignore[name-defined]
async def get_game(game_id: str, db: AsyncSession = Depends(get_db)):
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")
    return db_game




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

    # Some DB drivers donâ€™t populate rowcount; handle defensively.
    if not getattr(res, "rowcount", 0):  # type: ignore[attr-defined]
        raise HTTPException(status_code=404, detail="Contributor not found")

    return {"ok": True}


# ================================================================
# Local dev entrypoint (optional)
# ================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)  # pyright: ignore[reportUnknownMemberType]

