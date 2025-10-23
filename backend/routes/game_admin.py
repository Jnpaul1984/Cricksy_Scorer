from __future__ import annotations

from pathlib import Path
from typing import Any, List, Mapping, Optional, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend.sql_app import crud, models, schemas
from backend.sql_app.database import get_db
from backend.services import game_helpers as gh
from backend.services.snapshot_service import build_snapshot as _snapshot_from_game
from backend.services.live_bus import emit_state_update

router = APIRouter(prefix="/games", tags=["game-admin"])

BASE_DIR = Path(__file__).resolve().parent

class OversLimitBody(BaseModel):
    overs_limit: int

@router.post("/{game_id}/overs-limit")
async def set_overs_limit(
    game_id: str,
    body: OversLimitBody,
    db: AsyncSession = Depends(get_db),
):
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g: Any = db_game

    bowled_balls = int(getattr(g, "overs_completed", 0)) * 6 + int(getattr(g, "balls_this_over", 0))
    new_limit_balls = int(body.overs_limit) * 6
    if new_limit_balls < bowled_balls:
        raise HTTPException(status_code=400, detail="New limit is less than overs already bowled")

    g.overs_limit = int(body.overs_limit)

    try:
        interruptions = list(getattr(g, "interruptions", []))
    except Exception:
        interruptions = []
    interruptions.append({
        "type": "overs_reduction",
        "at_delivery_index": len(getattr(g, "deliveries", []) or []),
        "new_overs_limit": int(body.overs_limit),
    })
    g.interruptions = interruptions

    updated = await crud.update_game(db, game_model=db_game)

    u = cast(Any, updated)
    dl = gh._dedup_deliveries(u)
    last = dl[-1] if dl else None
    snap = _snapshot_from_game(u, last, BASE_DIR)
    gh._rebuild_scorecards_from_deliveries(u)
    gh._recompute_totals_and_runtime(u)
    gh._complete_game_by_result(u)
    await crud.update_game(db, game_model=cast(Any, u))
    await emit_state_update(game_id, snap)

    return {"id": game_id, "overs_limit": cast(Any, updated).overs_limit}

@router.post("/{game_id}/team-roles")
async def set_team_roles(
    game_id: str,
    payload: schemas.TeamRoleUpdate,
    db: AsyncSession = Depends(get_db),
):
    db_game = await crud.get_game(db, game_id=game_id)
    if not db_game:
        raise HTTPException(status_code=404, detail="Game not found")

    g: Any = db_game

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

    await crud.update_game(db, game_model=db_game)
    return {
        "ok": True,
        "team_roles": {
            "A": {"captain_id": getattr(g, "team_a_captain_id", None), "wicket_keeper_id": getattr(g, "team_a_keeper_id", None)},
            "B": {"captain_id": getattr(g, "team_b_captain_id", None), "wicket_keeper_id": getattr(g, "team_b_keeper_id", None)},
        },
    }