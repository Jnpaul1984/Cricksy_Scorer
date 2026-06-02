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
    PodcastResearchSection,
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
                "era_label": "Early Era (2014–2016)",
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
        combined = " ".join(
            s.body for s in pack.sections if s.body
        ) + (pack.match_context or "")
        assert "delivered scored" not in combined.lower()

    def test_no_1_runs_in_output(self) -> None:
        data = _minimal_match_data(result="Team A won by 1 runs")
        pack = build_match_research_pack("match-1", data)
        combined = " ".join(
            s.body for s in pack.sections if s.body
        ) + (pack.match_context or "")
        assert "1 runs" not in combined

    def test_no_1_wickets_in_output(self) -> None:
        data = _minimal_match_data(result="Team A won by 1 wickets")
        pack = build_match_research_pack("match-1", data)
        combined = " ".join(
            s.body for s in pack.sections if s.body
        ) + (pack.match_context or "")
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
        player_section = next(
            (s for s in pack.sections if s.section_key == "player_focus"), None
        )
        assert player_section is not None
        assert "1 wicket" in (player_section.body or "")
        assert "1 wickets" not in (player_section.body or "")


# ---------------------------------------------------------------------------
# build_tournament_research_pack tests
# ---------------------------------------------------------------------------


class TestBuildTournamentResearchPack:
    def test_returns_pack(self) -> None:
        pack = build_tournament_research_pack(
            "CPL_MEN", "2024", "men", _minimal_tournament_data()
        )
        assert isinstance(pack, PodcastResearchPack)

    def test_topic_type_is_tournament(self) -> None:
        pack = build_tournament_research_pack(
            "CPL_MEN", "2024", "men", _minimal_tournament_data()
        )
        assert pack.topic_type == "tournament"

    def test_trust_note_present(self) -> None:
        pack = build_tournament_research_pack(
            "CPL_MEN", "2024", "men", _minimal_tournament_data()
        )
        assert pack.trust_note
        assert "not official" in pack.trust_note.lower() or "derived" in pack.trust_note.lower()

    def test_trust_note_section_present(self) -> None:
        pack = build_tournament_research_pack(
            "CPL_MEN", "2024", "men", _minimal_tournament_data()
        )
        keys = [s.section_key for s in pack.sections]
        assert "data_trust_note" in keys or "trust_note" in keys

    def test_sections_include_opening_hook(self) -> None:
        pack = build_tournament_research_pack(
            "CPL_MEN", "2024", "men", _minimal_tournament_data()
        )
        keys = [s.section_key for s in pack.sections]
        assert "opening_hook" in keys

    def test_generated_markdown_not_empty(self) -> None:
        pack = build_tournament_research_pack(
            "CPL_MEN", "2024", "men", _minimal_tournament_data()
        )
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
        pack = build_roster_research_pack(
            "CPL_MEN", "2024", None, self._players(), self._teams()
        )
        assert isinstance(pack, PodcastResearchPack)

    def test_topic_type_is_roster(self) -> None:
        pack = build_roster_research_pack(
            "CPL_MEN", "2024", None, self._players(), self._teams()
        )
        assert pack.topic_type == "roster"

    def test_trust_note_present(self) -> None:
        pack = build_roster_research_pack(
            "CPL_MEN", "2024", None, self._players(), self._teams()
        )
        assert pack.trust_note
        assert "roster" in pack.trust_note.lower() or "maintained" in pack.trust_note.lower()

    def test_trust_note_section_present(self) -> None:
        pack = build_roster_research_pack(
            "CPL_MEN", "2024", None, self._players(), self._teams()
        )
        keys = [s.section_key for s in pack.sections]
        assert "data_trust_note" in keys or "trust_note" in keys

    def test_no_invented_stats(self) -> None:
        """Roster packs must not invent batting/bowling statistics."""
        pack = build_roster_research_pack(
            "CPL_MEN", "2024", None, self._players(), self._teams()
        )
        combined = " ".join(s.body for s in pack.sections if s.body).lower()
        # Should not contain invented stat phrases
        assert "average" not in combined or "stats unavailable" in combined
        # batting averages/strike rates should not be invented
        assert "strike rate" not in combined or "stats unavailable" in combined

    def test_squad_uncertainty_section_present(self) -> None:
        pack = build_roster_research_pack(
            "CPL_MEN", "2024", None, self._players(), self._teams()
        )
        keys = [s.section_key for s in pack.sections]
        assert "squad_uncertainty" in keys or "trust_note" in keys

    def test_returning_players_mentioned(self) -> None:
        pack = build_roster_research_pack(
            "CPL_MEN", "2024", None, self._players(), self._teams()
        )
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
                PodcastPrepReportUpdate(
                    status="reviewed"
                ),
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
                PodcastPrepReportUpdate(
                    status="approved"
                ),
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
        approved = run(
            list_podcast_prep_reports(
                session, status="approved"
            )
        )
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
