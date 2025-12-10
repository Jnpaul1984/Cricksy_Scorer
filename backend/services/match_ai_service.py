"""
Match AI Commentary Service.

Generates mock AI commentary for a match based on match metadata
(powerplay swings, wickets, boundaries). No real LLM call yet.

TODO: Replace mock implementation with actual LLM call.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from backend.sql_app import models
from backend.sql_app.match_ai import CommentaryItem, MatchAiCommentaryResponse


class MatchAiService:
    """Service for generating AI commentary for cricket matches."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def get_match_commentary(self, match_id: str) -> MatchAiCommentaryResponse:
        """
        Generate mock AI commentary for a match.

        Args:
            match_id: The game/match ID to generate commentary for.

        Returns:
            MatchAiCommentaryResponse with mock commentary entries.

        Raises:
            ValueError: If the match is not found.
        """
        # Fetch the game
        result = await self.db.execute(
            select(models.Game).where(models.Game.id == match_id)
        )
        game = result.scalar_one_or_none()

        if game is None:
            raise ValueError(f"Match {match_id} not found")

        # Generate mock commentary from match state
        commentary_items = self._generate_mock_commentary(game)

        return MatchAiCommentaryResponse(
            match_id=match_id,
            commentary=commentary_items,
        )

    def _generate_mock_commentary(self, game: models.Game) -> list[CommentaryItem]:
        """
        Generate mock commentary based on match metadata.

        Analyzes deliveries for:
        - Powerplay events
        - Wickets
        - Boundaries (4s and 6s)
        - Milestone overs
        """
        commentary: list[CommentaryItem] = []
        deliveries: list[dict[str, Any]] = game.deliveries or []
        overs_limit = game.overs_limit

        # Derive team names
        team_a_name = (game.team_a or {}).get("name", "Team A")
        team_b_name = (game.team_b or {}).get("name", "Team B")
        batting_team = game.batting_team_name or team_a_name

        # Track state for commentary generation
        total_runs = 0
        total_wickets = 0
        ball_index = 0

        for delivery in deliveries:
            over_number = delivery.get("over_number", 0)
            ball_number = delivery.get("ball_number", 0)
            runs = delivery.get("runs_scored", 0) or delivery.get("runs_off_bat", 0)
            is_wicket = delivery.get("is_wicket", False)
            extra_type = delivery.get("extra_type") or delivery.get("extra")

            total_runs += runs
            if is_wicket:
                total_wickets += 1

            # Calculate over as decimal (e.g., 5.3)
            over_decimal = float(over_number) + (ball_number / 10) if ball_number else float(over_number)

            # Generate commentary for significant events
            item = self._generate_event_commentary(
                over_decimal=over_decimal,
                ball_index=ball_index,
                runs=runs,
                is_wicket=is_wicket,
                extra_type=extra_type,
                total_runs=total_runs,
                total_wickets=total_wickets,
                over_number=over_number,
                overs_limit=overs_limit,
                batting_team=batting_team,
                delivery=delivery,
            )

            if item:
                commentary.append(item)

            ball_index += 1

        # Add match state commentary if no deliveries
        if not deliveries:
            commentary.append(
                CommentaryItem(
                    over=None,
                    ball_index=None,
                    event_tags=["match_start"],
                    text=f"Welcome to the match! {team_a_name} vs {team_b_name}. No deliveries recorded yet.",
                    tone="neutral",
                    created_at=datetime.now(UTC).isoformat(),
                )
            )

        return commentary

    def _generate_event_commentary(
        self,
        over_decimal: float,
        ball_index: int,
        runs: int,
        is_wicket: bool,
        extra_type: str | None,
        total_runs: int,
        total_wickets: int,
        over_number: int,
        overs_limit: int | None,
        batting_team: str,
        delivery: dict[str, Any],
    ) -> CommentaryItem | None:
        """Generate commentary for a specific delivery event."""
        event_tags: list[str] = []
        tone: str = "neutral"
        text: str | None = None

        # Determine phase
        phase = self._derive_phase(over_number, overs_limit)
        if phase:
            event_tags.append(phase)

        # Wicket - always generate commentary
        if is_wicket:
            event_tags.append("wicket")
            dismissal_type = delivery.get("dismissal_type", "out")
            tone = "critical"
            text = f"WICKET! {batting_team} lose their {self._ordinal(total_wickets)} wicket. Score: {total_runs}/{total_wickets}"

        # Boundary - six
        elif runs == 6:
            event_tags.extend(["boundary", "six"])
            tone = "hype"
            text = f"SIX! Massive hit! {batting_team} now at {total_runs}/{total_wickets}"

        # Boundary - four
        elif runs == 4:
            event_tags.extend(["boundary", "four"])
            tone = "hype"
            text = f"FOUR! Excellent shot. {batting_team} move to {total_runs}/{total_wickets}"

        # Powerplay end (over 6 in T20, over 10 in ODI)
        elif phase == "powerplay" and over_number == (6 if overs_limit and overs_limit <= 20 else 10) and ball_index > 0:
            if ball_index % 6 == 5:  # Last ball of the over
                event_tags.append("powerplay_end")
                text = f"End of the powerplay! {batting_team}: {total_runs}/{total_wickets}"
                tone = "neutral"

        # Extras
        elif extra_type:
            event_tags.append("extra")
            event_tags.append(extra_type)
            # Only generate commentary for extras occasionally (not too verbose)
            return None

        # No significant event
        if text is None:
            return None

        return CommentaryItem(
            over=over_decimal,
            ball_index=ball_index,
            event_tags=event_tags,
            text=text,
            tone=tone,  # type: ignore[arg-type]
            created_at=datetime.now(UTC).isoformat(),
        )

    def _derive_phase(self, over_number: int, overs_limit: int | None) -> str | None:
        """Derive match phase from over number."""
        if overs_limit is None:
            return None

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

    def _ordinal(self, n: int) -> str:
        """Convert number to ordinal string (1st, 2nd, 3rd, etc.)."""
        if 11 <= n % 100 <= 13:
            suffix = "th"
        else:
            suffix = {1: "st", 2: "nd", 3: "rd"}.get(n % 10, "th")
        return f"{n}{suffix}"


async def get_match_ai_commentary(
    db: AsyncSession, match_id: str
) -> MatchAiCommentaryResponse:
    """
    Convenience function to get AI commentary for a match.

    Args:
        db: Database session
        match_id: The match/game ID

    Returns:
        MatchAiCommentaryResponse with commentary entries
    """
    service = MatchAiService(db)
    return await service.get_match_commentary(match_id)
