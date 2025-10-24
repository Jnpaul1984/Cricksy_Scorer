"""
Validation helper functions for backend API endpoints.

Provides comprehensive validation for:
- Player IDs (existence, team membership)
- Team constraints (batting/bowling teams)
- Logical errors (same player batting and bowling)
- Dismissal types
"""

from typing import Dict, List, Any, Optional, Set
from fastapi import HTTPException


def validate_player_exists(player_id: str, team_a: Dict, team_b: Dict) -> bool:
    """
    Validate that a player ID exists in either team.
    
    Args:
        player_id: The player ID to validate
        team_a: Team A dictionary with players list
        team_b: Team B dictionary with players list
        
    Returns:
        True if player exists, False otherwise
    """
    if not player_id:
        return False
        
    team_a_players = {str(p["id"]) for p in (team_a.get("players", []) or [])}
    team_b_players = {str(p["id"]) for p in (team_b.get("players", []) or [])}
    
    return str(player_id) in (team_a_players | team_b_players)


def validate_player_in_team(player_id: str, team: Dict, team_name: str) -> None:
    """
    Validate that a player belongs to a specific team.
    
    Args:
        player_id: The player ID to validate
        team: The team dictionary
        team_name: Name of the team for error messages
        
    Raises:
        HTTPException: If player is not in the specified team
    """
    if not player_id:
        return
        
    team_players = {str(p["id"]) for p in (team.get("players", []) or [])}
    
    if str(player_id) not in team_players:
        raise HTTPException(
            status_code=422,
            detail=f"Player {player_id} is not in team {team_name}"
        )


def validate_batsman_in_batting_team(
    batsman_id: str,
    team_a: Dict,
    team_b: Dict,
    batting_team_name: str
) -> None:
    """
    Validate that a batsman belongs to the batting team.
    
    Args:
        batsman_id: The batsman's player ID
        team_a: Team A dictionary
        team_b: Team B dictionary
        batting_team_name: Name of the team currently batting
        
    Raises:
        HTTPException: If batsman is not in the batting team
    """
    if not batsman_id:
        return
        
    batting_team = team_a if team_a["name"] == batting_team_name else team_b
    validate_player_in_team(batsman_id, batting_team, batting_team_name)


def validate_bowler_in_bowling_team(
    bowler_id: str,
    team_a: Dict,
    team_b: Dict,
    bowling_team_name: str
) -> None:
    """
    Validate that a bowler belongs to the bowling team.
    
    Args:
        bowler_id: The bowler's player ID
        team_a: Team A dictionary
        team_b: Team B dictionary
        bowling_team_name: Name of the team currently bowling
        
    Raises:
        HTTPException: If bowler is not in the bowling team
    """
    if not bowler_id:
        return
        
    bowling_team = team_a if team_a["name"] == bowling_team_name else team_b
    validate_player_in_team(bowler_id, bowling_team, bowling_team_name)


def validate_no_same_player_batting_and_bowling(
    striker_id: Optional[str],
    non_striker_id: Optional[str],
    bowler_id: Optional[str]
) -> None:
    """
    Validate that the same player is not batting and bowling.
    
    Args:
        striker_id: The striker's player ID
        non_striker_id: The non-striker's player ID
        bowler_id: The bowler's player ID
        
    Raises:
        HTTPException: If the same player is batting and bowling
    """
    if not bowler_id:
        return
        
    batsmen = {str(striker_id), str(non_striker_id)} - {None, "None", ""}
    
    if str(bowler_id) in batsmen:
        raise HTTPException(
            status_code=422,
            detail="Same player cannot be batting and bowling simultaneously"
        )


def validate_dismissal_type(is_wicket: bool, dismissal_type: Optional[str]) -> None:
    """
    Validate dismissal type when a wicket occurs.
    
    Args:
        is_wicket: Whether this delivery is a wicket
        dismissal_type: The type of dismissal
        
    Raises:
        HTTPException: If wicket without dismissal type or invalid dismissal type
    """
    if not is_wicket:
        return
        
    if not dismissal_type:
        raise HTTPException(
            status_code=422,
            detail="Dismissal type is required when is_wicket is true"
        )
    
    valid_dismissal_types = {
        "bowled",
        "caught",
        "lbw",
        "run_out",
        "stumped",
        "hit_wicket",
        "obstructing_the_field",
        "handled_the_ball",
        "timed_out",
        "hit_the_ball_twice",
        "retired_hurt",
        "retired_out",
    }
    
    if dismissal_type.lower() not in valid_dismissal_types:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid dismissal type: {dismissal_type}. "
                   f"Valid types: {', '.join(sorted(valid_dismissal_types))}"
        )


def validate_delivery_players(
    striker_id: Optional[str],
    non_striker_id: Optional[str],
    bowler_id: Optional[str],
    team_a: Dict,
    team_b: Dict,
    batting_team_name: str,
    bowling_team_name: str,
    is_wicket: bool = False,
    dismissal_type: Optional[str] = None
) -> None:
    """
    Comprehensive validation for all players involved in a delivery.
    
    Args:
        striker_id: The striker's player ID
        non_striker_id: The non-striker's player ID
        bowler_id: The bowler's player ID
        team_a: Team A dictionary
        team_b: Team B dictionary
        batting_team_name: Name of the team currently batting
        bowling_team_name: Name of the team currently bowling
        is_wicket: Whether this delivery is a wicket
        dismissal_type: The type of dismissal if wicket
        
    Raises:
        HTTPException: If any validation fails
    """
    # Validate player IDs exist
    if striker_id and not validate_player_exists(striker_id, team_a, team_b):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid striker ID: {striker_id}"
        )
    
    if non_striker_id and not validate_player_exists(non_striker_id, team_a, team_b):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid non-striker ID: {non_striker_id}"
        )
    
    if bowler_id and not validate_player_exists(bowler_id, team_a, team_b):
        raise HTTPException(
            status_code=422,
            detail=f"Invalid bowler ID: {bowler_id}"
        )
    
    # Validate team constraints
    if striker_id:
        validate_batsman_in_batting_team(striker_id, team_a, team_b, batting_team_name)
    
    if non_striker_id:
        validate_batsman_in_batting_team(non_striker_id, team_a, team_b, batting_team_name)
    
    if bowler_id:
        validate_bowler_in_bowling_team(bowler_id, team_a, team_b, bowling_team_name)
    
    # Validate logical constraints
    validate_no_same_player_batting_and_bowling(striker_id, non_striker_id, bowler_id)
    
    # Validate dismissal
    validate_dismissal_type(is_wicket, dismissal_type)




