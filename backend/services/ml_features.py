"""
ML Feature Engineering for Cricket Match Predictions
=====================================================

This module builds feature vectors for ML models from match state data.

Win Predictor Features (12):
- over_progress, balls_left, wickets_left, run_rate, run_rate_last_3
- acceleration, dot_ratio_last_6, boundary_density_last_3
- required_run_rate, runs_needed, wickets_per_over, runs_per_wicket

Score Predictor Features (22):
- runs, overs, wickets, run_rate, balls_left, wickets_left
- last_5_runs, match_phase_id, dot_ratio_last_over, strike_rotation_last_6
- run_rate_last_5, boundary_ratio, momentum, wickets_last_5
- run_rate_variance, overs_remaining, wickets_per_over, runs_per_wicket
- balls_per_wicket, in_powerplay, projected_score_simple, balls_remaining
"""

from typing import Any

import numpy as np


def build_win_predictor_features(
    *,
    match_format: str,
    total_runs: int,
    total_wickets: int,
    overs_completed: int,
    balls_this_over: int,
    overs_limit: int,
    target: int,
    recent_overs_data: list[dict[str, Any]] | None = None,
) -> np.ndarray:
    """
    Build 12-feature vector for win probability prediction.

    Args:
        match_format: 't20' or 'odi'
        total_runs: Current runs scored
        total_wickets: Current wickets fallen
        overs_completed: Complete overs bowled
        balls_this_over: Balls in current over (0-5)
        overs_limit: Total overs for the innings
        target: Target score (for second innings)
        recent_overs_data: Optional list of recent over data for rolling features

    Returns:
        numpy array of shape (12,) with feature values
    """

    # Calculate basic values
    total_balls_bowled = overs_completed * 6 + balls_this_over
    balls_remaining = (overs_limit * 6) - total_balls_bowled
    wickets_remaining = 10 - total_wickets

    # Avoid division by zero
    completed_overs_safe = max(overs_completed + (balls_this_over / 6), 0.1)

    # Feature 1: over_progress (0-1)
    over_progress = completed_overs_safe / overs_limit if overs_limit > 0 else 0.0

    # Feature 2: balls_left
    balls_left = float(balls_remaining)

    # Feature 3: wickets_left
    wickets_left = float(wickets_remaining)

    # Feature 4: run_rate
    run_rate = total_runs / completed_overs_safe

    # Feature 5-8: Rolling features (simplified if no recent data)
    if recent_overs_data and len(recent_overs_data) >= 3:
        # Calculate from recent overs
        recent_3_runs = sum(over.get("runs", 0) for over in recent_overs_data[-3:])
        run_rate_last_3 = recent_3_runs / 3.0

        recent_6_balls = []
        recent_3_boundaries = 0
        for over in recent_overs_data[-2:]:  # Last 2 overs ~= last 6 balls sample
            balls = over.get("balls", [])
            recent_6_balls.extend(balls)
            recent_3_boundaries += sum(1 for b in balls if b.get("runs", 0) >= 4)

        dots_in_recent = sum(1 for b in recent_6_balls[-6:] if b.get("runs", 0) == 0)
        dot_ratio_last_6 = dots_in_recent / max(len(recent_6_balls[-6:]), 1)
        boundary_density_last_3 = recent_3_boundaries / max(len(recent_6_balls), 1)
    else:
        # Fallback: use current run rate as approximation
        run_rate_last_3 = run_rate * 0.9  # Assume slight deceleration
        dot_ratio_last_6 = 0.3  # Average dot ball ratio
        boundary_density_last_3 = 0.15  # Average boundary density

    # Feature 6: acceleration
    acceleration = run_rate - run_rate_last_3

    # Feature 9: required_run_rate
    runs_needed = target - total_runs
    required_run_rate = (runs_needed * 6.0) / max(balls_remaining, 1)

    # Feature 10: runs_needed
    runs_needed_float = float(runs_needed)

    # Feature 11: wickets_per_over
    wickets_per_over = total_wickets / completed_overs_safe

    # Feature 12: runs_per_wicket
    runs_per_wicket = total_runs / max(total_wickets, 1)

    # Build feature vector in exact order
    features = np.array(
        [
            over_progress,
            balls_left,
            wickets_left,
            run_rate,
            run_rate_last_3,
            acceleration,
            dot_ratio_last_6,
            boundary_density_last_3,
            required_run_rate,
            runs_needed_float,
            wickets_per_over,
            runs_per_wicket,
        ],
        dtype=np.float32,
    )

    # Replace any NaN/inf with 0
    features = np.nan_to_num(features, nan=0.0, posinf=999.0, neginf=-999.0)

    return features


def build_score_predictor_features(
    *,
    match_format: str,
    total_runs: int,
    total_wickets: int,
    overs_completed: int,
    balls_this_over: int,
    overs_limit: int,
    is_powerplay: bool = False,
    recent_overs_data: list[dict[str, Any]] | None = None,
) -> np.ndarray:
    """
    Build 22-feature vector for score prediction (first innings).

    Args:
        match_format: 't20' or 'odi'
        total_runs: Current runs scored (same as 'runs')
        total_wickets: Current wickets fallen (same as 'wickets')
        overs_completed: Complete overs bowled
        balls_this_over: Balls in current over (0-5)
        overs_limit: Total overs for the innings
        is_powerplay: Whether currently in powerplay
        recent_overs_data: Optional list of recent over data for rolling features

    Returns:
        numpy array of shape (22,) with feature values
    """

    # Calculate basic values
    total_balls_bowled = overs_completed * 6 + balls_this_over
    balls_remaining = (overs_limit * 6) - total_balls_bowled
    wickets_remaining = 10 - total_wickets

    # Avoid division by zero
    completed_overs_safe = max(overs_completed + (balls_this_over / 6), 0.1)
    overs_remaining = balls_remaining / 6.0

    # Feature 1: runs (same as total_runs)
    runs = float(total_runs)

    # Feature 2: overs (fractional)
    overs = completed_overs_safe

    # Feature 3: wickets
    wickets = float(total_wickets)

    # Feature 4: run_rate
    run_rate = total_runs / completed_overs_safe

    # Feature 5: balls_left
    balls_left = float(balls_remaining)

    # Feature 6: wickets_left
    wickets_left = float(wickets_remaining)

    # Feature 7-14: Rolling features (simplified if no recent data)
    if recent_overs_data and len(recent_overs_data) >= 5:
        # Last 5 runs
        recent_5_runs = sum(over.get("runs", 0) for over in recent_overs_data[-5:])
        last_5_runs = float(recent_5_runs)

        # Run rate last 5
        run_rate_last_5 = recent_5_runs / 5.0

        # Collect recent balls for dot/boundary/strike rotation
        recent_10_balls = []
        for over in recent_overs_data[-2:]:  # ~last 10-12 balls
            balls = over.get("balls", [])
            recent_10_balls.extend(balls)

        recent_6_balls = (
            recent_10_balls[-6:] if len(recent_10_balls) >= 6 else recent_10_balls
        )

        # Dot ratio last over
        dots = sum(1 for b in recent_6_balls if b.get("runs", 0) == 0)
        dot_ratio_last_over = dots / max(len(recent_6_balls), 1)

        # Strike rotation (singles/twos)
        singles_twos = sum(1 for b in recent_6_balls if 1 <= b.get("runs", 0) <= 2)
        strike_rotation_last_6 = singles_twos / max(len(recent_6_balls), 1)

        # Boundary ratio
        boundaries = sum(1 for b in recent_10_balls if b.get("runs", 0) >= 4)
        boundary_ratio = boundaries / max(len(recent_10_balls), 1)

        # Momentum (change in run rate)
        if len(recent_overs_data) >= 3:
            rr_recent = [over.get("runs", 0) for over in recent_overs_data[-3:]]
            momentum = np.mean(np.diff(rr_recent)) if len(rr_recent) > 1 else 0.0
        else:
            momentum = 0.0

        # Wickets last 5
        wickets_last_5 = sum(over.get("wickets", 0) for over in recent_overs_data[-5:])

        # Run rate variance
        if len(recent_overs_data) >= 5:
            rr_values = [over.get("runs", 0) for over in recent_overs_data[-5:]]
            run_rate_variance = float(np.std(rr_values))
        else:
            run_rate_variance = 0.0

    else:
        # Fallback approximations
        last_5_runs = run_rate * 5.0  # Approximate
        run_rate_last_5 = run_rate
        dot_ratio_last_over = 0.3
        strike_rotation_last_6 = 0.4
        boundary_ratio = 0.15
        momentum = 0.0
        wickets_last_5 = 0.0
        run_rate_variance = 2.0  # Default variance

    # Feature 8: match_phase_id (0=early, 1=middle, 2=death)
    if match_format == "t20":
        if overs_completed < 6:
            match_phase_id = 0
        elif overs_completed < 15:
            match_phase_id = 1
        else:
            match_phase_id = 2
    else:  # odi
        if overs_completed < 10:
            match_phase_id = 0
        elif overs_completed < 40:
            match_phase_id = 1
        else:
            match_phase_id = 2

    # Feature 15-22: Additional context features
    wickets_per_over = total_wickets / completed_overs_safe
    runs_per_wicket = total_runs / max(total_wickets, 1)
    balls_per_wicket = total_balls_bowled / max(total_wickets, 1)
    in_powerplay = 1.0 if is_powerplay else 0.0
    projected_score_simple = total_runs + (run_rate * overs_remaining)

    # Build feature vector in exact order (22 features)
    features = np.array(
        [
            runs,  # 1
            overs,  # 2
            wickets,  # 3
            run_rate,  # 4
            balls_left,  # 5
            wickets_left,  # 6
            last_5_runs,  # 7
            match_phase_id,  # 8
            dot_ratio_last_over,  # 9
            strike_rotation_last_6,  # 10
            run_rate_last_5,  # 11
            boundary_ratio,  # 12
            momentum,  # 13
            wickets_last_5,  # 14
            run_rate_variance,  # 15
            overs_remaining,  # 16
            wickets_per_over,  # 17
            runs_per_wicket,  # 18
            balls_per_wicket,  # 19
            in_powerplay,  # 20
            projected_score_simple,  # 21
            balls_remaining,  # 22
        ],
        dtype=np.float32,
    )

    # Replace any NaN/inf with sensible defaults
    features = np.nan_to_num(features, nan=0.0, posinf=999.0, neginf=-999.0)

    return features
