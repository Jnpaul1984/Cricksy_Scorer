"""
Billing API routes - Mock endpoints until Stripe integration.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from backend.security import get_current_user
from backend.services.billing_service import (
    check_feature_access,
    check_usage_limit,
    get_plan_features,
    get_subscription_status,
)
from backend.sql_app.database import get_db
from backend.sql_app.models import User

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/subscription")
async def get_my_subscription(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get current user's subscription status and usage.

    Returns plan details, feature access, and remaining limits.
    """
    return await get_subscription_status(db, current_user.id)


@router.get("/plans")
async def list_plans():
    """
    Get all available subscription plans and their features.
    """
    plans = ["free", "player_pro", "coach_pro", "analyst_pro", "org_pro"]
    return {
        "plans": [
            {"key": plan, **get_plan_features(plan)}
            for plan in plans
        ]
    }


@router.get("/plans/{plan}")
async def get_plan(plan: str):
    """
    Get features for a specific plan.
    """
    features = get_plan_features(plan)
    if not features:
        raise HTTPException(status_code=404, detail="Plan not found")
    return {"plan": plan, **features}


@router.get("/check-feature/{feature}")
async def check_feature(
    feature: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Check if current user has access to a specific feature.

    Features: export_pdf, priority_support, team_management, advanced_analytics
    """
    return await check_feature_access(db, current_user.id, feature)


@router.get("/check-limit/{resource}")
async def check_limit(
    resource: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Check remaining quota for a resource.

    Resources: ai_reports, tokens
    """
    if resource not in ("ai_reports", "tokens"):
        raise HTTPException(status_code=400, detail="Invalid resource. Use 'ai_reports' or 'tokens'")
    return await check_usage_limit(db, current_user.id, resource)
