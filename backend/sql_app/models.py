from __future__ import annotations

import datetime as dt
import enum
import uuid
from typing import Any, TypedDict

from pydantic import BaseModel
from sqlalchemy import (
    JSON,
    BigInteger,
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

# Import security logging models for DB discovery (import module to register models)
from backend.sql_app import models_security  # noqa: F401
from backend.services.player_development_state import (
    normalize_player_development_plan_governance,
)

from .database import Base


class ArrayOrJSON(TypeDecorator):
    """Handle both ARRAY and JSON column types for backward compatibility.

    For PostgreSQL: Uses JSONB (works with current migrations)
    For SQLite: Uses JSON (SQLite doesn't support ARRAY)
    """

    impl = JSON  # Default to JSON for SQLite compatibility in tests
    cache_ok = True

    def load_dialect_impl(self, dialect):
        """Use JSONB for PostgreSQL, JSON for SQLite/others."""
        if dialect.name == "postgresql":
            return dialect.type_descriptor(postgresql.JSONB())
        return dialect.type_descriptor(JSON())

    def process_bind_param(self, value, dialect):
        """Convert Python list to appropriate format for database."""
        if value is None:
            return None
        # Return list directly - dialect-specific handling will take care of it
        if isinstance(value, list):
            return value
        return value

    def process_result_value(self, value, dialect):
        """Convert DB value (ARRAY or JSON) to Python list when reading."""
        if value is None:
            return []
        # Already a list from PostgreSQL ARRAY or JSON
        if isinstance(value, list):
            return value
        # Handle JSON strings
        if isinstance(value, str):
            import json

            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
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
    venue_admin = "venue_admin"  # NEW: Ground/facility administrators


class PlayerCoachingNoteVisibility(str, enum.Enum):
    private_to_coach = "private_to_coach"
    org_only = "org_only"


class FanFavoriteType(str, enum.Enum):
    player = "player"
    team = "team"


class PlayerDevelopmentPlanStatus(str, enum.Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    completed = "completed"
    archived = "archived"


class PlayerDevelopmentSourceType(str, enum.Enum):
    match_data = "match_data"
    video_analysis = "video_analysis"
    coach_note = "coach_note"
    ai_insight = "ai_insight"
    manual = "manual"


class PlayerDevelopmentSeverity(str, enum.Enum):
    low = "low"
    medium = "medium"
    high = "high"


class PlayerDevelopmentApprovalState(str, enum.Enum):
    not_required = "not_required"
    pending_review = "pending_review"
    approved = "approved"
    rejected = "rejected"
    changes_requested = "changes_requested"


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
    player_development_plans: Mapped[list[PlayerDevelopmentPlan]] = relationship(
        back_populates="coach_user", cascade="all, delete-orphan"
    )
    player_development_interventions: Mapped[list[PlayerDevelopmentIntervention]] = relationship(
        back_populates="coach_user", cascade="all, delete-orphan"
    )
    player_drill_assignments: Mapped[list[PlayerDrillAssignment]] = relationship(
        back_populates="coach_user", cascade="all, delete-orphan"
    )
    player_progress_checkpoints: Mapped[list[PlayerProgressCheckpoint]] = relationship(
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

    # Innings grades relationship
    innings_grades: Mapped[list[InningsGrade]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )

    # Pressure points relationship
    pressure_points: Mapped[list[PressurePoint]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )

    # Phase predictions relationship
    phase_predictions: Mapped[list[PhasePrediction]] = relationship(
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


# ===== Innings Grades =====


class InningsGrade(Base):
    """Stores letter grades for innings performance (A+, A, B, C, D)."""

    __tablename__ = "innings_grades"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(
        String, ForeignKey("games.id", ondelete="CASCADE"), index=True, nullable=False
    )
    inning_num: Mapped[int] = mapped_column(Integer, nullable=False)
    grade: Mapped[str] = mapped_column(String(3), nullable=False)  # A+, A, B, C, D
    score_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    par_score: Mapped[int] = mapped_column(Integer, nullable=False)
    total_runs: Mapped[int] = mapped_column(Integer, nullable=False)
    run_rate: Mapped[float] = mapped_column(Float, nullable=False)
    wickets_lost: Mapped[int] = mapped_column(Integer, nullable=False)
    wicket_efficiency: Mapped[float] = mapped_column(Float, nullable=False)
    boundary_count: Mapped[int] = mapped_column(Integer, nullable=False)
    boundary_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    dot_ball_ratio: Mapped[float] = mapped_column(Float, nullable=False)
    overs_played: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    game: Mapped[Game] = relationship(back_populates="innings_grades")


# Unique index for (game_id, inning_num)
Index(
    "ix_innings_grades_game_inning",
    InningsGrade.game_id,
    InningsGrade.inning_num,
    unique=True,
)


# ===== Pressure Points =====


class PressurePoint(Base):
    """Stores pressure analysis data for each delivery in a game."""

    __tablename__ = "pressure_points"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(
        String, ForeignKey("games.id", ondelete="CASCADE"), index=True, nullable=False
    )
    inning_num: Mapped[int] = mapped_column(Integer, nullable=False)
    delivery_num: Mapped[int] = mapped_column(Integer, nullable=False)
    over_num: Mapped[float] = mapped_column(Float, nullable=False)
    pressure_score: Mapped[float] = mapped_column(Float, nullable=False)  # 0-100
    pressure_level: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # low, moderate, building, high, extreme
    factors: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    rates: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    cumulative_stats: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    game: Mapped[Game] = relationship(back_populates="pressure_points")


# Unique index for (game_id, inning_num, delivery_num)
Index(
    "ix_pressure_points_game_inning_delivery",
    PressurePoint.game_id,
    PressurePoint.inning_num,
    PressurePoint.delivery_num,
    unique=True,
)

# Index for faster lookups by game and inning
Index(
    "ix_pressure_points_game_inning",
    PressurePoint.game_id,
    PressurePoint.inning_num,
)


# ===== Phase Predictions =====


class PhasePrediction(Base):
    """Stores phase-based predictions for each delivery in a game."""

    __tablename__ = "phase_predictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    game_id: Mapped[str] = mapped_column(
        String, ForeignKey("games.id", ondelete="CASCADE"), index=True, nullable=False
    )
    inning_num: Mapped[int] = mapped_column(Integer, nullable=False)
    delivery_num: Mapped[int] = mapped_column(Integer, nullable=False)
    current_over: Mapped[float] = mapped_column(Float, nullable=False)
    current_phase: Mapped[str] = mapped_column(
        String(20), nullable=False
    )  # powerplay, middle, death, mini_death

    # Prediction fields
    projected_total: Mapped[int] = mapped_column(Integer, nullable=False)
    next_over_predicted_runs: Mapped[int] = mapped_column(Integer, nullable=False)
    next_over_range_min: Mapped[int] = mapped_column(Integer, nullable=False)
    next_over_range_max: Mapped[int] = mapped_column(Integer, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)  # 0-1

    # Phase statistics at this point
    phase_stats: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    # Win probability (if chasing)
    win_probability: Mapped[float | None] = mapped_column(Float, nullable=True)

    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime, nullable=False, server_default=func.now()
    )

    game: Mapped[Game] = relationship(back_populates="phase_predictions")


# Unique index for (game_id, inning_num, delivery_num)
Index(
    "ix_phase_predictions_game_inning_delivery",
    PhasePrediction.game_id,
    PhasePrediction.inning_num,
    PhasePrediction.delivery_num,
    unique=True,
)

# Index for faster lookups by game and inning
Index(
    "ix_phase_predictions_game_inning",
    PhasePrediction.game_id,
    PhasePrediction.inning_num,
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
    development_plans: Mapped[list[PlayerDevelopmentPlan]] = relationship(
        back_populates="player_profile", cascade="all, delete-orphan"
    )
    weakness_tags: Mapped[list[PlayerWeaknessTag]] = relationship(
        back_populates="player_profile", cascade="all, delete-orphan"
    )
    strength_tags: Mapped[list[PlayerStrengthTag]] = relationship(
        back_populates="player_profile", cascade="all, delete-orphan"
    )
    drill_assignments: Mapped[list[PlayerDrillAssignment]] = relationship(
        back_populates="player_profile", cascade="all, delete-orphan"
    )
    progress_checkpoints: Mapped[list[PlayerProgressCheckpoint]] = relationship(
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


class PlayerDevelopmentPlan(Base):
    __tablename__ = "player_development_plans"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    player_profile_id: Mapped[str] = mapped_column(
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
    org_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    summary: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[PlayerDevelopmentPlanStatus] = mapped_column(
        SAEnum(PlayerDevelopmentPlanStatus, name="player_development_plan_status"),
        default=PlayerDevelopmentPlanStatus.draft,
        server_default=PlayerDevelopmentPlanStatus.draft.value,
        nullable=False,
        index=True,
    )
    source_type: Mapped[PlayerDevelopmentSourceType] = mapped_column(
        SAEnum(PlayerDevelopmentSourceType, name="player_development_source_type"),
        default=PlayerDevelopmentSourceType.manual,
        server_default=PlayerDevelopmentSourceType.manual.value,
        nullable=False,
        index=True,
    )
    coach_approved: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
        nullable=False,
    )
    approval_state: Mapped[PlayerDevelopmentApprovalState] = mapped_column(
        SAEnum(PlayerDevelopmentApprovalState, name="player_development_approval_state"),
        default=PlayerDevelopmentApprovalState.not_required,
        server_default=PlayerDevelopmentApprovalState.not_required.value,
        nullable=False,
    )
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=_empty_list, nullable=False
    )
    ai_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=_empty_dict, nullable=False)
    activated_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    player_profile: Mapped[PlayerProfile] = relationship(back_populates="development_plans")
    coach_user: Mapped[User] = relationship(back_populates="player_development_plans")
    goals: Mapped[list[PlayerDevelopmentGoal]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )
    weakness_tags: Mapped[list[PlayerWeaknessTag]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )
    strength_tags: Mapped[list[PlayerStrengthTag]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )
    interventions: Mapped[list[PlayerDevelopmentIntervention]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )
    drill_assignments: Mapped[list[PlayerDrillAssignment]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )
    progress_checkpoints: Mapped[list[PlayerProgressCheckpoint]] = relationship(
        back_populates="plan", cascade="all, delete-orphan"
    )

    __table_args__ = (
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_player_development_plans_confidence_range",
        ),
        Index(
            "ix_player_development_plans_owner_status",
            "player_profile_id",
            "coach_user_id",
            "org_id",
            "status",
        ),
    )

    def __init__(self, **kwargs: Any):
        normalized_status, normalized_coach_approved, normalized_approval_state = (
            normalize_player_development_plan_governance(
                kwargs.get("source_type", PlayerDevelopmentSourceType.manual),
                kwargs.get("status"),
                kwargs.get("coach_approved"),
                kwargs.get("approval_state"),
            )
        )
        kwargs["status"] = PlayerDevelopmentPlanStatus(normalized_status)
        kwargs["coach_approved"] = normalized_coach_approved
        kwargs["approval_state"] = PlayerDevelopmentApprovalState(normalized_approval_state)
        super().__init__(**kwargs)


class CoachingSkillAuditLog(Base):
    __tablename__ = "coaching_skill_audit_logs"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    event_type: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    skill_id: Mapped[str] = mapped_column(String(128), nullable=False)
    skill_version: Mapped[str] = mapped_column(String(32), nullable=False)
    triggered_by_user_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    reviewed_by_user_id: Mapped[str | None] = mapped_column(String, nullable=True)
    player_profile_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    plan_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    video_session_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    video_analysis_job_id: Mapped[str | None] = mapped_column(String, nullable=True, index=True)
    approval_decision: Mapped[str | None] = mapped_column(String(64), nullable=True)
    approval_state_after: Mapped[str | None] = mapped_column(String(64), nullable=True)
    coach_approved_after: Mapped[bool | None] = mapped_column(Boolean, nullable=True)
    organization_id: Mapped[str | None] = mapped_column(String, nullable=True)
    input_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=_empty_dict, nullable=False)
    output_summary: Mapped[dict[str, Any]] = mapped_column(JSON, default=_empty_dict, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )


class PlayerDevelopmentGoal(Base):
    __tablename__ = "player_development_goals"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("player_development_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    target_metric: Mapped[str | None] = mapped_column(String(100), nullable=True)
    baseline_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    target_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    current_value: Mapped[float | None] = mapped_column(Float, nullable=True)
    unit: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[PlayerDevelopmentPlanStatus] = mapped_column(
        SAEnum(PlayerDevelopmentPlanStatus, name="player_development_plan_status", create_type=False),
        default=PlayerDevelopmentPlanStatus.draft,
        server_default=PlayerDevelopmentPlanStatus.draft.value,
        nullable=False,
        index=True,
    )
    due_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    evidence_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=_empty_list, nullable=False
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

    plan: Mapped[PlayerDevelopmentPlan] = relationship(back_populates="goals")


class PlayerWeaknessTag(Base):
    __tablename__ = "player_weakness_tags"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("player_development_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_profile_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("player_profiles.player_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    safe_display_label: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[PlayerDevelopmentSeverity] = mapped_column(
        SAEnum(PlayerDevelopmentSeverity, name="player_development_severity"),
        default=PlayerDevelopmentSeverity.medium,
        server_default=PlayerDevelopmentSeverity.medium.value,
        nullable=False,
    )
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_type: Mapped[PlayerDevelopmentSourceType] = mapped_column(
        SAEnum(PlayerDevelopmentSourceType, name="player_development_source_type", create_type=False),
        default=PlayerDevelopmentSourceType.manual,
        server_default=PlayerDevelopmentSourceType.manual.value,
        nullable=False,
        index=True,
    )
    evidence_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=_empty_list, nullable=False
    )
    ai_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=_empty_dict, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    plan: Mapped[PlayerDevelopmentPlan] = relationship(back_populates="weakness_tags")
    player_profile: Mapped[PlayerProfile] = relationship(back_populates="weakness_tags")

    __table_args__ = (
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_player_weakness_tags_confidence_range",
        ),
        Index("ix_player_weakness_tags_category", "category"),
    )


class PlayerStrengthTag(Base):
    __tablename__ = "player_strength_tags"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("player_development_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_profile_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("player_profiles.player_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(String(100), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    source_type: Mapped[PlayerDevelopmentSourceType] = mapped_column(
        SAEnum(PlayerDevelopmentSourceType, name="player_development_source_type", create_type=False),
        default=PlayerDevelopmentSourceType.manual,
        server_default=PlayerDevelopmentSourceType.manual.value,
        nullable=False,
        index=True,
    )
    evidence_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=_empty_list, nullable=False
    )
    ai_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=_empty_dict, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    plan: Mapped[PlayerDevelopmentPlan] = relationship(back_populates="strength_tags")
    player_profile: Mapped[PlayerProfile] = relationship(back_populates="strength_tags")

    __table_args__ = (
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_player_strength_tags_confidence_range",
        ),
        Index("ix_player_strength_tags_category", "category"),
    )


class PlayerDevelopmentIntervention(Base):
    __tablename__ = "player_development_interventions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("player_development_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    coach_user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_type: Mapped[PlayerDevelopmentSourceType] = mapped_column(
        SAEnum(PlayerDevelopmentSourceType, name="player_development_source_type", create_type=False),
        default=PlayerDevelopmentSourceType.manual,
        server_default=PlayerDevelopmentSourceType.manual.value,
        nullable=False,
        index=True,
    )
    intervention_type: Mapped[str] = mapped_column(String(100), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    scheduled_for: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=_empty_list, nullable=False
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

    plan: Mapped[PlayerDevelopmentPlan] = relationship(back_populates="interventions")
    coach_user: Mapped[User] = relationship(back_populates="player_development_interventions")


class PlayerDrillAssignment(Base):
    __tablename__ = "player_drill_assignments"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("player_development_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_profile_id: Mapped[str] = mapped_column(
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
    drill_category: Mapped[str] = mapped_column(String(100), nullable=False)
    drill_name: Mapped[str] = mapped_column(String(255), nullable=False)
    drill_description: Mapped[str | None] = mapped_column(Text, nullable=True)
    frequency: Mapped[str | None] = mapped_column(String(100), nullable=True)
    status: Mapped[PlayerDevelopmentPlanStatus] = mapped_column(
        SAEnum(PlayerDevelopmentPlanStatus, name="player_development_plan_status", create_type=False),
        default=PlayerDevelopmentPlanStatus.draft,
        server_default=PlayerDevelopmentPlanStatus.draft.value,
        nullable=False,
        index=True,
    )
    assigned_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    due_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    completed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    evidence_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=_empty_list, nullable=False
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

    plan: Mapped[PlayerDevelopmentPlan] = relationship(back_populates="drill_assignments")
    player_profile: Mapped[PlayerProfile] = relationship(back_populates="drill_assignments")
    coach_user: Mapped[User] = relationship(back_populates="player_drill_assignments")


class PlayerProgressCheckpoint(Base):
    __tablename__ = "player_progress_checkpoints"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    plan_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("player_development_plans.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    player_profile_id: Mapped[str] = mapped_column(
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
    checkpoint_date: Mapped[dt.date] = mapped_column(Date, nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    progress_status: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    evidence_refs: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, default=_empty_list, nullable=False
    )
    ai_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=_empty_dict, nullable=False)
    coach_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    plan: Mapped[PlayerDevelopmentPlan] = relationship(back_populates="progress_checkpoints")
    player_profile: Mapped[PlayerProfile] = relationship(back_populates="progress_checkpoints")
    coach_user: Mapped[User] = relationship(back_populates="player_progress_checkpoints")

    __table_args__ = (
        CheckConstraint(
            "confidence_score IS NULL OR (confidence_score >= 0 AND confidence_score <= 1)",
            name="ck_player_progress_checkpoints_confidence_range",
        ),
        Index(
            "ix_player_progress_checkpoints_player_date",
            "player_profile_id",
            "checkpoint_date",
        ),
    )


class MentalQuestionnaireCategory(str, enum.Enum):
    mental_toughness = "Mental Toughness"
    pressure_handling = "Pressure Handling"
    game_awareness = "Game Awareness / Cricket IQ"
    training_habits = "Training Habits & Discipline"


class MentalQuestionnaireQuestion(Base):
    __tablename__ = "mental_questionnaire_questions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    category: Mapped[MentalQuestionnaireCategory] = mapped_column(
        SAEnum(MentalQuestionnaireCategory, name="mental_questionnaire_category"),
        nullable=False,
        index=True,
    )
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    display_order: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=True, server_default="true"
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_mental_questionnaire_question_category_order",
            "category",
            "display_order",
            unique=True,
        ),
    )


class MentalQuestionnaireSession(Base):
    __tablename__ = "mental_questionnaire_sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    player_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("player_profiles.player_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    submitted_by_user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    overall_average_score: Mapped[float] = mapped_column(Float, nullable=False)
    overall_summary: Mapped[str] = mapped_column(Text, nullable=False)
    strengths: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=_empty_list)
    development_areas: Mapped[list[Any]] = mapped_column(JSON, nullable=False, default=_empty_list)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_mental_questionnaire_sessions_player_created", "player_id", "created_at"),
    )


class MentalQuestionnaireAnswer(Base):
    __tablename__ = "mental_questionnaire_answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("mental_questionnaire_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("mental_questionnaire_questions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    score: Mapped[int] = mapped_column(Integer, nullable=False)

    __table_args__ = (
        CheckConstraint("score >= 1 AND score <= 5", name="ck_mental_questionnaire_score_range"),
        Index(
            "ix_mental_questionnaire_answers_session_question",
            "session_id",
            "question_id",
            unique=True,
        ),
    )


class MentalQuestionnaireCategoryScore(Base):
    __tablename__ = "mental_questionnaire_category_scores"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("mental_questionnaire_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    category: Mapped[MentalQuestionnaireCategory] = mapped_column(
        SAEnum(
            MentalQuestionnaireCategory, name="mental_questionnaire_category", create_type=False
        ),
        nullable=False,
        index=True,
    )
    average_score: Mapped[float] = mapped_column(Float, nullable=False)

    __table_args__ = (
        Index(
            "ix_mental_questionnaire_category_scores_session_category",
            "session_id",
            "category",
            unique=True,
        ),
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


class BetaAccess(Base):
    """Beta access entitlements for early access users.

    Allows granting feature access beyond role restrictions:
    - is_super_beta: Access to all features (beta super user)
    - entitlements: Specific features like ["video_upload", "advanced_analytics"]
    - expires_at: Optional expiration date
    """

    __tablename__ = "beta_access"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )
    user_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    is_super_beta: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default="false",
        comment="Grants all features (beta super user)",
    )
    entitlements: Mapped[list[str] | None] = mapped_column(
        JSON,
        nullable=True,
        comment='Custom feature list: ["video_upload", "advanced_analytics"]',
    )
    expires_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Beta access expiration (NULL = permanent)",
    )
    granted_by: Mapped[str | None] = mapped_column(
        String, nullable=True, comment="Admin who granted access"
    )
    notes: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Admin notes about beta access"
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    __table_args__ = (Index("ix_beta_access_expires_at", "expires_at"),)


# -------- Cricket Player & Statistics Models --------


# ============================================================================
# Coach Notes (Coach Pro Plus)
# ============================================================================


class CoachNoteSeverity(str, enum.Enum):
    """Severity level for coach notes."""

    info = "info"
    improvement = "improvement"
    critical = "critical"


class VideoMomentType(str, enum.Enum):
    """Types of moments to mark in fielding/wicketkeeping videos."""

    setup = "setup"  # Initial positioning
    catch = "catch"  # Taking a catch
    throw = "throw"  # Throwing the ball
    dive = "dive"  # Diving save or effort
    stumping = "stumping"  # Wicketkeeping stumping
    other = "other"  # Other notable moments


class VideoMomentMarker(Base):
    """Timestamped markers for specific moments in video sessions.

    Used primarily for fielding and wicketkeeping analysis to mark
    key moments like catches, throws, dives, stumpings, etc.
    """

    __tablename__ = "video_moment_markers"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )
    video_session_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("video_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    timestamp_ms: Mapped[int] = mapped_column(
        BigInteger,
        nullable=False,
        index=True,
        comment="Timestamp in milliseconds from video start",
    )
    moment_type: Mapped[VideoMomentType] = mapped_column(
        SAEnum(VideoMomentType, name="video_moment_type"),
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_by: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        comment="Coach who created this marker",
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class CoachNote(Base):
    """Coach feedback/notes on individual players.

    Allows coaches to document observations, areas for improvement,
    and feedback linked to specific video sessions.
    """

    __tablename__ = "coach_notes"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )
    coach_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Coach who created the note",
    )
    player_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("players.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Player the note is about",
    )
    video_session_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("video_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional link to video session",
    )
    moment_marker_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("video_moment_markers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional link to specific moment in video",
    )
    note_text: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str] | None] = mapped_column(
        ArrayOrJSON,
        nullable=True,
        comment='Tags like ["footwork", "timing", "technique"]',
    )
    severity: Mapped[CoachNoteSeverity] = mapped_column(
        SAEnum(CoachNoteSeverity, name="coach_note_severity"),
        nullable=False,
        server_default="info",
        index=True,
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
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


class VideoSessionType(str, enum.Enum):
    """Type of cricket coaching session."""

    batting = "batting"
    bowling = "bowling"
    fielding = "fielding"
    wicketkeeping = "wicketkeeping"


class AnalysisContext(str, enum.Enum):
    """What aspect of cricket is being analyzed in the video."""

    batting = "batting"
    bowling = "bowling"
    wicketkeeping = "wicketkeeping"
    fielding = "fielding"
    mixed = "mixed"


class CameraView(str, enum.Enum):
    """Camera angle/view for the video recording."""

    side = "side"
    front = "front"
    behind = "behind"
    other = "other"


class VideoAnalysisJobStatus(str, enum.Enum):
    """Status of a video analysis job."""

    awaiting_upload = "awaiting_upload"  # Job created, waiting for upload to complete
    queued = "queued"  # Upload confirmed, ready for worker to claim

    # Staged processing (DB-backed worker)
    quick_running = "quick_running"
    quick_done = "quick_done"
    deep_running = "deep_running"
    done = "done"

    # Legacy states (kept for backward compatibility)
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
    session_type: Mapped[VideoSessionType | None] = mapped_column(
        SAEnum(VideoSessionType, name="video_session_type"),
        nullable=True,
        index=True,
        comment="Type of session: batting, bowling, fielding, wicketkeeping",
    )
    analysis_context: Mapped[AnalysisContext | None] = mapped_column(
        SAEnum(AnalysisContext, name="analysis_context"),
        nullable=True,
        index=True,
        comment="What aspect is being analyzed: batting, bowling, wicketkeeping, fielding, mixed",
    )
    camera_view: Mapped[CameraView | None] = mapped_column(
        SAEnum(CameraView, name="camera_view"),
        nullable=True,
        comment="Camera angle: side, front, behind, other",
    )
    min_duration_seconds: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        server_default="300",
        comment="Minimum video duration required (default 5 minutes)",
    )
    player_ids: Mapped[list[str]] = mapped_column(
        ArrayOrJSON,
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
    file_size_bytes: Mapped[int | None] = mapped_column(
        BigInteger, nullable=True, comment="File size in bytes for quota tracking"
    )

    # Pitch calibration data
    pitch_corners: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment="4 corner points for pitch homography: [{x, y}, {x, y}, {x, y}, {x, y}]",
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

    # Progress tracking (0-100) and stage label
    progress_pct: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Progress percent (0-100) across quick/deep stages",
    )
    stage: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Current stage label (e.g. QUICK, DEEP)",
    )

    # Stage control
    deep_enabled: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="If false, job completes after quick stage",
    )
    deep_mode: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        default="cpu",
        comment="Deep processing mode: cpu (monolithic) or gpu (chunked)",
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Error details if job failed"
    )

    # Chunked processing tracking
    total_chunks: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Total number of chunks for GPU processing",
    )
    completed_chunks: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        default=0,
        comment="Number of completed chunks",
    )
    video_duration_seconds: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
        comment="Video duration in seconds",
    )

    # Analysis configuration
    analysis_mode: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Analysis mode: batting, bowling, or wicketkeeping",
    )

    # SQS tracking
    sqs_message_id: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="AWS SQS message ID when enqueued"
    )

    # S3 storage snapshot (immutable per job - prevents 404s from session mutations)
    s3_bucket: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="S3 bucket snapshot at job creation"
    )
    s3_key: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="S3 key snapshot at job creation"
    )

    # Results storage
    # Keep legacy `results` for backward compatibility (older clients/tests)
    results: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Legacy combined analysis results"
    )

    # New staged results
    quick_results: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Quick pass results JSON"
    )
    deep_results: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Deep pass results JSON"
    )

    # Extracted artifacts for frontend consumption
    quick_findings: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Quick pass findings extracted from quick_results"
    )
    quick_report: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Quick pass report extracted from quick_results"
    )
    deep_findings: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Deep pass findings extracted from deep_results"
    )
    deep_report: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Deep pass report extracted from deep_results"
    )

    # S3 artifact keys for large payloads
    quick_results_s3_key: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="S3 key for quick results JSON"
    )
    deep_results_s3_key: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="S3 key for deep results JSON"
    )

    # PDF export
    pdf_s3_key: Mapped[str | None] = mapped_column(
        String(500), nullable=True, comment="S3 key for exported PDF report"
    )
    pdf_generated_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When PDF was generated"
    )

    # Phase 2: Coach goals and outcomes tracking
    coach_goals: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment=(
            "Coach-defined goals: "
            "{zones: [{zone_id, target_accuracy}], metrics: [{code, target_score}]}"
        ),
    )
    outcomes: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment=(
            "Calculated outcomes vs goals: {zones: [...], metrics: [...], overall_compliance_pct}"
        ),
    )
    goal_compliance_pct: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Overall goal compliance percentage (0-100)"
    )

    # Phase 3: AI coaching suggestions
    coach_suggestions: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment=(
            "AI-generated coaching suggestions: "
            "{primary_focus, secondary_focus, coaching_cues, drills, "
            "proposed_next_goal, rationale}"
        ),
    )
    player_summary: Mapped[dict[str, Any] | None] = mapped_column(
        JSON,
        nullable=True,
        comment=(
            "Player-facing simplified summary of suggestions: "
            "{focus, what_to_practice, encouragement}"
        ),
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

    # Per-stage timestamps (optional)
    quick_started_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When quick stage started"
    )
    quick_completed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When quick stage completed"
    )
    deep_started_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When deep stage started"
    )
    deep_completed_at: Mapped[dt.datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="When deep stage completed"
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )

    # Relationships
    session: Mapped[VideoSession] = relationship(back_populates="analysis_jobs")
    chunks: Mapped[list[VideoAnalysisChunk]] = relationship(
        back_populates="job", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_analysis_jobs_session_id", "session_id"),
        Index("ix_analysis_jobs_status", "status"),
        Index("ix_analysis_jobs_created_at", "created_at"),
        Index("ix_analysis_jobs_sqs_message_id", "sqs_message_id"),
    )


class VideoAnalysisChunkStatus(str, enum.Enum):
    """Status of a video analysis chunk."""

    queued = "queued"  # Chunk ready for GPU worker
    processing = "processing"  # Chunk being processed
    completed = "completed"  # Chunk processing complete
    failed = "failed"  # Chunk processing failed


class TargetZone(Base):
    """Coach-defined target zones on the pitch for accuracy analysis."""

    __tablename__ = "target_zones"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )
    owner_id: Mapped[str] = mapped_column(
        String, nullable=False, index=True, comment="Coach user_id who created the zone"
    )
    session_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("video_sessions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
        comment="Optional link to specific session",
    )
    name: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Zone name (e.g., 'Yorker Line', 'Off Stump')"
    )
    shape: Mapped[str] = mapped_column(
        String(20), nullable=False, default="rect", comment="Shape type: rect, circle, polygon"
    )
    definition_json: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        comment="Shape definition: {x, y, width, height} for rect, {cx, cy, r} for circle, etc.",
    )
    target_accuracy: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Target accuracy percentage (0.0-1.0) for goal compliance"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, nullable=False, comment="Whether zone is active for analysis"
    )
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )


class VideoAnalysisChunk(Base):
    """Individual chunk for parallel GPU processing.

    Each chunk represents a time segment of the video to be processed independently.
    GPU workers claim chunks via SKIP LOCKED for parallel processing.
    """

    __tablename__ = "video_analysis_chunks"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )

    # Reference to parent job
    job_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("video_analysis_jobs.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Chunk specification
    chunk_index: Mapped[int] = mapped_column(
        Integer, nullable=False, comment="0-based chunk index for ordering"
    )
    start_sec: Mapped[float] = mapped_column(Float, nullable=False, comment="Start time in seconds")
    end_sec: Mapped[float] = mapped_column(Float, nullable=False, comment="End time in seconds")

    # Status tracking
    status: Mapped[VideoAnalysisChunkStatus] = mapped_column(
        SAEnum(VideoAnalysisChunkStatus, name="video_analysis_chunk_status"),
        default=VideoAnalysisChunkStatus.queued,
        nullable=False,
    )
    attempts: Mapped[int] = mapped_column(
        Integer, default=0, nullable=False, comment="Number of processing attempts"
    )

    # Results
    artifact_s3_key: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="S3 key for chunk JSON output: jobs/{job_id}/chunks/chunk_{index:04d}.json",
    )
    runtime_ms: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Processing time in milliseconds"
    )
    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Error details if chunk failed"
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

    # Relationships
    job: Mapped[VideoAnalysisJob] = relationship(back_populates="chunks")

    __table_args__ = (
        Index("ix_analysis_chunks_job_id", "job_id"),
        Index("ix_analysis_chunks_status", "status"),
        Index("ix_analysis_chunks_job_chunk_idx", "job_id", "chunk_index", unique=True),
    )


# ---------------------------------------------------------------------------
# Phase 5C - Historical Import Batch Tracking
# ---------------------------------------------------------------------------


class HistoricalImportBatch(Base):
    """Tracks metadata for each historical JSON import dry-run preview.

    Persisted only when the caller explicitly requests record_preview=true.
    Phase 5C: never creates Game/Delivery/Player/Team rows; is_finalized stays False.
    Phase 5D: apply path sets is_finalized=True and applied_game_id after a successful write.
    """

    __tablename__ = "historical_import_batches"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )

    # Ownership - at least one should be set when available
    owner_user_id: Mapped[str | None] = mapped_column(
        String, nullable=True, index=True, comment="User who triggered the import preview"
    )
    owner_org_id: Mapped[str | None] = mapped_column(
        String, nullable=True, index=True, comment="Org scope for duplicate detection"
    )

    # Source provenance
    source_filename: Mapped[str | None] = mapped_column(
        String(512), nullable=True, comment="Original upload filename if supplied"
    )
    source_format: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="Detected format: cricksy_fixture, cricsheet_json, unknown",
    )
    source_hash_sha256: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        index=True,
        comment="SHA-256 of canonical JSON bytes for exact dup detection",
    )

    # Semantic duplicate key - competition|date|team_a|team_b when derivable
    semantic_key: Mapped[str | None] = mapped_column(
        String(512), nullable=True, index=True, comment="Semantic match key for fuzzy dup detection"
    )

    # Validation summary
    status: Mapped[str] = mapped_column(
        String(32), nullable=False, comment="valid | invalid | unsupported"
    )
    error_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    warning_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    innings_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    delivery_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Full dry-run summary stored as JSON for auditability
    dry_run_summary: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Serialized dry-run response payload for audit"
    )

    # Write-path gate - always False in Phase 5C; set True by Phase 5D apply path
    is_finalized: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="True only when actual Game rows have been committed (Phase 5D+)",
    )

    # Phase 5D: ID of the Game row created when this batch was applied.
    # Null until apply succeeds; enables rollback and audit.
    applied_game_id: Mapped[str | None] = mapped_column(
        String,
        nullable=True,
        comment="Game.id created by Phase 5D apply; null until batch is finalized",
    )

    # Timestamps
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index("ix_hist_import_hash_user", "source_hash_sha256", "owner_user_id"),
        Index("ix_hist_import_hash_org", "source_hash_sha256", "owner_org_id"),
        Index("ix_hist_import_semantic_user", "semantic_key", "owner_user_id"),
        Index("ix_hist_import_semantic_org", "semantic_key", "owner_org_id"),
    )


# ---------------------------------------------------------------------------
# Phase 10E - Historical Player Registry + Identity Resolution
# ---------------------------------------------------------------------------


class HistoricalPlayerResolutionState(str, enum.Enum):
    unresolved = "unresolved"
    auto_resolved = "auto_resolved"
    manually_resolved = "manually_resolved"
    ambiguous = "ambiguous"
    blocked = "blocked"
    duplicate = "duplicate"


class HistoricalSourcePlayerRegistry(Base):
    __tablename__ = "historical_source_player_registry"

    source_player_id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )
    source_player_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_schema: Mapped[str] = mapped_column(String(64), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    resolution_state: Mapped[HistoricalPlayerResolutionState] = mapped_column(
        SAEnum(HistoricalPlayerResolutionState, name="historical_player_resolution_state"),
        nullable=False,
        default=HistoricalPlayerResolutionState.unresolved,
        server_default=HistoricalPlayerResolutionState.unresolved.value,
        index=True,
    )
    canonical_player_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("players.id", ondelete="SET NULL"), nullable=True, index=True
    )
    confidence_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    mapping_method: Mapped[str | None] = mapped_column(String(64), nullable=True)
    reviewed_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    reviewed_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    manual_override: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default="false"
    )
    first_seen: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    match_references: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    competition_references: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    provenance_references: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list
    )
    alias_references: Mapped[list[str]] = mapped_column(JSON, nullable=False, default=list)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_hist_source_player_unique_key",
            "source_system",
            "source_schema",
            "normalized_name",
            unique=True,
        ),
    )


class HistoricalSourcePlayerAlias(Base):
    __tablename__ = "historical_source_player_aliases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_player_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("historical_source_player_registry.source_player_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    alias_name: Mapped[str] = mapped_column(String(255), nullable=False)
    normalized_alias: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    source_schema: Mapped[str] = mapped_column(String(64), nullable=False)
    source_system: Mapped[str] = mapped_column(String(64), nullable=False)
    provenance_reference: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    first_seen: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )

    __table_args__ = (
        Index(
            "ix_hist_source_player_alias_unique",
            "source_player_id",
            "normalized_alias",
            "source_schema",
            "source_system",
            unique=True,
        ),
    )


class HistoricalPlayerResolutionQueue(Base):
    __tablename__ = "historical_player_resolution_queue"

    id: Mapped[str] = mapped_column(
        String, primary_key=True, default=lambda: str(uuid.uuid4()), nullable=False
    )
    source_player_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("historical_source_player_registry.source_player_id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
        index=True,
    )
    queue_state: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    reason: Mapped[str] = mapped_column(String(128), nullable=False, default="unresolved")
    resolution_snapshot: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    created_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    last_seen: Mapped[dt.datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    resolved_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)


# ---------------------------------------------------------------------------
# Phase 8C — AI Insight Review
# ---------------------------------------------------------------------------


class AiInsightReviewState(str, enum.Enum):
    """Review state lifecycle for an AI-generated insight."""

    pending = "pending"
    """Awaiting reviewer action (default for requires_review outputs)."""

    approved = "approved"
    """Approved for internal-use distribution."""

    rejected = "rejected"
    """Blocked / rejected — must not be distributed."""

    changes_requested = "changes_requested"
    """Reviewer has requested revisions before approval."""

    flagged = "flagged"
    """Flagged as containing an unsafe claim or unsupported language."""


class AiInsightFeedbackType(str, enum.Enum):
    """Discrete feedback signal attached to a review action."""

    useful = "useful"
    not_useful = "not_useful"
    unsafe = "unsafe"
    unsupported_claim = "unsupported_claim"


class AiInsightReview(Base):
    """
    Persistent audit record for a reviewer's decision on an AI-generated insight.

    Phase 8C — Governance rule:
        This table stores advisory review metadata only.  It must never be
        used to write back to official scoring, player stats, match results,
        DLS calculations, or any other official cricket truth column.

    One row is created per reviewer action.  The latest row for a given
    (insight_type, insight_id) pair represents the current review state.
    """

    __tablename__ = "ai_insight_reviews"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
        nullable=False,
    )

    # Insight identity
    insight_type: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
        comment="AI output type: summary, insight, commentary, recommendation, report, draft",
        index=True,
    )
    insight_id: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        comment="Logical ID for the insight (e.g. match_id, player_id)",
        index=True,
    )

    # Reviewer identity + org at time of review
    reviewer_id: Mapped[str] = mapped_column(
        String, ForeignKey("users.id", ondelete="SET NULL"), nullable=False, index=True
    )
    reviewer_org_id: Mapped[str | None] = mapped_column(
        String, nullable=True, comment="Org at time of review (snapshot)"
    )

    # Review decision
    review_state: Mapped[AiInsightReviewState] = mapped_column(
        String(64),
        nullable=False,
        default=AiInsightReviewState.pending.value,
        index=True,
    )
    feedback_type: Mapped[AiInsightFeedbackType | None] = mapped_column(
        String(64),
        nullable=True,
    )
    note: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Optional reviewer note or change request text",
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

    __table_args__ = (
        Index("ix_ai_insight_review_type_id", "insight_type", "insight_id"),
    )
