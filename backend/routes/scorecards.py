"""
Scorecard routes - Player, BattingScorecard, BowlingScorecard, and Delivery endpoints.

Implements dual-write pattern:
- All writes go through scorecard_service which updates both old Game JSON and new normalized tables
- Queries can use either source (for gradual migration)
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from backend.services.scorecard_service import (
    DeliveryService,
    PlayerService,
    ScorecardService,
)
from backend.sql_app.database import get_db
from backend.sql_app.schemas import (
    BattingScorecardCreate,
    BattingScorecard as BattingScorecardSchema,
    BowlingScorecard as BowlingScorecardSchema,
    BowlingScorecardCreate,
    Delivery as DeliverySchema,
    DeliveryCreate,
    Player as PlayerSchema,
    PlayerCreate,
)

router = APIRouter(prefix="/api", tags=["scorecards"])


# ============================================================================
# PLAYER ENDPOINTS
# ============================================================================


@router.post("/players", response_model=PlayerSchema)
async def create_player_endpoint(
    player: PlayerCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Create a new player."""
    return await PlayerService.create_player(
        db=db,
        name=player.name,
        jersey_number=player.jersey_number,
        role=player.role,
    )


@router.get("/players/{player_id}", response_model=PlayerSchema)
async def get_player_endpoint(
    player_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get a player by ID."""
    player = await PlayerService.get_player(db=db, player_id=player_id)
    if not player:
        raise HTTPException(status_code=404, detail="Player not found")
    return player


@router.get("/players", response_model=list[PlayerSchema])
async def list_players_endpoint(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """List players with pagination."""
    return await PlayerService.get_players(db=db, skip=skip, limit=limit)


# ============================================================================
# DELIVERY ENDPOINTS
# ============================================================================


@router.post("/games/{game_id}/deliveries", response_model=DeliverySchema)
async def record_delivery_endpoint(
    game_id: int,
    delivery: DeliveryCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Record a delivery in the scorecard.

    Implements dual-write pattern:
    - Calls scoring_service.score_one() to apply cricket rules
    - Stores in both Game JSON (existing) and Delivery table (new)
    - Updates BattingScorecard and BowlingScorecard
    - Emits Socket.IO event for real-time updates
    """
    return await DeliveryService.record_delivery(
        db=db,
        game_id=game_id,
        batter_id=delivery.batter_id,
        bowler_id=delivery.bowler_id,
        non_striker_id=delivery.non_striker_id,
        runs=delivery.runs,
        extra_type=delivery.extra_type,
        is_wicket=delivery.is_wicket,
        dismissal_type=delivery.dismissal_type,
        dismissed_player_id=delivery.dismissed_player_id,
        fielder_id=delivery.fielder_id,
    )


@router.get("/games/{game_id}/deliveries", response_model=list[DeliverySchema])
async def get_deliveries_endpoint(
    game_id: int,
    inning_number: int | None = Query(None),
    over_number: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get deliveries for a game with optional filtering."""
    return await ScorecardService.get_deliveries(
        db=db,
        game_id=game_id,
        inning_number=inning_number,
        over_number=over_number,
    )


# ============================================================================
# BATTING SCORECARD ENDPOINTS
# ============================================================================


@router.post(
    "/games/{game_id}/batting-scorecards",
    response_model=BattingScorecardSchema,
)
async def create_batting_scorecard_endpoint(
    game_id: int,
    scorecard: BattingScorecardCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Create or update a batting scorecard.

    Use for manual entry or adjustments. For live scoring, use /deliveries endpoint.
    """
    return await ScorecardService.create_batting_scorecard_manual(
        db=db,
        game_id=game_id,
        player_id=scorecard.player_id,
        runs=scorecard.runs,
        balls_faced=scorecard.balls_faced,
        fours=scorecard.fours,
        sixes=scorecard.sixes,
        is_out=scorecard.is_out,
        dismissal_type=scorecard.dismissal_type,
    )


@router.get(
    "/games/{game_id}/batting-scorecards",
    response_model=list[BattingScorecardSchema],
)
async def get_batting_scorecards_endpoint(
    game_id: int,
    inning_number: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get batting scorecards for a game."""
    return await ScorecardService.get_batting_scorecards(
        db=db,
        game_id=game_id,
        inning_number=inning_number,
    )


# ============================================================================
# BOWLING SCORECARD ENDPOINTS
# ============================================================================


@router.post(
    "/games/{game_id}/bowling-scorecards",
    response_model=BowlingScorecardSchema,
)
async def create_bowling_scorecard_endpoint(
    game_id: int,
    scorecard: BowlingScorecardCreate,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Create or update a bowling scorecard.

    Use for manual entry or adjustments. For live scoring, use /deliveries endpoint.
    """
    return await ScorecardService.create_bowling_scorecard_manual(
        db=db,
        game_id=game_id,
        player_id=scorecard.player_id,
        overs_bowled=scorecard.overs_bowled,
        runs_conceded=scorecard.runs_conceded,
        wickets_taken=scorecard.wickets_taken,
        wides=scorecard.wides,
        no_balls=scorecard.no_balls,
    )


@router.get(
    "/games/{game_id}/bowling-scorecards",
    response_model=list[BowlingScorecardSchema],
)
async def get_bowling_scorecards_endpoint(
    game_id: int,
    inning_number: int | None = Query(None),
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get bowling scorecards for a game."""
    return await ScorecardService.get_bowling_scorecards(
        db=db,
        game_id=game_id,
        inning_number=inning_number,
    )


# ============================================================================
# SUMMARY ENDPOINTS
# ============================================================================


@router.get("/games/{game_id}/batting-summary")
async def get_batting_summary_endpoint(
    game_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get aggregate batting statistics for a game."""
    return await ScorecardService.get_batting_summary(db=db, game_id=game_id)


@router.get("/games/{game_id}/bowling-summary")
async def get_bowling_summary_endpoint(
    game_id: int,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """Get aggregate bowling statistics for a game."""
    return await ScorecardService.get_bowling_summary(db=db, game_id=game_id)
