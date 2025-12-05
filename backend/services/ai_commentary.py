"""
AI Commentary Service for Cricket Deliveries.

This module provides rule-based commentary generation for individual deliveries.
It analyzes the delivery context (runs, wickets, phase, players) and generates
short AI-style commentary strings.

TODO: Replace rule-based templates with actual LLM call using match/delivery context.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel

# ---------------------------------------------------------------------------
# Pydantic Schemas (co-located for simplicity; could move to schemas/ later)
# ---------------------------------------------------------------------------


class DeliveryContextRequest(BaseModel):
    """Request payload for generating AI commentary for a delivery."""

    game_id: str
    over_number: int
    ball_number: int
    tone: str = "neutral"  # "neutral" | "hype" | "coach"


class AiCommentaryResponse(BaseModel):
    """Response payload with generated AI commentary."""

    game_id: str
    over_number: int
    ball_number: int
    commentary: str
    tone: str
    tags: list[str]
    generated_at: datetime


# ---------------------------------------------------------------------------
# Helper: Derive phase from over number
# ---------------------------------------------------------------------------


def _derive_phase(over_number: int, overs_limit: int | None) -> str:
    """Derive match phase from over number."""
    if overs_limit is None:
        # Test match or unlimited: just use generic phases
        if over_number <= 10:
            return "early"
        elif over_number <= 40:
            return "middle"
        else:
            return "late"

    # Limited overs format
    if overs_limit <= 20:
        # T20 phases
        if over_number <= 6:
            return "powerplay"
        elif over_number <= 15:
            return "middle"
        else:
            return "death"
    else:
        # ODI/50-over phases
        if over_number <= 10:
            return "powerplay"
        elif over_number <= 40:
            return "middle"
        else:
            return "death"


# ---------------------------------------------------------------------------
# Helper: Find delivery in game.deliveries JSON list
# ---------------------------------------------------------------------------


def _find_delivery(
    deliveries: list[dict[str, Any]],
    over_number: int,
    ball_number: int,
) -> dict[str, Any] | None:
    """Find a specific delivery in the deliveries list."""
    for d in deliveries:
        if d.get("over_number") == over_number and d.get("ball_number") == ball_number:
            return d
    return None


# ---------------------------------------------------------------------------
# Helper: Get player name from game team data
# ---------------------------------------------------------------------------


def _get_player_name(
    player_id: str | None,
    team_a: dict[str, Any],
    team_b: dict[str, Any],
) -> str:
    """Look up a player name from team rosters."""
    if not player_id:
        return "Unknown"

    # Search in both teams
    for team in [team_a, team_b]:
        players = team.get("players", [])
        for p in players:
            if isinstance(p, dict) and p.get("id") == player_id:
                return p.get("name", "Unknown")
            elif isinstance(p, str) and p == player_id:
                return player_id  # fallback to ID if no name

    return "Unknown"


# ---------------------------------------------------------------------------
# Main Commentary Builder
# ---------------------------------------------------------------------------


def build_delivery_commentary(
    game: Any,  # Game model instance
    payload: DeliveryContextRequest,
) -> AiCommentaryResponse:
    """
    Build AI-style commentary for a specific delivery.

    This is a rule-based V1 implementation. The function:
    1. Finds the delivery in game.deliveries
    2. Extracts context (runs, wicket, phase, players)
    3. Generates a template-based commentary string
    4. Returns structured response with tags

    TODO: Replace rule-based commentary with actual LLM call using match/delivery context.

    Args:
        game: The Game model instance with deliveries data
        payload: Request with game_id, over_number, ball_number, tone

    Returns:
        AiCommentaryResponse with generated commentary

    Raises:
        ValueError: If delivery not found in game
    """
    # 1) Find the delivery
    deliveries: list[dict[str, Any]] = game.deliveries or []
    delivery = _find_delivery(deliveries, payload.over_number, payload.ball_number)

    if delivery is None:
        raise ValueError(
            f"Delivery not found: over {payload.over_number}, ball {payload.ball_number}"
        )

    # 2) Extract context
    runs_off_bat = delivery.get("runs_off_bat", 0) or delivery.get("runs_scored", 0)
    extra_runs = delivery.get("extra_runs", 0)
    total_runs = runs_off_bat + extra_runs
    is_wicket = bool(delivery.get("is_wicket", False))
    is_extra = bool(delivery.get("is_extra", False))
    extra_type = delivery.get("extra_type")
    dismissal_type = delivery.get("dismissal_type")

    # Player IDs
    striker_id = delivery.get("striker_id")
    bowler_id = delivery.get("bowler_id")
    dismissed_id = delivery.get("dismissed_player_id")

    # Get player names
    team_a = game.team_a or {}
    team_b = game.team_b or {}
    striker_name = _get_player_name(striker_id, team_a, team_b)
    bowler_name = _get_player_name(bowler_id, team_a, team_b)
    dismissed_name = _get_player_name(dismissed_id, team_a, team_b) if dismissed_id else None

    # Derive phase
    overs_limit = game.overs_limit
    phase = _derive_phase(payload.over_number, overs_limit)

    # 3) Build commentary using templates
    commentary_parts: list[str] = []
    tone = payload.tone

    # Wicket commentary
    if is_wicket:
        if dismissed_name and dismissed_name != "Unknown":
            if dismissal_type:
                commentary_parts.append(
                    f"{bowler_name} strikes! {dismissed_name} is out {dismissal_type}."
                )
            else:
                commentary_parts.append(f"{bowler_name} removes {dismissed_name}!")
        else:
            commentary_parts.append(f"Wicket! {bowler_name} has broken through.")

        if tone == "hype":
            commentary_parts.append("What a breakthrough!")

    # Boundary commentary
    elif total_runs == 6:
        commentary_parts.append(f"Huge six from {striker_name}!")
        if tone == "hype":
            commentary_parts.append("That's out of the ground!")
        elif tone == "coach":
            commentary_parts.append("Great timing and placement on that shot.")

    elif total_runs == 4:
        commentary_parts.append(f"{striker_name} finds the gap for four.")
        if tone == "coach":
            commentary_parts.append("Good use of the feet there.")

    # Extras
    elif is_extra and extra_type:
        if extra_type == "wd":
            commentary_parts.append(f"Wide from {bowler_name}. {extra_runs} extra(s).")
        elif extra_type == "nb":
            commentary_parts.append(f"No ball! {extra_runs} extra(s) to the total.")
        elif extra_type == "b":
            commentary_parts.append(f"Byes! {extra_runs} runs added.")
        elif extra_type == "lb":
            commentary_parts.append(f"Leg byes. {extra_runs} runs come off the pads.")

    # Dot ball
    elif total_runs == 0:
        commentary_parts.append(f"Dot ball to {striker_name} from {bowler_name}.")
        if tone == "coach":
            commentary_parts.append("Good line and length there.")

    # Regular runs
    else:
        if total_runs == 1:
            commentary_parts.append(f"Single taken by {striker_name}.")
        elif total_runs == 2:
            commentary_parts.append(f"Quick running! Two runs to {striker_name}.")
        elif total_runs == 3:
            commentary_parts.append("Three runs! Excellent running between the wickets.")
        else:
            commentary_parts.append(f"{total_runs} run(s) to {striker_name}.")

    # Add phase context (subtle)
    if phase in ("powerplay", "death") and tone == "coach":
        if phase == "powerplay":
            commentary_parts.append("Field restrictions still in play.")
        else:
            commentary_parts.append("Crucial death-over phase.")

    # TODO: Add more nuance with recent-over context, match situation, win probability, etc.

    commentary = " ".join(commentary_parts)

    # 4) Build tags
    tags: list[str] = []
    if is_wicket:
        tags.append("wicket")
    if total_runs >= 4:
        tags.append("boundary")
    if total_runs == 0 and not is_extra:
        tags.append("dot_ball")
    if is_extra:
        tags.append("extra")
    if phase in ("powerplay", "death"):
        tags.append(f"phase_{phase}")

    # Mark as rule-based for now
    tags.append("rule_based_v1")

    return AiCommentaryResponse(
        game_id=payload.game_id,
        over_number=payload.over_number,
        ball_number=payload.ball_number,
        commentary=commentary,
        tone=tone,
        tags=tags,
        generated_at=datetime.now(UTC),
    )
