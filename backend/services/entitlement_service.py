"""
Entitlement Service - Centralized Feature Access Control

REFACTORED: Now uses backend/config/pricing.py for all entitlements.

Checks if users can access features based on:
1. Superuser status (bypass all checks)
2. Beta access grants (is_super_beta or specific entitlements)
3. Subscription plan (role-based features from pricing.py)

This replaces scattered role checks across routes with a single source of truth.
"""

from __future__ import annotations

import datetime as dt
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.config.pricing import IndividualPlan, get_entitlements_for_plan
from backend.sql_app.models import BetaAccess, User

logger = logging.getLogger(__name__)

UTC = dt.UTC


async def can_access_feature(
    db: AsyncSession,
    user: User,
    feature_name: str,
) -> bool:
    """
    Check if a user can access a specific feature.

    Decision flow:
    1. If user.is_superuser → TRUE (bypass all checks)
    2. Check beta_access table:
       - If is_super_beta and not expired → TRUE
       - If feature_name in entitlements and not expired → TRUE
    3. Check subscription plan features (role-based)
    4. Default → FALSE

    Args:
        db: Database session
        user: User object
        feature_name: Feature key (e.g., "video_upload_enabled", "advanced_analytics")

    Returns:
        True if user has access, False otherwise

    Examples:
        >>> await can_access_feature(db, user, "video_upload_enabled")
        True  # If user is coach_pro_plus OR has beta access
    """
    # 1. Superuser bypass
    if user.is_superuser:
        return True

    # 2. Check beta access grants
    stmt = select(BetaAccess).where(BetaAccess.user_id == user.id)
    result = await db.execute(stmt)
    beta_access = result.scalar_one_or_none()

    if beta_access:
        # Check expiration
        if beta_access.expires_at:
            now = dt.datetime.now(UTC)
            if now > beta_access.expires_at.replace(tzinfo=UTC):
                logger.info(f"Beta access expired for user {user.id}")
            else:
                # Not expired, check grants
                if beta_access.is_super_beta:
                    return True

                if beta_access.entitlements and feature_name in beta_access.entitlements:
                    return True
        else:
            # No expiration (permanent beta access)
            if beta_access.is_super_beta:
                return True

            if beta_access.entitlements and feature_name in beta_access.entitlements:
                return True

    # 3. Check subscription plan (role-based features from pricing.py)
    # Requery user to get role in current session context
    stmt = select(User.role).where(User.id == user.id)
    result = await db.execute(stmt)
    user_role = result.scalar_one_or_none()
    
    if not user_role:
        logger.warning(f"Could not find role for user {user.id}")
        return False
    
    try:
        role_value = user_role.value if hasattr(user_role, "value") else str(user_role)
        plan = IndividualPlan(role_value)
        user_features = get_entitlements_for_plan(plan)
        return bool(user_features.get(feature_name, False))
    except (ValueError, KeyError):
        # Unknown plan - default deny
        logger.warning(f"Unknown plan for user {user.id}: {user_role}")
        return False


async def get_user_entitlements(
    db: AsyncSession,
    user: User,
) -> dict[str, Any]:
    """
    Get all entitlements for a user (for display/debugging).

    Args:
        db: Database session
        user: User object

    Returns:
        Dictionary with:
        - role: Current role
        - is_superuser: Bool
        - beta_access: BetaAccess record if exists
        - plan_features: Features from subscription plan
    """
    # Requery user role to avoid lazy load issues
    stmt = select(User.role).where(User.id == user.id)
    result = await db.execute(stmt)
    user_role = result.scalar_one_or_none()
    
    # Get beta access
    stmt = select(BetaAccess).where(BetaAccess.user_id == user.id)
    result = await db.execute(stmt)
    beta_access = result.scalar_one_or_none()

    # Get plan features from pricing.py
    plan_features: dict[str, Any] = {}
    if user_role:
        try:
            role_value = user_role.value if hasattr(user_role, "value") else str(user_role)
            plan = IndividualPlan(role_value)
            plan_features = get_entitlements_for_plan(plan).model_dump()
        except (ValueError, KeyError):
            pass

    return {
        "role": user_role.value if user_role and hasattr(user_role, "value") else str(user_role) if user_role else "unknown",
        "is_superuser": user.is_superuser,
        "beta_access": {
            "active": beta_access is not None,
            "is_super_beta": beta_access.is_super_beta if beta_access else False,
            "entitlements": beta_access.entitlements if beta_access else [],
            "expires_at": beta_access.expires_at.isoformat()
            if beta_access and beta_access.expires_at
            else None,
        }
        if beta_access
        else None,
        "plan_features": plan_features,
    }


def require_feature(feature_name: str):
    """
    FastAPI dependency decorator that enforces feature access.

    Usage:
        @router.get("/premium-endpoint", dependencies=[require_feature("advanced_analytics")])
        async def premium_feature(...):
            pass

    Args:
        feature_name: Feature key to check

    Returns:
        FastAPI Depends wrapper that validates access
    """
    from fastapi import Depends, HTTPException, status
    from backend.security import get_current_active_user
    from backend.sql_app.database import get_db

    async def _check_access(
        current_user: User = Depends(get_current_active_user),
        db: AsyncSession = Depends(get_db),
    ) -> User:
        has_access = await can_access_feature(db, current_user, feature_name)
        if not has_access:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied: '{feature_name}' requires a higher plan or beta access.",
            )
        return current_user

    return Depends(_check_access)
