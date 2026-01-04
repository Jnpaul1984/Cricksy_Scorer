"""
AI Corrective Guidance Service

Rule-based (non-generative) service for providing corrective checkpoints
and drill suggestions based on coach notes and player feedback.
"""

from __future__ import annotations

from typing import TypedDict, cast


class Checkpoint(TypedDict):
    """A single corrective checkpoint."""

    title: str
    description: str
    priority: str  # "high", "medium", "low"


class Drill(TypedDict):
    """A practice drill recommendation."""

    name: str
    description: str
    duration_minutes: int
    equipment: list[str]


class CorrectiveGuidance(TypedDict):
    """Complete corrective guidance response."""

    checkpoints: list[Checkpoint]
    drills: list[Drill]
    reference_media: list[str]


# Rule-based knowledge base for cricket coaching
BATTING_CHECKPOINTS = {
    "footwork": [
        {
            "title": "Front Foot Positioning",
            "description": "Ensure front foot moves towards the line of the ball, not across it",
            "priority": "high",
        },
        {
            "title": "Back Foot Alignment",
            "description": "Back foot should be parallel to crease when playing back foot shots",
            "priority": "high",
        },
        {
            "title": "Weight Transfer",
            "description": "Transfer weight smoothly from back to front foot during drive",
            "priority": "medium",
        },
    ],
    "timing": [
        {
            "title": "Head Position",
            "description": "Keep head still and eyes level at point of contact",
            "priority": "high",
        },
        {
            "title": "Bat Speed",
            "description": "Accelerate bat through the ball, don't decelerate at contact",
            "priority": "medium",
        },
    ],
    "technique": [
        {
            "title": "Grip Pressure",
            "description": "Maintain relaxed grip, tighten only at point of impact",
            "priority": "medium",
        },
        {
            "title": "Elbow Position",
            "description": "Keep front elbow high and pointing towards bowler",
            "priority": "high",
        },
    ],
}

BOWLING_CHECKPOINTS = {
    "run_up": [
        {
            "title": "Consistent Rhythm",
            "description": "Maintain same pace and stride length throughout run-up",
            "priority": "high",
        },
        {
            "title": "Shoulder Alignment",
            "description": "Shoulders should be aligned towards target at delivery stride",
            "priority": "high",
        },
    ],
    "release": [
        {
            "title": "Wrist Position",
            "description": "Keep wrist behind the ball for pace, side-on for spin",
            "priority": "high",
        },
        {
            "title": "Follow Through",
            "description": "Complete follow through towards target",
            "priority": "medium",
        },
    ],
}

FIELDING_CHECKPOINTS = {
    "catching": [
        {
            "title": "Soft Hands",
            "description": "Give with the ball on impact to absorb force",
            "priority": "high",
        },
        {
            "title": "Watch the Ball",
            "description": "Keep eyes on ball all the way into hands",
            "priority": "high",
        },
    ],
    "throwing": [
        {
            "title": "Sideways Stance",
            "description": "Turn sideways to target before release",
            "priority": "high",
        },
        {
            "title": "Over the Top",
            "description": "Release from high point directly over shoulder",
            "priority": "medium",
        },
    ],
}

WICKETKEEPING_CHECKPOINTS = {
    "stance": [
        {
            "title": "Low Centre of Gravity",
            "description": "Stay low with weight on balls of feet",
            "priority": "high",
        },
        {
            "title": "Glove Position",
            "description": "Gloves together at ground level behind stumps",
            "priority": "high",
        },
    ],
    "stumping": [
        {
            "title": "Anticipation",
            "description": "Read batsman's movement early",
            "priority": "high",
        },
        {
            "title": "Ball Collection",
            "description": "Collect ball in front of stumps, not behind",
            "priority": "medium",
        },
    ],
}

BATTING_DRILLS = {
    "footwork": [
        {
            "name": "Shadow Batting",
            "description": "Practice footwork movements without ball, focusing on balance and positioning",
            "duration_minutes": 10,
            "equipment": ["bat"],
        },
        {
            "name": "Cone Drills",
            "description": "Place cones as targets, practice moving feet to different lines",
            "duration_minutes": 15,
            "equipment": ["bat", "cones", "tennis_ball"],
        },
    ],
    "timing": [
        {
            "name": "Drop Feed Drives",
            "description": "Coach drops ball from standing position, practice timing through drives",
            "duration_minutes": 15,
            "equipment": ["bat", "tennis_balls"],
        },
    ],
    "technique": [
        {
            "name": "Mirror Work",
            "description": "Practice shots in front of mirror to check technique",
            "duration_minutes": 10,
            "equipment": ["bat", "mirror"],
        },
    ],
}

BOWLING_DRILLS = {
    "run_up": [
        {
            "name": "Run-Up Markers",
            "description": "Mark each stride, practice hitting same markers consistently",
            "duration_minutes": 15,
            "equipment": ["markers"],
        },
    ],
    "release": [
        {
            "name": "Target Practice",
            "description": "Bowl at specific target areas marked on pitch",
            "duration_minutes": 20,
            "equipment": ["balls", "target_markers"],
        },
    ],
}

FIELDING_DRILLS = {
    "catching": [
        {
            "name": "Reaction Catches",
            "description": "Partner throws from close range, practice quick reactions",
            "duration_minutes": 10,
            "equipment": ["tennis_balls"],
        },
    ],
    "throwing": [
        {
            "name": "Target Throws",
            "description": "Throw at stumps from various distances and angles",
            "duration_minutes": 15,
            "equipment": ["balls", "stumps"],
        },
    ],
}

WICKETKEEPING_DRILLS = {
    "stance": [
        {
            "name": "Squat Holds",
            "description": "Practice maintaining low stance for extended periods",
            "duration_minutes": 5,
            "equipment": ["gloves"],
        },
    ],
    "stumping": [
        {
            "name": "Stumping Practice",
            "description": "Bowler delivers, keeper practices quick stumping action",
            "duration_minutes": 20,
            "equipment": ["balls", "stumps", "gloves"],
        },
    ],
}


def get_corrective_guidance(
    role: str,
    skill_focus: str,
    note_text: str | None = None,
) -> CorrectiveGuidance:
    """
    Generate corrective guidance based on role and skill focus.

    Args:
        role: Player role ("batting", "bowling", "fielding", "wicketkeeping")
        skill_focus: Specific skill area (e.g., "footwork", "timing", "catching")
        note_text: Optional coach note text for context

    Returns:
        CorrectiveGuidance with checkpoints, drills, and references
    """
    checkpoints: list[Checkpoint] = []
    drills: list[Drill] = []
    reference_media: list[str] = []

    # Select knowledge base by role
    if role == "batting":
        checkpoint_db = BATTING_CHECKPOINTS
        drill_db = BATTING_DRILLS
    elif role == "bowling":
        checkpoint_db = BOWLING_CHECKPOINTS
        drill_db = BOWLING_DRILLS
    elif role == "fielding":
        checkpoint_db = FIELDING_CHECKPOINTS
        drill_db = FIELDING_DRILLS
    elif role == "wicketkeeping":
        checkpoint_db = WICKETKEEPING_CHECKPOINTS
        drill_db = WICKETKEEPING_DRILLS
    else:
        # Fallback: return basic guidance
        checkpoints = [
            {
                "title": "Practice Fundamentals",
                "description": "Focus on basic technique and consistency",
                "priority": "high",
            }
        ]
        drills = [
            {
                "name": "Basic Skills Practice",
                "description": "Work on fundamental skills for your role",
                "duration_minutes": 30,
                "equipment": ["cricket_ball", "bat"],
            }
        ]
        return {
            "checkpoints": checkpoints,
            "drills": drills,
            "reference_media": [],
        }

    # Get checkpoints for skill focus
    if skill_focus in checkpoint_db:
        checkpoints = cast(list[Checkpoint], list(checkpoint_db[skill_focus]))
    else:
        # If skill_focus not found, provide all checkpoints for role
        for skill_checkpoints in checkpoint_db.values():
            checkpoints.extend(
                cast(list[Checkpoint], list(skill_checkpoints[:2]))
            )  # Top 2 from each category

    # Get drills for skill focus
    if skill_focus in drill_db:
        drills = cast(list[Drill], list(drill_db[skill_focus]))
    else:
        # Provide sample drills from first category
        first_category = next(iter(drill_db.values())) if drill_db else []
        drills = cast(list[Drill], list(first_category[:2])) if first_category else []

    # Add reference media (placeholder URLs - would link to actual coaching videos)
    reference_media = [
        f"https://coaching.cricksy.com/{role}/{skill_focus}/basics",
        f"https://coaching.cricksy.com/{role}/{skill_focus}/advanced",
    ]

    return {
        "checkpoints": checkpoints[:5],  # Limit to 5 checkpoints
        "drills": drills[:3],  # Limit to 3 drills
        "reference_media": reference_media,
    }
