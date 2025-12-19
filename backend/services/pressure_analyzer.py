"""
Pressure Analyzer Service

Identifies and maps high-pressure moments during cricket matches by analyzing:
- Dot ball streaks (consecutive dot balls)
- Wicket timings (sudden momentum shifts)
- Required run rate changes (target gap widening)
- Scoring droughts (runs not coming)
- Comeback situations (pressure relief moments)

Pressure is scored 0-100 where:
- 0-20: Low pressure (runs flowing, wickets preserved)
- 20-40: Moderate pressure (some dots, manageable situation)
- 40-60: Building pressure (dot streaks, gap widening)
- 60-80: High pressure (multiple factors, critical moment)
- 80-100: Extreme pressure (critical situation, match-deciding moment)
"""

from typing import Any
from dataclasses import dataclass


@dataclass
class DeliveryContext:
    """Context for a single delivery"""
    delivery_num: int
    over_num: int
    ball_in_over: int
    runs_scored: int
    is_wicket: bool
    wicket_type: str | None
    is_dot: bool
    cumulative_runs: int
    cumulative_wickets: int
    overs_remaining: float
    target: int
    required_run_rate: float


class PressureAnalyzer:
    """
    Analyzes match pressure at delivery level.
    
    Calculates pressure score for each delivery based on:
    1. Dot ball streaks (multiple dots = higher pressure)
    2. Required run rate vs actual rate (gap = pressure)
    3. Wicket proximity to scoring droughts (loss of confidence)
    4. Overs remaining (reduced overs = higher pressure)
    5. Match situation (winning vs losing)
    """

    # Pressure thresholds
    DOT_STREAK_THRESHOLD = 3  # 3+ consecutive dots triggers pressure
    RRR_MULTIPLIER = 2.0  # For every run/over gap in RRR
    WICKET_PRESSURE_BOOST = 15  # Pressure increase on wicket

    @staticmethod
    def analyze_pressure_map(
        deliveries: list[dict[str, Any]],
        target: int,
        overs_limit: int,
    ) -> list[dict[str, Any]]:
        """
        Analyze pressure for each delivery in an innings.
        
        Args:
            deliveries: List of delivery dictionaries with keys:
                - runs_scored: int (0-6)
                - extra: str | None ('wd', 'nb', 'b', 'lb')
                - is_wicket: bool
                - how_out: str | None
                - ball_in_over: int (0-5)
                - over_num: int (0-based)
            target: Target runs to chase/defend
            overs_limit: Total overs in innings (20 for T20, 50 for ODI)
        
        Returns:
            List of pressure points:
            [
                {
                    "delivery_num": int,
                    "over_num": float,  # e.g., 5.3 = 5 overs 3 balls
                    "pressure_score": float,  # 0-100
                    "pressure_level": str,  # "low", "moderate", "building", "high", "extreme"
                    "factors": {
                        "dot_streak": int,  # consecutive dots
                        "rrr_gap": float,  # required RR - actual RR
                        "wicket_factor": float,  # 0 if no wicket, >0 if wicket
                        "overs_factor": float,  # pressure from overs remaining
                        "situation_factor": float,  # winning/losing pressure
                    },
                    "cumulative_stats": {
                        "runs": int,
                        "wickets": int,
                        "dot_count": int,
                        "strike_rate": float,
                    }
                },
                ...
            ]
        """
        if not deliveries:
            return []
        
        pressure_points = []
        cumulative_runs = 0
        cumulative_wickets = 0
        consecutive_dots = 0
        dot_count = 0
        
        for delivery_idx, delivery in enumerate(deliveries):
            delivery_num = delivery_idx + 1
            
            # Calculate overs position
            over_num = delivery_idx // 6
            ball_in_over = delivery_idx % 6
            over_position = over_num + (ball_in_over / 6.0)
            
            # Extract delivery details
            runs_scored = int(delivery.get("runs_scored", 0))
            extra = delivery.get("extra")
            is_wicket = bool(delivery.get("is_wicket", False))
            is_dot = (runs_scored == 0 and extra is None and not is_wicket)
            
            # Update cumulative stats
            cumulative_runs += runs_scored
            if extra and extra not in ['b', 'lb']:  # extras that don't count as legal
                cumulative_runs += int(delivery.get("extra_runs", 0)) if extra in ['wd', 'nb'] else 0
            
            if is_wicket:
                cumulative_wickets += 1
            
            # Track dot balls
            if is_dot:
                consecutive_dots += 1
                dot_count += 1
            else:
                consecutive_dots = 0
            
            # Calculate overs remaining and required rate
            balls_remaining = (overs_limit * 6) - delivery_idx
            overs_remaining = balls_remaining / 6.0
            
            # Calculate required run rate
            runs_remaining = target - cumulative_runs
            if overs_remaining > 0:
                required_run_rate = runs_remaining / overs_remaining
            else:
                required_run_rate = 0
            
            # Calculate actual run rate
            if over_position > 0:
                actual_run_rate = cumulative_runs / over_position
            else:
                actual_run_rate = 0
            
            # Calculate pressure score
            pressure_score = PressureAnalyzer._calculate_pressure_score(
                delivery_num=delivery_num,
                over_num=over_num,
                consecutive_dots=consecutive_dots,
                is_wicket=is_wicket,
                required_run_rate=required_run_rate,
                actual_run_rate=actual_run_rate,
                cumulative_wickets=cumulative_wickets,
                overs_remaining=overs_remaining,
                overs_limit=overs_limit,
                runs_remaining=runs_remaining,
                target=target,
                cumulative_runs=cumulative_runs,
            )
            
            # Get pressure level
            pressure_level = PressureAnalyzer._get_pressure_level(pressure_score)
            
            # Calculate individual factors
            dot_streak_factor = min(consecutive_dots * 5, 30)  # Max 30 from dots
            rrr_gap = max(0, required_run_rate - actual_run_rate)
            rrr_factor = min(rrr_gap * PressureAnalyzer.RRR_MULTIPLIER, 40)  # Max 40
            wicket_factor = PressureAnalyzer.WICKET_PRESSURE_BOOST if is_wicket else 0
            overs_factor = (1 - (overs_remaining / overs_limit)) * 20  # Up to 20 from overs
            
            # Situation factor (winning vs losing)
            if runs_remaining <= 0:
                situation_factor = 0  # Already won
            elif runs_remaining > (overs_remaining * required_run_rate * 1.2):
                situation_factor = 20  # Getting away from target
            else:
                situation_factor = 10  # On target
            
            point = {
                "delivery_num": delivery_num,
                "over_num": round(over_position, 1),
                "pressure_score": round(pressure_score, 1),
                "pressure_level": pressure_level,
                "factors": {
                    "dot_streak": consecutive_dots,
                    "dot_streak_factor": round(dot_streak_factor, 1),
                    "rrr_gap": round(rrr_gap, 2),
                    "rrr_factor": round(rrr_factor, 1),
                    "wicket_factor": wicket_factor,
                    "overs_factor": round(overs_factor, 1),
                    "situation_factor": round(situation_factor, 1),
                },
                "rates": {
                    "required_run_rate": round(required_run_rate, 2),
                    "actual_run_rate": round(actual_run_rate, 2),
                },
                "cumulative_stats": {
                    "runs": cumulative_runs,
                    "wickets": cumulative_wickets,
                    "dot_count": dot_count,
                    "strike_rate": round((cumulative_runs / delivery_idx * 100), 1) if delivery_idx > 0 else 0,
                    "balls_remaining": balls_remaining,
                    "overs_remaining": round(overs_remaining, 1),
                },
            }
            
            pressure_points.append(point)
        
        return pressure_points

    @staticmethod
    def _calculate_pressure_score(
        delivery_num: int,
        over_num: int,
        consecutive_dots: int,
        is_wicket: bool,
        required_run_rate: float,
        actual_run_rate: float,
        cumulative_wickets: int,
        overs_remaining: float,
        overs_limit: int,
        runs_remaining: int,
        target: int,
        cumulative_runs: int,
    ) -> float:
        """
        Calculate pressure score (0-100) based on multiple factors.
        
        Formula combines:
        1. Dot ball factor (0-30)
        2. RRR gap factor (0-40)
        3. Wicket pressure (0-15)
        4. Overs remaining factor (0-20)
        5. Match situation (0-10)
        """
        
        # 1. Dot ball factor
        dot_factor = min(consecutive_dots * 8, 30)
        
        # 2. RRR gap factor
        rrr_gap = max(0, required_run_rate - actual_run_rate)
        rrr_factor = min(rrr_gap * PressureAnalyzer.RRR_MULTIPLIER, 40)
        
        # 3. Wicket pressure
        wicket_factor = PressureAnalyzer.WICKET_PRESSURE_BOOST if is_wicket else 0
        
        # 4. Overs remaining (less overs = more pressure)
        overs_pressure = (1 - (overs_remaining / overs_limit)) * 20
        
        # 5. Match situation
        if runs_remaining <= 0:
            situation_factor = 0  # Already won
        elif runs_remaining > (overs_remaining * max(required_run_rate, 8) * 1.5):
            situation_factor = 25  # Far from target - low pressure
        elif runs_remaining > (overs_remaining * max(required_run_rate, 8) * 0.8):
            situation_factor = 10  # On target
        else:
            situation_factor = -15  # Ahead of target - relief
        
        # Combine with weights
        total_pressure = (
            dot_factor * 0.25 +       # Dots: 25%
            rrr_factor * 0.35 +       # RRR: 35%
            wicket_factor * 0.15 +    # Wickets: 15%
            overs_pressure * 0.15 +   # Overs: 15%
            situation_factor * 0.10   # Situation: 10%
        )
        
        # Clamp to 0-100
        return max(0, min(100, total_pressure))

    @staticmethod
    def _get_pressure_level(score: float) -> str:
        """Map pressure score to descriptive level."""
        if score < 20:
            return "low"
        elif score < 40:
            return "moderate"
        elif score < 60:
            return "building"
        elif score < 80:
            return "high"
        else:
            return "extreme"

    @staticmethod
    def get_peak_pressure_moments(
        pressure_points: list[dict[str, Any]],
        threshold: float = 70,
    ) -> list[dict[str, Any]]:
        """
        Extract peak pressure moments (above threshold).
        
        Useful for highlighting critical moments in a match.
        """
        return [p for p in pressure_points if p["pressure_score"] >= threshold]

    @staticmethod
    def get_pressure_phases(
        pressure_points: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Identify match phases based on pressure patterns.
        
        Returns:
        {
            "powerplay": {...},      # Overs 0-6
            "middle": {...},         # Overs 7-15 (T20) or 7-40 (ODI)
            "death": {...},          # Final overs
            "critical_moments": [...]
        }
        """
        if not pressure_points:
            return {}
        
        phases = {
            "powerplay": [],
            "middle": [],
            "death": [],
        }
        
        for point in pressure_points:
            over_num = int(point["over_num"])
            
            if over_num < 6:
                phases["powerplay"].append(point)
            elif over_num < 16:  # Assuming T20, adjust for ODI
                phases["middle"].append(point)
            else:
                phases["death"].append(point)
        
        # Calculate phase statistics
        phase_names = list(phases.keys())
        for phase_name in phase_names:
            if phases[phase_name]:
                scores = [p["pressure_score"] for p in phases[phase_name]]
                phases[phase_name + "_stats"] = {
                    "avg_pressure": round(sum(scores) / len(scores), 1),
                    "peak_pressure": round(max(scores), 1),
                    "deliveries": len(scores),
                }
        
        return phases


def get_pressure_map(
    deliveries: list[dict[str, Any]],
    target: int,
    overs_limit: int,
) -> dict[str, Any]:
    """
    Convenience function to generate pressure map for an innings.
    
    This is the main entry point for API usage.
    """
    pressure_points = PressureAnalyzer.analyze_pressure_map(
        deliveries=deliveries,
        target=target,
        overs_limit=overs_limit,
    )
    
    # Calculate summary statistics
    if pressure_points:
        scores = [p["pressure_score"] for p in pressure_points]
        peak_moments = PressureAnalyzer.get_peak_pressure_moments(pressure_points)
        phases = PressureAnalyzer.get_pressure_phases(pressure_points)
        
        return {
            "pressure_points": pressure_points,
            "summary": {
                "total_deliveries": len(pressure_points),
                "average_pressure": round(sum(scores) / len(scores), 1),
                "peak_pressure": round(max(scores), 1),
                "peak_pressure_at_delivery": pressure_points[scores.index(max(scores))]["delivery_num"],
                "critical_moments": len(peak_moments),
                "high_pressure_count": sum(1 for s in scores if s >= 60),
            },
            "peak_moments": peak_moments[:5] if peak_moments else [],  # Top 5
            "phases": phases,
        }
    else:
        return {
            "pressure_points": [],
            "summary": {
                "total_deliveries": 0,
                "average_pressure": 0,
                "peak_pressure": 0,
                "critical_moments": 0,
            },
            "peak_moments": [],
            "phases": {},
        }
