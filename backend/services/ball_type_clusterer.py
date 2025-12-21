"""
Ball Type Clustering Service

Classifies and clusters deliveries by ball type characteristics,
providing insights into delivery patterns and effectiveness.
"""

from dataclasses import dataclass, field
from enum import Enum


class DeliveryType(str, Enum):
    """Types of cricket deliveries."""

    FAST = "fast"
    SHORT_PITCH = "short_pitch"
    YORKER = "yorker"
    SLOWER_BALL = "slower_ball"
    BOUNCER = "bouncer"
    HALF_TRACKER = "half_tracker"
    FULL_LENGTH = "full_length"
    GOOD_LENGTH = "good_length"
    SPIN = "spin"
    DOOSRA = "doosra"
    GOOGLY = "googly"
    FLIPPER = "flipper"


class ClusterVariation(str, Enum):
    """Delivery variation within cluster."""

    STANDARD = "standard"
    VARIATION = "variation"
    SLOWER = "slower"
    FULLER = "fuller"
    SHORTER = "shorter"


@dataclass
class DeliveryCharacteristic:
    """Characteristics defining a ball type."""

    line: str  # off, leg, middle, wide
    length: str  # short, good, full, yorker
    pace: float  # 0-160+ km/h (relative scale 0-100)
    spin: float  # 0-100, rotations
    movement: str  # inswing, outswing, legbreak, offbreak
    bounce_index: float  # 0-100, how much it bounces


@dataclass
class DeliveryCluster:
    """Grouping of similar delivery types."""

    cluster_id: str
    delivery_type: str  # DeliveryType
    cluster_name: str
    description: str
    sample_count: int
    effectiveness_percentage: float  # 0-100
    success_rate: float  # Wicket rate
    average_runs_conceded: float
    variation_zones: list[str] = field(default_factory=list)
    key_characteristics: dict = field(default_factory=dict)


@dataclass
class DeliveryAnalysis:
    """Single delivery analysis."""

    delivery_id: str
    bowler_id: str
    bowler_name: str
    delivery_type: str  # DeliveryType
    variation: str  # ClusterVariation
    line: str
    length: str
    runs_conceded: int
    is_wicket: bool
    batter_reaction: str  # defensive, aggressive, uncomfortable
    outcome: str  # dot, boundary, wicket, none
    confidence_score: float  # 0-100, certainty of classification


@dataclass
class BowlerDeliveryProfile:
    """Bowler's delivery composition and patterns."""

    bowler_id: str
    bowler_name: str
    total_deliveries: int
    delivery_clusters: list[DeliveryCluster] = field(default_factory=list)
    primary_clusters: list[str] = field(default_factory=list)  # Top 3
    variation_score: float = 0.0  # 0-100, delivery diversity
    clustering_accuracy: float = 0.0  # 0-100, cluster consistency
    most_effective_cluster: str | None = None
    least_effective_cluster: str | None = None


@dataclass
class BatterDeliveryVulnerability:
    """Batter's vulnerability to delivery types."""

    batter_id: str
    batter_name: str
    vulnerable_clusters: list[str] = field(default_factory=list)
    vulnerable_delivery_types: dict[str, float] = field(default_factory=dict)  # Type -> avg runs
    strong_against: list[str] = field(default_factory=list)
    dismissal_delivery_types: list[str] = field(default_factory=list)
    recommended_bowling_strategy: str = ""


@dataclass
class ClusterMatrix:
    """Matrix of delivery type effectiveness against all batters."""

    cluster_type: str
    total_samples: int
    wicket_count: int
    dot_count: int
    boundary_count: int
    average_runs: float
    effectiveness_rating: float  # 0-100


class BallTypeClusterer:
    """
    Clusters cricket deliveries into types based on characteristics.
    Uses static methods for delivery analysis.
    """

    # Cluster definitions with thresholds
    CLUSTER_DEFINITIONS = {
        DeliveryType.FAST: {
            "pace_min": 70,
            "pace_max": 100,
            "spin_max": 20,
            "description": "Pace bowled at 130-160 km/h",
        },
        DeliveryType.SHORT_PITCH: {
            "length": "short",
            "pace_min": 50,
            "description": "Short pitched delivery around chest height",
        },
        DeliveryType.YORKER: {
            "length": "yorker",
            "pace_min": 40,
            "description": "Delivery at the stumps, difficult to hit",
        },
        DeliveryType.SLOWER_BALL: {
            "pace_max": 50,
            "spin_min": 30,
            "description": "Slower pace bowling for variation",
        },
        DeliveryType.BOUNCER: {
            "length": "short",
            "bounce_min": 60,
            "description": "Short delivery that bounces above head",
        },
        DeliveryType.HALF_TRACKER: {
            "length": "mid",
            "description": "Delivery between short and full",
        },
        DeliveryType.FULL_LENGTH: {
            "length": "full",
            "pace_min": 30,
            "description": "Full length delivery",
        },
        DeliveryType.GOOD_LENGTH: {
            "length": "good",
            "description": "Nagging length making it hard to score",
        },
        DeliveryType.SPIN: {
            "spin_min": 60,
            "movement": "spin",
            "description": "Spin bowling with significant rotation",
        },
        DeliveryType.GOOGLY: {
            "spin_min": 70,
            "movement": "offbreak",
            "description": "Off-break bowled from leg-break action",
        },
    }

    @staticmethod
    def classify_delivery(
        delivery_data: dict,
    ) -> DeliveryAnalysis:
        """
        Classify a single delivery into a cluster type.

        Args:
            delivery_data: Dict with keys: pace, spin, line, length, movement,
                          bounce_index, runs_conceded, is_wicket, bowler_id, bowler_name

        Returns:
            DeliveryAnalysis with classification and confidence
        """
        pace = delivery_data.get("pace", 0)
        spin = delivery_data.get("spin", 0)
        length = delivery_data.get("length", "good")
        movement = delivery_data.get("movement", "none")

        # Determine delivery type based on characteristics
        delivery_type = BallTypeClusterer._determine_delivery_type(pace, spin, length, movement)

        # Determine variation
        variation = BallTypeClusterer._determine_variation(pace, spin, length)

        # Determine batter reaction
        batter_reaction = BallTypeClusterer._assess_batter_reaction(
            delivery_data.get("line", "middle"),
            delivery_data.get("bounce_index", 0),
            delivery_type,
        )

        # Calculate confidence
        confidence = BallTypeClusterer._calculate_classification_confidence(
            pace, spin, length, movement
        )

        return DeliveryAnalysis(
            delivery_id=delivery_data.get("delivery_id", "unknown"),
            bowler_id=delivery_data.get("bowler_id", ""),
            bowler_name=delivery_data.get("bowler_name", ""),
            delivery_type=delivery_type,
            variation=variation,
            line=delivery_data.get("line", "middle"),
            length=length,
            runs_conceded=delivery_data.get("runs_conceded", 0),
            is_wicket=delivery_data.get("is_wicket", False),
            batter_reaction=batter_reaction,
            outcome=BallTypeClusterer._determine_outcome(
                delivery_data.get("is_wicket", False),
                delivery_data.get("runs_conceded", 0),
            ),
            confidence_score=confidence,
        )

    @staticmethod
    def _determine_delivery_type(
        pace: float,
        spin: float,
        length: str,
        movement: str,
    ) -> str:
        """Determine delivery type from characteristics."""
        # Check spin first
        if spin > 70:
            if "offbreak" in movement or "spinbreak" in movement:
                return DeliveryType.SPIN
            elif "legbreak" in movement:
                return DeliveryType.GOOGLY
            return DeliveryType.SPIN

        # Check length-based deliveries (priority over pace)
        if length == "yorker":
            return DeliveryType.YORKER
        elif length == "short":
            if pace > 70 and spin < 20:
                return DeliveryType.BOUNCER
            else:
                return DeliveryType.SHORT_PITCH
        elif length == "full":
            return DeliveryType.FULL_LENGTH
        elif length == "good":
            if pace > 70 and spin < 20:
                return DeliveryType.FAST
            else:
                return DeliveryType.GOOD_LENGTH

        # Check pace-based deliveries
        if pace > 70:  # Fast bowling
            if spin < 20:
                return DeliveryType.FAST

        # Check slower balls
        if pace < 50 and spin > 30:
            return DeliveryType.SLOWER_BALL

        # Default to good length
        return DeliveryType.GOOD_LENGTH

    @staticmethod
    def _determine_variation(pace: float, spin: float, length: str) -> str:
        """Determine if delivery is standard or variation."""
        if pace < 40 and spin > 40:
            return ClusterVariation.SLOWER
        elif length == "full":
            return ClusterVariation.FULLER
        elif length == "short":
            return ClusterVariation.SHORTER
        elif spin > 50:
            return ClusterVariation.VARIATION
        return ClusterVariation.STANDARD

    @staticmethod
    def _assess_batter_reaction(
        line: str,
        bounce_index: float,
        delivery_type: str,
    ) -> str:
        """Assess likely batter reaction."""
        if delivery_type == DeliveryType.YORKER:
            return "defensive"
        elif delivery_type == DeliveryType.BOUNCER and bounce_index > 70:
            return "uncomfortable"
        elif line == "off" or line == "leg":
            return "aggressive"
        return "defensive"

    @staticmethod
    def _determine_outcome(is_wicket: bool, runs_conceded: int) -> str:
        """Determine delivery outcome."""
        if is_wicket:
            return "wicket"
        elif runs_conceded == 0:
            return "dot"
        elif runs_conceded >= 4:
            return "boundary"
        else:
            return "runs"

    @staticmethod
    def _calculate_classification_confidence(
        pace: float,
        spin: float,
        length: str,
        movement: str,
    ) -> float:
        """Calculate confidence score (0-100) for classification."""
        confidence = 50.0

        # Add points for clear characteristics
        if length in ["yorker", "short", "full", "good"]:
            confidence += 15
        if pace > 70 or pace < 30:
            confidence += 15
        if spin > 50:
            confidence += 15
        if movement in ["inswing", "outswing", "legbreak", "offbreak"]:
            confidence += 10

        return min(confidence, 100.0)

    @staticmethod
    def analyze_bowler_deliveries(
        bowler_id: str,
        bowler_name: str,
        deliveries: list[dict],
    ) -> BowlerDeliveryProfile:
        """
        Analyze all deliveries from a bowler.

        Args:
            bowler_id: Bowler identifier
            bowler_name: Bowler name
            deliveries: List of delivery dicts

        Returns:
            Comprehensive delivery profile
        """
        if not deliveries:
            return BowlerDeliveryProfile(
                bowler_id=bowler_id,
                bowler_name=bowler_name,
                total_deliveries=0,
            )

        # Classify all deliveries
        classified = [BallTypeClusterer.classify_delivery(d) for d in deliveries]

        # Group by delivery type
        type_groups: dict[str, list[DeliveryAnalysis]] = {}
        for delivery in classified:
            if delivery.delivery_type not in type_groups:
                type_groups[delivery.delivery_type] = []
            type_groups[delivery.delivery_type].append(delivery)

        # Generate clusters
        clusters = []
        for delivery_type, group in type_groups.items():
            wicket_count = sum(1 for d in group if d.is_wicket)
            avg_runs = sum(d.runs_conceded for d in group) / len(group)
            effectiveness = (wicket_count / len(group)) * 50 + ((1 - avg_runs / 10) * 50)

            cluster = DeliveryCluster(
                cluster_id=f"{bowler_id}_{delivery_type}",
                delivery_type=delivery_type,
                cluster_name=delivery_type.replace("_", " ").title(),
                description=BallTypeClusterer.CLUSTER_DEFINITIONS.get(delivery_type, {}).get(  # type: ignore[arg-type, call-overload]
                    "description", ""
                ),
                sample_count=len(group),
                effectiveness_percentage=min(max(effectiveness, 0), 100),
                success_rate=(wicket_count / len(group)) * 100,
                average_runs_conceded=round(avg_runs, 2),
            )
            clusters.append(cluster)

        # Identify primary clusters (top 3)
        primary_clusters = sorted(clusters, key=lambda c: c.sample_count, reverse=True)[:3]
        primary_names = [c.delivery_type for c in primary_clusters]

        # Calculate variation score
        variation_score = (len(clusters) / 8) * 100  # 8 possible types

        # Find most/least effective
        most_effective: DeliveryCluster | None
        least_effective: DeliveryCluster | None
        if clusters:
            most_effective = max(clusters, key=lambda c: c.effectiveness_percentage)
            least_effective = min(clusters, key=lambda c: c.effectiveness_percentage)
        else:
            most_effective = None  # type: ignore[assignment]
            least_effective = None  # type: ignore[assignment]

        return BowlerDeliveryProfile(
            bowler_id=bowler_id,
            bowler_name=bowler_name,
            total_deliveries=len(deliveries),
            delivery_clusters=clusters,
            primary_clusters=primary_names,
            variation_score=min(variation_score, 100.0),
            clustering_accuracy=sum(d.confidence_score for d in classified) / len(classified),
            most_effective_cluster=most_effective.delivery_type if most_effective else None,
            least_effective_cluster=least_effective.delivery_type if least_effective else None,
        )

    @staticmethod
    def analyze_batter_vulnerabilities(
        batter_id: str,
        batter_name: str,
        faced_deliveries: list[dict],
    ) -> BatterDeliveryVulnerability:
        """
        Analyze batter's vulnerability to delivery types.
        """
        classified = [BallTypeClusterer.classify_delivery(d) for d in faced_deliveries]

        # Aggregate by delivery type
        type_stats: dict[str, dict] = {}
        for delivery in classified:
            dtype = delivery.delivery_type
            if dtype not in type_stats:
                type_stats[dtype] = {
                    "avg_runs": 0,
                    "count": 0,
                    "wickets": 0,
                }

            type_stats[dtype]["count"] += 1
            type_stats[dtype]["avg_runs"] += delivery.runs_conceded
            if delivery.is_wicket:
                type_stats[dtype]["wickets"] += 1

        # Finalize stats
        for dtype in type_stats:
            type_stats[dtype]["avg_runs"] /= type_stats[dtype]["count"]

        # Identify vulnerable types (high runs or dismissals)
        vulnerable = sorted(
            type_stats.items(),
            key=lambda x: (x[1]["wickets"], x[1]["avg_runs"]),
            reverse=True,
        )[:3]

        vulnerable_types = [t[0] for t in vulnerable]
        strong_types = sorted(
            type_stats.items(),
            key=lambda x: (x[1]["avg_runs"], x[1]["wickets"]),
        )[:2]
        strong_against = [t[0] for t in strong_types]

        dismissal_types = [d.delivery_type for d in classified if d.is_wicket]

        # Generate strategy
        if vulnerable_types:
            strategy = f"Avoid {vulnerable_types[0]}, use {vulnerable_types[0]}"
        else:
            strategy = "Maintain consistent line and length"

        return BatterDeliveryVulnerability(
            batter_id=batter_id,
            batter_name=batter_name,
            vulnerable_clusters=vulnerable_types,
            vulnerable_delivery_types={t[0]: t[1]["avg_runs"] for t in vulnerable},
            strong_against=strong_against,
            dismissal_delivery_types=dismissal_types,
            recommended_bowling_strategy=strategy,
        )

    @staticmethod
    def generate_cluster_matrix(
        deliveries: list[dict],
    ) -> dict[str, ClusterMatrix]:
        """
        Generate effectiveness matrix for all clusters across dataset.
        """
        classified = [BallTypeClusterer.classify_delivery(d) for d in deliveries]

        # Group by delivery type
        matrices: dict[str, ClusterMatrix] = {}
        for delivery in classified:
            dtype = delivery.delivery_type
            if dtype not in matrices:
                matrices[dtype] = {  # type: ignore[assignment]
                    "total": 0,
                    "wickets": 0,
                    "dots": 0,
                    "boundaries": 0,
                    "runs": 0,
                }

            matrices[dtype]["total"] += 1  # type: ignore[index]
            if delivery.is_wicket:
                matrices[dtype]["wickets"] += 1  # type: ignore[index]
            elif delivery.outcome == "dot":
                matrices[dtype]["dots"] += 1  # type: ignore[index]
            elif delivery.outcome == "boundary":
                matrices[dtype]["boundaries"] += 1  # type: ignore[index]
            matrices[dtype]["runs"] += delivery.runs_conceded  # type: ignore[index]

        # Create ClusterMatrix objects
        result = {}
        for dtype, stats in matrices.items():
            total = stats["total"]  # type: ignore[index]
            avg_runs = stats["runs"] / total if total > 0 else 0  # type: ignore[index]
            effectiveness = (
                (stats["wickets"] / total) * 50 + ((stats["dots"] / total) * 50) if total > 0 else 0  # type: ignore[index]
            )

            result[dtype] = ClusterMatrix(
                cluster_type=dtype,
                total_samples=total,
                wicket_count=stats["wickets"],  # type: ignore[index]
                dot_count=stats["dots"],  # type: ignore[index]
                boundary_count=stats["boundaries"],  # type: ignore[index]
                average_runs=round(avg_runs, 2),
                effectiveness_rating=min(max(effectiveness, 0), 100),
            )

        return result
