from __future__ import annotations

from pathlib import Path
from typing import Annotated, Any, List, Literal, Mapping, Optional, cast

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from backend import dls as dlsmod
from backend.sql_app import crud
from backend.sql_app.database import get_db

router = APIRouter(prefix="/games", tags=["games:dls"])

BASE_DIR = Path(__file__).resolve().parent


class DLSRequest(BaseModel):
    kind: Literal["odi", "t20"] = "odi"
    innings: Literal[1, 2] = 2
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


def _team1_runs(g: Any) -> int:
    fis_any: Any = getattr(g, "first_inning_summary", None)
    if isinstance(fis_any, dict) and "runs" in fis_any:
        try:
            return int(cast(Any, fis_any["runs"]))
        except Exception:
            pass
    # Fallback: sum from ledger for innings 1
    total = 0
    for d_any in getattr(g, "deliveries", []) or []:
        d = d_any.model_dump() if hasattr(d_any, "model_dump") else dict(d_any)
        if int(d.get("inning", 1) or 1) != 1:
            continue
        total += int(d.get("runs_scored") or 0)
    return total


@router.post("/{game_id}/dls/revised-target", response_model=DLSRevisedOut)
async def dls_revised_target(
    game_id: str, body: DLSRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    game = await crud.get_game(db, game_id=game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    g = cast(Any, game)
    env = dlsmod.load_env(body.kind, str(BASE_DIR))

    deliveries_m: List[Mapping[str, Any]] = cast(
        List[Mapping[str, Any]], list(getattr(g, "deliveries", []))
    )
    M1 = int(body.max_overs or (g.overs_limit or (50 if body.kind == "odi" else 20)))
    interruptions = list(getattr(g, "interruptions", []))
    R1_total = dlsmod.total_resources_team1(
        env=env,
        max_overs_initial=M1,
        deliveries=deliveries_m,
        interruptions=interruptions,
    )

    S1 = _team1_runs(g)
    M2 = int(body.max_overs or (g.overs_limit or (50 if body.kind == "odi" else 20)))
    R2_total = env.table.R(M2, 0)

    target = dlsmod.revised_target(S1=S1, R1_total=R1_total, R2_total=R2_total)
    return DLSRevisedOut(R1_total=R1_total, R2_total=R2_total, S1=S1, target=target)


@router.post("/{game_id}/dls/par", response_model=DLSParOut)
async def dls_par_now(
    game_id: str, body: DLSRequest, db: Annotated[AsyncSession, Depends(get_db)]
):
    game = await crud.get_game(db, game_id=game_id)
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")
    g = cast(Any, game)
    env = dlsmod.load_env(body.kind, str(BASE_DIR))

    deliveries_m: List[Mapping[str, Any]] = cast(
        List[Mapping[str, Any]], list(getattr(g, "deliveries", []))
    )
    M = int(body.max_overs or (g.overs_limit or (50 if body.kind == "odi" else 20)))

    R1_total = dlsmod.total_resources_team1(
        env=env,
        max_overs_initial=M,
        deliveries=deliveries_m,
        interruptions=list(getattr(g, "interruptions", [])),
    )
    S1 = _team1_runs(g)

    balls_so_far = int(getattr(g, "overs_completed", 0)) * 6 + int(
        getattr(g, "balls_this_over", 0)
    )
    wkts_so_far = int(getattr(g, "total_wickets", 0))

    R_start = env.table.R(M, 0)
    R_remaining = env.table.R(max(0.0, M - (balls_so_far / 6.0)), wkts_so_far)
    R2_used = max(0.0, R_start - R_remaining)

    par = dlsmod.par_score_now(S1=S1, R1_total=R1_total, R2_used_so_far=R2_used)
    runs_now = int(getattr(g, "total_runs", 0))
    return DLSParOut(
        R1_total=R1_total, R2_used=R2_used, S1=S1, par=par, ahead_by=runs_now - par
    )
