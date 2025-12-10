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
from backend.sql_app.match_ai import (
    CommentaryItem,
    DecisivePhaseSummary,
    MatchAiCommentaryResponse,
    MatchAiSummaryResponse,
    MatchAiSummaryTeam,
    MomentumShiftSummary,
    PlayerHighlightSummary,
)


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

    # -------------------------------------------------------------------------
    # Match AI Summary (for analyst case study view)
    # -------------------------------------------------------------------------

    async def build_match_ai_summary(self, match_id: str) -> MatchAiSummaryResponse:
        """
        Build a structured AI-style summary for a match case study.

        This is a MOCK implementation - no actual LLM call.
        Generates deterministic summaries based on match data.

        Args:
            match_id: The game/match ID.

        Returns:
            MatchAiSummaryResponse with structured summary data.

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

        # Extract team info
        team_a = game.team_a or {}
        team_b = game.team_b or {}
        team_a_name = team_a.get("name", "Team A")
        team_b_name = team_b.get("name", "Team B")
        team_a_id = str(team_a.get("id", "team_a"))
        team_b_id = str(team_b.get("id", "team_b"))

        # Determine format
        overs_limit = game.overs_limit or 20
        if overs_limit <= 20:
            match_format = "T20"
        elif overs_limit <= 50:
            match_format = "ODI"
        else:
            match_format = "Custom"

        # Analyze deliveries
        deliveries: list[dict[str, Any]] = game.deliveries or []
        analysis = self._analyze_match_deliveries(deliveries, overs_limit)

        # Build team summaries
        teams = self._build_team_summaries(
            game, team_a_id, team_a_name, team_b_id, team_b_name, analysis
        )

        # Build decisive phases
        decisive_phases = self._build_decisive_phases(analysis, teams)

        # Build momentum shifts
        momentum_shifts = self._build_momentum_shifts(analysis, teams)

        # Build player highlights
        player_highlights = self._build_player_highlights(game, teams, analysis)

        # Generate key themes
        key_themes = self._generate_key_themes(analysis, teams)

        # Generate overall summary
        overall_summary = self._generate_overall_summary(game, teams, analysis)

        return MatchAiSummaryResponse(
            match_id=match_id,
            format=match_format,  # type: ignore[arg-type]
            teams=teams,
            key_themes=key_themes,
            decisive_phases=decisive_phases,
            momentum_shifts=momentum_shifts,
            player_highlights=player_highlights,
            overall_summary=overall_summary,
        )

    def _analyze_match_deliveries(
        self, deliveries: list[dict[str, Any]], overs_limit: int
    ) -> dict[str, Any]:
        """Analyze deliveries to extract match statistics."""
        total_runs = 0
        total_wickets = 0
        total_balls = 0
        boundaries_4 = 0
        boundaries_6 = 0

        # Phase-level stats
        powerplay_runs = 0
        powerplay_wickets = 0
        powerplay_balls = 0
        middle_runs = 0
        middle_wickets = 0
        middle_balls = 0
        death_runs = 0
        death_wickets = 0
        death_balls = 0

        # Wicket overs for momentum shifts
        wicket_overs: list[float] = []
        boundary_overs: list[float] = []

        for d in deliveries:
            over_number = d.get("over_number", 0)
            ball_number = d.get("ball_number", 0)
            runs = d.get("runs_scored", 0) or d.get("runs_off_bat", 0) or 0
            is_wicket = d.get("is_wicket", False)

            total_runs += runs
            total_balls += 1

            over_decimal = float(over_number) + (ball_number / 10)

            if is_wicket:
                total_wickets += 1
                wicket_overs.append(over_decimal)

            if runs == 4:
                boundaries_4 += 1
                boundary_overs.append(over_decimal)
            elif runs == 6:
                boundaries_6 += 1
                boundary_overs.append(over_decimal)

            # Phase allocation
            phase = self._derive_phase(over_number, overs_limit)
            if phase == "powerplay":
                powerplay_runs += runs
                powerplay_balls += 1
                if is_wicket:
                    powerplay_wickets += 1
            elif phase == "middle":
                middle_runs += runs
                middle_balls += 1
                if is_wicket:
                    middle_wickets += 1
            elif phase == "death":
                death_runs += runs
                death_balls += 1
                if is_wicket:
                    death_wickets += 1

        return {
            "total_runs": total_runs,
            "total_wickets": total_wickets,
            "total_balls": total_balls,
            "total_overs": total_balls / 6 if total_balls else 0,
            "boundaries_4": boundaries_4,
            "boundaries_6": boundaries_6,
            "powerplay": {
                "runs": powerplay_runs,
                "wickets": powerplay_wickets,
                "balls": powerplay_balls,
                "run_rate": (powerplay_runs / (powerplay_balls / 6)) if powerplay_balls else 0,
            },
            "middle": {
                "runs": middle_runs,
                "wickets": middle_wickets,
                "balls": middle_balls,
                "run_rate": (middle_runs / (middle_balls / 6)) if middle_balls else 0,
            },
            "death": {
                "runs": death_runs,
                "wickets": death_wickets,
                "balls": death_balls,
                "run_rate": (death_runs / (death_balls / 6)) if death_balls else 0,
            },
            "wicket_overs": wicket_overs,
            "boundary_overs": boundary_overs,
        }

    def _build_team_summaries(
        self,
        game: models.Game,
        team_a_id: str,
        team_a_name: str,
        team_b_id: str,
        team_b_name: str,
        analysis: dict[str, Any],
    ) -> list[MatchAiSummaryTeam]:
        """Build team summary objects."""
        # Determine result from game state
        result_str = game.result or ""
        team_a_result: str = "no_result"
        team_b_result: str = "no_result"

        if "tie" in result_str.lower():
            team_a_result = "tied"
            team_b_result = "tied"
        elif team_a_name.lower() in result_str.lower() and "won" in result_str.lower():
            team_a_result = "won"
            team_b_result = "lost"
        elif team_b_name.lower() in result_str.lower() and "won" in result_str.lower():
            team_a_result = "lost"
            team_b_result = "won"

        # For now, assume team A batted (simplified)
        team_a_runs = analysis["total_runs"]
        team_a_wickets = analysis["total_wickets"]
        team_a_overs = analysis["total_overs"]

        team_a_stats = [
            f"{analysis['boundaries_4']} fours, {analysis['boundaries_6']} sixes",
            f"Run rate: {(team_a_runs / team_a_overs):.2f}" if team_a_overs else "N/A",
        ]

        teams = [
            MatchAiSummaryTeam(
                team_id=team_a_id,
                team_name=team_a_name,
                result=team_a_result,  # type: ignore[arg-type]
                total_runs=team_a_runs,
                wickets_lost=team_a_wickets,
                overs_faced=round(team_a_overs, 1),
                key_stats=team_a_stats,
            ),
            MatchAiSummaryTeam(
                team_id=team_b_id,
                team_name=team_b_name,
                result=team_b_result,  # type: ignore[arg-type]
                total_runs=0,  # Second innings not tracked in this mock
                wickets_lost=0,
                overs_faced=0.0,
                key_stats=["Second innings data not available"],
            ),
        ]
        return teams

    def _build_decisive_phases(
        self, analysis: dict[str, Any], teams: list[MatchAiSummaryTeam]
    ) -> list[DecisivePhaseSummary]:
        """Build decisive phase summaries."""
        phases: list[DecisivePhaseSummary] = []
        team_name = teams[0].team_name if teams else "Batting team"

        # Powerplay
        pp = analysis["powerplay"]
        if pp["balls"] > 0:
            # Impact score: high run rate = positive, wickets = negative
            pp_impact = min(100, max(-100, (pp["run_rate"] - 7.0) * 10 - pp["wickets"] * 15))
            phases.append(
                DecisivePhaseSummary(
                    phase_id="powerplay_1",
                    innings=1,
                    label="Powerplay",
                    over_range=(0.1, 6.0),
                    impact_score=round(pp_impact, 1),
                    narrative=f"{team_name} scored {pp['runs']} runs for {pp['wickets']} wickets in the powerplay at {pp['run_rate']:.2f} RPO.",
                )
            )

        # Middle overs
        mid = analysis["middle"]
        if mid["balls"] > 0:
            mid_impact = min(100, max(-100, (mid["run_rate"] - 6.0) * 10 - mid["wickets"] * 10))
            phases.append(
                DecisivePhaseSummary(
                    phase_id="middle_1",
                    innings=1,
                    label="Middle Overs",
                    over_range=(6.1, 15.0),
                    impact_score=round(mid_impact, 1),
                    narrative=f"Through the middle overs, {team_name} accumulated {mid['runs']} runs losing {mid['wickets']} wickets.",
                )
            )

        # Death overs
        death = analysis["death"]
        if death["balls"] > 0:
            death_impact = min(100, max(-100, (death["run_rate"] - 9.0) * 8 - death["wickets"] * 12))
            phases.append(
                DecisivePhaseSummary(
                    phase_id="death_1",
                    innings=1,
                    label="Death Overs",
                    over_range=(15.1, 20.0),
                    impact_score=round(death_impact, 1),
                    narrative=f"In the death overs, {team_name} scored {death['runs']} runs at {death['run_rate']:.2f} RPO.",
                )
            )

        return phases

    def _build_momentum_shifts(
        self, analysis: dict[str, Any], teams: list[MatchAiSummaryTeam]
    ) -> list[MomentumShiftSummary]:
        """Build momentum shift summaries based on wickets."""
        shifts: list[MomentumShiftSummary] = []
        wicket_overs = analysis.get("wicket_overs", [])
        bowling_team_id = teams[1].team_id if len(teams) > 1 else "bowling_team"
        bowling_team_name = teams[1].team_name if len(teams) > 1 else "Bowling team"

        # Detect wicket clusters (2+ wickets in 2 overs)
        for i, over in enumerate(wicket_overs):
            nearby = [o for o in wicket_overs if abs(o - over) <= 2.0]
            if len(nearby) >= 2 and i == wicket_overs.index(min(nearby)):
                shifts.append(
                    MomentumShiftSummary(
                        shift_id=f"shift_{i}",
                        innings=1,
                        over=over,
                        description=f"Wicket cluster around over {over:.1f} shifted momentum to {bowling_team_name}.",
                        impact_delta=round(-15.0 * len(nearby), 1),
                        team_benefiting_id=bowling_team_id,
                    )
                )

        return shifts[:3]  # Limit to top 3 shifts

    def _build_player_highlights(
        self,
        game: models.Game,
        teams: list[MatchAiSummaryTeam],
        analysis: dict[str, Any],
    ) -> list[PlayerHighlightSummary]:
        """Build player highlight summaries."""
        highlights: list[PlayerHighlightSummary] = []
        team_id = teams[0].team_id if teams else "team_a"
        team_name = teams[0].team_name if teams else "Team A"

        # For now, generate mock highlights based on total runs/wickets
        if analysis["total_runs"] > 100:
            highlights.append(
                PlayerHighlightSummary(
                    player_id="top_scorer_1",
                    player_name="Top Scorer",
                    team_id=team_id,
                    role="batter",
                    highlight_type="innings",
                    summary=f"Key contribution in helping {team_name} post a competitive total.",
                )
            )

        if analysis["boundaries_6"] >= 3:
            highlights.append(
                PlayerHighlightSummary(
                    player_id="power_hitter_1",
                    player_name="Power Hitter",
                    team_id=team_id,
                    role="batter",
                    highlight_type="innings",
                    summary=f"Struck {analysis['boundaries_6']} sixes in an explosive display.",
                )
            )

        if analysis["total_wickets"] >= 3:
            bowling_team_id = teams[1].team_id if len(teams) > 1 else "team_b"
            highlights.append(
                PlayerHighlightSummary(
                    player_id="top_bowler_1",
                    player_name="Top Bowler",
                    team_id=bowling_team_id,
                    role="bowler",
                    highlight_type="spell",
                    summary=f"Effective spell helping restrict the opposition to {analysis['total_runs']} runs.",
                )
            )

        return highlights

    def _generate_key_themes(
        self, analysis: dict[str, Any], teams: list[MatchAiSummaryTeam]
    ) -> list[str]:
        """Generate key themes from match analysis."""
        themes: list[str] = []

        # Powerplay performance
        pp = analysis["powerplay"]
        if pp["run_rate"] > 8.0 and pp["wickets"] <= 1:
            themes.append("Powerplay dominance")
        elif pp["wickets"] >= 3:
            themes.append("Early collapse")

        # Death over execution
        death = analysis["death"]
        if death["run_rate"] > 10.0:
            themes.append("Strong death over finish")
        elif death["wickets"] >= 2:
            themes.append("Bowlers fought back at death")

        # Boundary hitting
        if analysis["boundaries_6"] >= 5:
            themes.append("Aggressive six-hitting")
        if analysis["boundaries_4"] >= 10:
            themes.append("Boundary-rich innings")

        # Fall back
        if not themes:
            themes.append("Competitive contest")

        return themes

    def _generate_overall_summary(
        self,
        game: models.Game,
        teams: list[MatchAiSummaryTeam],
        analysis: dict[str, Any],
    ) -> str:
        """Generate an overall match summary."""
        team_a = teams[0] if teams else None
        team_b = teams[1] if len(teams) > 1 else None

        if not team_a:
            return "Match summary not available."

        summary_parts = [
            f"{team_a.team_name} scored {team_a.total_runs}/{team_a.wickets_lost}",
            f"in {team_a.overs_faced} overs.",
        ]

        # Add result if available
        if game.result:
            summary_parts.append(f"Result: {game.result}.")

        # Add key stat
        if analysis["boundaries_6"] >= 3:
            summary_parts.append(f"The innings featured {analysis['boundaries_6']} sixes.")

        return " ".join(summary_parts)


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
