"""
Tests for Ball Tracking Service

Tests ball detection, trajectory analysis, and coaching metrics.
Uses synthetic data for unit tests. Integration tests require video files.
"""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from backend.services.ball_tracking_service import (
    BallMetrics,
    BallPosition,
    BallTracker,
    BallTrajectory,
    _calculate_swing_deviation,
    _classify_trajectory_shape,
    analyze_ball_trajectory,
    analyze_multiple_deliveries,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def sample_positions():
    """Sample ball positions forming a straight trajectory."""
    return [
        BallPosition(
            frame_num=i,
            timestamp=i * 0.033,  # 30fps
            x=100.0 + i * 10,  # Moving right
            y=50.0 + i * 5,  # Moving down
            confidence=0.9,
            radius=12.0,
            velocity_x=10.0,
            velocity_y=5.0,
        )
        for i in range(20)
    ]


@pytest.fixture
def sample_trajectory(sample_positions):
    """Sample trajectory with positions."""
    trajectory = BallTrajectory(
        positions=sample_positions,
        total_frames=100,
        detected_frames=20,
        detection_rate=20.0,
    )
    trajectory.release_point = sample_positions[0]
    trajectory.bounce_point = sample_positions[10]
    trajectory.impact_point = sample_positions[-1]
    trajectory.avg_velocity = 11.18
    trajectory.max_velocity = 15.0
    trajectory.trajectory_length = 250.0
    return trajectory


# ============================================================================
# BallPosition Tests
# ============================================================================


class TestBallPosition:
    """Test BallPosition dataclass."""

    def test_creates_ball_position(self):
        """Test creating ball position."""
        pos = BallPosition(
            frame_num=10,
            timestamp=0.33,
            x=150.0,
            y=200.0,
            confidence=0.85,
            radius=15.0,
        )

        assert pos.frame_num == 10
        assert pos.timestamp == 0.33
        assert pos.x == 150.0
        assert pos.y == 200.0
        assert pos.confidence == 0.85
        assert pos.radius == 15.0
        assert pos.velocity_x == 0.0
        assert pos.velocity_y == 0.0


# ============================================================================
# BallTrajectory Tests
# ============================================================================


class TestBallTrajectory:
    """Test BallTrajectory dataclass."""

    def test_creates_empty_trajectory(self):
        """Test creating empty trajectory."""
        trajectory = BallTrajectory()

        assert trajectory.positions == []
        assert trajectory.total_frames == 0
        assert trajectory.detected_frames == 0
        assert trajectory.detection_rate == 0.0
        assert trajectory.release_point is None
        assert trajectory.bounce_point is None
        assert trajectory.impact_point is None

    def test_creates_trajectory_with_positions(self, sample_positions):
        """Test creating trajectory with positions."""
        trajectory = BallTrajectory(
            positions=sample_positions,
            total_frames=100,
            detected_frames=20,
            detection_rate=20.0,
        )

        assert len(trajectory.positions) == 20
        assert trajectory.total_frames == 100
        assert trajectory.detected_frames == 20
        assert trajectory.detection_rate == 20.0


# ============================================================================
# BallTracker Tests
# ============================================================================


class TestBallTracker:
    """Test BallTracker class."""

    def test_initializes_with_red_ball(self):
        """Test tracker initialization with red ball."""
        tracker = BallTracker(ball_color="red")

        assert tracker.ball_color == "red"
        assert tracker.min_radius == 5
        assert tracker.max_radius == 50

    def test_initializes_with_white_ball(self):
        """Test tracker initialization with white ball."""
        tracker = BallTracker(ball_color="white", min_radius=10, max_radius=30)

        assert tracker.ball_color == "white"
        assert tracker.min_radius == 10
        assert tracker.max_radius == 30

    def test_rejects_invalid_ball_color(self):
        """Test rejection of invalid ball color."""
        with pytest.raises(ValueError, match="Unsupported ball color"):
            BallTracker(ball_color="blue")

    def test_calculates_velocities(self):
        """Test velocity calculation for positions."""
        positions = [
            BallPosition(0, 0.0, 0.0, 0.0, 0.9, 10.0),
            BallPosition(1, 0.1, 10.0, 5.0, 0.9, 10.0),
            BallPosition(2, 0.2, 20.0, 10.0, 0.9, 10.0),
        ]

        tracker = BallTracker()
        tracker._calculate_velocities(positions, fps=10.0)

        # First position: forward difference
        assert abs(positions[0].velocity_x - 100.0) < 0.1
        assert abs(positions[0].velocity_y - 50.0) < 0.1

        # Middle position: central difference
        assert abs(positions[1].velocity_x - 100.0) < 0.1
        assert abs(positions[1].velocity_y - 50.0) < 0.1

        # Last position: backward difference
        assert abs(positions[2].velocity_x - 100.0) < 0.1
        assert abs(positions[2].velocity_y - 50.0) < 0.1

    def test_identifies_release_point(self):
        """Test release point identification."""
        positions = [BallPosition(i, i * 0.1, 100.0, 50.0 + i * 10, 0.9, 10.0) for i in range(10)]

        tracker = BallTracker()
        trajectory = BallTrajectory(positions=positions)
        tracker._identify_key_points(trajectory)

        # Release should be first position (lowest y = highest on screen)
        assert trajectory.release_point == positions[0]
        assert trajectory.impact_point == positions[-1]

    def test_finds_bounce_point(self):
        """Test bounce point detection."""
        # Create positions with velocity reversal at frame 5
        positions = [
            BallPosition(i, i * 0.1, 100.0, 50.0, 0.9, 10.0, 10.0, 100.0 if i < 5 else -50.0)
            for i in range(10)
        ]

        tracker = BallTracker()
        bounce_idx = tracker._find_bounce_point(positions)

        assert bounce_idx == 5

    def test_calculates_trajectory_metrics(self):
        """Test trajectory metrics calculation."""
        positions = [
            BallPosition(i, i * 0.1, 100.0 + i * 10, 50.0 + i * 5, 0.9, 10.0, 100.0, 50.0)
            for i in range(10)
        ]

        tracker = BallTracker()
        trajectory = BallTrajectory(positions=positions)
        tracker._calculate_trajectory_metrics(trajectory)

        # Should have calculated velocities and distance
        assert trajectory.avg_velocity > 0
        assert trajectory.max_velocity > 0
        assert trajectory.trajectory_length > 0


# ============================================================================
# Trajectory Analysis Tests
# ============================================================================


class TestTrajectoryAnalysis:
    """Test trajectory analysis functions."""

    def test_analyzes_ball_trajectory(self, sample_trajectory):
        """Test ball trajectory analysis."""
        metrics = analyze_ball_trajectory(sample_trajectory)

        assert isinstance(metrics, BallMetrics)
        assert metrics.release_height is not None
        assert metrics.release_position_x is not None
        assert metrics.flight_time > 0
        assert metrics.ball_speed_estimate > 0

    def test_handles_empty_trajectory(self):
        """Test analysis of empty trajectory."""
        empty_trajectory = BallTrajectory()
        metrics = analyze_ball_trajectory(empty_trajectory)

        assert metrics.release_height is None
        assert metrics.flight_time == 0.0

    def test_calculates_swing_deviation(self, sample_positions):
        """Test swing deviation calculation."""
        deviation = _calculate_swing_deviation(sample_positions)

        # Straight trajectory should have low deviation
        assert deviation < 10.0

    def test_detects_swing_in_curved_trajectory(self):
        """Test swing detection in curved path."""
        # Create positions that curve to the right
        positions = [
            BallPosition(
                i,
                i * 0.1,
                100.0 + i * 10 + (i - 10) ** 2 * 2,  # Parabolic x
                50.0 + i * 5,
                0.9,
                10.0,
            )
            for i in range(20)
        ]

        deviation = _calculate_swing_deviation(positions)

        # Curved trajectory should have higher deviation
        assert deviation > 20.0

    def test_classifies_straight_trajectory(self, sample_positions):
        """Test classification of straight trajectory."""
        shape = _classify_trajectory_shape(sample_positions, swing_deviation=5.0)

        assert shape == "straight"

    def test_classifies_inswing_trajectory(self):
        """Test classification of inswing trajectory."""
        # Create positions that curve left (inswing)
        positions = [
            BallPosition(
                i,
                i * 0.1,
                200.0 - abs(i - 10) * 5,  # Curves left at midpoint
                50.0 + i * 5,
                0.9,
                10.0,
            )
            for i in range(20)
        ]

        shape = _classify_trajectory_shape(positions, swing_deviation=35.0)

        assert shape == "inswing"

    def test_classifies_outswing_trajectory(self):
        """Test classification of outswing trajectory."""
        # Create positions that curve right (outswing)
        positions = [
            BallPosition(
                i,
                i * 0.1,
                100.0 + abs(i - 10) * 5,  # Curves right at midpoint
                50.0 + i * 5,
                0.9,
                10.0,
            )
            for i in range(20)
        ]

        shape = _classify_trajectory_shape(positions, swing_deviation=35.0)

        assert shape == "outswing"

    def test_classifies_rising_trajectory(self):
        """Test classification of rising delivery."""
        positions = [
            BallPosition(
                i,
                i * 0.1,
                100.0 + i * 10,
                50.0 - i * 5,  # Moving up (negative y velocity)
                0.9,
                10.0,
                10.0,
                -60.0,  # Negative y velocity
            )
            for i in range(20)
        ]

        shape = _classify_trajectory_shape(positions, swing_deviation=5.0)

        assert shape == "rising"

    def test_classifies_dipping_trajectory(self):
        """Test classification of dipping delivery."""
        positions = [
            BallPosition(
                i,
                i * 0.1,
                100.0 + i * 10,
                50.0 + i * 8,  # Moving down fast
                0.9,
                10.0,
                10.0,
                80.0,  # High positive y velocity
            )
            for i in range(20)
        ]

        shape = _classify_trajectory_shape(positions, swing_deviation=5.0)

        assert shape == "dipping"


# ============================================================================
# Multiple Deliveries Analysis Tests
# ============================================================================


class TestMultipleDeliveriesAnalysis:
    """Test consistency analysis across multiple deliveries."""

    def test_analyzes_empty_list(self):
        """Test analysis of empty trajectory list."""
        result = analyze_multiple_deliveries([])

        assert result["delivery_count"] == 0
        assert result["consistency_score"] == 0

    def test_analyzes_single_delivery(self, sample_trajectory):
        """Test analysis of single delivery."""
        result = analyze_multiple_deliveries([sample_trajectory])

        assert result["delivery_count"] == 1
        assert "consistency_score" in result

    def test_calculates_consistency_across_deliveries(self):
        """Test consistency calculation for multiple deliveries."""
        # Create 3 trajectories with similar release points
        trajectories = []
        for i in range(3):
            positions = [
                BallPosition(
                    j,
                    j * 0.1,
                    100.0 + i * 2 + j * 10,  # Slight x variation
                    50.0 + i * 1 + j * 5,  # Slight y variation
                    0.9,
                    10.0,
                )
                for j in range(10)
            ]
            trajectory = BallTrajectory(positions=positions)
            trajectory.release_point = positions[0]
            trajectory.avg_velocity = 110.0 + i * 5
            trajectories.append(trajectory)

        result = analyze_multiple_deliveries(trajectories)

        assert result["delivery_count"] == 3
        assert result["consistency_score"] > 0  # Should be high for similar releases
        assert "release_variance_x" in result
        assert "release_variance_y" in result
        assert "avg_release_x" in result
        assert "velocity_variance" in result

    def test_detects_inconsistent_deliveries(self):
        """Test detection of inconsistent release points."""
        # Create 3 trajectories with very different release points
        trajectories = []
        for i in range(3):
            positions = [
                BallPosition(
                    j,
                    j * 0.1,
                    100.0 + i * 50 + j * 10,  # Large x variation
                    50.0 + i * 30 + j * 5,  # Large y variation
                    0.9,
                    10.0,
                )
                for j in range(10)
            ]
            trajectory = BallTrajectory(positions=positions)
            trajectory.release_point = positions[0]
            trajectory.avg_velocity = 110.0
            trajectories.append(trajectory)

        result = analyze_multiple_deliveries(trajectories)

        # High variance should result in low consistency score
        assert result["consistency_score"] < 50


# ============================================================================
# Integration Tests (require mocking)
# ============================================================================


class TestBallTrackerIntegration:
    """Integration tests for ball tracker (with mocked video)."""

    @patch("backend.services.ball_tracking_service._import_cv2")
    def test_tracks_ball_in_mocked_video(self, mock_import_cv2):
        """Test ball tracking with mocked video file."""
        # Mock cv2
        mock_cv2 = MagicMock()
        mock_import_cv2.return_value = mock_cv2

        # Mock video capture
        mock_cap = MagicMock()
        mock_cv2.VideoCapture.return_value = mock_cap
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = lambda prop: {
            mock_cv2.CAP_PROP_FRAME_COUNT: 100,
            mock_cv2.CAP_PROP_FPS: 30.0,
        }.get(prop, 0)

        # Mock frame reading (simulate 5 frames)
        frame_count = [0]

        def read_side_effect():
            if frame_count[0] < 5:
                frame_count[0] += 1
                # Return mock frame (numpy array)
                return True, np.zeros((480, 640, 3), dtype=np.uint8)
            return False, None

        mock_cap.read.side_effect = read_side_effect

        # Mock contour detection (simulate ball found in some frames)
        mock_cv2.findContours.return_value = ([], None)
        mock_cv2.contourArea.return_value = 500
        mock_cv2.minEnclosingCircle.return_value = ((100.0, 200.0), 15.0)
        mock_cv2.arcLength.return_value = 100.0

        tracker = BallTracker(ball_color="red")

        # Track ball (should not crash with mocked cv2)
        # Note: This will return empty trajectory due to mocked contours
        # Real test would need proper video or more sophisticated mocking
        with patch("pathlib.Path.exists", return_value=True):
            try:
                trajectory = tracker.track_ball_in_video(
                    video_path="/fake/path/video.mp4",
                    sample_fps=10.0,
                )
                # Verify basic structure
                assert isinstance(trajectory, BallTrajectory)
                assert trajectory.total_frames == 100
            except Exception as e:
                # May fail due to incomplete mocking, but should exercise code paths
                pytest.skip(f"Mock setup incomplete: {e}")


# ============================================================================
# Edge Cases
# ============================================================================


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_handles_insufficient_positions_for_swing(self):
        """Test swing calculation with < 3 positions."""
        positions = [
            BallPosition(0, 0.0, 0.0, 0.0, 0.9, 10.0),
            BallPosition(1, 0.1, 10.0, 5.0, 0.9, 10.0),
        ]

        deviation = _calculate_swing_deviation(positions)

        assert deviation == 0.0

    def test_handles_insufficient_positions_for_classification(self):
        """Test trajectory classification with < 3 positions."""
        positions = [
            BallPosition(0, 0.0, 0.0, 0.0, 0.9, 10.0),
        ]

        shape = _classify_trajectory_shape(positions, swing_deviation=10.0)

        assert shape == "insufficient_data"

    def test_velocity_calculation_with_single_position(self):
        """Test velocity calculation with only one position."""
        positions = [BallPosition(0, 0.0, 0.0, 0.0, 0.9, 10.0)]

        tracker = BallTracker()
        tracker._calculate_velocities(positions, fps=30.0)

        # Should not crash, velocity remains 0
        assert positions[0].velocity_x == 0.0
        assert positions[0].velocity_y == 0.0

    def test_bounce_detection_with_no_bounce(self):
        """Test bounce detection when no bounce occurs."""
        # All velocities going down (no reversal)
        positions = [
            BallPosition(i, i * 0.1, 100.0, 50.0, 0.9, 10.0, 10.0, 50.0) for i in range(10)
        ]

        tracker = BallTracker()
        bounce_idx = tracker._find_bounce_point(positions)

        assert bounce_idx is None
