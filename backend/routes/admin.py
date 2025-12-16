"""Admin-only routes for user management."""

from __future__ import annotations

import secrets
import string
from typing import Annotated

from backend import security
from backend.sql_app import models, schemas
from backend.sql_app.database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _generate_temp_password(length: int = 16) -> str:
    """Generate a secure temporary password with letters and digits."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


async def get_current_superadmin(
    current_user: Annotated[models.User, Depends(security.get_current_active_user)],
) -> models.User:
    """Dependency that ensures the current user is a superuser."""
    if not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Super admin access required",
        )
    return current_user


@router.post("/users", response_model=schemas.BetaUserCreated, name="create_beta_user")
async def create_beta_user(
    payload: schemas.BetaUserCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[models.User, Depends(get_current_superadmin)],
) -> schemas.BetaUserCreated:
    """
    Create a beta user account (super admin only).

    - If password is not provided, generates a secure temporary password.
    - Returns the temporary password in the response (shown only once).
    """
    # Check if user with email already exists
    existing = await security.get_user_by_email(db, payload.email)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"User with email '{payload.email}' already exists",
        )

    # Generate or use provided password
    temp_password = payload.password or _generate_temp_password()

    # Hash the password using the existing security helper
    hashed_password = security.get_password_hash(temp_password)

    # Create the user
    user = models.User(
        email=payload.email,
        hashed_password=hashed_password,
        role=payload.role,
        subscription_plan=payload.plan,
        org_id=payload.org_id,
        beta_tag=payload.beta_tag,
        is_active=True,
        is_superuser=False,
        requires_password_change=True,  # Flag user to change password on first login
    )

    db.add(user)
    await db.commit()
    await db.refresh(user)

    return schemas.BetaUserCreated(
        id=str(user.id),
        email=user.email,
        role=user.role,
        plan=payload.plan,
        org_id=user.org_id,
        beta_tag=user.beta_tag,
        temp_password=temp_password,
    )


@router.get("/users", response_model=list[schemas.BetaUserList], name="list_beta_users")
async def list_beta_users(
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[models.User, Depends(get_current_superadmin)],
) -> list[schemas.BetaUserList]:
    """
    List all beta users (super admin only).

    Returns a list of all beta user accounts with their details.
    """
    result = await db.execute(select(models.User).order_by(models.User.created_at.desc()))
    users = result.scalars().all()

    return [
        schemas.BetaUserList(
            id=str(user.id),
            email=user.email,
            role=user.role,
            is_active=user.is_active,
            created_at=user.created_at.isoformat() if user.created_at else None,
            beta_tag=user.beta_tag,
            org_id=user.org_id,
        )
        for user in users
    ]


@router.post(
    "/users/{user_id}/reset-password",
    response_model=schemas.PasswordResetResponse,
    name="reset_user_password",
)
async def reset_user_password(
    user_id: str,
    payload: schemas.PasswordResetRequest,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[models.User, Depends(get_current_superadmin)],
) -> schemas.PasswordResetResponse:
    """
    Reset a user's password (super admin only).

    - If password is not provided, generates a new temporary password.
    - Returns the new temporary password in the response (shown only once).
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found",
        )

    # Generate or use provided password
    new_password = payload.password or _generate_temp_password()

    # Hash and update password
    user.hashed_password = security.get_password_hash(new_password)

    await db.commit()
    await db.refresh(user)

    return schemas.PasswordResetResponse(
        id=str(user.id),
        email=user.email,
        temp_password=new_password,
    )


@router.post(
    "/users/{user_id}/deactivate",
    response_model=schemas.UserDeactivateResponse,
    name="deactivate_user",
)
async def deactivate_user(
    user_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[models.User, Depends(get_current_superadmin)],
) -> schemas.UserDeactivateResponse:
    """
    Deactivate a user account (super admin only).

    Deactivates the user, preventing them from logging in.
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found",
        )

    user.is_active = False
    await db.commit()
    await db.refresh(user)

    return schemas.UserDeactivateResponse(
        id=str(user.id),
        email=user.email,
        is_active=user.is_active,
    )


@router.post(
    "/users/{user_id}/reactivate",
    response_model=schemas.UserDeactivateResponse,
    name="reactivate_user",
)
async def reactivate_user(
    user_id: str,
    db: Annotated[AsyncSession, Depends(get_db)],
    _admin: Annotated[models.User, Depends(get_current_superadmin)],
) -> schemas.UserDeactivateResponse:
    """
    Reactivate a user account (super admin only).

    Reactivates a deactivated user account, allowing them to log in.
    """
    result = await db.execute(select(models.User).where(models.User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID '{user_id}' not found",
        )

    user.is_active = True
    await db.commit()
    await db.refresh(user)

    return schemas.UserDeactivateResponse(
        id=str(user.id),
        email=user.email,
        is_active=user.is_active,
    )
