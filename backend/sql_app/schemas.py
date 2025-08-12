from pydantic import BaseModel, Field
from typing import Any, List, Dict, Literal, Optional
from enum import Enum

# ===================================================================
# Base & Re-usable Models
# ===================================================================

class Player(BaseModel):
    """Represents a single player with their ID and name."""
    id: str
    name: str

class Team(BaseModel):
    """Represents a team with its name and a list of Player objects."""
    name: str
    players: List[Player]

# Delivery ledger entry (what we store/return per ball)
class Delivery(BaseModel):
    over_number: int
    ball_number: int
    bowler_id: str
    striker_id: str
    non_striker_id: str
    runs_scored: int
    is_extra: bool
    extra_type: Optional[str] = None
    is_wicket: bool
    dismissal_type: Optional[str] = None
    dismissed_player_id: Optional[str] = None
    commentary: Optional[str] = None
    # Optional in earlier versions; we include it for richer events
    fielder_id: Optional[str] = None

class BattingScorecardEntry(BaseModel):
    """Represents a single player's batting stats for an innings."""
    player_id: str
    player_name: str
    runs: int
    balls_faced: int
    is_out: bool

class BowlingScorecardEntry(BaseModel):
    """Represents a single player's bowling stats for an innings."""
    player_id: str
    player_name: str
    overs_bowled: float
    runs_conceded: int
    wickets_taken: int

# ===================================================================
# Game staff / contributor roles
# ===================================================================

class GameContributorRole(str, Enum):
    scorer = "scorer"
    commentary = "commentary"
    analytics = "analytics"

class GameContributorIn(BaseModel):
    user_id: str = Field(..., description="Auth/user id (string for MVP)")
    role: GameContributorRole
    display_name: Optional[str] = None

class GameContributor(GameContributorIn):
    id: int
    game_id: str

# ===================================================================
# API Input
# ===================================================================

class GameCreate(BaseModel):
    team_a_name: str
    team_b_name: str
    players_a: List[str] = Field(..., min_length=2)
    players_b: List[str] = Field(..., min_length=2)

    # Flexible match config
    match_type: Literal["limited", "multi_day", "custom"] = "limited"
    overs_limit: Optional[int] = Field(None, ge=1, le=120)
    days_limit: Optional[int] = Field(None, ge=1, le=7)
    overs_per_day: Optional[int] = Field(None, ge=1, le=120)
    dls_enabled: bool = False
    interruptions: List[Dict[str, Optional[str]]] = Field(default_factory=list)

    toss_winner_team: str
    decision: Literal["bat", "bowl"]

class ScoreDelivery(BaseModel):
    striker_id: str
    non_striker_id: str
    bowler_id: str
    runs_scored: int = Field(..., ge=0, le=6)
    extra: Optional[str] = None
    is_wicket: bool = False

    # Full dismissal picker
    dismissal_type: Optional[Literal[
        "bowled", "caught", "lbw", "run_out", "stumped", "hit_wicket",
        "obstructing_the_field", "hit_ball_twice", "timed_out",
        "retired_out", "handled_ball"
    ]] = None
    dismissed_player_id: Optional[str] = None
    fielder_id: Optional[str] = None
    commentary: Optional[str] = None

# Team roles payload
class TeamSide(str, Enum):
    A = "A"
    B = "B"

class TeamRoleUpdate(BaseModel):
    side: TeamSide                  # "A" or "B"
    captain_id: Optional[str] = None
    wicket_keeper_id: Optional[str] = None

# ===================================================================
# API Output (ORM mode)
# ===================================================================

class Game(BaseModel):
    game_id: str = Field(..., alias='id')

    # Teams (stored as JSON in DB)
    team_a: Team
    team_b: Team

    # --- Match setup fields ---
    match_type: str
    overs_limit: Optional[int]
    days_limit: Optional[int]
    dls_enabled: bool
    interruptions: List[Dict[str, Optional[str]]] = Field(default_factory=list, description="Weather/other delays")

    toss_winner_team: str
    decision: str
    batting_team_name: str
    bowling_team_name: str

    # --- State ---
    status: str
    current_inning: int
    total_runs: int
    total_wickets: int
    overs_completed: int
    balls_this_over: int
    current_striker_id: Optional[str] = None
    current_non_striker_id: Optional[str] = None
    first_inning_summary: Optional[Dict[str, Any]] = None
    target: Optional[int] = None
    result: Optional[str] = None

    # --- Team roles (NEW, simple and explicit) ---
    team_a_captain_id: Optional[str] = None
    team_a_keeper_id: Optional[str] = None
    team_b_captain_id: Optional[str] = None
    team_b_keeper_id: Optional[str] = None

    # --- Ledgers & cards ---
    deliveries: List[Delivery]
    batting_scorecard: Dict[str, BattingScorecardEntry]
    bowling_scorecard: Dict[str, BowlingScorecardEntry]

    class Config:
        orm_mode = True
        allow_population_by_field_name = True
