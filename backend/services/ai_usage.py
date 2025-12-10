"""AI usage logging service for tracking LLM feature usage."""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from backend.sql_app.models import AiUsageLog

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


async def log_ai_usage(
    db: "AsyncSession",
    user_id: str,
    feature: str,
    tokens_used: int,
    context_id: str | None = None,
    org_id: str | None = None,
    model_name: str | None = None,
) -> AiUsageLog:
    """
    Log AI/LLM usage for a user.

    Args:
        db: Database session
        user_id: ID of the user making the request
        feature: Feature identifier (e.g. "match_summary", "player_insights")
        tokens_used: Number of tokens consumed
        context_id: Optional reference ID (game_id, player_id, etc.)
        org_id: Optional organization ID for org-level billing
        model_name: Optional LLM model name (e.g. "gpt-4", "claude-3")

    Returns:
        The created AiUsageLog record

    Example:
        >>> await log_ai_usage(
        ...     db=session,
        ...     user_id="user-123",
        ...     feature="match_summary",
        ...     tokens_used=1500,
        ...     context_id="game-456",
        ...     model_name="gpt-4"
        ... )
    """
    usage_log = AiUsageLog(
        user_id=user_id,
        feature=feature,
        tokens_used=tokens_used,
        context_id=context_id,
        org_id=org_id,
        model_name=model_name,
    )

    db.add(usage_log)
    await db.commit()
    await db.refresh(usage_log)

    logger.info(
        "AI usage logged: user=%s feature=%s tokens=%d context=%s",
        user_id,
        feature,
        tokens_used,
        context_id,
    )

    return usage_log


async def get_user_usage_summary(
    db: "AsyncSession",
    user_id: str,
    feature: str | None = None,
) -> dict[str, int]:
    """
    Get usage summary for a user, optionally filtered by feature.

    Returns:
        Dict with total_tokens and request_count
    """
    from sqlalchemy import func, select

    query = select(
        func.sum(AiUsageLog.tokens_used).label("total_tokens"),
        func.count(AiUsageLog.id).label("request_count"),
    ).where(AiUsageLog.user_id == user_id)

    if feature:
        query = query.where(AiUsageLog.feature == feature)

    result = await db.execute(query)
    row = result.one_or_none()

    return {
        "total_tokens": row.total_tokens or 0 if row else 0,
        "request_count": row.request_count or 0 if row else 0,
    }


async def get_org_usage_summary(
    db: "AsyncSession",
    org_id: str,
    feature: str | None = None,
) -> dict[str, int]:
    """
    Get usage summary for an organization, optionally filtered by feature.

    Returns:
        Dict with total_tokens and request_count
    """
    from sqlalchemy import func, select

    query = select(
        func.sum(AiUsageLog.tokens_used).label("total_tokens"),
        func.count(AiUsageLog.id).label("request_count"),
    ).where(AiUsageLog.org_id == org_id)

    if feature:
        query = query.where(AiUsageLog.feature == feature)

    result = await db.execute(query)
    row = result.one_or_none()

    return {
        "total_tokens": row.total_tokens or 0 if row else 0,
        "request_count": row.request_count or 0 if row else 0,
    }
