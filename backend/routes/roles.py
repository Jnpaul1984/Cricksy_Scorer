# backend/routes/roles.py
from __future__ import annotations

from typing import Any, AsyncGenerator, Dict, List, Optional, cast

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import delete, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from backend.sql_app import models, schemas
from backend.sql_app.database import SessionLocal  # Async sessionmaker

router = APIRouter(prefix="/games", tags=["roles"])

# ----------------------------------------------------
# DB dependency (async) â€” annotate as AsyncGenerator
# ----------------------------------------------------
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with SessionLocal() as session:  # type: ignore[misc]
        yield session

# ----------------------------------------------------
# Helpers
# ----------------------------------------------------
def _players_on_side(game: models.Game, side: schemas.TeamSide) -> List[Dict[str, Any]]:
    team = game.team_a if side == schemas.TeamSide.A else game.team_b
    team = team or {}
    return cast(List[Dict[str, Any]], team.get("players", []) or [])

def _ensure_player_on_team(player_id: Optional[str], team_players: List[Dict[str, Any]]) -> bool:
    if not player_id:
        return True
    return any(p.get("id") == player_id for p in team_players)

# ----------------------------------------------------
# Team roles (captain / wicket-keeper)
# ----------------------------------------------------
@router.post("/{game_id}/team-roles")
async def set_team_roles(
    game_id: str,
    payload: schemas.TeamRoleUpdate,
    db: AsyncSession = Depends(get_db),
):
    res = await db.execute(select(models.Game).where(models.Game.id == game_id))
    game = res.scalar_one_or_none()
    if not game:
        raise HTTPException(status_code=404, detail="Game not found")

    players = _players_on_side(game, payload.side)
    if payload.captain_id and not _ensure_player_on_team(payload.captain_id, players):
        raise HTTPException(status_code=400, detail="captain_id not in team players")
    if payload.wicket_keeper_id and not _ensure_player_on_team(payload.wicket_keeper_id, players):
        raise HTTPException(status_code=400, detail="wicket_keeper_id not in team players")

    # Cast to Any so Pylance doesn't treat attributes as Column[...]
    g = cast(Any, game)
    if payload.side == schemas.TeamSide.A:
        g.team_a_captain_id = payload.captain_id
        g.team_a_keeper_id = payload.wicket_keeper_id
    else:
        g.team_b_captain_id = payload.captain_id
        g.team_b_keeper_id = payload.wicket_keeper_id

    db.add(game)
    await db.commit()
    await db.refresh(game)

    return {
        "ok": True,
        "team_roles": {
            "A": {"captain_id": cast(Optional[str], g.team_a_captain_id), "wicket_keeper_id": cast(Optional[str], g.team_a_keeper_id)},
            "B": {"captain_id": cast(Optional[str], g.team_b_captain_id), "wicket_keeper_id": cast(Optional[str], g.team_b_keeper_id)},
        },
    }

# ----------------------------------------------------
# Game contributors (scorer / commentary / analytics)
# ----------------------------------------------------
@router.post("/{game_id}/contributors", response_model=schemas.GameContributor)
async def add_contributor(
    game_id: str,
    body: schemas.GameContributorIn,
    db: AsyncSession = Depends(get_db),
):
    # Ensure game exists
    res = await db.execute(select(models.Game).where(models.Game.id == game_id))
    if res.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Game not found")

    role_value = body.role.value if hasattr(body.role, "value") else str(body.role)
    try:
        rec = models.GameContributor(
            game_id=game_id,
            user_id=body.user_id,
            role=models.GameContributorRoleEnum(role_value),
            display_name=body.display_name,
        )
        db.add(rec)
        await db.commit()
        await db.refresh(rec)
    except IntegrityError:
        await db.rollback()
        stmt = (
            update(models.GameContributor)
            .where(
                models.GameContributor.game_id == game_id,
                models.GameContributor.user_id == body.user_id,
                models.GameContributor.role == models.GameContributorRoleEnum(role_value),
            )
            .values(display_name=body.display_name)
            .returning(models.GameContributor)
        )
        res2 = await db.execute(stmt)
        rec = res2.scalar_one()
        await db.commit()

    return schemas.GameContributor(
        id=cast(int, rec.id),
        game_id=cast(str, rec.game_id),
        user_id=cast(str, rec.user_id),
        role=schemas.GameContributorRole(cast(str, rec.role.value if hasattr(rec.role, "value") else rec.role)),
        display_name=cast(Optional[str], rec.display_name),
    )

@router.get("/{game_id}/contributors", response_model=List[schemas.GameContributor])
async def list_contributors(game_id: str, db: AsyncSession = Depends(get_db)):
    res = await db.execute(select(models.GameContributor).where(models.GameContributor.game_id == game_id))
    rows = res.scalars().all()
    return [
        schemas.GameContributor(
            id=cast(int, r.id),
            game_id=cast(str, r.game_id),
            user_id=cast(str, r.user_id),
            role=schemas.GameContributorRole(cast(str, r.role.value if hasattr(r.role, "value") else r.role)),
            display_name=cast(Optional[str], r.display_name),
        )
        for r in rows
    ]

@router.delete("/{game_id}/contributors/{contrib_id}")
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



