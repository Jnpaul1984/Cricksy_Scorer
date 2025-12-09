"""
AI Player Insights Service.

This module provides AI-style insights for player performance based on
their profile stats and recent form entries.

TODO: Replace rule-based logic with actual LLM integration for richer insights.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.sql_app.models import PlayerForm, PlayerProfile

# ---------------------------------------------------------------------------
# Pydantic Schemas
# ---------------------------------------------------------------------------


TrendType = Literal["improving", "declining", "mixed", "flat"]


class RecentForm(BaseModel):
    """Recent form statistics for a player."""

    matches_considered: int
    recent_runs: list[int]
    average: float
    trend: TrendType


class PlayerAiInsights(BaseModel):
    """AI-generated insights for a player."""

    player_id: str
    player_name: str
    summary: str
    strengths: list[str]
    weaknesses: list[str]
    recent_form: RecentForm
    tags: list[str]
    generated_at: datetime


# ---------------------------------------------------------------------------
# Helper: Infer trend from run sequence
# ---------------------------------------------------------------------------


def _infer_trend(runs: list[int]) -> TrendType:
    """
    Infer form trend from a sequence of recent runs.

    Compares average of first half vs second half of the sequence.
    """
    if len(runs) < 3:
        return "mixed"

    mid = len(runs) // 2
    first_avg = sum(runs[:mid]) / max(mid, 1)
    last_avg = sum(runs[mid:]) / max(len(runs) - mid, 1)
    diff = last_avg - first_avg

    if diff > 8:
        return "improving"
    if diff < -8:
        return "declining"
    if abs(diff) <= 3:
        return "flat"
    return "mixed"


# ---------------------------------------------------------------------------
# Main Service Function
# ---------------------------------------------------------------------------


async def build_player_ai_insights(
    db: AsyncSession,
    player_id: str,
) -> PlayerAiInsights:
    """
    Build AI-style insights for a player based on their profile and form data.

    This is a rule-based V1 implementation. The function:
    1. Fetches player profile with form entries
    2. Analyzes recent form trends
    3. Derives strengths/weaknesses from aggregate stats
    4. Generates a summary and tags

    TODO: Replace rule-based logic with actual LLM call for richer insights.

    Args:
        db: Async database session
        player_id: The player's UUID string

    Returns:
        PlayerAiInsights with summary, strengths, weaknesses, form, and tags

    Raises:
        ValueError: If player not found
    """
    # 1) Fetch player profile with form entries
    result = await db.execute(
        select(PlayerProfile)
        .where(PlayerProfile.player_id == player_id)
        .options(selectinload(PlayerProfile.form_entries))
    )
    profile = result.scalar_one_or_none()

    if profile is None:
        raise ValueError(f"Player {player_id} not found")

    # 2) Get recent form entries (sorted by period end, descending)
    form_entries: list[PlayerForm] = sorted(
        profile.form_entries,
        key=lambda f: f.period_end,
        reverse=True,
    )[
        :8
    ]  # Last 8 form periods

    # Extract runs from form entries (reverse to chronological order)
    recent_runs = [f.runs for f in reversed(form_entries)]
    matches_considered = sum(f.matches_played for f in form_entries)

    # Calculate average and trend
    if recent_runs:
        avg = sum(recent_runs) / len(recent_runs)
        trend = _infer_trend(recent_runs)
    else:
        # Fall back to profile stats if no form entries
        avg = profile.batting_average
        trend = "flat"
        # Use profile matches as a proxy
        matches_considered = profile.total_matches

    # 3) Derive strengths and weaknesses from profile stats
    strengths: list[str] = []
    weaknesses: list[str] = []
    tags: list[str] = []

    # TODO: Replace below rules with real analytics + LLM reasoning.

    # Batting analysis
    if profile.total_innings_batted >= 5:
        if profile.batting_average >= 35:
            strengths.append(
                f"Strong batting average of {profile.batting_average:.1f} "
                f"across {profile.total_innings_batted} innings."
            )
            tags.append("reliable_batter")

        if profile.strike_rate >= 130:
            strengths.append(
                f"Aggressive batting style with a strike rate of {profile.strike_rate:.1f}."
            )
            tags.append("aggressive")
        elif profile.strike_rate < 100 and profile.total_balls_faced >= 50:
            weaknesses.append(
                f"Relatively slow strike rate ({profile.strike_rate:.1f}). "
                "May need to rotate strike better."
            )
            tags.append("anchor")

        if profile.total_sixes >= 10:
            strengths.append(f"Power hitter with {profile.total_sixes} sixes to their name.")
            tags.append("power_hitter")

        if profile.centuries >= 1:
            strengths.append(
                f"Has scored {profile.centuries} century/centuries - "
                "shows ability to build big innings."
            )
            tags.append("match_winner")

        if profile.times_out > 0:
            conversion_rate = (
                (profile.half_centuries + profile.centuries) / profile.times_out
            ) * 100
            if conversion_rate < 15 and profile.total_innings_batted >= 10:
                weaknesses.append("Struggles to convert starts into big scores.")
                tags.append("inconsistent")

    # Bowling analysis
    if profile.total_innings_bowled >= 3:
        if profile.total_wickets >= 10:
            if profile.bowling_average <= 25:
                strengths.append(
                    f"Effective bowler with {profile.total_wickets} wickets "
                    f"at an average of {profile.bowling_average:.1f}."
                )
                tags.append("strike_bowler")
            else:
                strengths.append(f"Regular wicket-taker with {profile.total_wickets} wickets.")

        if profile.economy_rate <= 6.5 and profile.total_overs_bowled >= 10:
            strengths.append(f"Economical bowling with an economy of {profile.economy_rate:.2f}.")
            tags.append("economical")
        elif profile.economy_rate >= 9.0 and profile.total_overs_bowled >= 10:
            weaknesses.append(f"Economy rate of {profile.economy_rate:.2f} is on the higher side.")
            tags.append("expensive")

        if profile.five_wicket_hauls >= 1:
            strengths.append(
                f"Match-winning ability - {profile.five_wicket_hauls} five-wicket haul(s)."
            )

    # Fielding analysis
    total_fielding = profile.catches + profile.stumpings + profile.run_outs
    if total_fielding >= 5:
        strengths.append(
            f"Solid fielder with {total_fielding} dismissals "
            f"({profile.catches} catches, {profile.stumpings} stumpings, "
            f"{profile.run_outs} run-outs)."
        )
        tags.append("good_fielder")

    # Form-based analysis
    if trend == "improving":
        strengths.append("Recent form is trending upwards - building momentum.")
        tags.append("in_form")
    elif trend == "declining":
        weaknesses.append("Recent form has dipped compared to earlier performances.")
        tags.append("out_of_form")

    # Check for ducks in recent runs
    if recent_runs and any(r == 0 for r in recent_runs):
        duck_count = sum(1 for r in recent_runs if r == 0)
        if duck_count >= 2:
            weaknesses.append(
                f"{duck_count} low scores (including potential ducks) in recent form periods."
            )

    # Ensure we have at least one strength/weakness
    if not strengths:
        strengths.append("Solid foundation to build on with more game time.")
    if not weaknesses:
        weaknesses.append("No major weaknesses detected from available data.")

    # 4) Build summary
    if matches_considered > 0:
        summary = (
            f"{profile.player_name} has played {profile.total_matches} matches, "
            f"scoring {profile.total_runs_scored} runs"
        )
        if profile.total_wickets > 0:
            summary += f" and taking {profile.total_wickets} wickets"
        summary += f". Recent form trend: {trend}."
    else:
        summary = (
            f"{profile.player_name} has limited recent data. "
            f"Career stats: {profile.total_runs_scored} runs in {profile.total_matches} matches."
        )

    # 5) Build response
    recent_form = RecentForm(
        matches_considered=matches_considered,
        recent_runs=recent_runs,
        average=round(avg, 1),
        trend=trend,
    )

    return PlayerAiInsights(
        player_id=player_id,
        player_name=profile.player_name,
        summary=summary,
        strengths=strengths,
        weaknesses=weaknesses,
        recent_form=recent_form,
        tags=tags,
        generated_at=datetime.now(UTC),
    )
