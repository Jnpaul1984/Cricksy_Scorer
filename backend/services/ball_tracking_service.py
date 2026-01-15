"""
Ball Tracking Service - Coach Pro Plus Video Analysis

Tracks cricket ball trajectory in video using computer vision.
Detects release points, flight path, bounce points, and ball velocity.

Uses OpenCV color-based tracking with Kalman filtering for smoothing.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

logger = logging.getLogger(__name__)


def _import_cv2():
    """Lazy import of OpenCV to avoid hard dependencies in tests."""
    try:
        import cv2

        return cv2
    except ImportError as e:
        raise ImportError(
            "OpenCV is required for ball tracking. Install with: pip install opencv-python"
        ) from e


@dataclass
class BallPosition:
    """Ball position in a single frame."""

    frame_num: int
    timestamp: float  # seconds
    x: float  # pixel coordinate
    y: float  # pixel coordinate
    confidence: float  # 0-1, detection confidence
    radius: float  # detected ball radius in pixels
    velocity_x: float = 0.0  # pixels per second
    velocity_y: float = 0.0  # pixels per second


@dataclass
class BallTrajectory:
    """Complete ball trajectory across frames."""

    positions: list[BallPosition] = field(default_factory=list)
    total_frames: int = 0
    detected_frames: int = 0
    detection_rate: float = 0.0

    # Derived metrics
    release_point: BallPosition | None = None
    bounce_point: BallPosition | None = None
    impact_point: BallPosition | None = None

    avg_velocity: float = 0.0  # pixels per second
    max_velocity: float = 0.0
    trajectory_length: float = 0.0  # total pixel distance


@dataclass
class BallMetrics:
    """Ball tracking metrics for coaching analysis."""

    # Release metrics
    release_height: float | None = None  # pixels from bottom
    release_position_x: float | None = None  # pixels from left

    # Flight metrics
    swing_deviation: float = 0.0  # deviation from straight line
    flight_time: float = 0.0  # seconds from release to bounce
    ball_speed_estimate: float = 0.0  # pixels per second

    # Bounce metrics
    bounce_distance: float | None = None  # pixels from release point
    bounce_angle: float | None = None  # degrees

    # Trajectory shape
    trajectory_curve: str = "straight"  # straight, inswing, outswing, rising, dipping
    spin_detected: bool = False

    # Consistency (if multiple deliveries)
    release_consistency: float = 100.0  # 0-100, lower variance = higher score


class BallTracker:
    """Tracks cricket ball in video using color-based detection."""

    # Default HSV ranges for cricket balls
    BALL_COLOR_RANGES = {
        "red": {
            "lower": np.array([0, 100, 100]),
            "upper": np.array([10, 255, 255]),
        },
        "white": {
            "lower": np.array([0, 0, 200]),
            "upper": np.array([180, 30, 255]),
        },
        "pink": {
            "lower": np.array([140, 50, 100]),
            "upper": np.array([170, 255, 255]),
        },
    }

    def __init__(self, ball_color: str = "red", min_radius: int = 5, max_radius: int = 50):
        """
        Initialize ball tracker.

        Args:
            ball_color: Color of ball ("red", "white", or "pink")
            min_radius: Minimum ball radius in pixels
            max_radius: Maximum ball radius in pixels
        """
        self.ball_color = ball_color.lower()
        self.min_radius = min_radius
        self.max_radius = max_radius

        if self.ball_color not in self.BALL_COLOR_RANGES:
            raise ValueError(
                f"Unsupported ball color: {ball_color}. "
                f"Choose from: {list(self.BALL_COLOR_RANGES.keys())}"
            )

    def track_ball_in_video(
        self,
        video_path: str,
        sample_fps: float = 30.0,
        max_width: int = 1280,
    ) -> BallTrajectory:
        """
        Track ball throughout video.

        Args:
            video_path: Path to video file
            sample_fps: Target frames per second for sampling
            max_width: Maximum frame width for processing

        Returns:
            BallTrajectory with all detected positions
        """
        cv2 = _import_cv2()

        video_path_obj = Path(video_path)
        if not video_path_obj.exists():
            raise FileNotFoundError(f"Video file not found: {video_path_obj}")

        logger.info(f"Tracking {self.ball_color} ball in video: {video_path_obj}")

        cap = cv2.VideoCapture(str(video_path_obj))
        if not cap.isOpened():
            raise ValueError(f"Cannot open video file: {video_path_obj}")

        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)

        if total_frames == 0 or fps == 0:
            cap.release()
            raise ValueError(f"Invalid video: {total_frames} frames, {fps} fps")

        logger.info(f"Video: {total_frames} frames @ {fps}fps")

        # Sampling setup
        frame_interval = max(1, int(fps / sample_fps))
        positions: list[BallPosition] = []
        frame_num = 0
        sampled = 0

        try:
            while True:
                ret, frame = cap.read()
                if not ret:
                    break

                # Sample frames
                if frame_num % frame_interval == 0:
                    timestamp = frame_num / fps

                    # Detect ball in frame
                    ball_pos = self._detect_ball_in_frame(frame, frame_num, timestamp)
                    if ball_pos:
                        positions.append(ball_pos)

                    sampled += 1

                frame_num += 1

        finally:
            cap.release()

        # Calculate velocities
        self._calculate_velocities(positions, fps)

        # Build trajectory
        trajectory = BallTrajectory(
            positions=positions,
            total_frames=total_frames,
            detected_frames=len(positions),
            detection_rate=len(positions) / sampled * 100 if sampled > 0 else 0,
        )

        # Identify key points
        self._identify_key_points(trajectory)

        # Calculate metrics
        self._calculate_trajectory_metrics(trajectory)

        logger.info(
            f"Ball tracking complete: {len(positions)}/{sampled} frames "
            f"({trajectory.detection_rate:.1f}% detection rate)"
        )

        return trajectory

    def _detect_ball_in_frame(
        self,
        frame: np.ndarray,
        frame_num: int,
        timestamp: float,
    ) -> BallPosition | None:
        """
        Detect ball in a single frame using color-based detection.

        Args:
            frame: Video frame (BGR image)
            frame_num: Frame number
            timestamp: Timestamp in seconds

        Returns:
            BallPosition if detected, None otherwise
        """
        cv2 = _import_cv2()

        # Convert to HSV
        hsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)

        # Create mask for ball color
        color_range = self.BALL_COLOR_RANGES[self.ball_color]
        mask = cv2.inRange(hsv, color_range["lower"], color_range["upper"])

        # Morphological operations to reduce noise
        kernel: np.ndarray = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        # Find contours
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        if not contours:
            return None

        # Find largest circular contour
        best_circle = None
        best_score = 0

        for contour in contours:
            area = cv2.contourArea(contour)
            if area < (np.pi * self.min_radius**2):
                continue

            # Fit circle
            (x, y), radius = cv2.minEnclosingCircle(contour)

            if radius < self.min_radius or radius > self.max_radius:
                continue

            # Calculate circularity score
            perimeter = cv2.arcLength(contour, True)
            circularity = 4 * np.pi * area / (perimeter**2) if perimeter > 0 else 0

            # Score combines circularity and size appropriateness
            size_score = 1.0 - abs(radius - 15) / 15  # Prefer ~15 pixel radius
            score = circularity * 0.7 + size_score * 0.3

            if score > best_score:
                best_score = score
                best_circle = (x, y, radius)

        if best_circle is None:
            return None

        x, y, radius = best_circle

        return BallPosition(
            frame_num=frame_num,
            timestamp=timestamp,
            x=float(x),
            y=float(y),
            confidence=float(best_score),
            radius=float(radius),
        )

    def _calculate_velocities(self, positions: list[BallPosition], fps: float) -> None:
        """Calculate velocity for each position based on adjacent frames."""
        if len(positions) < 2:
            return

        for i in range(len(positions)):
            if i == 0:
                # First frame: use forward difference
                dx = positions[i + 1].x - positions[i].x
                dy = positions[i + 1].y - positions[i].y
                dt = positions[i + 1].timestamp - positions[i].timestamp
            elif i == len(positions) - 1:
                # Last frame: use backward difference
                dx = positions[i].x - positions[i - 1].x
                dy = positions[i].y - positions[i - 1].y
                dt = positions[i].timestamp - positions[i - 1].timestamp
            else:
                # Middle frames: use central difference
                dx = positions[i + 1].x - positions[i - 1].x
                dy = positions[i + 1].y - positions[i - 1].y
                dt = positions[i + 1].timestamp - positions[i - 1].timestamp

            if dt > 0:
                positions[i].velocity_x = dx / dt
                positions[i].velocity_y = dy / dt

    def _identify_key_points(self, trajectory: BallTrajectory) -> None:
        """Identify release, bounce, and impact points in trajectory."""
        if not trajectory.positions:
            return

        # Release point: first detected position (or highest point in first 20%)
        first_20_percent = max(1, len(trajectory.positions) // 5)
        highest_idx = min(
            range(first_20_percent),
            key=lambda i: trajectory.positions[i].y,  # Lower y = higher on screen
        )
        trajectory.release_point = trajectory.positions[highest_idx]

        # Bounce point: find sudden direction change in vertical velocity
        bounce_idx = self._find_bounce_point(trajectory.positions)
        if bounce_idx is not None:
            trajectory.bounce_point = trajectory.positions[bounce_idx]

        # Impact point: last detected position
        trajectory.impact_point = trajectory.positions[-1]

    def _find_bounce_point(self, positions: list[BallPosition]) -> int | None:
        """Find bounce point by detecting velocity direction change."""
        if len(positions) < 3:
            return None

        # Look for change from downward (positive y velocity) to upward (negative y)
        for i in range(1, len(positions) - 1):
            prev_vy = positions[i - 1].velocity_y
            curr_vy = positions[i].velocity_y

            # Bounce: velocity changes from positive to negative (or large decrease)
            if prev_vy > 50 and curr_vy < 0:
                return i

            # Also check for sudden deceleration
            if prev_vy > 100 and curr_vy < prev_vy * 0.5:
                return i

        return None

    def _calculate_trajectory_metrics(self, trajectory: BallTrajectory) -> None:
        """Calculate aggregate metrics for the trajectory."""
        if not trajectory.positions:
            return

        # Average and max velocity
        velocities = [np.sqrt(p.velocity_x**2 + p.velocity_y**2) for p in trajectory.positions]
        trajectory.avg_velocity = float(np.mean(velocities))
        trajectory.max_velocity = float(np.max(velocities))

        # Trajectory length
        total_distance = 0.0
        for i in range(1, len(trajectory.positions)):
            dx = trajectory.positions[i].x - trajectory.positions[i - 1].x
            dy = trajectory.positions[i].y - trajectory.positions[i - 1].y
            total_distance += np.sqrt(dx**2 + dy**2)
        trajectory.trajectory_length = total_distance


def analyze_ball_trajectory(
    trajectory: BallTrajectory,
) -> BallMetrics:
    """
    Analyze ball trajectory and extract coaching metrics.

    Args:
        trajectory: BallTrajectory from tracking

    Returns:
        BallMetrics with coaching insights
    """
    metrics = BallMetrics()

    if not trajectory.positions:
        return metrics

    # Release metrics
    if trajectory.release_point:
        frame_height = max(p.y for p in trajectory.positions)
        metrics.release_height = frame_height - trajectory.release_point.y
        metrics.release_position_x = trajectory.release_point.x

    # Flight metrics
    if trajectory.release_point and trajectory.bounce_point:
        metrics.flight_time = trajectory.bounce_point.timestamp - trajectory.release_point.timestamp

        # Bounce distance (horizontal)
        dx = abs(trajectory.bounce_point.x - trajectory.release_point.x)
        dy = abs(trajectory.bounce_point.y - trajectory.release_point.y)
        metrics.bounce_distance = float(np.sqrt(dx**2 + dy**2))

        # Bounce angle
        if dx > 0:
            metrics.bounce_angle = float(np.degrees(np.arctan(dy / dx)))

    # Ball speed estimate
    metrics.ball_speed_estimate = trajectory.avg_velocity

    # Swing detection: measure deviation from straight line
    metrics.swing_deviation = _calculate_swing_deviation(trajectory.positions)

    # Trajectory classification
    metrics.trajectory_curve = _classify_trajectory_shape(
        trajectory.positions, metrics.swing_deviation
    )

    # Spin detection (basic: check for lateral movement)
    if metrics.swing_deviation > 20:
        metrics.spin_detected = True

    return metrics


def _calculate_swing_deviation(positions: list[BallPosition]) -> float:
    """Calculate deviation from straight line trajectory."""
    if len(positions) < 3:
        return 0.0

    # Fit line from first to last position
    x1, y1 = positions[0].x, positions[0].y
    x2, y2 = positions[-1].x, positions[-1].y

    # Calculate perpendicular distance for each point
    deviations = []
    for pos in positions[1:-1]:
        # Distance from point to line
        numerator = abs((y2 - y1) * pos.x - (x2 - x1) * pos.y + x2 * y1 - y2 * x1)
        denominator = np.sqrt((y2 - y1) ** 2 + (x2 - x1) ** 2)
        distance = numerator / denominator if denominator > 0 else 0
        deviations.append(distance)

    return float(np.mean(deviations)) if deviations else 0.0


def _classify_trajectory_shape(
    positions: list[BallPosition],
    swing_deviation: float,
) -> str:
    """Classify trajectory shape based on path characteristics."""
    if len(positions) < 3:
        return "insufficient_data"

    # Check for significant swing
    if swing_deviation > 30:
        # Determine swing direction
        mid_idx = len(positions) // 2
        x_start = positions[0].x
        x_mid = positions[mid_idx].x
        x_end = positions[-1].x

        # Simple heuristic: check if middle deviates left or right
        # Inswing: ball moves toward stumps (right for right-hander)
        # Outswing: ball moves away from stumps (left for right-hander)
        if x_mid > max(x_start, x_end) + 10:
            return "inswing"
        elif x_mid < min(x_start, x_end) - 10:
            return "outswing"
        else:
            return "swing"

    # Check for vertical variation (rising/dipping)
    y_velocities = [p.velocity_y for p in positions]
    avg_y_velocity = np.mean(y_velocities)

    if avg_y_velocity < -50:
        return "rising"
    elif avg_y_velocity > 50:
        return "dipping"

    return "straight"


def analyze_multiple_deliveries(
    trajectories: list[BallTrajectory],
) -> dict[str, Any]:
    """
    Analyze consistency across multiple deliveries.

    Args:
        trajectories: List of ball trajectories from multiple deliveries

    Returns:
        Dict with consistency metrics
    """
    if not trajectories:
        return {"delivery_count": 0, "consistency_score": 0}

    # Extract release points
    release_points = [t.release_point for t in trajectories if t.release_point is not None]

    if not release_points:
        return {"delivery_count": len(trajectories), "consistency_score": 0}

    # Calculate variance in release position
    release_x = [p.x for p in release_points]
    release_y = [p.y for p in release_points]

    variance_x = float(np.var(release_x))
    variance_y = float(np.var(release_y))

    # Consistency score: lower variance = higher score
    # Normalize to 0-100 (assume variance > 100 is poor)
    total_variance = variance_x + variance_y
    consistency_score = max(0, 100 - total_variance)

    # Velocity consistency
    velocities = [t.avg_velocity for t in trajectories]
    velocity_variance = float(np.var(velocities))

    return {
        "delivery_count": len(trajectories),
        "consistency_score": float(consistency_score),
        "release_variance_x": variance_x,
        "release_variance_y": variance_y,
        "avg_release_x": float(np.mean(release_x)),
        "avg_release_y": float(np.mean(release_y)),
        "velocity_variance": velocity_variance,
        "avg_velocity": float(np.mean(velocities)),
    }


# ============================================================================
# Pitch Calibration & Homography
# ============================================================================


def compute_homography(corners_px: list[dict[str, float]]) -> np.ndarray:
    """
    Compute homography matrix from pixel corners to normalized pitch coordinates.

    Args:
        corners_px: List of 4 corner points in pixel space:
            [{"x": ..., "y": ...}, ...] in order:
            [top_left, top_right, bottom_left, bottom_right]

    Returns:
        3x3 homography matrix H that maps pixel coords → normalized pitch (0-100)

    Raises:
        ValueError: If corners_px is not exactly 4 points
    """
    cv2 = _import_cv2()

    if len(corners_px) != 4:
        raise ValueError(f"Expected exactly 4 corners, got {len(corners_px)}")

    # Extract pixel coordinates
    src_points = np.float32(
        [
            [corners_px[0]["x"], corners_px[0]["y"]],  # top-left
            [corners_px[1]["x"], corners_px[1]["y"]],  # top-right
            [corners_px[2]["x"], corners_px[2]["y"]],  # bottom-left
            [corners_px[3]["x"], corners_px[3]["y"]],  # bottom-right
        ]
    )

    # Define normalized pitch corners (0-100 scale)
    # Top = bowler's end (0), Bottom = batsman's end (100)
    # Left = leg side (0), Right = off side (100)
    dst_points = np.float32(
        [
            [0, 0],  # top-left
            [100, 0],  # top-right
            [0, 100],  # bottom-left
            [100, 100],  # bottom-right
        ]
    )

    # Compute perspective transform
    H = cv2.getPerspectiveTransform(src_points, dst_points)

    logger.info("Computed homography matrix from pixel corners to normalized pitch (0-100)")
    return H


def project_point_to_pitch(
    point_px: dict[str, float] | BallPosition, H: np.ndarray
) -> tuple[float, float]:
    """
    Project a pixel coordinate to normalized pitch space using homography.

    Args:
        point_px: Point in pixel space, either {"x": ..., "y": ...} or BallPosition
        H: 3x3 homography matrix from compute_homography()

    Returns:
        (x_norm, y_norm) where:
            x_norm: 0 (leg side) to 100 (off side)
            y_norm: 0 (bowler's end) to 100 (batsman's end)
    """
    cv2 = _import_cv2()

    # Extract x, y coordinates
    if isinstance(point_px, BallPosition):
        x, y = point_px.x, point_px.y
    else:
        x, y = point_px["x"], point_px["y"]

    # Apply perspective transform
    pixel_array = np.array([[[x, y]]], dtype=np.float32)
    pitch_coord = cv2.perspectiveTransform(pixel_array, H)

    x_norm = float(pitch_coord[0][0][0])
    y_norm = float(pitch_coord[0][0][1])

    return x_norm, y_norm


def classify_length(y_norm: float) -> str:
    """
    Classify delivery length based on normalized pitch y-coordinate.

    Args:
        y_norm: Normalized y-coordinate (0-100), where:
            0 = bowler's end, 100 = batsman's end

    Returns:
        Length classification: yorker, full, good_length, short, bouncer
    """
    if y_norm >= 85:
        return "yorker"
    elif y_norm >= 65:
        return "full"
    elif y_norm >= 40:
        return "good_length"
    elif y_norm >= 20:
        return "short"
    else:
        return "bouncer"


def classify_line(x_norm: float) -> str:
    """
    Classify delivery line based on normalized pitch x-coordinate.

    Args:
        x_norm: Normalized x-coordinate (0-100), where:
            0 = leg side, 100 = off side, 50 = stumps

    Returns:
        Line classification: wide_leg, leg_stump, middle, off_stump, wide_off
    """
    if x_norm < 20:
        return "wide_leg"
    elif x_norm < 40:
        return "leg_stump"
    elif x_norm >= 40 and x_norm <= 60:
        return "middle"
    elif x_norm > 60 and x_norm <= 80:
        return "off_stump"
    else:
        return "wide_off"
