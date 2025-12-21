"""
Dismissal Pattern Analyzer Service

Analyzes player dismissal patterns to identify recurring vulnerabilities
and recommend targeted interventions.
"""

from dataclasses import dataclass
from enum import Enum


class DismissalType(str, Enum):
    """Cricket dismissal types."""

    BOWLED = "bowled"
    LBW = "lbw"
    CAUGHT = "caught"
    CAUGHT_OUT = "caught_out"
    STUMPED = "stumped"
    RUN_OUT = "run_out"
    HIT_WICKET = "hit_wicket"
    OBSTRUCTING = "obstructing"
    HANDLED_BALL = "handled_ball"
    TIMED_OUT = "timed_out"


class MatchPhase(str, Enum):
    """Match phases for pattern analysis."""

    POWERPLAY = "powerplay"
    MIDDLE_OVERS = "middle_overs"
    DEATH_OVERS = "death_overs"
    FULL_MATCH = "full_match"


@dataclass
class DismissalRecord:
    """Single dismissal event."""

    dismissal_id: str
    dismissal_type: str  # From DismissalType
    bowler_name: str | None = None
    bowler_id: str | None = None
    delivery_type: str | None = None  # pace, spin, etc.
    line: str | None = None  # off, leg, middle, wide, yorker
    length: str | None = None  # full, good, short, bounce
    match_phase: str = MatchPhase.FULL_MATCH
    runs_at_dismissal: int = 0
    deliveries_faced: int = 0
    boundary_attempt: bool = False
    aggressive: bool = False
    context: str | None = None  # Description of context


@dataclass
class DismissalPattern:
    """Pattern group of related dismissals."""

    pattern_id: str
    pattern_name: str  # e.g., "LBW on legside yorkers"
    pattern_type: str  # dismissal_type, bowler_type, delivery_type, phase, etc.
    pattern_value: str  # e.g., "lbw", "pace_bowling", "yorker", "death_overs"
    dismissal_count: int
    dismissal_percentage: float
    confidence: float  # 0-1, how confident the pattern is
    severity: str  # high, medium, low - based on frequency and impact
    context: str  # Human-readable description
    recommendation: str  # Specific improvement recommendation


@dataclass
class DismissalSituation:
    """High-risk dismissal situation."""

    situation_id: str
    situation_type: str  # e.g., "pace_yorker_legside"
    trigger_factors: list[str]
    dismissal_count: int
    success_rate_vs_this: float  # Bowler/delivery success rate against player
    risk_level: str  # critical, high, medium, low
    scenario_description: str


@dataclass
class PlayerDismissalProfile:
    """Complete dismissal vulnerability profile for a player."""

    player_id: str
    player_name: str
    total_dismissals: int
    dismissals_by_type: dict[str, int]  # DismissalType -> count
    dismissals_by_phase: dict[str, int]  # MatchPhase -> count
    dismissals_by_delivery: dict[str, int]  # delivery_type -> count
    dismissals_by_line: dict[str, int]  # line -> count
    dismissals_by_length: dict[str, int]  # length -> count
    top_patterns: list[DismissalPattern]  # Sorted by severity/frequency
    critical_situations: list[DismissalSituation]
    overall_vulnerability_score: float  # 0-100, higher = more vulnerable
    primary_vulnerability: str | None  # Main weakness
    secondary_vulnerabilities: list[str]  # Other weaknesses
    improvement_areas: list[str]  # Ranked by impact


@dataclass
class DismissalTrend:
    """Dismissal trend over time."""

    period: str  # "last_5", "last_10", "last_20", etc.
    dismissal_count: int
    average_runs_at_dismissal: float
    average_deliveries_faced: float
    trend_direction: str  # improving, stable, declining
    pattern_changes: list[str]  # Notable changes in patterns


@dataclass
class TeamDismissalContext:
    """Team-level dismissal patterns."""

    team_id: str
    team_name: str
    total_team_dismissals: int
    common_patterns: list[DismissalPattern]
    vulnerable_players: list[tuple[str, float]]  # (player_name, vulnerability_score)
    phase_vulnerability: dict[str, float]  # Phase -> avg_vulnerability
    bowler_effectiveness_vs_team: list[tuple[str, float]]  # (bowler_name, effectiveness)
    team_recommendations: list[str]


class DismissalPatternAnalyzer:
    """
    Analyzes dismissal patterns to identify player vulnerabilities.
    Uses static methods for dismissal analysis.
    """

    # Dismissal type weightings for severity
    DISMISSAL_SEVERITY = {
        DismissalType.BOWLED: 0.9,  # Technical failure
        DismissalType.LBW: 0.85,  # Technical failure
        DismissalType.STUMPED: 0.88,  # Technical/positioning failure
        DismissalType.CAUGHT: 0.75,  # Can be skill or luck
        DismissalType.CAUGHT_OUT: 0.75,
        DismissalType.RUN_OUT: 0.6,  # Can be external factors
        DismissalType.HIT_WICKET: 0.8,  # Technical/positioning failure
        DismissalType.HANDLED_BALL: 0.95,  # Rule violation
        DismissalType.OBSTRUCTING: 0.9,  # Rule violation
    }

    # Phase multipliers for vulnerability scoring
    PHASE_MULTIPLIERS = {
        MatchPhase.POWERPLAY: 0.8,  # More technical play expected
        MatchPhase.MIDDLE_OVERS: 1.0,  # Baseline
        MatchPhase.DEATH_OVERS: 1.3,  # Higher risk context
    }

    # Delivery type vulnerability combinations
    HIGH_RISK_COMBINATIONS = [
        ("lbw", "pace", "yorker", "leg"),  # Yorker on leg to left-hander
        ("bowled", "pace", "yorker", "middle"),  # Yorker through middle
        ("caught", "pace", "short", "mid"),  # Short ball caught at mid
        ("lbw", "spin", "tossed", "leg"),  # Tossed up leg break to left-hander
        ("caught", "spin", "length", "deep"),  # Length ball caught at boundary
    ]

    @staticmethod
    def analyze_player_dismissals(
        player_id: str,
        player_name: str,
        dismissals: list[DismissalRecord],
    ) -> PlayerDismissalProfile:
        """
        Analyze all dismissals for a player and generate vulnerability profile.

        Args:
            player_id: Player identifier
            player_name: Player name
            dismissals: List of dismissal records

        Returns:
            Complete dismissal profile with patterns and vulnerabilities
        """
        if not dismissals:
            return PlayerDismissalProfile(
                player_id=player_id,
                player_name=player_name,
                total_dismissals=0,
                dismissals_by_type={},
                dismissals_by_phase={},
                dismissals_by_delivery={},
                dismissals_by_line={},
                dismissals_by_length={},
                top_patterns=[],
                critical_situations=[],
                overall_vulnerability_score=0.0,
                primary_vulnerability=None,
                secondary_vulnerabilities=[],
                improvement_areas=[],
            )

        # Aggregate dismissal data
        dismissals_by_type: dict[str, int] = {}
        dismissals_by_phase: dict[str, int] = {}
        dismissals_by_delivery: dict[str, int] = {}
        dismissals_by_line: dict[str, int] = {}
        dismissals_by_length: dict[str, int] = {}
        total_runs_at_dismissal = 0
        boundary_dismissals = 0
        aggressive_dismissals = 0

        for d in dismissals:
            # Type aggregation
            dismissals_by_type[d.dismissal_type] = dismissals_by_type.get(d.dismissal_type, 0) + 1

            # Phase aggregation
            dismissals_by_phase[d.match_phase] = dismissals_by_phase.get(d.match_phase, 0) + 1

            # Delivery/line/length aggregation
            if d.delivery_type:
                dismissals_by_delivery[d.delivery_type] = (
                    dismissals_by_delivery.get(d.delivery_type, 0) + 1
                )
            if d.line:
                dismissals_by_line[d.line] = dismissals_by_line.get(d.line, 0) + 1
            if d.length:
                dismissals_by_length[d.length] = dismissals_by_length.get(d.length, 0) + 1

            total_runs_at_dismissal += d.runs_at_dismissal
            if d.boundary_attempt:
                boundary_dismissals += 1
            if d.aggressive:
                aggressive_dismissals += 1

        # Identify patterns
        patterns = DismissalPatternAnalyzer._identify_patterns(
            player_name,
            dismissals,
            dismissals_by_type,
            dismissals_by_delivery,
            dismissals_by_phase,
        )

        # Identify critical situations
        situations = DismissalPatternAnalyzer._identify_critical_situations(
            player_name,
            dismissals,
            dismissals_by_type,
        )

        # Calculate vulnerability score
        vulnerability_score = DismissalPatternAnalyzer._calculate_vulnerability_score(
            len(dismissals),
            dismissals_by_type,
            dismissals_by_phase,
            aggressive_dismissals,
            boundary_dismissals,
        )

        # Identify primary/secondary vulnerabilities
        primary_vulnerability = None
        secondary_vulnerabilities = []
        if patterns:
            primary_vulnerability = patterns[0].pattern_value
            secondary_vulnerabilities = [p.pattern_value for p in patterns[1:3]]

        # Improvement areas (ranked by impact)
        improvement_areas = DismissalPatternAnalyzer._identify_improvement_areas(
            dismissals_by_type,
            dismissals_by_delivery,
            dismissals_by_phase,
            patterns,
        )

        return PlayerDismissalProfile(
            player_id=player_id,
            player_name=player_name,
            total_dismissals=len(dismissals),
            dismissals_by_type=dismissals_by_type,
            dismissals_by_phase=dismissals_by_phase,
            dismissals_by_delivery=dismissals_by_delivery,
            dismissals_by_line=dismissals_by_line,
            dismissals_by_length=dismissals_by_length,
            top_patterns=patterns,
            critical_situations=situations,
            overall_vulnerability_score=vulnerability_score,
            primary_vulnerability=primary_vulnerability,
            secondary_vulnerabilities=secondary_vulnerabilities,
            improvement_areas=improvement_areas,
        )

    @staticmethod
    def _identify_patterns(
        player_name: str,
        dismissals: list[DismissalRecord],
        dismissals_by_type: dict[str, int],
        dismissals_by_delivery: dict[str, int],
        dismissals_by_phase: dict[str, int],
    ) -> list[DismissalPattern]:
        """Identify recurring dismissal patterns."""
        patterns: list[DismissalPattern] = []
        total = len(dismissals)

        # Type-based patterns
        for dismissal_type, count in sorted(
            dismissals_by_type.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:3]:
            if count >= 2:  # At least 2 occurrences
                percentage = (count / total) * 100
                confidence = min(percentage / 100, 1.0)
                severity = "high" if percentage >= 40 else "medium" if percentage >= 20 else "low"

                patterns.append(
                    DismissalPattern(
                        pattern_id=f"dtype_{dismissal_type}",
                        pattern_name=f"{dismissal_type.title()} Pattern",
                        pattern_type="dismissal_type",
                        pattern_value=dismissal_type,
                        dismissal_count=count,
                        dismissal_percentage=round(percentage, 1),
                        confidence=round(confidence, 2),
                        severity=severity,
                        context=f"{player_name} dismissed {dismissal_type} {count} times ({percentage:.1f}% of dismissals)",
                        recommendation=DismissalPatternAnalyzer._get_type_recommendation(
                            dismissal_type
                        ),
                    )
                )

        # Delivery type patterns
        for delivery_type, count in sorted(
            dismissals_by_delivery.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:3]:
            if count >= 2:
                percentage = (count / total) * 100
                confidence = min(percentage / 100, 1.0)
                severity = "high" if percentage >= 40 else "medium" if percentage >= 25 else "low"

                patterns.append(
                    DismissalPattern(
                        pattern_id=f"delivery_{delivery_type}",
                        pattern_name=f"Vulnerable to {delivery_type.title()} Bowling",
                        pattern_type="delivery_type",
                        pattern_value=delivery_type,
                        dismissal_count=count,
                        dismissal_percentage=round(percentage, 1),
                        confidence=round(confidence, 2),
                        severity=severity,
                        context=f"Dismissed {count} times to {delivery_type} bowling",
                        recommendation=DismissalPatternAnalyzer._get_delivery_recommendation(
                            delivery_type
                        ),
                    )
                )

        # Phase-based patterns
        for phase, count in sorted(
            dismissals_by_phase.items(),
            key=lambda x: x[1],
            reverse=True,
        )[:2]:
            if count >= 2:
                percentage = (count / total) * 100
                if percentage >= 50:  # Only show if it's a majority
                    patterns.append(
                        DismissalPattern(
                            pattern_id=f"phase_{phase}",
                            pattern_name=f"Vulnerable During {phase.title()}",
                            pattern_type="phase",
                            pattern_value=phase,
                            dismissal_count=count,
                            dismissal_percentage=round(percentage, 1),
                            confidence=round(min(percentage / 100, 1.0), 2),
                            severity="high" if phase == MatchPhase.DEATH_OVERS else "medium",
                            context=f"{count} dismissals during {phase}",
                            recommendation=DismissalPatternAnalyzer._get_phase_recommendation(
                                phase
                            ),
                        )
                    )

        # Sort by severity and frequency
        patterns.sort(
            key=lambda p: (
                {"high": 0, "medium": 1, "low": 2}[p.severity],
                -p.dismissal_count,
            )
        )

        return patterns[:5]  # Top 5 patterns

    @staticmethod
    def _identify_critical_situations(
        player_name: str,
        dismissals: list[DismissalRecord],
        dismissals_by_type: dict[str, int],
    ) -> list[DismissalSituation]:
        """Identify critical high-risk dismissal situations."""
        situations: list[DismissalSituation] = []

        # Combination patterns (delivery + type + context)
        combinations: dict[str, int] = {}
        for d in dismissals:
            if d.delivery_type and d.line:
                key = f"{d.delivery_type}_{d.line}"
                combinations[key] = combinations.get(key, 0) + 1

        for combo, count in sorted(combinations.items(), key=lambda x: x[1], reverse=True)[:3]:
            if count >= 2:
                delivery, line = combo.split("_")
                situations.append(
                    DismissalSituation(
                        situation_id=f"sit_{combo}",
                        situation_type=combo,
                        trigger_factors=[f"{delivery} on {line}"],
                        dismissal_count=count,
                        success_rate_vs_this=min((count / len(dismissals)) * 100, 1.0),
                        risk_level="critical" if count >= 3 else "high",
                        scenario_description=f"{player_name} has been dismissed {count} times to {delivery} deliveries on the {line}",
                    )
                )

        return situations

    @staticmethod
    def _calculate_vulnerability_score(
        total_dismissals: int,
        dismissals_by_type: dict[str, int],
        dismissals_by_phase: dict[str, int],
        aggressive_dismissals: int,
        boundary_dismissals: int,
    ) -> float:
        """Calculate overall vulnerability score (0-100)."""
        if total_dismissals == 0:
            return 0.0

        score = 0.0

        # Base score from total dismissals (normalize to 0-30)
        score += min((total_dismissals / 20) * 30, 30)

        # Technical dismissals (bowled, lbw) are more concerning (0-30)
        technical_count = dismissals_by_type.get("bowled", 0) + dismissals_by_type.get("lbw", 0)
        score += min((technical_count / total_dismissals) * 30, 30)

        # Death overs vulnerability (0-20)
        death_count = dismissals_by_phase.get(MatchPhase.DEATH_OVERS, 0)
        score += min((death_count / total_dismissals) * 20, 20)

        # Boundary/aggressive dismissals (0-20)
        aggressive_total = aggressive_dismissals + boundary_dismissals
        score += min((aggressive_total / total_dismissals) * 20, 20)

        return min(round(score, 1), 100.0)

    @staticmethod
    def _identify_improvement_areas(
        dismissals_by_type: dict[str, int],
        dismissals_by_delivery: dict[str, int],
        dismissals_by_phase: dict[str, int],
        patterns: list[DismissalPattern],
    ) -> list[str]:
        """Identify ranked improvement areas."""
        areas = []

        # From patterns
        for pattern in patterns[:3]:
            if pattern.severity == "high":
                if pattern.pattern_type == "dismissal_type":
                    areas.append(f"Reduce {pattern.pattern_value} dismissals via technique drills")
                elif pattern.pattern_type == "delivery_type":
                    areas.append(f"Practice against {pattern.pattern_value} bowling")
                elif pattern.pattern_type == "phase":
                    areas.append(f"Improve performance during {pattern.pattern_value}")

        # Death overs specific
        if dismissals_by_phase.get(MatchPhase.DEATH_OVERS, 0) >= 2:
            areas.append("Death overs composure and decision-making")

        # Aggressive play management
        if len(areas) < 4:
            areas.append("Balanced aggression vs risk management")

        return areas[:4]

    @staticmethod
    def _get_type_recommendation(dismissal_type: str) -> str:
        """Get recommendation for a dismissal type."""
        recommendations = {
            "bowled": "Work on line and length discipline, improve footwork to stay behind the line",
            "lbw": "Improve pad placement and forward defense technique",
            "caught": "Reduce risky shot selection, practice catching avoidance",
            "stumped": "Improve distance management against spinners",
            "run_out": "Communication with partner and quick running execution",
            "hit_wicket": "Improve footwork and bat control during shots",
        }
        return recommendations.get(
            dismissal_type, "Review technique against this mode of dismissal"
        )

    @staticmethod
    def _get_delivery_recommendation(delivery_type: str) -> str:
        """Get recommendation for vulnerability to delivery type."""
        recommendations = {
            "pace": "Face more pace bowling in practice, work on counter-attacking strokes",
            "spin": "Improve recognition and footwork against spin, practice sweep shots",
            "yorker": "Improve yorker-reading ability, practice bat placement to dig them out",
            "short": "Perfect short ball techniques (duck, sway, pull shot)",
            "full": "Reduce aggressive drives outside off stump",
        }
        return recommendations.get(
            delivery_type, "Practice and conditioning against this delivery type"
        )

    @staticmethod
    def _get_phase_recommendation(phase: str) -> str:
        """Get recommendation for phase vulnerability."""
        recommendations: dict[str, str] = {
            MatchPhase.POWERPLAY.value: "Build strong foundation in powerplay, practice aggressive yet safe strokes",
            MatchPhase.MIDDLE_OVERS.value: "Maintain momentum and composure during middle overs",
            MatchPhase.DEATH_OVERS.value: "Death overs training: composure, explosive shots, risk management",
        }
        return recommendations.get(phase, "Analyze match situation and adapt strategy accordingly")

    @staticmethod
    def analyze_team_dismissals(
        team_id: str,
        team_name: str,
        player_profiles: list[PlayerDismissalProfile],
    ) -> TeamDismissalContext:
        """
        Analyze dismissal patterns across a team.
        """
        if not player_profiles:
            return TeamDismissalContext(
                team_id=team_id,
                team_name=team_name,
                total_team_dismissals=0,
                common_patterns=[],
                vulnerable_players=[],
                phase_vulnerability={},
                bowler_effectiveness_vs_team=[],
                team_recommendations=[],
            )

        total_dismissals = sum(p.total_dismissals for p in player_profiles)

        # Vulnerable players (by vulnerability score)
        vulnerable_players = [
            (p.player_name, p.overall_vulnerability_score)
            for p in player_profiles
            if p.total_dismissals > 0
        ]
        vulnerable_players.sort(key=lambda x: x[1], reverse=True)

        # Phase vulnerability aggregation
        phase_vulnerability: dict[str, float] = {}
        for phase in MatchPhase:
            total_phase = sum(p.dismissals_by_phase.get(phase, 0) for p in player_profiles)
            if total_phase > 0:
                phase_vulnerability[phase.value] = round((total_phase / total_dismissals) * 100, 1)

        # Team recommendations
        team_recommendations = []
        if vulnerable_players:
            top_vulnerable = vulnerable_players[0]
            team_recommendations.append(
                f"Focus on {top_vulnerable[0]}'s technical improvement (vulnerability: {top_vulnerable[1]:.0f}/100)"
            )

        if phase_vulnerability.get(MatchPhase.DEATH_OVERS, 0) > 30:
            team_recommendations.append("Team-wide death overs training required")

        team_recommendations.append(
            "Regular technical coaching sessions based on individual patterns"
        )

        return TeamDismissalContext(
            team_id=team_id,
            team_name=team_name,
            total_team_dismissals=total_dismissals,
            common_patterns=[],
            vulnerable_players=vulnerable_players[:5],
            phase_vulnerability=phase_vulnerability,
            bowler_effectiveness_vs_team=[],
            team_recommendations=team_recommendations[:3],
        )

    @staticmethod
    def get_dismissal_trend(
        dismissals: list[DismissalRecord],
        period: str = "last_10",
    ) -> DismissalTrend:
        """Analyze dismissal trend over time."""
        if not dismissals:
            return DismissalTrend(
                period=period,
                dismissal_count=0,
                average_runs_at_dismissal=0.0,
                average_deliveries_faced=0.0,
                trend_direction="stable",
                pattern_changes=[],
            )

        # Use last N dismissals based on period
        period_map = {"last_5": 5, "last_10": 10, "last_20": 20}
        limit = period_map.get(period, 10)
        recent_dismissals = dismissals[-limit:]

        avg_runs = sum(d.runs_at_dismissal for d in recent_dismissals) / len(recent_dismissals)
        avg_deliveries = sum(d.deliveries_faced for d in recent_dismissals) / len(recent_dismissals)

        # Trend direction (simplified: compare early vs recent)
        early_avg_runs = sum(
            d.runs_at_dismissal for d in recent_dismissals[: len(recent_dismissals) // 2]
        ) / max(1, len(recent_dismissals) // 2)
        late_avg_runs = sum(
            d.runs_at_dismissal for d in recent_dismissals[len(recent_dismissals) // 2 :]
        ) / max(1, len(recent_dismissals) - len(recent_dismissals) // 2)

        if late_avg_runs > early_avg_runs * 1.2:
            trend_direction = "improving"
        elif late_avg_runs < early_avg_runs * 0.8:
            trend_direction = "declining"
        else:
            trend_direction = "stable"

        return DismissalTrend(
            period=period,
            dismissal_count=len(recent_dismissals),
            average_runs_at_dismissal=round(avg_runs, 1),
            average_deliveries_faced=round(avg_deliveries, 1),
            trend_direction=trend_direction,
            pattern_changes=[],
        )
