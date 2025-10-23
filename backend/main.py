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
from datetime import datetime, timezone
import json
from backend import dls as dlsmod
from backend.routes.games_router import router as games_router
from backend.routes.games_dls import router as games_dls_router
from backend.routes.interruptions import router as interruptions_router
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
    first_inning_summary: Optional[Dict[str, Any]]
    result: Optional[Union[str, schemas.MatchResult]]
    current_bowler_id: Optional[str]
    last_ball_bowler_id: Optional[str]
    current_over_balls: int
    mid_over_change_used: bool
    pending_new_batter: bool
    pending_new_over: bool

    # âœ… missing runtime fields
    balls_bowled_total: int
    innings_history: List[Dict[str, Any]]
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
    batting_scorecard: Dict[str, BattingEntryDict]
    bowling_scorecard: Dict[str, BowlingEntryDict]

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
class StartNextInningsBody(BaseModel):
    striker_id: Optional[str] = None
    non_striker_id: Optional[str] = None
    opening_bowler_id: Optional[str] = None

class StartOverBody(BaseModel):
    bowler_id: str

class MidOverChangeBody(BaseModel):
    new_bowler_id: str
    reason: Literal["injury", "other"] = "injury"


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
# Expose the FastAPI instance for tests and external tooling.
fastapi_app = _fastapi
_fastapi.state.sio = sio
app = socketio.ASGIApp(sio, other_asgi_app=_fastapi)
from backend.socket_handlers import register_sio  # new import
register_sio(sio)  # attach the handlers to the AsyncServer

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


# --- PR 7: Static files for logos/sponsors ---
# Resolve to backend/static
BASE_DIR = Path(__file__).resolve().parent


# Create if missing (avoids RuntimeError)
STATIC_ROOT = Path(__file__).parent / "static"
SPONSORS_DIR = STATIC_ROOT / "sponsors"
SPONSORS_DIR.mkdir(parents=True, exist_ok=True)
_fastapi.mount("/static", StaticFiles(directory=STATIC_ROOT), name="static")


# Keep your separate games router mounted

_fastapi.include_router(games_dls_router)
_fastapi.include_router(interruptions_router)
_fastapi.include_router(games_router)

@_fastapi.get("/health", include_in_schema=False)
def health() -> dict[str, str]:
    return {"status": "ok"}



# ================================================================
# DB dependency (async)
# ================================================================
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:  # type: ignore[misc]
        yield session

if os.getenv("CRICKSY_IN_MEMORY_DB") == "1":
    from backend.testsupport.in_memory_crud import InMemoryCrudRepository, enable_in_memory_crud

    _memory_repo = InMemoryCrudRepository()

    async def _in_memory_get_db() -> AsyncGenerator[object, None]:
        yield object()

    _fastapi.dependency_overrides[get_db] = _in_memory_get_db  # type: ignore[assignment]
    enable_in_memory_crud(_memory_repo)

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
                "closed_at": datetime.now(timezone.utc).isoformat(),  # âœ… TZ-aware
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

class NextBatterBody(BaseModel):
    batter_id: str

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
async def options_games() -> Dict[str, str]:
    payload: Dict[str, str] = {"message": "OK"}
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

@_fastapi.post("/games/{game_id}/innings/start")
async def start_next_innings(
    game_id: str,
    body: StartNextInningsBody,      # << accept JSON body
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g: GameState = t.cast(GameState, db_game)


    # Must be at innings break to start the next one
    if g.status != models.GameStatus.innings_break:
        raise HTTPException(status_code=400, detail="No new innings to start")

    # Ensure these attrs exist on legacy rows
    if not isinstance(getattr(g, "innings_history", None), list):
        g.innings_history = []
    if not hasattr(g, "needs_new_innings"):
        g.needs_new_innings = True
    if not hasattr(g, "current_inning") or not g.current_inning:
        g.current_inning = 1

    prev_batting_team = g.batting_team_name
    prev_bowling_team = g.bowling_team_name

    # If the last innings wasnâ€™t archived yet, archive it now
    last_archived_no = g.innings_history[-1]["inning_no"] if g.innings_history else None
    if last_archived_no != g.current_inning:
        g.innings_history.append({
            "inning_no": g.current_inning,
            "batting_team": prev_batting_team,
            "bowling_team": prev_bowling_team,
            "runs": g.total_runs,
            "wickets": g.total_wickets,
            "overs": _overs_string_from_ledger(g),
            "batting_scorecard": g.batting_scorecard,
            "bowling_scorecard": g.bowling_scorecard,
            # DO NOT destroy the ledger; it spans both innings
            "closed_at": datetime.now(timezone.utc).isoformat(),
        })


    # Advance innings and flip teams
    g.current_inning = int(g.current_inning) + 1
    g.batting_team_name, g.bowling_team_name = prev_bowling_team, prev_batting_team

    # Reset per-innings runtime counters (keep the combined deliveries ledger)
    g.total_runs = 0
    g.total_wickets = 0
    g.overs_completed = 0
    g.balls_this_over = 0

    # Apply optional openers from body
    g.current_striker_id = body.striker_id or None
    g.current_non_striker_id = body.non_striker_id or None
    if not hasattr(g, "current_bowler_id"):
        g.current_bowler_id = None
    g.current_bowler_id = body.opening_bowler_id or None

    # (Re)build fresh scorecards for the new batting/bowling teams
    g.batting_scorecard = _mk_batting_scorecard(
        g.team_a if g.batting_team_name == g.team_a["name"] else g.team_b
    )
    g.bowling_scorecard = _mk_bowling_scorecard(
        g.team_b if g.batting_team_name == g.team_a["name"] else g.team_a
    )

    # Clear â€œgateâ€ flags and mark match live
    if not hasattr(g, "needs_new_over"):
        g.needs_new_over = False
    if not hasattr(g, "needs_new_batter"):
        g.needs_new_batter = False
    g.needs_new_innings = False
    g.current_inning = 2
    if g.first_inning_summary is None:
        g.first_inning_summary = _first_innings_summary(g)
    _ensure_target_if_chasing(g)
    g.needs_new_over = (g.current_bowler_id is None)
    g.needs_new_batter = (g.current_striker_id is None or g.current_non_striker_id is None)
    g.status = models.GameStatus.in_progress

    # Recompute derived/runtime and persist
    _rebuild_scorecards_from_deliveries(g)
    _recompute_totals_and_runtime(g)
    updated = await crud.update_game(db, game_model=db_game)
    u = cast(GameState, updated)

    # Snapshot + emit
    snap = _snapshot_from_game(u, None, BASE_DIR)
    snap["needs_new_innings"] = False
    snap["needs_new_over"] = (g.current_bowler_id is None)
    snap["needs_new_batter"] = (g.current_striker_id is None or g.current_non_striker_id is None)

    await sio.emit("state:update", {"id": game_id, "snapshot": snap}, room=game_id)
    return snap





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

    g: GameState = t.cast(GameState, db_game)

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
    snap = _snapshot_from_game(u, None, BASE_DIR)
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

    g: GameState = t.cast(GameState, db_game)


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

    # --- Apply change (do NOT touch last_ball_bowler_id; thatâ€™s an over-boundary concept)
    g.current_bowler_id = str(body.new_bowler_id)
    g.mid_over_change_used = True

    # Recompute & persist
    _recompute_totals_and_runtime(g)
    updated = await crud.update_game(db, game_model=db_game)
    u = cast(GameState, updated)

    # Build/augment snapshot so UI has everything it needs immediately
    snap = _snapshot_from_game(u, None, BASE_DIR)
    # Ensure runtime keys are present in snapshot payload:
    snap["current_bowler_id"] = g.current_bowler_id
    snap["last_ball_bowler_id"] = g.last_ball_bowler_id
    snap["current_over_balls"] = g.current_over_balls
    snap["mid_over_change_used"] = g.mid_over_change_used
    snap["needs_new_over"] = bool(getattr(g, "needs_new_over", False))

    await sio.emit("state:update", {"id": game_id, "snapshot": snap}, room=game_id)
    return snap  # return full snapshot, not just {"ok": true}

# ================================================================
# PR 1 â€” Record a delivery (with dismissal rules)
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

    g: GameState = t.cast(GameState, db_game)


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
            team_a: TeamDict = t.cast(TeamDict, getattr(g, "team_a"))
            team_b: TeamDict = t.cast(TeamDict, getattr(g, "team_b"))

            bowling_team_name = g.bowling_team_name
            bowling_team: TeamDict = team_a if team_a["name"] == bowling_team_name else team_b
            allowed = {str(p["id"]) for p in (bowling_team.get("players", []) or [])}

            if incoming not in allowed:
                raise HTTPException(status_code=409, detail="Bowler is not in the bowling team")

            g.current_bowler_id = incoming
            g.mid_over_change_used = True

    # --- Start-of-over handling -------------------------------------------------
    # If weâ€™re at the very start of a fresh over (0 balls), keep any chosen bowler
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
    # Allow UX to provide dismissed player by name instead of ID
    if bool(delivery.is_wicket) and not getattr(delivery, "dismissed_player_id", None):
        dpn = getattr(delivery, "dismissed_player_name", None)
        if dpn:
            resolved = _id_by_name(g.team_a, g.team_b, dpn)
            if not resolved:
                raise HTTPException(status_code=404, detail="Unknown dismissed player name")
            delivery.dismissed_player_id = resolved
    
    # --- Comprehensive player validation ---------------------------------------
    # Validate all players involved in the delivery
    validation_helpers.validate_delivery_players(
        striker_id=delivery.striker_id,
        non_striker_id=delivery.non_striker_id,
        bowler_id=delivery.bowler_id or getattr(g, "current_bowler_id", None),
        team_a=g.team_a,
        team_b=g.team_b,
        batting_team_name=g.batting_team_name,
        bowling_team_name=g.bowling_team_name,
        is_wicket=delivery.is_wicket or False,
        dismissal_type=getattr(delivery, "dismissal_type", None)
    )
    
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
        # --- Autofill batters from runtime so the client doesn't have to send them every ball ---
    # If the client omitted batter IDs, pull them from g.current_*.
    # If it's the first ball of the innings (no current_* yet), ask to select openers once.
    if _is_blank(getattr(delivery, "striker_id", None)):
        if getattr(g, "current_striker_id", None):
            delivery.striker_id = g.current_striker_id  # type: ignore[assignment]
        else:
            raise HTTPException(status_code=409, detail="Select openers before scoring the first ball.")

    if _is_blank(getattr(delivery, "non_striker_id", None)):
        if getattr(g, "current_non_striker_id", None):
            delivery.non_striker_id = g.current_non_striker_id  # type: ignore[assignment]
        else:
            raise HTTPException(status_code=409, detail="Select openers before scoring the first ball.")
    # Ensure we have batter IDs (you already guard these; this makes types explicit)
    if not delivery.striker_id:
        raise HTTPException(status_code=409, detail="Select openers before scoring the first ball.")
    if not delivery.non_striker_id:
        raise HTTPException(status_code=409, detail="Select openers before scoring the first ball.")

    # Effective bowler: current mid-over bowler, else payload bowler
    effective_bowler_id: t.Optional[str] = (
        t.cast(t.Optional[str], getattr(g, "current_bowler_id", None)) or delivery.bowler_id
    )
    if not effective_bowler_id:
        raise HTTPException(status_code=409, detail="Select a bowler before scoring the first ball of the over.")

    striker_id_n: str = delivery.striker_id
    non_striker_id_n: str = delivery.non_striker_id
    bowler_id_n: str = effective_bowler_id


    kwargs: DeliveryKwargs

    if x == "nb":
        off_bat = int(delivery.runs_off_bat or 0)
        kwargs = _score_one(
            g,
            striker_id=striker_id_n,
            non_striker_id=non_striker_id_n,
            bowler_id=bowler_id_n,
            runs_scored=off_bat,
            extra="nb",
            is_wicket=bool(delivery.is_wicket),
            dismissal_type=delivery.dismissal_type,
            dismissed_player_id=delivery.dismissed_player_id,
        )
    elif x in ("wd", "b", "lb"):
        extra_runs = int(delivery.runs_scored or 0)
        kwargs = _score_one(
            g,
            striker_id=striker_id_n,
            non_striker_id=non_striker_id_n,
            bowler_id=bowler_id_n,
            runs_scored=extra_runs,
            extra=_as_extra_code(x),
            is_wicket=bool(delivery.is_wicket),
            dismissal_type=delivery.dismissal_type,
            dismissed_player_id=delivery.dismissed_player_id,
        )

    else:
        batter_runs = int(delivery.runs_scored or 0)
        kwargs = _score_one(
            g,
            striker_id=striker_id_n,
            non_striker_id=non_striker_id_n,
            bowler_id=bowler_id_n,
            runs_scored=batter_runs,
            extra=None,
            is_wicket=bool(delivery.is_wicket),
            dismissal_type=delivery.dismissal_type,
            dismissed_player_id=delivery.dismissed_player_id,
        )

    # --- Append to ledger once --------------------------------------------------
    del_dict: Dict[str, Any] = schemas.Delivery(**kwargs).model_dump()
    del_dict["inning"] = int(getattr(g, "current_inning", 1) or 1)
    # Optional shot direction from client for wagon wheel analytics
    try:
        del_dict["shot_angle_deg"] = getattr(delivery, "shot_angle_deg", None)
    except Exception:
        del_dict["shot_angle_deg"] = None
    try:
        shot_map_val = getattr(delivery, "shot_map", None)
        del_dict["shot_map"] = str(shot_map_val) if shot_map_val is not None else None
    except Exception:
        del_dict["shot_map"] = None
    
    
    # Delegate append/persist to the extracted route/service implementation.
    # append_delivery_and_persist_impl returns the updated ORM Game row.
    updated = await _games_impl.append_delivery_and_persist_impl(
        db_game,
        delivery_dict=del_dict,
        db=db,
    )
    u = cast(GameState, updated)

    # Recompute derived runtime (actions that read from the persisted row)
    _rebuild_scorecards_from_deliveries(u)
    _recompute_totals_and_runtime(u)
    await _maybe_close_innings(u)

    # Ensure target and decide match result (these were done before persisting in the original flow).
    # Run finalizers now and persist their effects so the ORM row has correct result/status.
    _ensure_target_if_chasing(u)
    _maybe_finalize_match(u)
    # Persist again if finalizers changed state/result
    await crud.update_game(db, game_model=cast(Any, u))

    # --- Build snapshot + final flags ------------------------------------------
    last = u.deliveries[-1] if u.deliveries else None
    snap = _snapshot_from_game(u, last)
    is_break = str(getattr(u, "status", "")) == "innings_break" or bool(getattr(u, "needs_new_innings", False))
    if is_break:
        snap["needs_new_over"] = False
        snap["needs_new_innings"] = True

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

@_fastapi.get("/games/{game_id}/deliveries")
async def get_deliveries(
    game_id: str,
    innings: Optional[int] = Query(None, ge=1, le=4, description="Filter by innings number"),
    limit: int = Query(120, ge=1, le=500, description="Max number of rows to return"),
    order: Literal["desc", "asc"] = Query("desc", description="desc = newest-first"),
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    """
    Returns deliveries for a game (optionally filtered by innings),
    ordered newest-first by default.
    Response shape matches /recent_deliveries.
    """
    game = await crud.get_game(db, game_id=game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    g = cast(GameState, game)

    # Read the raw ledger (combined across innings)
    raw_seq: Sequence[Any] = getattr(g, "deliveries", []) or []
    rows: List[Dict[str, Any]] = []
    for item in raw_seq:
        d = _model_to_dict(item)
        if d is not None:
            # normalize extra_type to the canonical union expected by schemas.Delivery
            if "extra_type" in d:
                d["extra_type"] = _as_extra_code(cast(Optional[str], d.get("extra_type")))
            # ensure there is an int innings tag; default legacy to 1
            try:
                d["inning"] = int(d.get("inning", 1) or 1)
            except Exception:
                d["inning"] = 1
            rows.append(d)

    # Optional innings filter
    if innings is not None:
        rows = [d for d in rows if int(d.get("inning", 1)) == int(innings)]

    # Natural insertion order is earliestâ†’latest; enforce order + limit
    if order == "desc":
        # newest-first
        rows = rows[-limit:][::-1]
    else:
        # earliest-first
        rows = rows[:limit]

    # Validate/shape with Pydantic (keeps wire format consistent)
    out: List[Dict[str, Any]] = []
    for d_any in rows:
        try:
            model = schemas.Delivery(**cast(DeliveryKwargs, d_any))
            shaped = model.model_dump()
        except Exception:
            # Pydantic v1 fallback
            try:
                model = schemas.Delivery(**d_any)          # type: ignore[call-arg]
                shaped = model.dict()                      # type: ignore[attr-defined]
            except Exception:
                continue

        # Enrich names for UI convenience
        shaped["striker_name"] = _player_name(g.team_a, g.team_b, shaped.get("striker_id"))
        shaped["non_striker_name"] = _player_name(g.team_a, g.team_b, shaped.get("non_striker_id"))
        shaped["bowler_name"] = _player_name(g.team_a, g.team_b, shaped.get("bowler_id"))
        # pass through innings tag (frontend maps this to innings_no)
        shaped["inning"] = d_any.get("inning", 1)
        out.append(shaped)

    return {
        "game_id": game_id,
        "count": len(out),
        "deliveries": out,   # ordered per `order` (desc by default)
    }

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

    g: GameState = t.cast(GameState, db_game)


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
    dl = _dedup_deliveries(u)
    last = dl[-1] if dl else None
    snap = _snapshot_from_game(u, last, BASE_DIR)
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

    g: GameState = t.cast(GameState, db_game)

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
    snap = _snapshot_from_game(u, None, BASE_DIR)
    await sio.emit("state:update", {"id": game_id, "snapshot": snap}, room=game_id)
    return {"ok": True, "current_striker_id": g.current_striker_id}



# ================================================================
# PR 2 â€” Undo last ball (full state recompute from ledger)
# ================================================================
@_fastapi.post("/games/{game_id}/undo-last")
async def undo_last_delivery(game_id: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g: GameState = t.cast(GameState, db_game)

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
            extra=_as_extra_code(x),
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
# PR 4 â€” Rain control: adjust overs limit mid-match
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

    # Team 1 runs are just g.total_runs at end of inns 1; if called midâ€‘match, use snapshot
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

    # Team 1 score (use persisted summary or compute from innings 1)
    S1 = _team1_runs(g)

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
    S1 = _team1_runs(g)  # score to chase

    # Team 2 â€œused so farâ€ during chase
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

    g: GameState = t.cast(GameState, db_game)

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
    dl = _dedup_deliveries(u)
    last = dl[-1] if dl else None
    snap = _snapshot_from_game(u, last, BASE_DIR)
    _rebuild_scorecards_from_deliveries(u)
    _recompute_totals_and_runtime(u)
    _complete_game_by_result(u)
    # persist if we changed status/result
    await crud.update_game(db, game_model=cast(Any, u))
    await sio.emit("state:update", {"id": game_id, "snapshot": snap}, room=game_id)

    return {"id": game_id, "overs_limit": cast(GameState, updated).overs_limit}

@_fastapi.post("/games/{game_id}/finalize")
async def finalize_game(
    game_id: str,
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g: GameState = t.cast(GameState, db_game)

    # Always rebuild current totals first
    _rebuild_scorecards_from_deliveries(g)
    _recompute_totals_and_runtime(g)
    _ensure_target_if_chasing(g)

    # Try both finalizers (one uses runtime, one re-reads ledger)
    _complete_game_by_result(g)
    _maybe_finalize_match(g)  # harmless if already completed

    updated = await crud.update_game(db, game_model=db_game)
    u = cast(GameState, updated)
    snap = _snapshot_from_game(u, None, BASE_DIR)
    await sio.emit("state:update", {"id": game_id, "snapshot": snap}, room=game_id)
    return snap

# ================================================================
# PR 5 â€” GET game snapshot (viewer bootstrap)
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

    dl = _dedup_deliveries(g)
    last = dl[-1] if dl else None
    snap = _snapshot_from_game(g, last, BASE_DIR)

    # UI gating flags
    flags = _compute_snapshot_flags(g)
    is_break = str(getattr(g, "status","")) == "innings_break" or bool(getattr(g, "needs_new_innings", False))
    snap["needs_new_batter"] = flags["needs_new_batter"]
    snap["needs_new_over"] = False if is_break else flags["needs_new_over"]
    snap["needs_new_innings"] = is_break

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
            S1 = _team1_runs(g)

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
            # ensure the literal type matches the schema
            if "extra_type" in d_any:
                d_any["extra_type"] = _as_extra_code(cast(Optional[str], d_any.get("extra_type")))
            d_kw = cast(DeliveryKwargs, d_any)            # <-- silences â€œunknown argument typeâ€
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
    for i, row in enumerate(out):
        row["striker_name"] = _player_name(g.team_a, g.team_b, row.get("striker_id"))
        row["non_striker_name"] = _player_name(g.team_a, g.team_b, row.get("non_striker_id"))
        row["bowler_name"] = _player_name(g.team_a, g.team_b, row.get("bowler_id"))
        row["inning"] = int(ledger[i].get("inning", 1) or 1)

    return {
        "game_id": game_id,
        "count": len(out),
        "deliveries": out,  # newest-first
    }




# ================================================================
# OPTIONAL â€” Explicitly set openers (quality-of-life)
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

    g: GameState = t.cast(GameState, db_game)


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
    _complete_game_by_result(u)
    snap = _snapshot_from_game(u, None, BASE_DIR)
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

    g: GameState = t.cast(GameState, db_game)

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
# PR 8 â€” Sponsor upload endpoint
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

    # Surfaces parsing â€” ensure a list[str]
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
    sponsors_dir = str(SPONSORS_DIR)
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
# PR 9 â€” Per-game sponsors lineup (time-gated, v1 global)
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
# PR 10 â€” Impression logging (proof-of-play)
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

    # Some DB drivers donâ€™t populate rowcount; handle defensively.
    if not getattr(res, "rowcount", 0):  # type: ignore[attr-defined]
        raise HTTPException(status_code=404, detail="Contributor not found")

    return {"ok": True}


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

