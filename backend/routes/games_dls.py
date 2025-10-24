# routers/games_dls.py
from __future__ import annotations

from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel, Field
from typing import Annotated, Literal, Any
from sqlalchemy.orm import Session
from backend.sql_app import models
from backend.sql_app.database import get_db
from backend.services.dls_service import resource_remaining, calc_target

# Optional live-bus broadcast (safe no-op if you don't have it yet)
try:
    from services.live_bus import publish_game_update  # type: ignore # your WS/SSE hub
except Exception:  # pragma: no cover
    def publish_game_update(game_id: str, payload: dict[str, Any]) -> None:
        # No-op fallback: comment this out when you wire your bus.
        return None

router = APIRouter(prefix="/games", tags=["games:dls"])

# ---------- I/O Schemas ----------

class DLSPreviewOut(BaseModel):
    team1_score: int
    team1_resources: float
    team2_resources: float
    target: int
    format_overs: Literal[20, 50]
    G50: int

class DLSApplyOut(DLSPreviewOut):
    applied: bool

class ReduceOversIn(BaseModel):
    innings: Literal[1, 2] = 2
    new_overs: int = Field(gt=0, le=50)

class ReduceOversOut(BaseModel):
    innings: int
    new_overs: int
    new_balls_limit: int

# ---------- Helpers (adapt field names to your schema if different) ----------

def _infer_format_overs(g: models.Game) -> Literal[20, 50]:
    """
    Decide whether the match uses 20 or 50 overs (standard DLS tables).
    Priority: explicit innings limit â†’ match_overs â†’ default 50.
    """
    limit = getattr(g, "i1_overs_limit", None) or getattr(g, "match_overs", None) or 50
    return 20 if int(limit) <= 20 else 50  # type: ignore[return-value]

def _current_team2_state(g: models.Game) -> tuple[int, int]:
    """Return (balls_left, wickets_lost) for Team 2 right now."""
    i2_overs_limit = getattr(g, "i2_overs_limit", None) or 50
    i2_balls_limit = getattr(g, "i2_balls_limit", None) or int(i2_overs_limit) * 6
    balls_bowled = int(getattr(g, "i2_balls_bowled", 0) or 0)
    balls_left = max(0, int(i2_balls_limit) - balls_bowled)
    wickets_lost = int(getattr(g, "i2_wickets", 0) or 0)
    return balls_left, wickets_lost

def _team1_resources_completed(g: models.Game, fmt: Literal[20, 50]) -> float:
    """
    Standard Edition: usually 100 if Team 1 completed without interruptions.
    If you track interruptions/resources used for Team 1, use that stored value.
    """
    stored = getattr(g, "i1_resources_used", None)
    return float(stored) if stored is not None else 100.0

# ---------- Routes ----------

@router.get("/{game_id}/dls/preview", response_model=DLSPreviewOut)
def dls_preview(game_id: str, G50: int = 245, db: Session = Depends(get_db)) -> DLSPreviewOut:
    g: models.Game | None = (
        db.query(models.Game).filter(models.Game.id == game_id).first()
    )
    if not g:
        raise HTTPException(404, "Game not found")
    if not getattr(g, "innings1_completed", False):
        raise HTTPException(400, "DLS target requires Team 1 innings completed")

    fmt = _infer_format_overs(g)
    team1_score = int(getattr(g, "i1_runs", 0) or 0)
    team1_res = _team1_resources_completed(g, fmt)

    balls_left, wkts_lost = _current_team2_state(g)
    team2_res = resource_remaining(fmt, balls_left=balls_left, wickets_lost=wkts_lost)
    target = calc_target(team1_score, team1_res, team2_res, G50)

    return DLSPreviewOut(
        team1_score=team1_score,
        team1_resources=team1_res,
        team2_resources=team2_res,
        target=target,
        format_overs=fmt,
        G50=G50,
    )

@router.post("/{game_id}/dls/apply", response_model=DLSApplyOut)
def dls_apply(game_id: str, G50: int = 245, db: Session = Depends(get_db)) -> DLSApplyOut:
    # Lock row so two scorers can't apply at the same time
    g: models.Game | None = (
        db.query(models.Game)
        .filter(models.Game.id == game_id)
        .with_for_update()
        .first()
    )
    if not g:
        raise HTTPException(404, "Game not found")
    if not getattr(g, "innings1_completed", False):
        raise HTTPException(400, "DLS target requires Team 1 innings completed")

    fmt = _infer_format_overs(g)
    team1_score = int(getattr(g, "i1_runs", 0) or 0)
    team1_res = _team1_resources_completed(g, fmt)

    balls_left, wkts_lost = _current_team2_state(g)
    team2_res = resource_remaining(fmt, balls_left=balls_left, wickets_lost=wkts_lost)
    target = calc_target(team1_score, team1_res, team2_res, G50)

    # Persist to DB (adjust to your actual column names)
    setattr(g, "dls_applied", True)
    setattr(g, "dls_format", int(fmt))
    setattr(g, "dls_g50", int(G50))
    setattr(g, "target_revised", int(target))
    setattr(g, "team2_resources", float(team2_res))

    db.add(g)
    db.commit()

    # Notify connected clients (scoreboard, scorer UI, etc.)
    publish_game_update(
        game_id,
        {
            "type": "dls_applied",
            "target": target,
            "team2_resources": team2_res,
            "g50": G50,
            "format": fmt,
        },
    )

    return DLSApplyOut(
        team1_score=team1_score,
        team1_resources=team1_res,
        team2_resources=team2_res,
        target=target,
        format_overs=fmt,
        G50=G50,
        applied=True,
    )

@router.patch("/{game_id}/overs/reduce", response_model=ReduceOversOut)
def reduce_overs(game_id: str, body: ReduceOversIn, db: Session = Depends(get_db)) -> ReduceOversOut:
    g: models.Game | None = (
        db.query(models.Game).filter(models.Game.id == game_id).first()
    )
    if not g:
        raise HTTPException(404, "Game not found")

    # Business rules are up to you; these are soft examples:
    if body.innings == 1 and getattr(g, "innings1_completed", False):
        raise HTTPException(400, "Cannot reduce overs after Team 1 completed")
    if body.innings == 2 and getattr(g, "innings2_completed", False):
        raise HTTPException(400, "Cannot reduce overs after Team 2 completed")

    balls_limit = int(body.new_overs) * 6
    if body.innings == 1:
        setattr(g, "i1_overs_limit", int(body.new_overs))
        setattr(g, "i1_balls_limit", balls_limit)
    else:
        setattr(g, "i2_overs_limit", int(body.new_overs))
        setattr(g, "i2_balls_limit", balls_limit)

    db.add(g)
    db.commit()

    publish_game_update(
        game_id,
        {"type": "overs_reduced", "innings": int(body.innings), "new_balls_limit": balls_limit},
    )

    return ReduceOversOut(
        innings=int(body.innings),
        new_overs=int(body.new_overs),
        new_balls_limit=int(balls_limit),
    )



