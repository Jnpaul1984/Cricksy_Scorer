"""
Player Analytics Routes

Exposes player career analysis and AI-powered insights via REST API.
Endpoints for player summaries, career stats, and performance analysis.
"""

from fastapi import APIRouter, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from backend.sql_app.models import Player, BattingScorecard, BowlingScorecard, Game
from backend.services.player_career_analyzer import get_player_career_summary

router = APIRouter(prefix="/analytics/players", tags=["player_analytics"])


@router.get("/players/{player_id}/career-summary")
async def get_player_career_summary_endpoint(
    player_id: str,
    db: AsyncSession,
) -> dict:
    """
    Get AI-powered career summary for a player.
    
    Analyzes all historical performance data to generate:
    - Career statistics (batting/bowling)
    - Specialization analysis
    - Recent form trends
    - Best performances
    - Career highlights
    
    Returns:
        {
            "player_id": str,
            "player_name": str,
            "career_summary": str,  # Human-readable summary
            "batting_stats": {
                "matches": int,
                "total_runs": int,
                "average": float,
                "consistency_score": float (0-100),
                "strike_rate": float,
                "boundary_percentage": float,
                ...
            },
            "bowling_stats": {
                "matches": int,
                "total_wickets": int,
                "economy_rate": float,
                ...
            },
            "specialization": str,  # Opener, Finisher, Bowler, All-rounder, Batter
            "specialization_confidence": float (0-1),
            "recent_form": {
                "trend": str,  # improving, declining, stable
                "recent_runs": int,
                "recent_average": float,
                ...
            },
            "best_performances": {
                "best_batting": {...},
                "best_bowling": {...},
            },
            "career_highlights": [str, ...]
        }
    """
    try:
        # Fetch player
        stmt = select(Player).where(Player.id == player_id)
        result = await db.execute(stmt)
        player = result.scalars().first()
        
        if not player:
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found")
        
        # Fetch all batting records for this player
        stmt = select(BattingScorecard).where(BattingScorecard.player_id == player_id)
        result = await db.execute(stmt)
        batting_records_db = result.scalars().all()
        
        # Convert to dict format
        batting_records = [
            {
                "runs": int(b.runs),
                "balls_faced": int(b.balls_faced),
                "fours": int(b.fours),
                "sixes": int(b.sixes),
                "is_out": bool(b.is_out),
                "how_out": b.how_out,
                "match_date": b.created_at.isoformat() if b.created_at else None,
            }
            for b in batting_records_db
        ]
        
        # Fetch all bowling records for this player
        stmt = select(BowlingScorecard).where(BowlingScorecard.player_id == player_id)
        result = await db.execute(stmt)
        bowling_records_db = result.scalars().all()
        
        # Convert to dict format
        bowling_records = [
            {
                "overs_bowled": float(b.overs),
                "maidens": int(b.maidens),
                "runs_conceded": int(b.runs),
                "wickets_taken": int(b.wickets),
                "match_date": b.created_at.isoformat() if b.created_at else None,
            }
            for b in bowling_records_db
        ]
        
        # Generate career summary
        summary = get_player_career_summary(
            player_id=str(player.id),
            player_name=player.name,
            batting_records=batting_records,
            bowling_records=bowling_records,
        )
        
        return summary
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch career summary: {str(e)}"
        )


@router.get("/players/{player_id}/year-stats")
async def get_player_yearly_stats(
    player_id: str,
    db: AsyncSession,
) -> dict:
    """
    Get player statistics broken down by year.
    
    Returns year-wise performance metrics for trend analysis.
    """
    try:
        # Fetch player
        stmt = select(Player).where(Player.id == player_id)
        result = await db.execute(stmt)
        player = result.scalars().first()
        
        if not player:
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found")
        
        # Group batting by year
        stmt = select(BattingScorecard).where(BattingScorecard.player_id == player_id)
        result = await db.execute(stmt)
        batting_records = result.scalars().all()
        
        year_stats = {}
        
        for record in batting_records:
            year = record.created_at.year if record.created_at else "Unknown"
            
            if year not in year_stats:
                year_stats[year] = {
                    "year": year,
                    "matches": 0,
                    "runs": 0,
                    "average": 0,
                    "strike_rate": 0,
                    "centuries": 0,
                    "fifties": 0,
                }
            
            year_stats[year]["matches"] += 1
            year_stats[year]["runs"] += int(record.runs)
            
            if int(record.runs) >= 100:
                year_stats[year]["centuries"] += 1
            elif int(record.runs) >= 50:
                year_stats[year]["fifties"] += 1
        
        # Calculate averages
        for year, stats in year_stats.items():
            if stats["matches"] > 0:
                stats["average"] = round(stats["runs"] / stats["matches"], 2)
        
        return {
            "player_id": str(player.id),
            "player_name": player.name,
            "yearly_breakdown": list(year_stats.values()),
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to fetch yearly stats: {str(e)}"
        )


@router.get("/players/{player_id}/comparison")
async def get_player_comparison(
    player_id: str,
    comparison_player_id: str,
    db: AsyncSession,
) -> dict:
    """
    Compare statistics between two players.
    
    Side-by-side comparison of career metrics, recent form, and specialization.
    """
    try:
        # Fetch both players
        stmt = select(Player).where(Player.id == player_id)
        result = await db.execute(stmt)
        player1 = result.scalars().first()
        
        stmt = select(Player).where(Player.id == comparison_player_id)
        result = await db.execute(stmt)
        player2 = result.scalars().first()
        
        if not player1:
            raise HTTPException(status_code=404, detail=f"Player {player_id} not found")
        if not player2:
            raise HTTPException(status_code=404, detail=f"Player {comparison_player_id} not found")
        
        # Get summaries for both
        stmt = select(BattingScorecard).where(BattingScorecard.player_id == player_id)
        result = await db.execute(stmt)
        batting1 = result.scalars().all()
        
        stmt = select(BattingScorecard).where(BattingScorecard.player_id == comparison_player_id)
        result = await db.execute(stmt)
        batting2 = result.scalars().all()
        
        stmt = select(BowlingScorecard).where(BowlingScorecard.player_id == player_id)
        result = await db.execute(stmt)
        bowling1 = result.scalars().all()
        
        stmt = select(BowlingScorecard).where(BowlingScorecard.player_id == comparison_player_id)
        result = await db.execute(stmt)
        bowling2 = result.scalars().all()
        
        # Convert and get summaries
        summary1 = get_player_career_summary(
            player_id=str(player1.id),
            player_name=player1.name,
            batting_records=[
                {
                    "runs": int(b.runs),
                    "balls_faced": int(b.balls_faced),
                    "fours": int(b.fours),
                    "sixes": int(b.sixes),
                    "is_out": bool(b.is_out),
                    "how_out": b.how_out,
                    "match_date": b.created_at.isoformat() if b.created_at else None,
                }
                for b in batting1
            ],
            bowling_records=[
                {
                    "overs_bowled": float(b.overs),
                    "maidens": int(b.maidens),
                    "runs_conceded": int(b.runs),
                    "wickets_taken": int(b.wickets),
                    "match_date": b.created_at.isoformat() if b.created_at else None,
                }
                for b in bowling1
            ],
        )
        
        summary2 = get_player_career_summary(
            player_id=str(player2.id),
            player_name=player2.name,
            batting_records=[
                {
                    "runs": int(b.runs),
                    "balls_faced": int(b.balls_faced),
                    "fours": int(b.fours),
                    "sixes": int(b.sixes),
                    "is_out": bool(b.is_out),
                    "how_out": b.how_out,
                    "match_date": b.created_at.isoformat() if b.created_at else None,
                }
                for b in batting2
            ],
            bowling_records=[
                {
                    "overs_bowled": float(b.overs),
                    "maidens": int(b.maidens),
                    "runs_conceded": int(b.runs),
                    "wickets_taken": int(b.wickets),
                    "match_date": b.created_at.isoformat() if b.created_at else None,
                }
                for b in bowling2
            ],
        )
        
        return {
            "player_1": summary1,
            "player_2": summary2,
        }
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to compare players: {str(e)}"
        )
