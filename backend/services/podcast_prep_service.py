"""Phase 10T — Podcast Prep Studio: deterministic research-pack service.

Generates structured podcast research packs from existing deterministic data:
- Match-based: uses case study data (innings, key players, venue, result)
- Tournament-based: uses tournament intelligence (standings, champion, facts)
- Archive-based: uses archive explorer (era comparisons, champion history)
- Roster-based: uses current CPL season roster data

All output is deterministic and derived from imported data.
No official standings or invented stats are ever asserted.
AI polish is optional and guarded behind availability checks.

Saved reports are stored in the podcast_prep_reports table.
"""

from __future__ import annotations

import datetime as dt
import unicodedata
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.api.schemas.podcast_prep import (
    ArchivePodcastPackRequest,
    MatchPodcastPackRequest,
    PodcastPrepReportCreate,
    PodcastPrepReportListResponse,
    PodcastPrepReportResponse,
    PodcastPrepReportUpdate,
    PodcastResearchPack,
    PodcastResearchSection,
    RosterPodcastPackRequest,
    TournamentPodcastPackRequest,
)
from backend.sql_app.models import PodcastPrepReport, PodcastPrepTopicType


# ---------------------------------------------------------------------------
# Text helpers (copy quality)
# ---------------------------------------------------------------------------


def _pluralize(n: int, singular: str, plural: str | None = None) -> str:
    """Return correctly pluralised phrase.

    Examples:
        _pluralize(1, "run") → "1 run"
        _pluralize(2, "run") → "2 runs"
        _pluralize(1, "wicket") → "1 wicket"
        _pluralize(2, "wicket") → "2 wickets"
    """
    p = plural if plural is not None else f"{singular}s"
    return f"{n} {singular if n == 1 else p}"


def _format_runs_wickets(runs: int | None, wickets: int | None) -> str:
    """Format innings total with correct grammar.

    Returns e.g. '185/6' (standard cricket notation) with fallback text.
    """
    if runs is None:
        return "total unavailable"
    if wickets is None:
        return f"{runs}"
    return f"{runs}/{wickets}"


def _safe_join(items: list[str], conjunction: str = "and") -> str:
    """Join list items with a natural-language conjunction."""
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return f"{items[0]} {conjunction} {items[1]}"
    return ", ".join(items[:-1]) + f", {conjunction} {items[-1]}"


# ---------------------------------------------------------------------------
# Section builders
# ---------------------------------------------------------------------------


def _build_opening_hook(
    topic_type: str,
    episode_title: str,
    context: str | None,
    competition_label: str | None,
    season_label: str | None,
) -> PodcastResearchSection:
    if topic_type == "match" and context:
        body = f"Welcome back. {context} — let's break down what happened."
    elif topic_type == "tournament" and competition_label:
        season_text = f" {season_label}" if season_label else ""
        body = (
            f"We're looking back at the {competition_label}{season_text} today. "
            "Let's unpack the key moments."
        )
    elif topic_type == "archive":
        body = (
            "Welcome to our historical deep dive. "
            "We're pulling together archive data to tell the story of the game's evolution."
        )
    elif topic_type == "roster":
        body = (
            "Squad time. Let's look at who's been named for this season "
            "and what the roster tells us heading into the competition."
        )
    else:
        body = f"Welcome. Today's topic: {episode_title}."
    return PodcastResearchSection(
        section_key="opening_hook",
        title="Suggested opening hook",
        body=body,
        confidence="medium",
        note="Deterministic template — polish to suit your style.",
    )


def _build_trust_note_section(trust_note: str) -> PodcastResearchSection:
    return PodcastResearchSection(
        section_key="data_trust_note",
        title="Data trust note",
        body=trust_note,
        confidence="high",
        note="Always include this in final broadcast preparation.",
    )


def _build_debate_questions(
    topic_type: str,
    competition_label: str | None,
    extra_context: str | None = None,
) -> PodcastResearchSection:
    questions: list[str] = []
    if topic_type == "match":
        questions = [
            "Was this result a true reflection of the game or did the final overs distort it?",
            "Which single moment changed the outcome?",
            "What does this tell us about both teams going forward?",
        ]
    elif topic_type == "tournament":
        comp = competition_label or "this tournament"
        questions = [
            f"Who was the standout performer across the {comp}?",
            "Did the best team win, or did luck play a role?",
            "What's one thing the data tells us that the final standings don't?",
        ]
    elif topic_type == "archive":
        questions = [
            "Have scoring patterns genuinely changed, or does the data tell a more nuanced story?",
            "Which era produced the most competitive cricket in the archive?",
            "What would need to change for a different team to dominate?",
        ]
    elif topic_type == "roster":
        questions = [
            "Which returning player is the most important retention?",
            "Who is the new signing with the most to prove?",
            "Does this squad look balanced on paper?",
        ]
    else:
        questions = [
            "What's the most surprising thing in the data?",
            "What's the one stat you'd cite to settle this debate?",
        ]
    if extra_context:
        questions.append(f"Given {extra_context} — what changes your view?")
    return PodcastResearchSection(
        section_key="debate_questions",
        title="Debate questions",
        body="\n".join(f"• {q}" for q in questions),
        confidence="medium",
        note="Questions derived from topic context — not from live or official data.",
    )


def _build_closing_question(
    topic_type: str, episode_title: str
) -> PodcastResearchSection:
    if topic_type == "match":
        body = "Final thought: does this result change how you'd rate either of these teams right now?"
    elif topic_type == "tournament":
        body = "Closing question for the room: was this the most competitive edition in the archive?"
    elif topic_type == "archive":
        body = "We'll leave it there — but tell us: which era of cricket would you most want to watch again?"
    elif topic_type == "roster":
        body = "Before we go: one player on this squad who you think will surprise everyone this season?"
    else:
        body = f"That's all from us today on {episode_title} — see you next time."
    return PodcastResearchSection(
        section_key="closing_question",
        title="Suggested closing question",
        body=body,
        confidence="medium",
        note="Template closing — adapt to suit the flow of your show.",
    )


# ---------------------------------------------------------------------------
# Match-based research pack
# ---------------------------------------------------------------------------


def build_match_research_pack(
    match_id: str,
    match_data: dict[str, Any],
) -> PodcastResearchPack:
    """Build a podcast research pack from match case study data.

    All values derived from the provided match_data dict (case study payload).
    No stats are invented.
    """
    match = match_data.get("match", {})
    innings_list = match_data.get("innings", [])
    key_players = match_data.get("key_players", [])
    innings_analysis = match_data.get("innings_analysis", [])

    teams_label: str = match.get("teams_label") or "Unknown teams"
    match_date: str | None = match.get("date")
    venue: str | None = match.get("venue")
    result_raw: str | None = match.get("result")
    match_format: str | None = match.get("format")
    competition: str | None = match.get("event_name") or match.get("competition_code")

    date_str = f" ({match_date})" if match_date else ""
    fmt_str = f" — {match_format}" if match_format else ""
    episode_title = f"{teams_label}{fmt_str}{date_str}"

    # Normalise result text (remove "delivered scored" artifacts)
    result_display = _clean_result_text(result_raw)

    sections: list[PodcastResearchSection] = []

    # Opening hook
    sections.append(
        _build_opening_hook("match", episode_title, result_display, competition, None)
    )

    # Match context
    context_lines: list[str] = []
    if result_display:
        context_lines.append(f"Result: {result_display}")
    if venue:
        context_lines.append(f"Venue: {venue}")
    if match_format:
        context_lines.append(f"Format: {match_format}")
    sections.append(
        PodcastResearchSection(
            section_key="match_context",
            title="Match context",
            body="\n".join(context_lines) if context_lines else None,
            confidence="high" if result_display else "low",
            note="Derived from imported match metadata.",
        )
    )

    # Scoreboard / key facts
    scoreboard_lines: list[str] = []
    for inns in innings_list:
        inns_team = inns.get("batting_team") or "Unknown"
        runs = inns.get("runs")
        wickets = inns.get("wickets")
        overs = inns.get("overs")
        total_str = _format_runs_wickets(runs, wickets)
        overs_str = f" ({overs} overs)" if overs is not None else ""
        scoreboard_lines.append(f"{inns_team}: {total_str}{overs_str}")
    sections.append(
        PodcastResearchSection(
            section_key="key_facts",
            title="Key facts (scoreboard)",
            body="\n".join(scoreboard_lines) if scoreboard_lines else None,
            confidence="high" if scoreboard_lines else "unknown",
            note="Derived from innings data in imported match.",
        )
    )

    # Player focus
    player_lines: list[str] = []
    for p in key_players[:5]:
        p_name = p.get("player_name") or p.get("name", "Unknown")
        p_team = p.get("team", "")
        bat = p.get("batting")
        bowl = p.get("bowling")
        parts: list[str] = []
        if bat and bat.get("runs") is not None:
            parts.append(f"{bat['runs']} runs")
            if bat.get("balls"):
                parts.append(f"off {bat['balls']} balls")
        if bowl and bowl.get("wickets") is not None:
            w = bowl["wickets"]
            parts.append(_pluralize(w, "wicket"))
        if parts:
            player_lines.append(
                f"{p_name}{' (' + p_team + ')' if p_team else ''}: {', '.join(parts)}"
            )
    sections.append(
        PodcastResearchSection(
            section_key="player_focus",
            title="Player focus",
            body="\n".join(player_lines) if player_lines else None,
            confidence="medium" if player_lines else "unknown",
            note="Derived from key player data. Stats from imported delivery records.",
        )
    )

    # Key storylines (from innings analysis story blocks)
    storyline_lines: list[str] = []
    for ia in innings_analysis[:2]:
        for block in (ia.get("story_blocks") or [])[:3]:
            body_text = block.get("body")
            if body_text:
                storyline_lines.append(f"• {body_text}")
    sections.append(
        PodcastResearchSection(
            section_key="key_storylines",
            title="Key storylines",
            body="\n".join(storyline_lines) if storyline_lines else None,
            confidence="medium" if storyline_lines else "unknown",
            note="Derived from innings story analysis.",
        )
    )

    # Tactical talking points
    tactical_lines: list[str] = []
    for ia in innings_analysis[:2]:
        for callout in (ia.get("callouts") or [])[:2]:
            txt = callout.get("text")
            if txt:
                tactical_lines.append(f"• {txt}")
    for callout in (match_data.get("match_callouts") or [])[:3]:
        txt = callout.get("text")
        if txt:
            tactical_lines.append(f"• {txt}")
    sections.append(
        PodcastResearchSection(
            section_key="tactical_talking_points",
            title="Tactical talking points",
            body="\n".join(tactical_lines) if tactical_lines else None,
            confidence="medium" if tactical_lines else "unknown",
            note="Derived from analyst callouts in match data.",
        )
    )

    # Venue context
    sections.append(
        PodcastResearchSection(
            section_key="venue_context",
            title="Venue context",
            body=f"Played at: {venue}" if venue else None,
            confidence="high" if venue else "unknown",
            note="Venue from match metadata.",
        )
    )

    # Debate questions
    sections.append(_build_debate_questions("match", competition))

    # Closing question
    sections.append(_build_closing_question("match", episode_title))

    # Trust note
    trust_note = (
        "Match facts are derived from imported match data. "
        "Player statistics are from delivery records where available. "
        "Results and scoreboard totals are not official records."
    )
    sections.append(_build_trust_note_section(trust_note))

    confidence = "high" if (scoreboard_lines and result_display) else "medium"

    pack = PodcastResearchPack(
        topic_type="match",
        episode_title=episode_title,
        match_context=result_display,
        venue_context=venue,
        format_label=match_format,
        competition_label=competition,
        sections=sections,
        source_match_id=match_id,
        trust_note=trust_note,
        overall_confidence=confidence,  # type: ignore[arg-type]
    )
    pack.generated_markdown = _render_markdown(pack)
    pack.generated_plain_text = _render_plain_text(pack)
    return pack


# ---------------------------------------------------------------------------
# Tournament-based research pack
# ---------------------------------------------------------------------------


def build_tournament_research_pack(
    competition_code: str,
    season: str | None,
    gender_category: str,
    tournament_summary: dict[str, Any],
) -> PodcastResearchPack:
    """Build a podcast research pack from tournament intelligence data."""

    group = tournament_summary.get("group_key", {})
    comp_label = group.get("competition_name") or competition_code
    season_label = group.get("season") or season
    fmt_label = group.get("format_family")
    knockout = tournament_summary.get("knockout_context") or {}
    champion = knockout.get("champion_team")
    finalist = knockout.get("runner_up_team")
    final_result = knockout.get("final_result")
    podcast_facts = tournament_summary.get("podcast_facts") or {}
    completeness = tournament_summary.get("data_completeness") or {}
    standings = tournament_summary.get("derived_standings") or []
    top_run_scorer = tournament_summary.get("top_run_scorer")
    top_wicket_taker = tournament_summary.get("top_wicket_taker")
    total_matches = completeness.get("total_matches", 0)
    confidence_level = completeness.get("confidence_level", "unknown")

    season_str = f" {season_label}" if season_label else ""
    episode_title = f"{comp_label}{season_str} — Season Review"

    sections: list[PodcastResearchSection] = []

    # Opening hook
    sections.append(
        _build_opening_hook("tournament", episode_title, None, comp_label, season_label)
    )

    # Tournament setup
    setup_lines: list[str] = []
    if total_matches:
        setup_lines.append(f"Matches in archive: {total_matches}")
    if fmt_label:
        setup_lines.append(f"Format: {fmt_label}")
    if champion:
        setup_lines.append(f"Champion (derived): {champion}")
    elif knockout.get("final_match_title"):
        setup_lines.append(f"Final: {knockout['final_match_title']}")
    sections.append(
        PodcastResearchSection(
            section_key="tournament_setup",
            title="Tournament setup",
            body="\n".join(setup_lines) if setup_lines else None,
            confidence=confidence_level,  # type: ignore[arg-type]
            note="Derived from imported match archive.",
        )
    )

    # Champion story
    champ_lines: list[str] = []
    if champion:
        champ_lines.append(f"Champion: {champion} (derived from final result)")
    if finalist:
        champ_lines.append(f"Runner-up: {finalist}")
    if final_result:
        champ_lines.append(f"Final result: {final_result}")
    sections.append(
        PodcastResearchSection(
            section_key="champion_story",
            title="Champion story",
            body="\n".join(champ_lines) if champ_lines else "Champion data not available in archive.",
            confidence=confidence_level if champ_lines else "unknown",  # type: ignore[arg-type]
            note="Derived from knockout context — not official records.",
        )
    )

    # Standings story
    standings_lines: list[str] = []
    for i, row in enumerate(standings[:5]):
        team = row.get("team_name", "Unknown")
        wins = row.get("wins", 0)
        played = row.get("played", 0)
        pts = row.get("points", 0)
        standings_lines.append(
            f"{i + 1}. {team} — {_pluralize(wins, 'win')}, {played} played, {pts} pts (derived)"
        )
    sections.append(
        PodcastResearchSection(
            section_key="standings_story",
            title="Derived standings (not official)",
            body="\n".join(standings_lines) if standings_lines else None,
            confidence="low",
            note="Derived standings — estimated using 2pts/win. NOT official standings.",
        )
    )

    # Player storylines
    player_lines: list[str] = []
    if top_run_scorer:
        name = top_run_scorer.get("player_name", "Unknown")
        runs = top_run_scorer.get("value")
        if runs is not None:
            player_lines.append(f"Top run scorer: {name} — {runs} runs (derived from deliveries)")
    if top_wicket_taker:
        name = top_wicket_taker.get("player_name", "Unknown")
        wickets = top_wicket_taker.get("value")
        if wickets is not None:
            player_lines.append(
                f"Top wicket taker: {name} — {_pluralize(wickets, 'wicket')} (derived from deliveries)"
            )
    sections.append(
        PodcastResearchSection(
            section_key="player_storylines",
            title="Player storylines",
            body="\n".join(player_lines) if player_lines else "Player stats unavailable — delivery data required.",
            confidence="medium" if player_lines else "unknown",
            note="Derived from delivery-level data where available.",
        )
    )

    # Podcast facts
    fact_lines: list[str] = []
    if podcast_facts:
        top_venue = podcast_facts.get("top_scoring_venue")
        highest_title = podcast_facts.get("highest_scoring_match_title")
        highest_runs = podcast_facts.get("highest_match_total_runs")
        if top_venue:
            fact_lines.append(f"Top scoring venue: {top_venue}")
        if highest_title and highest_runs:
            fact_lines.append(f"Highest match total: {highest_runs} runs ({highest_title})")
    sections.append(
        PodcastResearchSection(
            section_key="key_facts",
            title="Key facts",
            body="\n".join(fact_lines) if fact_lines else None,
            confidence="medium" if fact_lines else "unknown",
            note="Derived from tournament-level aggregation.",
        )
    )

    # Debate questions
    sections.append(_build_debate_questions("tournament", comp_label))

    # Closing question
    sections.append(_build_closing_question("tournament", episode_title))

    # Trust note
    trust_note = (
        "Tournament facts are derived from imported match archive data. "
        "Derived standings are estimated and are NOT official standings. "
        "Champion data is inferred from final-stage match results where available. "
        "Player stats require delivery-level data and may be unavailable."
    )
    sections.append(_build_trust_note_section(trust_note))

    pack = PodcastResearchPack(
        topic_type="tournament",
        episode_title=episode_title,
        competition_label=comp_label,
        season_label=season_label,
        format_label=fmt_label,
        sections=sections,
        source_competition_code=competition_code,
        source_season=season,
        trust_note=trust_note,
        overall_confidence=confidence_level,  # type: ignore[arg-type]
    )
    pack.generated_markdown = _render_markdown(pack)
    pack.generated_plain_text = _render_plain_text(pack)
    return pack


# ---------------------------------------------------------------------------
# Archive-based research pack
# ---------------------------------------------------------------------------


def build_archive_research_pack(
    archive_data: dict[str, Any],
    request: ArchivePodcastPackRequest,
) -> PodcastResearchPack:
    """Build a podcast research pack from archive explorer data."""

    total_matches = archive_data.get("total_matches", 0)
    total_groups = archive_data.get("total_groups", 0)
    trust_note_from_data = archive_data.get(
        "trust_note",
        "All archive views are derived from imported match data and are not official.",
    )
    comparison_rows = archive_data.get("comparison_rows", [])
    champion_history = archive_data.get("champion_history", [])
    dynasty_indicators = archive_data.get("dynasty_indicators", [])
    era_comparisons = archive_data.get("era_comparison_cards", [])

    comp_filter = request.competition_code or "All competitions"
    episode_title = f"Historical Archive — {comp_filter}"
    if request.season_start and request.season_end:
        episode_title += f" ({request.season_start}–{request.season_end})"

    sections: list[PodcastResearchSection] = []
    sections.append(
        _build_opening_hook("archive", episode_title, None, comp_filter, None)
    )

    # Archive context
    archive_lines: list[str] = []
    if total_matches:
        archive_lines.append(f"Matches in archive: {total_matches}")
    if total_groups:
        archive_lines.append(f"Tournament seasons covered: {total_groups}")
    sections.append(
        PodcastResearchSection(
            section_key="archive_context",
            title="Archive context",
            body="\n".join(archive_lines) if archive_lines else "Archive data unavailable.",
            confidence="high" if total_matches else "unknown",
            note="Derived from imported historical match archive.",
        )
    )

    # Comparison angles
    comp_lines: list[str] = []
    for row in comparison_rows[:5]:
        label = row.get("season_label") or row.get("competition_label")
        matches = row.get("match_count", 0)
        wins_available = row.get("wins_available", False)
        avg_runs = row.get("avg_runs_per_match")
        line = f"• {label}: {matches} matches"
        if avg_runs is not None:
            line += f", avg {avg_runs:.0f} runs/match (derived)"
        if not wins_available:
            line += " [result coverage incomplete]"
        comp_lines.append(line)
    sections.append(
        PodcastResearchSection(
            section_key="comparison_angles",
            title="Comparison angles",
            body="\n".join(comp_lines) if comp_lines else None,
            confidence="medium" if comp_lines else "unknown",
            note="Season-level comparisons derived from imported data. Incomplete seasons may skew averages.",
        )
    )

    # Champion history
    champ_lines: list[str] = []
    for entry in champion_history[:6]:
        season = entry.get("season_label") or entry.get("season")
        champ = entry.get("champion_team")
        how = entry.get("detection_note")
        if season and champ:
            note_str = f" [{how}]" if how else ""
            champ_lines.append(f"• {season}: {champ}{note_str}")
    sections.append(
        PodcastResearchSection(
            section_key="champion_history",
            title="Champion history (derived)",
            body="\n".join(champ_lines) if champ_lines else "Champion history unavailable.",
            confidence="low",
            note="Derived from final-stage match detection — not an official trophy record.",
        )
    )

    # Dynasty indicators
    dynasty_lines: list[str] = []
    for d in dynasty_indicators[:3]:
        team = d.get("team_name")
        titles = d.get("title_count", 0)
        seasons = d.get("seasons_appeared")
        if team and titles:
            dynasty_lines.append(
                f"• {team}: {_pluralize(titles, 'derived title')}, "
                f"{seasons} seasons (derived)"
            )
    sections.append(
        PodcastResearchSection(
            section_key="dynasty_indicators",
            title="Dynasty indicators",
            body="\n".join(dynasty_lines) if dynasty_lines else None,
            confidence="low",
            note="Derived from champion history — not official records.",
        )
    )

    # Era comparisons
    era_lines: list[str] = []
    for card in era_comparisons[:3]:
        label = card.get("era_label") or card.get("label")
        narrative = card.get("narrative") or card.get("headline")
        if label and narrative:
            era_lines.append(f"• {label}: {narrative}")
    sections.append(
        PodcastResearchSection(
            section_key="era_comparisons",
            title="Era comparisons",
            body="\n".join(era_lines) if era_lines else None,
            confidence="medium" if era_lines else "unknown",
            note="Derived from archive-level aggregation across seasons.",
        )
    )

    # Debate questions
    sections.append(_build_debate_questions("archive", comp_filter))

    # Closing question
    sections.append(_build_closing_question("archive", episode_title))

    trust_note = (
        "Historical comparisons are derived from imported archive records and are not official standings. "
        "Champion history is inferred from detected final-stage results. "
        "Incomplete seasons may affect era comparisons."
    )
    sections.append(_build_trust_note_section(trust_note))

    pack = PodcastResearchPack(
        topic_type="archive",
        episode_title=episode_title,
        competition_label=comp_filter,
        sections=sections,
        source_competition_code=request.competition_code,
        trust_note=trust_note,
        overall_confidence="medium" if total_matches else "unknown",
    )
    pack.generated_markdown = _render_markdown(pack)
    pack.generated_plain_text = _render_plain_text(pack)
    return pack


# ---------------------------------------------------------------------------
# Roster-based research pack
# ---------------------------------------------------------------------------


def build_roster_research_pack(
    competition_code: str,
    season: str,
    team_name: str | None,
    players: list[dict[str, Any]],
    teams: list[dict[str, Any]],
) -> PodcastResearchPack:
    """Build a podcast research pack from current-season roster data."""

    comp_label = competition_code
    episode_title = f"{comp_label} {season} — Squad Overview"
    if team_name:
        episode_title = f"{team_name} ({comp_label} {season}) — Squad Rundown"

    sections: list[PodcastResearchSection] = []
    sections.append(
        _build_opening_hook("roster", episode_title, None, comp_label, season)
    )

    # Squad overview
    total_players = len(players)
    returning = [p for p in players if p.get("is_returning")]
    new_players = [p for p in players if not p.get("is_returning")]
    active = [p for p in players if p.get("status") == "active"]

    overview_lines: list[str] = [
        f"Total squad entries: {total_players}",
        f"Active: {len(active)}",
        f"Returning players: {len(returning)}",
        f"New additions: {len(new_players)}",
    ]
    if teams:
        overview_lines.append(f"Teams registered: {len(teams)}")
    sections.append(
        PodcastResearchSection(
            section_key="squad_overview",
            title="Squad overview",
            body="\n".join(overview_lines),
            confidence="high",
            note="Roster data is user-maintained.",
        )
    )

    # Returning players to watch
    returning_lines: list[str] = []
    for p in returning[:8]:
        name = p.get("display_name") or p.get("player_name", "Unknown")
        team = p.get("team_name")
        prior = p.get("prior_season")
        line = f"• {name}"
        if team:
            line += f" ({team})"
        if prior:
            line += f" — returning from {prior}"
        returning_lines.append(line)
    sections.append(
        PodcastResearchSection(
            section_key="returning_players",
            title="Returning players to watch",
            body="\n".join(returning_lines) if returning_lines else "No returning players detected.",
            confidence="high" if returning_lines else "medium",
            note="Based on user-maintained roster registry. No historical stats are attached to current-season entries.",
        )
    )

    # New squad additions
    new_lines: list[str] = []
    for p in new_players[:8]:
        name = p.get("display_name") or p.get("player_name", "Unknown")
        team = p.get("team_name")
        role = p.get("role")
        line = f"• {name}"
        if team:
            line += f" ({team})"
        if role:
            line += f" — {role}"
        new_lines.append(line)
    sections.append(
        PodcastResearchSection(
            section_key="new_additions",
            title="New squad additions",
            body="\n".join(new_lines) if new_lines else "No new additions identified.",
            confidence="high" if new_lines else "medium",
            note="New to this season's roster registry.",
        )
    )

    # Team continuity notes
    team_lines: list[str] = []
    for t in teams[:6]:
        t_name = t.get("team_name", "Unknown")
        team_players = [p for p in players if p.get("team_name") == t_name]
        returning_for_team = [p for p in team_players if p.get("is_returning")]
        team_lines.append(
            f"• {t_name}: {len(team_players)} registered"
            + (f", {len(returning_for_team)} returning" if returning_for_team else "")
        )
    sections.append(
        PodcastResearchSection(
            section_key="team_continuity",
            title="Team continuity notes",
            body="\n".join(team_lines) if team_lines else None,
            confidence="high" if team_lines else "unknown",
            note="Based on current-season roster registry entries.",
        )
    )

    # Squad uncertainty note (always present for roster packs)
    sections.append(
        PodcastResearchSection(
            section_key="squad_uncertainty",
            title="Squad uncertainty / trust note",
            body=(
                "Player statistics are not available for current-season roster entries unless "
                "historical match data exists in the archive. "
                "Roster data is user-maintained and should be verified before broadcast."
            ),
            confidence="high",
            note="Governance: never invent player stats from roster-only data.",
        )
    )

    # Debate questions
    sections.append(_build_debate_questions("roster", comp_label))
    sections.append(_build_closing_question("roster", episode_title))

    trust_note = (
        "Roster information is user-maintained and should be reviewed before publication. "
        "Player statistics are unavailable for players not yet in the historical archive. "
        "Do not assert player form or performance data from roster-only entries."
    )
    sections.append(_build_trust_note_section(trust_note))

    pack = PodcastResearchPack(
        topic_type="roster",  # type: ignore[arg-type]
        episode_title=episode_title,
        competition_label=comp_label,
        season_label=season,
        source_competition_code=competition_code,
        source_season=season,
        source_team_name=team_name,
        sections=sections,
        trust_note=trust_note,
        overall_confidence="medium",
    )
    pack.generated_markdown = _render_markdown(pack)
    pack.generated_plain_text = _render_plain_text(pack)
    return pack


# ---------------------------------------------------------------------------
# Markdown / plain-text renderers
# ---------------------------------------------------------------------------


def _render_markdown(pack: PodcastResearchPack) -> str:
    """Render the research pack as Markdown."""
    lines: list[str] = [
        f"# {pack.episode_title}",
        "",
        f"**Topic type:** {pack.topic_type}",
    ]
    if pack.competition_label:
        lines.append(f"**Competition:** {pack.competition_label}")
    if pack.season_label:
        lines.append(f"**Season:** {pack.season_label}")
    if pack.format_label:
        lines.append(f"**Format:** {pack.format_label}")
    lines.append("")
    for section in pack.sections:
        lines.append(f"## {section.title}")
        if section.body:
            lines.append(section.body)
        else:
            lines.append("_Not available_")
        lines.append(
            f"_Confidence: {section.confidence} — {section.note}_"
        )
        lines.append("")
    lines.append("---")
    lines.append(f"**Trust note:** {pack.trust_note}")
    lines.append(
        f"_Generated: {pack.generated_at.strftime('%Y-%m-%d %H:%M UTC')}_"
    )
    return "\n".join(lines)


def _render_plain_text(pack: PodcastResearchPack) -> str:
    """Render the research pack as clean plain text (no Markdown syntax)."""
    lines: list[str] = [
        pack.episode_title,
        "=" * min(len(pack.episode_title), 60),
        "",
        f"Topic: {pack.topic_type}",
    ]
    if pack.competition_label:
        lines.append(f"Competition: {pack.competition_label}")
    if pack.season_label:
        lines.append(f"Season: {pack.season_label}")
    if pack.format_label:
        lines.append(f"Format: {pack.format_label}")
    lines.append("")
    for section in pack.sections:
        lines.append(f"--- {section.title.upper()} ---")
        if section.body:
            lines.append(section.body)
        else:
            lines.append("[Not available]")
        lines.append(f"[{section.confidence} confidence]")
        lines.append("")
    lines.append("TRUST NOTE:")
    lines.append(pack.trust_note)
    lines.append(
        f"Generated: {pack.generated_at.strftime('%Y-%m-%d %H:%M UTC')}"
    )
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Result text cleanup (no "delivered scored" artifacts)
# ---------------------------------------------------------------------------


def _clean_result_text(raw: str | None) -> str | None:
    """Remove known copy artifacts from result text.

    Ensures phrases like 'delivered scored', '1 runs', '1 wickets' don't
    appear in podcast output.
    """
    if not raw:
        return None
    text = raw
    # Fix '1 runs' / '1 wickets' singular/plural
    import re

    text = re.sub(r"\b1 runs\b", "1 run", text)
    text = re.sub(r"\b1 wickets\b", "1 wicket", text)
    # Remove "delivered scored" artifacts
    text = re.sub(r"\bdelivered scored\b", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s{2,}", " ", text).strip()
    return text or None


# ---------------------------------------------------------------------------
# Saved report DB operations
# ---------------------------------------------------------------------------


async def create_podcast_prep_report(
    db: AsyncSession,
    data: PodcastPrepReportCreate,
    created_by_id: str | None = None,
) -> PodcastPrepReport:
    """Persist a new podcast prep report."""
    report = PodcastPrepReport(
        title=data.title,
        topic_type=PodcastPrepTopicType(data.topic_type),
        source_match_id=data.source_match_id,
        source_competition_code=data.source_competition_code,
        source_season=data.source_season,
        source_team_name=data.source_team_name,
        generated_markdown=data.generated_markdown,
        generated_plain_text=data.generated_plain_text,
        trust_summary=data.trust_summary,
        created_by_id=created_by_id,
    )
    db.add(report)
    await db.commit()
    await db.refresh(report)
    return report


async def update_podcast_prep_report(
    db: AsyncSession,
    report_id: str,
    data: PodcastPrepReportUpdate,
) -> PodcastPrepReport | None:
    """Update an existing podcast prep report."""
    result = await db.execute(
        select(PodcastPrepReport).where(PodcastPrepReport.id == report_id)
    )
    report = result.scalar_one_or_none()
    if report is None:
        return None
    if data.title is not None:
        report.title = data.title
    if data.generated_markdown is not None:
        report.generated_markdown = data.generated_markdown
    if data.generated_plain_text is not None:
        report.generated_plain_text = data.generated_plain_text
    if data.trust_summary is not None:
        report.trust_summary = data.trust_summary
    if data.status is not None:
        from backend.sql_app.models import PodcastPrepReportStatus
        report.status = PodcastPrepReportStatus(data.status)
    await db.commit()
    await db.refresh(report)
    return report


async def get_podcast_prep_report(
    db: AsyncSession,
    report_id: str,
) -> PodcastPrepReport | None:
    result = await db.execute(
        select(PodcastPrepReport).where(PodcastPrepReport.id == report_id)
    )
    return result.scalar_one_or_none()


async def list_podcast_prep_reports(
    db: AsyncSession,
    created_by_id: str | None = None,
    topic_type: str | None = None,
    status: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> PodcastPrepReportListResponse:
    stmt = select(PodcastPrepReport)
    count_stmt = select(PodcastPrepReport.id)
    if created_by_id:
        stmt = stmt.where(PodcastPrepReport.created_by_id == created_by_id)
        count_stmt = count_stmt.where(PodcastPrepReport.created_by_id == created_by_id)
    if topic_type:
        stmt = stmt.where(PodcastPrepReport.topic_type == PodcastPrepTopicType(topic_type))
        count_stmt = count_stmt.where(
            PodcastPrepReport.topic_type == PodcastPrepTopicType(topic_type)
        )
    if status:
        from backend.sql_app.models import PodcastPrepReportStatus as _Status
        stmt = stmt.where(PodcastPrepReport.status == _Status(status))
        count_stmt = count_stmt.where(PodcastPrepReport.status == _Status(status))
    stmt = stmt.order_by(PodcastPrepReport.updated_at.desc())
    count_result = await db.execute(count_stmt)
    total = len(count_result.all())
    stmt = stmt.limit(limit).offset(offset)
    result = await db.execute(stmt)
    reports = list(result.scalars().all())
    return PodcastPrepReportListResponse(
        reports=[PodcastPrepReportResponse.model_validate(r) for r in reports],
        total=total,
    )
