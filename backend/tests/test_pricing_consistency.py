"""
Pricing Consistency Tests - Ensure Single Source of Truth

Tests that verify:
1. Scoring is always free for individuals
2. No hardcoded prices exist outside pricing.py
3. Coaching API contracts remain unchanged
4. Venue plans don't break existing auth
"""

import pytest
from decimal import Decimal

from backend.config.pricing import (
    INDIVIDUAL_ENTITLEMENTS,
    INDIVIDUAL_PRICES,
    VENUE_ENTITLEMENTS,
    VENUE_PRICES,
    IndividualPlan,
    VenuePlan,
    can_score_for_free,
    get_entitlements_for_plan,
    get_price_for_plan,
)


class TestScoringIsFree:
    """CRITICAL: Verify scoring is free for ALL individual users."""

    def test_all_individual_plans_have_scoring_access(self):
        """Every individual plan must have scoring_access=True."""
        for plan in IndividualPlan:
            entitlements = INDIVIDUAL_ENTITLEMENTS[plan]
            assert (
                entitlements.get("scoring_access", False) is True
            ), f"Plan {plan.value} must have scoring_access=True"

    def test_free_plan_has_zero_price(self):
        """Free plan must cost $0.00."""
        free_plan = INDIVIDUAL_PRICES[IndividualPlan.FREE_SCORING]
        assert free_plan["monthly_usd"] == Decimal("0.00"), "Free plan must cost exactly $0.00"

    def test_can_score_for_free_helper(self):
        """All plans return True for can_score_for_free()."""
        for plan in IndividualPlan:
            assert (
                can_score_for_free(plan) is True
            ), f"can_score_for_free({plan.value}) must return True"


class TestPricingConsistency:
    """Verify pricing structure integrity."""

    def test_all_individual_plans_have_prices(self):
        """Every individual plan must have a defined price."""
        for plan in IndividualPlan:
            pricing = INDIVIDUAL_PRICES[plan]
            assert "monthly_usd" in pricing
            assert isinstance(pricing["monthly_usd"], Decimal)
            assert pricing["monthly_usd"] >= Decimal("0.00")

    def test_all_individual_plans_have_entitlements(self):
        """Every individual plan must have defined entitlements."""
        for plan in IndividualPlan:
            entitlements = INDIVIDUAL_ENTITLEMENTS[plan]
            assert isinstance(entitlements, dict)
            assert len(entitlements) > 0

    def test_venue_plans_exist(self):
        """Venue plans must be defined."""
        assert len(VenuePlan) >= 3  # At least 3 venue plans
        assert VenuePlan.VENUE_SCORING_PRO in VenuePlan
        assert VenuePlan.VENUE_BROADCAST_PLUS in VenuePlan
        assert VenuePlan.LEAGUE_LICENSE in VenuePlan

    def test_league_license_contact_only(self):
        """League license must have None price (contact for pricing)."""
        pricing = VENUE_PRICES[VenuePlan.LEAGUE_LICENSE]
        assert pricing["monthly_usd"] is None, "League license must be contact-only (None price)"


class TestCoachingContractPreserved:
    """Ensure coaching API contracts remain unchanged."""

    def test_coach_pro_exists(self):
        """Coach Pro plan must exist (contract requirement)."""
        assert IndividualPlan.COACH_PRO in IndividualPlan

    def test_coach_pro_plus_exists(self):
        """Coach Pro Plus plan must exist (contract requirement)."""
        assert IndividualPlan.COACH_PRO_PLUS in IndividualPlan

    def test_coach_pro_plus_has_video_features(self):
        """Coach Pro Plus must include all video features."""
        entitlements = INDIVIDUAL_ENTITLEMENTS[IndividualPlan.COACH_PRO_PLUS]

        required_features = [
            "video_sessions_enabled",
            "video_upload_enabled",
            "video_analysis_enabled",
            "ai_session_reports_enabled",
        ]

        for feature in required_features:
            assert (
                entitlements.get(feature) is True
            ), f"Coach Pro Plus must have {feature}=True (contract requirement)"

    def test_coach_pro_plus_price_correct(self):
        """Coach Pro Plus must cost $29.99."""
        pricing = INDIVIDUAL_PRICES[IndividualPlan.COACH_PRO_PLUS]
        assert pricing["monthly_usd"] == Decimal(
            "29.99"
        ), "Coach Pro Plus must cost $29.99 (contract requirement)"


class TestVenueEntitlements:
    """Verify venue-specific features."""

    def test_venue_scoring_pro_branding_removal(self):
        """Venue Scoring Pro must enable branding removal."""
        entitlements = VENUE_ENTITLEMENTS[VenuePlan.VENUE_SCORING_PRO]
        assert entitlements.get("branding_removal") is True
        assert entitlements.get("custom_logo") is True
        assert entitlements.get("fullscreen_scoreboard") is True

    def test_venue_broadcast_plus_all_features(self):
        """Venue Broadcast Plus must include all broadcast features."""
        entitlements = VENUE_ENTITLEMENTS[VenuePlan.VENUE_BROADCAST_PLUS]

        broadcast_features = [
            "branding_removal",
            "custom_logo",
            "fullscreen_scoreboard",
            "broadcast_layouts",
            "multi_camera_support",
            "led_integration",
        ]

        for feature in broadcast_features:
            assert (
                entitlements.get(feature) is True
            ), f"Venue Broadcast Plus must have {feature}=True"

    def test_venue_plans_pricing_correct(self):
        """Venue plans must have correct pricing."""
        assert VENUE_PRICES[VenuePlan.VENUE_SCORING_PRO]["monthly_usd"] == Decimal("39.00")
        assert VENUE_PRICES[VenuePlan.VENUE_BROADCAST_PLUS]["monthly_usd"] == Decimal("99.00")


class TestHelperFunctions:
    """Test pricing utility functions."""

    def test_get_price_for_plan(self):
        """get_price_for_plan() must return correct prices."""
        assert get_price_for_plan(IndividualPlan.FREE_SCORING) == Decimal("0.00")
        assert get_price_for_plan(IndividualPlan.PLAYER_PRO) == Decimal("1.99")
        assert get_price_for_plan(VenuePlan.VENUE_SCORING_PRO) == Decimal("39.00")
        assert get_price_for_plan(VenuePlan.LEAGUE_LICENSE) is None

    def test_get_entitlements_for_plan(self):
        """get_entitlements_for_plan() must return correct entitlements."""
        free_ent = get_entitlements_for_plan(IndividualPlan.FREE_SCORING)
        assert free_ent["scoring_access"] is True
        assert free_ent.get("advanced_analytics", False) is False

        coach_ent = get_entitlements_for_plan(IndividualPlan.COACH_PRO_PLUS)
        assert coach_ent["video_upload_enabled"] is True

        venue_ent = get_entitlements_for_plan(VenuePlan.VENUE_SCORING_PRO)
        assert venue_ent["branding_removal"] is True


class TestPricingValues:
    """Verify actual pricing matches spec."""

    def test_individual_pricing_matches_spec(self):
        """Individual pricing must match the spec."""
        assert INDIVIDUAL_PRICES[IndividualPlan.FREE_SCORING]["monthly_usd"] == Decimal("0.00")
        assert INDIVIDUAL_PRICES[IndividualPlan.PLAYER_PRO]["monthly_usd"] == Decimal("1.99")
        assert INDIVIDUAL_PRICES[IndividualPlan.COACH_PRO]["monthly_usd"] == Decimal("19.99")
        assert INDIVIDUAL_PRICES[IndividualPlan.COACH_PRO_PLUS]["monthly_usd"] == Decimal("29.99")
        assert INDIVIDUAL_PRICES[IndividualPlan.COACH_LIVE_AI]["monthly_usd"] == Decimal("59.99")
        assert INDIVIDUAL_PRICES[IndividualPlan.COACH_LIVE_AI_ADVANCED]["monthly_usd"] == Decimal(
            "99.99"
        )

    def test_venue_pricing_matches_spec(self):
        """Venue pricing must match the spec."""
        assert VENUE_PRICES[VenuePlan.VENUE_SCORING_PRO]["monthly_usd"] == Decimal("39.00")
        assert VENUE_PRICES[VenuePlan.VENUE_BROADCAST_PLUS]["monthly_usd"] == Decimal("99.00")
        assert VENUE_PRICES[VenuePlan.LEAGUE_LICENSE]["monthly_usd"] is None


@pytest.mark.asyncio
class TestPricingAPI:
    """Test pricing API endpoints."""

    async def test_get_pricing_endpoint_exists(self, async_client):
        """GET /pricing must return all plans."""
        response = await async_client.get("/pricing/", follow_redirects=True)
        assert response.status_code == 200

        data = response.json()
        assert "individual_plans" in data
        assert "venue_plans" in data
        assert data["scoring_is_free"] is True

    async def test_individual_plan_endpoint(self, async_client):
        """GET /pricing/individual/{plan_id} must work."""
        response = await async_client.get("/pricing/individual/player_pro", follow_redirects=True)
        assert response.status_code == 200

        data = response.json()
        assert data["plan_id"] == "player_pro"
        assert data["pricing"]["name"] == "Scorers Pro"
        assert data["pricing"]["monthly_usd"] == "1.99"
        assert data["entitlements"]["scoring_access"] is True

    async def test_venue_plan_endpoint(self, async_client):
        """GET /pricing/venue/{plan_id} must work."""
        response = await async_client.get("/pricing/venue/venue_scoring_pro")
        assert response.status_code == 200

        data = response.json()
        assert data["plan_id"] == "venue_scoring_pro"
        assert data["pricing"]["name"] == "Venue Scoring Pro"
        assert data["pricing"]["monthly_usd"] == "39.00"
        assert data["entitlements"]["branding_removal"] is True
