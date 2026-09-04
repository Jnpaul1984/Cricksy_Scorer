"""Phase 10T — Podcast Prep Studio tests.

Validates:
- _pluralize helper (singular/plural grammar)
- _clean_result_text (copy quality: no '1 runs', '1 wickets', 'delivered scored')
- _render_markdown / _render_plain_text section rendering
- build_match_research_pack (trust note, sections, correct grammar)
- build_tournament_research_pack (trust note, sections)
- build_archive_research_pack (trust note, sections)
- build_roster_research_pack (trust note, no invented stats)
- Saved report CRUD (create, update, get, list)

Run:
    CRICKSY_IN_MEMORY_DB=1 APP_SECRET_KEY=test-secret-key \\
      python -m pytest backend/tests/test_podcast_prep.py -v
"""

from __future__ import annotations

import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")

from backend.api.schemas.podcast_prep import (
    ArchivePodcastPackRequest,
    PodcastPrepReportCreate,
    PodcastPrepReportUpdate,
    PodcastResearchPack,
)
from backend.services.podcast_prep_service import (
    _clean_result_text,
    _pluralize,
    _render_markdown,
    _render_plain_text,
    build_archive_research_pack,
    build_match_research_pack,
    build_roster_research_pack,
    build_tournament_research_pack,
    create_podcast_prep_report,
    get_podcast_prep_report,
    list_podcast_prep_reports,
    update_podcast_prep_report,
)
from backend.sql_app import models


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def run(coro):
    import asyncio

    return asyncio.get_event_loop().run_until_complete(coro)


@pytest.fixture()
def session():
    import asyncio

    from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

    engine = create_async_engine("sqlite+aiosqlite:///:memory:", echo=False)

    async def _setup():
        async with engine.begin() as conn:
            await conn.run_sync(models.Base.metadata.create_all)

    asyncio.get_event_loop().run_until_complete(_setup())
    sm = async_sessionmaker(engine, expire_on_commit=False)

    async def _get():
        async with sm() as s:
            return s

    yield asyncio.get_event_loop().run_until_complete(_get())

    async def _teardown():
        await engine.dispose()

    asyncio.get_event_loop().run_until_complete(_teardown())


def _minimal_match_data(
    result: str | None = "Team A won by 50 runs",
    venue: str = "Kensington Oval",
    match_format: str = "T20",
) -> dict:
    return {
        "match": {
            "teams_label": "Team A vs Team B",
            "date": "2024-08-20",
            "venue": venue,
            "result": result,
            "format": match_format,
            "competition_code": "CPL_MEN",
        },
        "innings": [
            {"batting_team": "Team A", "runs": 185, "wickets": 6, "overs": 20},
            {"batting_team": "Team B", "runs": 135, "wickets": 10, "overs": 18.3},
        ],
        "key_players": [
            {
                "player_name": "Chris Gayle",
                "team": "Team A",
                "batting": {"runs": 80, "balls": 45},
            },
            {
                "player_name": "Dwayne Bravo",
                "team": "Team B",
                "bowling": {"wickets": 3},
            },
        ],
        "innings_analysis": [
            {
                "story_blocks": [
                    {"body": "Team A posted a strong total despite early pressure."},
                ],
                "callouts": [
                    {"text": "Chris Gayle's strike rate was exceptional."},
                ],
            }
        ],
        "match_callouts": [
            {"text": "The death bowling was decisive in this match."},
        ],
    }


def _minimal_tournament_data() -> dict:
    return {
        "competition_code": "CPL_MEN",
        "competition_name": "Caribbean Premier League",
        "season": "2024",
        "gender_category": "men",
        "format_family": "T20",
        "total_matches": 34,
        "completed_matches": 34,
        "champion": "Barbados Royals",
        "top_run_scorer": {"player_name": "Chris Gayle", "runs": 450},
        "top_wicket_taker": {"player_name": "Dwayne Bravo", "wickets": 15},
        "team_standings": [
            {"team_name": "Barbados Royals", "wins": 8, "losses": 2, "points": 16},
            {"team_name": "Jamaica Tallawahs", "wins": 6, "losses": 4, "points": 12},
        ],
        "key_facts": [
            "Barbados Royals won the 2024 CPL title.",
            "34 matches played across the tournament.",
        ],
        "top_storylines": [
            "Barbados Royals showed consistent form throughout.",
        ],
    }


def _minimal_archive_data() -> dict:
    return {
        "available_competitions": [
            {
                "competition_code": "CPL_MEN",
                "competition_name": "Caribbean Premier League",
                "seasons": ["2014", "2015", "2024"],
                "total_matches": 200,
            }
        ],
        "champion_history": [
            {"season": "2024", "champion": "Barbados Royals"},
            {"season": "2023", "champion": "Guyana Amazon Warriors"},
        ],
        "era_comparisons": [
            {
                "era_label": "Early Era (2014-2016)",
                "notes": "High-scoring era with many close finishes.",
            }
        ],
        "key_facts": ["200 archived matches across CPL history."],
        "trust_note": "Derived from imported historical archive.",
    }


def _minimal_roster_data() -> dict:
    return {
        "competition_code": "CPL_MEN",
        "season": "2024",
        "teams": [
            {
                "team_name": "Barbados Royals",
                "players": [
                    {
                        "player_name": "Chris Gayle",
                        "role": "Batsman",
                        "status": "active",
                        "is_returning": True,
                        "prior_season": "2023",
                    },
                    {
                        "player_name": "New Player Junior",
                        "role": "All-Rounder",
                        "status": "active",
                        "is_returning": False,
                        "prior_season": None,
                    },
                ],
            }
        ],
        "returning_players": ["Chris Gayle"],
        "new_players": ["New Player Junior"],
        "squad_notes": "Roster is user-maintained and subject to change.",
    }


# ---------------------------------------------------------------------------
# _pluralize tests
# ---------------------------------------------------------------------------


class TestPluralize:
    def test_one_run(self) -> None:
        assert _pluralize(1, "run") == "1 run"

    def test_two_runs(self) -> None:
        assert _pluralize(2, "run") == "2 runs"

    def test_one_wicket(self) -> None:
        assert _pluralize(1, "wicket") == "1 wicket"

    def test_two_wickets(self) -> None:
        assert _pluralize(2, "wicket") == "2 wickets"

    def test_zero_wickets(self) -> None:
        assert _pluralize(0, "wicket") == "0 wickets"

    def test_custom_plural(self) -> None:
        assert _pluralize(1, "match", "matches") == "1 match"
        assert _pluralize(3, "match", "matches") == "3 matches"

    def test_one_win(self) -> None:
        assert _pluralize(1, "win") == "1 win"

    def test_multiple_wins(self) -> None:
        assert _pluralize(5, "win") == "5 wins"


# ---------------------------------------------------------------------------
# _clean_result_text tests
# ---------------------------------------------------------------------------


class TestCleanResultText:
    def test_fixes_one_runs(self) -> None:
        assert _clean_result_text("Team A won by 1 runs") == "Team A won by 1 run"

    def test_fixes_one_wickets(self) -> None:
        assert _clean_result_text("Team A won by 1 wickets") == "Team A won by 1 wicket"

    def test_removes_delivered_scored(self) -> None:
        result = _clean_result_text("Team A delivered scored 50 runs")
        assert "delivered scored" not in (result or "")

    def test_removes_delivered_scored_case_insensitive(self) -> None:
        result = _clean_result_text("Team A Delivered Scored 50 runs")
        assert "delivered scored" not in (result or "").lower()

    def test_normal_text_unchanged(self) -> None:
        text = "Team A won by 50 runs"
        assert _clean_result_text(text) == text

    def test_none_returns_none(self) -> None:
        assert _clean_result_text(None) is None

    def test_empty_string_returns_none(self) -> None:
        assert _clean_result_text("") is None

    def test_multiple_spaces_collapsed(self) -> None:
        result = _clean_result_text("Team A  won  by 50 runs")
        assert "  " not in (result or "")

    def test_2_runs_unchanged(self) -> None:
        # "2 runs" should NOT be changed to "2 run"
        assert _clean_result_text("Team A won by 2 runs") == "Team A won by 2 runs"

    def test_2_wickets_unchanged(self) -> None:
        assert _clean_result_text("Team A won by 2 wickets") == "Team A won by 2 wickets"


# ---------------------------------------------------------------------------
# build_match_research_pack tests
# ---------------------------------------------------------------------------


class TestBuildMatchResearchPack:
    def test_returns_pack(self) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        assert isinstance(pack, PodcastResearchPack)

    def test_episode_title_contains_teams(self) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        assert "Team A" in pack.episode_title
        assert "Team B" in pack.episode_title

    def test_topic_type_is_match(self) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        assert pack.topic_type == "match"

    def test_trust_note_present(self) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        assert pack.trust_note
        assert len(pack.trust_note) > 10

    def test_trust_note_section_present(self) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        keys = [s.section_key for s in pack.sections]
        assert "data_trust_note" in keys or "trust_note" in keys

    def test_no_delivered_scored_in_output(self) -> None:
        data = _minimal_match_data(result="Team A delivered scored 50 runs")
        pack = build_match_research_pack("match-1", data)
        combined = " ".join(s.body for s in pack.sections if s.body) + (pack.match_context or "")
        assert "delivered scored" not in combined.lower()

    def test_no_1_runs_in_output(self) -> None:
        data = _minimal_match_data(result="Team A won by 1 runs")
        pack = build_match_research_pack("match-1", data)
        combined = " ".join(s.body for s in pack.sections if s.body) + (pack.match_context or "")
        assert "1 runs" not in combined

    def test_no_1_wickets_in_output(self) -> None:
        data = _minimal_match_data(result="Team A won by 1 wickets")
        pack = build_match_research_pack("match-1", data)
        combined = " ".join(s.body for s in pack.sections if s.body) + (pack.match_context or "")
        assert "1 wickets" not in combined

    def test_sections_include_key_facts(self) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        keys = [s.section_key for s in pack.sections]
        assert "key_facts" in keys

    def test_sections_include_player_focus(self) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        keys = [s.section_key for s in pack.sections]
        assert "player_focus" in keys

    def test_sections_include_opening_hook(self) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        keys = [s.section_key for s in pack.sections]
        assert "opening_hook" in keys

    def test_generated_markdown_is_string(self) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        assert isinstance(pack.generated_markdown, str)
        assert len(pack.generated_markdown) > 50

    def test_generated_plain_text_is_string(self) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        assert isinstance(pack.generated_plain_text, str)
        assert len(pack.generated_plain_text) > 50

    def test_empty_match_data_does_not_crash(self) -> None:
        pack = build_match_research_pack("match-1", {})
        assert pack.topic_type == "match"
        assert pack.trust_note

    def test_source_match_id_set(self) -> None:
        pack = build_match_research_pack("match-abc", _minimal_match_data())
        assert pack.source_match_id == "match-abc"

    def test_player_wickets_plural_correct(self) -> None:
        data = _minimal_match_data()
        data["key_players"] = [
            {
                "player_name": "Big Hitter",
                "team": "Team A",
                "bowling": {"wickets": 1},
            }
        ]
        pack = build_match_research_pack("match-1", data)
        player_section = next((s for s in pack.sections if s.section_key == "player_focus"), None)
        assert player_section is not None
        assert "1 wicket" in (player_section.body or "")
        assert "1 wickets" not in (player_section.body or "")


# ---------------------------------------------------------------------------
# build_tournament_research_pack tests
# ---------------------------------------------------------------------------


class TestBuildTournamentResearchPack:
    def test_returns_pack(self) -> None:
        pack = build_tournament_research_pack("CPL_MEN", "2024", "men", _minimal_tournament_data())
        assert isinstance(pack, PodcastResearchPack)

    def test_topic_type_is_tournament(self) -> None:
        pack = build_tournament_research_pack("CPL_MEN", "2024", "men", _minimal_tournament_data())
        assert pack.topic_type == "tournament"

    def test_trust_note_present(self) -> None:
        pack = build_tournament_research_pack("CPL_MEN", "2024", "men", _minimal_tournament_data())
        assert pack.trust_note
        assert "not official" in pack.trust_note.lower() or "derived" in pack.trust_note.lower()

    def test_trust_note_section_present(self) -> None:
        pack = build_tournament_research_pack("CPL_MEN", "2024", "men", _minimal_tournament_data())
        keys = [s.section_key for s in pack.sections]
        assert "data_trust_note" in keys or "trust_note" in keys

    def test_sections_include_opening_hook(self) -> None:
        pack = build_tournament_research_pack("CPL_MEN", "2024", "men", _minimal_tournament_data())
        keys = [s.section_key for s in pack.sections]
        assert "opening_hook" in keys

    def test_generated_markdown_not_empty(self) -> None:
        pack = build_tournament_research_pack("CPL_MEN", "2024", "men", _minimal_tournament_data())
        assert isinstance(pack.generated_markdown, str)
        assert len(pack.generated_markdown) > 30

    def test_empty_tournament_data_does_not_crash(self) -> None:
        pack = build_tournament_research_pack("CPL_MEN", "2024", "men", {})
        assert pack.topic_type == "tournament"
        assert pack.trust_note


# ---------------------------------------------------------------------------
# build_archive_research_pack tests
# ---------------------------------------------------------------------------


class TestBuildArchiveResearchPack:
    def test_returns_pack(self) -> None:
        req = ArchivePodcastPackRequest(competition_code="CPL_MEN")
        pack = build_archive_research_pack(_minimal_archive_data(), req)
        assert isinstance(pack, PodcastResearchPack)

    def test_topic_type_is_archive(self) -> None:
        req = ArchivePodcastPackRequest(competition_code="CPL_MEN")
        pack = build_archive_research_pack(_minimal_archive_data(), req)
        assert pack.topic_type == "archive"

    def test_trust_note_present(self) -> None:
        req = ArchivePodcastPackRequest(competition_code="CPL_MEN")
        pack = build_archive_research_pack(_minimal_archive_data(), req)
        assert pack.trust_note
        assert len(pack.trust_note) > 10

    def test_trust_note_section_present(self) -> None:
        req = ArchivePodcastPackRequest(competition_code="CPL_MEN")
        pack = build_archive_research_pack(_minimal_archive_data(), req)
        keys = [s.section_key for s in pack.sections]
        assert "data_trust_note" in keys or "trust_note" in keys

    def test_generated_markdown_not_empty(self) -> None:
        req = ArchivePodcastPackRequest(competition_code="CPL_MEN")
        pack = build_archive_research_pack(_minimal_archive_data(), req)
        assert isinstance(pack.generated_markdown, str)
        assert len(pack.generated_markdown) > 30

    def test_empty_archive_data_does_not_crash(self) -> None:
        req = ArchivePodcastPackRequest(competition_code="CPL_MEN")
        pack = build_archive_research_pack({}, req)
        assert pack.topic_type == "archive"
        assert pack.trust_note


# ---------------------------------------------------------------------------
# build_roster_research_pack tests
# ---------------------------------------------------------------------------


class TestBuildRosterResearchPack:
    def _players(self) -> list[dict]:
        data = _minimal_roster_data()
        result = []
        for team in data.get("teams", []):
            result.extend(team.get("players", []))
        return result

    def _teams(self) -> list[dict]:
        data = _minimal_roster_data()
        return [
            {"team_name": t["team_name"], "player_count": len(t.get("players", []))}
            for t in data.get("teams", [])
        ]

    def test_returns_pack(self) -> None:
        pack = build_roster_research_pack("CPL_MEN", "2024", None, self._players(), self._teams())
        assert isinstance(pack, PodcastResearchPack)

    def test_topic_type_is_roster(self) -> None:
        pack = build_roster_research_pack("CPL_MEN", "2024", None, self._players(), self._teams())
        assert pack.topic_type == "roster"

    def test_trust_note_present(self) -> None:
        pack = build_roster_research_pack("CPL_MEN", "2024", None, self._players(), self._teams())
        assert pack.trust_note
        assert "roster" in pack.trust_note.lower() or "maintained" in pack.trust_note.lower()

    def test_trust_note_section_present(self) -> None:
        pack = build_roster_research_pack("CPL_MEN", "2024", None, self._players(), self._teams())
        keys = [s.section_key for s in pack.sections]
        assert "data_trust_note" in keys or "trust_note" in keys

    def test_no_invented_stats(self) -> None:
        """Roster packs must not invent batting/bowling statistics."""
        pack = build_roster_research_pack("CPL_MEN", "2024", None, self._players(), self._teams())
        combined = " ".join(s.body for s in pack.sections if s.body).lower()
        # Should not contain invented stat phrases
        assert "average" not in combined or "stats unavailable" in combined
        # batting averages/strike rates should not be invented
        assert "strike rate" not in combined or "stats unavailable" in combined

    def test_squad_uncertainty_section_present(self) -> None:
        pack = build_roster_research_pack("CPL_MEN", "2024", None, self._players(), self._teams())
        keys = [s.section_key for s in pack.sections]
        assert "squad_uncertainty" in keys or "trust_note" in keys

    def test_returning_players_mentioned(self) -> None:
        pack = build_roster_research_pack("CPL_MEN", "2024", None, self._players(), self._teams())
        combined = " ".join(s.body for s in pack.sections if s.body).lower()
        assert "chris gayle" in combined or "returning" in combined

    def test_empty_roster_does_not_crash(self) -> None:
        pack = build_roster_research_pack("CPL_MEN", "2024", None, [], [])
        assert pack.topic_type == "roster"
        assert pack.trust_note


# ---------------------------------------------------------------------------
# _render_markdown tests
# ---------------------------------------------------------------------------


class TestRenderMarkdown:
    def test_outputs_markdown_string(self) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        md = _render_markdown(pack)
        assert isinstance(md, str)
        assert "#" in md  # should have markdown headings

    def test_contains_episode_title(self) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        md = _render_markdown(pack)
        assert "Team A" in md

    def test_contains_trust_note(self) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        md = _render_markdown(pack)
        assert "trust" in md.lower() or "derived" in md.lower()


# ---------------------------------------------------------------------------
# _render_plain_text tests
# ---------------------------------------------------------------------------


class TestRenderPlainText:
    def test_outputs_string(self) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        text = _render_plain_text(pack)
        assert isinstance(text, str)
        assert len(text) > 20

    def test_no_markdown_headers(self) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        text = _render_plain_text(pack)
        # Plain text should not have # headings
        assert "##" not in text

    def test_contains_trust_note(self) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        text = _render_plain_text(pack)
        assert "trust" in text.lower() or "derived" in text.lower()


# ---------------------------------------------------------------------------
# Saved podcast prep report tests (DB)
# ---------------------------------------------------------------------------


class TestSavedPodcastPrepReports:
    def test_create_report(self, session) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        report = run(
            create_podcast_prep_report(
                session,
                PodcastPrepReportCreate(
                    title="Test Match Report",
                    topic_type="match",
                    source_match_id="match-1",
                    generated_markdown=pack.generated_markdown,
                    generated_plain_text=pack.generated_plain_text,
                    trust_summary=pack.trust_note,
                ),
            )
        )
        assert report.id
        assert report.title == "Test Match Report"
        assert report.topic_type == "match"
        assert report.status == "draft"

    def test_create_report_has_trust_summary(self, session) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        report = run(
            create_podcast_prep_report(
                session,
                PodcastPrepReportCreate(
                    title="Trust Test",
                    topic_type="match",
                    source_match_id="match-1",
                    trust_summary=pack.trust_note,
                ),
            )
        )
        assert report.trust_summary
        assert len(report.trust_summary) > 5

    def test_get_report_by_id(self, session) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        created = run(
            create_podcast_prep_report(
                session,
                PodcastPrepReportCreate(
                    title="Get Test",
                    topic_type="match",
                    trust_summary=pack.trust_note,
                ),
            )
        )
        fetched = run(get_podcast_prep_report(session, created.id))
        assert fetched is not None
        assert fetched.id == created.id
        assert fetched.title == "Get Test"

    def test_get_nonexistent_report_returns_none(self, session) -> None:
        result = run(get_podcast_prep_report(session, "does-not-exist"))
        assert result is None

    def test_update_report_status(self, session) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        created = run(
            create_podcast_prep_report(
                session,
                PodcastPrepReportCreate(
                    title="Update Test",
                    topic_type="match",
                    trust_summary=pack.trust_note,
                ),
            )
        )
        updated = run(
            update_podcast_prep_report(
                session,
                created.id,
                PodcastPrepReportUpdate(status="reviewed"),
            )
        )
        assert updated is not None
        assert updated.status == "reviewed"

    def test_update_report_title(self, session) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        created = run(
            create_podcast_prep_report(
                session,
                PodcastPrepReportCreate(
                    title="Original Title",
                    topic_type="match",
                    trust_summary=pack.trust_note,
                ),
            )
        )
        updated = run(
            update_podcast_prep_report(
                session,
                created.id,
                PodcastPrepReportUpdate(title="Updated Title"),
            )
        )
        assert updated is not None
        assert updated.title == "Updated Title"

    def test_update_nonexistent_report_returns_none(self, session) -> None:
        result = run(
            update_podcast_prep_report(
                session,
                "no-such-id",
                PodcastPrepReportUpdate(title="Whatever"),
            )
        )
        assert result is None

    def test_list_reports_empty(self, session) -> None:
        result = run(list_podcast_prep_reports(session))
        assert result.total == 0

    def test_list_reports_after_creation(self, session) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        run(
            create_podcast_prep_report(
                session,
                PodcastPrepReportCreate(
                    title="Report One",
                    topic_type="match",
                    trust_summary=pack.trust_note,
                ),
            )
        )
        run(
            create_podcast_prep_report(
                session,
                PodcastPrepReportCreate(
                    title="Report Two",
                    topic_type="tournament",
                    trust_summary=pack.trust_note,
                ),
            )
        )
        result = run(list_podcast_prep_reports(session))
        assert result.total == 2

    def test_list_reports_filter_by_status(self, session) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        created = run(
            create_podcast_prep_report(
                session,
                PodcastPrepReportCreate(
                    title="Draft Report",
                    topic_type="match",
                    trust_summary=pack.trust_note,
                ),
            )
        )
        run(
            update_podcast_prep_report(
                session,
                created.id,
                PodcastPrepReportUpdate(status="approved"),
            )
        )
        run(
            create_podcast_prep_report(
                session,
                PodcastPrepReportCreate(
                    title="Another Draft",
                    topic_type="match",
                    trust_summary=pack.trust_note,
                ),
            )
        )
        approved = run(list_podcast_prep_reports(session, status="approved"))
        assert approved.total == 1
        assert approved.reports[0].title == "Draft Report"

    def test_report_has_generated_markdown(self, session) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        report = run(
            create_podcast_prep_report(
                session,
                PodcastPrepReportCreate(
                    title="Markdown Test",
                    topic_type="match",
                    generated_markdown=pack.generated_markdown,
                    trust_summary=pack.trust_note,
                ),
            )
        )
        assert report.generated_markdown
        assert len(report.generated_markdown) > 50

    def test_report_has_generated_plain_text(self, session) -> None:
        pack = build_match_research_pack("match-1", _minimal_match_data())
        report = run(
            create_podcast_prep_report(
                session,
                PodcastPrepReportCreate(
                    title="Plain Text Test",
                    topic_type="match",
                    generated_plain_text=pack.generated_plain_text,
                    trust_summary=pack.trust_note,
                ),
            )
        )
        assert report.generated_plain_text
        assert len(report.generated_plain_text) > 20


# ---------------------------------------------------------------------------
# Integration: rich case study data (Phase 10T.1)
# ---------------------------------------------------------------------------


def _rich_match_data() -> dict:
    """Match data structured like MatchCaseStudyResponse.model_dump()."""
    base = _minimal_match_data()
    # Override innings to use CaseStudyInningsSummary 'team' key (no batting_team)
    base["match"]["innings"] = [
        {"team": "Team A", "runs": 185, "wickets": 6, "overs": 20.0, "run_rate": 9.25},
        {"team": "Team B", "runs": 140, "wickets": 10, "overs": 18.3, "run_rate": 7.57},
    ]
    # Remove top-level innings so function reads from match.innings
    base.pop("innings", None)
    base["momentum_summary"] = {
        "title": "Team A dominated from ball one",
        "subtitle": "Consistent scoring across all phases.",
        "winning_side": "Team A",
    }
    base["key_phase"] = {
        "title": "Death overs (17-20)",
        "detail": "Team A smashed 48 runs in the final four overs.",
        "team": "Team A",
    }
    base["dismissal_patterns"] = {
        "summary": "Three wickets fell in a cluster during overs 8-11.",
        "wicket_cluster_callout": "Possible collapse window: overs 8-11 — 3 wickets in 4 overs.",
        "total_wickets": 10,
    }
    base["match_level_summary"] = "Team A dominated this T20 from the powerplay onwards."
    base["analysis_mode"] = "t20_limited_overs"
    base["match_callouts"] = [
        {"explanation": "Powerplay domination set up Team A's total.", "title": "Powerplay"}
    ]
    return base


def _rich_match_data_odi() -> dict:
    base = _rich_match_data()
    base["match"]["format"] = "ODI"
    base["odi_intelligence"] = {
        "chase_intelligence": {
            "target": 256,
            "chasing_team": "Team B",
            "initial_required_rate": 5.12,
            "chase_pressure_note": "Team B needed 12 an over from over 40.",
            "chase_result": "fell_short",
        },
        "turning_point_candidate": "The wicket of the captain in over 35 proved decisive.",
    }
    return base


def _rich_match_data_test() -> dict:
    base = _rich_match_data()
    base["match"]["format"] = "TEST"
    base["multi_day_summary"] = {
        "match_status": "won",
        "first_innings_lead_note": "Team A took a 67-run first innings lead.",
        "lead_swing_notes": ["Team B's second innings collapse shifted momentum."],
        "match_turning_point": "Wicket cluster in Team B's second innings (overs 23-28).",
        "fourth_innings_chase": {
            "target": 145,
            "chasing_team": "Team A",
            "chase_result": "completed",
        },
    }
    return base


def _rich_tournament_data() -> dict:
    base = _minimal_tournament_data()
    base["total_runs"] = 4830
    base["total_wickets"] = 220
    base["highest_team_total"] = 217
    base["highest_team_total_by"] = "TKR"
    base["venues"] = ["Queen's Park Oval", "Providence Stadium", "Sabina Park"]
    base["biggest_win_by_runs"] = {
        "match_id": "m1",
        "match_title": "TKR vs GF 2024",
        "highlight_type": "biggest_win_runs",
        "detail": "Won by 82 runs",
    }
    base["biggest_win_by_wickets"] = {
        "match_id": "m2",
        "match_title": "BAR vs JT 2024",
        "highlight_type": "biggest_win_wickets",
        "detail": "Won by 9 wickets",
    }
    base["closest_match"] = {
        "match_id": "m3",
        "match_title": "GF vs BAR 2024",
        "highlight_type": "closest_match",
        "detail": "Won by 1 run",
    }
    # Augment podcast_facts
    base.setdefault("podcast_facts", {})
    base["podcast_facts"]["strongest_team_by_wins"] = "Trinbago Knight Riders"
    base["podcast_facts"]["key_journey_note"] = "TKR won all three knockout stage matches."
    base["podcast_facts"]["closest_finish_match_title"] = "GF vs BAR 2024"
    base["knockout_context"] = {
        "champion_team": "Trinbago Knight Riders",
        "runner_up_team": "Barbados Royals",
        "final_result": "TKR won by 28 runs",
        "semi_final_matches": [
            {
                "match_id": "sf1",
                "match_title": "TKR vs SLK Semi-Final",
                "highlight_type": "semi_final",
                "result": "TKR won by 5 wickets",
            },
            {
                "match_id": "sf2",
                "match_title": "BAR vs GF Semi-Final",
                "highlight_type": "semi_final",
                "result": "BAR won by 3 runs",
            },
        ],
    }
    return base


class TestMatchPackRichCaseStudy:
    """Phase 10T.1: match pack reads from MatchCaseStudyResponse format."""

    def test_scoreboard_from_match_innings(self) -> None:
        """Innings from match.innings (CaseStudyInningsSummary format) appear in scoreboard."""
        pack = build_match_research_pack("m1", _rich_match_data())
        kf = next((s for s in pack.sections if s.section_key == "key_facts"), None)
        assert kf is not None
        assert kf.body is not None
        assert "Team A" in kf.body
        assert "185" in kf.body

    def test_momentum_verdict_section_present(self) -> None:
        pack = build_match_research_pack("m1", _rich_match_data())
        mv = next((s for s in pack.sections if s.section_key == "momentum_verdict"), None)
        assert mv is not None
        assert mv.body is not None
        assert "Team A dominated" in mv.body

    def test_key_phase_section_present(self) -> None:
        pack = build_match_research_pack("m1", _rich_match_data())
        kp = next((s for s in pack.sections if s.section_key == "key_phase"), None)
        assert kp is not None
        assert kp.body is not None
        assert "Death overs" in kp.body

    def test_dismissal_patterns_section_present(self) -> None:
        pack = build_match_research_pack("m1", _rich_match_data())
        dp = next((s for s in pack.sections if s.section_key == "dismissal_patterns"), None)
        assert dp is not None
        assert dp.body is not None
        assert "cluster" in dp.body.lower()

    def test_callout_explanation_used(self) -> None:
        """CaseStudyAnalystCallout uses 'explanation' not 'text'."""
        pack = build_match_research_pack("m1", _rich_match_data())
        ttp = next((s for s in pack.sections if s.section_key == "tactical_talking_points"), None)
        assert ttp is not None
        assert ttp.body is not None
        assert "Powerplay domination" in ttp.body

    def test_odi_intelligence_section(self) -> None:
        pack = build_match_research_pack("m-odi", _rich_match_data_odi())
        odi = next((s for s in pack.sections if s.section_key == "odi_intelligence"), None)
        assert odi is not None
        assert odi.body is not None
        assert "256" in odi.body

    def test_test_match_section(self) -> None:
        pack = build_match_research_pack("m-test", _rich_match_data_test())
        tmi = next((s for s in pack.sections if s.section_key == "test_match_intelligence"), None)
        assert tmi is not None
        assert tmi.body is not None
        assert "first innings" in tmi.body.lower() or "lead" in tmi.body.lower()

    def test_source_note_references_case_study(self) -> None:
        """Section notes mention Match Case Study as source."""
        pack = build_match_research_pack("m1", _rich_match_data())
        mv = next((s for s in pack.sections if s.section_key == "momentum_verdict"), None)
        assert mv is not None
        assert "Case Study" in mv.note


class TestTournamentPackRichIntelligence:
    """Phase 10T.1: tournament pack uses rich TournamentSummaryResponse data."""

    def test_total_runs_in_setup(self) -> None:
        pack = build_tournament_research_pack("CPL_MEN", "2024", "men", _rich_tournament_data())
        setup = next((s for s in pack.sections if s.section_key == "tournament_setup"), None)
        assert setup is not None
        assert setup.body is not None
        assert "4830" in setup.body

    def test_biggest_win_runs_section(self) -> None:
        pack = build_tournament_research_pack("CPL_MEN", "2024", "men", _rich_tournament_data())
        mm = next((s for s in pack.sections if s.section_key == "key_match_moments"), None)
        assert mm is not None
        assert mm.body is not None
        assert "82 runs" in mm.body

    def test_biggest_win_wickets_section(self) -> None:
        pack = build_tournament_research_pack("CPL_MEN", "2024", "men", _rich_tournament_data())
        mm = next((s for s in pack.sections if s.section_key == "key_match_moments"), None)
        assert mm is not None
        assert mm.body is not None
        assert "9 wickets" in mm.body

    def test_closest_match_section(self) -> None:
        pack = build_tournament_research_pack("CPL_MEN", "2024", "men", _rich_tournament_data())
        mm = next((s for s in pack.sections if s.section_key == "key_match_moments"), None)
        assert mm is not None
        assert "1 run" in mm.body

    def test_venue_patterns_section(self) -> None:
        pack = build_tournament_research_pack("CPL_MEN", "2024", "men", _rich_tournament_data())
        vp = next((s for s in pack.sections if s.section_key == "venue_scoring_patterns"), None)
        assert vp is not None
        assert vp.body is not None
        assert "Queen's Park Oval" in vp.body

    def test_strongest_team_in_key_facts(self) -> None:
        pack = build_tournament_research_pack("CPL_MEN", "2024", "men", _rich_tournament_data())
        kf = next((s for s in pack.sections if s.section_key == "key_facts"), None)
        assert kf is not None
        assert kf.body is not None
        assert "Trinbago" in kf.body

    def test_semi_finals_in_champion_story(self) -> None:
        pack = build_tournament_research_pack("CPL_MEN", "2024", "men", _rich_tournament_data())
        cs = next((s for s in pack.sections if s.section_key == "champion_story"), None)
        assert cs is not None
        assert cs.body is not None
        assert "Semi-final" in cs.body

    def test_key_journey_note_in_champion_story(self) -> None:
        pack = build_tournament_research_pack("CPL_MEN", "2024", "men", _rich_tournament_data())
        cs = next((s for s in pack.sections if s.section_key == "champion_story"), None)
        assert cs is not None
        assert cs.body is not None
        assert "knockout stage" in cs.body

    def test_source_note_references_tournament_intelligence(self) -> None:
        pack = build_tournament_research_pack("CPL_MEN", "2024", "men", _rich_tournament_data())
        mm = next((s for s in pack.sections if s.section_key == "key_match_moments"), None)
        assert mm is not None
        assert "Tournament Intelligence" in mm.note
