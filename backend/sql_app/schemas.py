from __future__ import annotations
from uuid import UUID
from pydantic import BaseModel, Field
from pydantic import field_validator, model_validator
from pydantic.config import ConfigDict
from typing import Any, List, Dict, Literal, Optional, Sequence, Mapping, Union, TypeAlias, cast
from enum import Enum

TeamItem: TypeAlias = Union[str, UUID, Mapping[str, object]]
ExtraCode = Literal['wd', 'nb', 'b', 'lb']
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

class PlayingXIRequest(BaseModel):
    # Make all the fields explicit so router access is typed
    team_a: List[str] = Field(default_factory=list)
    team_b: List[str] = Field(default_factory=list)
    captain_a: Optional[str] = None
    keeper_a: Optional[str] = None
    captain_b: Optional[str] = None
    keeper_b: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("team_a", "team_b", mode="before")
    @classmethod
    def _normalize_team(cls, v: object) -> List[str]:
        if v is None:
            return []
        if not isinstance(v, (list, tuple)):
            raise TypeError("team must be a list or tuple")

        # Tell the checker exactly what we're iterating
        items: Sequence[TeamItem] = cast(Sequence[TeamItem], v)

        out: List[str] = []
        for item in items:
            # simple id/UUID cases
            if isinstance(item, (str, UUID)):
                out.append(str(item))
                continue

            # mapping case: item is Mapping[str, object] here
            pid_obj = item.get("id") or item.get("player_id")
            if isinstance(pid_obj, (str, UUID)):
                out.append(str(pid_obj))
            else:
                raise TypeError("dict must include 'id' or 'player_id' as str/UUID")

        return out



    
class PlayingXIResponse(BaseModel):
    ok: bool
    game_id: UUID

# Delivery ledger entry (what we store/return per ball)
class Delivery(BaseModel):
    over_number: int
    ball_number: int
    bowler_id: str
    striker_id: str
    non_striker_id: str

    # Store a clear breakdown per ball (new fields, backwards compat with runs_scored)
    runs_off_bat: int = 0                  # off the bat (used on legal and nb)
    extra_type: Optional[ExtraCode] = None # 'wd' | 'nb' | 'b' | 'lb' | None
    extra_runs: int = 0                    # extra count (wides/byes/leg-byes)
    runs_scored: int = 0                   # derived total for the ball, kept for compat

    is_extra: bool
    is_wicket: bool
    dismissal_type: Optional[str] = None
    dismissed_player_id: Optional[str] = None
    commentary: Optional[str] = None
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
    players_a: List[str] = Field(default=..., min_length=2)
    players_b: List[str] = Field(default=..., min_length=2)


    # Flexible match config
    match_type: Literal["limited", "multi_day", "custom"] = "limited"
    overs_limit: Optional[int] = Field(None, ge=1, le=120)
    days_limit: Optional[int] = Field(None, ge=1, le=7)
    overs_per_day: Optional[int] = Field(None, ge=1, le=120)
    dls_enabled: bool = False
    interruptions: List[Dict[str, Optional[str]]] = Field(default_factory=list)

    toss_winner_team: str
    decision: Literal["bat", "bowl"]

class InterruptionStart(BaseModel):
    inning: int = Field(ge=1, le=2)
    kind: Literal["rain", "bad_light", "other"] = "rain"
    note: Optional[str] = None

class InterruptionEnd(BaseModel):
    interruption_id: str
    overs_reduced_to: Optional[int] = Field(default=None, ge=1, le=50)

class ScoreDelivery(BaseModel):
    striker_id: str
    non_striker_id: str
    bowler_id: str
    bowler_name: Optional[str] = None
    # Inputs (mutually exclusive by mode)
    runs_scored: Optional[int] = Field(None, ge=0, le=6)  # used for legal balls or wd/b/lb
    runs_off_bat: Optional[int] = Field(None, ge=0, le=6) # required for nb
    extra: Optional[ExtraCode] = None

    is_wicket: bool = False
    dismissal_type: Optional[Literal[
        "bowled", "caught", "lbw", "run_out", "stumped", "hit_wicket",
        "obstructing_the_field", "hit_ball_twice", "timed_out",
        "retired_out", "handled_ball"
    ]] = None
    dismissed_player_id: Optional[str] = None
    fielder_id: Optional[str] = None
    fielder_name: Optional[str] = None
    commentary: Optional[str] = None

    @model_validator(mode="after")
    def _validate_mode(self):
        if self.extra == "nb":
            if self.runs_off_bat is None:
                raise ValueError("runs_off_bat is required when extra == 'nb'")
            # ignore runs_scored for nb; we derive it
            self.runs_scored = None
        elif self.extra in ("wd", "b", "lb"):
            if self.runs_scored is None:
                raise ValueError("runs_scored is required when extra in {'wd','b','lb'}")
            if self.runs_off_bat not in (None, 0):
                raise ValueError("runs_off_bat must be 0/None unless extra == 'nb'")
        else:
            # legal ball
            self.extra = None
            self.runs_scored = self.runs_scored or 0
            if self.runs_off_bat not in (None, 0):
                raise ValueError("runs_off_bat must be 0/None on a legal ball")
        return self

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
    game_id: str = Field(default=..., alias='id')

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
