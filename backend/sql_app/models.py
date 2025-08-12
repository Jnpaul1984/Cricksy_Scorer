from sqlalchemy import (
    Column, Integer, String, JSON, Boolean, Text, Enum as SAEnum,
    ForeignKey, Index, DateTime, func
)
from sqlalchemy.orm import relationship
from .database import Base
import enum
import uuid

class Game(Base):
    __tablename__ = "games"

    id = Column(String, primary_key=True, index=True)

    # Existing team JSON (name + players[{id,name}, ...])
    team_a = Column(JSON)
    team_b = Column(JSON)

    # --- Match Setup Fields ---
    match_type = Column(String, default="custom", nullable=False)  # e.g., T20, ODI, Test, custom
    overs_limit = Column(Integer, nullable=True)                   # None for unlimited
    days_limit = Column(Integer, nullable=True)                    # For multi-day matches
    dls_enabled = Column(Boolean, default=False)                   # Duckworth-Lewis-Stern method toggle
    interruptions = Column(JSON, default=[])                       # List of interruption events
    overs_per_day = Column(Integer, nullable=True)

    toss_winner_team = Column(String)
    decision = Column(String)
    batting_team_name = Column(String)
    bowling_team_name = Column(String)

    status = Column(String, default="pending_start")
    total_runs = Column(Integer, default=0)
    total_wickets = Column(Integer, default=0)
    overs_completed = Column(Integer, default=0)
    balls_this_over = Column(Integer, default=0)
    current_striker_id = Column(String, nullable=True)
    current_non_striker_id = Column(String, nullable=True)

    # --- Team roles (NEW) ---
    team_a_captain_id = Column(Text, nullable=True)
    team_a_keeper_id  = Column(Text, nullable=True)
    team_b_captain_id = Column(Text, nullable=True)
    team_b_keeper_id  = Column(Text, nullable=True)

    # --- Deliveries ledger ---
    deliveries = Column(JSON, default=[])  # per-ball dicts with dismissal, extras, etc.

    batting_scorecard = Column(JSON, default={})
    bowling_scorecard = Column(JSON, default={})
    current_inning = Column(Integer, default=1)
    first_inning_summary = Column(JSON, nullable=True)
    target = Column(Integer, nullable=True)
    result = Column(String, nullable=True)

# ===== Game Staff / Contributors (NEW) =====

class GameContributorRoleEnum(str, enum.Enum):
    scorer = "scorer"
    commentary = "commentary"
    analytics = "analytics"

class GameContributor(Base):
    __tablename__ = "game_contributors"

    id = Column(Integer, primary_key=True)
    game_id = Column(String, ForeignKey("games.id", ondelete="CASCADE"), index=True, nullable=False)
    user_id = Column(Text, nullable=False)
    role = Column(SAEnum(GameContributorRoleEnum, name="game_contributor_role"), nullable=False)
    display_name = Column(Text, nullable=True)

    game = relationship("Game", backref="contributors")

Index(
    "ix_game_contributors_unique",
    GameContributor.game_id, GameContributor.user_id, GameContributor.role,
    unique=True
)

# ===== Sponsors (NEW) =====

class Sponsor(Base):
    __tablename__ = "sponsors"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)

    # stored as relative path under STATIC_DIR, e.g. "sponsors/<uuid>.svg"
    logo_path = Column(String, nullable=False)

    click_url = Column(Text, nullable=True)
    weight = Column(Integer, nullable=False, default=1)       # 1..5
    surfaces = Column(JSON, default=["all"])                  # e.g., ["all"] or ["viewer","embed"]

    start_at = Column(DateTime(timezone=True), nullable=True) # UTC
    end_at   = Column(DateTime(timezone=True), nullable=True) # UTC

    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    __table_args__ = (
        Index("ix_sponsors_weight", "weight"),
        Index("ix_sponsors_active_window", "start_at", "end_at"),
    )

# ===== Sponsor Impressions (NEW) =====
# Minimal proof-of-play ledger
class SponsorImpression(Base):
    __tablename__ = "sponsor_impressions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    game_id = Column(String, ForeignKey("games.id", ondelete="CASCADE"), nullable=False, index=True)
    sponsor_id = Column(String, ForeignKey("sponsors.id", ondelete="CASCADE"), nullable=False)
    at = Column(DateTime(timezone=True), nullable=False, server_default=func.now())

    __table_args__ = (
        Index("ix_sponsor_impressions_sponsor_id", "sponsor_id"),
        Index("ix_sponsor_impressions_at", "at"),
    )
