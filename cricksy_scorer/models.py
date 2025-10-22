"""Data models for cricket scoring."""

from dataclasses import dataclass, field
from typing import List, Optional


__all__ = ["Player", "MatchConfig", "ScoreResult"]


@dataclass
class Player:
    """Player information.

    TODO: Expand with full player details (batting/bowling stats, etc.)
    """

    name: str
    player_id: Optional[str] = None
    is_captain: bool = False
    is_wicketkeeper: bool = False


@dataclass
class MatchConfig:
    """Match configuration settings.

    TODO: Move full match configuration logic here in follow-up PR.
    """

    match_id: Optional[str] = None
    team1_name: str = "Team 1"
    team2_name: str = "Team 2"
    overs: int = 20
    team1_players: List[Player] = field(default_factory=list)
    team2_players: List[Player] = field(default_factory=list)


@dataclass
class ScoreResult:
    """Result of scoring a match.

    TODO: Expand with detailed match statistics in follow-up PR.
    """

    match_id: Optional[str] = None
    team1_score: int = 0
    team2_score: int = 0
    team1_wickets: int = 0
    team2_wickets: int = 0
    winner: Optional[str] = None
    status: str = "pending"
