from __future__ import annotations

import datetime as dt
from collections.abc import Mapping, Sequence
from enum import Enum
from typing import Any, Literal, TypeAlias, cast
from uuid import UUID

from pydantic import BaseModel, Field, field_validator, model_validator
from pydantic.config import ConfigDict

UTC = getattr(dt, "UTC", dt.UTC)
TeamItem: TypeAlias = str | UUID | Mapping[str, object]  # noqa: UP040
ExtraCode = Literal["wd", "nb", "b", "lb"]
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
    players: list[Player]


class PlayingXIRequest(BaseModel):
    # Make all the fields explicit so router access is typed
    team_a: list[str] = Field(default_factory=list)
    team_b: list[str] = Field(default_factory=list)
    captain_a: str | None = None
    keeper_a: str | None = None
    captain_b: str | None = None
    keeper_b: str | None = None

    model_config = ConfigDict(populate_by_name=True)

    @field_validator("team_a", "team_b", mode="before")
    @classmethod
    def _normalize_team(cls, v: object) -> list[str]:
        if v is None:
            return []
        if not isinstance(v, (list, tuple)):
            raise TypeError("team must be a list or tuple")

        # Tell the checker exactly what we're iterating
        items: Sequence[TeamItem] = cast(Sequence[TeamItem], v)

        out: list[str] = []
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
    runs_off_bat: int = 0  # off the bat (used on legal and nb)
    extra_type: ExtraCode | None = None  # 'wd' | 'nb' | 'b' | 'lb' | None
    extra_runs: int = 0  # extra count (wides/byes/leg-byes)
    runs_scored: int = 0  # derived total for the ball, kept for compat

    is_extra: bool
    is_wicket: bool
    dismissal_type: str | None = None
    dismissed_player_id: str | None = None
    commentary: str | None = None
    fielder_id: str | None = None
    shot_map: str | None = None


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


class MatchStatus(str, Enum):
    SCHEDULED = "SCHEDULED"
    IN_PROGRESS = "IN_PROGRESS"
    INNINGS_BREAK = "INNINGS_BREAK"
    COMPLETED = "COMPLETED"
    ABANDONED = "ABANDONED"


class GameContributorIn(BaseModel):
    user_id: str = Field(..., description="Auth/user id (string for MVP)")
    role: GameContributorRole
    display_name: str | None = None


class GameContributor(GameContributorIn):
    id: int
    game_id: str


class MatchType(str, Enum):
    limited = "limited"
    multi_day = "multi_day"
    custom = "custom"


# ===================================================================
# API Input
# ===================================================================


class GameCreate(BaseModel):
    team_a_name: str
    team_b_name: str
    players_a: list[str] = Field(default=..., min_length=2)
    players_b: list[str] = Field(default=..., min_length=2)

    # Flexible match config
    match_type: MatchType
    overs_limit: int | None = Field(None, ge=1, le=120)
    days_limit: int | None = Field(None, ge=1, le=7)
    overs_per_day: int | None = Field(None, ge=1, le=120)
    dls_enabled: bool = False
    interruptions: list[dict[str, str | None]] = Field(default_factory=list)

    toss_winner_team: str
    decision: Literal["bat", "bowl"]


class InterruptionStart(BaseModel):
    inning: int = Field(ge=1, le=2)
    kind: Literal["rain", "bad_light", "other"] = "rain"
    note: str | None = None


class InterruptionEnd(BaseModel):
    interruption_id: str
    overs_reduced_to: int | None = Field(default=None, ge=1, le=50)


class ScoreDelivery(BaseModel):
    shot_angle_deg: float | None = None  # optional shot direction for wagon wheel
    shot_map: str | None = None  # compact SVG or encoded sketch for analytics
    striker_id: str | None = None
    non_striker_id: str | None = None
    bowler_id: str | None = None  # let server keep current bowler mid-over
    bowler_name: str | None = None
    # Allow UX to submit dismissed player by name to avoid exposing IDs in UI
    dismissed_player_name: str | None = None
    # Inputs (mutually exclusive by mode)
    runs_scored: int | None = Field(None, ge=0, le=6)
    runs_off_bat: int | None = Field(None, ge=0, le=6)
    extra: ExtraCode | None = None

    is_wicket: bool = False
    dismissal_type: (
        Literal[
            "bowled",
            "caught",
            "lbw",
            "run_out",
            "stumped",
            "hit_wicket",
            "obstructing_the_field",
            "hit_ball_twice",
            "timed_out",
            "retired_out",
            "retired_hurt",
            "handled_ball",
        ]
        | None
    ) = None
    dismissed_player_id: str | None = None
    fielder_id: str | None = None
    fielder_name: str | None = None
    commentary: str | None = None

    @model_validator(mode="after")
    def _validate_mode(self):
        if self.extra == "nb":
            if self.runs_off_bat is None:
                raise ValueError("runs_off_bat is required when extra == 'nb'")
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
    side: TeamSide  # "A" or "B"
    captain_id: str | None = None
    wicket_keeper_id: str | None = None


# ===================================================================
# API Output (ORM mode)
# ===================================================================
class MatchMethod(str, Enum):
    by_runs = "by runs"
    by_wickets = "by wickets"
    tie = "tie"  # ... existing code ...
    no_result = "no result"


class MatchResult(BaseModel):
    """
    Structured result so frontend can show a winner banner and avoid guessing.
    Keep result_text for human-readable display.
    """

    winner_team_id: str | None = None
    winner_team_name: str | None = None
    method: MatchMethod | None = None

    margin: int | None = None
    result_text: str | None = None
    completed_at: dt.datetime | None = None


class MatchResultRequest(BaseModel):
    match_id: UUID  # ... existing code ...
    winner: str | None = None  # ID of the winning team or None for a draw
    team_a_score: int  # Total score of Team A
    team_b_score: int  # Total score of Team B


class Game(BaseModel):
    game_id: str = Field(default=..., alias="id")

    # Teams (stored as JSON in DB)
    team_a: Team
    team_b: Team

    # --- Match setup fields ---
    match_type: MatchType
    overs_limit: int | None
    days_limit: int | None
    dls_enabled: bool
    interruptions: list[dict[str, str | None]] = Field(
        default_factory=list, description="Weather/other delays"
    )

    toss_winner_team: str
    decision: str
    batting_team_name: str
    bowling_team_name: str

    # --- State ---
    status: MatchStatus
    current_inning: int
    total_runs: int
    total_wickets: int
    overs_completed: int
    balls_this_over: int
    current_striker_id: str | None = None
    current_non_striker_id: str | None = None
    first_inning_summary: dict[str, Any] | None = None
    target: int | None = None

    # --- Result / completion (NEW / updated) ---
    result: MatchResult | MatchResultRequest | None = None
    is_game_over: bool = False
    completed_at: dt.datetime | None = None

    # --- Team roles ---
    team_a_captain_id: str | None = None
    team_a_keeper_id: str | None = None
    team_b_captain_id: str | None = None
    team_b_keeper_id: str | None = None

    # --- Ledgers & cards ---
    deliveries: list[Delivery]
    batting_scorecard: dict[str, BattingScorecardEntry]
    bowling_scorecard: dict[str, BowlingScorecardEntry]

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)

    @field_validator("status", mode="before")
    @classmethod
    def _normalize_status(cls, v: Any) -> MatchStatus:
        """
        Accept backend statuses (enum or str), map to API enum.
        Backend emits: not_started, started, in_progress, innings_break, live, completed, abandoned
        API serves:    SCHEDULED, IN_PROGRESS, INNINGS_BREAK, COMPLETED, ABANDONED
        """
        # unwrap SA/Python Enum
        if isinstance(v, Enum):
            v = v.value

        s = str(v).strip().lower()

        mapping: dict[str, MatchStatus] = {
            "not_started": MatchStatus.SCHEDULED,
            "scheduled": MatchStatus.SCHEDULED,
            "started": MatchStatus.IN_PROGRESS,
            "live": MatchStatus.IN_PROGRESS,
            "in_progress": MatchStatus.IN_PROGRESS,
            "innings_break": MatchStatus.INNINGS_BREAK,
            "completed": MatchStatus.COMPLETED,
            "abandoned": MatchStatus.ABANDONED,
        }

        # Already one of the API enum strings?
        for m in MatchStatus:
            if s == m.value.lower():
                return m

        # Map internal â†' API
        if s in mapping:
            return mapping[s]

        # Fallback (keeps the response valid)
        return MatchStatus.IN_PROGRESS

    @field_validator("result", mode="before")
    @classmethod
    def _coerce_result(cls, v: object) -> MatchResult | dict[str, Any] | None:
        """
        Accepts:
        - None
        - MatchResult instance
        - Mapping[str, Any] (dict-like)
        - Legacy string -> coerced to {'result_text': ...}
        Returns:
        MatchResult | Dict[str, Any] | None
        """
        if v is None:
            return None

        if isinstance(v, MatchResult):
            return v

        # Handle dict-like inputs with known key/value types
        if isinstance(v, Mapping):
            return dict(cast(Mapping[str, Any], v))

        # Legacy plain string from older routes/DB snapshots
        if isinstance(v, str):
            return {"result_text": v}

        # Fallback: stringify to keep type known and avoid "Unknown"
        return {"result_text": str(v)}


# NEW: A concise snapshot schema for UI consumption
class Snapshot(BaseModel):
    """
    Minimal, stable shape the frontend consumes.
    Return this from scoring/ledger endpoints to keep payloads light.
    """

    id: str = Field(..., alias="game_id")

    status: MatchStatus
    current_inning: int

    batting_team_name: str
    bowling_team_name: str

    total_runs: int
    total_wickets: int
    overs_completed: int
    balls_this_over: int

    target: int | None = None
    overs_limit: int | None = None

    # completion/result signals
    is_game_over: bool = False
    result: MatchResult | None = None
    completed_at: dt.datetime | None = None

    model_config = ConfigDict(populate_by_name=True)
