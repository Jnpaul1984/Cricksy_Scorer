from __future__ import annotations

from typing import Any, Dict, Optional, Mapping, List, Sequence, cast
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.sql_app import crud, schemas, models
from backend.sql_app.database import SessionLocal as _SessionLocal  # async SessionLocal for DI
from backend.services.snapshot_service import build_snapshot as _snapshot_from_game
from backend.services import game_helpers as gh
from backend.services.scoring_service import score_one as _score_one
from backend.services import validation as validation_helpers
from backend.routes import games as _games_impl
from backend import dls as dlsmod

router = APIRouter(prefix="/games", tags=["gameplay"])

# Local DB dependency mirroring main.get_db
async def get_db() -> Any:
    async with _SessionLocal() as session:  # type: ignore[misc]
        yield session

BASE_DIR = Path(__file__).resolve().parent


def _model_to_dict(x: Any) -> Optional[Dict[str, Any]]:
    # Minimal copy of main._model_to_dict for this router
    try:
        from pydantic import BaseModel  # local import to avoid circulars at import time
    except Exception:
        BaseModel = object  # type: ignore[assignment]

    if isinstance(x, dict):
        return {str(k): v for k, v in x.items()}

    if isinstance(x, BaseModel):  # type: ignore[arg-type]
        try:
            md = x.model_dump()  # pydantic v2
            return {str(k): v for k, v in md.items()}  # type: ignore[union-attr]
        except Exception:
            try:
                md = x.dict()  # type: ignore[attr-defined]
                return {str(k): v for k, v in md.items()}
            except Exception:
                return None

    for attr in ("model_dump", "dict"):
        fn = getattr(x, attr, None)
        if callable(fn):
            try:
                data = fn()
                if isinstance(data, dict):
                    return {str(k): v for k, v in data.items()}
            except Exception:
                return None

    return None


# Local helper: close innings if all out or overs exhausted (ported from main.py)
async def _maybe_close_innings(g: Any) -> None:
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

        # Only archive if not already archived
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
                "overs": gh._overs_string_from_ledger(g),
                "batting_scorecard": g.batting_scorecard,
                "bowling_scorecard": g.bowling_scorecard,
                "deliveries": g.deliveries,
                "closed_at": datetime.now(timezone.utc).isoformat(),
            })

        g.status = models.GameStatus.innings_break
        g.needs_new_innings = True
        g.needs_new_over = False
        g.needs_new_batter = False
        g.current_striker_id = None
        g.current_non_striker_id = None
        g.current_bowler_id = None


@router.get("/{game_id}/snapshot")
async def get_snapshot(game_id: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
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
    gh._rebuild_scorecards_from_deliveries(g)
    gh._recompute_totals_and_runtime(g)

    dl = gh._dedup_deliveries(g)
    last = dl[-1] if dl else None
    snap = _snapshot_from_game(g, last, BASE_DIR)

    # UI gating flags
    flags = gh._compute_snapshot_flags(g)
    is_break = str(getattr(g, "status", "")).lower() == "innings_break" or bool(
        getattr(g, "needs_new_innings", False)
    )
    snap["needs_new_batter"] = flags["needs_new_batter"]
    snap["needs_new_over"] = False if is_break else flags["needs_new_over"]
    snap["needs_new_innings"] = is_break

    # Interruption records + mini cards
    snap["interruptions"] = cast(List[Dict[str, Any]], getattr(g, "interruptions", []) or [])
    snap["mini_batting_card"] = gh._mini_batting_card(g)
    snap["mini_bowling_card"] = gh._mini_bowling_card(g)

    # DLS panel best-effort (matches main.py logic)
    try:
        overs_limit_opt = cast(Optional[int], getattr(g, "overs_limit", None))
        current_innings = int(getattr(g, "current_inning", 1) or 1)
        if isinstance(overs_limit_opt, int) and current_innings >= 2 and overs_limit_opt in (20, 50):
            format_overs = int(overs_limit_opt)
            kind = "odi" if format_overs >= 40 else "t20"
            env = dlsmod.load_env(kind, str(BASE_DIR))

            deliveries_m: List[Mapping[str, Any]] = cast(
                List[Mapping[str, Any]], list(getattr(g, "deliveries", []))
            )
            interruptions = list(getattr(g, "interruptions", []))

            R1_total = dlsmod.total_resources_team1(
                env=env,
                max_overs_initial=format_overs,
                deliveries=deliveries_m,
                interruptions=interruptions,
            )
            S1 = 0
            fis_any = getattr(g, "first_inning_summary", None)
            if isinstance(fis_any, dict) and "runs" in fis_any:
                try:
                    S1 = int(fis_any.get("runs", 0))
                except Exception:
                    S1 = 0
            else:
                S1 = sum(
                    int(d.get("runs_scored") or 0)
                    for d in list(getattr(g, "deliveries", []) or [])
                    if int(d.get("inning", 1) or 1) == 1
                )

            overs_completed = float(getattr(g, "overs_completed", 0.0) or 0.0)
            balls_this_over = float(getattr(g, "balls_this_over", 0.0) or 0.0)
            team2_overs_left_now = max(
                0.0, float(format_overs) - (overs_completed + (balls_this_over / 6.0))
            )
            team2_wkts_now = int(getattr(g, "total_wickets", 0)) if current_innings == 2 else 0

            R_start = env.table.R(format_overs, 0)
            R_remaining = env.table.R(team2_overs_left_now, team2_wkts_now)
            R2_used = max(0.0, R_start - R_remaining)

            par_now = int(
                dlsmod.par_score_now(S1=S1, R1_total=R1_total, R2_used_so_far=R2_used)
            )
            target_full = int(dlsmod.revised_target(S1=S1, R1_total=R1_total, R2_total=R_start))

            snap["dls"] = {"method": "DLS", "par": par_now, "target": target_full}
    except Exception:
        # Leave snapshot_service panel if ours fails
        pass

    # Enrich for bootstrap (team names + player lists), matches main.py
    snap["teams"] = {
        "batting": {"name": g.batting_team_name},
        "bowling": {"name": g.bowling_team_name},
    }
    snap["players"] = {
        "batting": [
            {"id": p["id"], "name": p["name"]}
            for p in (
                g.team_a if g.batting_team_name == g.team_a["name"] else g.team_b
            )["players"]
        ],
        "bowling": [
            {"id": p["id"], "name": p["name"]}
            for p in (
                g.team_b if g.batting_team_name == g.team_a["name"] else g.team_a
            )["players"]
        ],
    }
    return snap


@router.get("/{game_id}/recent_deliveries")
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

    g = cast(Any, game)

    # Slice last N from the authoritative ledger, newest-first
    raw_seq: Sequence[Any] = getattr(g, "deliveries", []) or []
    tail: List[Any] = list(raw_seq)[-limit:][::-1]

    # Normalize each item to a dict
    ledger: List[Dict[str, Any]] = []
    for item in tail:
        d = _model_to_dict(item)
        if d is not None:
            ledger.append(d)

    # Validate/shape with Pydantic
    out: List[Dict[str, Any]] = []
    for d_any in ledger:
        try:
            if "extra_type" in d_any:
                x = gh._norm_extra(d_any.get("extra_type"))
                d_any["extra_type"] = x
            model = schemas.Delivery(**cast(Dict[str, Any], d_any))
            out.append(model.model_dump())
        except Exception:
            try:
                model = schemas.Delivery(**d_any)  # type: ignore[call-arg]
                out.append(model.dict())  # type: ignore[attr-defined]
            except Exception:
                continue

    # Enrich with names
    for i, row in enumerate(out):
        row["striker_name"] = gh._player_name(g.team_a, g.team_b, row.get("striker_id"))
        row["non_striker_name"] = gh._player_name(g.team_a, g.team_b, row.get("non_striker_id"))
        row["bowler_name"] = gh._player_name(g.team_a, g.team_b, row.get("bowler_id"))
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
    db: AsyncSession = Depends(get_db),
) -> Dict[str, Any]:
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g: Any = db_game

    # Preserve selections from /overs/start or earlier calls
    active_bowler_id = getattr(g, "current_bowler_id", None)
    mid_over_change_used = getattr(g, "mid_over_change_used", False)

    # Rebuild from authoritative ledger
    gh._rebuild_scorecards_from_deliveries(g)
    gh._recompute_totals_and_runtime(g)

    # Mid-over bowler change (fallback)
    if int(getattr(g, "balls_this_over", 0)) > 0:
        cur = getattr(g, "current_bowler_id", None)
        incoming = str(delivery.bowler_id)
        if cur and incoming and incoming != cur:
            if getattr(g, "mid_over_change_used", False):
                raise HTTPException(status_code=409, detail="Mid-over change already used this over")

            bowling_team_name = getattr(g, "bowling_team_name", None)
            team_a = cast(Dict[str, Any], getattr(g, "team_a"))
            team_b = cast(Dict[str, Any], getattr(g, "team_b"))
            bowling_team = team_a if team_a["name"] == bowling_team_name else team_b
            allowed = {str(p["id"]) for p in (bowling_team.get("players", []) or [])}
            if incoming not in allowed:
                raise HTTPException(status_code=409, detail="Bowler is not in the bowling team")

            g.current_bowler_id = incoming
            g.mid_over_change_used = True

    # Start-of-over handling
    if active_bowler_id and int(getattr(g, "balls_this_over", 0)) == 0:
        g.current_bowler_id = active_bowler_id
        g.mid_over_change_used = mid_over_change_used
    if not delivery.bowler_id and delivery.bowler_name:
        resolved = gh._id_by_name(g.team_a, g.team_b, delivery.bowler_name)
        if not resolved:
            raise HTTPException(status_code=404, detail="Unknown bowler name")
        delivery.bowler_id = resolved

    if int(getattr(g, "balls_this_over", 0)) == 0 and not getattr(g, "current_bowler_id", None):
        g.current_bowler_id = delivery.bowler_id
        g.mid_over_change_used = False

    # Fill fielder/dismissed by name if needed
    needs_fielder = bool(delivery.is_wicket and str(getattr(delivery, "dismissal_type", "")).lower() in {"caught", "run_out", "stumped"})
    if needs_fielder and not delivery.fielder_id and delivery.fielder_name:
        resolved = gh._id_by_name(g.team_a, g.team_b, delivery.fielder_name)
        if not resolved:
            raise HTTPException(status_code=404, detail="Unknown fielder name")
        delivery.fielder_id = resolved
    if bool(delivery.is_wicket) and not getattr(delivery, "dismissed_player_id", None):
        dpn = getattr(delivery, "dismissed_player_name", None)
        if dpn:
            resolved = gh._id_by_name(g.team_a, g.team_b, dpn)
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
        dismissal_type=getattr(delivery, "dismissal_type", None)
    )

    # UI gating flags & guards
    flags = gh._compute_snapshot_flags(g)
    if getattr(g, "current_bowler_id", None) and int(getattr(g, "balls_this_over", 0)) == 0:
        flags["needs_new_over"] = False
    if flags.get("needs_new_batter"):
        raise HTTPException(status_code=409, detail="Select a new batter before scoring the next ball.")
    if flags.get("needs_new_over"):
        msg = (
            f"Start a new over and select a bowler before scoring. "
            f"(debug bto={g.balls_this_over}, cbi={g.current_bowler_id}, lbi={getattr(g,'last_ball_bowler_id',None)})"
        )
        raise HTTPException(status_code=409, detail=msg)

    # No consecutive overs by same bowler when a new over starts
    last_id = getattr(g, "last_ball_bowler_id", None)
    eff_bowler = getattr(g, "current_bowler_id", None) or delivery.bowler_id
    if int(getattr(g, "balls_this_over", 0)) == 0 and last_id and eff_bowler == last_id:
        raise HTTPException(status_code=400, detail="Bowler cannot bowl consecutive overs")

    # Normalize delivery + score one ball
    x = gh._norm_extra(delivery.extra)

    # Autofill batters from runtime to avoid requiring them every ball
    if not getattr(delivery, "striker_id", None):
        if getattr(g, "current_striker_id", None):
            delivery.striker_id = g.current_striker_id  # type: ignore[assignment]
        else:
            raise HTTPException(status_code=409, detail="Select openers before scoring the first ball.")
    if not getattr(delivery, "non_striker_id", None):
        if getattr(g, "current_non_striker_id", None):
            delivery.non_striker_id = g.current_non_striker_id  # type: ignore[assignment]
        else:
            raise HTTPException(status_code=409, detail="Select openers before scoring the first ball.")
    if not delivery.striker_id:
        raise HTTPException(status_code=409, detail="Select openers before scoring the first ball.")
    if not delivery.non_striker_id:
        raise HTTPException(status_code=409, detail="Select openers before scoring the first ball.")

    effective_bowler_id: Optional[str] = (
        cast(Optional[str], getattr(g, "current_bowler_id", None)) or delivery.bowler_id
    )
    if not effective_bowler_id:
        raise HTTPException(status_code=409, detail="Select a bowler before scoring the first ball of the over.")

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
    del_dict: Dict[str, Any] = schemas.Delivery(**kwargs).model_dump()
    del_dict["inning"] = int(getattr(g, "current_inning", 1) or 1)
    try:
        del_dict["shot_angle_deg"] = getattr(delivery, "shot_angle_deg", None)
    except Exception:
        del_dict["shot_angle_deg"] = None
    try:
        shot_map_val = getattr(delivery, "shot_map", None)
        del_dict["shot_map"] = str(shot_map_val) if shot_map_val is not None else None
    except Exception:
        del_dict["shot_map"] = None

    updated = await _games_impl.append_delivery_and_persist_impl(
        db_game,
        delivery_dict=del_dict,
        db=db,
    )
    u = cast(Any, updated)

    # Recompute derived runtime, finalize, and persist if changed
    gh._rebuild_scorecards_from_deliveries(u)
    gh._recompute_totals_and_runtime(u)
    await _maybe_close_innings(u)
    gh._ensure_target_if_chasing(u)
    gh._maybe_finalize_match(u)
    await crud.update_game(db, game_model=cast(Any, u))

    # Build snapshot + final flags
    last = u.deliveries[-1] if u.deliveries else None
    snap = _snapshot_from_game(u, last, BASE_DIR)
    is_break = str(getattr(u, "status", "")) == "innings_break" or bool(getattr(u, "needs_new_innings", False))
    if is_break:
        snap["needs_new_over"] = False
        snap["needs_new_innings"] = True

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

    # Emit via global sio from backend.main (lazy import to avoid circulars)
    try:
        from backend.main import sio  # type: ignore
        await sio.emit("state:update", {"id": game_id, "snapshot": snap}, room=game_id)
    except Exception:
        pass

    return snap


@router.post("/{game_id}/undo-last")
async def undo_last_delivery(game_id: str, db: AsyncSession = Depends(get_db)) -> Dict[str, Any]:
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
        game.batting_scorecard = gh._mk_batting_scorecard(batting_team)
        game.bowling_scorecard = gh._mk_bowling_scorecard(bowling_team)

    _reset_runtime_and_scorecards(g)

    deliveries_seq: Sequence[Mapping[str, Any]] = cast(Sequence[Mapping[str, Any]], g.deliveries)
    for d in deliveries_seq:
        x = gh._norm_extra(d.get("extra_type"))
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
    u = cast(Any, updated)
    gh._rebuild_scorecards_from_deliveries(u)
    last = u.deliveries[-1] if u.deliveries else None
    snapshot = _snapshot_from_game(u, last, BASE_DIR)

    try:
        from backend.main import sio  # type: ignore
        await sio.emit("state:update", {"id": game_id, "snapshot": snapshot}, room=game_id)
    except Exception:
        pass

    return snapshot