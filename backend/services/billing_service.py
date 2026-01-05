"""
Mock Billing Service - placeholder until Stripe integration.

Provides subscription status and plan feature lookups with mocked limits.
"""

from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.sql_app.models import AiUsageLog, RoleEnum, User

from backend.config.pricing import IndividualPlan, get_complete_plan_details

# Plan feature definitions - dynamically generated from pricing config
# This ensures backward compatibility while using the new single source of truth
PLAN_FEATURES: dict[str, dict] = {}

# Build PLAN_FEATURES from the IndividualPlan enum
for plan in IndividualPlan:
    details = get_complete_plan_details(plan)
    PLAN_FEATURES[plan.value] = details

# Add legacy aliases for backward compatibility
PLAN_FEATURES["superuser"] = {
    "plan_id": "superuser",
    "display_name": "Superuser",
    "price_monthly_usd": 0.0,
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
    "feature_flags": {
        "live_scoring": True,
        "scoring_access": True,
        "ai_predictions": True,
        "ai_reports_per_month": None,
        "tokens_limit": None,
        "max_games": None,
        "max_tournaments": None,
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
        Dictionary of plan features and limits with plan_id, display_name,
        price_monthly_usd, and feature_flags
    """
    # Import here to avoid circular dependency
    from backend.config.pricing import (
        IndividualPlan,
        get_complete_plan_details,
    )

    # Try to convert string to IndividualPlan enum
    try:
        plan_enum = IndividualPlan(plan)
        return get_complete_plan_details(plan_enum)
    except ValueError:
        # Fallback to old PLAN_FEATURES for backward compatibility
        details = PLAN_FEATURES.get(plan, PLAN_FEATURES["free"]).copy()
        # Add missing fields for backward compatibility
        details["plan_id"] = plan
        details["display_name"] = details.get("name", "Unknown Plan")
        details["price_monthly_usd"] = details.get("price_monthly", 0.0)
        details["feature_flags"] = details
        return details


async def get_user_plan_id(db: AsyncSession, user: User) -> str:
    """
    Get the plan ID (role) for a user.

    Args:
        db: Database session
        user: User object

    Returns:
        Plan identifier string (free, player_pro, coach_pro, etc.)
    """
    # Try to access role directly first (works if already loaded or user is transient)
    try:
        if hasattr(user, "__dict__") and "role" in user.__dict__:
            # Role is already loaded in the object's dict
            user_role = user.role
        else:
            # Need to query the database
            stmt = select(User.role).where(User.id == user.id)
            result = await db.execute(stmt)
            user_role = result.scalar_one()
    except Exception:
        # Fallback: try direct access (for transient objects not yet in DB)
        user_role = user.role

    return user_role.value if isinstance(user_role, RoleEnum) else str(user_role)


async def get_user_features(db: AsyncSession, user: User) -> dict:
    """
    Get the feature set for a user based on their role/plan.

    Args:
        db: Database session
        user: User object

    Returns:
        Dictionary of plan features and limits
    """
    plan_id = await get_user_plan_id(db, user)
    return get_plan_features(plan_id)


async def user_has_feature(db: AsyncSession, user: User, feature_name: str) -> bool:
    """
    Check if a user has access to a specific feature.

    Args:
        db: Database session
        user: User object
        feature_name: Feature key to check (e.g., 'video_upload_enabled')

    Returns:
        True if user's plan includes the feature and it is enabled, False otherwise
    """
    features = await get_user_features(db, user)
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
        db: AsyncSession = Depends(
            __import__("backend.sql_app.database", fromlist=["get_db"]).get_db
        ),
    ) -> User:
        if not await user_has_feature(db, current_user, feature_name):
            plan = await get_user_plan_id(db, current_user)
            plan_info = get_plan_features(plan)
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Feature '{feature_name}' requires a higher tier plan. Current: {plan_info['name']}",
            )
        return current_user

    return Depends(_check_feature)
