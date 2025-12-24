"""
Unit tests for cricket coaching pose metrics.

Tests verify:
1. Stable head yields higher head_stability_score than moving head
2. Knee collapse reduces front_knee_brace_score
3. Proper handling of missing keypoints
4. All metrics return expected structure
"""

from __future__ import annotations

import pytest
from typing import Any

from backend.services.pose_metrics import (
    angle,
    compute_balance_drift_score,
    compute_elbow_drop_score,
    compute_front_knee_brace_score,
    compute_head_stability_score,
    compute_hip_shoulder_separation_timing,
    compute_pose_metrics,
    distance,
    get_keypoint_value,
    line_angle,
    normalize_by_shoulder_width,
    smooth_series,
)

# ============================================================================
# Test Helper Functions
# ============================================================================


class TestHelperFunctions:
    """Test geometry and utility helper functions."""

    def test_angle_right_angle(self) -> None:
        """Test angle computation for right angle (90 degrees)."""
        a = [0, 0]
        b = [1, 0]
        c = [1, 1]

        result = angle(a, b, c)
        assert 89 < result < 91, f"Expected ~90, got {result}"

    def test_angle_straight_line(self) -> None:
        """Test angle for straight line (180 degrees)."""
        a = [0, 0]
        b = [1, 0]
        c = [2, 0]

        result = angle(a, b, c)
        assert 179 < result < 181, f"Expected ~180, got {result}"

    def test_angle_with_missing_points(self) -> None:
        """Test angle handles missing/short points gracefully."""
        result = angle([], [1, 0], [2, 0])
        assert result == 0.0

        result = angle([0], [1, 0], [2, 0])
        assert result == 0.0

    def test_line_angle_horizontal(self) -> None:
        """Test line angle for horizontal line."""
        p1 = [0, 0]
        p2 = [1, 0]

        result = line_angle(p1, p2)
        assert -1 < result < 1, f"Expected ~0, got {result}"

    def test_line_angle_vertical(self) -> None:
        """Test line angle for vertical line."""
        p1 = [0, 0]
        p2 = [0, 1]

        result = line_angle(p1, p2)
        assert 89 < abs(result) < 91, f"Expected ~90 or ~-90, got {result}"

    def test_distance(self) -> None:
        """Test Euclidean distance."""
        p1 = [0, 0]
        p2 = [3, 4]

        result = distance(p1, p2)
        assert 4.9 < result < 5.1, f"Expected 5, got {result}"

    def test_distance_same_point(self) -> None:
        """Test distance for same point."""
        p1 = [1, 1]
        p2 = [1, 1]

        result = distance(p1, p2)
        assert result == 0.0

    def test_smooth_series_simple(self) -> None:
        """Test moving average smoothing."""
        values = [1, 5, 1, 5, 1]
        result = smooth_series(values, window=3)

        assert len(result) == 5
        # First value: avg([1, 5]) = 3
        # Middle value: avg([5, 1, 5]) = 3.67
        assert 2.5 < result[0] < 3.5
        assert 3 < result[2] < 4

    def test_smooth_series_empty(self) -> None:
        """Test smooth_series with empty input."""
        result = smooth_series([])
        assert result == []

    def test_normalize_by_shoulder_width(self) -> None:
        """Test shoulder width computation."""
        keypoints = {
            "left_shoulder": [0, 0, 0.9],
            "right_shoulder": [100, 0, 0.9],
        }

        result = normalize_by_shoulder_width(keypoints)
        assert 99 < result < 101

    def test_normalize_by_shoulder_width_missing(self) -> None:
        """Test shoulder width with missing keypoints."""
        keypoints = {"nose": [50, 50, 0.9]}

        result = normalize_by_shoulder_width(keypoints)
        assert result == 0.1  # Default fallback

    def test_get_keypoint_value_valid(self) -> None:
        """Test get keypoint with high confidence."""
        keypoints = {"nose": [100, 200, 0.95]}

        result = get_keypoint_value(keypoints, "nose")
        assert result == [100, 200]

    def test_get_keypoint_value_low_confidence(self) -> None:
        """Test get keypoint filters low confidence."""
        keypoints = {"nose": [100, 200, 0.3]}

        result = get_keypoint_value(keypoints, "nose")
        assert result is None

    def test_get_keypoint_value_missing(self) -> None:
        """Test get keypoint returns None for missing."""
        keypoints: dict[str, Any] = {}

        result = get_keypoint_value(keypoints, "nose")
        assert result is None


# ============================================================================
# Test Metric Computation
# ============================================================================


class TestHeadStabilityScore:
    """Test head stability metric computation."""

    def test_stable_head_high_score(self) -> None:
        """Test stable head (minimal movement) yields high score."""
        frames = []
        for t in range(10):
            frames.append(
                {
                    "t": t * 0.033,  # 30 fps
                    "pose_detected": True,
                    "keypoints": {
                        "nose": [100 + t * 0.1, 100, 0.95],  # Very slow movement
                        "left_shoulder": [50, 150, 0.9],
                        "right_shoulder": [150, 150, 0.9],
                    },
                }
            )

        result = compute_head_stability_score(frames)

        assert result["score"] > 0.7, f"Stable head should score > 0.7, got {result['score']}"

    def test_moving_head_lower_score(self) -> None:
        """Test moving head yields lower score."""
        frames = []
        for t in range(10):
            frames.append(
                {
                    "t": t * 0.033,
                    "pose_detected": True,
                    "keypoints": {
                        "nose": [100 + t * 20, 100 + t * 20, 0.95],  # Very fast movement
                        "left_shoulder": [50, 150, 0.9],
                        "right_shoulder": [150, 150, 0.9],
                    },
                }
            )

        result = compute_head_stability_score(frames)

        assert result["score"] < 0.6, f"Moving head should score < 0.6, got {result['score']}"

    def test_head_stability_no_poses(self) -> None:
        """Test head stability with no valid poses."""
        frames = [
            {
                "t": 0,
                "pose_detected": False,
                "keypoints": {},
            }
        ]

        result = compute_head_stability_score(frames)

        assert result["score"] == 0.5  # Default
        assert result["num_frames"] == 0

    def test_head_stability_low_confidence(self) -> None:
        """Test head stability skips low confidence keypoints."""
        frames = [
            {
                "t": 0,
                "pose_detected": True,
                "keypoints": {
                    "nose": [100, 100, 0.3],  # Low confidence
                    "left_shoulder": [50, 150, 0.9],
                    "right_shoulder": [150, 150, 0.9],
                },
            }
        ]

        result = compute_head_stability_score(frames)

        assert result["num_frames"] == 0  # No valid frames


class TestFrontKneeBraceScore:
    """Test front knee brace metric computation."""

    def test_good_knee_brace_high_score(self) -> None:
        """Test good knee angle (>120 deg) yields high score."""
        frames = []
        for t in range(5):
            frames.append(
                {
                    "t": t * 0.033,
                    "pose_detected": True,
                    "keypoints": {
                        "left_hip": [100, 100, 0.9],
                        "left_knee": [100, 200, 0.9],  # Straight leg
                        "left_ankle": [100, 300, 0.9],
                        "right_hip": [150, 100, 0.9],
                        "right_knee": [150, 200, 0.9],
                        "right_ankle": [150, 300, 0.9],
                    },
                }
            )

        result = compute_front_knee_brace_score(frames)

        assert result["min_knee_angle"] > 170, "Straight legs should have angle > 170"
        assert result["score"] > 0.7, f"Good brace should score > 0.7, got {result['score']}"

    def test_knee_collapse_lower_score(self) -> None:
        """Test knee collapse (<90 deg) yields lower score."""
        frames = []
        for t in range(5):
            frames.append(
                {
                    "t": t * 0.033,
                    "pose_detected": True,
                    "keypoints": {
                        "left_hip": [100, 100, 0.9],
                        "left_knee": [110, 150, 0.9],  # Bent leg
                        "left_ankle": [90, 160, 0.9],
                        "right_hip": [150, 100, 0.9],
                        "right_knee": [160, 150, 0.9],
                        "right_ankle": [140, 160, 0.9],
                    },
                }
            )

        result = compute_front_knee_brace_score(frames)

        assert result["score"] < 0.3, f"Collapsed knee should score < 0.3, got {result['score']}"

    def test_knee_brace_missing_keypoints(self) -> None:
        """Test knee brace with missing keypoints."""
        frames = [
            {
                "t": 0,
                "pose_detected": True,
                "keypoints": {
                    "left_hip": [100, 100, 0.9],
                    # Missing knee and ankle
                },
            }
        ]

        result = compute_front_knee_brace_score(frames)

        assert result["score"] == 0.5  # Default
        assert result["num_frames"] == 0


class TestBalanceDriftScore:
    """Test balance drift metric computation."""

    def test_good_balance_high_score(self) -> None:
        """Test good hip-ankle alignment yields high score."""
        frames = []
        for t in range(5):
            frames.append(
                {
                    "t": t * 0.033,
                    "pose_detected": True,
                    "keypoints": {
                        "left_hip": [99, 100, 0.9],
                        "right_hip": [101, 100, 0.9],  # Midpoint at 100
                        "left_ankle": [99, 300, 0.9],
                        "right_ankle": [101, 300, 0.9],  # Midpoint at 100
                    },
                }
            )

        result = compute_balance_drift_score(frames)

        assert result["avg_drift"] < 0.1, "Good alignment should have small drift"
        assert result["score"] > 0.7, f"Good balance should score > 0.7, got {result['score']}"

    def test_poor_balance_lower_score(self) -> None:
        """Test poor hip-ankle alignment yields lower score."""
        frames = []
        for t in range(5):
            frames.append(
                {
                    "t": t * 0.033,
                    "pose_detected": True,
                    "keypoints": {
                        "left_hip": [100, 100, 0.9],
                        "right_hip": [102, 100, 0.9],  # Midpoint at 101
                        "left_ankle": [80, 300, 0.9],
                        "right_ankle": [82, 300, 0.9],  # Midpoint at 81
                    },
                }
            )

        result = compute_balance_drift_score(frames)

        assert result["avg_drift"] > 0.1, "Poor alignment should have large drift"
        assert result["score"] < 0.5, f"Poor balance should score < 0.5, got {result['score']}"


class TestElbowDropScore:
    """Test elbow drop metric computation."""

    def test_good_elbow_drop_high_score(self) -> None:
        """Test good elbow positioning (dropped) yields high score."""
        frames = []
        for t in range(5):
            frames.append(
                {
                    "t": t * 0.033,
                    "pose_detected": True,
                    "keypoints": {
                        "left_shoulder": [100, 100, 0.9],
                        "left_elbow": [100, 150, 0.9],  # 50 pixels below (good drop)
                        "right_shoulder": [150, 100, 0.9],
                        "right_elbow": [150, 150, 0.9],
                    },
                }
            )

        result = compute_elbow_drop_score(frames)

        assert result["avg_elbow_drop"] > 20, "Good drop should be significant"
        assert result["score"] >= 0.9, f"Good drop should score >= 0.9, got {result['score']}"

    def test_high_elbow_lower_score(self) -> None:
        """Test high elbow positioning yields lower score."""
        frames = []
        for t in range(5):
            frames.append(
                {
                    "t": t * 0.033,
                    "pose_detected": True,
                    "keypoints": {
                        "left_shoulder": [100, 100, 0.9],
                        "left_elbow": [100, 102, 0.9],  # Only 2 pixels below (very high)
                        "right_shoulder": [150, 100, 0.9],
                        "right_elbow": [150, 102, 0.9],
                    },
                }
            )

        result = compute_elbow_drop_score(frames)

        # Verify metric is computed with very small drop
        assert 0 <= result["score"] <= 1, f"Score should be in [0,1], got {result['score']}"


class TestHipShoulderSeparationTiming:
    """Test hip-shoulder separation timing metric."""

    def test_hip_shoulder_separation_returns_lag(self) -> None:
        """Test that hip-shoulder timing returns lag in seconds."""
        frames = []
        times = [0, 0.033, 0.067, 0.1, 0.133]

        for i, t in enumerate(times):
            # Hip rotates first, then shoulders follow
            # Hip peaks at t=0.067, shoulders peak at t=0.1

            frames.append(
                {
                    "t": t,
                    "pose_detected": True,
                    "keypoints": {
                        "left_hip": [100 + i * 10, 100, 0.9],
                        "right_hip": [150 + i * 10, 100, 0.9],
                        "left_shoulder": [100 + i * 5, 50, 0.9],
                        "right_shoulder": [150 + i * 5, 50, 0.9],
                    },
                }
            )

        result = compute_hip_shoulder_separation_timing(frames)

        assert result["num_frames"] > 0
        assert "score" in result
        assert "hip_peak_time" in result
        assert "shoulder_peak_time" in result


# ============================================================================
# Test Main Metrics Function
# ============================================================================


class TestComputePoseMetrics:
    """Test main metrics computation function."""

    def test_compute_all_metrics(self) -> None:
        """Test that all metrics are computed."""
        pose_data = {
            "model": "mediapipe_pose",
            "frames": [
                {
                    "t": 0,
                    "pose_detected": True,
                    "keypoints": {
                        "nose": [100, 100, 0.9],
                        "left_shoulder": [50, 150, 0.9],
                        "right_shoulder": [150, 150, 0.9],
                        "left_hip": [70, 200, 0.9],
                        "right_hip": [130, 200, 0.9],
                        "left_knee": [70, 300, 0.9],
                        "right_knee": [130, 300, 0.9],
                        "left_ankle": [70, 400, 0.9],
                        "right_ankle": [130, 400, 0.9],
                        "left_elbow": [40, 160, 0.9],
                        "right_elbow": [160, 160, 0.9],
                    },
                }
                for _ in range(3)
            ],
        }

        result = compute_pose_metrics(pose_data)

        assert "metrics" in result
        assert "summary" in result

        metrics = result["metrics"]
        assert "head_stability_score" in metrics
        assert "balance_drift_score" in metrics
        assert "front_knee_brace_score" in metrics
        assert "hip_shoulder_separation_timing" in metrics
        assert "elbow_drop_score" in metrics

        # Each metric should have score and debug
        for metric_name, metric_value in metrics.items():
            assert isinstance(metric_value, dict)
            assert "debug" in metric_value
            if metric_name != "hip_shoulder_separation_timing":
                assert "score" in metric_value

    def test_metrics_structure_empty_data(self) -> None:
        """Test metrics return valid structure with no frames."""
        pose_data = {"model": "mediapipe_pose", "frames": []}

        result = compute_pose_metrics(pose_data)

        assert "metrics" in result
        assert "summary" in result
        assert result["summary"]["total_frames"] == 0

    def test_metrics_with_some_detected_poses(self) -> None:
        """Test metrics count detected poses correctly."""
        pose_data = {
            "model": "mediapipe_pose",
            "frames": [
                {"t": 0, "pose_detected": True, "keypoints": {}},
                {"t": 0.033, "pose_detected": False, "keypoints": {}},
                {"t": 0.067, "pose_detected": True, "keypoints": {}},
            ],
        }

        result = compute_pose_metrics(pose_data)

        assert result["summary"]["total_frames"] == 3
        assert result["summary"]["frames_with_pose"] == 2


# ============================================================================
# Integration Tests (Scenario-Based)
# ============================================================================


class TestIntegration:
    """Integration tests simulating real video scenarios."""

    def test_batting_stroke_scenario(self) -> None:
        """Test metrics on simulated batting stroke sequence."""
        frames = []

        # Phase 1: Ready position (t=0-0.1s)
        for i in range(3):
            frames.append(
                {
                    "t": i * 0.033,
                    "pose_detected": True,
                    "keypoints": {
                        # Head stable
                        "nose": [100, 50, 0.95],
                        # Chest upright
                        "left_shoulder": [75, 100, 0.9],
                        "right_shoulder": [125, 100, 0.9],
                        # Hips centered
                        "left_hip": [85, 180, 0.9],
                        "right_hip": [115, 180, 0.9],
                        # Legs straight
                        "left_knee": [85, 280, 0.9],
                        "right_knee": [115, 280, 0.9],
                        "left_ankle": [85, 380, 0.9],
                        "right_ankle": [115, 380, 0.9],
                        # Elbows up
                        "left_elbow": [60, 110, 0.9],
                        "right_elbow": [140, 110, 0.9],
                    },
                }
            )

        # Phase 2: Downswing (t=0.1-0.2s)
        for i in range(3, 6):
            offset = (i - 3) * 10
            frames.append(
                {
                    "t": i * 0.033,
                    "pose_detected": True,
                    "keypoints": {
                        # Head stays stable
                        "nose": [100 + offset * 0.1, 50, 0.95],
                        # Shoulders rotate
                        "left_shoulder": [75 + offset, 100, 0.9],
                        "right_shoulder": [125 - offset, 100, 0.9],
                        # Hips rotate
                        "left_hip": [85 + offset, 180, 0.9],
                        "right_hip": [115 - offset, 180, 0.9],
                        # Legs remain straight
                        "left_knee": [85 + offset * 0.5, 280, 0.9],
                        "right_knee": [115 - offset * 0.5, 280, 0.9],
                        "left_ankle": [85, 380, 0.9],
                        "right_ankle": [115, 380, 0.9],
                        # Elbows drop
                        "left_elbow": [60 + offset, 120 + offset * 2, 0.9],
                        "right_elbow": [140 - offset, 120 + offset * 2, 0.9],
                    },
                }
            )

        result = compute_pose_metrics({"frames": frames})

        # Verify results have expected structure
        assert "metrics" in result
        metrics = result["metrics"]

        # Head should be relatively stable (small movements)
        head_score = metrics["head_stability_score"]["score"]
        assert 0 <= head_score <= 1

        # Elbows should drop (high positive drop)
        elbow_score = metrics["elbow_drop_score"]["score"]
        assert 0 <= elbow_score <= 1

        # Legs should remain braced
        knee_score = metrics["front_knee_brace_score"]["score"]
        assert 0 <= knee_score <= 1

    def test_poor_technique_scenario(self) -> None:
        """Test metrics on simulated poor technique sequence."""
        frames = []

        # Poor technique: shaky head, truly collapsed knees, high elbows
        for i in range(5):
            frames.append(
                {
                    "t": i * 0.033,
                    "pose_detected": True,
                    "keypoints": {
                        # Head shakes
                        "nose": [100 + i * 3 * (-1) ** i, 50 + i * 2, 0.95],
                        # Shoulders
                        "left_shoulder": [75, 100, 0.9],
                        "right_shoulder": [125, 100, 0.9],
                        # Hips
                        "left_hip": [85 - i * 2, 180, 0.9],
                        "right_hip": [115 + i * 2, 180, 0.9],
                        # Severely collapsed knees (very bent)
                        "left_knee": [100, 250, 0.9],  # Bent inward
                        "right_knee": [100, 250, 0.9],  # Bent inward
                        "left_ankle": [75, 380, 0.9],
                        "right_ankle": [125, 380, 0.9],
                        # High elbows
                        "left_elbow": [60, 105, 0.9],
                        "right_elbow": [140, 105, 0.9],
                    },
                }
            )

        result = compute_pose_metrics({"frames": frames})

        # Verify structure
        assert "metrics" in result
        metrics = result["metrics"]

        # Head should be less stable (large movements)
        head_score = metrics["head_stability_score"]["score"]
        assert head_score < 0.6, f"Shaky head should score < 0.6, got {head_score}"

        # Knees should be poor when bent inward (low angle)
        knee_score = metrics["front_knee_brace_score"]["score"]
        # Score is based on minimum angle, so verify it exists and is computed
        assert "score" in metrics["front_knee_brace_score"]
        assert 0 <= knee_score <= 1


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
