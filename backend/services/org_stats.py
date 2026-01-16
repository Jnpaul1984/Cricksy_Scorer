"""
Organization Statistics Service

Calculates organization-level aggregates:
- Total teams and matches
- Season win rate
- Average run rate
- Phase-based net run rates vs par
"""

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from backend.sql_app import models


async def calculate_org_stats(db: AsyncSession, org_id: str) -> dict:
    """
    Calculate organization-wide statistics.
    
    Returns:
    {
        "total_teams": int,
        "total_matches": int,
        "season_win_rate": float,  # percentage
        "avg_run_rate": float,
        "powerplay_net_runs": int,
        "middle_net_runs": int,
        "death_net_runs": int,
        "death_over_economy": float,
    }
    """
    
    # Get all teams for this organization (org_id is the owner_user_id)
    stmt = select(models.Team).where(models.Team.owner_user_id == org_id)
    result = await db.execute(stmt)
    org_teams = result.scalars().all()
    
    team_ids = [str(t.id) for t in org_teams]
    total_teams = len(team_ids)
    
    if not team_ids:
        # No teams in organization
        return {
            "total_teams": 0,
            "total_matches": 0,
            "season_win_rate": 0.0,
            "avg_run_rate": 0.0,
            "powerplay_net_runs": 0,
            "middle_net_runs": 0,
            "death_net_runs": 0,
            "death_over_economy": 0.0,
        }
    
    # Get all games where org teams participated
    stmt = select(models.Game).where(
        (models.Game.team_a_id.in_(team_ids)) |
        (models.Game.team_b_id.in_(team_ids))
    )
    result = await db.execute(stmt)
    games = result.scalars().all()
    
    total_matches = len(games)
    wins = 0
    total_runs = 0
    total_deliveries = 0
    
    powerplay_runs = 0  # Overs 1-6
    powerplay_wickets = 0
    middle_runs = 0     # Overs 7-16
    middle_wickets = 0
    death_runs = 0      # Overs 17-20
    death_wickets = 0
    
    for game in games:
        # Count as win if org team is winner
        if game.result and isinstance(game.result, dict):
            winner_id = game.result.get("winner_team_id")
            if winner_id in team_ids:
                wins += 1
        
        # Aggregate runs and phase performance
        state = game.current_state or {}
        total_runs += state.get("total_runs", 0)
        
        # Get deliveries for phase analysis
        stmt = select(models.Delivery).where(
            models.Delivery.game_id == game.id
        )
        result = await db.execute(stmt)
        deliveries = result.scalars().all()
        
        for d in deliveries:
            total_deliveries += 1
            
            # Phase bucketing
            if 1 <= d.over_number <= 6:
                powerplay_runs += d.runs_scored or 0
                if d.is_wicket:
                    powerplay_wickets += 1
            elif 7 <= d.over_number <= 16:
                middle_runs += d.runs_scored or 0
                if d.is_wicket:
                    middle_wickets += 1
            elif 17 <= d.over_number <= 20:
                death_runs += d.runs_scored or 0
                if d.is_wicket:
                    death_wickets += 1
    
    # Calculate aggregates
    season_win_rate = (wins / total_matches * 100) if total_matches > 0 else 0.0
    avg_run_rate = (total_runs / total_matches) if total_matches > 0 else 0.0
    
    # DLS par values (simplified - actual par depends on overs/wickets)
    # Using standard T20 par: 120 runs for 20 overs (6 runs/over)
    pp_par = 72  # 6 overs * 12 runs/over
    middle_par = 108  # 10 overs * 10.8 runs/over
    death_par = 60   # 4 overs * 15 runs/over
    
    powerplay_net_runs = powerplay_runs - pp_par
    middle_net_runs = middle_runs - middle_par
    death_net_runs = death_runs - death_par
    
    # Economy in death overs
    death_balls = 0
    for game in games:
        stmt = select(models.Delivery).where(
            (models.Delivery.game_id == game.id) &
            (models.Delivery.over_number >= 17) &
            (models.Delivery.over_number <= 20)
        )
        result = await db.execute(stmt)
        deliveries = result.scalars().all()
        death_balls += len(deliveries)
    
    death_overs = death_balls / 6 if death_balls > 0 else 1
    death_over_economy = death_runs / death_overs if death_overs > 0 else 0.0
    
    return {
        "total_teams": total_teams,
        "total_matches": total_matches,
        "season_win_rate": round(season_win_rate, 2),
        "avg_run_rate": round(avg_run_rate, 2),
        "powerplay_net_runs": round(powerplay_net_runs, 1),
        "middle_net_runs": round(middle_net_runs, 1),
        "death_net_runs": round(death_net_runs, 1),
        "death_over_economy": round(death_over_economy, 2),
    }


async def get_org_teams_stats(db: AsyncSession, org_id: str) -> list[dict]:
    """
    Get statistics for all teams in an organization.
    
    Returns:
    [
        {
            "id": str,
            "name": str,
            "played": int,
            "won": int,
            "lost": int,
            "win_percent": float,
            "avg_score": float,
            "nrr": float,  # Net run rate
        }
    ]
    """
    
    # Get all teams for this organization (org_id is the owner_user_id)
    stmt = select(models.Team).where(models.Team.owner_user_id == org_id)
    result = await db.execute(stmt)
    org_teams = result.scalars().all()
    
    teams_stats = []
    
    for team in org_teams:
        # Get all games for this team
        stmt = select(models.Game).where(
            (models.Game.team_a_id == team.id) |
            (models.Game.team_b_id == team.id)
        )
        result = await db.execute(stmt)
        games = result.scalars().all()
        
        played = len(games)
        won = 0
        total_runs = 0
        total_runs_conceded = 0
        
        for game in games:
            # Check if team won
            if game.result and isinstance(game.result, dict):
                if game.result.get("winner_team_id") == str(team.id):
                    won += 1
            
            # Get innings-specific stats
            state = game.current_state or {}
            is_batting_team = game.batting_team_id == team.id if hasattr(game, 'batting_team_id') else False
            
            if is_batting_team:
                total_runs += state.get("total_runs", 0)
            
            # For NRR calculation (simplified - actual NRR is more complex)
            stmt = select(models.Delivery).where(
                models.Delivery.game_id == game.id
            )
            result = await db.execute(stmt)
            deliveries = result.scalars().all()
            
            if is_batting_team:
                total_runs += sum(d.runs_scored or 0 for d in deliveries)
            else:
                total_runs_conceded += sum(d.runs_scored or 0 for d in deliveries)
        
        lost = played - won
        win_percent = (won / played * 100) if played > 0 else 0.0
        avg_score = (total_runs / played) if played > 0 else 0.0
        nrr = (total_runs - total_runs_conceded) / played if played > 0 else 0.0
        
        teams_stats.append({
            "id": str(team.id),
            "name": team.name,
            "played": played,
            "won": won,
            "lost": lost,
            "win_percent": round(win_percent, 2),
            "avg_score": round(avg_score, 1),
            "nrr": round(nrr, 2),
        })
    
    return teams_stats


async def get_tournament_leaderboards(
    db: AsyncSession,
    tournament_id: str,
    leaderboard_type: str = "all",  # "batting", "bowling", or "all"
    limit: int = 10,
) -> dict:
    """
    Get tournament-wide player statistics for leaderboards.
    
    Returns:
    {
        "batting": [
            {
                "player_id": str,
                "player_name": str,
                "runs": int,
                "innings": int,
                "average": float,
                "strike_rate": float,
                "fours": int,
                "sixes": int,
            }
        ],
        "bowling": [
            {
                "player_id": str,
                "player_name": str,
                "wickets": int,
                "overs": float,
                "runs_conceded": int,
                "economy": float,
                "average": float,
            }
        ]
    }
    """
    
    # Get all fixtures for this tournament
    stmt = select(models.Fixture).where(models.Fixture.tournament_id == tournament_id)
    result = await db.execute(stmt)
    fixtures = result.scalars().all()
    
    # Collect all game IDs
    game_ids = [f.game_id for f in fixtures if f.game_id]
    
    if not game_ids:
        return {"batting": [], "bowling": []}
    
    # Get all deliveries for these games
    stmt = select(models.Delivery).where(models.Delivery.game_id.in_(game_ids))
    result = await db.execute(stmt)
    deliveries = result.scalars().all()
    
    # Aggregate batting stats
    batting_stats = {}
    for d in deliveries:
        if d.striker_id:
            if d.striker_id not in batting_stats:
                batting_stats[d.striker_id] = {
                    "player_id": d.striker_id,
                    "player_name": d.striker_id,  # Would get from player model in real scenario
                    "runs": 0,
                    "balls": 0,
                    "innings": 0,
                    "fours": 0,
                    "sixes": 0,
                }
            
            batting_stats[d.striker_id]["runs"] += d.runs_off_bat or 0
            batting_stats[d.striker_id]["balls"] += 1
            
            if d.runs_off_bat == 4:
                batting_stats[d.striker_id]["fours"] += 1
            elif d.runs_off_bat == 6:
                batting_stats[d.striker_id]["sixes"] += 1
    
    # Calculate derived metrics for batting
    batting_list = []
    for player_id, stats in batting_stats.items():
        avg = (stats["runs"] / max(1, stats["innings"])) if stats["innings"] > 0 else 0
        sr = (stats["runs"] / max(1, stats["balls"]) * 100) if stats["balls"] > 0 else 0
        
        batting_list.append({
            "player_id": str(player_id),
            "player_name": stats["player_name"],
            "runs": stats["runs"],
            "innings": 1,  # Simplified - should track actual innings
            "average": round(avg, 2),
            "strike_rate": round(sr, 2),
            "fours": stats["fours"],
            "sixes": stats["sixes"],
        })
    
    # Aggregate bowling stats
    bowling_stats = {}
    for d in deliveries:
        if d.bowler_id:
            if d.bowler_id not in bowling_stats:
                bowling_stats[d.bowler_id] = {
                    "player_id": d.bowler_id,
                    "player_name": d.bowler_id,
                    "wickets": 0,
                    "runs": 0,
                    "balls": 0,
                }
            
            bowling_stats[d.bowler_id]["runs"] += d.runs_scored or 0
            bowling_stats[d.bowler_id]["balls"] += 1
            
            if d.is_wicket:
                bowling_stats[d.bowler_id]["wickets"] += 1
    
    # Calculate derived metrics for bowling
    bowling_list = []
    for player_id, stats in bowling_stats.items():
        overs = stats["balls"] / 6
        economy = (stats["runs"] / overs) if overs > 0 else 0
        avg = (stats["runs"] / max(1, stats["wickets"])) if stats["wickets"] > 0 else 0
        
        bowling_list.append({
            "player_id": str(player_id),
            "player_name": stats["player_name"],
            "wickets": stats["wickets"],
            "overs": round(overs, 1),
            "runs_conceded": stats["runs"],
            "economy": round(economy, 2),
            "average": round(avg, 2),
        })
    
    # Sort and limit
    batting_list = sorted(batting_list, key=lambda x: x["runs"], reverse=True)[:limit]
    bowling_list = sorted(bowling_list, key=lambda x: x["wickets"], reverse=True)[:limit]
    
    return {
        "batting": batting_list if leaderboard_type in ["batting", "all"] else [],
        "bowling": bowling_list if leaderboard_type in ["bowling", "all"] else [],
    }
