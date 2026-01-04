"""
Pricing API Routes - Expose canonical pricing to frontend.

This endpoint serves as the frontend's ONLY source for pricing information.
Frontend must NOT hardcode prices.
"""  
from fastapi import APIRouter, HTTPException

from backend.config.pricing import (
    INDIVIDUAL_ENTITLEMENTS,
    INDIVIDUAL_PRICES,
    VENUE_ENTITLEMENTS,
    VENUE_PRICES,
    IndividualPlan,
    VenuePlan,
)

router = APIRouter(prefix="/pricing", tags=["pricing"])


@router.get("/")
async def get_pricing():
    """
    Get all pricing plans (individual + venue).
    
    Frontend should call this endpoint on app load and cache locally.
    Do NOT hardcode prices in frontend - they may change.
    
    Returns:
        {
            "individual_plans": [...],
            "venue_plans": [...],
            "scoring_is_free": True  # CRITICAL guarantee
        }
    """
    individual_plans = []
    for plan in IndividualPlan:
        pricing = INDIVIDUAL_PRICES[plan]
        entitlements = INDIVIDUAL_ENTITLEMENTS[plan]
        
        individual_plans.append({
            "id": plan.value,
            "name": pricing["name"],
            "tagline": pricing["tagline"],
            "price_monthly_usd": float(pricing["monthly_usd"]),
            "features": entitlements,
        })
    
    venue_plans = []
    for plan in VenuePlan:
        pricing = VENUE_PRICES[plan]
        entitlements = VENUE_ENTITLEMENTS[plan]
        
        venue_plans.append({
            "id": plan.value,
            "name": pricing["name"],
            "tagline": pricing["tagline"],
            "price_monthly_usd": float(pricing["monthly_usd"]) if pricing["monthly_usd"] is not None else None,
            "contact_for_pricing": pricing["monthly_usd"] is None,
            "features": entitlements,
        })
    
    return {
        "individual_plans": individual_plans,
        "venue_plans": venue_plans,
        "scoring_is_free": True,  # CRITICAL: Scoring always free for individuals
        "contract_version": "1.0.0",
        "last_updated": "2026-01-04",
    }


@router.get("/individual/{plan_id}")
async def get_individual_plan(plan_id: str):
    """
    Get details for a specific individual plan.
    
    Args:
        plan_id: Plan identifier (free, player_pro, coach_pro, etc.)
        
    Returns:
        Plan details with pricing and entitlements
    """
    try:
        plan = IndividualPlan(plan_id)
        pricing = INDIVIDUAL_PRICES[plan]
        entitlements = INDIVIDUAL_ENTITLEMENTS[plan]
        
        return {
            "id": plan.value,
            "name": pricing["name"],
            "tagline": pricing["tagline"],
            "price_monthly_usd": float(pricing["monthly_usd"]),
            "features": entitlements,
        }
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown plan: {plan_id}")


@router.get("/venue/{plan_id}")
async def get_venue_plan(plan_id: str):
    """
    Get details for a specific venue plan.
    
    Args:
        plan_id: Plan identifier (venue_scoring_pro, venue_broadcast_plus, league_license)
        
    Returns:
        Plan details with pricing and entitlements
    """
    try:
        plan = VenuePlan(plan_id)
        pricing = VENUE_PRICES[plan]
        entitlements = VENUE_ENTITLEMENTS[plan]
        
        return {
            "id": plan.value,
            "name": pricing["name"],
            "tagline": pricing["tagline"],
            "price_monthly_usd": float(pricing["monthly_usd"]) if pricing["monthly_usd"] is not None else None,
            "contact_for_pricing": pricing["monthly_usd"] is None,
            "features": entitlements,
        }
    except ValueError:
        raise HTTPException(status_code=404, detail=f"Unknown plan: {plan_id}")
