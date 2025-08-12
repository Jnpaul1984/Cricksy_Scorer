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
)

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete, update, or_, and_
from sqlalchemy.exc import IntegrityError
from fastapi import UploadFile, File, Form
from datetime import datetime, timezone
import json

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

    # team roles
    team_a_captain_id: Optional[str]
    team_a_keeper_id: Optional[str]
    team_b_captain_id: Optional[str]
    team_b_keeper_id: Optional[str]

    # timelines & scorecards
    deliveries: List[schemas.Delivery]
    batting_scorecard: Dict[str, schemas.BattingScorecardEntry]
    bowling_scorecard: Dict[str, schemas.BowlingScorecardEntry]

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
STATIC_DIR = os.getenv("STATIC_DIR", "static")
_fastapi.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

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
    """Seed a blank batting card for the selected team."""
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
    """Seed a blank bowling card for the *opposition* team."""
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
    Convert an integer ball count to a decimal representation of overs (1 decimal place).
    Example: 8 balls -> 1.2 (read as 1 over + 2 balls).
    """
    return round(balls / 6.0, 1)

# ================================================================
# Helpers: dismissal / extras rules
# ================================================================
# Bowler gets credit for these modes:
_CREDIT_BOWLER = {
    "bowled",
    "caught",
    "lbw",
    "stumped",
    "hit_wicket",
}

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

def _rotate_strike_on_runs(runs: int) -> bool:
    return (runs % 2) == 1

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

    match_type: schemas.Literal["limited", "multi_day", "custom"] = "limited"  # type: ignore[name-defined]
    overs_limit: Optional[int] = Field(None, ge=1, le=120)
    days_limit: Optional[int] = Field(None, ge=1, le=7)
    overs_per_day: Optional[int] = Field(None, ge=1, le=120)
    dls_enabled: bool = False
    interruptions: List[Dict[str, Optional[str]]] = Field(default_factory=list)

    toss_winner_team: str
    decision: schemas.Literal["bat", "bowl"]  # type: ignore[name-defined]

class OversLimitBody(BaseModel):
    overs_limit: int

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
def _ensure_batting_entry(g: GameState, batter_id: str) -> schemas.BattingScorecardEntry:
    try:
        return g.batting_scorecard[batter_id]
    except KeyError:
        entry = schemas.BattingScorecardEntry(
            player_id=batter_id,
            player_name=_player_name(g.team_a, g.team_b, batter_id),
            runs=0,
            balls_faced=0,
            is_out=False,
        )
        g.batting_scorecard[batter_id] = entry
        return entry

def _ensure_bowling_entry(g: GameState, bowler_id: str) -> schemas.BowlingScorecardEntry:
    try:
        return g.bowling_scorecard[bowler_id]
    except KeyError:
        entry = schemas.BowlingScorecardEntry(
            player_id=bowler_id,
            player_name=_player_name(g.team_a, g.team_b, bowler_id),
            overs_bowled=_bowling_balls_to_overs(0),
            runs_conceded=0,
            wickets_taken=0,
        )
        g.bowling_scorecard[bowler_id] = entry
        return entry

def _reset_runtime_and_scorecards(g: GameState) -> None:
    """Zero totals and rebuild scorecards for current batting/bowling teams."""
    g.total_runs = 0
    g.total_wickets = 0
    g.overs_completed = 0
    g.balls_this_over = 0
    g.current_striker_id = None
    g.current_non_striker_id = None

    batting_team = g.team_a if g.batting_team_name == g.team_a["name"] else g.team_b
    bowling_team = g.team_b if batting_team is g.team_a else g.team_a

    # Re-seed with schema entries (not plain dicts)
    g.batting_scorecard = {}
    for p in batting_team["players"]:
        g.batting_scorecard[p["id"]] = schemas.BattingScorecardEntry(
            player_id=p["id"], player_name=p["name"], runs=0, balls_faced=0, is_out=False
        )
    g.bowling_scorecard = {}
    for p in bowling_team["players"]:
        g.bowling_scorecard[p["id"]] = schemas.BowlingScorecardEntry(
            player_id=p["id"], player_name=p["name"], overs_bowled=0.0, runs_conceded=0, wickets_taken=0
        )

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
    """Apply a single delivery's effects to `g` and return kwargs for a ledger row."""
    # Initialize striker/non-striker if not yet set
    if g.current_striker_id is None:
        g.current_striker_id = striker_id
    if g.current_non_striker_id is None:
        g.current_non_striker_id = non_striker_id

    runs = int(runs_scored or 0)
    is_nb = _is_no_ball(extra)
    is_wd = _is_wide(extra)
    legal = not (is_nb or is_wd)

    # Totals
    g.total_runs = int(g.total_runs + runs)

    # Batting
    bs = _ensure_batting_entry(g, striker_id)
    bs.runs = int(bs.runs + runs)
    if legal:
        bs.balls_faced = int(bs.balls_faced + 1)

    # Bowling
    bw = _ensure_bowling_entry(g, bowler_id)
    bw.runs_conceded = int(bw.runs_conceded + runs)
    if legal:
        balls = int(round(bw.overs_bowled * 6)) + 1
        bw.overs_bowled = _bowling_balls_to_overs(balls)

    # Dismissal
    dismissal: Optional[str] = (dismissal_type or "").strip().lower() or None
    if dismissal:
        if is_nb and dismissal in _INVALID_ON_NO_BALL:
            dismissal = None
        if is_wd and dismissal in _INVALID_ON_WIDE:
            dismissal = None

    out_happened = False
    out_player_id = dismissed_player_id or striker_id
    if is_wicket and dismissal:
        out_happened = True

    if out_happened and out_player_id:
        out_entry = _ensure_batting_entry(g, out_player_id)
        out_entry.is_out = True
        g.total_wickets = int(g.total_wickets + 1)

        if dismissal in _CREDIT_BOWLER:
            bw2 = _ensure_bowling_entry(g, bowler_id)
            bw2.wickets_taken = int(bw2.wickets_taken + 1)

    # Over/ball progression + strike
    if legal:
        g.balls_this_over = int(g.balls_this_over + 1)
        if _rotate_strike_on_runs(runs):
            g.current_striker_id, g.current_non_striker_id = g.current_non_striker_id, g.current_striker_id
        if g.balls_this_over >= 6:
            g.overs_completed = int(g.overs_completed + 1)
            g.balls_this_over = 0
            g.current_striker_id, g.current_non_striker_id = g.current_non_striker_id, g.current_striker_id

    return {
        "over_number": int(g.overs_completed),
        "ball_number": int(g.balls_this_over),
        "bowler_id": str(bowler_id),
        "striker_id": str(striker_id),
        "non_striker_id": str(non_striker_id),
        "runs_scored": int(runs),
        "is_extra": extra is not None,
        "extra_type": extra,
        "is_wicket": bool(out_happened),
        "dismissal_type": dismissal,
        "dismissed_player_id": out_player_id if out_happened else None,
        "commentary": None,
        "fielder_id": None,
    }

def _bat_entry(g: GameState, pid: Optional[str]) -> schemas.BattingScorecardEntry:
    if not pid:
        return schemas.BattingScorecardEntry(player_id="", player_name="", runs=0, balls_faced=0, is_out=False)
    return g.batting_scorecard.get(
        pid,
        schemas.BattingScorecardEntry(
            player_id=pid, player_name=_player_name(g.team_a, g.team_b, pid), runs=0, balls_faced=0, is_out=False
        ),
    )

def _snapshot_from_game(g: GameState, last_delivery: Optional[schemas.Delivery]) -> Dict[str, Any]:
    snapshot: Dict[str, Any] = {
        "id": g.id,
        "status": g.status,
        "score": {"runs": g.total_runs, "wickets": g.total_wickets, "overs": g.overs_completed},
        "batsmen": {
            "striker": {
                "id": g.current_striker_id,
                "name": _player_name(g.team_a, g.team_b, g.current_striker_id),
                "runs": _bat_entry(g, g.current_striker_id).runs,
                "balls": _bat_entry(g, g.current_striker_id).balls_faced,
                "is_out": _bat_entry(g, g.current_striker_id).is_out,
            },
            "non_striker": {
                "id": g.current_non_striker_id,
                "name": _player_name(g.team_a, g.team_b, g.current_non_striker_id),
                "runs": _bat_entry(g, g.current_non_striker_id).runs,
                "balls": _bat_entry(g, g.current_non_striker_id).balls_faced,
                "is_out": _bat_entry(g, g.current_non_striker_id).is_out,
            },
        },
        "over": {"completed": g.overs_completed, "balls_this_over": g.balls_this_over},
        "last_delivery": last_delivery.model_dump() if last_delivery else None,
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
        batting_scorecard=batting_scorecard,
        bowling_scorecard=bowling_scorecard,
    )

    return db_game  # Pydantic orm_mode -> schemas.Game

@_fastapi.get("/games/{game_id}", response_model=schemas.Game)  # type: ignore[name-defined]
async def get_game(game_id: str, db: AsyncSession = Depends(get_db)):
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")
    return db_game

# ================================================================
# PR 1 — Record a delivery (with dismissal rules)
# ================================================================
@_fastapi.post("/games/{game_id}/deliveries")
async def add_delivery(
    game_id: str,
    delivery: schemas.ScoreDelivery,  # matches your schema
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g = cast(GameState, db_game)

    # Score one ball
    kwargs: DeliveryKwargs = _score_one(
        g,
        striker_id=delivery.striker_id,
        non_striker_id=delivery.non_striker_id,
        bowler_id=delivery.bowler_id,
        runs_scored=int(delivery.runs_scored or 0),
        extra=getattr(delivery, "extra", None),
        is_wicket=bool(getattr(delivery, "is_wicket", False)),
        dismissal_type=getattr(delivery, "dismissal_type", None),
        dismissed_player_id=getattr(delivery, "dismissed_player_id", None),
    )
    new_delivery = schemas.Delivery(**kwargs)

    try:
        g.deliveries.append(new_delivery)
    except Exception:
        g.deliveries = [new_delivery]  # type: ignore[assignment]

    # Persist & emit
    updated = await crud.update_game(db, game_model=db_game)
    u = cast(GameState, updated)

    snapshot = _snapshot_from_game(u, new_delivery)
    await sio.emit("state:update", {"id": game_id, "snapshot": snapshot}, room=game_id)
    return snapshot

# ================================================================
# PR 2 — Undo last ball (full state recompute from ledger)
# ================================================================
@_fastapi.post("/games/{game_id}/undo-last")
async def undo_last_delivery(game_id: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
    game = await crud.get_game(db, game_id=game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    g = cast(GameState, game)
    if not g.deliveries:
        raise HTTPException(status_code=409, detail="Nothing to undo")

    # Remove last delivery from ledger
    g.deliveries = g.deliveries[:-1]  # type: ignore[assignment]

    # Reset runtime & scorecards, then replay remaining ledger
    _reset_runtime_and_scorecards(g)
    for d in g.deliveries:
        _ = _score_one(
            g,
            striker_id=d.striker_id,
            non_striker_id=d.non_striker_id,
            bowler_id=d.bowler_id,
            runs_scored=int(d.runs_scored or 0),
            extra=d.extra_type,
            is_wicket=bool(d.is_wicket),
            dismissal_type=d.dismissal_type,
            dismissed_player_id=d.dismissed_player_id,
        )

    updated = await crud.update_game(db, game_model=game)
    u = cast(GameState, updated)
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
    game = await crud.get_game(db, game_id=game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    g = cast(GameState, game)
    bowled_balls = g.overs_completed * 6 + g.balls_this_over
    new_limit_balls = int(body.overs_limit) * 6

    if new_limit_balls < bowled_balls:
        raise HTTPException(status_code=400, detail="New limit is less than overs already bowled")

    g.overs_limit = int(body.overs_limit)
    updated = await crud.update_game(db, game_model=game)
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
    last = g.deliveries[-1] if g.deliveries else None
    snap = _snapshot_from_game(g, last)

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
# Team Roles (captain / wicket-keeper)
# ================================================================
@_fastapi.post("/games/{game_id}/team-roles")
async def set_team_roles(
    game_id: str,
    payload: schemas.TeamRoleUpdate,
    db: AsyncSession = Depends(get_db),
):
    game = await crud.get_game(db, game_id=game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    g = cast(GameState, game)
    # Validate role ids are on the correct team
    if payload.side == schemas.TeamSide.A:
        players = g.team_a.get("players", [])
    else:
        players = g.team_b.get("players", [])
    player_ids = {p["id"] for p in players}

    if payload.captain_id and payload.captain_id not in player_ids:
        raise HTTPException(status_code=400, detail="captain_id not in team players")
    if payload.wicket_keeper_id and payload.wicket_keeper_id not in player_ids:
        raise HTTPException(status_code=400, detail="wicket_keeper_id not in team players")

    # Update DB columns directly
    if payload.side == schemas.TeamSide.A:
        g.team_a_captain_id = payload.captain_id
        g.team_a_keeper_id = payload.wicket_keeper_id
    else:
        g.team_b_captain_id = payload.captain_id
        g.team_b_keeper_id = payload.wicket_keeper_id

    await crud.update_game(db, game_model=game)
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

    # Surfaces parsing — ensure a list[str] WITHOUT generator-typed vars
    try:
        parsed_any: Any = json.loads(surfaces) if surfaces else ["all"]
    except Exception:
        raise HTTPException(status_code=400, detail="surfaces must be a JSON array of strings")

    if not isinstance(parsed_any, list):
        raise HTTPException(status_code=400, detail="surfaces must be a JSON array of strings")

    parsed_list: List[Any] = cast(List[Any], parsed_any)
    # Validate items explicitly (avoid `x` in a generator)
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
async def list_contributors(game_id: str, db: AsyncSession = Depends(get_db)):
    stmt = select(models.GameContributor).where(models.GameContributor.game_id == game_id)
    res = await db.execute(stmt)
    rows = res.scalars().all()
    out: List[schemas.GameContributor] = []
    for r in rows:
        out.append(
            schemas.GameContributor(
                id=cast(int, r.id),
                game_id=cast(str, r.game_id),
                user_id=cast(str, r.user_id),
                role=schemas.GameContributorRole(cast(str, r.role)),
                display_name=cast(Optional[str], r.display_name),
            )
        )
    return out

@_fastapi.delete("/games/{game_id}/contributors/{contrib_id}")
async def remove_contributor(game_id: str, contrib_id: int, db: AsyncSession = Depends(get_db)):
    stmt = delete(models.GameContributor).where(
        models.GameContributor.game_id == game_id,
        models.GameContributor.id == contrib_id,
    )
    res = await db.execute(stmt)
    await db.commit()
    if res.rowcount == 0:  # type: ignore[attr-defined]
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
    payload: Dict[str, str] = {"status": "ok"}
    return payload

# ================================================================
# Local dev entrypoint (optional)
# ================================================================
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)  # pyright: ignore[reportUnknownMemberType]
