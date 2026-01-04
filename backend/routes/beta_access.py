"""
Beta Access Management Endpoints

Allows superusers/org admins to grant beta access to users.
"""

from __future__ import annotations

import datetime as dt
import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import security
from backend.services.entitlement_service import get_user_entitlements
from backend.sql_app.database import get_db
from backend.sql_app.models import BetaAccess, User

router = APIRouter(prefix="/api/admin/beta-access", tags=["admin", "beta_access"])

UTC = dt.UTC


class GrantBetaAccessRequest(BaseModel):
    """Request to grant beta access to a user."""
    
    user_id: str = Field(..., description="User ID to grant beta access")
    is_super_beta: bool = Field(False, description="Grant all features (beta super user)")
    entitlements: list[str] | None = Field(None, description='Specific features: ["video_upload", "advanced_analytics"]')
    expires_at: dt.datetime | None = Field(None, description="Expiration date (None = permanent)")
    notes: str | None = Field(None, description="Admin notes")


class BetaAccessResponse(BaseModel):
    """Response with beta access details."""
    
    id: str
    user_id: str
    user_email: str
    is_super_beta: bool
    entitlements: list[str] | None
    expires_at: dt.datetime | None
    granted_by: str
    notes: str | None
    created_at: dt.datetime


@router.post("/grant", response_model=BetaAccessResponse)
async def grant_beta_access(
    request: GrantBetaAccessRequest,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> BetaAccessResponse:
    """
    Grant beta access to a user (superuser only).
    
    Allows granting:
    - Super beta access (all features)
    - Specific feature entitlements
    - Time-limited access
    """
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only superusers can grant beta access")
    
    # Check target user exists
    user_result = await db.execute(select(User).where(User.id == request.user_id))
    target_user = user_result.scalar_one_or_none()
    if not target_user:
        raise HTTPException(status_code=404, detail=f"User {request.user_id} not found")
    
    # Check if beta access already exists
    beta_result = await db.execute(select(BetaAccess).where(BetaAccess.user_id == request.user_id))
    existing = beta_result.scalar_one_or_none()
    
    if existing:
        # Update existing
        existing.is_super_beta = request.is_super_beta
        existing.entitlements = request.entitlements
        existing.expires_at = request.expires_at
        existing.granted_by = current_user.email
        existing.notes = request.notes
        beta_access = existing
    else:
        # Create new
        beta_access = BetaAccess(
            id=str(uuid.uuid4()),
            user_id=request.user_id,
            is_super_beta=request.is_super_beta,
            entitlements=request.entitlements,
            expires_at=request.expires_at,
            granted_by=current_user.email,
            notes=request.notes,
        )
        db.add(beta_access)
    
    await db.commit()
    await db.refresh(beta_access)
    
    return BetaAccessResponse(
        id=beta_access.id,
        user_id=beta_access.user_id,
        user_email=target_user.email,
        is_super_beta=beta_access.is_super_beta,
        entitlements=beta_access.entitlements,
        expires_at=beta_access.expires_at,
        granted_by=beta_access.granted_by or "unknown",
        notes=beta_access.notes,
        created_at=beta_access.created_at,
    )


@router.delete("/{user_id}")
async def revoke_beta_access(
    user_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """Revoke beta access from a user (superuser only)."""
    if not current_user.is_superuser:
        raise HTTPException(status_code=403, detail="Only superusers can revoke beta access")
    
    result = await db.execute(select(BetaAccess).where(BetaAccess.user_id == user_id))
    beta_access = result.scalar_one_or_none()
    
    if not beta_access:
        raise HTTPException(status_code=404, detail="Beta access not found for this user")
    
    await db.delete(beta_access)
    await db.commit()
    
    return {"message": f"Beta access revoked for user {user_id}"}


@router.get("/{user_id}/entitlements")
async def get_entitlements(
    user_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> dict:
    """
    Get all entitlements for a user (for debugging/support).
    
    Accessible by:
    - Superuser (any user)
    - User themselves
    """
    if not current_user.is_superuser and current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Can only view your own entitlements")
    
    user_result = await db.execute(select(User).where(User.id == user_id))
    user = user_result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return await get_user_entitlements(db, user)
