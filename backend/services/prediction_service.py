"""
AI-powered win/loss prediction service for cricket matches.

This module calculates win probabilities based on current match state using
cricket-specific factors and historical patterns.
"""

from __future__ import annotations
import math
from typing import Any, Dict, Optional


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
        overs_limit: Optional[int],
        target: Optional[int] = None,
        match_type: str = "limited",
    ) -> Dict[str, Any]:
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
        overs_limit: Optional[int],
    ) -> Dict[str, Any]:
        """
        Calculate first innings win probability based on projected score.
        """
        
        # If overs limit not set, return neutral prediction
        if not overs_limit or overs_limit <= 0:
            return {
                "batting_team_win_prob": 50.0,
                "bowling_team_win_prob": 50.0,
                "confidence": 0.0,
                "factors": {
                    "reason": "Match format requires overs limit for prediction"
                }
            }
        
        # Calculate balls bowled
        total_balls = overs_completed * 6 + balls_this_over
        total_balls_limit = overs_limit * 6
        
        # Early innings - low confidence
        if total_balls < 12:  # Less than 2 overs
            return {
                "batting_team_win_prob": 50.0,
                "bowling_team_win_prob": 50.0,
                "confidence": 10.0,
                "factors": {
                    "reason": "Too early to predict reliably",
                    "balls_bowled": total_balls,
                }
            }
        
        # Calculate current run rate
        current_rr = (total_runs / total_balls) * 6 if total_balls > 0 else 0.0
        
        # Project final score
        wickets_remaining = 10 - total_wickets
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
            }
        }

    @staticmethod
    def _second_innings_prediction(
        *,
        total_runs: int,
        total_wickets: int,
        overs_completed: int,
        balls_this_over: int,
        overs_limit: Optional[int],
        target: Optional[int],
    ) -> Dict[str, Any]:
        """
        Calculate second innings win probability based on target chase.
        """
        
        # Need target for second innings prediction
        if target is None or target <= 0:
            return {
                "batting_team_win_prob": 50.0,
                "bowling_team_win_prob": 50.0,
                "confidence": 0.0,
                "factors": {
                    "reason": "Target not set"
                }
            }
        
        if not overs_limit or overs_limit <= 0:
            return {
                "batting_team_win_prob": 50.0,
                "bowling_team_win_prob": 50.0,
                "confidence": 0.0,
                "factors": {
                    "reason": "Overs limit not set"
                }
            }
        
        # Calculate balls bowled and remaining
        total_balls = overs_completed * 6 + balls_this_over
        total_balls_limit = overs_limit * 6
        balls_remaining = total_balls_limit - total_balls
        
        # Calculate runs needed
        runs_needed = target - total_runs
        wickets_remaining = 10 - total_wickets
        
        # Already won or lost
        if runs_needed <= 0:
            return {
                "batting_team_win_prob": 100.0,
                "bowling_team_win_prob": 0.0,
                "confidence": 100.0,
                "factors": {
                    "reason": "Target achieved",
                    "runs_needed": 0,
                }
            }
        
        if wickets_remaining == 0:
            return {
                "batting_team_win_prob": 0.0,
                "bowling_team_win_prob": 100.0,
                "confidence": 100.0,
                "factors": {
                    "reason": "All out",
                    "wickets_remaining": 0,
                }
            }
        
        if balls_remaining <= 0:
            return {
                "batting_team_win_prob": 0.0,
                "bowling_team_win_prob": 100.0,
                "confidence": 100.0,
                "factors": {
                    "reason": "Overs completed",
                    "balls_remaining": 0,
                }
            }
        
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
            }
        }


def get_win_probability(game_state: Dict[str, Any]) -> Dict[str, Any]:
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
