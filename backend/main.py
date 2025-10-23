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
from backend.routes.gameplay import router as gameplay_router
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

_fastapi.include_router(games_dls_router)
_fastapi.include_router(interruptions_router)
_fastapi.include_router(games_router)
_fastapi.include_router(gameplay_router)

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

