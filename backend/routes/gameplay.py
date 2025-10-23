from __future__ import annotations

from typing import Any, Dict, Optional, Mapping, List, Sequence, cast
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.sql_app import crud, schemas, models
from backend.sql_app.database import SessionLocal as _SessionLocal  # re-use async SessionLocal in DI
from backend.services.snapshot_service import build_snapshot as _snapshot_from_game
from backend.services import game_helpers as gh
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

    # Validate/shape with Pydantic; help Pylance via a cast to DeliveryKwargs
    out: List[Dict[str, Any]] = []
    for d_any in ledger:
        try:
            # ensure the literal type matches the schema
            if "extra_type" in d_any:
                d_any["extra_type"] = gh._as_extra_code(cast(Optional[str], d_any.get("extra_type")))
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