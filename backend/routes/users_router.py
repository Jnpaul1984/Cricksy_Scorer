from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend import security
from backend.sql_app import models, schemas
from backend.sql_app.database import get_db

router = APIRouter(prefix="/users", tags=["users"])


@router.post("/{user_id}/role", response_model=schemas.UserRead)
async def update_user_role(
    user_id: str,
    payload: schemas.UserRoleUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[models.User, Depends(security.get_current_active_user)],
) -> schemas.UserRead:
    if not current_user.is_superuser:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not enough permissions")

    user = await db.get(models.User, user_id)
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    user.role = payload.role
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # Explicitly construct UserRead to handle potential None values in mock DB
    return schemas.UserRead(
        id=str(getattr(user, "id", "")),
        email=getattr(user, "email", ""),
        is_active=bool(getattr(user, "is_active", False)),
        is_superuser=bool(getattr(user, "is_superuser", False)),
        role=user.role,
    )
