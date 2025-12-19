"""
Innings performance grading service for cricket matches.

This module calculates letter grades (A+, A, B, C, D) for batting innings performance
based on multiple factors including run rate, wicket management, and strike rotation.

Grading Scale:
- A+: >150% of par score (exceptional innings)
- A: 130-150% of par score (very good innings)
- B: 100-130% of par score (good innings)
- C: 70-100% of par score (average innings)
- D: <70% of par score (below average innings)

Additional factors considered:
- Wickets preserved (lower wicket loss = higher grade)
- Strike rotation quality (fewer dot balls = higher grade)
- Boundary percentage (high boundary count = higher grade)
"""

from __future__ import annotations

import logging
from typing import Any, Literal

logger = logging.getLogger(__name__)


class InningsGradeCalculator:
    """
    Calculates performance grades for cricket match innings.

    Grading takes into account:
    - Run rate vs par/expected score
    - Wicket management
    - Strike rotation (dot ball ratio)
    - Boundary efficiency
    """

    # Par scores for different overs (reference standards)
    PAR_SCORES = {
        6: 45,      # Powerplay: ~7.5 RR
        20: 160,    # T20 full innings
        50: 270,    # ODI full innings
    }

    GRADE_THRESHOLDS = {
        "A+": 1.50,   # >150% of par
        "A": 1.30,    # 130-150% of par
        "B": 1.00,    # 100-130% of par
        "C": 0.70,    # 70-100% of par
        "D": 0.00,    # <70% of par
    }

    @staticmethod
    def calculate_innings_grade(
        *,
        total_runs: int,
        total_wickets: int,
        overs_completed: int,
        balls_this_over: int,
        overs_limit: int | None,
        batting_team_size: int = 11,
        deliveries: list[dict[str, Any]] | None = None,
        is_completed: bool = False,
    ) -> dict[str, Any]:
        """
        Calculate the grade for a cricket innings.

        Args:
            total_runs: Total runs scored in the innings
            total_wickets: Total wickets lost in the innings
            overs_completed: Complete overs bowled
            balls_this_over: Balls bowled in current over (0-5)
            overs_limit: Maximum overs allowed for the innings
            batting_team_size: Size of batting XI (default 11)
            deliveries: List of delivery details for detailed analysis
            is_completed: Whether the innings is complete

        Returns:
            Dictionary containing:
            - grade: Letter grade (A+, A, B, C, D)
            - score_percentage: Percentage of par score achieved
            - par_score: Expected score for reference
            - run_rate: Current/average run rate
            - wicket_efficiency: Wickets preserved ratio (0-1)
            - boundary_count: Number of boundaries hit
            - boundary_percentage: % of runs from boundaries
            - dot_ball_ratio: Ratio of dot balls (0-1)
            - grade_factors: Breakdown of factors affecting grade
        """

        # Determine overs completed more precisely
        total_balls_bowled = overs_completed * 6 + balls_this_over
        total_overs = total_balls_bowled / 6.0

        # Get par score based on overs limit
        par_score = InningsGradeCalculator._get_par_score(
            overs_limit=overs_limit,
            overs_completed=overs_completed,
            is_completed=is_completed,
        )

        # Calculate score percentage
        score_percentage = (total_runs / par_score * 100) if par_score > 0 else 0

        # Analyze deliveries if provided
        boundary_count = 0
        boundary_runs = 0
        dot_balls = 0
        total_legal_balls = 0

        if deliveries:
            for delivery in deliveries:
                # Count boundaries
                if delivery.get("runs_scored", 0) >= 4:
                    boundary_count += 1
                    boundary_runs += delivery.get("runs_scored", 0)

                # Count dot balls (legal deliveries with 0 runs)
                is_extra = delivery.get("is_extra", False)
                extra_type = delivery.get("extra_type")
                if not is_extra or extra_type in ("b", "lb"):
                    total_legal_balls += 1
                    if delivery.get("runs_scored", 0) == 0 and not is_extra:
                        dot_balls += 1

        boundary_percentage = (
            (boundary_runs / total_runs * 100) if total_runs > 0 else 0
        )
        dot_ball_ratio = (
            (dot_balls / total_legal_balls) if total_legal_balls > 0 else 0
        )

        # Calculate wicket efficiency (preserve more = better)
        wickets_preserved = max(0, batting_team_size - total_wickets)
        wicket_efficiency = (wickets_preserved / batting_team_size) if batting_team_size > 0 else 0

        # Calculate grade
        grade = InningsGradeCalculator._calculate_grade(
            score_percentage=score_percentage,
            wicket_efficiency=wicket_efficiency,
            dot_ball_ratio=dot_ball_ratio,
            boundary_percentage=boundary_percentage,
        )

        # Run rate
        run_rate = (total_runs / total_overs) if total_overs > 0 else 0

        return {
            "grade": grade,
            "score_percentage": round(score_percentage, 1),
            "par_score": par_score,
            "total_runs": total_runs,
            "run_rate": round(run_rate, 2),
            "wickets_lost": total_wickets,
            "wicket_efficiency": round(wicket_efficiency, 2),
            "boundary_count": boundary_count,
            "boundary_percentage": round(boundary_percentage, 1),
            "dot_ball_ratio": round(dot_ball_ratio, 2),
            "overs_played": round(total_overs, 1),
            "grade_factors": {
                "score_percentage_contribution": InningsGradeCalculator._score_contribution(
                    score_percentage
                ),
                "wicket_efficiency_contribution": InningsGradeCalculator._wicket_contribution(
                    wicket_efficiency
                ),
                "strike_rotation_contribution": InningsGradeCalculator._strike_contribution(
                    dot_ball_ratio
                ),
                "boundary_efficiency_contribution": InningsGradeCalculator._boundary_contribution(
                    boundary_percentage
                ),
            },
        }

    @staticmethod
    def _get_par_score(
        overs_limit: int | None,
        overs_completed: int,
        is_completed: bool = False,
    ) -> int:
        """
        Get the par/expected score for the innings.

        Par scores are based on:
        - T20 (20 overs): 160 runs
        - ODI (50 overs): 270 runs
        - Default: 7.5 runs per over
        """
        if overs_limit is None:
            # Default to T20 par
            overs_limit = 20

        # Use predefined par if available
        if overs_limit in InningsGradeCalculator.PAR_SCORES:
            return InningsGradeCalculator.PAR_SCORES[overs_limit]

        # Calculate par based on 7.5 runs per over
        par_for_limit = overs_limit * 7.5

        # If not completed, scale down proportionally
        if not is_completed and overs_completed > 0:
            # Par for overs played
            return int((overs_completed * 7.5))

        return int(par_for_limit)

    @staticmethod
    def _calculate_grade(
        score_percentage: float,
        wicket_efficiency: float,
        dot_ball_ratio: float,
        boundary_percentage: float,
    ) -> Literal["A+", "A", "B", "C", "D"]:
        """
        Calculate the final grade based on multiple factors.

        Grade is primarily determined by score percentage, with adjustments for:
        - Wicket management
        - Strike rotation efficiency
        - Boundary hitting ability
        """

        # Base grade from score percentage
        base_score_pct = score_percentage / 100.0

        # Adjustment factors (weight: 0.7 score, 0.15 wickets, 0.1 strike, 0.05 boundaries)
        adjustment = (
            wicket_efficiency * 0.15
            - dot_ball_ratio * 0.05  # More dot balls = lower grade
            + (boundary_percentage / 100) * 0.05
        )

        adjusted_percentage = base_score_pct + adjustment

        # Determine grade based on thresholds
        if adjusted_percentage >= InningsGradeCalculator.GRADE_THRESHOLDS["A+"]:
            return "A+"
        elif adjusted_percentage >= InningsGradeCalculator.GRADE_THRESHOLDS["A"]:
            return "A"
        elif adjusted_percentage >= InningsGradeCalculator.GRADE_THRESHOLDS["B"]:
            return "B"
        elif adjusted_percentage >= InningsGradeCalculator.GRADE_THRESHOLDS["C"]:
            return "C"
        else:
            return "D"

    @staticmethod
    def _score_contribution(score_percentage: float) -> str:
        """Describe score contribution to grade."""
        if score_percentage >= 150:
            return "Exceptional run rate"
        elif score_percentage >= 130:
            return "Very good run rate"
        elif score_percentage >= 100:
            return "Good run rate"
        elif score_percentage >= 70:
            return "Average run rate"
        else:
            return "Below average run rate"

    @staticmethod
    def _wicket_contribution(wicket_efficiency: float) -> str:
        """Describe wicket preservation contribution to grade."""
        if wicket_efficiency >= 0.9:
            return "Excellent wicket preservation"
        elif wicket_efficiency >= 0.7:
            return "Good wicket preservation"
        elif wicket_efficiency >= 0.5:
            return "Average wicket preservation"
        else:
            return "Poor wicket preservation"

    @staticmethod
    def _strike_contribution(dot_ball_ratio: float) -> str:
        """Describe strike rotation contribution to grade."""
        if dot_ball_ratio >= 0.6:
            return "Aggressive strike rotation (low dot balls)"
        elif dot_ball_ratio >= 0.4:
            return "Good strike rotation"
        elif dot_ball_ratio >= 0.2:
            return "Conservative batting"
        else:
            return "Very conservative approach"

    @staticmethod
    def _boundary_contribution(boundary_percentage: float) -> str:
        """Describe boundary efficiency contribution to grade."""
        if boundary_percentage >= 40:
            return "Excellent boundary hitting"
        elif boundary_percentage >= 30:
            return "Good boundary hitting"
        elif boundary_percentage >= 20:
            return "Average boundary hitting"
        else:
            return "Limited boundary hitting"


# Convenience function for API usage
def get_innings_grade(game_state: dict[str, Any]) -> dict[str, Any]:
    """
    Calculate innings grade from game state dictionary.

    Expected keys in game_state:
    - current_inning: Current innings number
    - total_runs: Runs scored
    - total_wickets: Wickets lost
    - overs_completed: Complete overs bowled
    - balls_this_over: Balls in current over
    - overs_limit: Overs limit for match
    - deliveries: (optional) List of delivery details
    """
    return InningsGradeCalculator.calculate_innings_grade(
        total_runs=game_state.get("total_runs", 0),
        total_wickets=game_state.get("total_wickets", 0),
        overs_completed=game_state.get("overs_completed", 0),
        balls_this_over=game_state.get("balls_this_over", 0),
        overs_limit=game_state.get("overs_limit"),
        deliveries=game_state.get("deliveries"),
        is_completed=game_state.get("is_completed", False),
    )
