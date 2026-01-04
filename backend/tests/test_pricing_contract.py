"""
Test pricing configuration contract and consistency.

This test ensures all plans have required fields and proper types,
serving as a snapshot of the pricing structure.
"""

from __future__ import annotations

from backend.config.pricing import (
    INDIVIDUAL_ENTITLEMENTS,
    INDIVIDUAL_PRICES,
    IndividualPlan,
    get_complete_plan_details,
    get_video_storage_bytes,
)
from backend.services.billing_service import PLAN_FEATURES, get_plan_features


class TestPricingContract:
    """Test that all plans conform to the required structure."""

    def test_all_individual_plans_have_required_fields(self) -> None:
        """Validate that every individual plan has all required fields."""
        required_fields = {
            "plan_id",
            "display_name",
            "price_monthly_usd",
            "video_storage_bytes",
            "max_video_duration_seconds",
            "ai_reports_per_month",
            "feature_flags",
        }

        for plan in IndividualPlan:
            details = get_complete_plan_details(plan)

            # Check all required fields exist
            assert set(details.keys()) == required_fields, (
                f"Plan {plan.value} missing required fields. "
                f"Expected: {required_fields}, Got: {set(details.keys())}"
            )

            # Validate field types
            assert isinstance(details["plan_id"], str)
            assert isinstance(details["display_name"], str)
            assert details["price_monthly_usd"] is None or isinstance(
                details["price_monthly_usd"], float
            )
            assert details["video_storage_bytes"] is None or isinstance(
                details["video_storage_bytes"], int
            )
            assert details["max_video_duration_seconds"] is None or isinstance(
                details["max_video_duration_seconds"], int
            )
            assert details["ai_reports_per_month"] is None or isinstance(
                details["ai_reports_per_month"], int
            )
            assert isinstance(details["feature_flags"], dict)

    def test_org_pro_has_unlimited_storage(self) -> None:
        """Verify that org_pro has unlimited video storage."""
        org_details = get_complete_plan_details(IndividualPlan.ORG_PRO)
        assert org_details["video_storage_bytes"] is None, "Org Pro should have unlimited storage"
        assert org_details["max_video_duration_seconds"] is None, (
            "Org Pro should have unlimited duration"
        )

        # Also test via get_video_storage_bytes
        storage = get_video_storage_bytes(IndividualPlan.ORG_PRO)
        assert storage is None, "get_video_storage_bytes should return None for org_pro"

    def test_free_plan_has_no_video_features(self) -> None:
        """Verify free plan doesn't have video upload enabled."""
        free_details = get_complete_plan_details(IndividualPlan.FREE_SCORING)
        features = free_details["feature_flags"]

        assert features.get("video_upload_enabled", False) is False, (
            "Free plan should not allow video uploads"
        )
        assert features.get("video_sessions_enabled", False) is False, (
            "Free plan should not have video sessions"
        )

    def test_coach_pro_plus_video_quota(self) -> None:
        """Verify coach_pro_plus has expected video storage quota."""
        details = get_complete_plan_details(IndividualPlan.COACH_PRO_PLUS)

        # 25 GB in bytes
        expected_bytes = 25 * 1024 * 1024 * 1024
        assert details["video_storage_bytes"] == expected_bytes, (
            "Coach Pro Plus should have 25GB storage"
        )

        # 2 hours in seconds
        expected_duration = 7200
        assert details["max_video_duration_seconds"] == expected_duration, (
            "Coach Pro Plus should allow 2 hour videos"
        )

    def test_plan_features_backward_compatibility(self) -> None:
        """Test that PLAN_FEATURES exports all plans for backward compatibility."""
        # Should contain all individual plan IDs
        for plan in IndividualPlan:
            assert plan.value in PLAN_FEATURES, f"PLAN_FEATURES missing {plan.value}"

        # Each entry should have complete details
        for plan_id, details in PLAN_FEATURES.items():
            assert "plan_id" in details
            assert "display_name" in details
            assert "price_monthly_usd" in details
            assert details["plan_id"] == plan_id

    def test_get_plan_features_returns_complete_details(self) -> None:
        """Test get_plan_features() function returns expected structure."""
        details = get_plan_features("coach_pro_plus")

        assert details["plan_id"] == "coach_pro_plus"
        assert details["display_name"] == "Coach Pro Plus"
        assert isinstance(details["price_monthly_usd"], float)
        assert "feature_flags" in details
        assert "ai_reports_per_month" in details

    def test_pricing_snapshot(self) -> None:
        """
        Snapshot test for current pricing structure.

        Update this test when prices intentionally change.
        """
        from decimal import Decimal

        # Individual plans pricing
        assert INDIVIDUAL_PRICES[IndividualPlan.FREE_SCORING]["monthly_usd"] == Decimal("0.00")
        assert INDIVIDUAL_PRICES[IndividualPlan.PLAYER_PRO]["monthly_usd"] == Decimal("1.99")
        assert INDIVIDUAL_PRICES[IndividualPlan.COACH_PRO]["monthly_usd"] == Decimal("19.99")
        assert INDIVIDUAL_PRICES[IndividualPlan.COACH_PRO_PLUS]["monthly_usd"] == Decimal("29.99")
        assert INDIVIDUAL_PRICES[IndividualPlan.COACH_LIVE_AI]["monthly_usd"] == Decimal("59.99")
        assert INDIVIDUAL_PRICES[IndividualPlan.COACH_LIVE_AI_ADVANCED]["monthly_usd"] == Decimal(
            "99.99"
        )
        assert INDIVIDUAL_PRICES[IndividualPlan.ANALYST_PRO]["monthly_usd"] == Decimal("29.99")
        assert INDIVIDUAL_PRICES[IndividualPlan.ORG_PRO]["monthly_usd"] == Decimal("99.99")

    def test_entitlements_snapshot(self) -> None:
        """
        Snapshot test for current entitlements.

        Update this test when features intentionally change.
        """
        # Coach Pro Plus entitlements
        cpp = INDIVIDUAL_ENTITLEMENTS[IndividualPlan.COACH_PRO_PLUS]
        assert cpp["ai_reports_per_month"] == 100
        assert cpp["video_storage_gb"] == 25
        assert cpp["max_video_duration_seconds"] == 7200
        assert cpp["video_upload_enabled"] is True

        # Org Pro unlimited
        org = INDIVIDUAL_ENTITLEMENTS[IndividualPlan.ORG_PRO]
        assert org["ai_reports_per_month"] is None  # Unlimited
        assert org["video_storage_gb"] is None  # Unlimited
        assert org["max_video_duration_seconds"] is None  # Unlimited

    def test_all_video_plans_have_duration_limits(self) -> None:
        """Verify all plans with video upload have max_video_duration_seconds defined."""
        for plan in IndividualPlan:
            entitlements = INDIVIDUAL_ENTITLEMENTS[plan]

            if entitlements.get("video_upload_enabled"):
                # If video upload is enabled, duration limit must be defined (even if None for unlimited)
                assert "max_video_duration_seconds" in entitlements, (
                    f"Plan {plan.value} has video_upload_enabled but no max_video_duration_seconds"
                )

    def test_scoring_always_free(self) -> None:
        """Verify that scoring_access is True for all individual plans."""
        for plan in IndividualPlan:
            entitlements = INDIVIDUAL_ENTITLEMENTS[plan]
            assert entitlements.get("scoring_access") is True, (
                f"Plan {plan.value} must have scoring_access=True (scoring is free for individuals)"
            )
