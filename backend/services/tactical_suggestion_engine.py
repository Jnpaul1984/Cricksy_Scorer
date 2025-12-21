"""
Tactical Suggestion Engine for real-time coaching recommendations

Provides AI-powered suggestions during match scoring:
- Best bowler selection based on batter profile
- Weakness analysis (delivery type recommendations)
- Fielding setup recommendations based on batter scoring zones
"""

from dataclasses import dataclass, field
from typing import Any
from enum import Enum


class DeliveryType(str, Enum):
    """Delivery type classifications"""

    PACE = "pace"
    SPIN = "spin"
    FAST_MEDIUM = "fast_medium"
    OFF_SPIN = "off_spin"
    LEG_SPIN = "leg_spin"
    YORKER = "yorker"
    BOUNCER = "bouncer"
    SLOW_BALL = "slow_ball"
    KNUCKLEBALL = "knuckleball"


class LineType(str, Enum):
    """Ball line classifications"""

    OFF_STUMP = "off_stump"
    LEG_STUMP = "leg_stump"
    MIDDLE = "middle"
    OUTSIDE_OFF = "outside_off"
    OUTSIDE_LEG = "outside_leg"
    YORKER_LENGTH = "yorker_length"


@dataclass
class BowlerProfile:
    """Bowler statistical profile"""

    bowler_id: str
    bowler_name: str
    total_deliveries: int
    runs_conceded: int
    wickets_taken: int
    economy_rate: float
    strike_rate_against: float  # Runs per 100 balls
    average_speed: float | None = None
    common_delivery: str = DeliveryType.PACE

    @property
    def effectiveness_score(self) -> float:
        """Higher score = more effective bowler (0-100)"""
        if self.total_deliveries == 0:
            return 50.0

        # Wicket efficiency: normalized to 0-100 where 1 wicket per 6 balls = 50 pts
        wicket_rate_per_6 = (self.wickets_taken / max(1, self.total_deliveries)) * 6
        wicket_score = min(100, wicket_rate_per_6 * 50)  # 1 per 6 = 50 pts, 2 per 6 = 100 pts

        # Economy efficiency: lower is better. 3.5 = 50pts, 2.0 = 70pts, 5.0 = 25pts
        economy_diff = max(0, 5.0 - self.economy_rate)  # Higher difference = lower economy
        economy_score = min(100, 10 + (economy_diff * 15))  # Range 10-100

        # Combine: 60% wicket efficiency, 40% economy
        score = (wicket_score * 0.6) + (economy_score * 0.4)
        return round(min(100, score), 2)


@dataclass
class BatterProfile:
    """Batter statistical profile and preferences"""

    batter_id: str
    batter_name: str
    total_runs: int
    total_deliveries: int
    dismissals: int
    batting_average: float
    strike_rate: float

    # Weakness indicators
    dot_ball_weakness: float = 0.0  # 0-100, higher = weaker against dots
    pace_weakness: float = 0.0  # 0-100, higher = struggles vs pace
    spin_weakness: float = 0.0  # 0-100, higher = struggles vs spin
    short_ball_strength: float = 50.0  # 0-100, higher = strong vs short balls
    yorker_weakness: float = 0.0  # 0-100

    # Recent form
    last_5_runs: list[int] = field(default_factory=list)
    recent_dismissals: int = 0

    @property
    def current_form_score(self) -> float:
        """Score from 0-100 based on last 5 innings"""
        if not self.last_5_runs:
            return 50.0

        avg_recent = sum(self.last_5_runs) / len(self.last_5_runs)
        score = min(100, (avg_recent / 50) * 100)  # Normalize to 50-run average
        return round(score, 1)

    @property
    def is_in_form(self) -> bool:
        """True if batter is in good recent form"""
        return self.current_form_score >= 60


@dataclass
class ScoringZone:
    """Batter scoring pattern by pitch location"""

    line: str  # off, leg, middle, etc.
    length: str  # full, good, short, yorker
    runs_scored: int
    dismissals: int
    deliveries: int

    @property
    def run_rate(self) -> float:
        """Runs per delivery in this zone"""
        if self.deliveries == 0:
            return 0.0
        return round(self.runs_scored / self.deliveries, 2)

    @property
    def dismissal_risk(self) -> float:
        """Dismissal probability 0-100"""
        if self.deliveries == 0:
            return 0.0
        return round((self.dismissals / self.deliveries) * 100, 1)


@dataclass
class BestBowlerSuggestion:
    """Recommendation for best bowler to bowl next"""

    bowler_id: str
    bowler_name: str
    reason: str
    effectiveness_vs_batter: float  # 0-100 score
    expected_economy: float
    confidence: float  # 0-1


@dataclass
class WeaknessAnalysis:
    """Analysis of batter weaknesses"""

    primary_weakness: str  # The delivery type to exploit
    weakness_score: float  # 0-100, higher = more exploitable
    secondary_weakness: str | None = None
    recommended_line: str = LineType.OFF_STUMP
    recommended_length: str = "good"
    recommended_speed: float | None = None
    confidence: float = 0.7


@dataclass
class FieldingZone:
    """Fielding position recommendation"""

    position: str  # e.g., "mid-wicket", "mid-on", "third-man"
    priority: int  # 1 = highest priority (most likely runs)
    coverage_reason: str


@dataclass
class FieldingSetup:
    """Complete fielding recommendation"""

    bowler_id: str
    batter_id: str
    primary_zone: str  # Primary scoring zone to block
    recommended_positions: list[FieldingZone]
    confidence: float  # 0-1
    reasoning: str


class TacticalSuggestionEngine:
    """
    AI-powered tactical suggestions for coaches during match play.

    Provides real-time recommendations for:
    1. Best bowler selection
    2. Weakness analysis (delivery type)
    3. Fielding setup
    """

    # Thresholds for suggestion confidence
    MIN_SAMPLE_SIZE = 3  # Minimum deliveries for statistical validity
    EFFECTIVENESS_THRESHOLD = (
        40  # Minimum effectiveness score to recommend (adjusted for realistic data)
    )

    @staticmethod
    def get_best_bowler(
        bowlers: list[dict],
        batter_profile: dict,
        recent_bowlers: list[str] | None = None,
    ) -> BestBowlerSuggestion | None:
        """
        Recommend best bowler based on batter profile and stats.

        Args:
            bowlers: List of bowler statistics
            batter_profile: Current batter data
            recent_bowlers: Recently bowled bowlers (to avoid repeats)

        Returns:
            BestBowlerSuggestion or None
        """
        if not bowlers:
            return None

        recent_bowlers = recent_bowlers or []
        best_score: float = 0
        best_bowler = None

        for bowler_data in bowlers:
            bowler = BowlerProfile(**bowler_data)

            # Skip bowlers who just bowled
            if bowler.bowler_id in recent_bowlers:
                effectiveness = bowler.effectiveness_score * 0.7  # 30% penalty
            else:
                effectiveness = bowler.effectiveness_score

            # Match bowler type to batter weakness
            batter = BatterProfile(**batter_profile)
            weakness_match = TacticalSuggestionEngine._match_bowler_to_weakness(bowler, batter)

            # Combined score
            total_score = (effectiveness * 0.6) + (weakness_match * 0.4)

            if total_score > best_score:
                best_score = total_score
                best_bowler = bowler

        if not best_bowler or best_score < TacticalSuggestionEngine.EFFECTIVENESS_THRESHOLD:
            return None

        batter = BatterProfile(**batter_profile)
        return BestBowlerSuggestion(
            bowler_id=best_bowler.bowler_id,
            bowler_name=best_bowler.bowler_name,
            reason=f"High effectiveness ({best_bowler.effectiveness_score:.0f}) vs {batter.batter_name}'s profile",
            effectiveness_vs_batter=round(best_score, 1),
            expected_economy=best_bowler.economy_rate,
            confidence=min(1.0, best_score / 100),
        )

    @staticmethod
    def analyze_weakness(
        batter_profile: dict,
        dismissal_history: list[dict] | None = None,
    ) -> WeaknessAnalysis:
        """
        Analyze batter weaknesses and recommend delivery type.

        Args:
            batter_profile: Batter statistics and weakness indicators
            dismissal_history: Recent dismissals for context

        Returns:
            WeaknessAnalysis with recommendations
        """
        batter = BatterProfile(**batter_profile)
        dismissal_history = dismissal_history or []

        # Find primary weakness
        weaknesses = {
            DeliveryType.PACE: batter.pace_weakness,
            DeliveryType.SPIN: batter.spin_weakness,
            DeliveryType.YORKER: batter.yorker_weakness,
            "dot_strategy": batter.dot_ball_weakness,
        }

        primary = max(weaknesses.items(), key=lambda x: x[1])
        primary_weakness = primary[0]  # Key: DeliveryType or string
        weakness_score = primary[1]  # Value: float

        # Find secondary weakness
        secondary_weakness = None
        if len(dismissal_history) >= TacticalSuggestionEngine.MIN_SAMPLE_SIZE:
            # Recent dismissals indicate pattern
            recent_types = [d.get("dismissal_type") for d in dismissal_history[-5:]]
            type_counts: dict[str, int] = {}
            for dt in recent_types:
                if dt:
                    type_counts[dt] = type_counts.get(dt, 0) + 1

            if type_counts:
                secondary_weakness = max(type_counts.items(), key=lambda x: x[1])[0]

        # Determine recommended line and length
        if primary_weakness == DeliveryType.YORKER:
            recommended_line = LineType.MIDDLE
            recommended_length = "yorker"
        elif primary_weakness == "dot_strategy":
            recommended_line = LineType.OFF_STUMP
            recommended_length = "good"
        else:
            recommended_line = LineType.OFF_STUMP
            recommended_length = "short" if batter.short_ball_strength < 50 else "good"

        return WeaknessAnalysis(
            primary_weakness=str(primary_weakness),
            weakness_score=round(weakness_score, 1),
            secondary_weakness=secondary_weakness,
            recommended_line=recommended_line,
            recommended_length=recommended_length,
            recommended_speed=135 if primary_weakness == DeliveryType.PACE else None,
            confidence=min(1.0, (weakness_score / 100)),
        )

    @staticmethod
    def recommend_fielding(
        bowler_data: dict,
        batter_data: dict,
        scoring_zones: list[dict],
    ) -> FieldingSetup:
        """
        Recommend fielding positions based on batter's scoring zones.

        Args:
            bowler_data: Bowler information
            batter_data: Batter profile
            scoring_zones: List of ScoringZone data

        Returns:
            FieldingSetup with recommended positions
        """
        zones = [ScoringZone(**z) for z in scoring_zones]

        # Sort zones by run rate (highest scoring zones first)
        priority_zones = sorted(zones, key=lambda z: z.run_rate, reverse=True)

        # Map zones to fielding positions
        position_mapping = {
            ("off", "full"): "cover",
            ("off", "good"): "point",
            ("off", "short"): "third-man",
            ("leg", "full"): "mid-on",
            ("leg", "good"): "square-leg",
            ("leg", "short"): "short-fine",
            ("middle", "full"): "mid-off",
            ("middle", "good"): "mid-wicket",
        }

        recommended_positions = []
        for idx, zone in enumerate(priority_zones[:3], 1):
            pos_key = (zone.line, zone.length)
            position = position_mapping.get(pos_key, "mid-field")

            recommended_positions.append(
                FieldingZone(
                    position=position,
                    priority=idx,
                    coverage_reason=f"Batter scores {zone.run_rate} runs/delivery here",
                )
            )

        return FieldingSetup(
            bowler_id=bowler_data.get("bowler_id", ""),
            batter_id=batter_data.get("batter_id", ""),
            primary_zone=f"{priority_zones[0].line}-{priority_zones[0].length}"
            if priority_zones
            else "off-good",
            recommended_positions=recommended_positions,
            confidence=min(1.0, (sum(z.deliveries for z in zones) / 20)),
            reasoning=f"Block primary scoring zone at {priority_zones[0].line} {priority_zones[0].length}",
        )

    @staticmethod
    def _match_bowler_to_weakness(
        bowler: BowlerProfile,
        batter: BatterProfile,
    ) -> float:
        """
        Score how well bowler's style matches batter's weakness (0-100).
        """
        score = 50.0  # Base score

        if (
            bowler.common_delivery == DeliveryType.PACE
            and batter.pace_weakness > 50
            or bowler.common_delivery == DeliveryType.SPIN
            and batter.spin_weakness > 50
        ):
            score += 25

        # Penalize if bowler recently bowled (fatigue)
        # This is handled by caller

        return min(100, score)


def get_tactical_suggestions(
    game_id: str,
    bowlers: list[dict],
    current_batter: dict,
    recent_bowlers: list[str] | None = None,
    scoring_zones: list[dict] | None = None,
    dismissal_history: list[dict] | None = None,
) -> dict[str, Any]:
    """
    Convenience function to get all tactical suggestions at once.

    Args:
        game_id: Game ID for reference
        bowlers: Available bowlers
        current_batter: Current batter profile
        recent_bowlers: Recently used bowlers
        scoring_zones: Batter's scoring zone breakdown
        dismissal_history: Recent dismissal patterns

    Returns:
        Dict with best_bowler, weakness, and fielding suggestions
    """
    engine = TacticalSuggestionEngine()

    return {
        "game_id": game_id,
        "best_bowler": engine.get_best_bowler(bowlers, current_batter, recent_bowlers),
        "weakness": engine.analyze_weakness(current_batter, dismissal_history),
        "fielding": engine.recommend_fielding(
            bowlers[0] if bowlers else {},
            current_batter,
            scoring_zones or [],
        )
        if scoring_zones
        else None,
    }
