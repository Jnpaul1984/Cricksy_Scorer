"""
Canonical Pricing Configuration - Single Source of Truth

CRITICAL: This is the ONLY place where prices should be defined.
Do NOT hardcode prices anywhere else in the codebase.

Last Updated: 2026-01-04
Contract Version: 1.0.0
"""

from __future__ import annotations

from decimal import Decimal
from enum import Enum
from typing import TypedDict

# =============================================================================
# INDIVIDUAL PLANS - Player & Coach Focused
# =============================================================================

class IndividualPlan(str, Enum):
    """Individual user subscription plans."""
    FREE_SCORING = "free"
    PLAYER_PRO = "player_pro"
    COACH_PRO = "coach_pro"
    COACH_PRO_PLUS = "coach_pro_plus"
    COACH_LIVE_AI = "coach_live_ai"
    COACH_LIVE_AI_ADVANCED = "coach_live_ai_advanced"
    ANALYST_PRO = "analyst_pro"
    ORG_PRO = "org_pro"


class IndividualPricing(TypedDict):
    """Pricing structure for individual plans."""
    monthly_usd: Decimal
    name: str
    tagline: str


INDIVIDUAL_PRICES: dict[IndividualPlan, IndividualPricing] = {
    IndividualPlan.FREE_SCORING: {
        "monthly_usd": Decimal("0.00"),
        "name": "Free Scoring",
        "tagline": "Scoring is always free for individuals",
    },
    IndividualPlan.PLAYER_PRO: {
        "monthly_usd": Decimal("1.99"),
        "name": "Scorers Pro",
        "tagline": "Profile, stats, and exports for social media",
    },
    IndividualPlan.COACH_PRO: {
        "monthly_usd": Decimal("19.99"),
        "name": "Coach Pro",
        "tagline": "Team management and coaching tools",
    },
    IndividualPlan.COACH_PRO_PLUS: {
        "monthly_usd": Decimal("29.99"),
        "name": "Coach Pro Plus",
        "tagline": "Video analysis, session notes, and advanced metrics",
    },
    IndividualPlan.COACH_LIVE_AI: {
        "monthly_usd": Decimal("59.99"),
        "name": "Coach Live AI",
        "tagline": "Real-time AI commentary and live insights",
    },
    IndividualPlan.COACH_LIVE_AI_ADVANCED: {
        "monthly_usd": Decimal("99.99"),
        "name": "Coach Live AI Advanced",
        "tagline": "Premium AI with predictive analytics and automation",
    },
    IndividualPlan.ANALYST_PRO: {
        "monthly_usd": Decimal("29.99"),
        "name": "Analyst Pro",
        "tagline": "Deep stats and unlimited exports",
    },
    IndividualPlan.ORG_PRO: {
        "monthly_usd": Decimal("99.99"),
        "name": "Organization Pro",
        "tagline": "Multi-team management and unlimited everything",
    },
}


# =============================================================================
# VENUE PLANS - Ground/Facility Focused
# =============================================================================

class VenuePlan(str, Enum):
    """Venue/ground subscription plans."""
    VENUE_SCORING_PRO = "venue_scoring_pro"
    VENUE_BROADCAST_PLUS = "venue_broadcast_plus"
    LEAGUE_LICENSE = "league_license"


class VenuePricing(TypedDict):
    """Pricing structure for venue plans."""
    monthly_usd: Decimal | None  # None = contact for pricing
    name: str
    tagline: str


VENUE_PRICES: dict[VenuePlan, VenuePricing] = {
    VenuePlan.VENUE_SCORING_PRO: {
        "monthly_usd": Decimal("39.00"),
        "name": "Venue Scoring Pro",
        "tagline": "Branding removal, custom logos, fullscreen scoreboard",
    },
    VenuePlan.VENUE_BROADCAST_PLUS: {
        "monthly_usd": Decimal("99.00"),
        "name": "Venue Broadcast Plus",
        "tagline": "Broadcast layouts, multi-camera, LED integration",
    },
    VenuePlan.LEAGUE_LICENSE: {
        "monthly_usd": None,  # Contact only
        "name": "League License",
        "tagline": "Custom pricing for leagues and tournament organizers",
    },
}


# =============================================================================
# FEATURE ENTITLEMENTS - What Each Plan Unlocks
# =============================================================================

class FeatureEntitlements(TypedDict, total=False):
    """Feature flags for each subscription plan."""
    # Core Scoring (FREE for individuals)
    live_scoring: bool
    scoring_access: bool
    
    # AI & Analytics
    ai_predictions: bool
    ai_reports_per_month: int | None  # None = unlimited
    tokens_limit: int | None  # None = unlimited
    advanced_analytics: bool
    
    # Data & Export
    export_pdf: bool
    export_csv: bool
    max_games: int | None  # None = unlimited
    max_tournaments: int | None  # None = unlimited
    
    # Coaching Features
    coach_dashboard: bool
    coaching_sessions: bool
    player_assignments: bool
    coaching_notes: bool
    video_sessions_enabled: bool
    video_upload_enabled: bool
    video_analysis_enabled: bool
    ai_session_reports_enabled: bool
    video_storage_gb: int | None  # None = unlimited (org plans)
    max_video_duration_seconds: int | None  # Per upload, None = unlimited
    
    # Organization
    team_management: bool
    priority_support: bool
    
    # Venue/Broadcast (Ground-level)
    branding_removal: bool
    custom_logo: bool
    fullscreen_scoreboard: bool
    broadcast_layouts: bool
    multi_camera_support: bool
    led_integration: bool
    custom_overlays: bool


# Individual Plan Entitlements
INDIVIDUAL_ENTITLEMENTS: dict[IndividualPlan, FeatureEntitlements] = {
    IndividualPlan.FREE_SCORING: {
        "live_scoring": True,
        "scoring_access": True,  # CRITICAL: Always true
        "ai_predictions": True,
        "ai_reports_per_month": 5,
        "tokens_limit": 10_000,
        "max_games": 10,
        "max_tournaments": 1,
        "export_pdf": False,
        "export_csv": False,
        "advanced_analytics": False,
        "team_management": False,
        "priority_support": False,
    },
    IndividualPlan.PLAYER_PRO: {
        "live_scoring": True,
        "scoring_access": True,  # CRITICAL: Always true
        "ai_predictions": True,
        "ai_reports_per_month": 15,  # Reduced for Scorers Pro
        "tokens_limit": 30_000,  # Reduced for Scorers Pro
        "max_games": None,  # Unlimited
        "max_tournaments": None,  # Unlimited for stats/exports
        "export_pdf": True,
        "export_csv": True,
        "advanced_analytics": True,  # Full stats for social media
        "team_management": False,
        "priority_support": False,
    },
    IndividualPlan.COACH_PRO: {
        "live_scoring": True,
        "scoring_access": True,  # CRITICAL: Always true
        "ai_predictions": True,
        "ai_reports_per_month": 100,
        "tokens_limit": 100_000,
        "max_games": None,
        "max_tournaments": 50,
        "export_pdf": True,
        "export_csv": True,
        "advanced_analytics": True,
        "team_management": True,
        "priority_support": True,
        "coach_dashboard": True,
        "coaching_sessions": False,
        "coaching_notes": True,
    },
    IndividualPlan.COACH_PRO_PLUS: {
        "live_scoring": True,
        "scoring_access": True,  # CRITICAL: Always true
        "ai_predictions": True,
        "ai_reports_per_month": 100,
        "tokens_limit": 100_000,
        "max_games": None,
        "max_tournaments": 50,
        "export_pdf": True,
        "export_csv": True,
        "advanced_analytics": True,
        "team_management": True,
        "priority_support": True,
        "coach_dashboard": True,
        "coaching_sessions": True,
        "player_assignments": True,
        "coaching_notes": True,
        "video_sessions_enabled": True,
        "video_upload_enabled": True,
        "video_analysis_enabled": True,
        "ai_session_reports_enabled": True,
        "video_storage_gb": 25,
        "max_video_duration_seconds": 7200,  # 2 hours per upload
    },
    IndividualPlan.COACH_LIVE_AI: {
        "live_scoring": True,
        "scoring_access": True,
        "ai_predictions": True,
        "ai_reports_per_month": 200,
        "tokens_limit": 250_000,
        "max_games": None,
        "max_tournaments": None,
        "export_pdf": True,
        "export_csv": True,
        "advanced_analytics": True,
        "team_management": True,
        "priority_support": True,
        "coach_dashboard": True,
        "coaching_sessions": True,
        "player_assignments": True,
        "coaching_notes": True,
        "video_sessions_enabled": True,
        "video_upload_enabled": True,
        "video_analysis_enabled": True,
        "ai_session_reports_enabled": True,
        "video_storage_gb": 50,
        "max_video_duration_seconds": 10800,  # 3 hours per upload
    },
    IndividualPlan.COACH_LIVE_AI_ADVANCED: {
        "live_scoring": True,
        "scoring_access": True,
        "ai_predictions": True,
        "ai_reports_per_month": None,  # Unlimited
        "tokens_limit": None,  # Unlimited
        "max_games": None,
        "max_tournaments": None,
        "export_pdf": True,
        "export_csv": True,
        "advanced_analytics": True,
        "team_management": True,
        "priority_support": True,
        "coach_dashboard": True,
        "coaching_sessions": True,
        "player_assignments": True,
        "coaching_notes": True,
        "video_sessions_enabled": True,
        "video_upload_enabled": True,
        "video_analysis_enabled": True,
        "ai_session_reports_enabled": True,
        "video_storage_gb": 100,
        "max_video_duration_seconds": None,  # Unlimited
    },
    IndividualPlan.ANALYST_PRO: {
        "live_scoring": True,
        "scoring_access": True,
        "ai_predictions": True,
        "ai_reports_per_month": 200,
        "tokens_limit": 100_000,
        "max_games": None,
        "max_tournaments": None,
        "export_pdf": True,
        "export_csv": True,
        "advanced_analytics": True,
        "team_management": True,
        "priority_support": True,
    },
    IndividualPlan.ORG_PRO: {
        "live_scoring": True,
        "scoring_access": True,
        "ai_predictions": True,
        "ai_reports_per_month": None,  # Unlimited
        "tokens_limit": None,  # Unlimited
        "max_games": None,
        "max_tournaments": None,
        "export_pdf": True,
        "export_csv": True,
        "advanced_analytics": True,
        "team_management": True,
        "priority_support": True,
        "coach_dashboard": True,
        "coaching_sessions": True,
        "player_assignments": True,
        "coaching_notes": True,
        "video_sessions_enabled": True,
        "video_upload_enabled": True,
        "video_analysis_enabled": True,
        "ai_session_reports_enabled": True,
        "video_storage_gb": None,  # Unlimited for organizations (fair-use policy applies)
        "max_video_duration_seconds": None,  # Unlimited
    },
}


# Venue Plan Entitlements
VENUE_ENTITLEMENTS: dict[VenuePlan, FeatureEntitlements] = {
    VenuePlan.VENUE_SCORING_PRO: {
        "live_scoring": True,
        "scoring_access": True,
        "branding_removal": True,
        "custom_logo": True,
        "fullscreen_scoreboard": True,
        "broadcast_layouts": False,
        "multi_camera_support": False,
        "led_integration": False,
    },
    VenuePlan.VENUE_BROADCAST_PLUS: {
        "live_scoring": True,
        "scoring_access": True,
        "branding_removal": True,
        "custom_logo": True,
        "fullscreen_scoreboard": True,
        "broadcast_layouts": True,
        "multi_camera_support": True,
        "led_integration": True,
        "custom_overlays": True,
    },
    VenuePlan.LEAGUE_LICENSE: {
        # Custom negotiated - defer to contract
        "live_scoring": True,
        "scoring_access": True,
        "branding_removal": True,
        "custom_logo": True,
        "fullscreen_scoreboard": True,
        "broadcast_layouts": True,
        "multi_camera_support": True,
        "led_integration": True,
        "custom_overlays": True,
    },
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def get_price_for_plan(plan: IndividualPlan | VenuePlan) -> Decimal | None:
    """
    Get monthly price for any plan.
    
    Args:
        plan: Plan enum value
        
    Returns:
        Monthly price in USD, or None for contact-only pricing
    """
    if isinstance(plan, IndividualPlan):
        return INDIVIDUAL_PRICES[plan]["monthly_usd"]
    elif isinstance(plan, VenuePlan):
        return VENUE_PRICES[plan]["monthly_usd"]
    return None


def get_entitlements_for_plan(plan: IndividualPlan | VenuePlan) -> FeatureEntitlements:
    """
    Get feature entitlements for any plan.
    
    Args:
        plan: Plan enum value
        
    Returns:
        Dictionary of feature flags
    """
    if isinstance(plan, IndividualPlan):
        return INDIVIDUAL_ENTITLEMENTS[plan].copy()
    elif isinstance(plan, VenuePlan):
        return VENUE_ENTITLEMENTS[plan].copy()
    return {}


def get_video_storage_bytes(plan: IndividualPlan | VenuePlan) -> int | None:
    """
    Get video storage quota in bytes for a plan.
    
    Args:
        plan: Plan enum value
        
    Returns:
        Storage quota in bytes, or None for unlimited
    """
    entitlements = get_entitlements_for_plan(plan)
    storage_gb = entitlements.get("video_storage_gb")
    
    if storage_gb is None:
        return None  # Unlimited
    if storage_gb == 0:
        return 0  # No video access
    
    return int(storage_gb * 1024 * 1024 * 1024)  # Convert GB to bytes


def get_complete_plan_details(plan: IndividualPlan | VenuePlan) -> dict:
    """
    Get complete plan details including pricing, entitlements, and computed values.
    
    Args:
        plan: Plan enum value
        
    Returns:
        Dictionary with plan_id, display_name, price_monthly_usd, 
        video_storage_bytes, and all feature_flags
    """
    price_info: IndividualPricing | VenuePricing = (
        INDIVIDUAL_PRICES[plan] if isinstance(plan, IndividualPlan)  # type: ignore[index]
        else VENUE_PRICES[plan]  # type: ignore[index]
    )
    entitlements = get_entitlements_for_plan(plan)
    
    return {
        "plan_id": plan.value,
        "display_name": price_info["name"],
        "price_monthly_usd": (
            float(price_info["monthly_usd"])  # type: ignore[arg-type]
            if price_info["monthly_usd"] else None
        ),
        "video_storage_bytes": get_video_storage_bytes(plan),
        "max_video_duration_seconds": entitlements.get("max_video_duration_seconds"),
        "ai_reports_per_month": entitlements.get("ai_reports_per_month"),
        "feature_flags": entitlements,
    }


def can_score_for_free(plan: IndividualPlan) -> bool:
    """
    Verify that scoring is always free for individuals.
    
    Args:
        plan: Individual plan enum
        
    Returns:
        True (always - scoring is free for all individual users)
    """
    entitlements = INDIVIDUAL_ENTITLEMENTS.get(plan, {})
    return entitlements.get("scoring_access", True)  # Default True for safety


# =============================================================================
# MIGRATION NOTES
# =============================================================================
"""
PRICING REFACTOR - Single Source of Truth

✅ Created backend/config/pricing.py as single source of truth
✅ All plans have standardized structure (plan_id, display_name, price, features)
✅ Refactored billing_service.py to derive PLAN_FEATURES from config
✅ Updated tests to reference config instead of hardcoding values
✅ Added snapshot test for pricing contract validation
✅ Video quotas and duration limits now centralized

CRITICAL GUARANTEES:
1. Scoring is ALWAYS free for individuals (scoring_access=True)
2. Coaching API contract unchanged (coach_pro, coach_pro_plus preserved)
3. Org plans have unlimited storage and duration (fair-use policy applies)

FAIR-USE POLICY:
Organization Pro plans have unlimited video storage and upload duration.
This is subject to fair-use guidelines:
- Intended for legitimate cricket coaching and analysis
- Excessive abuse (>1TB/month or >100hrs/upload) may trigger review
- Commercial redistribution is prohibited
- Storage quotas may be introduced in future with grandfathering

VIDEO DURATION LIMITS PER UPLOAD:
- Coach Pro Plus: 2 hours (7200 seconds)
- Coach Live AI: 3 hours (10800 seconds)  
- Coach Live AI Advanced: Unlimited
- Organization Pro: Unlimited
"""
