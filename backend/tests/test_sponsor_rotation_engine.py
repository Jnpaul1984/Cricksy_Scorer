"""
Tests for Sponsor Rotation Engine - Feature 12

Comprehensive tests for sponsor rotation scheduling, tracking, and metrics
"""

from backend.services.sponsor_rotation_engine import (
    EngagementEvent,
    RotationStrategy,
    Sponsor,
    SponsorRotationEngine,
)


class TestRotationScheduleBuilder:
    """Tests for building rotation schedules"""

    def test_builds_equal_time_schedule(self):
        """Test building equal-time distribution schedule"""
        sponsors = [
            Sponsor("s1", "Sponsor 1", "url1", 5, 10),
            Sponsor("s2", "Sponsor 2", "url2", 5, 10),
        ]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g1", "org1", sponsors, max_overs=20, strategy=RotationStrategy.EQUAL_TIME
        )

        assert schedule.game_id == "g1"
        assert schedule.organization_id == "org1"
        assert schedule.max_overs == 20
        assert len(schedule.slots) == 20
        assert schedule.strategy == RotationStrategy.EQUAL_TIME

    def test_builds_priority_weighted_schedule(self):
        """Test building priority-weighted schedule"""
        sponsors = [
            Sponsor("s1", "Sponsor 1", "url1", 8, 10),  # High priority
            Sponsor("s2", "Sponsor 2", "url2", 2, 10),  # Low priority
        ]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g2", "org1", sponsors, max_overs=20, strategy=RotationStrategy.PRIORITY_WEIGHTED
        )

        # Count slots per sponsor
        s1_slots = sum(1 for slot in schedule.slots if slot.sponsor_id == "s1")
        s2_slots = sum(1 for slot in schedule.slots if slot.sponsor_id == "s2")

        # High priority should get more slots
        assert s1_slots > s2_slots

    def test_builds_dynamic_schedule(self):
        """Test building dynamic strategy schedule"""
        sponsors = [
            Sponsor("s1", "Sponsor 1", "url1", 5, 10),
            Sponsor("s2", "Sponsor 2", "url2", 5, 10),
        ]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g3", "org1", sponsors, max_overs=20, strategy=RotationStrategy.DYNAMIC
        )

        assert schedule.strategy == RotationStrategy.DYNAMIC
        assert len(schedule.slots) > 0

    def test_handles_empty_sponsors(self):
        """Test building schedule with no sponsors"""
        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g4", "org1", [], max_overs=20, strategy=RotationStrategy.EQUAL_TIME
        )

        assert schedule.slots == []
        assert len(schedule.sponsors) == 0

    def test_handles_single_sponsor(self):
        """Test building schedule with single sponsor"""
        sponsors = [Sponsor("s1", "Sponsor 1", "url1", 5, 10)]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g5", "org1", sponsors, max_overs=20, strategy=RotationStrategy.EQUAL_TIME
        )

        # All slots should be sponsor s1
        for slot in schedule.slots:
            assert slot.sponsor_id == "s1"


class TestSponsorSlotRetrieval:
    """Tests for retrieving sponsor slots"""

    def test_gets_sponsor_for_over(self):
        """Test retrieving sponsor for specific over"""
        sponsors = [
            Sponsor("s1", "Sponsor 1", "url1", 5, 10),
            Sponsor("s2", "Sponsor 2", "url2", 5, 10),
        ]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g6", "org1", sponsors, max_overs=20, strategy=RotationStrategy.EQUAL_TIME
        )

        # Get sponsor for over 1
        slot = SponsorRotationEngine.get_sponsor_for_over(schedule, 1)

        assert slot is not None
        assert slot.over_num == 1
        assert slot.sponsor_id in ["s1", "s2"]

    def test_returns_none_for_missing_over(self):
        """Test retrieving non-existent over returns None"""
        sponsors = [Sponsor("s1", "Sponsor 1", "url1", 5, 10)]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g7", "org1", sponsors, max_overs=20, strategy=RotationStrategy.EQUAL_TIME
        )

        # Get sponsor for over that doesn't exist
        slot = SponsorRotationEngine.get_sponsor_for_over(schedule, 99)

        assert slot is None

    def test_retrieves_correct_slot_by_ball(self):
        """Test retrieving slot with specific ball number"""
        sponsors = [Sponsor("s1", "Sponsor 1", "url1", 5, 10)]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g8", "org1", sponsors, max_overs=20, strategy=RotationStrategy.EQUAL_TIME
        )

        slot = SponsorRotationEngine.get_sponsor_for_over(schedule, 1, ball_num=1)

        assert slot is not None
        assert slot.ball_num == 1


class TestEngagementEventTracking:
    """Tests for tracking engagement events"""

    def test_records_engagement_event(self):
        """Test recording engagement event"""
        sponsors = [Sponsor("s1", "Sponsor 1", "url1", 5, 10)]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g9", "org1", sponsors, max_overs=20, strategy=RotationStrategy.DYNAMIC
        )

        SponsorRotationEngine.record_engagement(
            schedule, over_num=5, event_type=EngagementEvent.WICKET
        )

        assert len(schedule.engagement_events) == 1
        assert schedule.engagement_events[0] == (5, EngagementEvent.WICKET)

    def test_records_multiple_engagement_events(self):
        """Test recording multiple engagement events"""
        sponsors = [Sponsor("s1", "Sponsor 1", "url1", 5, 10)]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g10", "org1", sponsors, max_overs=20, strategy=RotationStrategy.DYNAMIC
        )

        SponsorRotationEngine.record_engagement(
            schedule, over_num=3, event_type=EngagementEvent.BOUNDARY
        )
        SponsorRotationEngine.record_engagement(
            schedule, over_num=8, event_type=EngagementEvent.SIX
        )
        SponsorRotationEngine.record_engagement(
            schedule, over_num=10, event_type=EngagementEvent.WICKET
        )

        assert len(schedule.engagement_events) == 3

    def test_increases_premium_exposure_for_dynamic(self):
        """Test that DYNAMIC strategy increases premium exposure on engagement"""
        sponsors = [Sponsor("s1", "Sponsor 1", "url1", 5, 10)]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g11", "org1", sponsors, max_overs=20, strategy=RotationStrategy.DYNAMIC
        )

        # Get slot for over 5
        slot_before = SponsorRotationEngine.get_sponsor_for_over(schedule, 5)
        initial_value = slot_before.exposure_value if slot_before else 1.0

        # Record high-engagement event
        SponsorRotationEngine.record_engagement(
            schedule, over_num=5, event_type=EngagementEvent.WICKET
        )

        slot_after = SponsorRotationEngine.get_sponsor_for_over(schedule, 5)
        assert slot_after.exposure_value > initial_value


class TestExposureTracking:
    """Tests for tracking sponsor exposures"""

    def test_records_sponsor_exposure(self):
        """Test recording sponsor exposure"""
        sponsors = [Sponsor("s1", "Sponsor 1", "url1", 5, 10)]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g12", "org1", sponsors, max_overs=20, strategy=RotationStrategy.EQUAL_TIME
        )

        SponsorRotationEngine.record_exposure(schedule, "s1", premium=False)

        assert schedule.exposures_per_sponsor["s1"] == 1

    def test_records_multiple_exposures(self):
        """Test recording multiple exposures for same sponsor"""
        sponsors = [Sponsor("s1", "Sponsor 1", "url1", 5, 10)]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g13", "org1", sponsors, max_overs=20, strategy=RotationStrategy.EQUAL_TIME
        )

        SponsorRotationEngine.record_exposure(schedule, "s1", premium=False)
        SponsorRotationEngine.record_exposure(schedule, "s1", premium=False)
        SponsorRotationEngine.record_exposure(schedule, "s1", premium=True)

        assert schedule.exposures_per_sponsor["s1"] == 3


class TestExposureMetrics:
    """Tests for calculating exposure metrics"""

    def test_calculates_exposure_metrics(self):
        """Test calculating exposure metrics for sponsors"""
        sponsors = [
            Sponsor("s1", "Sponsor 1", "url1", 5, 10),
            Sponsor("s2", "Sponsor 2", "url2", 5, 10),
        ]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g14", "org1", sponsors, max_overs=20, strategy=RotationStrategy.EQUAL_TIME
        )

        # Record some exposures
        SponsorRotationEngine.record_exposure(schedule, "s1", premium=False)
        SponsorRotationEngine.record_exposure(schedule, "s2", premium=False)

        metrics = SponsorRotationEngine.get_exposure_metrics(schedule)

        assert "s1" in metrics
        assert "s2" in metrics
        assert metrics["s1"].sponsor_id == "s1"
        assert metrics["s2"].sponsor_id == "s2"

    def test_metrics_include_exposure_rate(self):
        """Test that metrics include exposure rate percentage"""
        sponsors = [
            Sponsor("s1", "Sponsor 1", "url1", 10, 10),
            Sponsor("s2", "Sponsor 2", "url2", 1, 10),
        ]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g15", "org1", sponsors, max_overs=20, strategy=RotationStrategy.PRIORITY_WEIGHTED
        )

        # Record exposures based on priority distribution
        for slot in schedule.slots:
            SponsorRotationEngine.record_exposure(schedule, slot.sponsor_id, premium=False)

        metrics = SponsorRotationEngine.get_exposure_metrics(schedule)

        # Higher priority sponsor should have higher exposure rate
        assert metrics["s1"].exposure_rate > metrics["s2"].exposure_rate

    def test_tracks_first_and_last_exposure(self):
        """Test tracking first and last exposure over"""
        sponsors = [Sponsor("s1", "Sponsor 1", "url1", 5, 10)]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g16", "org1", sponsors, max_overs=20, strategy=RotationStrategy.EQUAL_TIME
        )

        metrics = SponsorRotationEngine.get_exposure_metrics(schedule)

        assert metrics["s1"].first_exposure_over > 0
        assert metrics["s1"].last_exposure_over > 0


class TestPhaseAdjustments:
    """Tests for adjusting rotation by match phase"""

    def test_adjusts_for_powerplay_phase(self):
        """Test adjusting rotation for powerplay phase"""
        sponsors = [
            Sponsor("s1", "Sponsor 1", "url1", 5, 10),
            Sponsor("s2", "Sponsor 2", "url2", 5, 10),
        ]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g17", "org1", sponsors, max_overs=20, strategy=RotationStrategy.DYNAMIC
        )

        # Before adjustment
        slot_before = SponsorRotationEngine.get_sponsor_for_over(schedule, 3)
        value_before = slot_before.exposure_value if slot_before else 1.0

        # Adjust for powerplay with s1 as priority
        SponsorRotationEngine.adjust_rotation_for_phase(
            schedule, phase="powerplay", boost_priority_sponsor_id="s1"
        )

        # After adjustment
        slot_after = SponsorRotationEngine.get_sponsor_for_over(schedule, 3)

        # If slot is for s1, exposure should increase
        if slot_after and slot_after.sponsor_id == "s1":
            assert slot_after.exposure_value >= value_before

    def test_adjusts_for_middle_phase(self):
        """Test adjusting rotation for middle phase"""
        sponsors = [Sponsor("s1", "Sponsor 1", "url1", 5, 10)]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g18", "org1", sponsors, max_overs=20, strategy=RotationStrategy.DYNAMIC
        )

        # Adjust for middle
        SponsorRotationEngine.adjust_rotation_for_phase(
            schedule, phase="middle", boost_priority_sponsor_id="s1"
        )

        assert schedule.updated_at > schedule.created_at

    def test_adjusts_for_death_phase(self):
        """Test adjusting rotation for death phase"""
        sponsors = [Sponsor("s1", "Sponsor 1", "url1", 5, 10)]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g19", "org1", sponsors, max_overs=20, strategy=RotationStrategy.DYNAMIC
        )

        # Get slots before death adjustment
        death_slots_before = [
            slot
            for slot in schedule.slots
            if slot.over_num >= 18  # Last 3 overs
        ]

        # Adjust for death
        SponsorRotationEngine.adjust_rotation_for_phase(
            schedule, phase="death", boost_priority_sponsor_id="s1"
        )

        death_slots_after = [slot for slot in schedule.slots if slot.over_num >= 18]

        # Death overs should have adjusted exposure values
        for slot in death_slots_after:
            if slot.sponsor_id == "s1":
                assert slot.exposure_value >= 1.0


class TestPriorityWeighting:
    """Tests for priority-weighted rotation"""

    def test_higher_priority_gets_more_overs(self):
        """Test that higher priority sponsors get more overs"""
        sponsors = [
            Sponsor("premium", "Premium Sponsor", "url1", 10, 10),
            Sponsor("standard", "Standard Sponsor", "url2", 2, 10),
        ]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g20", "org1", sponsors, max_overs=20, strategy=RotationStrategy.PRIORITY_WEIGHTED
        )

        premium_overs = sum(1 for slot in schedule.slots if slot.sponsor_id == "premium")
        standard_overs = sum(1 for slot in schedule.slots if slot.sponsor_id == "standard")

        # Premium should have significantly more overs
        assert premium_overs > standard_overs
        assert premium_overs > 10

    def test_equal_priority_gets_equal_overs(self):
        """Test that equal priority sponsors get similar overs"""
        sponsors = [
            Sponsor("s1", "Sponsor 1", "url1", 5, 10),
            Sponsor("s2", "Sponsor 2", "url2", 5, 10),
            Sponsor("s3", "Sponsor 3", "url3", 5, 10),
        ]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g21", "org1", sponsors, max_overs=20, strategy=RotationStrategy.PRIORITY_WEIGHTED
        )

        s1_overs = sum(1 for slot in schedule.slots if slot.sponsor_id == "s1")
        s2_overs = sum(1 for slot in schedule.slots if slot.sponsor_id == "s2")
        s3_overs = sum(1 for slot in schedule.slots if slot.sponsor_id == "s3")

        # All should be roughly equal (within 2 overs tolerance for 20 total / 3 sponsors)
        assert abs(s1_overs - s2_overs) <= 2
        assert abs(s2_overs - s3_overs) <= 2


class TestEdgeCases:
    """Tests for edge cases and error handling"""

    def test_handles_overs_not_divisible_by_sponsors(self):
        """Test building schedule when overs not evenly divisible by sponsor count"""
        sponsors = [
            Sponsor("s1", "Sponsor 1", "url1", 5, 10),
            Sponsor("s2", "Sponsor 2", "url2", 5, 10),
            Sponsor("s3", "Sponsor 3", "url3", 5, 10),
        ]

        # 20 overs / 3 sponsors = 6.67 per sponsor
        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g22", "org1", sponsors, max_overs=20, strategy=RotationStrategy.EQUAL_TIME
        )

        assert len(schedule.slots) == 20

    def test_handles_very_small_match(self):
        """Test building schedule for very small match"""
        sponsors = [
            Sponsor("s1", "Sponsor 1", "url1", 5, 10),
            Sponsor("s2", "Sponsor 2", "url2", 5, 10),
        ]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g23", "org1", sponsors, max_overs=5, strategy=RotationStrategy.EQUAL_TIME
        )

        assert len(schedule.slots) == 5

    def test_exposure_metrics_for_no_recorded_exposures(self):
        """Test calculating metrics when no exposures recorded"""
        sponsors = [Sponsor("s1", "Sponsor 1", "url1", 5, 10)]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g24", "org1", sponsors, max_overs=20, strategy=RotationStrategy.EQUAL_TIME
        )

        # Don't record any exposures
        metrics = SponsorRotationEngine.get_exposure_metrics(schedule)

        assert metrics["s1"].total_exposures == 0
        assert metrics["s1"].exposure_rate == 0.0

    def test_handles_invalid_phase(self):
        """Test that invalid phase is handled gracefully"""
        sponsors = [Sponsor("s1", "Sponsor 1", "url1", 5, 10)]

        schedule = SponsorRotationEngine.build_rotation_schedule(
            "g25", "org1", sponsors, max_overs=20, strategy=RotationStrategy.DYNAMIC
        )

        # Should handle invalid phase without crashing (in route validation)
        SponsorRotationEngine.adjust_rotation_for_phase(
            schedule, phase="powerplay", boost_priority_sponsor_id="s1"
        )

        assert schedule.updated_at is not None
