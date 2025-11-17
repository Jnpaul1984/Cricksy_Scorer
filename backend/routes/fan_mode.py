from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import security
from backend.sql_app.database import get_db
from backend.sql_app.models import (
    FanFavorite,
    FanFavoriteType,
    Game,
    PlayerProfile,
    User,
)
from backend.sql_app.schemas import (
    FanFavoriteCreate,
    FanFavoriteRead,
    FanMatchCreate,
    FanMatchRead,
)

router = APIRouter(prefix="/api/fan", tags=["Fan Mode"])


def _team_name(team_data: Any) -> str:
    if isinstance(team_data, dict):
        name = team_data.get("name")
        if isinstance(name, str):
            return name
    return ""


def _match_to_read(game: Game) -> FanMatchRead:
    return FanMatchRead(
        id=game.id,
        home_team_name=_team_name(game.team_a),
        away_team_name=_team_name(game.team_b),
        match_type=game.match_type,
        overs_limit=game.overs_limit,
        is_fan_match=game.is_fan_match,
    )


@router.post("/matches", response_model=FanMatchRead)
async def create_fan_match(
    match_data: FanMatchCreate,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> FanMatchRead:
    game = Game(
        team_a={"name": match_data.home_team_name, "players": []},
        team_b={"name": match_data.away_team_name, "players": []},
        match_type=match_data.match_type,
        overs_limit=match_data.overs_limit,
        created_by_user_id=current_user.id,
        is_fan_match=True,
    )
    db.add(game)
    await db.commit()
    await db.refresh(game)
    return _match_to_read(game)


@router.get("/matches", response_model=list[FanMatchRead])
async def list_fan_matches(
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
) -> list[FanMatchRead]:
    stmt = (
        select(Game)
        .where(
            Game.is_fan_match.is_(True),
            Game.created_by_user_id == current_user.id,
        )
        .order_by(Game.id)
        .limit(limit)
        .offset(offset)
    )
    result = await db.execute(stmt)
    games = result.scalars().all()
    return [_match_to_read(game) for game in games]


@router.get("/matches/{match_id}", response_model=FanMatchRead)
async def get_fan_match(
    match_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> FanMatchRead:
    stmt = select(Game).where(
        Game.id == match_id,
        Game.is_fan_match.is_(True),
        Game.created_by_user_id == current_user.id,
    )
    result = await db.execute(stmt)
    game = result.scalar_one_or_none()
    if game is None:
        raise HTTPException(status_code=404, detail="Fan match not found")
    return _match_to_read(game)


async def _ensure_player_exists(db: AsyncSession, player_id: str) -> None:
    player = await db.get(PlayerProfile, player_id)
    if player is None:
        raise HTTPException(status_code=400, detail="Player profile not found")


async def _favorite_exists(
    db: AsyncSession,
    user_id: str,
    payload: FanFavoriteCreate,
) -> bool:
    stmt = select(FanFavorite).where(FanFavorite.user_id == user_id)
    if payload.favorite_type == FanFavoriteType.player:
        stmt = stmt.where(FanFavorite.player_profile_id == payload.player_profile_id)
    else:
        stmt = stmt.where(FanFavorite.team_id == payload.team_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none() is not None


@router.post("/favorites", response_model=FanFavoriteRead)
async def create_favorite(
    payload: FanFavoriteCreate,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> FanFavoriteRead:
    if payload.favorite_type == FanFavoriteType.player and payload.player_profile_id:
        await _ensure_player_exists(db, payload.player_profile_id)

    if await _favorite_exists(db, current_user.id, payload):
        raise HTTPException(status_code=400, detail="Favorite already exists")

    favorite = FanFavorite(
        user_id=current_user.id,
        favorite_type=payload.favorite_type,
        player_profile_id=payload.player_profile_id,
        team_id=payload.team_id,
    )
    db.add(favorite)
    await db.commit()
    await db.refresh(favorite)
    player_name = None
    if favorite.player_profile_id:
        player = await db.get(PlayerProfile, favorite.player_profile_id)
        player_name = player.player_name if player else None
    return FanFavoriteRead(
        id=favorite.id,
        favorite_type=favorite.favorite_type,
        player_profile_id=favorite.player_profile_id,
        team_id=favorite.team_id,
        created_at=favorite.created_at,
        player_name=player_name,
        team_name=favorite.team_id if favorite.favorite_type == FanFavoriteType.team else None,
    )


@router.get("/favorites", response_model=list[FanFavoriteRead])
async def list_favorites(
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> list[FanFavoriteRead]:
    stmt = (
        select(FanFavorite, PlayerProfile.player_name)
        .outerjoin(
            PlayerProfile,
            FanFavorite.player_profile_id == PlayerProfile.player_id,
        )
        .where(FanFavorite.user_id == current_user.id)
        .order_by(FanFavorite.created_at.desc())
    )
    result = await db.execute(stmt)
    favorites: list[FanFavoriteRead] = []
    for favorite, player_name in result.all():
        favorites.append(
            FanFavoriteRead(
                id=favorite.id,
                favorite_type=favorite.favorite_type,
                player_profile_id=favorite.player_profile_id,
                team_id=favorite.team_id,
                created_at=favorite.created_at,
                player_name=player_name,
                team_name=(
                    favorite.team_id if favorite.favorite_type == FanFavoriteType.team else None
                ),
            )
        )
    return favorites


@router.delete("/favorites/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_favorite(
    favorite_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> Response:
    favorite = await db.get(FanFavorite, favorite_id)
    if favorite is None or favorite.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Favorite not found")
    await db.delete(favorite)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
