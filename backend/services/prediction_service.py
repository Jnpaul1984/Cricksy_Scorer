"""
AI-powered win/loss prediction service for cricket matches.

This module calculates win probabilities based on current match state using
ML models (XGBoost) with fallback to rule-based predictions.

Strategy:
- First innings: Use ML score predictor to project final score, then calculate win probability
- Second innings: Use ML win predictor with known target
- Fallback: Use rule-based prediction if ML unavailable or fails
"""

from __future__ import annotations

import logging
from typing import Any, Literal

from .ml_features import build_score_predictor_features, build_win_predictor_features
from .ml_model_service import get_ml_service

logger = logging.getLogger(__name__)


class WinProbabilityPredictor:
    """
    Calculates win/loss probabilities for cricket matches based on current state.

    Uses a combination of factors:
    - Current run rate vs required run rate
    - Wickets remaining
    - Balls remaining
    - Target gap (if chasing)
    - Match momentum
    """

    @staticmethod
    def calculate_win_probability(
        *,
        current_inning: int,
        total_runs: int,
        total_wickets: int,
        overs_completed: int,
        balls_this_over: int,
        overs_limit: int | None,
        target: int | None = None,
        match_type: str = "limited",
    ) -> dict[str, Any]:
        """
        Calculate win probability for the batting team.

        Args:
            current_inning: Current innings number (1 or 2)
            total_runs: Current runs scored
            total_wickets: Current wickets fallen
            overs_completed: Complete overs bowled
            balls_this_over: Balls in current over
            overs_limit: Total overs limit for innings
            target: Target score (for second innings)
            match_type: Type of match (limited, multi_day, custom)

        Returns:
            Dictionary containing:
            - batting_team_win_prob: Probability batting team wins (0-100)
            - bowling_team_win_prob: Probability bowling team wins (0-100)
            - confidence: Confidence level of prediction (0-100)
            - factors: Contributing factors to the prediction
        """

        # For first innings, prediction is based on score projection
        if current_inning == 1:
            return WinProbabilityPredictor._first_innings_prediction(
                total_runs=total_runs,
                total_wickets=total_wickets,
                overs_completed=overs_completed,
                balls_this_over=balls_this_over,
                overs_limit=overs_limit,
            )

        # For second innings, prediction is target-based
        return WinProbabilityPredictor._second_innings_prediction(
            total_runs=total_runs,
            total_wickets=total_wickets,
            overs_completed=overs_completed,
            balls_this_over=balls_this_over,
            overs_limit=overs_limit,
            target=target,
        )

    @staticmethod
    def _first_innings_prediction(
        *,
        total_runs: int,
        total_wickets: int,
        overs_completed: int,
        balls_this_over: int,
        overs_limit: int | None,
    ) -> dict[str, Any]:
        """
        Calculate first innings win probability based on projected score.

        Uses ML score predictor if available, falls back to rule-based projection.
        """

        # If overs limit not set, return neutral prediction
        if not overs_limit or overs_limit <= 0:
            return {
                "batting_team_win_prob": 50.0,
                "bowling_team_win_prob": 50.0,
                "confidence": 0.0,
                "factors": {"reason": "Match format requires overs limit for prediction"},
            }

        # Determine match format
        match_format: Literal["t20", "odi"] = "t20" if overs_limit <= 20 else "odi"

        # Try ML prediction first
        try:
            ml_service = get_ml_service()

            # Build features for score predictor
            features = build_score_predictor_features(
                match_format=match_format,
                total_runs=total_runs,
                total_wickets=total_wickets,
                overs_completed=overs_completed,
                balls_this_over=balls_this_over,
                overs_limit=overs_limit,
                is_powerplay=(overs_completed < 6),  # Simple powerplay detection
                recent_overs_data=None,  # Could be enhanced with actual over-by-over data
            )

            # Get ML prediction
            projected_score = ml_service.predict_score(match_format, features)

            # Check if ML returned None
            if projected_score is None:
                raise ValueError("ML model returned None")

            # Calculate win probability from projected score
            par_score = 160.0 if match_format == "t20" else 270.0

            score_diff = projected_score - par_score
            batting_prob = 50.0 + (score_diff / 4.0)
            batting_prob = max(20.0, min(80.0, batting_prob))
            bowling_prob = 100.0 - batting_prob

            # Confidence increases with match progress
            total_balls = overs_completed * 6 + balls_this_over
            total_balls_limit = overs_limit * 6
            progress = total_balls / total_balls_limit
            confidence = min(75.0, progress * 100.0)

            # Calculate current run rate
            current_rr = (total_runs / total_balls) * 6 if total_balls > 0 else 0.0

            logger.info(
                f"ML score prediction: {match_format} format, "
                f"projected={projected_score:.1f}, prob={batting_prob:.1f}%"
            )

            return {
                "batting_team_win_prob": round(batting_prob, 1),
                "bowling_team_win_prob": round(bowling_prob, 1),
                "confidence": round(confidence, 1),
                "factors": {
                    "projected_score": round(projected_score, 0),
                    "par_score": round(par_score, 0),
                    "current_run_rate": round(current_rr, 2),
                    "prediction_method": "ml_score_predictor",
                    "wickets_remaining": 10 - total_wickets,
                    "balls_remaining": total_balls_limit - total_balls,
                },
            }

        except Exception as e:
            logger.warning(
                f"ML score prediction failed for {match_format} format, "
                f"using rule-based fallback: {e}"
            )
            # Fall through to rule-based prediction

        # Rule-based fallback (original implementation)
        # Calculate balls bowled
        total_balls = overs_completed * 6 + balls_this_over
        total_balls_limit = overs_limit * 6

        # Calculate current run rate
        current_rr = (total_runs / total_balls) * 6 if total_balls > 0 else 0.0

        # Early innings - low confidence
        if total_balls < 12:  # Less than 2 overs
            # Project score based on current run rate for early innings
            projected_score = current_rr * overs_limit if current_rr > 0 else 0.0
            return {
                "batting_team_win_prob": 50.0,
                "bowling_team_win_prob": 50.0,
                "confidence": 10.0,
                "factors": {
                    "reason": "Too early to predict reliably",
                    "balls_bowled": total_balls,
                    "current_run_rate": round(current_rr, 2),
                    "projected_score": round(projected_score, 0),
                    "prediction_method": "rule_based_early",
                },
            }

        # Project final score
        wickets_remaining = max(0, 10 - total_wickets)
        balls_remaining = total_balls_limit - total_balls

        # Wicket factor: reduce projected RR as wickets fall
        # Using 20.0 as denominator provides gradual reduction (each wicket reduces by 5%)
        # rather than sharp drop if using 10.0 (each wicket reduces by 10%)
        WICKET_FACTOR_DENOMINATOR = 20.0
        wicket_factor = 1.0 - (total_wickets / WICKET_FACTOR_DENOMINATOR)

        # Project remaining runs
        projected_rr = current_rr * wicket_factor
        projected_remaining_runs = (projected_rr * balls_remaining) / 6
        projected_score = total_runs + projected_remaining_runs

        # Typical T20 scores: 140-180, ODI: 240-300
        # Estimate par score based on format
        if overs_limit <= 20:
            par_score = 160.0  # T20
        elif overs_limit <= 50:
            par_score = 270.0  # ODI
        else:
            par_score = 400.0  # Test/multi-day

        # Calculate advantage
        score_diff = projected_score - par_score

        # Convert to probability (sigmoid-like function)
        # Higher projected score = higher win probability
        batting_prob = 50.0 + (score_diff / 4.0)

        # Clamp between 20-80% for first innings
        batting_prob = max(20.0, min(80.0, batting_prob))
        bowling_prob = 100.0 - batting_prob

        # Confidence increases as match progresses
        progress = total_balls / total_balls_limit
        confidence = min(70.0, progress * 100.0)  # Max 70% in first innings

        return {
            "batting_team_win_prob": round(batting_prob, 1),
            "bowling_team_win_prob": round(bowling_prob, 1),
            "confidence": round(confidence, 1),
            "factors": {
                "projected_score": round(projected_score, 0),
                "par_score": round(par_score, 0),
                "current_run_rate": round(current_rr, 2),
                "wickets_remaining": wickets_remaining,
                "balls_remaining": balls_remaining,
            },
        }

    @staticmethod
    def _second_innings_prediction(
        *,
        total_runs: int,
        total_wickets: int,
        overs_completed: int,
        balls_this_over: int,
        overs_limit: int | None,
        target: int | None,
    ) -> dict[str, Any]:
        """
        Calculate second innings win probability based on target chase.

        Uses ML win predictor if available, falls back to rule-based calculation.
        """

        # Need target for second innings prediction
        if target is None or target <= 0:
            return {
                "batting_team_win_prob": 50.0,
                "bowling_team_win_prob": 50.0,
                "confidence": 0.0,
                "factors": {"reason": "Target not set"},
            }

        if not overs_limit or overs_limit <= 0:
            return {
                "batting_team_win_prob": 50.0,
                "bowling_team_win_prob": 50.0,
                "confidence": 0.0,
                "factors": {"reason": "Overs limit not set"},
            }

        # Calculate balls bowled and remaining
        total_balls = overs_completed * 6 + balls_this_over
        total_balls_limit = overs_limit * 6
        balls_remaining = total_balls_limit - total_balls

        # Calculate runs needed
        runs_needed = target - total_runs
        wickets_remaining = max(0, 10 - total_wickets)

        # Already won or lost
        if runs_needed <= 0:
            return {
                "batting_team_win_prob": 100.0,
                "bowling_team_win_prob": 0.0,
                "confidence": 100.0,
                "factors": {
                    "reason": "Target achieved",
                    "runs_needed": 0,
                },
            }

        if wickets_remaining == 0:
            return {
                "batting_team_win_prob": 0.0,
                "bowling_team_win_prob": 100.0,
                "confidence": 100.0,
                "factors": {
                    "reason": "All out",
                    "wickets_remaining": 0,
                },
            }

        if balls_remaining <= 0:
            return {
                "batting_team_win_prob": 0.0,
                "bowling_team_win_prob": 100.0,
                "confidence": 100.0,
                "factors": {
                    "reason": "Overs completed",
                    "balls_remaining": 0,
                },
            }

        # Determine match format
        match_format: Literal["t20", "odi"] = "t20" if overs_limit <= 20 else "odi"

        # Try ML win prediction first
        try:
            ml_service = get_ml_service()

            # Build features for win predictor
            features = build_win_predictor_features(
                match_format=match_format,
                total_runs=total_runs,
                total_wickets=total_wickets,
                overs_completed=overs_completed,
                balls_this_over=balls_this_over,
                overs_limit=overs_limit,
                target=target,
                recent_overs_data=None,  # Could be enhanced with actual over-by-over data
            )

            # Get ML win probability (returns 0-1, convert to 0-100)
            batting_prob_ml_raw = ml_service.predict_win_probability(match_format, features)

            # Check if ML returned None
            if batting_prob_ml_raw is None:
                raise ValueError("ML model returned None")

            batting_prob_ml = batting_prob_ml_raw * 100.0

            # Confidence increases with match progress
            progress = total_balls / total_balls_limit
            confidence = min(95.0, 40.0 + (progress * 60.0))

            # Calculate required run rate for factors
            required_rr = (runs_needed / balls_remaining) * 6 if balls_remaining > 0 else 99.99
            current_rr = (total_runs / total_balls) * 6 if total_balls > 0 else 0.0

            logger.info(
                f"ML win prediction: {match_format} format, "
                f"prob={batting_prob_ml:.1f}%, RRR={required_rr:.2f}, "
                f"runs_needed={runs_needed}, balls={balls_remaining}"
            )

            batting_prob = batting_prob_ml
            if (
                runs_needed > 0
                and balls_remaining > 0
                and wickets_remaining <= 3
                and required_rr >= 15.0
            ):
                batting_prob = min(batting_prob, 10.0)

            bowling_prob = 100.0 - batting_prob

            return {
                "batting_team_win_prob": round(batting_prob, 1),
                "bowling_team_win_prob": round(bowling_prob, 1),
                "confidence": round(confidence, 1),
                "factors": {
                    "runs_needed": runs_needed,
                    "balls_remaining": balls_remaining,
                    "required_run_rate": round(required_rr, 2),
                    "current_run_rate": round(current_rr, 2),
                    "wickets_remaining": wickets_remaining,
                    "prediction_method": "ml_win_predictor",
                },
            }

        except Exception as e:
            logger.warning(
                f"ML win prediction failed for {match_format} format, "
                f"using rule-based fallback: {e}"
            )
            # Fall through to rule-based prediction

        # Rule-based fallback (original implementation)
        # Calculate required run rate
        required_rr = (runs_needed / balls_remaining) * 6 if balls_remaining > 0 else 99.99

        # Calculate current run rate
        current_rr = (total_runs / total_balls) * 6 if total_balls > 0 else 0.0

        # Pressure index based on RRR vs CRR
        rr_diff = required_rr - current_rr

        # Wicket pressure: fewer wickets = more pressure
        wicket_pressure = 1.0 - (wickets_remaining / 10.0)

        # Ball pressure: fewer balls = more pressure
        ball_pressure = 1.0 - (balls_remaining / total_balls_limit)

        # Combined pressure
        pressure = (rr_diff / 3.0) + (wicket_pressure * 20) + (ball_pressure * 10)

        # Calculate batting probability (inverse of pressure)
        batting_prob = 50.0 - pressure

        # Adjustments
        # If RRR is very high (>12), reduce probability significantly
        if required_rr > 12:
            batting_prob *= 0.6
        # If RRR is reasonable (<6), boost probability
        elif required_rr < 6:
            batting_prob = min(85.0, batting_prob * 1.2)

        # If plenty of wickets remaining and RRR is achievable
        if wickets_remaining >= 7 and required_rr < 8:
            batting_prob = min(80.0, batting_prob + 10)

        # If down to last few wickets
        if wickets_remaining <= 2:
            batting_prob = min(batting_prob, 30.0)

        # Clamp probability
        batting_prob = max(1.0, min(99.0, batting_prob))
        bowling_prob = 100.0 - batting_prob

        # Confidence increases as match progresses
        progress = total_balls / total_balls_limit
        confidence = min(95.0, 30.0 + (progress * 70.0))

        return {
            "batting_team_win_prob": round(batting_prob, 1),
            "bowling_team_win_prob": round(bowling_prob, 1),
            "confidence": round(confidence, 1),
            "factors": {
                "runs_needed": runs_needed,
                "balls_remaining": balls_remaining,
                "required_run_rate": round(required_rr, 2),
                "current_run_rate": round(current_rr, 2),
                "wickets_remaining": wickets_remaining,
            },
        }


def get_win_probability(game_state: dict[str, Any]) -> dict[str, Any]:
    """
    Convenience function to get win probability from game state dict.

    Args:
        game_state: Game state dictionary containing match information

    Returns:
        Win probability prediction dictionary
    """
    predictor = WinProbabilityPredictor()

    return predictor.calculate_win_probability(
        current_inning=game_state.get("current_inning", 1),
        total_runs=game_state.get("total_runs", 0),
        total_wickets=game_state.get("total_wickets", 0),
        overs_completed=game_state.get("overs_completed", 0),
        balls_this_over=game_state.get("balls_this_over", 0),
        overs_limit=game_state.get("overs_limit"),
        target=game_state.get("target"),
        match_type=game_state.get("match_type", "limited"),
    )
