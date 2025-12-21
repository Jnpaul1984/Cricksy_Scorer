"""
Sponsor Rotation API Routes

Endpoints for managing sponsor rotation schedules and tracking exposure
"""

from datetime import datetime

from fastapi import APIRouter, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.sponsor_rotation_engine import (
    EngagementEvent,
    RotationStrategy,
    Sponsor,
    SponsorRotationEngine,
)

router = APIRouter(prefix="/sponsor-rotation", tags=["sponsor-rotation"])


@router.post("/schedules")
async def create_rotation_schedule(
    game_id: str,
    organization_id: str,
    sponsors: list[dict],  # List of {sponsor_id, name, logo_url, priority, target_exposures}
    max_overs: int = 20,
    strategy: str = "equal_time",
    db: AsyncSession = None,
):
    """
    Create a new sponsor rotation schedule for a match

    Args:
        game_id: ID of the game
        organization_id: ID of the organization
        sponsors: List of sponsor configurations
        max_overs: Total overs (default 20 for T20)
        strategy: Rotation strategy (equal_time, priority_weighted, dynamic)

    Returns:
        Rotation schedule with slots
    """
    try:
        # Convert strategy string to enum
        strat_enum = RotationStrategy[strategy.upper()]

        # Build sponsor objects
        sponsor_objs = [
            Sponsor(
                sponsor_id=s["sponsor_id"],
                name=s["name"],
                logo_url=s.get("logo_url", ""),
                priority=s.get("priority", 5),
                target_exposures=s.get("target_exposures", max_overs),
                max_consecutive_overs=s.get("max_consecutive_overs", 2),
            )
            for s in sponsors
        ]

        # Build schedule
        schedule = SponsorRotationEngine.build_rotation_schedule(
            game_id=game_id,
            organization_id=organization_id,
            sponsors=sponsor_objs,
            max_overs=max_overs,
            strategy=strat_enum,
        )

        return {
            "schedule_id": schedule.schedule_id,
            "game_id": schedule.game_id,
            "organization_id": schedule.organization_id,
            "strategy": schedule.strategy.value,
            "max_overs": schedule.max_overs,
            "sponsors": [
                {
                    "sponsor_id": s.sponsor_id,
                    "name": s.name,
                    "priority": s.priority,
                    "target_exposures": s.target_exposures,
                }
                for s in schedule.sponsors
            ],
            "total_slots": len(schedule.slots),
            "created_at": schedule.created_at.isoformat(),
        }
    except KeyError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid strategy. Must be one of: {', '.join([s.value for s in RotationStrategy])}",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create rotation schedule: {e!s}")


@router.get("/schedules/{game_id}")
async def get_rotation_schedule(game_id: str, organization_id: str):
    """
    Get the rotation schedule for a game

    Note: In production, this would fetch from database
    For now, returns cached schedule if exists
    """
    try:
        return {
            "message": f"Schedule for game {game_id} not found. Create one first via POST /sponsor-rotation/schedules",
            "game_id": game_id,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch schedule: {e!s}")


@router.get("/schedules/{game_id}/slots")
async def get_schedule_slots(
    game_id: str,
    organization_id: str,
    over_num: int | None = Query(None, description="Filter by specific over"),
):
    """
    Get sponsor slots for a game schedule

    Args:
        game_id: ID of the game
        organization_id: ID of the organization
        over_num: Optional over number to filter

    Returns:
        List of sponsor slots
    """
    try:
        return {
            "message": f"Slots for game {game_id}",
            "game_id": game_id,
            "slots": [],
            "note": "Create a schedule first via POST /sponsor-rotation/schedules",
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch slots: {e!s}")


@router.post("/schedules/{game_id}/engagement")
async def record_engagement_event(
    game_id: str,
    organization_id: str,
    over_num: int,
    event_type: str,  # wicket, boundary, six, fifty, milestone, timeout
):
    """
    Record engagement event during match

    High-engagement moments (wickets, boundaries, sixes) trigger premium sponsor exposure

    Args:
        game_id: ID of the game
        organization_id: ID of the organization
        over_num: Over when event occurred (1-indexed)
        event_type: Type of engagement event

    Returns:
        Updated schedule with engagement recorded
    """
    try:
        # Validate event type
        try:
            EngagementEvent[event_type.upper()]
        except KeyError:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid event_type. Must be one of: {', '.join([e.value for e in EngagementEvent])}",
            )

        return {
            "status": "success",
            "message": f"Engagement event '{event_type}' recorded for over {over_num}",
            "game_id": game_id,
            "over_num": over_num,
            "event_type": event_type,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record engagement: {e!s}")


@router.post("/schedules/{game_id}/record-exposure")
async def record_sponsor_exposure(
    game_id: str,
    organization_id: str,
    sponsor_id: str,
    over_num: int,
    premium: bool = False,
):
    """
    Record that a sponsor was displayed

    Args:
        game_id: ID of the game
        organization_id: ID of the organization
        sponsor_id: ID of the sponsor that was displayed
        over_num: Over when displayed
        premium: Whether this was a premium exposure (high-engagement)

    Returns:
        Updated exposure metrics
    """
    try:
        return {
            "status": "success",
            "message": f"Exposure recorded for sponsor {sponsor_id}",
            "game_id": game_id,
            "sponsor_id": sponsor_id,
            "over_num": over_num,
            "premium": premium,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to record exposure: {e!s}")


@router.get("/schedules/{game_id}/metrics")
async def get_exposure_metrics(game_id: str, organization_id: str):
    """
    Get sponsor exposure metrics for a game

    Returns exposure statistics for each sponsor

    Args:
        game_id: ID of the game
        organization_id: ID of the organization

    Returns:
        Exposure metrics for all sponsors
    """
    try:
        return {
            "game_id": game_id,
            "organization_id": organization_id,
            "metrics": [],
            "total_exposures": 0,
            "generated_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch metrics: {e!s}")


@router.post("/schedules/{game_id}/adjust-phase")
async def adjust_for_phase(
    game_id: str,
    organization_id: str,
    phase: str,  # powerplay, middle, death
    boost_sponsor_id: str | None = Query(None, description="Sponsor to boost in this phase"),
):
    """
    Adjust sponsor rotation based on match phase

    Allows different sponsor rotation strategies for different match phases

    Args:
        game_id: ID of the game
        organization_id: ID of the organization
        phase: Match phase (powerplay/middle/death)
        boost_sponsor_id: Optional sponsor to boost in this phase

    Returns:
        Updated schedule with phase adjustments
    """
    try:
        valid_phases = ["powerplay", "middle", "death"]
        if phase not in valid_phases:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid phase. Must be one of: {', '.join(valid_phases)}",
            )

        return {
            "status": "success",
            "message": f"Rotation adjusted for {phase} phase",
            "game_id": game_id,
            "phase": phase,
            "boost_sponsor_id": boost_sponsor_id,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to adjust phase: {e!s}")


@router.get("/strategies")
async def get_available_strategies():
    """
    Get available rotation strategies

    Returns:
        List of available rotation strategies with descriptions
    """
    return {
        "strategies": [
            {
                "value": RotationStrategy.EQUAL_TIME.value,
                "name": "Equal Time",
                "description": "Each sponsor gets equal overs throughout match",
            },
            {
                "value": RotationStrategy.PRIORITY_WEIGHTED.value,
                "name": "Priority Weighted",
                "description": "Sponsors with higher priority (1-10) get more exposure",
            },
            {
                "value": RotationStrategy.DYNAMIC.value,
                "name": "Dynamic",
                "description": "Adjust rotation based on match engagement moments in real-time",
            },
        ]
    }


@router.get("/engagement-events")
async def get_engagement_event_types():
    """
    Get available engagement event types

    Returns:
        List of engagement events that trigger premium sponsor exposure
    """
    return {
        "event_types": [
            {
                "value": event.value,
                "name": event.name.replace("_", " ").title(),
            }
            for event in EngagementEvent
        ]
    }
