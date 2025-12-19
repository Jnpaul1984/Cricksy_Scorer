"""
Match Phase Analyzer Service

Segments a cricket match into logical phases (powerplay, middle, death, mini-death)
and provides phase-specific analysis and predictions:

- Powerplay (0-6 overs): Expected runs, wicket burnout rate, aggressive index
- Middle (7-15 overs): Acceleration rate, rotation quality, 3rd man patterns
- Death (16-20 overs): Boundary-dot ratio, finish rate needed, yorker effectiveness
- Mini-death (2nd innings, last 3 overs): Runs needed per ball, win probability
"""

from typing import Any
from dataclasses import dataclass


@dataclass
class PhaseStats:
    """Statistics for a single phase"""
    phase_name: str
    phase_number: int
    start_over: int
    end_over: int
    deliveries: list[dict[str, Any]]
    total_runs: int
    total_wickets: int
    total_deliveries: int
    run_rate: float
    expected_runs_in_phase: float
    actual_vs_expected_pct: float
    wicket_rate: float  # wickets per over
    boundary_count: int
    dot_ball_count: int
    aggressive_index: float  # (boundaries + sixes) / (total runs)
    acceleration_rate: float  # runs per over vs powerplay baseline


class MatchPhaseAnalyzer:
    """
    Analyzes cricket matches by dividing them into phases.
    
    Each phase has different scoring patterns and strategies:
    - Powerplay: Attacking batting, high-risk shots
    - Middle: Consolidation and rotation
    - Death: Aggressive finish, boundary-heavy
    - Mini-death (2nd innings): Run-chasing pressure
    """

    # Phase definitions (overs are 1-indexed for user display)
    POWERPLAY_START = 0
    POWERPLAY_END = 6
    MIDDLE_START = 6
    MIDDLE_END = 15
    DEATH_START = 15
    DEATH_END = 20
    MINI_DEATH_OVERS = 3  # Last 3 overs of 2nd innings

    # Expected run rates by phase (per over)
    EXPECTED_RR_POWERPLAY = 8.5  # T20 typical
    EXPECTED_RR_MIDDLE = 7.0
    EXPECTED_RR_DEATH = 12.0

    @staticmethod
    def analyze_phases(
        deliveries: list[dict[str, Any]],
        target: int,
        overs_limit: int,
        is_second_innings: bool = False,
    ) -> dict[str, Any]:
        """
        Analyze match phases and generate predictions.
        
        Args:
            deliveries: List of delivery dictionaries
            target: Target runs (if chasing)
            overs_limit: Total overs in innings (20 for T20, 50 for ODI)
            is_second_innings: Whether analyzing the chasing innings
        
        Returns:
            {
                "phases": [PhaseStats, ...],
                "current_phase": "powerplay" | "middle" | "death" | "mini_death",
                "phase_index": int,
                "summary": {
                    "total_runs": int,
                    "total_wickets": int,
                    "overall_run_rate": float,
                    "overall_expected_runs": float,
                    "acceleration_trend": "increasing" | "decreasing" | "stable",
                },
                "predictions": {
                    "powerplay_expected": float,
                    "total_expected": float,
                    "finish_probability": float (if chasing),
                },
                "phase_performance": {
                    "powerplay": {...},
                    "middle": {...},
                    "death": {...},
                }
            }
        """
        if not deliveries:
            return {
                "phases": [],
                "current_phase": "powerplay",
                "phase_index": 0,
                "summary": {
                    "total_runs": 0,
                    "total_wickets": 0,
                    "overall_run_rate": 0,
                    "overall_expected_runs": 0,
                    "acceleration_trend": "stable",
                },
                "predictions": {},
                "phase_performance": {},
            }

        # Parse deliveries into phases
        phases_dict: dict[str, list[dict[str, Any]]] = {}
        
        for delivery in deliveries:
            over_num = int(delivery.get("over_number", 0))
            phase = MatchPhaseAnalyzer._get_phase(over_num, overs_limit, is_second_innings)
            
            if phase:
                if phase not in phases_dict:
                    phases_dict[phase] = []
                phases_dict[phase].append(delivery)
        
        # Convert to ordered list
        phase_order = ["powerplay", "middle", "death", "mini_death"]
        phases = []
        for idx, phase_name in enumerate(phase_order):
            if phase_name in phases_dict:
                phase_obj = MatchPhaseAnalyzer._calculate_phase_stats(
                    phases_dict[phase_name],
                    idx,
                    target,
                    overs_limit,
                )
                if phase_obj:
                    phases.append(phase_obj)

        # Calculate summary statistics
        if phases:
            total_runs = sum(p.total_runs for p in phases)
            total_wickets = sum(p.total_wickets for p in phases)
            total_deliveries = sum(p.total_deliveries for p in phases)
            overall_rr = (total_runs / (total_deliveries / 6)) if total_deliveries else 0

            # Calculate expected runs
            expected_pp = MatchPhaseAnalyzer.EXPECTED_RR_POWERPLAY * 6  # 6 overs
            expected_mid = MatchPhaseAnalyzer.EXPECTED_RR_MIDDLE * 9  # 9 overs
            expected_death = MatchPhaseAnalyzer.EXPECTED_RR_DEATH * 5  # 5 overs
            overall_expected = expected_pp + expected_mid + expected_death

            # Detect acceleration trend
            acceleration_trend = MatchPhaseAnalyzer._detect_acceleration_trend(phases)

            # Predictions
            predictions = MatchPhaseAnalyzer._generate_predictions(
                phases, target, overs_limit, is_second_innings
            )

            # Current phase
            current_phase = phases[-1].phase_name if phases else "powerplay"
            phase_index = len(phases) - 1

            return {
                "phases": [
                    {
                        "phase_name": p.phase_name,
                        "phase_number": p.phase_number,
                        "start_over": p.start_over,
                        "end_over": p.end_over,
                        "total_runs": p.total_runs,
                        "total_wickets": p.total_wickets,
                        "total_deliveries": p.total_deliveries,
                        "run_rate": round(p.run_rate, 2),
                        "expected_runs_in_phase": round(p.expected_runs_in_phase, 1),
                        "actual_vs_expected_pct": round(p.actual_vs_expected_pct, 1),
                        "wicket_rate": round(p.wicket_rate, 2),
                        "boundary_count": p.boundary_count,
                        "dot_ball_count": p.dot_ball_count,
                        "aggressive_index": round(p.aggressive_index, 2),
                        "acceleration_rate": round(p.acceleration_rate, 2),
                    }
                    for p in phases
                ],
                "current_phase": current_phase,
                "phase_index": phase_index,
                "summary": {
                    "total_runs": total_runs,
                    "total_wickets": total_wickets,
                    "overall_run_rate": round(overall_rr, 2),
                    "overall_expected_runs": round(overall_expected, 1),
                    "acceleration_trend": acceleration_trend,
                },
                "predictions": predictions,
                "phase_performance": {
                    p.phase_name: {
                        "actual_runs": p.total_runs,
                        "expected_runs": round(p.expected_runs_in_phase, 1),
                        "performance_pct": round(p.actual_vs_expected_pct, 1),
                    }
                    for p in phases
                },
            }
        else:
            return {
                "phases": [],
                "current_phase": "powerplay",
                "phase_index": 0,
                "summary": {
                    "total_runs": 0,
                    "total_wickets": 0,
                    "overall_run_rate": 0,
                    "overall_expected_runs": 0,
                    "acceleration_trend": "stable",
                },
                "predictions": {},
                "phase_performance": {},
            }

    @staticmethod
    def _get_phase(
        over_num: int, overs_limit: int, is_second_innings: bool
    ) -> str | None:
        """Determine which phase an over belongs to."""
        if over_num < MatchPhaseAnalyzer.POWERPLAY_END:
            return "powerplay"
        elif over_num < MatchPhaseAnalyzer.MIDDLE_END:
            return "middle"
        elif is_second_innings and over_num >= (overs_limit - MatchPhaseAnalyzer.MINI_DEATH_OVERS):
            return "mini_death"
        elif over_num < MatchPhaseAnalyzer.DEATH_END:
            return "death"
        return None

    @staticmethod
    def _calculate_phase_stats(
        deliveries: list[dict[str, Any]],
        phase_index: int,
        target: int,
        overs_limit: int,
    ) -> PhaseStats | None:
        """Calculate statistics for a phase."""
        if not deliveries:
            return None

        phase_names = ["powerplay", "middle", "death", "mini_death"]
        phase_name = phase_names[min(phase_index, len(phase_names) - 1)]

        # Calculate cumulative stats
        total_runs = 0
        total_wickets = 0
        boundary_count = 0
        dot_ball_count = 0

        for delivery in deliveries:
            runs = int(delivery.get("runs_scored", 0))
            total_runs += runs
            total_wickets += 1 if delivery.get("is_wicket") else 0
            dot_ball_count += 1 if runs == 0 else 0

            # Count boundaries
            if runs in [4, 6]:
                boundary_count += 1

        total_deliveries = len(deliveries)
        overs_bowled = total_deliveries / 6 if total_deliveries else 0
        run_rate = (total_runs / overs_bowled) if overs_bowled > 0 else 0
        wicket_rate = total_wickets / overs_bowled if overs_bowled > 0 else 0

        # Expected runs for phase
        if phase_name == "powerplay":
            expected_runs = MatchPhaseAnalyzer.EXPECTED_RR_POWERPLAY * 6
        elif phase_name == "middle":
            expected_runs = MatchPhaseAnalyzer.EXPECTED_RR_MIDDLE * 9
        elif phase_name == "death":
            expected_runs = MatchPhaseAnalyzer.EXPECTED_RR_DEATH * 5
        else:  # mini_death
            expected_runs = MatchPhaseAnalyzer.EXPECTED_RR_DEATH * 3

        actual_vs_expected_pct = (total_runs / expected_runs * 100) if expected_runs else 0

        # Aggressive index
        aggressive_index = (boundary_count / total_runs) if total_runs else 0

        # Acceleration rate (relative to powerplay)
        acceleration_rate = run_rate / MatchPhaseAnalyzer.EXPECTED_RR_POWERPLAY if phase_name != "powerplay" else 1.0

        # Determine phase boundaries
        if phase_name == "powerplay":
            start_over = 0
            end_over = 6
        elif phase_name == "middle":
            start_over = 6
            end_over = 15
        elif phase_name == "death":
            start_over = 15
            end_over = 20
        else:  # mini_death
            start_over = max(0, overs_limit - MatchPhaseAnalyzer.MINI_DEATH_OVERS)
            end_over = overs_limit

        return PhaseStats(
            phase_name=phase_name,
            phase_number=phase_index,
            start_over=start_over,
            end_over=end_over,
            deliveries=deliveries,
            total_runs=total_runs,
            total_wickets=total_wickets,
            total_deliveries=total_deliveries,
            run_rate=run_rate,
            expected_runs_in_phase=expected_runs,
            actual_vs_expected_pct=actual_vs_expected_pct,
            wicket_rate=wicket_rate,
            boundary_count=boundary_count,
            dot_ball_count=dot_ball_count,
            aggressive_index=aggressive_index,
            acceleration_rate=acceleration_rate,
        )

    @staticmethod
    def _detect_acceleration_trend(phases: list[PhaseStats]) -> str:
        """Detect acceleration trend across phases."""
        if len(phases) < 2:
            return "stable"

        run_rates = [p.run_rate for p in phases]
        if len(run_rates) >= 2:
            if run_rates[-1] > run_rates[-2] * 1.1:  # >10% increase
                return "increasing"
            elif run_rates[-1] < run_rates[-2] * 0.9:  # >10% decrease
                return "decreasing"
        return "stable"

    @staticmethod
    def _generate_predictions(
        phases: list[PhaseStats],
        target: int,
        overs_limit: int,
        is_second_innings: bool,
    ) -> dict[str, Any]:
        """Generate phase-based predictions."""
        predictions = {}

        # Expected powerplay runs
        pp_phase = next((p for p in phases if p.phase_name == "powerplay"), None)
        if pp_phase:
            predictions["powerplay_actual"] = pp_phase.total_runs
            predictions["powerplay_efficiency"] = round(pp_phase.actual_vs_expected_pct, 1)

        # Total expected runs projection
        current_runs = sum(p.total_runs for p in phases)
        current_overs = sum(p.total_deliveries for p in phases) / 6

        if current_overs > 0 and overs_limit > current_overs:
            avg_rr = current_runs / current_overs
            remaining_overs = overs_limit - current_overs
            projected_runs = current_runs + (avg_rr * remaining_overs)
            predictions["total_expected_runs"] = round(projected_runs, 0)
        else:
            predictions["total_expected_runs"] = current_runs

        # Win probability (if chasing)
        if is_second_innings and target:
            runs_needed = max(0, target - current_runs)
            overs_remaining = overs_limit - current_overs
            if overs_remaining > 0:
                rr_needed = runs_needed / overs_remaining
                current_rr = current_runs / current_overs if current_overs > 0 else 0
                # Simple heuristic: if RRR <= actual RR so far, likely to win
                if rr_needed <= current_rr * 0.9:
                    win_prob = 0.85
                elif rr_needed <= current_rr:
                    win_prob = 0.65
                elif rr_needed <= current_rr * 1.2:
                    win_prob = 0.45
                else:
                    win_prob = 0.20
                predictions["win_probability"] = round(win_prob, 2)

        return predictions


def get_phase_analysis(
    deliveries: list[dict[str, Any]],
    target: int,
    overs_limit: int,
    is_second_innings: bool = False,
) -> dict[str, Any]:
    """Convenience function for phase analysis."""
    return MatchPhaseAnalyzer.analyze_phases(
        deliveries=deliveries,
        target=target,
        overs_limit=overs_limit,
        is_second_innings=is_second_innings,
    )
