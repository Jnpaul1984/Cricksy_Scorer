"""Authenticated staff-only favorites for already-public entities."""

from __future__ import annotations

from typing import Annotated

from backend.api.schemas.public_favorites import PublicFavoriteList, PublicFavoritePut, PublicFavoriteRead
from backend.security import get_current_active_user
from backend.services import public_favorite_service
from backend.sql_app.database import get_db
from backend.sql_app.models import PublicEntityFavorite, User
from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/me/public-favorites", tags=["public-favorites"])


async def _staff(db: AsyncSession, user: User) -> None:
    try:
        await public_favorite_service.require_active_staff(db, user_id=user.id)
    except PermissionError as exc:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Active staff membership required") from exc


def _read(row: PublicEntityFavorite, subject: public_favorite_service.ResolvedPublicSubject) -> PublicFavoriteRead:
    return PublicFavoriteRead(id=row.id, subject_kind=row.subject_kind, public_key=subject.public_key,
                              display_name=subject.display_name, canonical_path=subject.canonical_path,
                              created_at=row.created_at)


@router.put("", response_model=PublicFavoriteRead)
async def put_public_favorite(payload: PublicFavoritePut, current_user: Annotated[User, Depends(get_current_active_user)], db: Annotated[AsyncSession, Depends(get_db)]) -> PublicFavoriteRead:
    await _staff(db, current_user)
    subject = await public_favorite_service.resolve_public_subject(db, kind=payload.subject_kind, public_key=payload.subject_public_key)
    if subject is None:
        raise HTTPException(status_code=404, detail="Public page not found")
    favorite = await db.scalar(select(PublicEntityFavorite).where(
        PublicEntityFavorite.user_id == current_user.id, PublicEntityFavorite.subject_kind == subject.kind,
        PublicEntityFavorite.subject_public_key == subject.public_key))
    if favorite is None:
        favorite = PublicEntityFavorite(user_id=current_user.id, subject_kind=subject.kind, subject_public_key=subject.public_key)
        db.add(favorite)
        try:
            await db.commit()
        except IntegrityError:
            await db.rollback()
            favorite = await db.scalar(select(PublicEntityFavorite).where(
                PublicEntityFavorite.user_id == current_user.id, PublicEntityFavorite.subject_kind == subject.kind,
                PublicEntityFavorite.subject_public_key == subject.public_key))
            if favorite is None:
                raise
        await db.refresh(favorite)
    return _read(favorite, subject)


@router.get("", response_model=PublicFavoriteList)
async def list_public_favorites(current_user: Annotated[User, Depends(get_current_active_user)], db: Annotated[AsyncSession, Depends(get_db)], limit: int = Query(20, ge=1, le=100), offset: int = Query(0, ge=0)) -> PublicFavoriteList:
    await _staff(db, current_user)
    rows = list((await db.scalars(select(PublicEntityFavorite).where(PublicEntityFavorite.user_id == current_user.id).order_by(PublicEntityFavorite.created_at.desc(), PublicEntityFavorite.id.desc()).offset(offset).limit(limit + 1))).all())
    next_offset = offset + limit if len(rows) > limit else None
    items: list[PublicFavoriteRead] = []
    for favorite in rows[:limit]:
        subject = await public_favorite_service.resolve_public_subject(db, kind=favorite.subject_kind, public_key=favorite.subject_public_key)
        if subject is not None:
            items.append(_read(favorite, subject))
    return PublicFavoriteList(items=items, next_offset=next_offset)


@router.delete("/{favorite_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_public_favorite(favorite_id: str, current_user: Annotated[User, Depends(get_current_active_user)], db: Annotated[AsyncSession, Depends(get_db)]) -> Response:
    await _staff(db, current_user)
    favorite = await db.scalar(select(PublicEntityFavorite).where(PublicEntityFavorite.id == favorite_id, PublicEntityFavorite.user_id == current_user.id))
    if favorite is None:
        raise HTTPException(status_code=404, detail="Favorite not found")
    await db.delete(favorite)
    await db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
