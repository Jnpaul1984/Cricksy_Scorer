"""
Video Storage Quota Management Service

Enforces Coach Pro Plus video storage limits (25GB default).
Computes user storage usage and validates uploads against quota.
"""

from __future__ import annotations

import logging
from typing import Any, cast

import boto3
from backend.config import settings
from backend.services.billing_service import get_user_features
from backend.sql_app.models import User, VideoSession, VideoSessionStatus
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def compute_user_video_usage_bytes(db: AsyncSession, user_id: str) -> int:
    """
    Compute total video storage used by a user in bytes.
    
    Sums file_size_bytes across all video sessions owned by the user
    that are in uploaded, processing, or ready status (excludes failed/pending).
    
    Args:
        db: Database session
        user_id: User ID (owner_id in video_sessions)
    
    Returns:
        Total bytes used (0 if no sessions or all sizes are NULL)
    """
    # Query sum of file_size_bytes for this user's active sessions
    stmt = select(func.coalesce(func.sum(VideoSession.file_size_bytes), 0)).where(
        VideoSession.owner_id == user_id,
        VideoSession.status.in_([
            VideoSessionStatus.uploaded,
            VideoSessionStatus.processing,
            VideoSessionStatus.ready,
        ]),
    )
    result = await db.execute(stmt)
    total_bytes = result.scalar_one()
    return int(total_bytes)


async def get_user_video_quota_bytes(user: User) -> int | None:
    """
    Get the video storage quota for a user in bytes.
    
    Args:
        user: User object
    
    Returns:
        Quota in bytes, or None if unlimited (org_pro, superuser)
    """
    if user.is_superuser:
        return None  # Unlimited
    
    features = get_user_features(user)
    # New structure has feature_flags nested
    feature_flags = features.get("feature_flags", features)
    quota_gb = feature_flags.get("video_storage_gb")
    
    if quota_gb is None:
        return None  # Unlimited (e.g., org_pro)
    
    if quota_gb == 0:
        return 0  # No video access
    
    return int(quota_gb * 1024 * 1024 * 1024)  # Convert GB to bytes


async def check_video_quota(
    db: AsyncSession,
    user: User,
    additional_bytes: int,
) -> tuple[bool, str | None]:
    """
    Check if user can upload additional video bytes without exceeding quota.
    
    Args:
        db: Database session
        user: User object
        additional_bytes: Size of new video to upload (in bytes)
    
    Returns:
        Tuple of (allowed: bool, error_message: str | None)
        If allowed=False, error_message explains why.
    """
    quota_bytes = await get_user_video_quota_bytes(user)
    
    # Unlimited quota (superuser or org_pro)
    if quota_bytes is None:
        return True, None
    
    # No video access at all
    if quota_bytes == 0:
        return False, "Video uploads not available on your plan. Upgrade to Coach Pro Plus."
    
    # Check current usage
    current_usage = await compute_user_video_usage_bytes(db, user.id)
    new_total = current_usage + additional_bytes
    
    if new_total > quota_bytes:
        quota_gb = quota_bytes / (1024 ** 3)
        used_gb = current_usage / (1024 ** 3)
        return False, (
            f"Storage quota exceeded. You have used {used_gb:.2f}GB of {quota_gb:.0f}GB. "
            f"Delete old sessions or upgrade your plan."
        )
    
    return True, None


async def get_s3_object_size(bucket: str, key: str) -> int:
    """
    Fetch the actual size of an S3 object using HeadObject.
    
    Args:
        bucket: S3 bucket name
        key: S3 object key
    
    Returns:
        File size in bytes
    
    Raises:
        Exception: If object does not exist or AWS credentials invalid
    """
    s3_client = cast(Any, boto3.client("s3", region_name=settings.AWS_REGION))
    
    try:
        response = s3_client.head_object(Bucket=bucket, Key=key)
        return int(response["ContentLength"])
    except Exception as e:
        logger.error(f"Failed to get S3 object size for s3://{bucket}/{key}: {e}")
        raise ValueError(f"Could not retrieve video file size from S3: {e}") from e
