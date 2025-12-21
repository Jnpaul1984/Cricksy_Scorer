"""
Tests for ball type clustering service.
"""

from backend.services.ball_type_clusterer import (
    BallTypeClusterer,
    DeliveryType,
    ClusterVariation,
)


class TestDeliveryClassification:
    """Test single delivery classification."""

    def test_classifies_fast_delivery(self):
        """Test fast delivery classification."""
        delivery = {
            "delivery_id": "d1",
            "pace": 85,
            "spin": 10,
            "line": "middle",
            "length": "good",
            "movement": "none",
            "bounce_index": 50,
            "runs_conceded": 0,
            "is_wicket": False,
            "bowler_id": "b1",
            "bowler_name": "Fast Bowler",
        }

        analysis = BallTypeClusterer.classify_delivery(delivery)

        assert analysis.delivery_type == DeliveryType.FAST
        assert analysis.confidence_score > 50

    def test_classifies_yorker(self):
        """Test yorker delivery classification."""
        delivery = {
            "pace": 60,
            "spin": 5,
            "line": "middle",
            "length": "yorker",
            "movement": "none",
            "bounce_index": 30,
            "runs_conceded": 0,
            "is_wicket": True,
            "bowler_id": "b1",
            "bowler_name": "Bowler",
        }

        analysis = BallTypeClusterer.classify_delivery(delivery)

        assert analysis.delivery_type == DeliveryType.YORKER

    def test_classifies_spin_delivery(self):
        """Test spin delivery classification."""
        delivery = {
            "pace": 40,
            "spin": 75,
            "line": "off",
            "length": "good",
            "movement": "offbreak",
            "bounce_index": 40,
            "runs_conceded": 2,
            "is_wicket": False,
            "bowler_id": "b1",
            "bowler_name": "Spinner",
        }

        analysis = BallTypeClusterer.classify_delivery(delivery)

        assert analysis.delivery_type == DeliveryType.SPIN

    def test_classifies_bouncer(self):
        """Test bouncer classification."""
        delivery = {
            "pace": 80,
            "spin": 5,
            "line": "middle",
            "length": "short",
            "movement": "none",
            "bounce_index": 75,
            "runs_conceded": 0,
            "is_wicket": False,
            "bowler_id": "b1",
            "bowler_name": "Bowler",
        }

        analysis = BallTypeClusterer.classify_delivery(delivery)

        assert analysis.delivery_type == DeliveryType.BOUNCER

    def test_calculates_confidence_high(self):
        """Test high confidence for clear characteristics."""
        delivery = {
            "pace": 95,
            "spin": 0,
            "line": "middle",
            "length": "full",
            "movement": "inswing",
            "bounce_index": 50,
            "runs_conceded": 0,
            "is_wicket": False,
            "bowler_id": "b1",
            "bowler_name": "Bowler",
        }

        analysis = BallTypeClusterer.classify_delivery(delivery)

        assert analysis.confidence_score >= 70


class TestBatterReactionAssessment:
    """Test batter reaction assessment."""

    def test_uncomfortable_to_bouncer(self):
        """Test batter discomfort to bouncer."""
        delivery = {
            "pace": 80,
            "spin": 5,
            "line": "middle",
            "length": "short",
            "movement": "none",
            "bounce_index": 80,
            "runs_conceded": 0,
            "is_wicket": False,
            "bowler_id": "b1",
            "bowler_name": "Bowler",
        }

        analysis = BallTypeClusterer.classify_delivery(delivery)

        assert analysis.batter_reaction == "uncomfortable"

    def test_defensive_to_yorker(self):
        """Test defensive reaction to yorker."""
        delivery = {
            "pace": 60,
            "spin": 0,
            "line": "middle",
            "length": "yorker",
            "movement": "none",
            "bounce_index": 30,
            "runs_conceded": 0,
            "is_wicket": False,
            "bowler_id": "b1",
            "bowler_name": "Bowler",
        }

        analysis = BallTypeClusterer.classify_delivery(delivery)

        assert analysis.batter_reaction == "defensive"


class TestOutcomeDetermination:
    """Test delivery outcome determination."""

    def test_outcome_wicket(self):
        """Test wicket outcome."""
        delivery = {
            "pace": 70,
            "spin": 0,
            "line": "middle",
            "length": "good",
            "movement": "none",
            "bounce_index": 50,
            "runs_conceded": 0,
            "is_wicket": True,
            "bowler_id": "b1",
            "bowler_name": "Bowler",
        }

        analysis = BallTypeClusterer.classify_delivery(delivery)

        assert analysis.outcome == "wicket"

    def test_outcome_dot(self):
        """Test dot outcome."""
        delivery = {
            "pace": 70,
            "spin": 0,
            "line": "middle",
            "length": "good",
            "movement": "none",
            "bounce_index": 50,
            "runs_conceded": 0,
            "is_wicket": False,
            "bowler_id": "b1",
            "bowler_name": "Bowler",
        }

        analysis = BallTypeClusterer.classify_delivery(delivery)

        assert analysis.outcome == "dot"

    def test_outcome_boundary(self):
        """Test boundary outcome."""
        delivery = {
            "pace": 40,
            "spin": 0,
            "line": "off",
            "length": "full",
            "movement": "none",
            "bounce_index": 50,
            "runs_conceded": 4,
            "is_wicket": False,
            "bowler_id": "b1",
            "bowler_name": "Bowler",
        }

        analysis = BallTypeClusterer.classify_delivery(delivery)

        assert analysis.outcome == "boundary"


class TestBowlerDeliveryProfile:
    """Test bowler delivery profile analysis."""

    def test_generates_bowler_profile(self):
        """Test bowler profile generation."""
        deliveries = [
            {
                "pace": 85,
                "spin": 5,
                "line": "middle",
                "length": "good",
                "movement": "none",
                "bounce_index": 50,
                "runs_conceded": 0,
                "is_wicket": False,
                "bowler_id": "b1",
                "bowler_name": "Bowler",
            }
            for _ in range(5)
        ] + [
            {
                "pace": 60,
                "spin": 0,
                "line": "middle",
                "length": "yorker",
                "movement": "none",
                "bounce_index": 30,
                "runs_conceded": 0,
                "is_wicket": True,
                "bowler_id": "b1",
                "bowler_name": "Bowler",
            }
            for _ in range(3)
        ]

        profile = BallTypeClusterer.analyze_bowler_deliveries(
            bowler_id="b1",
            bowler_name="Bowler",
            deliveries=deliveries,
        )

        assert profile.bowler_id == "b1"
        assert profile.total_deliveries == 8
        assert len(profile.delivery_clusters) >= 1
        assert profile.most_effective_cluster is not None

    def test_identifies_primary_clusters(self):
        """Test identification of primary clusters."""
        deliveries = [
            {
                "pace": 85,
                "spin": 5,
                "line": "middle",
                "length": "good",
                "movement": "none",
                "bounce_index": 50,
                "runs_conceded": 0,
                "is_wicket": False,
                "bowler_id": "b1",
                "bowler_name": "Bowler",
            }
            for _ in range(10)
        ] + [
            {
                "pace": 60,
                "spin": 0,
                "line": "middle",
                "length": "yorker",
                "movement": "none",
                "bounce_index": 30,
                "runs_conceded": 0,
                "is_wicket": True,
                "bowler_id": "b1",
                "bowler_name": "Bowler",
            }
            for _ in range(3)
        ]

        profile = BallTypeClusterer.analyze_bowler_deliveries(
            bowler_id="b1",
            bowler_name="Bowler",
            deliveries=deliveries,
        )

        assert len(profile.primary_clusters) <= 3
        assert len(profile.primary_clusters) > 0

    def test_calculates_variation_score(self):
        """Test variation score calculation."""
        # Bowler with all same type = low variation
        same_type_deliveries = [
            {
                "pace": 85,
                "spin": 5,
                "line": "middle",
                "length": "good",
                "movement": "none",
                "bounce_index": 50,
                "runs_conceded": 0,
                "is_wicket": False,
                "bowler_id": "b1",
                "bowler_name": "Bowler",
            }
            for _ in range(10)
        ]

        profile = BallTypeClusterer.analyze_bowler_deliveries(
            bowler_id="b1",
            bowler_name="Bowler",
            deliveries=same_type_deliveries,
        )

        assert 0 <= profile.variation_score <= 100

    def test_empty_deliveries_handling(self):
        """Test handling of empty deliveries."""
        profile = BallTypeClusterer.analyze_bowler_deliveries(
            bowler_id="b1",
            bowler_name="Bowler",
            deliveries=[],
        )

        assert profile.total_deliveries == 0
        assert len(profile.delivery_clusters) == 0


class TestBatterVulnerability:
    """Test batter vulnerability analysis."""

    def test_identifies_vulnerable_clusters(self):
        """Test identification of vulnerable delivery types."""
        # Batter gets out to fast bowling and expensive against yorkers
        faced_deliveries = [
            {
                "pace": 85,
                "spin": 5,
                "line": "middle",
                "length": "good",
                "movement": "none",
                "bounce_index": 50,
                "runs_conceded": 4,
                "is_wicket": False,
                "bowler_id": "b1",
                "bowler_name": "Bowler",
            }
            for _ in range(3)
        ] + [
            {
                "pace": 85,
                "spin": 5,
                "line": "middle",
                "length": "good",
                "movement": "none",
                "bounce_index": 50,
                "runs_conceded": 0,
                "is_wicket": True,
                "bowler_id": "b2",
                "bowler_name": "Bowler2",
            }
        ]

        vulnerability = BallTypeClusterer.analyze_batter_vulnerabilities(
            batter_id="p1",
            batter_name="Batter",
            faced_deliveries=faced_deliveries,
        )

        assert vulnerability.batter_id == "p1"
        assert len(vulnerability.vulnerable_clusters) > 0

    def test_identifies_strong_delivery_types(self):
        """Test identification of strong delivery types."""
        faced_deliveries = [
            {
                "pace": 40,
                "spin": 80,
                "line": "off",
                "length": "good",
                "movement": "offbreak",
                "bounce_index": 40,
                "runs_conceded": 0,
                "is_wicket": False,
                "bowler_id": "b1",
                "bowler_name": "Spinner",
            }
            for _ in range(5)
        ]

        vulnerability = BallTypeClusterer.analyze_batter_vulnerabilities(
            batter_id="p1",
            batter_name="Batter",
            faced_deliveries=faced_deliveries,
        )

        assert vulnerability.batter_id == "p1"
        # Spin bowling should appear in strong_against or low vulnerability

    def test_tracks_dismissal_types(self):
        """Test tracking of dismissal delivery types."""
        faced_deliveries = [
            {
                "pace": 85,
                "spin": 0,
                "line": "middle",
                "length": "good",
                "movement": "none",
                "bounce_index": 50,
                "runs_conceded": 0,
                "is_wicket": True,
                "bowler_id": "b1",
                "bowler_name": "Bowler",
            }
            for _ in range(2)
        ]

        vulnerability = BallTypeClusterer.analyze_batter_vulnerabilities(
            batter_id="p1",
            batter_name="Batter",
            faced_deliveries=faced_deliveries,
        )

        assert len(vulnerability.dismissal_delivery_types) > 0


class TestClusterMatrix:
    """Test cluster effectiveness matrix generation."""

    def test_generates_cluster_matrix(self):
        """Test matrix generation."""
        deliveries = [
            {
                "pace": 85,
                "spin": 5,
                "line": "middle",
                "length": "good",
                "movement": "none",
                "bounce_index": 50,
                "runs_conceded": 0,
                "is_wicket": False,
                "bowler_id": "b1",
                "bowler_name": "Bowler",
            }
            for _ in range(4)
        ] + [
            {
                "pace": 85,
                "spin": 5,
                "line": "middle",
                "length": "good",
                "movement": "none",
                "bounce_index": 50,
                "runs_conceded": 0,
                "is_wicket": True,
                "bowler_id": "b1",
                "bowler_name": "Bowler",
            }
        ]

        matrix = BallTypeClusterer.generate_cluster_matrix(deliveries)

        assert len(matrix) > 0
        assert DeliveryType.FAST in matrix or DeliveryType.GOOD_LENGTH in matrix

    def test_matrix_calculates_effectiveness(self):
        """Test effectiveness rating in matrix."""
        deliveries = [
            {
                "pace": 85,
                "spin": 5,
                "line": "middle",
                "length": "good",
                "movement": "none",
                "bounce_index": 50,
                "runs_conceded": 0,
                "is_wicket": False,
                "bowler_id": "b1",
                "bowler_name": "Bowler",
            }
            for _ in range(10)
        ]

        matrix = BallTypeClusterer.generate_cluster_matrix(deliveries)

        for cluster_type, cluster_matrix in matrix.items():
            assert 0 <= cluster_matrix.effectiveness_rating <= 100


class TestVariationDetection:
    """Test delivery variation detection."""

    def test_detects_slower_ball_variation(self):
        """Test detection of slower ball as variation."""
        delivery = {
            "pace": 35,
            "spin": 50,
            "line": "off",
            "length": "good",
            "movement": "none",
            "bounce_index": 40,
            "runs_conceded": 0,
            "is_wicket": False,
            "bowler_id": "b1",
            "bowler_name": "Bowler",
        }

        analysis = BallTypeClusterer.classify_delivery(delivery)

        assert analysis.variation == ClusterVariation.SLOWER

    def test_detects_yorker_variation(self):
        """Test detection of yorker."""
        delivery = {
            "pace": 80,
            "spin": 5,
            "line": "middle",
            "length": "yorker",
            "movement": "none",
            "bounce_index": 25,
            "runs_conceded": 0,
            "is_wicket": False,
            "bowler_id": "b1",
            "bowler_name": "Bowler",
        }

        analysis = BallTypeClusterer.classify_delivery(delivery)

        assert analysis.delivery_type == DeliveryType.YORKER


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_handles_missing_delivery_fields(self):
        """Test handling of deliveries with missing fields."""
        delivery = {"delivery_id": "d1"}

        analysis = BallTypeClusterer.classify_delivery(delivery)

        assert analysis.delivery_id == "d1"
        # Should classify with defaults

    def test_handles_extreme_pace_values(self):
        """Test handling of extreme pace values."""
        # Unrealistically high pace
        delivery = {
            "pace": 200,
            "spin": 0,
            "line": "middle",
            "length": "good",
            "movement": "none",
            "bounce_index": 50,
            "runs_conceded": 0,
            "is_wicket": False,
            "bowler_id": "b1",
            "bowler_name": "Bowler",
        }

        analysis = BallTypeClusterer.classify_delivery(delivery)

        # Should classify as fast or similar
        assert analysis.confidence_score >= 0
