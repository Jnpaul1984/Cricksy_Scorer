"""
Tests for video storage quota enforcement.
"""

from __future__ import annotations

import pytest
from backend.services.billing_service import PLAN_FEATURES
from backend.services.video_quota_service import (
    check_video_quota,
    compute_user_video_usage_bytes,
    get_user_video_quota_bytes,
)
from backend.sql_app.models import (
    RoleEnum,
    User,
    VideoSession,
    VideoSessionStatus,
)


@pytest.mark.asyncio
async def test_compute_user_video_usage_bytes_empty(db_session):
    """Test that usage is 0 for a user with no videos."""
    usage = await compute_user_video_usage_bytes(db_session, "user_123")
    assert usage == 0


@pytest.mark.asyncio
async def test_compute_user_video_usage_bytes_with_sessions(db_session):
    """Test that usage sums across uploaded/processing/ready sessions."""
    # Create user
    user = User(
        id="coach_1",
        email="coach@test.com",
        hashed_password="hashed",
        role=RoleEnum.coach_pro_plus,
    )
    db_session.add(user)
    
    # Create sessions with different statuses
    session1 = VideoSession(
        id="s1",
        owner_type="coach",
        owner_id="coach_1",
        title="Session 1",
        player_ids=[],
        status=VideoSessionStatus.uploaded,
        file_size_bytes=1_000_000_000,  # 1 GB
    )
    session2 = VideoSession(
        id="s2",
        owner_type="coach",
        owner_id="coach_1",
        title="Session 2",
        player_ids=[],
        status=VideoSessionStatus.ready,
        file_size_bytes=500_000_000,  # 0.5 GB
    )
    session3 = VideoSession(
        id="s3",
        owner_type="coach",
        owner_id="coach_1",
        title="Session 3 (pending)",
        player_ids=[],
        status=VideoSessionStatus.pending,  # Should NOT count
        file_size_bytes=2_000_000_000,
    )
    db_session.add_all([session1, session2, session3])
    await db_session.commit()
    
    usage = await compute_user_video_usage_bytes(db_session, "coach_1")
    assert usage == 1_500_000_000  # Only s1 + s2


@pytest.mark.asyncio
async def test_get_user_video_quota_bytes_coach_pro_plus(db_session):
    """Test that coach_pro_plus gets quota from pricing config."""
    from backend.config.pricing import IndividualPlan, get_video_storage_bytes
    
    user = User(
        id="coach_1",
        email="coach@test.com",
        hashed_password="hashed",
        role=RoleEnum.coach_pro_plus,
    )
    quota_bytes = await get_user_video_quota_bytes(user)
    
    # Get expected value from pricing config (single source of truth)
    expected = get_video_storage_bytes(IndividualPlan.COACH_PRO_PLUS)
    assert quota_bytes == expected


@pytest.mark.asyncio
async def test_get_user_video_quota_bytes_org_pro_unlimited(db_session):
    """Test that org_pro has unlimited quota (from pricing config)."""
    from backend.config.pricing import IndividualPlan, get_video_storage_bytes
    
    user = User(
        id="org_1",
        email="org@test.com",
        hashed_password="hashed",
        role=RoleEnum.org_pro,
    )
    quota_bytes = await get_user_video_quota_bytes(user)
    
    # Verify against pricing config
    expected = get_video_storage_bytes(IndividualPlan.ORG_PRO)
    assert quota_bytes is None  # Unlimited
    assert expected is None  # Config also says unlimited


@pytest.mark.asyncio
async def test_check_video_quota_allowed(db_session):
    """Test that upload is allowed when under quota."""
    from backend.config.pricing import IndividualPlan, get_video_storage_bytes
    
    user = User(
        id="coach_1",
        email="coach@test.com",
        hashed_password="hashed",
        role=RoleEnum.coach_pro_plus,
    )
    db_session.add(user)
    await db_session.commit()
    
    # Check 1GB upload (well under quota)
    allowed, error = await check_video_quota(db_session, user, 1_000_000_000)
    assert allowed is True
    assert error is None


@pytest.mark.asyncio
async def test_check_video_quota_exceeded(db_session):
    """Test that upload is blocked when quota exceeded."""
    from backend.config.pricing import IndividualPlan, get_video_storage_bytes
    
    user = User(
        id="coach_1",
        email="coach@test.com",
        hashed_password="hashed",
        role=RoleEnum.coach_pro_plus,
    )
    db_session.add(user)
    
    # Get quota from pricing config
    quota_bytes = get_video_storage_bytes(IndividualPlan.COACH_PRO_PLUS)
    assert quota_bytes is not None, "Should have a quota"
    
    # Create session just under quota
    almost_full = quota_bytes - 1_000_000_000  # Leave 1GB free
    session1 = VideoSession(
        id="s1",
        owner_type="coach",
        owner_id="coach_1",
        title="Big Session",
        player_ids=[],
        status=VideoSessionStatus.ready,
        file_size_bytes=almost_full,
    )
    db_session.add(session1)
    await db_session.commit()
    
    # Try to upload more than remaining space (2GB > 1GB remaining)
    allowed, error = await check_video_quota(db_session, user, 2_000_000_000)
    assert allowed is False
    assert "quota exceeded" in error.lower()


@pytest.mark.asyncio
async def test_check_video_quota_superuser_unlimited(db_session):
    """Test that superuser has unlimited quota."""
    user = User(
        id="super_1",
        email="super@test.com",
        hashed_password="hashed",
        role=RoleEnum.free,
        is_superuser=True,
    )
    db_session.add(user)
    await db_session.commit()
    
    # Can upload any amount
    allowed, error = await check_video_quota(db_session, user, 100_000_000_000)
    assert allowed is True
    assert error is None
