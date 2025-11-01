from __future__ import annotations

import datetime as dt
import enum
import uuid
from typing import Any, TypedDict

from pydantic import BaseModel
from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy import (
    Enum as SAEnum,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base

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
    id: Mapped[str] = mapped_column(String, primary_key=True, index=True)

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

    # Relationship backref from GameContributor is set below
    contributors: Mapped[list[GameContributor]] = relationship(
        back_populates="game", cascade="all, delete-orphan"
    )

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

    __table_args__ = (
        Index("ix_player_profiles_total_runs", "total_runs_scored"),
        Index("ix_player_profiles_total_wickets", "total_wickets"),
        Index("ix_player_profiles_batting_avg", "total_runs_scored", "times_out"),
    )

    @property
    def batting_average(self) -> float:
        """Calculate batting average: total runs / times out."""
        return round(self.total_runs_scored / self.times_out, 2) if self.times_out > 0 else float(self.total_runs_scored)

    @property
    def strike_rate(self) -> float:
        """Calculate strike rate: (total runs / balls faced) * 100."""
        return round((self.total_runs_scored / self.total_balls_faced) * 100, 2) if self.total_balls_faced > 0 else 0.0

    @property
    def bowling_average(self) -> float:
        """Calculate bowling average: runs conceded / wickets taken."""
        return round(self.total_runs_conceded / self.total_wickets, 2) if self.total_wickets > 0 else float(self.total_runs_conceded)

    @property
    def economy_rate(self) -> float:
        """Calculate economy rate: runs conceded / overs bowled."""
        return round(self.total_runs_conceded / self.total_overs_bowled, 2) if self.total_overs_bowled > 0 else 0.0


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
        String, ForeignKey("player_profiles.player_id", ondelete="CASCADE"), index=True, nullable=False
    )
    game_id: Mapped[str | None] = mapped_column(
        String, ForeignKey("games.id", ondelete="SET NULL"), index=True, nullable=True
    )

    achievement_type: Mapped[AchievementType] = mapped_column(
        SAEnum(AchievementType, name="achievement_type"), nullable=False
    )
    title: Mapped[str] = mapped_column(String, nullable=False)  # e.g., "Century Maker"
    description: Mapped[str] = mapped_column(Text, nullable=False)  # e.g., "Scored 105 runs vs Team B"
    badge_icon: Mapped[str | None] = mapped_column(String, nullable=True)  # emoji or icon class

    earned_at: Mapped[dt.datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Optional: achievement details (runs scored, wickets taken, etc.)
    achievement_metadata: Mapped[dict[str, Any]] = mapped_column(JSON, default=_empty_dict, nullable=False)

    # Relationships
    player_profile: Mapped[PlayerProfile] = relationship(back_populates="achievements")

    __table_args__ = (
        Index("ix_player_achievements_player_id", "player_id"),
        Index("ix_player_achievements_type", "achievement_type"),
        Index("ix_player_achievements_earned_at", "earned_at"),
    )
