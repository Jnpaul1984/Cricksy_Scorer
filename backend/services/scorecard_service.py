"""
Scorecard Service - Handles Player, BattingScorecard, BowlingScorecard, and Delivery operations.

This service implements the dual-write pattern:
1. Calls scoring_service.score_one() to apply cricket rules
2. Stores results in both Game JSON (existing) and normalized tables (new)
3. Emits Socket.IO updates for real-time sync
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.domain.constants import CREDIT_BOWLER
from backend.services import scoring_service
from backend.services.live_bus import emit_state_update
from backend.sql_app.models import (
    BattingScorecard,
    BowlingScorecard,
    Delivery,
    Game,
    Player,
)


class PlayerService:
    """Handles Player CRUD operations."""

    @staticmethod
    async def create_player(
        db: AsyncSession,
        name: str,
        jersey_number: int | None = None,
        role: str | None = None,
    ) -> Player:
        """Create a new player."""
        player = Player(
            name=name,
            jersey_number=jersey_number,
            role=role,
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(player)
        await db.commit()
        await db.refresh(player)
        return player

    @staticmethod
    async def get_player(db: AsyncSession, player_id: int) -> Player | None:
        """Get a player by ID."""
        result = await db.execute(select(Player).where(Player.id == player_id))
        return result.scalars().first()

    @staticmethod
    async def get_players(
        db: AsyncSession,
        skip: int = 0,
        limit: int = 100,
    ) -> list[Player]:
        """List players with pagination."""
        result = await db.execute(
            select(Player).offset(skip).limit(limit),
        )
        return result.scalars().all()

    @staticmethod
    async def get_or_create_player(db: AsyncSession, name: str) -> Player:
        """Get player by name or create if doesn't exist."""
        result = await db.execute(select(Player).where(Player.name == name))
        player = result.scalars().first()
        if not player:
            player = await PlayerService.create_player(db, name=name)
        return player


class DeliveryService:
    """Handles delivery recording with dual-write pattern."""

    @staticmethod
    async def record_delivery(
        db: AsyncSession,
        game_id: int,
        batter_id: int,
        bowler_id: int,
        non_striker_id: int,
        runs: int,
        extra_type: str | None = None,
        is_wicket: bool = False,
        dismissal_type: str | None = None,
        dismissed_player_id: int | None = None,
        fielder_id: int | None = None,
    ) -> Delivery:
        """
        Record a delivery with dual-write pattern.

        1. Load game and players
        2. Call scoring_service.score_one() to mutate game state
        3. Create Delivery record in DB
        4. Update BattingScorecard in DB
        5. Update BowlingScorecard in DB
        6. Update Game object
        7. Emit Socket.IO event
        8. Commit atomically
        """
        # 1. Load game and validate
        game = await db.get(Game, game_id)
        if not game:
            msg = f"Game {game_id} not found"
            raise ValueError(msg)

        # 2. Get player objects
        batter = await db.get(Player, batter_id)
        bowler = await db.get(Player, bowler_id)
        non_striker = await db.get(Player, non_striker_id)

        if not all([batter, bowler, non_striker]):
            msg = "One or more players not found"
            raise ValueError(msg)

        # 3. Call scoring_service.score_one() - mutates game object
        score_result = scoring_service.score_one(
            g=game,
            striker_id=str(batter_id),
            non_striker_id=str(non_striker_id),
            bowler_id=str(bowler_id),
            runs_scored=runs,
            extra=extra_type,
            is_wicket=is_wicket,
            dismissal_type=dismissal_type,
            dismissed_player_id=str(dismissed_player_id) if dismissed_player_id else None,
        )

        # 4. Create Delivery record (DUAL-WRITE)
        delivery = Delivery(
            game_id=game_id,
            inning_number=getattr(game, "current_inning", 1),
            over_number=score_result["over_number"],
            ball_number=score_result["ball_number"],
            bowler_id=bowler_id,
            batter_id=batter_id,
            non_striker_id=non_striker_id,
            runs=score_result["runs_scored"],
            runs_off_bat=score_result["runs_off_bat"],
            extra_type=score_result["extra_type"],
            extra_runs=score_result["extra_runs"],
            is_wicket=score_result["is_wicket"],
            wicket_type=score_result["dismissal_type"],
            wicket_fielder_id=fielder_id,
            is_legal=not score_result["is_extra"],
            created_at=datetime.utcnow(),
            updated_at=datetime.utcnow(),
        )
        db.add(delivery)

        # 5. Update or create BattingScorecard (DUAL-WRITE)
        result = await db.execute(
            select(BattingScorecard).where(
                (BattingScorecard.game_id == game_id) & (BattingScorecard.player_id == batter_id),
            ),
        )
        batting_card = result.scalars().first()

        if batting_card:
            # Update existing
            batting_card.runs += score_result["runs_scored"]
            if not score_result["is_extra"]:
                batting_card.balls_faced += 1
            if score_result["runs_off_bat"] >= 4:
                if score_result["runs_off_bat"] == 4:
                    batting_card.fours += 1
                elif score_result["runs_off_bat"] == 6:
                    batting_card.sixes += 1
            if score_result["is_wicket"]:
                batting_card.is_out = True
                batting_card.dismissal_type = score_result["dismissal_type"]
                if dismissed_player_id == batter_id:
                    batting_card.bowler_id = bowler_id
                if fielder_id:
                    batting_card.fielder_id = fielder_id
            batting_card.updated_at = datetime.utcnow()
        else:
            # Create new
            batting_card = BattingScorecard(
                game_id=game_id,
                player_id=batter_id,
                runs=score_result["runs_scored"],
                balls_faced=0 if score_result["is_extra"] else 1,
                fours=1 if score_result["runs_off_bat"] == 4 else 0,
                sixes=1 if score_result["runs_off_bat"] == 6 else 0,
                is_out=score_result["is_wicket"],
                dismissal_type=score_result["dismissal_type"]
                if score_result["is_wicket"]
                else None,
                bowler_id=bowler_id if score_result["is_wicket"] else None,
                fielder_id=fielder_id if score_result["is_wicket"] else None,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(batting_card)

        # 6. Update or create BowlingScorecard (DUAL-WRITE)
        result = await db.execute(
            select(BowlingScorecard).where(
                (BowlingScorecard.game_id == game_id) & (BowlingScorecard.player_id == bowler_id),
            ),
        )
        bowling_card = result.scalars().first()

        if bowling_card:
            # Update existing
            bowling_card.runs_conceded += score_result["extra_runs"]
            bowling_card.overs_bowled = getattr(game, "overs_completed", 0) + (
                getattr(game, "balls_this_over", 0) / 6
            )
            if score_result["is_extra"]:
                if score_result["extra_type"] == "wd":
                    bowling_card.wides += 1
                elif score_result["extra_type"] == "nb":
                    bowling_card.no_balls += 1
            if score_result["is_wicket"] and score_result["dismissal_type"] in CREDIT_BOWLER:
                bowling_card.wickets_taken += 1
            bowling_card.updated_at = datetime.utcnow()
        else:
            # Create new
            bowling_card = BowlingScorecard(
                game_id=game_id,
                player_id=bowler_id,
                overs_bowled=0.0,
                balls_bowled=0,
                runs_conceded=score_result["extra_runs"],
                wickets_taken=(
                    1
                    if (
                        score_result["is_wicket"]
                        and score_result["dismissal_type"] in CREDIT_BOWLER
                    )
                    else 0
                ),
                wides=1 if score_result["extra_type"] == "wd" else 0,
                no_balls=1 if score_result["extra_type"] == "nb" else 0,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(bowling_card)

        # 7. Update Game object (keeps old system working)
        game.updated_at = datetime.utcnow()

        # 8. Commit all changes atomically
        await db.commit()

        # Refresh to get all IDs
        await db.refresh(delivery)

        # 9. Emit Socket.IO event (broadcast to all clients)
        try:
            await emit_state_update(game_id, game)
        except Exception as e:
            # Log but don't fail if Socket.IO broadcast fails
            print(f"Warning: Socket.IO emit failed: {e}")

        return delivery


class ScorecardService:
    """Handles scorecard queries and manual entry."""

    @staticmethod
    async def get_batting_scorecards(
        db: AsyncSession,
        game_id: int,
        inning_number: int | None = None,
    ) -> list[BattingScorecard]:
        """Get batting scorecards for a game."""
        query = select(BattingScorecard).where(BattingScorecard.game_id == game_id)
        if inning_number is not None:
            query = query.where(BattingScorecard.inning_number == inning_number)
        query = query.order_by(BattingScorecard.created_at.asc())
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_bowling_scorecards(
        db: AsyncSession,
        game_id: int,
        inning_number: int | None = None,
    ) -> list[BowlingScorecard]:
        """Get bowling scorecards for a game."""
        query = select(BowlingScorecard).where(BowlingScorecard.game_id == game_id)
        if inning_number is not None:
            query = query.where(BowlingScorecard.inning_number == inning_number)
        query = query.order_by(BowlingScorecard.created_at.asc())
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_deliveries(
        db: AsyncSession,
        game_id: int,
        inning_number: int | None = None,
        over_number: int | None = None,
    ) -> list[Delivery]:
        """Get deliveries for a game with optional filtering."""
        query = select(Delivery).where(Delivery.game_id == game_id)
        if inning_number is not None:
            query = query.where(Delivery.inning_number == inning_number)
        if over_number is not None:
            query = query.where(Delivery.over_number == over_number)
        query = query.order_by(Delivery.inning_number, Delivery.over_number, Delivery.ball_number)
        result = await db.execute(query)
        return result.scalars().all()

    @staticmethod
    async def get_batting_summary(db: AsyncSession, game_id: int) -> dict[str, Any]:
        """Get aggregate batting statistics for a game."""
        batting_cards = await ScorecardService.get_batting_scorecards(db, game_id)
        return {
            "total_batters": len(batting_cards),
            "total_runs": sum(c.runs for c in batting_cards),
            "total_balls": sum(c.balls_faced for c in batting_cards),
            "wickets": sum(1 for c in batting_cards if c.is_out),
            "fours": sum(c.fours for c in batting_cards),
            "sixes": sum(c.sixes for c in batting_cards),
        }

    @staticmethod
    async def get_bowling_summary(db: AsyncSession, game_id: int) -> dict[str, Any]:
        """Get aggregate bowling statistics for a game."""
        bowling_cards = await ScorecardService.get_bowling_scorecards(db, game_id)
        return {
            "total_bowlers": len(bowling_cards),
            "total_runs_conceded": sum(c.runs_conceded for c in bowling_cards),
            "total_wickets": sum(c.wickets_taken for c in bowling_cards),
            "total_wides": sum(c.wides for c in bowling_cards),
            "total_no_balls": sum(c.no_balls for c in bowling_cards),
        }

    @staticmethod
    async def create_batting_scorecard_manual(
        db: AsyncSession,
        game_id: int,
        player_id: int,
        runs: int,
        balls_faced: int,
        fours: int = 0,
        sixes: int = 0,
        is_out: bool = False,
        dismissal_type: str | None = None,
    ) -> BattingScorecard:
        """
        Manually create or update a batting scorecard.
        Use this for manual data entry (e.g., offline scoring).
        """
        # Check if exists
        result = await db.execute(
            select(BattingScorecard).where(
                (BattingScorecard.game_id == game_id) & (BattingScorecard.player_id == player_id),
            ),
        )
        batting_card = result.scalars().first()

        if batting_card:
            # Update
            batting_card.runs = runs
            batting_card.balls_faced = balls_faced
            batting_card.fours = fours
            batting_card.sixes = sixes
            batting_card.is_out = is_out
            batting_card.dismissal_type = dismissal_type
            batting_card.updated_at = datetime.utcnow()
        else:
            # Create
            batting_card = BattingScorecard(
                game_id=game_id,
                player_id=player_id,
                runs=runs,
                balls_faced=balls_faced,
                fours=fours,
                sixes=sixes,
                is_out=is_out,
                dismissal_type=dismissal_type,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(batting_card)

        await db.commit()
        await db.refresh(batting_card)
        return batting_card

    @staticmethod
    async def create_bowling_scorecard_manual(
        db: AsyncSession,
        game_id: int,
        player_id: int,
        overs_bowled: float,
        runs_conceded: int,
        wickets_taken: int = 0,
        wides: int = 0,
        no_balls: int = 0,
    ) -> BowlingScorecard:
        """
        Manually create or update a bowling scorecard.
        Use this for manual data entry (e.g., offline scoring).
        """
        # Check if exists
        result = await db.execute(
            select(BowlingScorecard).where(
                (BowlingScorecard.game_id == game_id) & (BowlingScorecard.player_id == player_id),
            ),
        )
        bowling_card = result.scalars().first()

        if bowling_card:
            # Update
            bowling_card.overs_bowled = overs_bowled
            bowling_card.runs_conceded = runs_conceded
            bowling_card.wickets_taken = wickets_taken
            bowling_card.wides = wides
            bowling_card.no_balls = no_balls
            bowling_card.updated_at = datetime.utcnow()
        else:
            # Create
            bowling_card = BowlingScorecard(
                game_id=game_id,
                player_id=player_id,
                overs_bowled=overs_bowled,
                runs_conceded=runs_conceded,
                wickets_taken=wickets_taken,
                wides=wides,
                no_balls=no_balls,
                created_at=datetime.utcnow(),
                updated_at=datetime.utcnow(),
            )
            db.add(bowling_card)

        await db.commit()
        await db.refresh(bowling_card)
        return bowling_card
