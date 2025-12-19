"""
Training Drill Generator for personalized player development

Generates targeted training drills based on player weaknesses and match performance.
Each drill targets specific skill gaps identified through match analysis.
"""

from dataclasses import dataclass, field
from typing import Optional
from enum import Enum


class DrillSeverity(str, Enum):
    """Priority level for training drill"""
    HIGH = "high"  # Critical weakness, needs immediate attention
    MEDIUM = "medium"  # Important skill gap
    LOW = "low"  # Minor improvement area


class DrillCategory(str, Enum):
    """Type of training drill"""
    PACE_HANDLING = "pace_handling"  # Cope with fast bowling
    SPIN_HANDLING = "spin_handling"  # Play spin bowling
    DOT_BALL = "dot_ball"  # Survive pressure
    AGGRESSIVE = "aggressive"  # Scoring shots
    FIELDING = "fielding"  # Defensive positioning
    ENDURANCE = "endurance"  # Fitness and stamina
    WICKET_PROTECTION = "wicket_protection"  # Avoid dismissals
    BOUNDARY_HITTING = "boundary_hitting"  # Maximum scoring


@dataclass
class DrillTemplate:
    """Blueprint for a training drill"""
    category: DrillCategory
    name: str
    description: str
    duration_minutes: int  # How long the drill lasts
    reps_or_count: int  # Number of repetitions/deliveries
    focus_area: str  # What skill is being trained
    difficulty: int  # 1-10 scale


@dataclass
class TrainingDrill:
    """Personalized training drill recommendation"""
    drill_id: str
    player_id: str
    category: DrillCategory
    name: str
    description: str
    reason: str  # Why this drill is recommended
    severity: DrillSeverity
    
    # Drill specifics
    reps_or_count: int
    duration_minutes: int
    focus_area: str
    difficulty: int  # 1-10
    
    # Tracking
    recommended_frequency: str  # "daily", "3x/week", "weekly"
    expected_improvement: str  # What player should improve
    
    # Optional context
    weakness_score: Optional[float] = None  # 0-100, how severe is weakness
    confidence: Optional[float] = None  # 0-1, how confident is recommendation


@dataclass
class TrainingDrillPlan:
    """Complete personalized drill plan for a player"""
    player_id: str
    player_name: str
    drills: list[TrainingDrill] = field(default_factory=list)
    high_priority_count: int = 0
    medium_priority_count: int = 0
    low_priority_count: int = 0
    total_weekly_hours: float = 0.0
    focus_areas: list[str] = field(default_factory=list)
    last_updated: Optional[str] = None


class TrainingDrillGenerator:
    """
    AI-powered training drill recommendation engine.
    
    Analyzes player weaknesses from match performance and generates
    targeted drills for skill development.
    """
    
    # Drill templates library
    DRILL_TEMPLATES = {
        DrillCategory.PACE_HANDLING: [
            DrillTemplate(
                category=DrillCategory.PACE_HANDLING,
                name="Fast Bowling Gauntlet",
                description="Face 30 deliveries of 140+ km/h pace bowling",
                duration_minutes=20,
                reps_or_count=30,
                focus_area="Reaction time vs fast bowling",
                difficulty=9,
            ),
            DrillTemplate(
                category=DrillCategory.PACE_HANDLING,
                name="Pace Variation Response",
                description="Face varied pace (130-145 km/h) with unpredictable changes",
                duration_minutes=15,
                reps_or_count=25,
                focus_area="Handling pace variation",
                difficulty=8,
            ),
            DrillTemplate(
                category=DrillCategory.PACE_HANDLING,
                name="Short Pitch Practice",
                description="Face 20 short-pitched deliveries at pace",
                duration_minutes=15,
                reps_or_count=20,
                focus_area="Short ball handling",
                difficulty=7,
            ),
        ],
        DrillCategory.SPIN_HANDLING: [
            DrillTemplate(
                category=DrillCategory.SPIN_HANDLING,
                name="Spin Bowling Masterclass",
                description="Face 40 deliveries of off-spin and leg-spin",
                duration_minutes=25,
                reps_or_count=40,
                focus_area="Reading spin, footwork to spin",
                difficulty=8,
            ),
            DrillTemplate(
                category=DrillCategory.SPIN_HANDLING,
                name="Line and Length vs Spin",
                description="Practice defending good length spin with precision footwork",
                duration_minutes=20,
                reps_or_count=30,
                focus_area="Defending to spin bowlers",
                difficulty=7,
            ),
        ],
        DrillCategory.DOT_BALL: [
            DrillTemplate(
                category=DrillCategory.DOT_BALL,
                name="50 Dot Ball Challenge",
                description="Score ZERO runs in 50 consecutive deliveries",
                duration_minutes=25,
                reps_or_count=50,
                focus_area="Pressure handling, patience",
                difficulty=9,
            ),
            DrillTemplate(
                category=DrillCategory.DOT_BALL,
                name="Maiden Over Defense",
                description="Successfully defend 6 consecutive maiden overs",
                duration_minutes=30,
                reps_or_count=36,
                focus_area="Defensive technique vs dot balls",
                difficulty=8,
            ),
        ],
        DrillCategory.AGGRESSIVE: [
            DrillTemplate(
                category=DrillCategory.AGGRESSIVE,
                name="Aggressive Stroke Play",
                description="Score 40+ runs in 20 deliveries (SR 200+)",
                duration_minutes=15,
                reps_or_count=20,
                focus_area="Aggressive batting, shot execution",
                difficulty=8,
            ),
            DrillTemplate(
                category=DrillCategory.AGGRESSIVE,
                name="Power Play Practice",
                description="Score 50+ runs in 6 overs facing varied bowling",
                duration_minutes=20,
                reps_or_count=36,
                focus_area="Power play acceleration",
                difficulty=7,
            ),
        ],
        DrillCategory.BOUNDARY_HITTING: [
            DrillTemplate(
                category=DrillCategory.BOUNDARY_HITTING,
                name="Six-Hitting Challenge",
                description="Hit 20 sixes in 30 deliveries",
                duration_minutes=20,
                reps_or_count=30,
                focus_area="Boundary hitting under pressure",
                difficulty=9,
            ),
            DrillTemplate(
                category=DrillCategory.BOUNDARY_HITTING,
                name="Yorker Handling Offense",
                description="Score 15+ runs against 15 yorker deliveries",
                duration_minutes=15,
                reps_or_count=15,
                focus_area="Scoring off yorkers (death bowling)",
                difficulty=9,
            ),
        ],
        DrillCategory.WICKET_PROTECTION: [
            DrillTemplate(
                category=DrillCategory.WICKET_PROTECTION,
                name="Wicket Preservation",
                description="Bat through 60 deliveries with mandatory defense",
                duration_minutes=30,
                reps_or_count=60,
                focus_area="Wicket preservation, shot selection",
                difficulty=8,
            ),
        ],
    }
    
    # Weakness-to-drill mapping
    WEAKNESS_DRILL_MAPPING = {
        "pace_weakness": (DrillCategory.PACE_HANDLING, DrillSeverity.HIGH),
        "spin_weakness": (DrillCategory.SPIN_HANDLING, DrillSeverity.HIGH),
        "dot_ball_weakness": (DrillCategory.DOT_BALL, DrillSeverity.MEDIUM),
        "yorker_weakness": (DrillCategory.BOUNDARY_HITTING, DrillSeverity.HIGH),
        "aggressive_weakness": (DrillCategory.AGGRESSIVE, DrillSeverity.MEDIUM),
        "boundary_weakness": (DrillCategory.BOUNDARY_HITTING, DrillSeverity.MEDIUM),
    }
    
    @staticmethod
    def generate_drills_for_player(
        player_id: str,
        player_name: str,
        player_profile: dict,
        recent_dismissals: list[dict] = None,
    ) -> TrainingDrillPlan:
        """
        Generate personalized training drill plan for a player.
        
        Args:
            player_id: Player identifier
            player_name: Player name
            player_profile: Player stats dict with weakness scores
            recent_dismissals: Recent dismissal patterns
        
        Returns:
            TrainingDrillPlan with recommended drills
        """
        recent_dismissals = recent_dismissals or []
        drills: list[TrainingDrill] = []
        high_count = 0
        medium_count = 0
        low_count = 0
        total_hours = 0.0
        focus_areas = set()
        
        # Extract weakness scores from player profile
        weaknesses = {
            "pace_weakness": player_profile.get("pace_weakness", 0),
            "spin_weakness": player_profile.get("spin_weakness", 0),
            "dot_ball_weakness": player_profile.get("dot_ball_weakness", 0),
            "yorker_weakness": player_profile.get("yorker_weakness", 0),
        }
        
        # Generate drills based on weaknesses
        for weakness_name, weakness_score in weaknesses.items():
            if weakness_score >= 50:  # Significant weakness threshold
                category, severity = TrainingDrillGenerator.WEAKNESS_DRILL_MAPPING.get(
                    weakness_name, (DrillCategory.ENDURANCE, DrillSeverity.LOW)
                )
                
                # Get templates for this category
                templates = TrainingDrillGenerator.DRILL_TEMPLATES.get(category, [])
                if templates:
                    template = templates[0]  # Use first template for category
                    
                    drill = TrainingDrill(
                        drill_id=f"{player_id}_{weakness_name}",
                        player_id=player_id,
                        category=category,
                        name=template.name,
                        description=template.description,
                        reason=f"Address identified weakness: {weakness_name.replace('_', ' ')}",
                        severity=severity,
                        reps_or_count=template.reps_or_count,
                        duration_minutes=template.duration_minutes,
                        focus_area=template.focus_area,
                        difficulty=template.difficulty,
                        recommended_frequency="daily" if severity == DrillSeverity.HIGH else "3x/week",
                        expected_improvement=f"Expected 15-20% improvement in {weakness_name} handling",
                        weakness_score=weakness_score,
                        confidence=min(1.0, weakness_score / 100),
                    )
                    
                    drills.append(drill)
                    focus_areas.add(template.focus_area)
                    total_hours += template.duration_minutes / 60
                    
                    if severity == DrillSeverity.HIGH:
                        high_count += 1
                    elif severity == DrillSeverity.MEDIUM:
                        medium_count += 1
                    else:
                        low_count += 1
        
        # Check dismissal patterns for additional drills
        dismissal_patterns = TrainingDrillGenerator._analyze_dismissal_patterns(recent_dismissals)
        for pattern, count in dismissal_patterns.items():
            if count >= 2:  # Pattern appears at least twice
                if pattern == "aggressive_dismissal":
                    category = DrillCategory.WICKET_PROTECTION
                    severity = DrillSeverity.MEDIUM
                elif pattern == "dot_pressure_release":
                    category = DrillCategory.DOT_BALL
                    severity = DrillSeverity.MEDIUM
                else:
                    continue
                
                templates = TrainingDrillGenerator.DRILL_TEMPLATES.get(category, [])
                if templates and len(drills) < 6:  # Max 6 drills per plan
                    template = templates[0]
                    
                    drill = TrainingDrill(
                        drill_id=f"{player_id}_pattern_{pattern}",
                        player_id=player_id,
                        category=category,
                        name=template.name,
                        description=template.description,
                        reason=f"Pattern detected: {pattern.replace('_', ' ')} in recent dismissals",
                        severity=severity,
                        reps_or_count=template.reps_or_count,
                        duration_minutes=template.duration_minutes,
                        focus_area=template.focus_area,
                        difficulty=template.difficulty,
                        recommended_frequency="3x/week",
                        expected_improvement=f"Reduce {pattern} dismissals",
                        weakness_score=None,
                        confidence=0.7,
                    )
                    
                    drills.append(drill)
                    focus_areas.add(template.focus_area)
                    total_hours += template.duration_minutes / 60
                    medium_count += 1
        
        # Sort by severity (HIGH first)
        severity_order = {DrillSeverity.HIGH: 0, DrillSeverity.MEDIUM: 1, DrillSeverity.LOW: 2}
        drills.sort(key=lambda d: severity_order.get(d.severity, 3))
        
        return TrainingDrillPlan(
            player_id=player_id,
            player_name=player_name,
            drills=drills[:6],  # Cap at 6 drills
            high_priority_count=high_count,
            medium_priority_count=medium_count,
            low_priority_count=low_count,
            total_weekly_hours=round(total_hours * 5, 1),  # Assume 5 days/week
            focus_areas=sorted(list(focus_areas)),
        )
    
    @staticmethod
    def _analyze_dismissal_patterns(dismissals: list[dict]) -> dict[str, int]:
        """
        Analyze dismissal patterns to identify recurring scenarios.
        
        Args:
            dismissals: List of recent dismissal records
        
        Returns:
            Dict mapping pattern names to occurrence counts
        """
        patterns = {}
        
        for dismissal in dismissals[-5:]:  # Check last 5 dismissals
            dismissal_type = dismissal.get("dismissal_type", "unknown")
            context = dismissal.get("context", {})
            
            # Detect patterns
            if dismissal_type == "bowled" and context.get("dot_balls_before", 0) >= 3:
                patterns["dot_pressure_release"] = patterns.get("dot_pressure_release", 0) + 1
            
            if dismissal_type == "caught" and context.get("aggressive_attempt", False):
                patterns["aggressive_dismissal"] = patterns.get("aggressive_dismissal", 0) + 1
            
            if dismissal_type == "lbw" and context.get("delivery_type") in ["yorker", "full"]:
                patterns["yorker_dismissal"] = patterns.get("yorker_dismissal", 0) + 1
        
        return patterns
    
    @staticmethod
    def get_drill_progress(
        drill_id: str,
        completed_sessions: list[dict],
    ) -> dict:
        """
        Calculate drill progress and improvement metrics.
        
        Args:
            drill_id: The drill being tracked
            completed_sessions: List of completed drill sessions
        
        Returns:
            Progress dict with completion rate and improvement
        """
        if not completed_sessions:
            return {
                "completion_rate": 0.0,
                "sessions_completed": 0,
                "improvement_score": 0.0,
                "status": "not_started",
            }
        
        total_sessions = len(completed_sessions)
        successful_sessions = sum(1 for s in completed_sessions if s.get("success", False))
        completion_rate = successful_sessions / total_sessions if total_sessions > 0 else 0
        
        # Calculate improvement from first to last session
        if total_sessions >= 2:
            first_session_score = completed_sessions[0].get("performance_score", 0)
            last_session_score = completed_sessions[-1].get("performance_score", 0)
            improvement = max(0, last_session_score - first_session_score)
        else:
            improvement = 0
        
        status = "completed" if completion_rate >= 0.8 else "in_progress" if total_sessions > 0 else "not_started"
        
        return {
            "completion_rate": round(completion_rate, 2),
            "sessions_completed": successful_sessions,
            "total_sessions": total_sessions,
            "improvement_score": round(improvement, 1),
            "status": status,
            "next_session_recommended": status == "in_progress",
        }
