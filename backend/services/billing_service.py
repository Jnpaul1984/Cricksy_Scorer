"""
Mock Billing Service - placeholder until Stripe integration.

Provides subscription status and plan feature lookups with mocked limits.
"""

from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.sql_app.models import AiUsageLog, RoleEnum, User


# Plan feature definitions
PLAN_FEATURES: dict[str, dict] = {
    "free": {
        "name": "Free",
        "price_monthly": 0,
        "tokens_limit": 10_000,
        "ai_reports_per_month": 5,
        "max_games": 10,
        "max_tournaments": 1,
        "live_scoring": True,
        "ai_predictions": True,
        "export_pdf": False,
        "priority_support": False,
        "team_management": False,
        "advanced_analytics": False,
    },
    "player_pro": {
        "name": "Player Pro",
        "price_monthly": 9.99,
        "tokens_limit": 100_000,
        "ai_reports_per_month": 50,
        "max_games": None,  # Unlimited
        "max_tournaments": 10,
        "live_scoring": True,
        "ai_predictions": True,
        "export_pdf": True,
        "priority_support": False,
        "team_management": False,
        "advanced_analytics": True,
    },
    "coach_pro": {
        "name": "Coach Pro",
        "price_monthly": 19.99,
        "tokens_limit": 100_000,
        "ai_reports_per_month": 100,
        "max_games": None,
        "max_tournaments": 50,
        "live_scoring": True,
        "ai_predictions": True,
        "export_pdf": True,
        "priority_support": True,
        "team_management": True,
        "advanced_analytics": True,
    },
    "coach_pro_plus": {
        "name": "Coach Pro Plus",
        "price_monthly": 24.99,
        "base_plan": "coach_pro",
        "tokens_limit": 100_000,
        "ai_reports_per_month": 20,
        "max_games": None,
        "max_tournaments": 50,
        "live_scoring": True,
        "ai_predictions": True,
        "export_pdf": True,
        "priority_support": True,
        "team_management": True,
        "advanced_analytics": True,
        "coach_dashboard": True,
        "coaching_sessions": True,
        "player_assignments": True,
        "video_sessions_enabled": True,
        "video_upload_enabled": True,
        "ai_session_reports_enabled": True,
        "video_storage_gb": 25,
    },
    "analyst_pro": {
        "name": "Analyst Pro",
        "price_monthly": 29.99,
        "tokens_limit": 100_000,
        "ai_reports_per_month": 200,
        "max_games": None,
        "max_tournaments": None,
        "live_scoring": True,
        "ai_predictions": True,
        "export_pdf": True,
        "priority_support": True,
        "team_management": True,
        "advanced_analytics": True,
    },
    "org_pro": {
        "name": "Organization Pro",
        "price_monthly": 99.99,
        "tokens_limit": None,  # Unlimited
        "ai_reports_per_month": None,  # Unlimited
        "max_games": None,
        "max_tournaments": None,
        "live_scoring": True,
        "ai_predictions": True,
        "export_pdf": True,
        "priority_support": True,
        "team_management": True,
        "advanced_analytics": True,
    },
    "superuser": {
        "name": "Superuser",
        "price_monthly": 0,
        "tokens_limit": None,
        "ai_reports_per_month": None,
        "max_games": None,
        "max_tournaments": None,
        "live_scoring": True,
        "ai_predictions": True,
        "export_pdf": True,
        "priority_support": True,
        "team_management": True,
        "advanced_analytics": True,
    },
}


def get_plan_features(plan: str) -> dict:
    """
    Get feature set for a subscription plan.

    Args:
        plan: Plan identifier (free, player_pro, coach_pro, etc.)

    Returns:
        Dictionary of plan features and limits
    """
    return PLAN_FEATURES.get(plan, PLAN_FEATURES["free"]).copy()


def get_user_plan_id(user: User) -> str:
    """
    Get the plan ID (role) for a user.

    Args:
        user: User object

    Returns:
        Plan identifier string (free, player_pro, coach_pro, etc.)
    """
    return user.role.value if isinstance(user.role, RoleEnum) else str(user.role)


def get_user_features(user: User) -> dict:
    """
    Get the feature set for a user based on their role/plan.

    Args:
        user: User object

    Returns:
        Dictionary of plan features and limits
    """
    plan_id = get_user_plan_id(user)
    return get_plan_features(plan_id)


def user_has_feature(user: User, feature_name: str) -> bool:
    """
    Check if a user has access to a specific feature.

    Args:
        user: User object
        feature_name: Feature key to check (e.g., 'video_upload_enabled')

    Returns:
        True if user's plan includes the feature and it is enabled, False otherwise
    """
    features = get_user_features(user)
    return features.get(feature_name, False)


async def get_subscription_status(
    db: AsyncSession,
    user_id: int,
) -> dict:
    """
    Get subscription status for a user (mocked for now).

    Args:
        db: Database session
        user_id: User ID

    Returns:
        Dictionary with subscription status, usage, and remaining limits
    """
    # Fetch user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        return {
            "status": "not_found",
            "error": "User not found",
        }

    plan = user.role.value if isinstance(user.role, RoleEnum) else str(user.role)
    features = get_plan_features(plan)

    # Get current month's AI usage
    month_start = datetime.utcnow().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    usage_result = await db.execute(
        select(
            func.count(AiUsageLog.id).label("report_count"),
            func.coalesce(func.sum(AiUsageLog.tokens_used), 0).label("tokens_used"),
        ).where(
            AiUsageLog.user_id == user_id,
            AiUsageLog.created_at >= month_start,
        )
    )
    usage = usage_result.one()
    reports_used = usage.report_count or 0
    tokens_used = usage.tokens_used or 0

    # Calculate remaining
    reports_limit = features["ai_reports_per_month"]
    tokens_limit = features["tokens_limit"]

    reports_remaining = None if reports_limit is None else max(0, reports_limit - reports_used)
    tokens_remaining = None if tokens_limit is None else max(0, tokens_limit - tokens_used)

    # Mock renewal date (first of next month)
    next_month = datetime.utcnow().replace(day=1) + timedelta(days=32)
    renewal_date = next_month.replace(day=1)

    return {
        "status": "active",  # Mocked as always active for now
        "plan": plan,
        "plan_name": features["name"],
        "price_monthly": features["price_monthly"],
        "renewal_date": renewal_date.isoformat(),
        "usage": {
            "ai_reports_used": reports_used,
            "ai_reports_limit": reports_limit,
            "ai_reports_remaining": reports_remaining,
            "tokens_used": tokens_used,
            "tokens_limit": tokens_limit,
            "tokens_remaining": tokens_remaining,
        },
        "features": {
            "max_games": features["max_games"],
            "max_tournaments": features["max_tournaments"],
            "live_scoring": features["live_scoring"],
            "ai_predictions": features["ai_predictions"],
            "export_pdf": features["export_pdf"],
            "priority_support": features["priority_support"],
            "team_management": features["team_management"],
            "advanced_analytics": features["advanced_analytics"],
        },
        "can_upgrade": plan in ("free", "player_pro", "coach_pro", "analyst_pro"),
    }


async def check_feature_access(
    db: AsyncSession,
    user_id: int,
    feature: str,
) -> dict:
    """
    Check if a user has access to a specific feature.

    Args:
        db: Database session
        user_id: User ID
        feature: Feature key to check

    Returns:
        Dictionary with access status and reason
    """
    status = await get_subscription_status(db, user_id)

    if status["status"] != "active":
        return {"allowed": False, "reason": "No active subscription"}

    features = status["features"]

    if feature not in features:
        return {"allowed": False, "reason": f"Unknown feature: {feature}"}

    if not features[feature]:
        return {
            "allowed": False,
            "reason": f"Feature '{feature}' not available on {status['plan_name']} plan",
            "upgrade_required": True,
        }

    return {"allowed": True}


async def check_usage_limit(
    db: AsyncSession,
    user_id: int,
    resource: str,
) -> dict:
    """
    Check if user has remaining quota for a resource.

    Args:
        db: Database session
        user_id: User ID
        resource: Resource type ("ai_reports" or "tokens")

    Returns:
        Dictionary with limit status
    """
    status = await get_subscription_status(db, user_id)

    if status["status"] != "active":
        return {"allowed": False, "reason": "No active subscription"}

    usage = status["usage"]

    if resource == "ai_reports":
        remaining = usage["ai_reports_remaining"]
        if remaining is None:
            return {"allowed": True, "remaining": None, "unlimited": True}
        if remaining <= 0:
            return {
                "allowed": False,
                "reason": "Monthly AI report limit reached",
                "remaining": 0,
                "limit": usage["ai_reports_limit"],
                "upgrade_required": True,
            }
        return {"allowed": True, "remaining": remaining, "limit": usage["ai_reports_limit"]}

    elif resource == "tokens":
        remaining = usage["tokens_remaining"]
        if remaining is None:
            return {"allowed": True, "remaining": None, "unlimited": True}
        if remaining <= 0:
            return {
                "allowed": False,
                "reason": "Monthly token limit reached",
                "remaining": 0,
                "limit": usage["tokens_limit"],
                "upgrade_required": True,
            }
        return {"allowed": True, "remaining": remaining, "limit": usage["tokens_limit"]}

    return {"allowed": False, "reason": f"Unknown resource: {resource}"}


def require_feature(feature_name: str):
    """
    FastAPI dependency that checks if the current user has access to a feature.

    Args:
        feature_name: Feature key to check (e.g., 'video_upload_enabled')

    Returns:
        Dependency function that validates feature access

    Raises:
        HTTPException: 403 Forbidden if user lacks the feature
    """

    async def _check_feature(
        current_user: User = Depends(
            __import__("backend.security", fromlist=["get_current_user"]).get_current_user
        ),
    ) -> User:
        if not user_has_feature(current_user, feature_name):
            plan = get_user_plan_id(current_user)
            plan_info = get_plan_features(plan)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature_name}' requires a higher tier plan. Current: {plan_info['name']}",
            )
        return current_user

    return Depends(_check_feature)
