"""
Tests for pitch heatmap generator service.
"""

from backend.services.pitch_heatmap_generator import (
    PitchHeatmapGenerator,
    HeatmapType,
    PitchZone,
)


class TestBatterScoringHeatmap:
    """Test batter scoring heatmap generation."""

    def test_generates_scoring_heatmap(self):
        """Test basic scoring heatmap generation."""
        deliveries = [
            {"zone": PitchZone.OFF_SIDE_FULL, "runs_scored": 4},
            {"zone": PitchZone.OFF_SIDE_FULL, "runs_scored": 2},
            {"zone": PitchZone.LEG_SIDE_FULL, "runs_scored": 6},
            {"zone": PitchZone.MIDDLE_FULL, "runs_scored": 1},
        ]

        heatmap = PitchHeatmapGenerator.generate_batter_scoring_heatmap(
            player_id="p1",
            player_name="Test Batter",
            deliveries=deliveries,
        )

        assert heatmap.player_id == "p1"
        assert heatmap.player_name == "Test Batter"
        assert heatmap.heatmap_type == HeatmapType.RUNS
        assert len(heatmap.data_points) == 3
        assert heatmap.total_events == 4
        assert heatmap.metadata["total_runs"] == 13

    def test_calculates_intensity_correctly(self):
        """Test that intensity is normalized 0-100."""
        deliveries = [
            {"zone": PitchZone.OFF_SIDE_FULL, "runs_scored": 10},
            {"zone": PitchZone.LEG_SIDE_FULL, "runs_scored": 5},
        ]

        heatmap = PitchHeatmapGenerator.generate_batter_scoring_heatmap(
            player_id="p1",
            player_name="Scorer",
            deliveries=deliveries,
        )

        max_intensity = max(p.value for p in heatmap.data_points)
        assert 95 <= max_intensity <= 100  # Should be close to 100
        assert heatmap.min_value == 0.0
        assert heatmap.max_value == 100.0

    def test_handles_empty_deliveries(self):
        """Test handling of empty deliveries."""
        heatmap = PitchHeatmapGenerator.generate_batter_scoring_heatmap(
            player_id="p1",
            player_name="Non-Scorer",
            deliveries=[],
        )

        assert heatmap.total_events == 0
        assert len(heatmap.data_points) == 0
        assert heatmap.average_value == 0.0

    def test_coordinates_are_valid(self):
        """Test that zone coordinates are within pitch boundaries."""
        deliveries = [
            {"zone": PitchZone.OFF_SIDE_SHORT, "runs_scored": 4},
            {"zone": PitchZone.LEG_SIDE_YORKER, "runs_scored": 6},
            {"zone": PitchZone.MIDDLE_FULL, "runs_scored": 1},
        ]

        heatmap = PitchHeatmapGenerator.generate_batter_scoring_heatmap(
            player_id="p1",
            player_name="Batter",
            deliveries=deliveries,
        )

        for point in heatmap.data_points:
            assert 0 <= point.x_coordinate <= 100
            assert 0 <= point.y_coordinate <= 100
            assert 0 <= point.value <= 100

    def test_preserves_run_aggregation(self):
        """Test that runs are correctly aggregated by zone."""
        deliveries = [
            {"zone": PitchZone.OFF_SIDE_FULL, "runs_scored": 4},
            {"zone": PitchZone.OFF_SIDE_FULL, "runs_scored": 2},
            {"zone": PitchZone.OFF_SIDE_FULL, "runs_scored": 1},
        ]

        heatmap = PitchHeatmapGenerator.generate_batter_scoring_heatmap(
            player_id="p1",
            player_name="Batter",
            deliveries=deliveries,
        )

        assert len(heatmap.data_points) == 1
        assert heatmap.data_points[0].count == 3
        assert heatmap.metadata["total_runs"] == 7


class TestDismissalHeatmap:
    """Test dismissal pattern heatmaps."""

    def test_generates_dismissal_heatmap(self):
        """Test basic dismissal heatmap."""
        dismissals = [
            {"zone": PitchZone.OFF_SIDE_FULL, "dismissal_type": "lbw"},
            {"zone": PitchZone.OFF_SIDE_FULL, "dismissal_type": "caught"},
            {"zone": PitchZone.LEG_SIDE_FULL, "dismissal_type": "bowled"},
        ]

        heatmap = PitchHeatmapGenerator.generate_dismissal_heatmap(
            player_id="p1",
            player_name="Dismissed Batter",
            dismissals=dismissals,
        )

        assert heatmap.heatmap_type == HeatmapType.DISMISSALS
        assert len(heatmap.data_points) == 2
        assert heatmap.total_events == 3
        assert heatmap.metadata["total_dismissals"] == 3

    def test_dismissal_intensity_by_frequency(self):
        """Test that dismissal intensity is based on frequency."""
        dismissals = [
            {"zone": PitchZone.OFF_SIDE_FULL, "dismissal_type": "lbw"},
            {"zone": PitchZone.OFF_SIDE_FULL, "dismissal_type": "caught"},
            {"zone": PitchZone.OFF_SIDE_FULL, "dismissal_type": "bowled"},
            {"zone": PitchZone.LEG_SIDE_FULL, "dismissal_type": "run_out"},
        ]

        heatmap = PitchHeatmapGenerator.generate_dismissal_heatmap(
            player_id="p1",
            player_name="Batter",
            dismissals=dismissals,
        )

        # Off-side should have highest intensity (3 vs 1)
        off_side_point = next(
            (p for p in heatmap.data_points if p.zone == PitchZone.OFF_SIDE_FULL),
            None,
        )
        leg_side_point = next(
            (p for p in heatmap.data_points if p.zone == PitchZone.LEG_SIDE_FULL),
            None,
        )

        assert off_side_point is not None
        assert leg_side_point is not None
        assert off_side_point.value > leg_side_point.value

    def test_dismissal_types_in_detail(self):
        """Test that dismissal types are captured in detail field."""
        dismissals = [
            {"zone": PitchZone.OFF_SIDE_FULL, "dismissal_type": "lbw"},
            {"zone": PitchZone.OFF_SIDE_FULL, "dismissal_type": "caught"},
        ]

        heatmap = PitchHeatmapGenerator.generate_dismissal_heatmap(
            player_id="p1",
            player_name="Batter",
            dismissals=dismissals,
        )

        detail = heatmap.data_points[0].detail
        assert "lbw" in detail.lower() or "caught" in detail.lower()


class TestBowlerReleaseZones:
    """Test bowler release zone heatmap."""

    def test_generates_release_heatmap(self):
        """Test bowler release heatmap generation."""
        deliveries = [
            {"zone": PitchZone.MIDDLE_FULL},
            {"zone": PitchZone.MIDDLE_FULL},
            {"zone": PitchZone.OFF_SIDE_FULL},
            {"zone": PitchZone.OFF_SIDE_FULL},
            {"zone": PitchZone.LEG_SIDE_FULL},
        ]

        heatmap = PitchHeatmapGenerator.generate_bowler_release_heatmap(
            bowler_id="b1",
            bowler_name="Test Bowler",
            deliveries=deliveries,
        )

        assert heatmap.heatmap_type == HeatmapType.BOWLER_RELEASE
        assert heatmap.total_events == 5
        assert len(heatmap.data_points) == 3

    def test_accuracy_score_calculation(self):
        """Test bowler accuracy score (concentration)."""
        # Bowler who bowls mostly in one zone (high accuracy)
        concentrated_deliveries = [
            {"zone": PitchZone.MIDDLE_FULL},
        ] * 8 + [
            {"zone": PitchZone.OFF_SIDE_FULL},
        ] * 2

        heatmap = PitchHeatmapGenerator.generate_bowler_release_heatmap(
            bowler_id="b1",
            bowler_name="Accurate Bowler",
            deliveries=concentrated_deliveries,
        )

        accuracy = heatmap.metadata["accuracy_score"]
        assert 70 <= accuracy <= 100  # 8/10 = 80%

    def test_primary_zone_identification(self):
        """Test identification of primary zone."""
        deliveries = (
            [
                {"zone": PitchZone.MIDDLE_FULL},
            ]
            * 6
            + [
                {"zone": PitchZone.OFF_SIDE_FULL},
            ]
            * 3
            + [
                {"zone": PitchZone.LEG_SIDE_FULL},
            ]
        )

        heatmap = PitchHeatmapGenerator.generate_bowler_release_heatmap(
            bowler_id="b1",
            bowler_name="Bowler",
            deliveries=deliveries,
        )

        assert heatmap.metadata["primary_zone"] == PitchZone.MIDDLE_FULL


class TestBatterProfile:
    """Test comprehensive batter profile analysis."""

    def test_generates_batter_profile(self):
        """Test batter profile generation."""
        deliveries = [
            {"zone": PitchZone.OFF_SIDE_FULL, "runs_scored": 4},
            {"zone": PitchZone.OFF_SIDE_FULL, "runs_scored": 0},
            {"zone": PitchZone.LEG_SIDE_FULL, "runs_scored": 6},
            {"zone": PitchZone.MIDDLE_FULL, "runs_scored": 1},
        ]
        dismissals = [
            {"zone": PitchZone.OFF_SIDE_FULL, "dismissal_type": "caught"},
        ]

        profile = PitchHeatmapGenerator.analyze_batter_profile(
            player_id="p1",
            player_name="Test Batter",
            deliveries=deliveries,
            dismissals=dismissals,
        )

        assert profile.player_id == "p1"
        assert profile.total_runs == 11
        assert profile.total_dismissals == 1
        assert PitchZone.OFF_SIDE_FULL in profile.scoring_zones
        assert profile.profile_type == "scoring"

    def test_identifies_strong_zones(self):
        """Test identification of strong scoring zones."""
        deliveries = [
            {"zone": PitchZone.OFF_SIDE_FULL, "runs_scored": 20},  # Strong
            {"zone": PitchZone.LEG_SIDE_FULL, "runs_scored": 3},  # Weak
            {"zone": PitchZone.MIDDLE_FULL, "runs_scored": 0},  # Weak
        ]

        profile = PitchHeatmapGenerator.analyze_batter_profile(
            player_id="p1",
            player_name="Batter",
            deliveries=deliveries,
            dismissals=[],
        )

        assert PitchZone.OFF_SIDE_FULL in profile.strong_zones

    def test_identifies_weak_zones(self):
        """Test identification of dismissal-prone zones."""
        deliveries = []
        dismissals = [
            {"zone": PitchZone.OFF_SIDE_FULL, "dismissal_type": "lbw"},
            {"zone": PitchZone.OFF_SIDE_FULL, "dismissal_type": "caught"},
            {"zone": PitchZone.LEG_SIDE_FULL, "dismissal_type": "bowled"},
        ]

        profile = PitchHeatmapGenerator.analyze_batter_profile(
            player_id="p1",
            player_name="Batter",
            deliveries=deliveries,
            dismissals=dismissals,
        )

        # Off-side should be weak zone (2 dismissals)
        assert PitchZone.OFF_SIDE_FULL in profile.weak_zones

    def test_calculates_scoring_efficiency(self):
        """Test scoring efficiency (runs per delivery) by zone."""
        deliveries = [
            {"zone": PitchZone.OFF_SIDE_FULL, "runs_scored": 8},
            {"zone": PitchZone.OFF_SIDE_FULL, "runs_scored": 2},
            {"zone": PitchZone.LEG_SIDE_FULL, "runs_scored": 3},
        ]

        profile = PitchHeatmapGenerator.analyze_batter_profile(
            player_id="p1",
            player_name="Batter",
            deliveries=deliveries,
            dismissals=[],
        )

        off_efficiency = profile.scoring_efficiency[PitchZone.OFF_SIDE_FULL]
        leg_efficiency = profile.scoring_efficiency[PitchZone.LEG_SIDE_FULL]

        assert off_efficiency == 5.0  # (8+2)/2 = 5
        assert leg_efficiency == 3.0  # 3/1 = 3


class TestBowlerProfile:
    """Test comprehensive bowler profile analysis."""

    def test_generates_bowler_profile(self):
        """Test bowler profile generation."""
        deliveries = [
            {"zone": PitchZone.MIDDLE_FULL},
            {"zone": PitchZone.MIDDLE_FULL},
            {"zone": PitchZone.OFF_SIDE_FULL},
        ]
        wickets = [
            {"zone": PitchZone.MIDDLE_FULL},
        ]

        profile = PitchHeatmapGenerator.analyze_bowler_profile(
            bowler_id="b1",
            bowler_name="Test Bowler",
            deliveries=deliveries,
            wickets=wickets,
        )

        assert profile.player_id == "b1"
        assert profile.total_deliveries == 3
        assert PitchZone.MIDDLE_FULL in profile.primary_zones

    def test_identifies_primary_zones(self):
        """Test identification of primary zones (>15% of deliveries)."""
        deliveries = (
            [
                {"zone": PitchZone.MIDDLE_FULL},
            ]
            * 6
            + [
                {"zone": PitchZone.OFF_SIDE_FULL},
            ]
            * 2
            + [
                {"zone": PitchZone.LEG_SIDE_FULL},
            ]
        )

        profile = PitchHeatmapGenerator.analyze_bowler_profile(
            bowler_id="b1",
            bowler_name="Bowler",
            deliveries=deliveries,
            wickets=[],
        )

        # MIDDLE_FULL: 6/9 = 67% (primary)
        # OFF_SIDE: 2/9 = 22% (primary)
        # LEG_SIDE: 1/9 = 11% (not primary)
        assert PitchZone.MIDDLE_FULL in profile.primary_zones
        assert PitchZone.OFF_SIDE_FULL in profile.primary_zones
        assert PitchZone.LEG_SIDE_FULL not in profile.primary_zones

    def test_calculates_zone_effectiveness(self):
        """Test wicket rate calculation per zone."""
        deliveries = [
            {"zone": PitchZone.MIDDLE_FULL},
            {"zone": PitchZone.MIDDLE_FULL},
            {"zone": PitchZone.OFF_SIDE_FULL},
            {"zone": PitchZone.OFF_SIDE_FULL},
        ]
        wickets = [
            {"zone": PitchZone.MIDDLE_FULL},
        ]

        profile = PitchHeatmapGenerator.analyze_bowler_profile(
            bowler_id="b1",
            bowler_name="Bowler",
            deliveries=deliveries,
            wickets=wickets,
        )

        middle_effectiveness = profile.zone_effectiveness[PitchZone.MIDDLE_FULL]
        off_effectiveness = profile.zone_effectiveness[PitchZone.OFF_SIDE_FULL]

        assert middle_effectiveness == 50.0  # 1/2 = 50%
        assert off_effectiveness == 0.0  # 0/2 = 0%


class TestMatchupAnalysis:
    """Test batter vs bowler matchup analysis."""

    def test_generates_matchup_analysis(self):
        """Test matchup analysis generation."""
        deliveries = [
            {"zone": PitchZone.MIDDLE_FULL},
            {"zone": PitchZone.OFF_SIDE_FULL},
        ]
        dismissals = []

        matchup = PitchHeatmapGenerator.analyze_matchup(
            batter_id="p1",
            batter_name="Batter",
            bowler_id="b1",
            bowler_name="Bowler",
            deliveries=deliveries,
            dismissals=dismissals,
        )

        assert matchup.batter_id == "p1"
        assert matchup.bowler_id == "b1"
        assert matchup.total_deliveries == 2

    def test_identifies_dangerous_overlap_areas(self):
        """Test identification of dangerous areas for bowler."""
        deliveries = [
            {"zone": PitchZone.OFF_SIDE_FULL},
        ] * 2
        dismissals = []

        matchup = PitchHeatmapGenerator.analyze_matchup(
            batter_id="p1",
            batter_name="Batter",
            bowler_id="b1",
            bowler_name="Bowler",
            deliveries=deliveries,
            dismissals=dismissals,
        )

        # If off-side is strong for batter and bowler delivers there,
        # it's a dangerous area
        assert isinstance(matchup.dangerous_areas, list)

    def test_generates_strategic_recommendation(self):
        """Test that recommendation is generated."""
        deliveries = [{"zone": PitchZone.MIDDLE_FULL}] * 3
        dismissals = []

        matchup = PitchHeatmapGenerator.analyze_matchup(
            batter_id="p1",
            batter_name="Batter",
            bowler_id="b1",
            bowler_name="Bowler",
            deliveries=deliveries,
            dismissals=dismissals,
        )

        assert isinstance(matchup.recommendation, str)
        assert len(matchup.recommendation) > 0


class TestZoneBoundaries:
    """Test pitch zone boundary definitions."""

    def test_zone_boundaries_are_valid(self):
        """Test that all zone boundaries are within pitch limits."""
        for zone, (x_min, x_max, y_min, y_max) in PitchHeatmapGenerator.ZONE_BOUNDARIES.items():
            assert 0 <= x_min <= 100
            assert 0 <= x_max <= 100
            assert 0 <= y_min <= 100
            assert 0 <= y_max <= 100
            assert x_min < x_max
            assert y_min < y_max

    def test_zone_boundaries_cover_pitch(self):
        """Test that zones collectively cover the pitch."""
        # At least 6 zones should exist
        assert len(PitchHeatmapGenerator.ZONE_BOUNDARIES) >= 6
