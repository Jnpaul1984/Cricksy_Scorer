"""
Tests for beta access entitlement system.

Tests:
1. Super beta user can access all features regardless of role
2. User with specific entitlements can access those features
3. Expired beta access does not grant access
4. Non-beta users fall back to role-based access
"""

from __future__ import annotations

import datetime as dt
import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.entitlement_service import can_access_feature, get_user_entitlements
from backend.sql_app.models import BetaAccess, RoleEnum, User

UTC = dt.UTC


@pytest.mark.asyncio
async def test_super_beta_user_all_features(db_session: AsyncSession):
    """Super beta users should access all features regardless of role."""
    # Create user with role=free
    user = User(
        id=str(uuid.uuid4()),
        email="superbeta@example.com",
        hashed_password="fake",
        role=RoleEnum.free,
        is_superuser=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    # Grant super beta access
    beta = BetaAccess(
        id=str(uuid.uuid4()),
        user_id=user.id,
        is_super_beta=True,
        entitlements=None,
        granted_by="admin@example.com",
    )
    db_session.add(beta)
    await db_session.commit()
    await db_session.refresh(user)  # Refresh to avoid lazy loading issues

    # Should have access to all coach_pro_plus features
    assert await can_access_feature(db_session, user, "video_upload_enabled")
    assert await can_access_feature(db_session, user, "video_analysis_enabled")
    assert await can_access_feature(db_session, user, "advanced_analytics")


@pytest.mark.asyncio
async def test_specific_entitlements(db_session: AsyncSession):
    """User with specific entitlements should access only those features."""
    user = User(
        id=str(uuid.uuid4()),
        email="beta@example.com",
        hashed_password="fake",
        role=RoleEnum.free,
        is_superuser=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    # Grant specific entitlements
    beta = BetaAccess(
        id=str(uuid.uuid4()),
        user_id=user.id,
        is_super_beta=False,
        entitlements=["video_upload_enabled", "video_sessions_enabled"],
        granted_by="admin@example.com",
    )
    db_session.add(beta)
    await db_session.commit()
    await db_session.refresh(user)  # Refresh to avoid lazy loading issues

    # Should have access to granted features
    assert await can_access_feature(db_session, user, "video_upload_enabled")
    assert await can_access_feature(db_session, user, "video_sessions_enabled")

    # Should NOT have access to non-granted features
    assert not await can_access_feature(db_session, user, "video_analysis_enabled")
    assert not await can_access_feature(db_session, user, "advanced_analytics")


@pytest.mark.asyncio
async def test_expired_beta_access_no_grant(db_session: AsyncSession):
    """Expired beta access should not grant feature access."""
    user = User(
        id=str(uuid.uuid4()),
        email="expired@example.com",
        hashed_password="fake",
        role=RoleEnum.free,
        is_superuser=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    # Grant beta access that expired yesterday
    yesterday = dt.datetime.now(UTC) - dt.timedelta(days=1)
    beta = BetaAccess(
        id=str(uuid.uuid4()),
        user_id=user.id,
        is_super_beta=True,
        entitlements=None,
        expires_at=yesterday,
        granted_by="admin@example.com",
    )
    db_session.add(beta)
    await db_session.commit()
    await db_session.refresh(user)  # Refresh to avoid lazy loading issues

    # Should NOT have access (expired)
    assert not await can_access_feature(db_session, user, "video_upload_enabled")
    assert not await can_access_feature(db_session, user, "video_analysis_enabled")


@pytest.mark.asyncio
async def test_role_based_fallback_no_beta(db_session: AsyncSession):
    """Users without beta access should fall back to role-based features."""
    # Coach Pro Plus user (no beta access)
    user = User(
        id=str(uuid.uuid4()),
        email="coach@example.com",
        hashed_password="fake",
        role=RoleEnum.coach_pro_plus,
        is_superuser=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)  # Refresh to avoid lazy loading issues

    # Should have access via role features
    assert await can_access_feature(db_session, user, "video_upload_enabled")
    assert await can_access_feature(db_session, user, "video_analysis_enabled")


@pytest.mark.asyncio
async def test_superuser_bypass(db_session: AsyncSession):
    """Superusers should bypass all checks (no beta access needed)."""
    user = User(
        id=str(uuid.uuid4()),
        email="admin@example.com",
        hashed_password="fake",
        role=RoleEnum.free,  # Even with free role
        is_superuser=True,
        is_active=True,
    )
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)  # Refresh to avoid lazy loading issues

    # Superuser should access everything
    assert await can_access_feature(db_session, user, "video_upload_enabled")
    assert await can_access_feature(db_session, user, "video_analysis_enabled")
    assert await can_access_feature(db_session, user, "advanced_analytics")


@pytest.mark.asyncio
async def test_get_user_entitlements_super_beta(db_session: AsyncSession):
    """get_user_entitlements should show super beta status."""
    user = User(
        id=str(uuid.uuid4()),
        email="superbeta@example.com",
        hashed_password="fake",
        role=RoleEnum.free,
        is_superuser=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    beta = BetaAccess(
        id=str(uuid.uuid4()),
        user_id=user.id,
        is_super_beta=True,
        entitlements=None,
        granted_by="admin@example.com",
    )
    db_session.add(beta)
    await db_session.commit()
    await db_session.refresh(user)  # Refresh to preload user.id

    entitlements = await get_user_entitlements(db_session, user.id)

    assert entitlements["role"] == "free"
    assert entitlements["beta_access"] is not None
    assert entitlements["beta_access"]["is_super_beta"] is True
    assert entitlements["beta_access"]["active"] is True


@pytest.mark.asyncio
async def test_get_user_entitlements_specific(db_session: AsyncSession):
    """get_user_entitlements should list specific entitlements."""
    user = User(
        id=str(uuid.uuid4()),
        email="beta@example.com",
        hashed_password="fake",
        role=RoleEnum.free,
        is_superuser=False,
        is_active=True,
    )
    db_session.add(user)
    await db_session.flush()

    beta = BetaAccess(
        id=str(uuid.uuid4()),
        user_id=user.id,
        is_super_beta=False,
        entitlements=["video_upload_enabled"],
        granted_by="admin@example.com",
    )
    db_session.add(beta)
    await db_session.commit()
    await db_session.refresh(user)  # Refresh to preload user.id

    entitlements = await get_user_entitlements(db_session, user.id)

    assert entitlements["beta_access"] is not None
    assert entitlements["beta_access"]["is_super_beta"] is False
    assert "video_upload_enabled" in entitlements["beta_access"]["entitlements"]
