"""
Pitch Heatmap Generator Service

Generates pitch heatmaps showing scoring and dismissal zones
from ball-by-ball delivery data.
"""

from dataclasses import dataclass, field
from enum import Enum


class HeatmapType(str, Enum):
    """Types of heatmaps to generate."""

    RUNS = "runs"
    DISMISSALS = "dismissals"
    BOWLER_RELEASE = "bowler_release"
    BATTING_CONTACT = "batting_contact"


class PitchZone(str, Enum):
    """Cricket pitch zones for heatmap."""

    OFF_SIDE_SHORT = "off_short"
    OFF_SIDE_FULL = "off_full"
    OFF_SIDE_YORKER = "off_yorker"
    LEG_SIDE_SHORT = "leg_short"
    LEG_SIDE_FULL = "leg_full"
    LEG_SIDE_YORKER = "leg_yorker"
    MIDDLE_SHORT = "middle_short"
    MIDDLE_FULL = "middle_full"
    MIDDLE_YORKER = "middle_yorker"
    WIDE_OFF = "wide_off"
    WIDE_LEG = "wide_leg"


@dataclass
class HeatmapDataPoint:
    """Single data point in a heatmap."""

    zone: str  # PitchZone
    x_coordinate: float  # 0-100 (pitch width)
    y_coordinate: float  # 0-100 (pitch length)
    value: float  # 0-100, intensity of heatmap
    count: int  # Number of deliveries in this zone
    detail: str | None = None  # e.g., "4 runs", "2 wickets"


@dataclass
class PitchHeatmap:
    """Complete pitch heatmap visualization data."""

    heatmap_id: str
    heatmap_type: str  # HeatmapType
    player_id: str | None = None
    player_name: str | None = None
    bowler_id: str | None = None
    bowler_name: str | None = None
    game_id: str | None = None
    match_phase: str | None = None
    data_points: list[HeatmapDataPoint] = field(default_factory=list)
    min_value: float = 0.0
    max_value: float = 100.0
    average_value: float = 0.0
    total_events: int = 0
    metadata: dict = field(default_factory=dict)


@dataclass
class BatterProfile:
    """Batter's spatial scoring/dismissal profile."""

    player_id: str
    player_name: str
    profile_type: str  # "scoring" or "dismissals"
    total_runs: int
    total_dismissals: int
    scoring_zones: dict[str, int]  # Zone -> runs
    dismissal_zones: dict[str, int]  # Zone -> dismissal count
    strong_zones: list[str]  # Zones with >20% runs
    weak_zones: list[str]  # Zones with dismissals
    scoring_efficiency: dict[str, float]  # Zone -> runs/delivery
    preferred_areas: dict[str, float]  # Zone -> percentage of deliveries faced


@dataclass
class BowlerProfile:
    """Bowler's spatial delivery profile."""

    player_id: str
    player_name: str
    total_deliveries: int
    primary_zones: list[str]  # Most common delivery zones
    zone_effectiveness: dict[str, float]  # Zone -> wicket rate %
    release_distribution: dict[str, float]  # Zone -> percentage
    accuracy_score: float  # 0-100, concentration in zones
    variation_zones: list[str]  # Zones used for variation


@dataclass
class MatchupAnalysis:
    """Analysis of batter vs bowler spatial matchup."""

    batter_id: str
    batter_name: str
    bowler_id: str
    bowler_name: str
    total_deliveries: int
    dangerous_areas: list[str]  # Batter strong zones where bowler delivers
    weak_overlap_areas: list[str]  # Where batter is weak, bowler bowls
    dismissal_zones: list[str]  # Where bowler has dismissed this batter
    recommendation: str  # Strategic recommendation


class PitchHeatmapGenerator:
    """
    Generates pitch heatmaps from delivery data.
    Uses static methods for heatmap analysis.
    """

    # Pitch coordinate system: 0-100 scale
    # X: 0 (leg) - 50 (middle) - 100 (off)
    # Y: 0 (bowler) - 50 (middle) - 100 (stumps)

    # Zone definitions (x_min, x_max, y_min, y_max)
    ZONE_BOUNDARIES = {
        PitchZone.OFF_SIDE_SHORT: (60, 100, 0, 35),
        PitchZone.OFF_SIDE_FULL: (60, 100, 35, 70),
        PitchZone.OFF_SIDE_YORKER: (60, 100, 70, 100),
        PitchZone.LEG_SIDE_SHORT: (0, 40, 0, 35),
        PitchZone.LEG_SIDE_FULL: (0, 40, 35, 70),
        PitchZone.LEG_SIDE_YORKER: (0, 40, 70, 100),
        PitchZone.MIDDLE_SHORT: (40, 60, 0, 35),
        PitchZone.MIDDLE_FULL: (40, 60, 35, 70),
        PitchZone.MIDDLE_YORKER: (40, 60, 70, 100),
        PitchZone.WIDE_OFF: (85, 100, 35, 70),
        PitchZone.WIDE_LEG: (0, 15, 35, 70),
    }

    @staticmethod
    def generate_batter_scoring_heatmap(
        player_id: str,
        player_name: str,
        deliveries: list[dict],
    ) -> PitchHeatmap:
        """
        Generate heatmap showing where batter scores runs.

        Args:
            player_id: Batter identifier
            player_name: Batter name
            deliveries: List of delivery dicts with keys:
                       zone, runs_scored, bowler_zone, etc.

        Returns:
            PitchHeatmap with scoring distribution
        """
        zone_data: dict[str, dict] = {}
        total_runs = 0
        max_runs_in_zone = 0

        # Aggregate deliveries by zone
        for delivery in deliveries:
            zone = delivery.get("zone", PitchZone.MIDDLE_FULL)
            runs = delivery.get("runs_scored", 0)
            total_runs += runs

            if zone not in zone_data:
                zone_data[zone] = {"runs": 0, "count": 0}

            zone_data[zone]["runs"] += runs
            zone_data[zone]["count"] += 1
            max_runs_in_zone = max(max_runs_in_zone, zone_data[zone]["runs"])

        # Create heatmap data points
        data_points = []
        average_value = 0.0
        total_events = len(deliveries)

        for zone, data in zone_data.items():
            runs = data["runs"]
            count = data["count"]

            # Normalize to 0-100 scale
            intensity = (runs / max_runs_in_zone * 100) if max_runs_in_zone > 0 else 0
            average_value += intensity

            # Get zone coordinates
            x_min, x_max, y_min, y_max = PitchHeatmapGenerator.ZONE_BOUNDARIES.get(
                zone, (40, 60, 35, 70)
            )
            x_center = (x_min + x_max) / 2
            y_center = (y_min + y_max) / 2

            data_points.append(
                HeatmapDataPoint(
                    zone=zone,
                    x_coordinate=x_center,
                    y_coordinate=y_center,
                    value=intensity,
                    count=count,
                    detail=f"{runs} runs ({count} balls)",
                )
            )

        average_value = average_value / len(data_points) if data_points else 0

        return PitchHeatmap(
            heatmap_id=f"batter_scoring_{player_id}",
            heatmap_type=HeatmapType.RUNS,
            player_id=player_id,
            player_name=player_name,
            data_points=data_points,
            min_value=0.0,
            max_value=100.0,
            average_value=round(average_value, 1),
            total_events=total_events,
            metadata={
                "total_runs": total_runs,
                "average_runs_per_delivery": round(total_runs / total_events, 2)
                if total_events > 0
                else 0,
            },
        )

    @staticmethod
    def generate_dismissal_heatmap(
        player_id: str,
        player_name: str,
        dismissals: list[dict],
    ) -> PitchHeatmap:
        """
        Generate heatmap showing where batter gets dismissed.
        """
        zone_data: dict[str, dict] = {}
        total_dismissals = 0

        for dismissal in dismissals:
            zone = dismissal.get("zone", PitchZone.MIDDLE_FULL)
            dismissal_type = dismissal.get("dismissal_type", "unknown")

            if zone not in zone_data:
                zone_data[zone] = {"count": 0, "types": {}}

            zone_data[zone]["count"] += 1
            zone_data[zone]["types"][dismissal_type] = (
                zone_data[zone]["types"].get(dismissal_type, 0) + 1
            )
            total_dismissals += 1

        # Create heatmap data points
        data_points = []
        max_dismissals = max(
            (data["count"] for data in zone_data.values()),
            default=1,
        )

        for zone, data in zone_data.items():
            count = data["count"]
            intensity = (count / max_dismissals * 100) if max_dismissals > 0 else 0

            # Get zone coordinates
            x_min, x_max, y_min, y_max = PitchHeatmapGenerator.ZONE_BOUNDARIES.get(
                zone, (40, 60, 35, 70)
            )
            x_center = (x_min + x_max) / 2
            y_center = (y_min + y_max) / 2

            dismissal_types = ", ".join(f"{t}({c})" for t, c in data["types"].items())

            data_points.append(
                HeatmapDataPoint(
                    zone=zone,
                    x_coordinate=x_center,
                    y_coordinate=y_center,
                    value=intensity,
                    count=count,
                    detail=f"{count} dismissals ({dismissal_types})",
                )
            )

        average_value = sum(p.value for p in data_points) / len(data_points) if data_points else 0

        return PitchHeatmap(
            heatmap_id=f"batter_dismissal_{player_id}",
            heatmap_type=HeatmapType.DISMISSALS,
            player_id=player_id,
            player_name=player_name,
            data_points=data_points,
            min_value=0.0,
            max_value=100.0,
            average_value=round(average_value, 1),
            total_events=total_dismissals,
            metadata={"total_dismissals": total_dismissals},
        )

    @staticmethod
    def generate_bowler_release_heatmap(
        bowler_id: str,
        bowler_name: str,
        deliveries: list[dict],
    ) -> PitchHeatmap:
        """Generate heatmap of bowler's release point consistency."""
        zone_data: dict[str, int] = {}
        total_deliveries = 0

        for delivery in deliveries:
            zone = delivery.get("zone", PitchZone.MIDDLE_FULL)
            zone_data[zone] = zone_data.get(zone, 0) + 1
            total_deliveries += 1

        # Create heatmap data points
        data_points = []
        max_zone_count = max(zone_data.values()) if zone_data else 1

        for zone, count in zone_data.items():
            intensity = (count / max_zone_count * 100) if max_zone_count > 0 else 0

            x_min, x_max, y_min, y_max = PitchHeatmapGenerator.ZONE_BOUNDARIES.get(
                zone, (40, 60, 35, 70)
            )
            x_center = (x_min + x_max) / 2
            y_center = (y_min + y_max) / 2

            percentage = round((count / total_deliveries) * 100, 1)

            data_points.append(
                HeatmapDataPoint(
                    zone=zone,
                    x_coordinate=x_center,
                    y_coordinate=y_center,
                    value=intensity,
                    count=count,
                    detail=f"{count} deliveries ({percentage}%)",
                )
            )

        # Calculate accuracy (concentration in zones)
        accuracy = (max_zone_count / total_deliveries * 100) if total_deliveries > 0 else 0

        average_value = sum(p.value for p in data_points) / len(data_points) if data_points else 0

        return PitchHeatmap(
            heatmap_id=f"bowler_release_{bowler_id}",
            heatmap_type=HeatmapType.BOWLER_RELEASE,
            bowler_id=bowler_id,
            bowler_name=bowler_name,
            data_points=data_points,
            min_value=0.0,
            max_value=100.0,
            average_value=round(average_value, 1),
            total_events=total_deliveries,
            metadata={
                "accuracy_score": round(accuracy, 1),
                "primary_zone": max(zone_data, key=zone_data.get) if zone_data else "unknown",
            },
        )

    @staticmethod
    def analyze_batter_profile(
        player_id: str,
        player_name: str,
        deliveries: list[dict],
        dismissals: list[dict],
    ) -> BatterProfile:
        """
        Analyze comprehensive batter spatial profile.
        """
        scoring_zones: dict[str, int] = {}
        dismissal_zones: dict[str, int] = {}
        zone_deliveries: dict[str, int] = {}
        total_runs = 0
        total_dismissals = len(dismissals)

        # Aggregate scoring data
        for delivery in deliveries:
            zone = delivery.get("zone", PitchZone.MIDDLE_FULL)
            runs = delivery.get("runs_scored", 0)

            scoring_zones[zone] = scoring_zones.get(zone, 0) + runs
            zone_deliveries[zone] = zone_deliveries.get(zone, 0) + 1
            total_runs += runs

        # Aggregate dismissal data
        for dismissal in dismissals:
            zone = dismissal.get("zone", PitchZone.MIDDLE_FULL)
            dismissal_zones[zone] = dismissal_zones.get(zone, 0) + 1

        # Identify strong/weak zones
        strong_zones = []
        weak_zones = []
        threshold = (total_runs / len(scoring_zones)) * 0.8 if scoring_zones else 0

        for zone, runs in scoring_zones.items():
            if runs > threshold * 1.2:
                strong_zones.append(zone)

        for zone, count in dismissal_zones.items():
            if count >= 2:
                weak_zones.append(zone)

        # Calculate efficiency
        scoring_efficiency = {}
        for zone, runs in scoring_zones.items():
            deliveries_in_zone = zone_deliveries.get(zone, 1)
            scoring_efficiency[zone] = round(runs / deliveries_in_zone, 2)

        # Calculate zone preferences
        total_deliveries = len(deliveries)
        preferred_areas = {
            zone: round((count / total_deliveries) * 100, 1)
            for zone, count in zone_deliveries.items()
        }

        return BatterProfile(
            player_id=player_id,
            player_name=player_name,
            profile_type="scoring",
            total_runs=total_runs,
            total_dismissals=total_dismissals,
            scoring_zones=scoring_zones,
            dismissal_zones=dismissal_zones,
            strong_zones=strong_zones,
            weak_zones=weak_zones,
            scoring_efficiency=scoring_efficiency,
            preferred_areas=preferred_areas,
        )

    @staticmethod
    def analyze_bowler_profile(
        bowler_id: str,
        bowler_name: str,
        deliveries: list[dict],
        wickets: list[dict],
    ) -> BowlerProfile:
        """Analyze comprehensive bowler spatial delivery profile."""
        zone_counts: dict[str, int] = {}
        zone_wickets: dict[str, int] = {}
        total_deliveries = 0

        for delivery in deliveries:
            zone = delivery.get("zone", PitchZone.MIDDLE_FULL)
            zone_counts[zone] = zone_counts.get(zone, 0) + 1
            total_deliveries += 1

        for wicket in wickets:
            zone = wicket.get("zone", PitchZone.MIDDLE_FULL)
            zone_wickets[zone] = zone_wickets.get(zone, 0) + 1

        # Primary zones (>15% of deliveries)
        primary_zones = [
            zone for zone, count in zone_counts.items() if (count / total_deliveries) > 0.15
        ]

        # Zone effectiveness (wicket rate)
        zone_effectiveness = {
            zone: round(
                (zone_wickets.get(zone, 0) / zone_counts[zone]) * 100,
                1,
            )
            for zone in zone_counts
        }

        # Release distribution
        release_distribution = {
            zone: round((count / total_deliveries) * 100, 1) for zone, count in zone_counts.items()
        }

        # Accuracy score (concentration)
        max_zone_deliveries = max(zone_counts.values()) if zone_counts else 1
        accuracy = round((max_zone_deliveries / total_deliveries) * 100, 1)

        # Variation zones (zones with <5% deliveries but effective)
        variation_zones = [
            zone
            for zone, count in zone_counts.items()
            if (count / total_deliveries) < 0.05 and zone_effectiveness.get(zone, 0) >= 10
        ]

        return BowlerProfile(
            player_id=bowler_id,
            player_name=bowler_name,
            total_deliveries=total_deliveries,
            primary_zones=primary_zones,
            zone_effectiveness=zone_effectiveness,
            release_distribution=release_distribution,
            accuracy_score=accuracy,
            variation_zones=variation_zones,
        )

    @staticmethod
    def analyze_matchup(
        batter_id: str,
        batter_name: str,
        bowler_id: str,
        bowler_name: str,
        deliveries: list[dict],
        dismissals: list[dict],
    ) -> MatchupAnalysis:
        """
        Analyze batter vs bowler spatial matchup.
        """
        batter_profile = PitchHeatmapGenerator.analyze_batter_profile(
            batter_id, batter_name, deliveries, dismissals
        )
        bowler_profile = PitchHeatmapGenerator.analyze_bowler_profile(
            bowler_id, bowler_name, deliveries, []
        )

        # Find dangerous areas (batter strong + bowler delivers)
        dangerous_areas = [
            zone for zone in batter_profile.strong_zones if zone in bowler_profile.primary_zones
        ]

        # Find weak overlaps (batter weak + bowler delivers there)
        weak_overlap_areas = [
            zone for zone in batter_profile.weak_zones if zone in bowler_profile.primary_zones
        ]

        # Find dismissal zones
        dismissal_zones = batter_profile.weak_zones

        # Generate recommendation
        if weak_overlap_areas:
            recommendation = f"Exploit weak overlap areas: {', '.join(weak_overlap_areas[:2])}"
        elif dangerous_areas:
            recommendation = f"Avoid batter's strong zones: {', '.join(dangerous_areas[:2])}"
        else:
            recommendation = "Maintain accuracy and variation"

        return MatchupAnalysis(
            batter_id=batter_id,
            batter_name=batter_name,
            bowler_id=bowler_id,
            bowler_name=bowler_name,
            total_deliveries=len(deliveries),
            dangerous_areas=dangerous_areas,
            weak_overlap_areas=weak_overlap_areas,
            dismissal_zones=dismissal_zones,
            recommendation=recommendation,
        )
