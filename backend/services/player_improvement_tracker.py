"""
Player Improvement Tracker Service

Tracks and analyzes player skill progression month-over-month:
- Batting average trend
- Strike rate improvement
- Consistency (variance reduction)
- Role adaptation
- Performance growth rate calculation
"""

from datetime import datetime, timedelta
from typing import Any
from dataclasses import dataclass
from collections import defaultdict


@dataclass
class MonthlyStats:
    """Monthly performance statistics for a player"""
    month: str  # "YYYY-MM"
    total_runs: int
    total_deliveries: int
    matches_played: int
    innings_played: int
    dismissals: int
    boundaries_4: int
    boundaries_6: int
    batting_average: float
    strike_rate: float
    consistency_score: float  # Inverse of variance
    role: str  # "opener", "middle_order", "finisher", "bowler"


@dataclass
class ImprovementMetrics:
    """Growth metrics comparing periods"""
    metric_name: str
    previous_value: float
    current_value: float
    absolute_change: float
    percentage_change: float  # -50% to +50% typical
    trend: str  # "improving", "declining", "stable"
    confidence: float  # 0-1 based on sample size


class PlayerImprovementTracker:
    """
    Analyzes player performance trends and calculates improvement metrics.
    
    Tracks:
    - Monthly batting averages
    - Strike rate progression
    - Consistency (variance in runs per innings)
    - Role-specific improvements
    - Growth rate (month-over-month %)
    """

    # Threshold for detecting changes
    IMPROVEMENT_THRESHOLD = 0.05  # 5% improvement
    DECLINE_THRESHOLD = -0.05  # 5% decline
    CONSISTENCY_THRESHOLD = 0.1  # 10% improvement in consistency

    @staticmethod
    def calculate_monthly_stats(
        matches: list[dict[str, Any]],
        month: str = None,
    ) -> MonthlyStats | None:
        """
        Calculate aggregated monthly statistics from matches.
        
        Args:
            matches: List of match dicts with player performance data
            month: Target month ("YYYY-MM"), defaults to current month
        
        Returns:
            MonthlyStats object with aggregated metrics
        """
        if not matches:
            return None

        if month is None:
            now = datetime.now()
            month = now.strftime("%Y-%m")

        # Aggregate stats
        total_runs = 0
        total_deliveries = 0
        total_matches = len(matches)
        total_innings = 0
        total_dismissals = 0
        total_4s = 0
        total_6s = 0
        roles = []

        for match in matches:
            # Extract batting data
            runs = int(match.get("runs_scored", 0))
            deliveries = int(match.get("deliveries_faced", 0))
            is_dismissed = match.get("is_dismissed", False)
            boundaries_4 = int(match.get("boundaries_4", 0))
            boundaries_6 = int(match.get("boundaries_6", 0))
            role = match.get("role", "unknown")

            total_runs += runs
            total_deliveries += deliveries
            if deliveries > 0:
                total_innings += 1
            if is_dismissed:
                total_dismissals += 1
            total_4s += boundaries_4
            total_6s += boundaries_6
            if role:
                roles.append(role)

        # Calculate metrics
        batting_average = total_runs / total_innings if total_innings > 0 else 0
        strike_rate = (total_runs / total_deliveries * 100) if total_deliveries > 0 else 0

        # Consistency score (lower variance = higher consistency)
        runs_per_innings = []
        for match in matches:
            deliveries = int(match.get("deliveries_faced", 0))
            if deliveries > 0:
                runs = int(match.get("runs_scored", 0))
                runs_per_innings.append(runs)

        consistency_score = PlayerImprovementTracker._calculate_consistency(runs_per_innings)

        # Determine primary role
        primary_role = (
            max(set(roles), key=roles.count) if roles else "unknown"
        )

        return MonthlyStats(
            month=month,
            total_runs=total_runs,
            total_deliveries=total_deliveries,
            matches_played=total_matches,
            innings_played=total_innings,
            dismissals=total_dismissals,
            boundaries_4=total_4s,
            boundaries_6=total_6s,
            batting_average=batting_average,
            strike_rate=strike_rate,
            consistency_score=consistency_score,
            role=primary_role,
        )

    @staticmethod
    def calculate_improvement_metrics(
        previous_stats: MonthlyStats,
        current_stats: MonthlyStats,
    ) -> dict[str, ImprovementMetrics]:
        """
        Calculate improvement metrics between two periods.
        
        Args:
            previous_stats: Previous month statistics
            current_stats: Current month statistics
        
        Returns:
            Dict of ImprovementMetrics by metric name
        """
        metrics = {}

        # Batting average improvement
        ba_change = current_stats.batting_average - previous_stats.batting_average
        ba_pct_change = (ba_change / previous_stats.batting_average * 100) if previous_stats.batting_average > 0 else 0
        metrics["batting_average"] = ImprovementMetrics(
            metric_name="Batting Average",
            previous_value=round(previous_stats.batting_average, 2),
            current_value=round(current_stats.batting_average, 2),
            absolute_change=round(ba_change, 2),
            percentage_change=round(ba_pct_change, 1),
            trend=PlayerImprovementTracker._get_trend(ba_pct_change),
            confidence=min(1.0, current_stats.innings_played / 10),  # More matches = more confidence
        )

        # Strike rate improvement
        sr_change = current_stats.strike_rate - previous_stats.strike_rate
        sr_pct_change = (sr_change / previous_stats.strike_rate * 100) if previous_stats.strike_rate > 0 else 0
        metrics["strike_rate"] = ImprovementMetrics(
            metric_name="Strike Rate",
            previous_value=round(previous_stats.strike_rate, 2),
            current_value=round(current_stats.strike_rate, 2),
            absolute_change=round(sr_change, 2),
            percentage_change=round(sr_pct_change, 1),
            trend=PlayerImprovementTracker._get_trend(sr_pct_change),
            confidence=min(1.0, current_stats.total_deliveries / 100),
        )

        # Consistency improvement (higher score = more consistent)
        consistency_change = current_stats.consistency_score - previous_stats.consistency_score
        consistency_pct_change = (
            (consistency_change / previous_stats.consistency_score * 100)
            if previous_stats.consistency_score > 0
            else 0
        )
        metrics["consistency"] = ImprovementMetrics(
            metric_name="Consistency",
            previous_value=round(previous_stats.consistency_score, 2),
            current_value=round(current_stats.consistency_score, 2),
            absolute_change=round(consistency_change, 2),
            percentage_change=round(consistency_pct_change, 1),
            trend=PlayerImprovementTracker._get_trend(consistency_pct_change),
            confidence=min(1.0, current_stats.innings_played / 10),
        )

        # Dismissal rate improvement (lower = better)
        prev_dismissal_rate = previous_stats.dismissals / previous_stats.innings_played if previous_stats.innings_played > 0 else 0
        curr_dismissal_rate = current_stats.dismissals / current_stats.innings_played if current_stats.innings_played > 0 else 0
        dismissal_change = prev_dismissal_rate - curr_dismissal_rate  # Inverted (lower is better)
        dismissal_pct_change = (
            (dismissal_change / prev_dismissal_rate * 100)
            if prev_dismissal_rate > 0
            else 0
        )
        metrics["dismissal_rate"] = ImprovementMetrics(
            metric_name="Dismissal Rate",
            previous_value=round(prev_dismissal_rate, 2),
            current_value=round(curr_dismissal_rate, 2),
            absolute_change=round(dismissal_change, 2),
            percentage_change=round(dismissal_pct_change, 1),
            trend=PlayerImprovementTracker._get_trend(dismissal_pct_change),
            confidence=min(1.0, current_stats.innings_played / 10),
        )

        # Boundary percentage improvement
        prev_boundary_pct = (previous_stats.boundaries_4 + previous_stats.boundaries_6) / max(1, previous_stats.total_deliveries)
        curr_boundary_pct = (current_stats.boundaries_4 + current_stats.boundaries_6) / max(1, current_stats.total_deliveries)
        boundary_change = curr_boundary_pct - prev_boundary_pct
        boundary_pct_change = (boundary_change / prev_boundary_pct * 100) if prev_boundary_pct > 0 else 0
        metrics["boundary_rate"] = ImprovementMetrics(
            metric_name="Boundary Rate",
            previous_value=round(prev_boundary_pct * 100, 2),
            current_value=round(curr_boundary_pct * 100, 2),
            absolute_change=round(boundary_change * 100, 2),
            percentage_change=round(boundary_pct_change, 1),
            trend=PlayerImprovementTracker._get_trend(boundary_pct_change),
            confidence=min(1.0, current_stats.total_deliveries / 100),
        )

        return metrics

    @staticmethod
    def _calculate_consistency(runs_per_innings: list[int]) -> float:
        """
        Calculate consistency score (0-100, higher is better).
        Uses inverse of variance normalized to 0-100 scale.
        """
        if not runs_per_innings or len(runs_per_innings) < 2:
            return 50.0

        # Calculate mean and variance
        mean = sum(runs_per_innings) / len(runs_per_innings)
        variance = sum((x - mean) ** 2 for x in runs_per_innings) / len(runs_per_innings)

        # Normalize variance to consistency score (0-100)
        # Higher variance = lower score
        # Assuming max reasonable variance is around 100
        max_variance = 100
        consistency = max(0, 100 - (variance / max_variance * 100))

        return round(consistency, 1)

    @staticmethod
    def _get_trend(percentage_change: float) -> str:
        """Determine trend based on percentage change."""
        if percentage_change >= PlayerImprovementTracker.IMPROVEMENT_THRESHOLD * 100:
            return "improving"
        elif percentage_change <= PlayerImprovementTracker.DECLINE_THRESHOLD * 100:
            return "declining"
        else:
            return "stable"

    @staticmethod
    def get_improvement_summary(
        monthly_stats_list: list[MonthlyStats],
    ) -> dict[str, Any]:
        """
        Generate comprehensive improvement summary across multiple months.
        
        Args:
            monthly_stats_list: List of MonthlyStats objects, sorted by month
        
        Returns:
            Summary dict with trends, highlights, and recommendations
        """
        if not monthly_stats_list or len(monthly_stats_list) < 2:
            return {
                "status": "insufficient_data",
                "message": "Need at least 2 months of data for trend analysis",
                "months_available": len(monthly_stats_list),
            }

        # Sort by month
        sorted_stats = sorted(monthly_stats_list, key=lambda x: x.month)

        # Calculate all improvements
        improvement_metrics = []
        for i in range(1, len(sorted_stats)):
            metrics = PlayerImprovementTracker.calculate_improvement_metrics(
                sorted_stats[i - 1],
                sorted_stats[i],
            )
            improvement_metrics.append({
                "from_month": sorted_stats[i - 1].month,
                "to_month": sorted_stats[i].month,
                "metrics": metrics,
            })

        # Get latest metrics
        latest = sorted_stats[-1]
        previous = sorted_stats[-2] if len(sorted_stats) >= 2 else None

        # Calculate overall trend
        latest_metrics = (
            PlayerImprovementTracker.calculate_improvement_metrics(previous, latest)
            if previous
            else {}
        )

        improving_count = sum(
            1 for m in latest_metrics.values() if m.trend == "improving"
        )
        total_metrics = len(latest_metrics)

        overall_trend = (
            "accelerating"
            if improving_count == total_metrics
            else "stable" if improving_count >= total_metrics / 2 else "declining"
        )

        return {
            "status": "success",
            "overall_trend": overall_trend,
            "improvement_score": round((improving_count / total_metrics) * 100) if total_metrics > 0 else 0,
            "latest_month": latest.month,
            "months_analyzed": len(sorted_stats),
            "latest_stats": {
                "batting_average": round(latest.batting_average, 2),
                "strike_rate": round(latest.strike_rate, 2),
                "consistency_score": round(latest.consistency_score, 1),
                "matches_played": latest.matches_played,
                "innings_played": latest.innings_played,
                "role": latest.role,
            },
            "latest_improvements": latest_metrics,
            "historical_improvements": improvement_metrics,
            "highlights": PlayerImprovementTracker._generate_highlights(sorted_stats, latest_metrics),
        }

    @staticmethod
    def _generate_highlights(
        monthly_stats_list: list[MonthlyStats],
        latest_metrics: dict[str, ImprovementMetrics],
    ) -> list[str]:
        """Generate human-readable highlights from data."""
        highlights = []

        if not monthly_stats_list:
            return highlights

        latest = monthly_stats_list[-1]

        # Batting average highlight
        ba_metric = latest_metrics.get("batting_average")
        if ba_metric and ba_metric.trend == "improving":
            highlights.append(
                f"📈 Batting average improved {ba_metric.percentage_change:.1f}% to {ba_metric.current_value}"
            )
        elif ba_metric and ba_metric.trend == "declining":
            highlights.append(
                f"📉 Batting average declined {abs(ba_metric.percentage_change):.1f}% to {ba_metric.current_value}"
            )

        # Strike rate highlight
        sr_metric = latest_metrics.get("strike_rate")
        if sr_metric and sr_metric.trend == "improving":
            highlights.append(
                f"⚡ Strike rate improved to {sr_metric.current_value} ({sr_metric.percentage_change:+.1f}%)"
            )

        # Consistency highlight
        consistency_metric = latest_metrics.get("consistency")
        if consistency_metric and consistency_metric.trend == "improving":
            highlights.append(
                f"🎯 Consistency improved {consistency_metric.percentage_change:.1f}% - More stable performances"
            )

        # Role-based highlight
        if latest.role != "unknown":
            highlights.append(f"🏏 Specialist role: {latest.role} with {latest.matches_played} matches")

        # Boundary highlight
        boundary_metric = latest_metrics.get("boundary_rate")
        if boundary_metric and boundary_metric.trend == "improving":
            highlights.append(
                f"💥 Aggressive batting: {boundary_metric.percentage_change:+.1f}% more boundaries"
            )

        return highlights


def get_player_improvement_data(
    monthly_stats_list: list[dict[str, Any]],
) -> dict[str, Any]:
    """Convenience function to analyze player improvement from monthly stats."""
    # Convert dicts to MonthlyStats objects
    stats_objects = [
        MonthlyStats(
            month=s.get("month", ""),
            total_runs=s.get("total_runs", 0),
            total_deliveries=s.get("total_deliveries", 0),
            matches_played=s.get("matches_played", 0),
            innings_played=s.get("innings_played", 0),
            dismissals=s.get("dismissals", 0),
            boundaries_4=s.get("boundaries_4", 0),
            boundaries_6=s.get("boundaries_6", 0),
            batting_average=s.get("batting_average", 0),
            strike_rate=s.get("strike_rate", 0),
            consistency_score=s.get("consistency_score", 50),
            role=s.get("role", "unknown"),
        )
        for s in monthly_stats_list
    ]

    return PlayerImprovementTracker.get_improvement_summary(stats_objects)
