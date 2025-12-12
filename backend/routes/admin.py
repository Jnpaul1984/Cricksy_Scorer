"""Admin-only routes for user management."""

from __future__ import annotations

import secrets
import string
from typing import Annotated

from backend import security
from backend.sql_app import models, schemas
from backend.sql_app.database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
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
