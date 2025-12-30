from __future__ import annotations

import datetime as dt
from collections.abc import Mapping, Sequence
from pathlib import Path
from typing import Annotated, Any, Literal, cast

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend import dls as dlsmod
from backend.domain.constants import as_extra_code as norm_extra
from backend.routes import games as _games_impl
from backend.services import game_helpers as gh
from backend.services import validation as validation_helpers
from backend.services.live_bus import emit_state_update
from backend.services.scoring_service import score_one as _score_one
from backend.services.snapshot_service import build_snapshot as _snapshot_from_game
from backend.sql_app import crud, models, schemas
from backend.sql_app.database import get_db

# Local type alias for JSON dictionaries
JSONDict = dict[str, Any]

UTC = getattr(dt, "UTC", dt.UTC)
router = APIRouter(prefix="/games", tags=["gameplay"])


BASE_DIR = Path(__file__).resolve().parent


def _model_to_dict(x: Any) -> dict[str, Any] | None:
    # Minimal copy of main._model_to_dict for this router
    try:
        from pydantic import (
            BaseModel as _PydanticBaseModel,  # local import to avoid circulars at import time
        )
    except Exception:
        _PydanticBaseModel = None  # type: ignore[assignment]  # nosec

    if isinstance(x, dict):
        # Narrow the dict to a concrete mapping for static analysis
        d_map = cast(dict[str, Any], x)
        return {str(k): v for k, v in d_map.items()}

    if _PydanticBaseModel is not None and isinstance(x, _PydanticBaseModel):  # type: ignore[arg-type]
        try:
            md = x.model_dump()  # pydantic v2
            md2: dict[str, Any] = md
            return {str(k): v for k, v in md2.items()}  # type: ignore[union-attr]
        except Exception:
            try:
                md = x.dict()  # type: ignore[attr-defined]
                md_dict: dict[str, Any] = dict(md)
                return {str(k): v for k, v in md_dict.items()}
            except Exception:
                return None  # nosec

    for attr in ("model_dump", "dict"):
        fn = getattr(x, attr, None)
        if callable(fn):
            try:
                data = fn()
                if isinstance(data, dict):
                    data2 = cast(dict[str, Any], data)
                    return {str(k): v for k, v in data2.items()}
            except Exception:
                return None  # nosec

    return None


# Safe dynamic caller for private helpers in game_helpers (avoids static private
# usage diagnostics while keeping runtime behavior identical when helpers exist)
def _gh(name: str, *args: Any, **kwargs: Any) -> Any:
    fn = getattr(gh, name, None)
    if callable(fn):
        return fn(*args, **kwargs)
    return None


# Small runtime helper to coerce unknown values to int safely for static checks
def _to_int_safe(x: Any) -> int:
    try:
        return int(x)  # type: ignore[arg-type]
    except Exception:
        return 0  # nosec


# Local helper: close innings if all out or overs exhausted (ported from main.py)
async def _maybe_close_innings(g: Any) -> None:
    balls_limit = (g.overs_limit or 0) * 6
    balls_bowled = int(
        getattr(g, "balls_bowled_total", None)
        or (int(getattr(g, "overs_completed", 0)) * 6 + int(getattr(g, "balls_this_over", 0)))
    )

    if g.status == models.GameStatus.innings_break:
        return

    all_out = g.total_wickets >= 10
    overs_exhausted = balls_limit > 0 and balls_bowled >= balls_limit

    if all_out or overs_exhausted:
        if not hasattr(g, "innings_history"):
            g.innings_history = []

        # Only archive if not already archived
        innings_history: list[dict[str, Any]] = list(getattr(g, "innings_history", []) or [])  # type: ignore[assignment]
        already_archived = any(inn.get("inning_no") == g.current_inning for inn in innings_history)
        if not already_archived:
            entry = {
                "inning_no": g.current_inning or 1,
                "batting_team": g.batting_team_name,
                "bowling_team": g.bowling_team_name,
                "runs": g.total_runs,
                "wickets": g.total_wickets,
                "overs": _gh("_overs_string_from_ledger", g),
                "batting_scorecard": g.batting_scorecard,
                "bowling_scorecard": g.bowling_scorecard,
                "deliveries": g.deliveries,
                "closed_at": dt.datetime.now(UTC).isoformat(),
            }
            innings_history.append(entry)
            g.innings_history = innings_history  # type: ignore[assignment]

        g.status = models.GameStatus.innings_break
        # g.needs_new_innings is a computed property based on status
        g.needs_new_over = False
        g.needs_new_batter = False
        g.current_striker_id = None
        g.current_non_striker_id = None
        g.current_bowler_id = None


class StartOverBody(BaseModel):
    bowler_id: str


class MidOverChangeBody(BaseModel):
    new_bowler_id: str
    reason: Literal["injury", "other"] = "injury"


class StartNextInningsBody(BaseModel):
    striker_id: str | None = None
    non_striker_id: str | None = None
    opening_bowler_id: str | None = None


class NextBatterBody(BaseModel):
    batter_id: str


class ReplaceBatterBody(BaseModel):
    new_batter_id: str


@router.post("/{game_id}/overs/start")
async def start_over(
    game_id: str,
    body: StartOverBody,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g: Any = db_game

    # Ensure runtime attrs exist (legacy rows)
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

    # Constraint: cannot start mid-over; cannot be same as last over's bowler
    err = _gh("_can_start_over", g, body.bowler_id)
    if err:
        raise HTTPException(status_code=400, detail=err)

    g.current_bowler_id = body.bowler_id
    g.current_over_balls = 0
    g.mid_over_change_used = False
    g.pending_new_over = False

    _gh("_rebuild_scorecards_from_deliveries", g)
    _gh("_recompute_totals_and_runtime", g)

    updated = await crud.update_game(db, game_model=db_game)
    u = updated
    snap = _snapshot_from_game(u, None, BASE_DIR)

    # Emit to room
    await emit_state_update(game_id, snap)

    return {"ok": True, "current_bowler_id": g.current_bowler_id}


@router.get("/{game_id}/deliveries")
async def get_deliveries(
    game_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    innings: int | None = Query(None, ge=1, le=4, description="Filter by innings number"),
    limit: int = Query(500, ge=1, le=500, description="Max number of rows to return"),
    order: Literal["desc", "asc"] = Query("desc", description="desc = newest-first"),
) -> dict[str, Any]:
    """
    Returns deliveries for a game (optionally filtered by innings),
    ordered newest-first by default.
    Response shape matches the previous main.py implementation.
    """
    game = await crud.get_game(db, game_id=game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    g = cast(Any, game)

    # Read the raw ledger (combined across innings)
    raw_seq: Sequence[Any] = getattr(g, "deliveries", []) or []
    rows: list[dict[str, Any]] = []
    for item in raw_seq:
        d = _model_to_dict(item)
        if d is not None:
            # normalize extra_type to the canonical union expected by schemas.Delivery
            if "extra_type" in d:
                d["extra_type"] = norm_extra(cast(str | None, d.get("extra_type")))
            # ensure there is an int innings tag; default legacy to 1
            try:
                d["inning"] = int(d.get("inning", 1) or 1)
            except Exception:
                d["inning"] = 1  # nosec
            rows.append(d)

    # Optional innings filter
    if innings is not None:
        rows = [d for d in rows if int(d.get("inning", 1)) == int(innings)]

    # Enforce order + limit
    rows = rows[-limit:][::-1] if order == "desc" else rows[:limit]

    # Validate/shape with Pydantic (keeps wire format consistent)
    out: list[dict[str, Any]] = []
    for d_any in rows:
        try:
            model = schemas.Delivery(**d_any)  # type: ignore[call-arg]
            shaped = model.model_dump()
        except Exception:
            try:
                model = schemas.Delivery(**d_any)  # type: ignore[call-arg]
                shaped = model.dict()  # type: ignore[attr-defined]
            except Exception:
                continue  # nosec

        # Enrich names for UI convenience
        shaped["striker_name"] = cast(
            str | None,
            _gh("_player_name", g.team_a, g.team_b, shaped.get("striker_id")),
        )
        shaped["non_striker_name"] = cast(
            str | None,
            _gh("_player_name", g.team_a, g.team_b, shaped.get("non_striker_id")),
        )
        shaped["bowler_name"] = cast(
            str | None, _gh("_player_name", g.team_a, g.team_b, shaped.get("bowler_id"))
        )
        # pass through innings tag
        shaped["inning"] = d_any.get("inning", 1)
        out.append(shaped)

    return {
        "game_id": game_id,
        "count": len(out),
        "deliveries": out,  # ordered per `order` (desc by default)
    }


@router.post("/{game_id}/overs/change_bowler")
async def change_bowler_mid_over(
    game_id: str,
    body: MidOverChangeBody,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g: Any = db_game

    # Ensure runtime attrs exist (legacy rows)
    if getattr(g, "current_over_balls", None) is None:
        g.current_over_balls = 0
    if getattr(g, "mid_over_change_used", None) is None:
        g.mid_over_change_used = False
    if not hasattr(g, "current_bowler_id"):
        g.current_bowler_id = None
    if not hasattr(g, "last_ball_bowler_id"):
        g.last_ball_bowler_id = None

    # Rebuild runtime to set current_bowler_id/current_over_balls correctly
    _gh("_rebuild_scorecards_from_deliveries", g)
    _gh("_recompute_totals_and_runtime", g)

    # Validate match state
    status_ok = str(getattr(g, "status", "in_progress")).lower() in {
        "in_progress",
        "live",
        "started",
    }
    if not status_ok:
        raise HTTPException(status_code=409, detail=f"Game is {getattr(g, 'status', 'unknown')}")

    balls_this_over = int(getattr(g, "current_over_balls", 0) or 0)
    current = getattr(g, "current_bowler_id", None)

    # Must be mid-over and have an active bowler
    if not current or balls_this_over <= 0:
        raise HTTPException(status_code=409, detail="Over not in progress; use /overs/start")

    if getattr(g, "mid_over_change_used", False):
        raise HTTPException(status_code=409, detail="Mid-over change already used this over")

    if str(body.new_bowler_id) == str(current):
        raise HTTPException(status_code=409, detail="New bowler is already the current bowler")

    # New bowler must be in the bowling team
    bowling_team_name = getattr(g, "bowling_team_name", None)
    team_a = cast(dict[str, Any], g.team_a)
    team_b = cast(dict[str, Any], g.team_b)
    if not (bowling_team_name and team_a and team_b):
        raise HTTPException(status_code=500, detail="Teams not initialized on game")
    bowling_team: dict[str, Any] = team_a if team_a["name"] == bowling_team_name else team_b
    players: list[dict[str, Any]] = list(bowling_team.get("players", []) or [])  # type: ignore[assignment]
    allowed = {str(p["id"]) for p in players}
    if str(body.new_bowler_id) not in allowed:
        raise HTTPException(status_code=409, detail="Bowler is not in the bowling team")

    # Apply change (do NOT touch last_ball_bowler_id; over-boundary concept)
    g.current_bowler_id = str(body.new_bowler_id)
    g.mid_over_change_used = True

    _gh("_recompute_totals_and_runtime", g)
    updated = await crud.update_game(db, game_model=db_game)
    u = cast(Any, updated)

    # Build/augment snapshot so UI has everything it needs immediately
    snap = _snapshot_from_game(u, None, BASE_DIR)
    # Ensure runtime keys are present in snapshot payload:
    snap["current_bowler_id"] = g.current_bowler_id
    snap["last_ball_bowler_id"] = g.last_ball_bowler_id
    snap["current_over_balls"] = g.current_over_balls
    snap["mid_over_change_used"] = g.mid_over_change_used
    snap["needs_new_over"] = bool(getattr(g, "needs_new_over", False))

    from backend.services.live_bus import emit_state_update

    await emit_state_update(game_id, snap)

    return snap


@router.post("/{game_id}/innings/end")
async def end_current_innings(
    game_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    """
    Manually end the current innings and set status to innings_break.
    Useful for testing or manual control.
    """
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g: Any = db_game

    # Don't end if already at innings break or completed
    if g.status == models.GameStatus.innings_break:
        return {"message": "Already at innings break"}
    if g.status == models.GameStatus.completed:
        raise HTTPException(status_code=400, detail="Match already completed")

    # Archive the current innings
    if not hasattr(g, "innings_history"):
        g.innings_history = []

    innings_history: list[dict[str, Any]] = list(getattr(g, "innings_history", []) or [])
    already_archived = any(inn.get("inning_no") == g.current_inning for inn in innings_history)

    if not already_archived:
        batting_scorecard_map: dict[str, Any] = dict(getattr(g, "batting_scorecard", {}) or {})
        bowling_scorecard_map: dict[str, Any] = dict(getattr(g, "bowling_scorecard", {}) or {})

        entry = {
            "inning_no": g.current_inning or 1,
            "batting_team": g.batting_team_name,
            "bowling_team": g.bowling_team_name,
            "runs": g.total_runs,
            "wickets": g.total_wickets,
            "overs": _gh("_overs_string_from_ledger", g),
            "batting_scorecard": batting_scorecard_map,
            "bowling_scorecard": bowling_scorecard_map,
            "closed_at": dt.datetime.now(UTC).isoformat(),
        }
        innings_history.append(entry)
        g.innings_history = innings_history

    # Set status to innings break
    g.status = models.GameStatus.innings_break
    # g.needs_new_innings is a computed property based on status
    g.needs_new_over = False
    g.needs_new_batter = False
    g.current_striker_id = None
    g.current_non_striker_id = None
    g.current_bowler_id = None

    # Persist
    updated = await crud.update_game(db, game_model=db_game)
    u = cast(Any, updated)

    # Build snapshot and emit
    _gh("_rebuild_scorecards_from_deliveries", u)
    _gh("_recompute_totals_and_runtime", u)
    snap = _snapshot_from_game(u, None, BASE_DIR)

    from backend.services.live_bus import emit_innings_grade_update, emit_state_update

    await emit_state_update(game_id, snap)

    # Calculate and emit innings grade
    try:
        from backend.services.innings_grade_service import get_innings_grade

        # Get deliveries for this innings
        deliveries_data = None
        if u.deliveries:
            deliveries_data = [
                d
                for d in u.deliveries
                if d.get("inning_no") == u.current_inning or d.get("innings_no") == u.current_inning
            ]

        game_state = {
            "total_runs": u.total_runs,
            "total_wickets": u.total_wickets,
            "overs_completed": u.overs_completed,
            "balls_this_over": u.balls_this_over,
            "overs_limit": u.overs_limit,
            "deliveries": deliveries_data or [],
            "is_completed": True,  # Innings is completed
        }

        grade_data = get_innings_grade(game_state)
        grade_data["inning_num"] = u.current_inning
        grade_data["game_id"] = game_id
        grade_data["batting_team"] = u.batting_team_name
        grade_data["bowling_team"] = u.bowling_team_name

        # Store in database
        innings_grade = models.InningsGrade(
            game_id=game_id,
            inning_num=u.current_inning,
            grade=grade_data["grade"],
            score_percentage=grade_data["score_percentage"],
            par_score=grade_data["par_score"],
            total_runs=grade_data["total_runs"],
            run_rate=grade_data["run_rate"],
            wickets_lost=grade_data["wickets_lost"],
            wicket_efficiency=grade_data["wicket_efficiency"],
            boundary_count=grade_data["boundary_count"],
            boundary_percentage=grade_data["boundary_percentage"],
            dot_ball_ratio=grade_data["dot_ball_ratio"],
            overs_played=grade_data["overs_played"],
        )

        db.add(innings_grade)
        await db.commit()

        # Emit real-time grade update
        await emit_innings_grade_update(game_id, grade_data)
    except Exception as e:
        # Don't let grade calculation failure break the innings end flow
        import logging

        logger = logging.getLogger(__name__)
        logger.warning(f"Failed to calculate innings grade: {e}")

    return snap


@router.post("/{game_id}/innings/start")
async def start_next_innings(
    game_id: str,
    body: StartNextInningsBody,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g: Any = db_game

    # Must be at innings break to start the next one
    if g.status != models.GameStatus.innings_break:
        raise HTTPException(status_code=400, detail="No new innings to start")

    # Ensure legacy attrs exist
    if not isinstance(getattr(g, "innings_history", None), list):
        g.innings_history = []
    # Handle transition from Inning 0 (Pre-match) -> 1, or Inning N -> N+1
    current_inn = int(getattr(g, "current_inning", 0) or 0)

    if current_inn == 0:
        # Starting First Innings
        g.current_inning = 1
        # Teams and scorecards are already set by create_game
        g.total_runs = 0
        g.total_wickets = 0
        g.overs_completed = 0
        g.balls_this_over = 0
    else:
        # Starting Subsequent Innings
        prev_batting_team = g.batting_team_name
        prev_bowling_team = g.bowling_team_name

        # Archive the COMPLETED innings
        hist2: list[dict[str, Any]] = list(getattr(g, "innings_history", []) or [])  # type: ignore[assignment]
        last_archived_no = hist2[-1]["inning_no"] if hist2 else None

        if last_archived_no != current_inn:
            batting_scorecard_map: dict[str, Any] = dict(getattr(g, "batting_scorecard", {}) or {})
            bowling_scorecard_map: dict[str, Any] = dict(getattr(g, "bowling_scorecard", {}) or {})

            entry = {
                "inning_no": current_inn,
                "batting_team": prev_batting_team,
                "bowling_team": prev_bowling_team,
                "runs": g.total_runs,
                "wickets": g.total_wickets,
                "overs": _gh("_overs_string_from_ledger", g),
                "batting_scorecard": batting_scorecard_map,
                "bowling_scorecard": bowling_scorecard_map,
                # DO NOT destroy the ledger; it spans both innings
                "closed_at": dt.datetime.now(UTC).isoformat(),
            }
            hist2.append(entry)
            g.innings_history = hist2  # type: ignore[assignment]

        # Advance innings and flip teams
        g.current_inning = current_inn + 1
        g.batting_team_name, g.bowling_team_name = prev_bowling_team, prev_batting_team

        # Reset per-innings runtime counters (keep combined deliveries ledger)
        g.total_runs = 0
        g.total_wickets = 0
        g.overs_completed = 0
        g.balls_this_over = 0

        # (Re)build fresh scorecards for the new batting/bowling teams
        g.batting_scorecard = _gh(
            "_mk_batting_scorecard",
            g.team_a if g.batting_team_name == g.team_a["name"] else g.team_b,
        )
        g.bowling_scorecard = _gh(
            "_mk_bowling_scorecard",
            g.team_b if g.batting_team_name == g.team_a["name"] else g.team_a,
        )

    # Apply optional openers from body
    g.current_striker_id = body.striker_id or None
    g.current_non_striker_id = body.non_striker_id or None
    if not hasattr(g, "current_bowler_id"):
        g.current_bowler_id = None
    g.current_bowler_id = body.opening_bowler_id or None

    # Clear â€œgateâ€ flags and mark match live
    if not hasattr(g, "needs_new_over"):
        g.needs_new_over = False
    if not hasattr(g, "needs_new_batter"):
        g.needs_new_batter = False
    # g.needs_new_innings is computed from status

    if g.current_inning >= 2:
        if g.first_inning_summary is None:
            g.first_inning_summary = _gh("_first_innings_summary", g)
        _gh("_ensure_target_if_chasing", g)

    g.needs_new_over = g.current_bowler_id is None
    g.needs_new_batter = g.current_striker_id is None or g.current_non_striker_id is None
    g.status = models.GameStatus.in_progress

    # Recompute derived/runtime and persist
    _gh("_rebuild_scorecards_from_deliveries", g)
    _gh("_recompute_totals_and_runtime", g)
    updated = await crud.update_game(db, game_model=db_game)
    u = cast(Any, updated)

    # Snapshot + emit
    snap = _snapshot_from_game(u, None, BASE_DIR)
    snap["needs_new_innings"] = False
    snap["needs_new_over"] = g.current_bowler_id is None
    snap["needs_new_batter"] = g.current_striker_id is None or g.current_non_striker_id is None

    from backend.services.live_bus import emit_state_update

    await emit_state_update(game_id, snap)

    return snap


@router.post("/{game_id}/openers")
async def set_openers(
    game_id: str,
    body: dict[str, str],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g: Any = db_game

    striker_id = str(body.get("striker_id") or "")
    non_striker_id = str(body.get("non_striker_id") or "")

    g.current_striker_id = striker_id
    g.current_non_striker_id = non_striker_id

    updated = await crud.update_game(db, game_model=db_game)
    u = cast(Any, updated)

    _gh("_rebuild_scorecards_from_deliveries", u)
    _gh("_recompute_totals_and_runtime", u)
    _gh("_complete_game_by_result", u)
    snap = _snapshot_from_game(u, None, BASE_DIR)

    from backend.services.live_bus import emit_state_update

    await emit_state_update(game_id, snap)

    return snap


@router.post("/{game_id}/batters/replace")
async def replace_batter(
    game_id: str,
    body: ReplaceBatterBody,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g: Any = db_game

    # Ensure latest state
    _gh("_rebuild_scorecards_from_deliveries", g)
    _gh("_recompute_totals_and_runtime", g)

    # Narrow batting_scorecard into a concrete mapping for static checks
    batting_scorecard_map: dict[str, Any] = cast(
        dict[str, Any], dict(getattr(g, "batting_scorecard", {}) or {})
    )

    # Determine which current batter is out
    def _is_out(pid: str | None) -> bool:
        if not pid:
            return False
        entry = batting_scorecard_map.get(pid)
        entry_map = _model_to_dict(entry) or {}
        return bool(entry_map.get("is_out", False))

    if _is_out(g.current_striker_id):
        g.current_striker_id = body.new_batter_id
    elif _is_out(g.current_non_striker_id):
        g.current_non_striker_id = body.new_batter_id
    else:
        raise HTTPException(
            status_code=409, detail="No striker or non-striker requires replacement."
        )

    # Ensure scorecard entry exists for the incoming batter
    _gh("_ensure_batting_entry", g, body.new_batter_id)

    # Persist and snapshot
    from sqlalchemy.orm.attributes import flag_modified

    flag_modified(db_game, "batting_scorecard")
    updated = await crud.update_game(db, game_model=db_game)
    u = cast(Any, updated)

    dl_any = cast(list[Mapping[str, Any]], _gh("_dedup_deliveries", u) or [])
    dl: list[Mapping[str, Any]] = list(dl_any)  # type: ignore[assignment]
    last = cast(dict[str, Any], dl[-1]) if dl else None
    snap = _snapshot_from_game(u, last, BASE_DIR)
    flags = cast(dict[str, Any], _gh("_compute_snapshot_flags", u) or {})
    snap["needs_new_batter"] = flags["needs_new_batter"]
    snap["needs_new_over"] = flags["needs_new_over"]

    from backend.services.live_bus import emit_state_update

    await emit_state_update(game_id, snap)

    return snap


@router.post("/{game_id}/next-batter")
async def set_next_batter(
    game_id: str,
    body: NextBatterBody,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g: Any = db_game

    if getattr(g, "pending_new_batter", None) is None:
        g.pending_new_batter = False

    # If no replacement is required, no-op
    if not g.pending_new_batter:
        return {"ok": True, "message": "No replacement batter required"}

    # Convention: new batter becomes striker after a wicket
    g.current_striker_id = body.batter_id

    _gh("_ensure_batting_entry", g, body.batter_id)

    g.pending_new_batter = False

    _gh("_rebuild_scorecards_from_deliveries", g)
    _gh("_recompute_totals_and_runtime", g)

    updated = await crud.update_game(db, game_model=db_game)
    u = cast(Any, updated)
    snap = _snapshot_from_game(u, None, BASE_DIR)

    from backend.services.live_bus import emit_state_update

    await emit_state_update(game_id, snap)

    return {"ok": True, "current_striker_id": g.current_striker_id}


@router.post("/{game_id}/finalize")
async def finalize_game(
    game_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g: Any = db_game

    _gh("_rebuild_scorecards_from_deliveries", g)
    _gh("_recompute_totals_and_runtime", g)
    _gh("_ensure_target_if_chasing", g)

    # Try both finalizers (one uses runtime, one re-reads ledger)
    _gh("_complete_game_by_result", g)
    _gh("_maybe_finalize_match", g)

    updated = await crud.update_game(db, game_model=db_game)
    u = cast(Any, updated)
    snap = _snapshot_from_game(u, None, BASE_DIR)

    from backend.services.live_bus import emit_state_update

    await emit_state_update(game_id, snap)

    return snap


@router.get("/{game_id}/snapshot")
async def get_snapshot(
    game_id: str, db: Annotated[AsyncSession, Depends(get_db)]
) -> dict[str, Any]:
    game = await crud.get_game(db, game_id=game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    g = cast(Any, game)
    # Ensure runtime fields exist (legacy safety)
    if getattr(g, "current_over_balls", None) is None:
        g.current_over_balls = 0
    if getattr(g, "mid_over_change_used", None) is None:
        g.mid_over_change_used = False
    if not hasattr(g, "current_bowler_id"):
        g.current_bowler_id = None
    if not hasattr(g, "last_ball_bowler_id"):
        g.last_ball_bowler_id = None

    # Rebuild from ledger BEFORE panels
    _gh("_rebuild_scorecards_from_deliveries", g)
    _gh("_recompute_totals_and_runtime", g)

    dl_any = cast(list[Mapping[str, Any]], _gh("_dedup_deliveries", g) or [])
    dl: list[Mapping[str, Any]] = list(dl_any)  # type: ignore[assignment]
    last = cast(dict[str, Any], dl[-1]) if dl else None
    snap = _snapshot_from_game(g, last, BASE_DIR)

    # UI gating flags
    flags = cast(dict[str, Any], _gh("_compute_snapshot_flags", g) or {})
    is_break = str(getattr(g, "status", "")).lower() == "innings_break" or bool(
        getattr(g, "needs_new_innings", False)
    )

    snap["needs_new_batter"] = flags["needs_new_batter"]
    snap["needs_new_over"] = False if is_break else flags["needs_new_over"]
    snap["needs_new_innings"] = is_break

    # Interruption records + mini cards
    snap["interruptions"] = cast(list[dict[str, Any]], getattr(g, "interruptions", []) or [])
    snap["mini_batting_card"] = _gh("_mini_batting_card", g)
    snap["mini_bowling_card"] = _gh("_mini_bowling_card", g)

    # DLS panel best-effort (matches main.py logic)
    try:
        overs_limit_opt = cast(int | None, getattr(g, "overs_limit", None))
        current_innings = int(getattr(g, "current_inning", 1) or 1)
        if (
            isinstance(overs_limit_opt, int)
            and current_innings >= 2
            and overs_limit_opt in (20, 50)
        ):
            format_overs = int(overs_limit_opt)
            kind: Literal["odi", "t20"] = "odi" if format_overs >= 40 else "t20"
            env = dlsmod.load_env(kind, str(BASE_DIR))

            deliveries_m: list[Mapping[str, Any]] = list(getattr(g, "deliveries", []))
            interruptions = list(getattr(g, "interruptions", []))

            R1_total = dlsmod.total_resources_team1(
                env=env,
                max_overs_initial=format_overs,
                deliveries=deliveries_m,
                interruptions=interruptions,
            )
            s1 = 0
            fis_any = getattr(g, "first_inning_summary", None)
            if isinstance(fis_any, dict) and "runs" in fis_any:
                try:
                    # use safe coercion helper to avoid pyright unknown-arg warnings
                    s1 = _to_int_safe(fis_any["runs"])
                except Exception:
                    s1 = 0  # nosec
            else:
                # Sum runs from first-innings deliveries using a typed local list to avoid
                # partially-unknown generator types in static checks.
                s1 = 0
                deliveries_list: list[Mapping[str, Any]] = list(getattr(g, "deliveries", []) or [])
                for d in deliveries_list:
                    try:
                        if int(d.get("inning", 1) or 1) == 1:
                            s1 += int(d.get("runs_scored") or 0)
                    except Exception:
                        # Ignore malformed entries
                        continue  # nosec

            overs_completed = float(getattr(g, "overs_completed", 0.0) or 0.0)
            balls_this_over = float(getattr(g, "balls_this_over", 0.0) or 0.0)
            team2_overs_left_now = max(
                0.0, float(format_overs) - (overs_completed + (balls_this_over / 6.0))
            )
            team2_wkts_now = int(getattr(g, "total_wickets", 0)) if current_innings == 2 else 0

            R_start = env.table.R(format_overs, 0)
            R_remaining = env.table.R(team2_overs_left_now, team2_wkts_now)
            R2_used = max(0.0, R_start - R_remaining)

            try:
                par_raw = dlsmod.par_score_now(S1=s1, R1_total=R1_total, R2_used_so_far=R2_used)
                par_now = _to_int_safe(par_raw)
            except Exception:
                par_now = 0  # nosec
            try:
                target_raw = dlsmod.revised_target(S1=s1, R1_total=R1_total, R2_total=R_start)
                target_full = _to_int_safe(target_raw)
            except Exception:
                target_full = 0  # nosec

            snap["dls"] = {"method": "DLS", "par": par_now, "target": target_full}
    except Exception:
        # Leave snapshot_service panel if ours fails
        pass  # nosec

    # Enrich for bootstrap (team names + player lists), matches main.py
    snap["teams"] = {
        "batting": {"name": g.batting_team_name},
        "bowling": {"name": g.bowling_team_name},
    }
    # Narrow team objects to concrete mappings before iterating players
    team_a_map: dict[str, Any] = dict(getattr(g, "team_a", {}) or {})
    team_b_map: dict[str, Any] = dict(getattr(g, "team_b", {}) or {})
    batting_team_map = team_a_map if g.batting_team_name == team_a_map.get("name") else team_b_map
    bowling_team_map = team_b_map if g.batting_team_name == team_a_map.get("name") else team_a_map

    snap["players"] = {
        "batting": [
            {"id": p["id"], "name": p["name"]}
            for p in list(batting_team_map.get("players", []) or [])
        ],
        "bowling": [
            {"id": p["id"], "name": p["name"]}
            for p in list(bowling_team_map.get("players", []) or [])
        ],
    }

    # Add win probability prediction to snapshot (so frontend has it on page load)
    try:
        from backend.services.prediction_service import get_win_probability

        game_state_for_prediction = {
            "current_inning": g.current_inning,
            "total_runs": g.total_runs,
            "total_wickets": g.total_wickets,
            "overs_completed": g.overs_completed,
            "balls_this_over": g.balls_this_over,
            "overs_limit": g.overs_limit,
            "target": g.target,
            "match_type": g.match_type,
        }
        prediction = get_win_probability(game_state_for_prediction)
        prediction["batting_team"] = g.batting_team_name
        prediction["bowling_team"] = g.bowling_team_name
        snap["prediction"] = prediction
    except Exception:
        # Don't break snapshot if prediction fails
        pass

    return snap


@router.get("/{game_id}/recent_deliveries")
async def get_recent_deliveries(
    game_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    limit: int = Query(10, ge=1, le=50, description="Max number of most recent deliveries"),
) -> dict[str, Any]:
    """
    Returns the most-recent `limit` deliveries for a game, newest-first.
    Each delivery matches schemas.Delivery (wire-safe dict).
    """
    game = await crud.get_game(db, game_id=game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    g = cast(Any, game)

    # Slice last N from the authoritative ledger, newest-first
    raw_seq: Sequence[Any] = getattr(g, "deliveries", []) or []
    tail: list[Any] = list(raw_seq)[-limit:][::-1]

    # Normalize each item to a dict
    ledger: list[dict[str, Any]] = []
    for item in tail:
        d = _model_to_dict(item)
        if d is not None:
            ledger.append(d)

    # Validate/shape with Pydantic
    out: list[dict[str, Any]] = []
    for d_any in ledger:
        try:
            if "extra_type" in d_any:
                x = _gh("_norm_extra", d_any.get("extra_type"))
                d_any["extra_type"] = x
            model = schemas.Delivery(**d_any)  # type: ignore[call-arg]
            out.append(model.model_dump())
        except Exception:
            try:
                model = schemas.Delivery(**d_any)  # type: ignore[call-arg]
                out.append(model.dict())  # type: ignore[attr-defined]
            except Exception:
                continue  # nosec

    # Enrich with names
    for i, row in enumerate(out):
        row["striker_name"] = cast(
            str | None, _gh("_player_name", g.team_a, g.team_b, row.get("striker_id"))
        )
        row["non_striker_name"] = cast(
            str | None,
            _gh("_player_name", g.team_a, g.team_b, row.get("non_striker_id")),
        )
        row["bowler_name"] = cast(
            str | None, _gh("_player_name", g.team_a, g.team_b, row.get("bowler_id"))
        )
        row["inning"] = int(ledger[i].get("inning", 1) or 1)

    return {
        "game_id": game_id,
        "count": len(out),
        "deliveries": out,  # newest-first
    }


@router.post("/{game_id}/deliveries")
async def add_delivery(
    game_id: str,
    delivery: schemas.ScoreDelivery,
    db: Annotated[AsyncSession, Depends(get_db)],
) -> dict[str, Any]:
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g: Any = db_game

    # Check if game is already completed/finalized
    if g.status == models.GameStatus.completed:
        raise HTTPException(status_code=400, detail="Game is already completed")

    # Preserve selections from /overs/start or earlier calls
    active_bowler_id = getattr(g, "current_bowler_id", None)
    mid_over_change_used = getattr(g, "mid_over_change_used", False)

    # Rebuild from authoritative ledger
    _gh("_rebuild_scorecards_from_deliveries", g)
    _gh("_recompute_totals_and_runtime", g)

    # Mid-over bowler change (fallback)
    if int(getattr(g, "balls_this_over", 0)) > 0:
        cur = getattr(g, "current_bowler_id", None)
        incoming = str(delivery.bowler_id)
        if cur and incoming and incoming != cur:
            if getattr(g, "mid_over_change_used", False):
                raise HTTPException(
                    status_code=409, detail="Mid-over change already used this over"
                )

            bowling_team_name = getattr(g, "bowling_team_name", None)
            team_a = cast(dict[str, Any], g.team_a)
            team_b = cast(dict[str, Any], g.team_b)
            bowling_team = team_a if team_a["name"] == bowling_team_name else team_b
            players_list: list[Mapping[str, Any]] = list(bowling_team.get("players", []) or [])
            allowed: set[str] = set()
            for p in players_list:
                try:
                    pid_val = p.get("id")
                    allowed.add(str(pid_val))
                except Exception:
                    continue  # nosec
            if incoming not in allowed:
                raise HTTPException(status_code=409, detail="Bowler is not in the bowling team")

            g.current_bowler_id = incoming
            g.mid_over_change_used = True

    # Start-of-over handling
    if active_bowler_id and int(getattr(g, "balls_this_over", 0)) == 0:
        g.current_bowler_id = active_bowler_id
        g.mid_over_change_used = mid_over_change_used
    if not delivery.bowler_id and delivery.bowler_name:
        resolved = cast(str | None, _gh("_id_by_name", g.team_a, g.team_b, delivery.bowler_name))
        if not resolved:
            raise HTTPException(status_code=404, detail="Unknown bowler name")
        delivery.bowler_id = resolved

    if int(getattr(g, "balls_this_over", 0)) == 0 and not getattr(g, "current_bowler_id", None):
        g.current_bowler_id = delivery.bowler_id
        g.mid_over_change_used = False

    # Fill fielder/dismissed by name if needed
    needs_fielder = bool(
        delivery.is_wicket
        and str(getattr(delivery, "dismissal_type", "")).lower() in {"caught", "run_out", "stumped"}
    )
    if needs_fielder and not delivery.fielder_id and delivery.fielder_name:
        resolved = cast(str | None, _gh("_id_by_name", g.team_a, g.team_b, delivery.fielder_name))
        if not resolved:
            raise HTTPException(status_code=404, detail="Unknown fielder name")
        delivery.fielder_id = resolved
    if bool(delivery.is_wicket) and not getattr(delivery, "dismissed_player_id", None):
        dpn = getattr(delivery, "dismissed_player_name", None)
        if dpn:
            resolved = cast(str | None, _gh("_id_by_name", g.team_a, g.team_b, dpn))
            if not resolved:
                raise HTTPException(status_code=404, detail="Unknown dismissed player name")
            delivery.dismissed_player_id = resolved

    # Comprehensive validation
    validation_helpers.validate_delivery_players(
        striker_id=delivery.striker_id,
        non_striker_id=delivery.non_striker_id,
        bowler_id=delivery.bowler_id or getattr(g, "current_bowler_id", None),
        team_a=g.team_a,
        team_b=g.team_b,
        batting_team_name=g.batting_team_name,
        bowling_team_name=g.bowling_team_name,
        is_wicket=delivery.is_wicket or False,
        dismissal_type=getattr(delivery, "dismissal_type", None),
    )

    # UI gating flags & guards
    flags = cast(dict[str, Any], _gh("_compute_snapshot_flags", g) or {})
    if getattr(g, "current_bowler_id", None) and int(getattr(g, "balls_this_over", 0)) == 0:
        flags["needs_new_over"] = False
    if flags.get("needs_new_batter"):
        raise HTTPException(
            status_code=409, detail="Select a new batter before scoring the next ball."
        )
    if flags.get("needs_new_over"):
        msg = (
            "Start a new over and select a bowler before scoring. "
            f"(debug bto={g.balls_this_over}, "
            f"cbi={g.current_bowler_id}, "
            f"lbi={getattr(g, 'last_ball_bowler_id', None)})"
        )
        raise HTTPException(status_code=409, detail=msg)

    # No consecutive overs by same bowler when a new over starts
    last_id = getattr(g, "last_ball_bowler_id", None)
    eff_bowler = getattr(g, "current_bowler_id", None) or delivery.bowler_id
    if int(getattr(g, "balls_this_over", 0)) == 0 and last_id and eff_bowler == last_id:
        raise HTTPException(status_code=400, detail="Bowler cannot bowl consecutive overs")

    # Normalize delivery + score one ball
    x = _gh("_norm_extra", delivery.extra)

    # Autofill batters from runtime to avoid requiring them every ball
    if not getattr(delivery, "striker_id", None):
        if getattr(g, "current_striker_id", None):
            delivery.striker_id = g.current_striker_id  # type: ignore[assignment]
        else:
            raise HTTPException(
                status_code=409, detail="Select openers before scoring the first ball."
            )
    if not getattr(delivery, "non_striker_id", None):
        if getattr(g, "current_non_striker_id", None):
            delivery.non_striker_id = g.current_non_striker_id  # type: ignore[assignment]
        else:
            raise HTTPException(
                status_code=409, detail="Select openers before scoring the first ball."
            )
    if not delivery.striker_id:
        raise HTTPException(status_code=409, detail="Select openers before scoring the first ball.")
    if not delivery.non_striker_id:
        raise HTTPException(status_code=409, detail="Select openers before scoring the first ball.")

    effective_bowler_id: str | None = (
        cast(str | None, getattr(g, "current_bowler_id", None)) or delivery.bowler_id
    )
    if not effective_bowler_id:
        raise HTTPException(
            status_code=409,
            detail="Select a bowler before scoring the first ball of the over.",
        )

    striker_id_n: str = delivery.striker_id
    non_striker_id_n: str = delivery.non_striker_id
    bowler_id_n: str = effective_bowler_id

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
            extra=x,
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

    # Append to ledger once
    del_dict: dict[str, Any] = schemas.Delivery(**kwargs).model_dump()
    del_dict["inning"] = int(getattr(g, "current_inning", 1) or 1)
    try:
        del_dict["shot_angle_deg"] = getattr(delivery, "shot_angle_deg", None)
    except Exception:
        del_dict["shot_angle_deg"] = None  # nosec
    try:
        shot_map_val = getattr(delivery, "shot_map", None)
        del_dict["shot_map"] = str(shot_map_val) if shot_map_val is not None else None
    except Exception:
        del_dict["shot_map"] = None  # nosec

    updated = await _games_impl.append_delivery_and_persist_impl(
        db_game,
        delivery_dict=del_dict,
        db=db,
    )
    u = updated

    # Recompute derived runtime, finalize, and persist if changed
    _gh("_rebuild_scorecards_from_deliveries", u)
    _gh("_recompute_totals_and_runtime", u)
    await _maybe_close_innings(u)
    _gh("_ensure_target_if_chasing", u)
    _gh("_maybe_finalize_match", u)
    await crud.update_game(db, game_model=u)

    # Build snapshot + final flags
    last = u.deliveries[-1] if u.deliveries else None
    snap = _snapshot_from_game(u, last, BASE_DIR)
    is_break = str(getattr(u, "status", "")) == "innings_break" or bool(
        getattr(u, "needs_new_innings", False)
    )
    if is_break:
        snap["needs_new_over"] = False
        snap["needs_new_innings"] = True

    cur_bowler_from_obj: str | None = None
    cb_any = snap.get("current_bowler")
    if isinstance(cb_any, dict):
        cb_map_typed = cast(dict[str, Any], cb_any)
        cur_bowler_from_obj = None
        raw = cb_map_typed.get("id", None)
        if isinstance(raw, str):
            cur_bowler_from_obj = raw
        elif raw is not None:
            try:
                cur_bowler_from_obj = str(raw)
            except Exception:
                cur_bowler_from_obj = None  # nosec

    snap["current_bowler_id"] = cast(
        str | None,
        snap.get("current_bowler_id")
        or cur_bowler_from_obj
        or getattr(u, "current_bowler_id", None),
    )
    snap["last_ball_bowler_id"] = cast(
        str | None,
        snap.get("last_ball_bowler_id") or getattr(u, "last_ball_bowler_id", None),
    )

    # Emit via global sio from backend.main (lazy import to avoid circulars)
    from backend.services.live_bus import emit_prediction_update, emit_state_update
    from backend.services.prediction_service import get_win_probability

    await emit_state_update(game_id, snap)

    # Calculate and emit win probability prediction
    try:
        game_state_for_prediction = {
            "current_inning": u.current_inning,
            "total_runs": u.total_runs,
            "total_wickets": u.total_wickets,
            "overs_completed": u.overs_completed,
            "balls_this_over": u.balls_this_over,
            "overs_limit": u.overs_limit,
            "target": u.target,
            "match_type": u.match_type,
        }
        prediction = get_win_probability(game_state_for_prediction)
        prediction["batting_team"] = u.batting_team_name
        prediction["bowling_team"] = u.bowling_team_name
        await emit_prediction_update(game_id, prediction)
    except Exception as e:
        # Don't break scoring if prediction fails, but log for debugging
        import logging

        logging.warning(f"Prediction calculation failed for game {game_id}: {e}")

    return snap


@router.post("/{game_id}/undo-last")
async def undo_last_delivery(
    game_id: str, db: Annotated[AsyncSession, Depends(get_db)]
) -> dict[str, Any]:
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g: Any = db_game

    if not g.deliveries:
        raise HTTPException(status_code=409, detail="Nothing to undo")

    g.deliveries = g.deliveries[:-1]  # type: ignore[assignment]

    # Reset and replay ledger
    def _reset_runtime_and_scorecards(game: Any) -> None:
        game.total_runs = 0
        game.total_wickets = 0
        game.overs_completed = 0
        game.balls_this_over = 0
        game.current_striker_id = None
        game.current_non_striker_id = None
        batting_team = game.team_a if game.batting_team_name == game.team_a["name"] else game.team_b
        bowling_team = game.team_b if batting_team is game.team_a else game.team_a
        game.batting_scorecard = _gh("_mk_batting_scorecard", batting_team)
        game.bowling_scorecard = _gh("_mk_bowling_scorecard", bowling_team)

    _reset_runtime_and_scorecards(g)

    deliveries_seq: Sequence[Mapping[str, Any]] = cast(Sequence[Mapping[str, Any]], g.deliveries)
    for d in deliveries_seq:
        x = _gh("_norm_extra", d.get("extra_type"))
        if x == "nb":
            rs = int(d.get("runs_off_bat") or 0)
        elif x in ("wd", "b", "lb"):
            rs = int(d.get("extra_runs") or 0)
        else:
            rs = int(d.get("runs_off_bat") or 0)

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

    updated = await crud.update_game(db, game_model=db_game)
    u = updated
    _gh("_rebuild_scorecards_from_deliveries", u)
    last = u.deliveries[-1] if u.deliveries else None
    snapshot = _snapshot_from_game(u, last, BASE_DIR)

    from backend.services.live_bus import emit_state_update

    await emit_state_update(game_id, snapshot)

    return snapshot
