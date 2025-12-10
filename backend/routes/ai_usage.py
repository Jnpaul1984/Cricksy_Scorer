"""AI Usage Stats API for the usage dashboard."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import extract, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend import security
from backend.sql_app import models
from backend.sql_app.database import get_db

router = APIRouter(prefix="/ai-usage", tags=["ai-usage"])


# --- Response Schemas ---


class FeatureUsage(BaseModel):
    feature: str
    tokens: int
    request_count: int


class MonthlyUsage(BaseModel):
    month: str  # "2025-01"
    tokens: int
    request_count: int


class TopUser(BaseModel):
    user_id: str
    email: str
    tokens: int
    request_count: int


class UsageQuota(BaseModel):
    used: int
    limit: int | None  # None = unlimited
    percentage: float


class UsageStatsResponse(BaseModel):
    total_tokens: int
    total_requests: int
    by_feature: list[FeatureUsage]
    by_month: list[MonthlyUsage]
    top_users: list[TopUser]
    quota: UsageQuota


# --- API Endpoints ---


@router.get("/stats", response_model=UsageStatsResponse)
async def get_usage_stats(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[models.User, Depends(security.get_current_active_user)],
    org_id: str | None = Query(None, description="Filter by organization ID"),
    user_id: str | None = Query(None, description="Filter by specific user ID"),
    year: int | None = Query(None, description="Filter by year (e.g. 2025)"),
    month: int | None = Query(None, description="Filter by month (1-12)"),
) -> UsageStatsResponse:
    """
    Get AI usage statistics with optional filters.
    
    Requires org_pro or superuser role for org-wide stats.
    Regular users can only see their own usage.
    """
    user_role = str(current_user.role.value if hasattr(current_user.role, "value") else current_user.role)
    is_admin = current_user.is_superuser or user_role == "org_pro"

    # Non-admins can only see their own data
    if not is_admin:
        user_id = str(current_user.id)
        org_id = None

    # Build base query filter
    def apply_filters(query):
        if user_id:
            query = query.where(models.AiUsageLog.user_id == user_id)
        if org_id:
            query = query.where(models.AiUsageLog.org_id == org_id)
        if year:
            query = query.where(extract("year", models.AiUsageLog.timestamp) == year)
        if month:
            query = query.where(extract("month", models.AiUsageLog.timestamp) == month)
        return query

    # Get totals
    totals_query = apply_filters(
        select(
            func.coalesce(func.sum(models.AiUsageLog.tokens_used), 0).label("total_tokens"),
            func.count(models.AiUsageLog.id).label("total_requests"),
        )
    )
    totals_result = await db.execute(totals_query)
    totals_row = totals_result.one()

    # Get by feature
    feature_query = apply_filters(
        select(
            models.AiUsageLog.feature,
            func.sum(models.AiUsageLog.tokens_used).label("tokens"),
            func.count(models.AiUsageLog.id).label("request_count"),
        ).group_by(models.AiUsageLog.feature)
    )
    feature_result = await db.execute(feature_query)
    by_feature = [
        FeatureUsage(feature=row.feature, tokens=int(row.tokens or 0), request_count=int(row.request_count))
        for row in feature_result.all()
    ]

    # Get by month
    month_query = apply_filters(
        select(
            func.to_char(models.AiUsageLog.timestamp, "YYYY-MM").label("month"),
            func.sum(models.AiUsageLog.tokens_used).label("tokens"),
            func.count(models.AiUsageLog.id).label("request_count"),
        ).group_by(func.to_char(models.AiUsageLog.timestamp, "YYYY-MM"))
        .order_by(func.to_char(models.AiUsageLog.timestamp, "YYYY-MM"))
    )
    month_result = await db.execute(month_query)
    by_month = [
        MonthlyUsage(month=row.month, tokens=int(row.tokens or 0), request_count=int(row.request_count))
        for row in month_result.all()
    ]

    # Get top users (only for admins)
    top_users: list[TopUser] = []
    if is_admin:
        top_users_query = apply_filters(
            select(
                models.AiUsageLog.user_id,
                func.sum(models.AiUsageLog.tokens_used).label("tokens"),
                func.count(models.AiUsageLog.id).label("request_count"),
            )
            .group_by(models.AiUsageLog.user_id)
            .order_by(func.sum(models.AiUsageLog.tokens_used).desc())
            .limit(10)
        )
        top_result = await db.execute(top_users_query)

        for row in top_result.all():
            # Fetch user email
            user = await db.get(models.User, row.user_id)
            email = user.email if user else "unknown"
            top_users.append(
                TopUser(
                    user_id=row.user_id,
                    email=email,
                    tokens=int(row.tokens or 0),
                    request_count=int(row.request_count),
                )
            )

    # Calculate quota (example: 100k tokens/month for pro, unlimited for org_pro)
    quota_limit: int | None = None
    if user_role == "free":
        quota_limit = 10000
    elif user_role in ("player_pro", "coach_pro", "analyst_pro"):
        quota_limit = 100000
    # org_pro and superuser have unlimited

    used_tokens = int(totals_row.total_tokens or 0)
    percentage = (used_tokens / quota_limit * 100) if quota_limit else 0.0

    return UsageStatsResponse(
        total_tokens=used_tokens,
        total_requests=int(totals_row.total_requests or 0),
        by_feature=by_feature,
        by_month=by_month,
        top_users=top_users,
        quota=UsageQuota(
            used=used_tokens,
            limit=quota_limit,
            percentage=min(percentage, 100.0),
        ),
    )


@router.get("/my-usage", response_model=UsageStatsResponse)
async def get_my_usage(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[models.User, Depends(security.get_current_active_user)],
    year: int | None = Query(None),
    month: int | None = Query(None),
) -> UsageStatsResponse:
    """Get the current user's AI usage stats."""
    return await get_usage_stats(
        db=db,
        current_user=current_user,
        org_id=None,
        user_id=str(current_user.id),
        year=year,
        month=month,
    )
