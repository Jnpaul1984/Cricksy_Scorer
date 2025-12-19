"""
Player Career Analyzer Service

Generates comprehensive AI-powered career summaries for cricket players including:
- Best innings and performances
- Consistency metrics
- Specialization analysis (opener, finisher, bowler, all-rounder)
- Recent form trends
- Career highlights and key achievements
"""

from typing import Any
from datetime import datetime, timedelta
from collections import defaultdict
import statistics


class PlayerCareerAnalyzer:
    """
    Analyzes player career statistics and generates AI-powered summaries.
    
    Provides insights into:
    - Career batting/bowling performance
    - Consistency and variance
    - Specialization patterns
    - Recent form
    - Best performances
    """

    # Specialization thresholds
    OPENER_POSITION_THRESHOLD = 0.5  # 50% of innings in top 3
    FINISHER_POSITION_THRESHOLD = 0.4  # 40% of innings in bottom 3
    BOWLER_MIN_OVERS = 10  # Minimum overs to be considered a bowler
    ALLROUNDER_BATTING_THRESHOLD = 400  # Min runs
    ALLROUNDER_BOWLING_THRESHOLD = 5  # Min wickets

    @staticmethod
    def analyze_player_career(
        player_id: str,
        player_name: str,
        batting_records: list[dict[str, Any]],
        bowling_records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Comprehensive career analysis for a player.
        
        Args:
            player_id: Unique player identifier
            player_name: Player's full name
            batting_records: List of batting dictionaries with keys:
                - runs: int
                - balls_faced: int
                - fours: int
                - sixes: int
                - is_out: bool
                - how_out: str | None
                - match_date: str (ISO format)
            bowling_records: List of bowling dictionaries with keys:
                - overs_bowled: float
                - maidens: int
                - runs_conceded: int
                - wickets_taken: int
                - match_date: str (ISO format)
        
        Returns:
            Dictionary containing:
            {
                "player_id": str,
                "player_name": str,
                "career_summary": str,
                "batting_stats": {...},
                "bowling_stats": {...},
                "specialization": str,
                "specialization_confidence": float,
                "recent_form": {...},
                "best_performances": {...},
                "career_highlights": [...]
            }
        """
        if not batting_records and not bowling_records:
            return {
                "player_id": player_id,
                "player_name": player_name,
                "career_summary": "No career data available",
                "batting_stats": {},
                "bowling_stats": {},
                "specialization": "Unknown",
                "specialization_confidence": 0.0,
                "recent_form": {},
                "best_performances": {},
                "career_highlights": [],
            }

        # Analyze batting
        batting_stats = PlayerCareerAnalyzer._analyze_batting(batting_records)
        
        # Analyze bowling
        bowling_stats = PlayerCareerAnalyzer._analyze_bowling(bowling_records)
        
        # Determine specialization
        specialization, confidence = PlayerCareerAnalyzer._determine_specialization(
            batting_stats, bowling_stats, batting_records
        )
        
        # Analyze recent form
        recent_form = PlayerCareerAnalyzer._analyze_recent_form(
            batting_records, bowling_records
        )
        
        # Find best performances
        best_performances = PlayerCareerAnalyzer._get_best_performances(
            batting_records, bowling_records
        )
        
        # Generate career highlights
        career_highlights = PlayerCareerAnalyzer._generate_career_highlights(
            player_name, batting_stats, bowling_stats, best_performances
        )
        
        # Generate summary
        career_summary = PlayerCareerAnalyzer._generate_summary(
            player_name, specialization, batting_stats, bowling_stats, recent_form
        )
        
        return {
            "player_id": player_id,
            "player_name": player_name,
            "career_summary": career_summary,
            "batting_stats": batting_stats,
            "bowling_stats": bowling_stats,
            "specialization": specialization,
            "specialization_confidence": confidence,
            "recent_form": recent_form,
            "best_performances": best_performances,
            "career_highlights": career_highlights,
        }

    @staticmethod
    def _analyze_batting(records: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze batting statistics from records."""
        if not records:
            return {}
        
        total_runs = sum(r.get("runs", 0) for r in records)
        total_innings = len(records)
        
        # Runs per inning
        runs_list = [r.get("runs", 0) for r in records]
        avg_runs = total_runs / total_innings if total_innings > 0 else 0
        
        # Consistency (std deviation)
        if len(runs_list) > 1:
            consistency = statistics.stdev(runs_list)
        else:
            consistency = 0
        
        # Strike rate
        total_balls = sum(r.get("balls_faced", 0) for r in records)
        strike_rate = (total_runs / total_balls * 100) if total_balls > 0 else 0
        
        # Boundary efficiency
        total_fours = sum(r.get("fours", 0) for r in records)
        total_sixes = sum(r.get("sixes", 0) for r in records)
        boundary_runs = (total_fours * 4) + (total_sixes * 6)
        boundary_pct = (boundary_runs / total_runs * 100) if total_runs > 0 else 0
        
        # Out percentage
        outs = sum(1 for r in records if r.get("is_out", False))
        out_pct = (outs / total_innings * 100) if total_innings > 0 else 0
        
        # Best and worst
        best_score = max(runs_list) if runs_list else 0
        worst_score = min(runs_list) if runs_list else 0
        
        # Half-centuries and centuries
        fifties = sum(1 for r in runs_list if 50 <= r < 100)
        centuries = sum(1 for r in runs_list if r >= 100)
        
        return {
            "matches": total_innings,
            "total_runs": total_runs,
            "average": round(avg_runs, 2),
            "consistency_score": round(100 - min(consistency / 10, 100), 1),  # Higher is more consistent
            "strike_rate": round(strike_rate, 2),
            "boundary_percentage": round(boundary_pct, 1),
            "fours": total_fours,
            "sixes": total_sixes,
            "best_score": best_score,
            "worst_score": worst_score,
            "fifties": fifties,
            "centuries": centuries,
            "out_percentage": round(out_pct, 1),
            "dismissal_rate": round(100 - out_pct, 1),  # % of times not out
        }

    @staticmethod
    def _analyze_bowling(records: list[dict[str, Any]]) -> dict[str, Any]:
        """Analyze bowling statistics from records."""
        if not records:
            return {}
        
        total_wickets = sum(r.get("wickets_taken", 0) for r in records)
        total_runs = sum(r.get("runs_conceded", 0) for r in records)
        total_overs = sum(r.get("overs_bowled", 0) for r in records)
        total_maidens = sum(r.get("maidens", 0) for r in records)
        
        matches = len(records)
        
        # Economy rate
        economy = (total_runs / total_overs) if total_overs > 0 else 0
        
        # Average wickets per match
        avg_wickets = total_wickets / matches if matches > 0 else 0
        
        # Maiden percentage
        maiden_pct = (total_maidens / total_overs * 100) if total_overs > 0 else 0
        
        return {
            "matches": matches,
            "total_wickets": total_wickets,
            "total_overs": round(total_overs, 1),
            "runs_conceded": total_runs,
            "economy_rate": round(economy, 2),
            "average_wickets_per_match": round(avg_wickets, 2),
            "maiden_percentage": round(maiden_pct, 1),
            "maidens": total_maidens,
        }

    @staticmethod
    def _determine_specialization(
        batting_stats: dict[str, Any],
        bowling_stats: dict[str, Any],
        batting_records: list[dict[str, Any]],
    ) -> tuple[str, float]:
        """Determine player specialization (opener, finisher, bowler, all-rounder)."""
        
        specialization_scores = defaultdict(float)
        
        # Check for all-rounder
        is_allrounder = (
            batting_stats.get("total_runs", 0) >= PlayerCareerAnalyzer.ALLROUNDER_BATTING_THRESHOLD
            and bowling_stats.get("total_wickets", 0) >= PlayerCareerAnalyzer.ALLROUNDER_BOWLING_THRESHOLD
        )
        
        if is_allrounder:
            specialization_scores["All-rounder"] = 0.9
        
        # Check for bowler
        bowling_overs = bowling_stats.get("total_overs", 0)
        if bowling_overs >= PlayerCareerAnalyzer.BOWLER_MIN_OVERS and not is_allrounder:
            specialization_scores["Bowler"] = 0.85
        
        # Check for opener/finisher
        if batting_records:
            # Try to infer position from order (simplified - would need actual batting order data)
            # For now, use performance patterns
            avg_runs = batting_stats.get("average", 0)
            sr = batting_stats.get("strike_rate", 0)
            
            # Openers typically: higher average, moderate SR, more consistent
            if avg_runs > 30 and 70 < sr < 120:
                specialization_scores["Opener"] = 0.75
            
            # Finishers typically: good SR, aggressive, sometimes lower average but match-winning
            if sr > 120:
                specialization_scores["Finisher"] = 0.80
        
        # Default to batter if nothing else matches
        if not specialization_scores:
            if batting_stats:
                specialization_scores["Batter"] = 0.7
            elif bowling_stats:
                specialization_scores["Bowler"] = 0.7
            else:
                specialization_scores["Player"] = 0.5
        
        # Get highest specialization
        best_spec = max(specialization_scores.items(), key=lambda x: x[1])
        return best_spec[0], best_spec[1]

    @staticmethod
    def _analyze_recent_form(
        batting_records: list[dict[str, Any]],
        bowling_records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Analyze recent form (last 5 matches)."""
        recent_form = {
            "recent_matches": 0,
            "recent_runs": 0,
            "recent_average": 0.0,
            "recent_strike_rate": 0.0,
            "recent_wickets": 0,
            "trend": "stable",  # "improving", "declining", "stable"
            "last_match_performance": "Not available",
        }
        
        if not batting_records and not bowling_records:
            return recent_form
        
        # Get last 5 batting records
        recent_batting = batting_records[-5:] if batting_records else []
        recent_runs = sum(r.get("runs", 0) for r in recent_batting)
        recent_balls = sum(r.get("balls_faced", 0) for r in recent_batting)
        recent_count = len(recent_batting)
        
        recent_form["recent_matches"] = recent_count
        recent_form["recent_runs"] = recent_runs
        
        if recent_count > 0:
            recent_form["recent_average"] = round(recent_runs / recent_count, 2)
            recent_form["recent_strike_rate"] = round(
                (recent_runs / recent_balls * 100) if recent_balls > 0 else 0, 2
            )
        
        # Bowling from last 5 records
        recent_bowling = bowling_records[-5:] if bowling_records else []
        recent_wickets = sum(r.get("wickets_taken", 0) for r in recent_bowling)
        recent_form["recent_wickets"] = recent_wickets
        
        # Trend analysis
        if len(recent_batting) >= 3:
            first_half_avg = sum(r.get("runs", 0) for r in recent_batting[:2]) / 2
            second_half_avg = sum(r.get("runs", 0) for r in recent_batting[2:]) / len(recent_batting[2:])
            
            if second_half_avg > first_half_avg * 1.15:
                recent_form["trend"] = "improving"
            elif second_half_avg < first_half_avg * 0.85:
                recent_form["trend"] = "declining"
        
        # Last match
        if recent_batting:
            last_score = recent_batting[-1].get("runs", 0)
            recent_form["last_match_performance"] = f"{last_score} runs"
        
        return recent_form

    @staticmethod
    def _get_best_performances(
        batting_records: list[dict[str, Any]],
        bowling_records: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Get player's best performances."""
        performances = {
            "best_batting": None,
            "best_bowling": None,
            "best_partnership": None,
        }
        
        # Best batting
        if batting_records:
            best_bat = max(batting_records, key=lambda r: r.get("runs", 0))
            performances["best_batting"] = {
                "runs": best_bat.get("runs", 0),
                "balls_faced": best_bat.get("balls_faced", 0),
                "fours": best_bat.get("fours", 0),
                "sixes": best_bat.get("sixes", 0),
                "date": best_bat.get("match_date", "Unknown"),
            }
        
        # Best bowling
        if bowling_records:
            best_bowl = max(bowling_records, key=lambda r: r.get("wickets_taken", 0))
            performances["best_bowling"] = {
                "wickets": best_bowl.get("wickets_taken", 0),
                "overs": best_bowl.get("overs_bowled", 0),
                "runs_conceded": best_bowl.get("runs_conceded", 0),
                "economy": round(
                    best_bowl.get("runs_conceded", 0) / best_bowl.get("overs_bowled", 1),
                    2
                ),
                "date": best_bowl.get("match_date", "Unknown"),
            }
        
        return performances

    @staticmethod
    def _generate_career_highlights(
        player_name: str,
        batting_stats: dict[str, Any],
        bowling_stats: dict[str, Any],
        best_performances: dict[str, Any],
    ) -> list[str]:
        """Generate career highlight achievements."""
        highlights = []
        
        # Batting highlights
        if batting_stats:
            if batting_stats.get("centuries", 0) > 0:
                highlights.append(f"🏆 Scored {batting_stats['centuries']} century/centuries")
            
            if batting_stats.get("fifties", 0) >= 3:
                highlights.append(f"⭐ {batting_stats['fifties']} half-centuries in career")
            
            consistency = batting_stats.get("consistency_score", 0)
            if consistency > 70:
                highlights.append("📊 Exceptional consistency in performance")
            
            if batting_stats.get("strike_rate", 0) > 130:
                highlights.append("⚡ Aggressive striker with high strike rate")
            
            if batting_stats.get("boundary_percentage", 0) > 40:
                highlights.append("🎯 Excellent boundary hitter (40%+ runs from 4s & 6s)")
        
        # Bowling highlights
        if bowling_stats:
            if bowling_stats.get("total_wickets", 0) >= 10:
                highlights.append(
                    f"🎱 {bowling_stats['total_wickets']} career wickets at {bowling_stats.get('economy_rate', 0)} economy"
                )
            
            if bowling_stats.get("economy_rate", 0) < 5.0:
                highlights.append("🛡️ Economical bowler (economy <5.0)")
            
            if bowling_stats.get("maiden_percentage", 0) > 15:
                highlights.append(f"⭐ Strong control bowler ({bowling_stats.get('maiden_percentage', 0):.0f}% maidens)")
        
        # Default highlights if none
        if not highlights:
            highlights.append("Player on career journey - building records")
        
        return highlights

    @staticmethod
    def _generate_summary(
        player_name: str,
        specialization: str,
        batting_stats: dict[str, Any],
        bowling_stats: dict[str, Any],
        recent_form: dict[str, Any],
    ) -> str:
        """Generate a human-readable career summary."""
        
        parts = []
        
        # Introduction
        parts.append(f"{player_name} is a {specialization}.")
        
        # Batting summary
        if batting_stats:
            avg = batting_stats.get("average", 0)
            sr = batting_stats.get("strike_rate", 0)
            matches = batting_stats.get("matches", 0)
            
            if matches > 0:
                parts.append(
                    f"In {matches} matches, {player_name} has averaged {avg} runs with a strike rate of {sr}."
                )
        
        # Bowling summary
        if bowling_stats and bowling_stats.get("total_wickets", 0) > 0:
            wickets = bowling_stats.get("total_wickets", 0)
            economy = bowling_stats.get("economy_rate", 0)
            parts.append(f"With the ball, {player_name} has {wickets} wickets at an economy of {economy}.")
        
        # Recent form
        trend = recent_form.get("trend", "stable")
        if trend == "improving":
            parts.append(f"Recent form is improving - showing positive momentum in recent matches.")
        elif trend == "declining":
            parts.append(f"Recent form has been declining - looking to regain consistency.")
        else:
            parts.append(f"Playing with steady, consistent performances recently.")
        
        return " ".join(parts)


def get_player_career_summary(
    player_id: str,
    player_name: str,
    batting_records: list[dict[str, Any]],
    bowling_records: list[dict[str, Any]],
) -> dict[str, Any]:
    """
    Convenience function to generate player career summary.
    
    This is the main entry point for API usage.
    """
    return PlayerCareerAnalyzer.analyze_player_career(
        player_id=player_id,
        player_name=player_name,
        batting_records=batting_records,
        bowling_records=bowling_records,
    )
