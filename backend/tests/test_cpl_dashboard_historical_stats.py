"""CPL Dashboard — historical stats backend tests.

Validates:
- The historical-stats summary endpoint correctly returns CPL competition data
  when CPL matches are imported.
- Empty CPL state handled safely (no CPL data returns empty lists, not errors).
- CPL competition name detection matches "Caribbean Premier League" variants.
- No fabrication: all aggregates come from imported match data only.
- No mutation of official Game truth fields.

These tests use the simulated_t20_match.json fixture for non-CPL imports and
a CPL-tagged fixture variant to test competition-aware filtering.
"""

from __future__ import annotations

import json
import os
import uuid as _uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")

from backend.main import fastapi_app
from backend.sql_app import models
from backend.sql_app.database import get_db

# ── Fixture paths ──────────────────────────────────────────────────────────

FIXTURE_PATH = Path(__file__).resolve().parent / "simulated_t20_match.json"


# ── Auth helpers ───────────────────────────────────────────────────────────


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def register_user(client: TestClient, email: str, password: str = "secret123") -> dict[str, Any]:
    resp = client.post("/auth/register", json={"email": email, "password": password})
    assert resp.status_code == 201, resp.text
    login_resp = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert login_resp.status_code == 200, login_resp.text
    token = login_resp.json()["access_token"]
    me_resp = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200, me_resp.text
    return me_resp.json()


def login_user(client: TestClient, email: str, password: str = "secret123") -> str:
    resp = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


async def _set_user_role(
    session_maker: async_sessionmaker,
    email: str,
    role: models.RoleEnum,
) -> None:
    async with session_maker() as session:
        result = await session.execute(select(models.User).where(models.User.email == email))
        user = result.scalar_one()
        user.role = role
        await session.commit()


async def set_role(client: TestClient, email: str, role: models.RoleEnum) -> None:
    session_maker = client.session_maker  # type: ignore[attr-defined]
    await _set_user_role(session_maker, email, role)


# ── Fixtures ───────────────────────────────────────────────────────────────


@pytest.fixture
def client() -> TestClient:
    from backend.sql_app.database import SessionLocal

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db

    with TestClient(fastapi_app) as test_client:
        test_client.session_maker = SessionLocal  # type: ignore[attr-defined]
        yield test_client

    fastapi_app.dependency_overrides.pop(get_db, None)


def _analyst_token(client: TestClient) -> str:
    """Register and return a token for a fresh analyst_pro user."""
    import asyncio

    email = f"cpl-test-{_uuid.uuid4().hex[:8]}@example.com"
    user = register_user(client, email)
    asyncio.get_event_loop().run_until_complete(
        set_role(client, user["email"], models.RoleEnum.analyst_pro)
    )
    return login_user(client, email)


def _load_fixture() -> dict[str, Any]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _make_cpl_fixture(
    match_number: int = 1,
    season: str = "2023",
    *,
    team_a: str = "Team Alpha",
    team_b: str = "Team Beta",
    winner: str | None = None,
) -> dict[str, Any]:
    """Return a CPL-tagged fixture variant.

    Sets event.name to 'Caribbean Premier League' and a unique match_number
    so each call produces a non-duplicate entry.
    """
    fixture = deepcopy(_load_fixture())
    info = fixture.setdefault("info", {})
    if not isinstance(info, dict):
        return fixture
    event = info.setdefault("event", {})
    if isinstance(event, dict):
        event["match_number"] = match_number
        event["name"] = "Caribbean Premier League"
    info["season"] = season
    if winner:
        info["outcome"] = {"winner": winner, "by": {"wickets": 5}}
        fixture["result"] = {"winner": winner, "summary": f"{winner} won by 5 wickets"}
    # Unique dates to avoid collision
    info["dates"] = [f"2023-08-{(match_number % 28) + 1:02d}"]
    fixture["teams"] = [team_a, team_b]
    innings = fixture.get("innings")
    if isinstance(innings, list):
        if len(innings) > 0 and isinstance(innings[0], dict):
            innings[0]["team"] = team_a
        if len(innings) > 1 and isinstance(innings[1], dict):
            innings[1]["team"] = team_b
    return fixture


def _apply_fixture(client: TestClient, token: str, payload: dict[str, Any]) -> tuple[str, str]:
    """Run dry-run + apply, return (batch_id, game_id)."""
    dry_run_resp = client.post(
        "/api/historical-import/json/dry-run",
        headers=_auth_headers(token),
        params={"record_preview": "true"},
        json=payload,
    )
    assert dry_run_resp.status_code == 200, dry_run_resp.text
    batch_id = dry_run_resp.json()["record_id"]
    assert batch_id

    apply_resp = client.post(
        f"/api/historical-import/json/batches/{batch_id}/apply",
        headers=_auth_headers(token),
        json={"confirm": True},
    )
    assert apply_resp.status_code == 200, apply_resp.text
    game_id = apply_resp.json()["applied_game_id"]
    assert game_id
    return batch_id, game_id


# ── Tests ──────────────────────────────────────────────────────────────────


def test_summary_empty_when_no_cpl_imports(client: TestClient) -> None:
    """When no historical matches exist, competitions list is empty.

    The CPL dashboard must handle this state safely — returning empty lists
    is the correct no-data state (not an error, not fake data).
    """
    token = _analyst_token(client)
    resp = client.get("/analytics/historical-stats/summary", headers=_auth_headers(token))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["competitions"] == []
    assert data["total_eligible_matches"] == 0
    # No fabricated data in response
    assert data["players"] == []
    assert data["venues"] == []


def test_summary_schema_fields_present(client: TestClient) -> None:
    """The summary response must include all required schema fields for the dashboard."""
    token = _analyst_token(client)
    resp = client.get("/analytics/historical-stats/summary", headers=_auth_headers(token))
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Required top-level fields
    required_fields = [
        "total_eligible_matches",
        "excluded_metadata_only_count",
        "excluded_invalid_count",
        "matches",
        "players",
        "teams",
        "venues",
        "competitions",
        "seasons",
        "generated_at",
        "note",
    ]
    for field in required_fields:
        assert field in data, f"Missing required field: {field}"


def test_cpl_match_appears_in_competitions(client: TestClient) -> None:
    """A CPL-tagged imported match must appear under competitions with the CPL name."""
    token = _analyst_token(client)
    cpl_payload = _make_cpl_fixture(match_number=1, season="2023")
    _apply_fixture(client, token, cpl_payload)

    resp = client.get("/analytics/historical-stats/summary", headers=_auth_headers(token))
    assert resp.status_code == 200, resp.text
    data = resp.json()

    assert data["total_eligible_matches"] >= 1
    competition_names = [c["competition"] for c in data["competitions"]]
    assert any(
        "caribbean premier league" in (name or "").lower() or "cpl" in (name or "").lower()
        for name in competition_names
    ), f"Expected CPL competition in {competition_names}"


def test_cpl_match_appears_in_matches_list(client: TestClient) -> None:
    """The matches list must include the CPL game after import."""
    token = _analyst_token(client)
    cpl_payload = _make_cpl_fixture(match_number=2, season="2023")
    _batch_id, game_id = _apply_fixture(client, token, cpl_payload)

    resp = client.get("/analytics/historical-stats/summary", headers=_auth_headers(token))
    assert resp.status_code == 200, resp.text
    data = resp.json()

    match_ids = [m["match_id"] for m in data["matches"]]
    assert game_id in match_ids, f"Expected CPL game {game_id} in matches"


def test_cpl_match_competition_field_is_cpl(client: TestClient) -> None:
    """The competition field on the MatchAggregate for a CPL match must be CPL."""
    token = _analyst_token(client)
    cpl_payload = _make_cpl_fixture(match_number=3, season="2023")
    _batch_id, game_id = _apply_fixture(client, token, cpl_payload)

    resp = client.get(
        f"/analytics/historical-stats/match/{game_id}",
        headers=_auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    match = resp.json()["match"]
    competition = (match.get("competition") or "").lower()
    assert (
        "caribbean premier league" in competition or "cpl" in competition
    ), f"Expected CPL competition, got: {match.get('competition')!r}"


def test_cpl_season_appears_in_seasons_list(client: TestClient) -> None:
    """A CPL season value must appear in the seasons aggregate list."""
    token = _analyst_token(client)
    cpl_payload = _make_cpl_fixture(match_number=4, season="2023")
    _apply_fixture(client, token, cpl_payload)

    resp = client.get("/analytics/historical-stats/summary", headers=_auth_headers(token))
    assert resp.status_code == 200, resp.text
    data = resp.json()

    season_values = [s["season"] for s in data["seasons"]]
    assert any(
        "2023" in (s or "") for s in season_values
    ), f"Expected 2023 season in {season_values}"


def test_no_official_truth_mutation(client: TestClient) -> None:
    """Calling the stats endpoint must not mutate any Game truth fields.

    Reads the key Game fields before and after the stats endpoint call and
    verifies they are unchanged. This is the no-mutation contract.
    """
    import asyncio

    token = _analyst_token(client)
    _batch_id, game_id = _apply_fixture(client, token, _make_cpl_fixture(match_number=5))

    # Capture pre-call state
    session_maker = client.session_maker  # type: ignore[attr-defined]

    async def _read_game() -> dict[str, Any]:
        async with session_maker() as session:
            result = await session.execute(select(models.Game).where(models.Game.id == game_id))
            game = result.scalar_one_or_none()
            assert game is not None
            return {
                "status": game.status,
                "total_runs": game.total_runs,
                "result": game.result,
            }

    before = asyncio.get_event_loop().run_until_complete(_read_game())

    # Call the stats endpoint
    resp = client.get("/analytics/historical-stats/summary", headers=_auth_headers(token))
    assert resp.status_code == 200, resp.text

    after = asyncio.get_event_loop().run_until_complete(_read_game())

    assert (
        before == after
    ), f"Game truth fields were mutated by stats endpoint!\nBefore: {before}\nAfter: {after}"


def test_non_cpl_match_excluded_from_cpl_competition(client: TestClient) -> None:
    """A non-CPL match must NOT appear in the CPL competition aggregate.

    The fixture uses the default event name from simulated_t20_match.json, which
    is not "Caribbean Premier League". It must not contaminate CPL stats.
    """
    token = _analyst_token(client)
    non_cpl_payload = _load_fixture()
    _apply_fixture(client, token, non_cpl_payload)

    resp = client.get("/analytics/historical-stats/summary", headers=_auth_headers(token))
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # Either no competitions, or none of them are CPL
    cpl_competitions = [
        c
        for c in data["competitions"]
        if "caribbean premier league" in (c["competition"] or "").lower()
        or "cpl" in (c["competition"] or "").lower()
    ]
    assert (
        cpl_competitions == []
    ), f"Non-CPL match should not appear in CPL competition list: {cpl_competitions}"


def test_summary_note_field_is_deterministic(client: TestClient) -> None:
    """The summary note must be a deterministic provenance statement, not AI-generated."""
    token = _analyst_token(client)
    resp = client.get("/analytics/historical-stats/summary", headers=_auth_headers(token))
    assert resp.status_code == 200, resp.text
    data = resp.json()

    note = data.get("note", "")
    assert isinstance(note, str)
    assert len(note) > 0
    # Must mention deterministic / historical import origin
    note_lower = note.lower()
    assert (
        "deterministic" in note_lower or "historical" in note_lower
    ), f"Expected deterministic provenance note, got: {note!r}"


def test_summary_top_team_by_wins_uses_alias_continuity(client: TestClient) -> None:
    token = _analyst_token(client)
    for match_number in range(31, 37):
        _apply_fixture(
            client,
            token,
            _make_cpl_fixture(
                match_number=match_number,
                season="2023" if match_number % 2 else "2024",
                team_a="Barbados Tridents" if match_number % 2 else "Barbados Royals",
                team_b="Jamaica Tallawahs" if match_number % 2 else "Guyana Amazon Warriors",
                winner="Barbados Tridents" if match_number % 2 else "Barbados Royals",
            ),
        )

    resp = client.get("/analytics/historical-stats/summary", headers=_auth_headers(token))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    leader = data.get("top_team_by_wins")
    assert leader is not None
    assert leader["team_name"] == "Barbados Royals"
    assert leader["wins"] >= 6
    assert data["diagnostics"]["matches_with_parsed_winner"] >= 6


def test_summary_scorecard_wicket_fallback_is_reported(client: TestClient) -> None:
    import asyncio

    token = _analyst_token(client)
    _batch_id, game_id = _apply_fixture(client, token, _make_cpl_fixture(match_number=40))
    session_maker = client.session_maker  # type: ignore[attr-defined]

    async def _mutate_game_for_scorecard_fallback() -> None:
        async with session_maker() as session:
            result = await session.execute(select(models.Game).where(models.Game.id == game_id))
            game = result.scalar_one()
            phases = dict(game.phases or {})
            innings = phases.get("historical_innings_summary") or []
            if isinstance(innings, list) and len(innings) > 0 and isinstance(innings[0], dict):
                innings[0]["wickets"] = None
                innings[0]["score"] = "157/6"
            phases["historical_innings_summary"] = innings
            hist_meta = dict(phases.get("historical_import") or {})
            hist_meta["deliveries_imported"] = False
            phases["historical_import"] = hist_meta
            game.phases = phases
            game.deliveries = []
            await session.commit()

    asyncio.get_event_loop().run_until_complete(_mutate_game_for_scorecard_fallback())

    resp = client.get("/analytics/historical-stats/summary", headers=_auth_headers(token))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    match = next(m for m in data["matches"] if m["match_id"] == game_id)
    assert match["total_wickets"] > 0
    assert match["wicket_derivation_source"] == "scorecard"
    assert data["diagnostics"]["scorecard_derived_wicket_matches"] >= 1


def test_summary_includes_deterministic_case_studies(client: TestClient) -> None:
    token = _analyst_token(client)
    _apply_fixture(client, token, _make_cpl_fixture(match_number=51, season="2023"))

    resp = client.get("/analytics/historical-stats/summary", headers=_auth_headers(token))
    assert resp.status_code == 200, resp.text
    data = resp.json()
    case_ids = {entry["id"] for entry in data.get("case_studies", [])}
    assert "high_scoring_match" in case_ids
    assert "venue_scoring_pattern" in case_ids
