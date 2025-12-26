from __future__ import annotations

# Import security logging models for DB discovery (import module to register models)
from backend.sql_app import models_security  # noqa: F401

import datetime as dt
import enum
import uuid
from typing import Any, TypedDict

from pydantic import BaseModel
from sqlalchemy import (
    JSON,
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    TypeDecorator,
    func,
)
from sqlalchemy import Enum as SAEnum
from sqlalchemy.dialects import postgresql
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class ArrayOrJSON(TypeDecorator):
    """Handle both ARRAY and JSON column types for backward compatibility.

    Converts between ARRAY (legacy) and JSON (current) types transparently.
    Reads as either type from DB, always writes as JSON.
    """

    impl = JSON
    cache_ok = True

    def process_bind_param(self, value, dialect):
        """Convert Python list to JSON when writing to DB."""
        if value is None:
            return None
        # Always write as JSON
        return value

    def process_result_value(self, value, dialect):
        """Convert DB value (ARRAY or JSON) to Python list when reading."""
        if value is None:
            return []
        # Handle both array strings like ['a','b'] and JSON like ["a","b"]
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            # PostgreSQL might return ARRAY as string representation
            import json
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                # If it's a string like "['a','b']", try to parse as Python literal
                try:
                    import ast
                    return ast.literal_eval(value)
                except (ValueError, SyntaxError):
                    return [value] if value else []
        return value if isinstance(value, list) else []

UTC = getattr(dt, "UTC", dt.UTC)


# -----------------------------
# Enums (align with Snapshot)
# -----------------------------


class GameStatus(str, enum.Enum):
    not_started = "not_started"
    started = "started"  # <-- add
    in_progress = "in_progress"
    innings_break = "innings_break"  # <-- add
    live = "live"  # <-- add (your code checks for this)
    completed = "completed"
    abandoned = "abandoned"


# Keep existing contributor roles
class GameContributorRoleEnum(str, enum.Enum):
    scorer = "scorer"
    commentary = "commentary"
    analytics = "analytics"


class RoleEnum(str, enum.Enum):
    free = "free"
    player_pro = "player_pro"
    coach_pro = "coach_pro"
    coach_pro_plus = "coach_pro_plus"
    analyst_pro = "analyst_pro"
    org_pro = "org_pro"


class PlayerCoachingNoteVisibility(str, enum.Enum):
    private_to_coach = "private_to_coach"
    org_only = "org_only"


class FanFavoriteType(str, enum.Enum):
    player = "player"
    team = "team"


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )
    email: Mapped[str] = mapped_column(String, nullable=False, unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    is_superuser: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    role: Mapped[RoleEnum] = mapped_column(
        SAEnum(RoleEnum, name="user_role"),
        default=RoleEnum.free,
        server_default=RoleEnum.free.value,
        nullable=False,
    )
    subscription_plan: Mapped[RoleEnum | None] = mapped_column(
        SAEnum(RoleEnum, name="user_role", create_type=False),
        nullable=True,
    )
    org_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    beta_tag: Mapped[str | None] = mapped_column(String, nullable=True)
    requires_password_change: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    password_changed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
    fan_matches: Mapped[list[Game]] = relationship(back_populates="created_by_user")
    fan_favorites: Mapped[list[FanFavorite]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )
    coach_assignments: Mapped[list[CoachPlayerAssignment]] = relationship(
        back_populates="coach_user", cascade="all, delete-orphan"
    )
    coaching_sessions: Mapped[list[CoachingSession]] = relationship(
        back_populates="coach_user", cascade="all, delete-orphan"
    )


# -----------------------------
# Helpers for safe JSON defaults
# (avoid default={} or default=[])
# -----------------------------


def _empty_dict() -> dict[str, Any]:
    return {}


def _empty_list() -> list[Any]:
    return []


def _empty_extras() -> dict[str, int]:
    # Matches Snapshot.extras shape
    return {
        "wides": 0,
        "no_balls": 0,
        "byes": 0,
        "leg_byes": 0,
        "penalty": 0,
        "total": 0,
    }


# -----------------------------
# Optional typed helpers
# -----------------------------


class TeamPlayer(TypedDict, total=False):
    id: str
    name: str


class TeamJSON(TypedDict, total=False):
    name: str
    players: list[TeamPlayer]


# -----------------------------
# Core Game model
# -----------------------------


class Game(Base):
    __tablename__ = "games"

    # Identifiers
    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), index=True
    )

    # Existing team JSON (name + players[{id,name}, ...])
    team_a: Mapped[dict[str, Any]] = mapped_column(JSON, default=_empty_dict, nullable=False)
    team_b: Mapped[dict[str, Any]] = mapped_column(JSON, default=_empty_dict, nullable=False)

    # --- Match Setup Fields ---
    match_type: Mapped[str] = mapped_column(
        String, default="custom", nullable=False
    )  # e.g., T20, ODI, Test, custom
    overs_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)  # None for unlimited
    days_limit: Mapped[int | None] = mapped_column(Integer, nullable=True)  # For multi-day matches
    dls_enabled: Mapped[bool] = mapped_column(
        Boolean, default=False, nullable=False
    )  # Duckworth-Lewis-Stern toggle
    interruptions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=_empty_list, nullable=False
    )  # list of events
    overs_per_day: Mapped[int | None] = mapped_column(Integer, nullable=True)

    toss_winner_team: Mapped[str | None] = mapped_column(String, nullable=True)
    decision: Mapped[str | None] = mapped_column(String, nullable=True)
    batting_team_name: Mapped[str | None] = mapped_column(String, nullable=True)
    bowling_team_name: Mapped[str | None] = mapped_column(String, nullable=True)

    # Align with Snapshot.status
    status: Mapped[GameStatus] = mapped_column(
        SAEnum(GameStatus, name="game_status"),
        default=GameStatus.not_started,
        nullable=False,
    )

    # Running total for *current innings* (recomputed when innings changes)
    total_runs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_wickets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    overs_completed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    balls_this_over: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    current_striker_id: Mapped[str | None] = mapped_column(String, nullable=True)
    current_non_striker_id: Mapped[str | None] = mapped_column(String, nullable=True)

    # --- Team roles (NEW already present; keep) ---
    team_a_captain_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    team_a_keeper_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    team_b_captain_id: Mapped[str | None] = mapped_column(Text, nullable=True)
    team_b_keeper_id: Mapped[str | None] = mapped_column(Text, nullable=True)

    # --- Live context for Snapshot (NEW) ---
    current_bowler_id: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # whoâ€™s bowling now (optional)
    last_ball_bowler_id: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # bowler of most recent ball

    # Extras totals for the *current innings* (fast access for snapshot/extras)
    extras_totals: Mapped[dict[str, int]] = mapped_column(
        JSON, default=_empty_extras, nullable=False
    )

    # Fall of wickets (array of {score_at_fall, over, batter_id})
    fall_of_wickets: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=_empty_list, nullable=False
    )

    # Optional caches (compute on the fly; keep persisted for convenience)
    phases: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=_empty_dict, nullable=False
    )  # {powerplay|middle|death: {...}}
    projections: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=_empty_dict, nullable=False
    )  # rr_current, rr_last_5_overs, etc.

    # Chase context (nullable when not chasing)
    target: Mapped[int | None] = mapped_column(Integer, nullable=True)
    par_score: Mapped[int | None] = mapped_column(Integer, nullable=True)  # if you wire DLS
    required_run_rate: Mapped[float | None] = mapped_column(
        Float, nullable=True
    )  # computed; convenience

    # --- Deliveries ledger ---
    # per-ball dicts with dismissal, extras, etc. (authoritative event store)
    deliveries: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=_empty_list, nullable=False
    )

    # Per-player tallies (you already had; ensure safe defaults)
    batting_scorecard: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=_empty_dict, nullable=False
    )
    bowling_scorecard: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=_empty_dict, nullable=False
    )

    # Innings / result
    current_inning: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    first_inning_summary: Mapped[dict[str, Any] | None] = mapped_column(JSON, nullable=True)
    result: Mapped[str | None] = mapped_column(String, nullable=True)
    created_by_user_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    is_fan_match: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
    )
    created_by_user: Mapped[User | None] = relationship(back_populates="fan_matches")

    # Relationship backref from GameContributor is set below
    contributors: Mapped[list[GameContributor]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )

    # New relationships for analytics routes
    batting_scorecards: Mapped[list[BattingScorecard]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )
    bowling_scorecards: Mapped[list[BowlingScorecard]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_games_is_fan_match", "is_fan_match"),)

    def get_winner(self):
        """
        Logic to determine the winner of the game.
        This may involve comparing team scores, checking any decided rules or tie-breakers.
        """
        # Placeholder logic, replace with actual game win condition logic
        if self.target is not None:
            if self.total_runs > self.target:  # Simplified logic example
                return self.batting_team_name
            elif self.total_runs < self.target:
                return self.bowling_team_name
            else:
                return "Draw"  # or other logic for tie condition
        else:
            return None  # or handle case where target is not set

    def get_team_scores(self):
        """
        Logic to calculate team scores.
        This will typically return scores for both teams in a tuple.
        """
        team_a_score = self.batting_scorecard.get("total", 0)
        team_b_score = self.bowling_scorecard.get("total", 0)
        return team_a_score, team_b_score

    @property
    def is_game_over(self) -> bool:
        return self.status in (GameStatus.completed, GameStatus.abandoned)

    @property
    def needs_new_innings(self) -> bool:
        return self.status == GameStatus.innings_break


# ---------- Pydantic payloads you already had ----------


class PlayingXIRequest(BaseModel):
    team_a: list[uuid.UUID]
    team_b: list[uuid.UUID]
    captain_a: uuid.UUID | None = None
    keeper_a: uuid.UUID | None = None
    captain_b: uuid.UUID | None = None
    keeper_b: uuid.UUID | None = None


class PlayingXIResponse(BaseModel):
    ok: bool
    game_id: uuid.UUID


# ===== Game Staff / Contributors =====


class GameContributor(Base):
    __tablename__ = "game_contributors"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(
        String, ForeignKey("games.id", ondelete="CASCADE"), index=True, nullable=False
    )
    user_id: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[GameContributorRoleEnum] = mapped_column(
        SAEnum(GameContributorRoleEnum, name="game_contributor_role"), nullable=False
    )
    display_name: Mapped[str | None] = mapped_column(Text, nullable=True)

    game: Mapped[Game] = relationship(back_populates="contributors")


# Unique index for (game_id, user_id, role)
Index(
    "ix_game_contributors_unique",
    GameContributor.game_id,
    GameContributor.user_id,
    GameContributor.role,
    unique=True,
)


# ===== Sponsors =====


class Sponsor(Base):
    __tablename__ = "sponsors"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)

    # stored as relative path under STATIC_DIR, e.g. "sponsors/<uuid>.svg"
    logo_path: Mapped[str] = mapped_column(String, nullable=False)

    click_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    weight: Mapped[int] = mapped_column(Integer, nullable=False, default=1)  # 1..5
    surfaces: Mapped[list[str]] = mapped_column(JSON, default=lambda: ["all"], nullable=False)

    start_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # UTC
    end_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )  # UTC

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_sponsors_weight", "weight"),
        Index("ix_sponsors_active_window", "start_at", "end_at"),
    )


# ===== Sponsor Impressions =====


class SponsorImpression(Base):
    __tablename__ = "sponsor_impressions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(
        String, ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sponsor_id: Mapped[str] = mapped_column(
        String, ForeignKey("sponsors.id", ondelete="CASCADE"), nullable=False
    )
    at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )

    __table_args__ = (
        Index("ix_sponsor_impressions_sponsor_id", "sponsor_id"),
        Index("ix_sponsor_impressions_at", "at"),
    )


# ===== Player Profiles =====


class PlayerProfile(Base):
    """Stores comprehensive player statistics and profile information."""

    __tablename__ = "player_profiles"

    player_id: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    player_name: Mapped[str] = mapped_column(String, nullable=False)

    # Batting statistics
    total_matches: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_innings_batted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_runs_scored: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_balls_faced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_fours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_sixes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    times_out: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    highest_score: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    centuries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    half_centuries: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Bowling statistics
    total_innings_bowled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_overs_bowled: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    total_runs_conceded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    total_wickets: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    best_bowling_figures: Mapped[str | None] = mapped_column(String, nullable=True)  # "5/23"
    five_wicket_hauls: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    maidens: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Fielding statistics
    catches: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    stumpings: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    run_outs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Timestamps
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    achievements: Mapped[list[PlayerAchievement]] = relationship(
        back_populates="player_profile", cascade="all, delete-orphan"
    )
    form_entries: Mapped[list[PlayerForm]] = relationship(
        back_populates="player_profile", cascade="all, delete-orphan"
    )
    coaching_notes: Mapped[list[PlayerCoachingNotes]] = relationship(
        back_populates="player_profile", cascade="all, delete-orphan"
    )
    summary: Mapped[PlayerSummary] = relationship(back_populates="player_profile", uselist=False)
    coach_assignments: Mapped[list[CoachPlayerAssignment]] = relationship(
        back_populates="player_profile", cascade="all, delete-orphan"
    )
    coaching_sessions: Mapped[list[CoachingSession]] = relationship(
        back_populates="player_profile", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_player_profiles_total_runs", "total_runs_scored"),
        Index("ix_player_profiles_total_wickets", "total_wickets"),
        Index("ix_player_profiles_batting_avg", "total_runs_scored", "times_out"),
    )

    @property
    def batting_average(self) -> float:
        """Calculate batting average: total runs / times out."""
        return (
            round(self.total_runs_scored / self.times_out, 2)
            if self.times_out > 0
            else float(self.total_runs_scored)
        )

    @property
    def strike_rate(self) -> float:
        """Calculate strike rate: (total runs / balls faced) * 100."""
        return (
            round((self.total_runs_scored / self.total_balls_faced) * 100, 2)
            if self.total_balls_faced > 0
            else 0.0
        )

    @property
    def bowling_average(self) -> float:
        """Calculate bowling average: runs conceded / wickets taken."""
        return (
            round(self.total_runs_conceded / self.total_wickets, 2)
            if self.total_wickets > 0
            else float(self.total_runs_conceded)
        )

    @property
    def economy_rate(self) -> float:
        """Calculate economy rate: runs conceded / overs bowled."""
        return (
            round(self.total_runs_conceded / self.total_overs_bowled, 2)
            if self.total_overs_bowled > 0
            else 0.0
        )


# ===== Player Achievements =====


class AchievementType(str, enum.Enum):
    """Types of achievements that can be awarded to players."""

    century = "century"  # 100+ runs in an innings
    half_century = "half_century"  # 50-99 runs in an innings
    five_wickets = "five_wickets"  # 5+ wickets in an innings
    best_scorer = "best_scorer"  # Best scorer of the match
    best_bowler = "best_bowler"  # Best bowler of the match
    hat_trick = "hat_trick"  # 3 wickets in consecutive balls
    golden_duck = "golden_duck"  # Out on first ball
    maiden_over = "maiden_over"  # Bowled a maiden over
    six_sixes = "six_sixes"  # 6 sixes in an innings
    perfect_catch = "perfect_catch"  # 3+ catches in a match


class PlayerAchievement(Base):
    """Stores individual achievements and badges earned by players."""

    __tablename__ = "player_achievements"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    player_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("player_profiles.player_id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    game_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("games.id", ondelete="SET NULL"), index=True, nullable=True
    )

    achievement_type: Mapped[AchievementType] = mapped_column(
        SAEnum(AchievementType, name="achievement_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)  # e.g., "Century Maker"
    description: Mapped[str] = mapped_column(
        Text, nullable=False
    )  # e.g., "Scored 105 runs vs Team B"
    badge_icon: Mapped[str | None] = mapped_column(String, nullable=True)  # emoji or icon class

    earned_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Optional: achievement details (runs scored, wickets taken, etc.)
    achievement_metadata: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=_empty_dict, nullable=False
    )

    # Relationships
    player_profile: Mapped[PlayerProfile] = relationship(back_populates="achievements")

    __table_args__ = (
        Index("ix_player_achievements_type", "achievement_type"),
        Index("ix_player_achievements_earned_at", "earned_at"),
    )


# ===== Player Pro =====


class PlayerForm(Base):
    __tablename__ = "player_forms"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    player_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("player_profiles.player_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    period_start: Mapped[dt.date] = mapped_column(Date, nullable=False)
    period_end: Mapped[dt.date] = mapped_column(Date, nullable=False)
    matches_played: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    wickets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    batting_average: Mapped[float | None] = mapped_column(Float, nullable=True)
    strike_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    economy: Mapped[float | None] = mapped_column(Float, nullable=True)
    form_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    player_profile: Mapped[PlayerProfile] = relationship(back_populates="form_entries")

    __table_args__ = (Index("ix_player_forms_period", "player_id", "period_start", "period_end"),)


class PlayerCoachingNotes(Base):
    __tablename__ = "player_coaching_notes"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    player_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("player_profiles.player_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    coach_user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    strengths: Mapped[str] = mapped_column(Text, nullable=False)
    weaknesses: Mapped[str] = mapped_column(Text, nullable=False)
    action_plan: Mapped[str | None] = mapped_column(Text, nullable=True)
    visibility: Mapped[PlayerCoachingNoteVisibility] = mapped_column(
        postgresql.ENUM(
            PlayerCoachingNoteVisibility,
            name="coaching_note_visibility",
            create_type=False,
        ),
        nullable=False,
        default=PlayerCoachingNoteVisibility.private_to_coach,
        server_default=PlayerCoachingNoteVisibility.private_to_coach.value,
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    player_profile: Mapped[PlayerProfile] = relationship(back_populates="coaching_notes")

    __table_args__ = (Index("ix_player_coaching_notes_visibility", "visibility"),)


class PlayerSummary(Base):
    __tablename__ = "player_summaries"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    player_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("player_profiles.player_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    total_matches: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_runs: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    total_wickets: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    batting_average: Mapped[float | None] = mapped_column(Float, nullable=True)
    bowling_average: Mapped[float | None] = mapped_column(Float, nullable=True)
    strike_rate: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    player_profile: Mapped[PlayerProfile] = relationship(back_populates="summary")

    __table_args__ = (
        Index("ix_player_summaries_player_id", "player_id"),
        Index("ix_player_summaries_totals", "total_runs", "total_wickets"),
    )


class CoachPlayerAssignment(Base):
    __tablename__ = "coach_player_assignments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    coach_user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_profile_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("player_profiles.player_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        server_default="true",
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    coach_user: Mapped[User] = relationship(back_populates="coach_assignments")
    player_profile: Mapped[PlayerProfile] = relationship(back_populates="coach_assignments")

    __table_args__ = (
        Index(
            "ix_coach_assignments_unique",
            "coach_user_id",
            "player_profile_id",
            unique=True,
        ),
    )


class CoachingSession(Base):
    __tablename__ = "coaching_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    coach_user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_profile_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("player_profiles.player_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scheduled_at: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    focus_area: Mapped[str] = mapped_column(String, nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    outcome: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    coach_user: Mapped[User] = relationship(back_populates="coaching_sessions")
    player_profile: Mapped[PlayerProfile] = relationship(back_populates="coaching_sessions")

    __table_args__ = (
        Index("ix_coaching_sessions_coach_time", "coach_user_id", "scheduled_at"),
        Index("ix_coaching_sessions_player_time", "player_profile_id", "scheduled_at"),
    )


class FanFavorite(Base):
    __tablename__ = "fan_favorites"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    favorite_type: Mapped[FanFavoriteType] = mapped_column(
        postgresql.ENUM(
            FanFavoriteType,
            name="fan_favorite_type",
            create_type=False,
        ),
        nullable=False,
    )
    player_profile_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("player_profiles.player_id", ondelete="CASCADE"),
        nullable=True,
    )
    team_id: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    user: Mapped[User] = relationship(back_populates="fan_favorites")
    player_profile: Mapped[PlayerProfile | None] = relationship()

    __table_args__ = (
        CheckConstraint(
            "(player_profile_id IS NOT NULL AND team_id IS NULL) OR "
            "(player_profile_id IS NULL AND team_id IS NOT NULL)",
            name="ck_fan_favorites_target",
        ),
        Index("ix_fan_favorites_user_type", "user_id", "favorite_type"),
        Index(
            "ix_fan_favorites_user_player",
            "user_id",
            "player_profile_id",
        ),
        Index("ix_fan_favorites_user_team", "user_id", "team_id"),
    )


# ===== Tournament Management =====


class Tournament(Base):
    __tablename__ = "tournaments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name: Mapped[str] = mapped_column(String, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    tournament_type: Mapped[str] = mapped_column(
        String, nullable=False, default="league"
    )  # league, knockout, round-robin
    start_date: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    end_date: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    status: Mapped[str] = mapped_column(
        String, nullable=False, default="upcoming"
    )  # upcoming, ongoing, completed

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    teams: Mapped[list[TournamentTeam]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )
    fixtures: Mapped[list[Fixture]] = relationship(
        back_populates="tournament", cascade="all, delete-orphan"
    )

    __table_args__ = (Index("ix_tournaments_status", "status"),)


class TournamentTeam(Base):
    __tablename__ = "tournament_teams"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tournament_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    team_name: Mapped[str] = mapped_column(String, nullable=False)
    team_data: Mapped[dict[str, Any]] = mapped_column(
        JSON, default=_empty_dict, nullable=False
    )  # Store team info like players

    # Points table data
    matches_played: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matches_won: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matches_lost: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    matches_drawn: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    points: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    net_run_rate: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    # Relationships
    tournament: Mapped[Tournament] = relationship(back_populates="teams")

    __table_args__ = (Index("ix_tournament_teams_points", "points"),)


class Fixture(Base):
    __tablename__ = "fixtures"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    tournament_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("tournaments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    match_number: Mapped[int | None] = mapped_column(Integer, nullable=True)
    team_a_name: Mapped[str] = mapped_column(String, nullable=False)
    team_b_name: Mapped[str] = mapped_column(String, nullable=False)
    venue: Mapped[str | None] = mapped_column(String, nullable=True)
    scheduled_date: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Link to actual game if created
    game_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("games.id", ondelete="SET NULL"), nullable=True
    )

    status: Mapped[str] = mapped_column(
        String, nullable=False, default="scheduled"
    )  # scheduled, in_progress, completed, cancelled
    result: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    tournament: Mapped[Tournament] = relationship(back_populates="fixtures")

    __table_args__ = (
        Index("ix_fixtures_status", "status"),
        Index("ix_fixtures_scheduled_date", "scheduled_date"),
    )


# ===== Feedback Submissions =====


class FeedbackSubmission(Base):
    __tablename__ = "feedback_submissions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )
    text: Mapped[str] = mapped_column(Text, nullable=False)
    email: Mapped[str | None] = mapped_column(String, nullable=True)
    user_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    user_role: Mapped[str | None] = mapped_column(String, nullable=True)
    page_route: Mapped[str | None] = mapped_column(String, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_feedback_submissions_created_at", "created_at"),)


# ===== Team Management =====


class Team(Base):
    """Standalone team entity for organization-level team management."""

    __tablename__ = "teams"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    home_ground: Mapped[str | None] = mapped_column(String(255), nullable=True)
    season: Mapped[str | None] = mapped_column(String(50), nullable=True)
    owner_user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    coach_user_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    coach_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    players: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )  # [{id, name}, ...]
    competitions: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=list, nullable=False
    )  # [{id, name}, ...]
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (
        Index("ix_teams_name", "name"),
        Index("ix_teams_owner", "owner_user_id"),
    )


class AiUsageLog(Base):
    """Tracks AI/LLM feature usage for billing and analytics."""

    __tablename__ = "ai_usage_logs"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    org_id: Mapped[str | None] = mapped_column(
        String, nullable=True, index=True
    )  # Optional org association for billing
    feature: Mapped[str] = mapped_column(
        String(100), nullable=False, index=True
    )  # e.g. "match_summary", "player_insights", "tactical_advice"
    tokens_used: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    context_id: Mapped[str | None] = mapped_column(
        String, nullable=True
    )  # Optional reference (game_id, player_id, etc.)
    model_name: Mapped[str | None] = mapped_column(
        String(100), nullable=True
    )  # e.g. "gpt-4", "claude-3"
    timestamp: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    __table_args__ = (
        Index("ix_ai_usage_user_feature", "user_id", "feature"),
        Index("ix_ai_usage_org_timestamp", "org_id", "timestamp"),
    )


# -------- Cricket Player & Statistics Models --------


class Player(Base):
    """Cricket player profile."""

    __tablename__ = "players"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    country: Mapped[str | None] = mapped_column(String(100), nullable=True)
    role: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # Batsman, Bowler, All-rounder
    jersey_number: Mapped[int | None] = mapped_column(Integer, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    __table_args__ = (Index("ix_players_name", "name"),)


class BattingScorecard(Base):
    """Batting statistics for a player in a game."""

    __tablename__ = "batting_scorecards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_id: Mapped[str] = mapped_column(String, ForeignKey("games.id"), nullable=False)
    player_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)

    runs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    balls_faced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    fours: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    sixes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    is_wicket: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    dismissal_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    game: Mapped[Game] = relationship(back_populates="batting_scorecards")
    player: Mapped[Player] = relationship()

    __table_args__ = (Index("ix_batting_scorecard_game_player", "game_id", "player_id"),)


class BowlingScorecard(Base):
    """Bowling statistics for a player in a game."""

    __tablename__ = "bowling_scorecards"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_id: Mapped[str] = mapped_column(String, ForeignKey("games.id"), nullable=False)
    bowler_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)

    overs_bowled: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    runs_conceded: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    wickets_taken: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    maiden_overs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extras_bowled: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    game: Mapped[Game] = relationship(back_populates="bowling_scorecards")
    bowler: Mapped[Player] = relationship()

    __table_args__ = (Index("ix_bowling_scorecard_game_bowler", "game_id", "bowler_id"),)


class Delivery(Base):
    """Individual ball delivery record."""

    __tablename__ = "deliveries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    game_id: Mapped[str] = mapped_column(String, ForeignKey("games.id"), nullable=False)
    inning_number: Mapped[int] = mapped_column(Integer, nullable=False)
    over: Mapped[int] = mapped_column(Integer, nullable=False)
    ball: Mapped[int] = mapped_column(Integer, nullable=False)

    bowler_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)
    batter_id: Mapped[int] = mapped_column(Integer, ForeignKey("players.id"), nullable=False)

    runs: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    extras: Mapped[str | None] = mapped_column(String(20), nullable=True)  # 'wd', 'nb', 'b', 'lb'
    is_wicket: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    wicket_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    pitch_coordinate_x: Mapped[float | None] = mapped_column(Float, nullable=True)
    pitch_coordinate_y: Mapped[float | None] = mapped_column(Float, nullable=True)
    delivery_type: Mapped[str | None] = mapped_column(
        String(50), nullable=True
    )  # 'fast', 'spin', etc.

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    game: Mapped[Game] = relationship()
    bowler: Mapped[Player] = relationship(foreign_keys=[bowler_id])
    batter: Mapped[Player] = relationship(foreign_keys=[batter_id])

    __table_args__ = (
        Index("ix_delivery_game_inning", "game_id", "inning_number"),
        Index("ix_delivery_bowler", "bowler_id"),
        Index("ix_delivery_batter", "batter_id"),
    )


# ============================================================================
# Video Analysis Models (Coach Pro Plus)
# ============================================================================


class OwnerTypeEnum(str, enum.Enum):
    """Type of owner for video sessions and analysis jobs."""

    coach = "coach"
    org = "org"


class VideoSessionStatus(str, enum.Enum):
    """Status of a video session."""

    pending = "pending"  # Created but no video uploaded
    uploaded = "uploaded"  # Video file uploaded to S3
    processing = "processing"  # Analysis in progress
    ready = "ready"  # Analysis complete
    failed = "failed"  # Analysis failed


class VideoAnalysisJobStatus(str, enum.Enum):
    """Status of a video analysis job."""

    queued = "queued"  # Job created, waiting in queue
    processing = "processing"  # Job is being processed
    completed = "completed"  # Job completed successfully
    failed = "failed"  # Job failed


class VideoSession(Base):
    """Video session for Coach Pro Plus features.

    Tracks uploaded coaching videos with metadata about ownership and S3 storage.
    """

    __tablename__ = "video_sessions"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )
    # Ownership (flexible: coach user or org)
    owner_type: Mapped[OwnerTypeEnum] = mapped_column(
        SAEnum(OwnerTypeEnum, name="owner_type"),
        nullable=False,
        comment="Type of owner: coach or org",
    )
    owner_id: Mapped[str] = mapped_column(
        String, nullable=False, index=True, comment="Coach user_id or org_id"
    )

    # Session metadata
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    player_ids: Mapped[list[str]] = mapped_column(
        ArrayOrJSON,
        default=list,
        nullable=False,
        comment="Player IDs involved (handles both ARRAY and JSON types)",
    )

    # S3 storage details
    s3_bucket: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="S3 bucket name where video is stored"
    )
    s3_key: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="S3 object key for the video file"
    )

    # Status tracking
    status: Mapped[VideoSessionStatus] = mapped_column(
        SAEnum(VideoSessionStatus, name="video_session_status"),
        default=VideoSessionStatus.pending,
        nullable=False,
    )

    # Timestamps
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    analysis_jobs: Mapped[list[VideoAnalysisJob]] = relationship(
        back_populates="session", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_video_sessions_owner", "owner_type", "owner_id"),
        Index("ix_video_sessions_status", "status"),
        Index("ix_video_sessions_created_at", "created_at"),
    )


class VideoAnalysisJob(Base):
    """Video analysis job for processing video content.

    Represents an async job in the SQS queue for frame extraction, pose detection, etc.
    """

    __tablename__ = "video_analysis_jobs"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )

    # Reference to session
    session_id: Mapped[str] = mapped_column(
        String, ForeignKey("video_sessions.id", ondelete="CASCADE"), nullable=False, index=True
    )

    # Job configuration
    sample_fps: Mapped[int] = mapped_column(
        Integer, default=10, nullable=False, comment="Frames sampled per second"
    )
    include_frames: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Include per-frame data in results",
    )

    # Status and error handling
    status: Mapped[VideoAnalysisJobStatus] = mapped_column(
        SAEnum(VideoAnalysisJobStatus, name="video_analysis_job_status"),
        default=VideoAnalysisJobStatus.queued,
        nullable=False,
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Error details if job failed"
    )

    # SQS tracking
    sqs_message_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="AWS SQS message ID when enqueued"
    )

    # Results storage
    results: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Full analysis results: pose, metrics, findings, report"
    )

    # Timestamps
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    started_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When processing started"
    )
    completed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When processing completed"
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    session: Mapped[VideoSession] = relationship(back_populates="analysis_jobs")

    __table_args__ = (
        Index("ix_analysis_jobs_session_id", "session_id"),
        Index("ix_analysis_jobs_status", "status"),
        Index("ix_analysis_jobs_created_at", "created_at"),
        Index("ix_analysis_jobs_sqs_message_id", "sqs_message_id"),
    )
