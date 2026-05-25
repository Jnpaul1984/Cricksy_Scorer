"""Phase 10M — Analyst Data Registry tests.

Validates:
- Competition classification (CPL_MEN, WCPL, unknown)
- Gender classification (men, women, unknown)
- Source type classification (historical_import, cricksy_completed_scored, unknown)
- Data completeness classification (delivery_complete, phase_level, innings_totals, metadata_only)
- Registry endpoint returns correct entries and diagnostics
- Women's records are never mixed into men's
- Unknown values remain visible and do not break the endpoint

Run:
    cd backend
    CRICKSY_IN_MEMORY_DB=1 APP_SECRET_KEY=test-secret-key \\
      python -m pytest tests/test_analyst_registry.py -v
"""

from __future__ import annotations

import asyncio
import json
import os
import uuid as _uuid
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")

from backend.main import fastapi_app  # noqa: E402
from backend.sql_app import models  # noqa: E402
from backend.sql_app.database import get_db  # noqa: E402
from backend.services.analyst_registry_service import (  # noqa: E402
    classify_competition,
    classify_gender,
    classify_source_type,
    classify_data_completeness,
)

# ---------------------------------------------------------------------------
# Classification unit tests — no database needed
# ---------------------------------------------------------------------------


class TestCompetitionClassification:
    def test_cpl_men_full_name(self) -> None:
        code, name = classify_competition("Caribbean Premier League")
        assert code == "CPL_MEN"
        assert "Caribbean Premier League" in name

    def test_cpl_men_abbreviation(self) -> None:
        code, _ = classify_competition("CPL 2024")
        assert code == "CPL_MEN"

    def test_cpl_men_case_insensitive(self) -> None:
        code, _ = classify_competition("caribbean premier league")
        assert code == "CPL_MEN"

    def test_wcpl_abbreviation(self) -> None:
        code, _ = classify_competition("WCPL")
        assert code == "WCPL"

    def test_wcpl_full_name(self) -> None:
        code, _ = classify_competition("Women's Caribbean Premier League")
        assert code == "WCPL"

    def test_wcpl_apostrophe_variants(self) -> None:
        code, _ = classify_competition("Womens Caribbean Premier League")
        assert code == "WCPL"

    def test_womens_cpl_variant(self) -> None:
        code, _ = classify_competition("Women's CPL")
        assert code == "WCPL"

    def test_unknown_competition(self) -> None:
        code, _ = classify_competition("Super50 Cup")
        assert code == "unknown"

    def test_empty_name_is_unknown(self) -> None:
        code, _ = classify_competition("")
        assert code == "unknown"

    def test_none_is_unknown(self) -> None:
        code, _ = classify_competition(None)
        assert code == "unknown"

    def test_cpl_with_women_marker_is_wcpl(self) -> None:
        # "CPL Women" should NOT be classified as CPL_MEN
        code, _ = classify_competition("CPL Women 2024")
        assert code != "CPL_MEN"

    def test_local_competition_is_unknown(self) -> None:
        code, _ = classify_competition("Local School Tournament")
        assert code == "unknown"


class TestGenderClassification:
    def test_wcpl_is_women(self) -> None:
        assert classify_gender("WCPL") == "women"

    def test_cpl_men_is_men(self) -> None:
        assert classify_gender("CPL_MEN") == "men"

    def test_unknown_competition_is_unknown_gender(self) -> None:
        assert classify_gender("unknown") == "unknown"

    def test_gender_metadata_women(self) -> None:
        assert classify_gender("unknown", "female") == "women"
        assert classify_gender("unknown", "women") == "women"
        assert classify_gender("unknown", "f") == "women"

    def test_gender_metadata_men(self) -> None:
        assert classify_gender("unknown", "male") == "men"
        assert classify_gender("unknown", "men") == "men"
        assert classify_gender("unknown", "m") == "men"

    def test_gender_metadata_mixed(self) -> None:
        assert classify_gender("unknown", "mixed") == "mixed"

    def test_unknown_gender_not_forced_into_men(self) -> None:
        # An unknown competition with no gender metadata must stay unknown
        result = classify_gender("unknown", None)
        assert result == "unknown"
        assert result != "men"

    def test_competition_code_overrides_metadata(self) -> None:
        # WCPL always means women regardless of metadata
        assert classify_gender("WCPL", "men") == "women"
        assert classify_gender("CPL_MEN", "female") == "men"


class TestDataCompletenessClassification:
    """Unit tests for classify_data_completeness using mock Game objects."""

    class _MockGame:
        """Minimal Game-like object for testing."""
        def __init__(
            self,
            phases: dict | None = None,
            deliveries: list | None = None,
            first_inning_summary: dict | None = None,
        ) -> None:
            self.phases = phases or {}
            self.deliveries = deliveries
            self.first_inning_summary = first_inning_summary

    def test_delivery_complete_via_deliveries_flag(self) -> None:
        game = self._MockGame(phases={"historical_import": {"is_historical": True}})
        hist_meta = {"deliveries_imported": True}
        result = classify_data_completeness(game, hist_meta)  # type: ignore[arg-type]
        assert result == "delivery_complete"

    def test_delivery_complete_via_deliveries_list(self) -> None:
        game = self._MockGame(
            phases={},
            deliveries=[{"inning": 1, "runs_off_bat": 4}],
        )
        result = classify_data_completeness(game, None)  # type: ignore[arg-type]
        assert result == "delivery_complete"

    def test_phase_level_when_phases_present(self) -> None:
        game = self._MockGame(
            phases={"powerplay": {"runs": 50, "wickets": 1}},
        )
        result = classify_data_completeness(game, None)  # type: ignore[arg-type]
        assert result == "phase_level"

    def test_innings_totals_via_historical_innings_summary(self) -> None:
        game = self._MockGame(
            phases={
                "historical_innings_summary": [{"inning_no": 1, "runs": 180}]
            }
        )
        result = classify_data_completeness(game, None)  # type: ignore[arg-type]
        assert result == "innings_totals"

    def test_innings_totals_via_first_inning_summary(self) -> None:
        game = self._MockGame(first_inning_summary={"runs": 140})
        result = classify_data_completeness(game, None)  # type: ignore[arg-type]
        assert result == "innings_totals"

    def test_metadata_only_when_nothing_present(self) -> None:
        game = self._MockGame()
        result = classify_data_completeness(game, None)  # type: ignore[arg-type]
        assert result == "metadata_only"

    def test_delivery_beats_phase_beats_innings(self) -> None:
        """delivery_complete > phase_level > innings_totals."""
        game = self._MockGame(
            phases={
                "powerplay": {"runs": 50},
                "historical_innings_summary": [{"inning_no": 1, "runs": 180}],
            },
            deliveries=[{"inning": 1, "runs_off_bat": 1}],
        )
        result = classify_data_completeness(game, None)  # type: ignore[arg-type]
        assert result == "delivery_complete"


# ---------------------------------------------------------------------------
# Integration tests — registry endpoint
# ---------------------------------------------------------------------------

_FIXTURE_PATH = Path(__file__).parent / "simulated_t20_match.json"


def _load_fixture() -> dict[str, Any]:
    with open(_FIXTURE_PATH) as f:
        return json.load(f)


def _make_cpl_fixture(
    match_number: int = 1,
    season: str | None = "2023",
    *,
    competition: str = "Caribbean Premier League",
) -> dict[str, Any]:
    fixture = deepcopy(_load_fixture())
    info = fixture.setdefault("info", {})
    if isinstance(info, dict):
        event = info.setdefault("event", {})
        if isinstance(event, dict):
            event["match_number"] = match_number
            event["name"] = competition
        if season is None:
            info.pop("season", None)
        else:
            info["season"] = season
        info["dates"] = [f"2023-08-{(match_number % 28) + 1:02d}"]
    return fixture


def _make_wcpl_fixture(match_number: int = 1) -> dict[str, Any]:
    return _make_cpl_fixture(
        match_number=match_number,
        competition="Women's Caribbean Premier League",
    )


def _register_user(client: TestClient, email: str, password: str = "secret123") -> dict[str, Any]:
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


def _login_user(client: TestClient, email: str, password: str = "secret123") -> str:
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


def _analyst_token(client: TestClient) -> str:
    email = f"reg-test-{_uuid.uuid4().hex[:8]}@example.com"
    user = _register_user(client, email)
    asyncio.get_event_loop().run_until_complete(
        _set_user_role(client.session_maker, user["email"], models.RoleEnum.analyst_pro)  # type: ignore[attr-defined]
    )
    return _login_user(client, email)


def _auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


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


class TestAnalystRegistryEndpoint:
    def test_registry_empty_when_no_matches(self, client: TestClient) -> None:
        token = _analyst_token(client)
        resp = client.get("/analytics/matches/registry", headers=_auth_headers(token))
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["entries"] == []
        assert data["total"] == 0
        assert "diagnostics" in data

    def test_registry_requires_auth(self, client: TestClient) -> None:
        resp = client.get("/analytics/matches/registry")
        assert resp.status_code in (401, 403)

    def test_cpl_match_appears_in_registry_with_cpl_men(self, client: TestClient) -> None:
        token = _analyst_token(client)
        _apply_fixture(client, token, _make_cpl_fixture(match_number=1))

        resp = client.get("/analytics/matches/registry", headers=_auth_headers(token))
        assert resp.status_code == 200, resp.text
        data = resp.json()

        assert data["total"] >= 1
        entries = data["entries"]
        cpl_entries = [e for e in entries if e["competition_code"] == "CPL_MEN"]
        assert len(cpl_entries) >= 1

    def test_cpl_match_gender_is_men(self, client: TestClient) -> None:
        token = _analyst_token(client)
        _apply_fixture(client, token, _make_cpl_fixture(match_number=2))

        resp = client.get("/analytics/matches/registry", headers=_auth_headers(token))
        assert resp.status_code == 200, resp.text
        data = resp.json()
        cpl_entries = [e for e in data["entries"] if e["competition_code"] == "CPL_MEN"]
        assert all(e["gender_category"] == "men" for e in cpl_entries)

    def test_wcpl_match_appears_with_wcpl_code(self, client: TestClient) -> None:
        token = _analyst_token(client)
        _apply_fixture(client, token, _make_wcpl_fixture(match_number=3))

        resp = client.get("/analytics/matches/registry", headers=_auth_headers(token))
        assert resp.status_code == 200, resp.text
        data = resp.json()
        wcpl_entries = [e for e in data["entries"] if e["competition_code"] == "WCPL"]
        assert len(wcpl_entries) >= 1

    def test_wcpl_match_gender_is_women(self, client: TestClient) -> None:
        token = _analyst_token(client)
        _apply_fixture(client, token, _make_wcpl_fixture(match_number=4))

        resp = client.get("/analytics/matches/registry", headers=_auth_headers(token))
        assert resp.status_code == 200, resp.text
        data = resp.json()
        wcpl_entries = [e for e in data["entries"] if e["competition_code"] == "WCPL"]
        assert all(e["gender_category"] == "women" for e in wcpl_entries), (
            "WCPL matches must always have gender_category='women'"
        )

    def test_women_not_mixed_into_men(self, client: TestClient) -> None:
        token = _analyst_token(client)
        _apply_fixture(client, token, _make_wcpl_fixture(match_number=5))
        _apply_fixture(client, token, _make_cpl_fixture(match_number=6))

        resp = client.get("/analytics/matches/registry", headers=_auth_headers(token))
        data = resp.json()
        men_entries = [e for e in data["entries"] if e["gender_category"] == "men"]
        women_entries = [e for e in data["entries"] if e["gender_category"] == "women"]
        # No overlap: men should not contain WCPL, women should not contain CPL_MEN
        assert all(e["competition_code"] != "WCPL" for e in men_entries)
        assert all(e["competition_code"] != "CPL_MEN" for e in women_entries)

    def test_source_type_is_historical_import(self, client: TestClient) -> None:
        token = _analyst_token(client)
        _apply_fixture(client, token, _make_cpl_fixture(match_number=7))

        resp = client.get("/analytics/matches/registry", headers=_auth_headers(token))
        data = resp.json()
        assert all(
            e["source_type"] == "historical_import"
            for e in data["entries"]
        )

    def test_registry_has_diagnostics(self, client: TestClient) -> None:
        token = _analyst_token(client)
        _apply_fixture(client, token, _make_cpl_fixture(match_number=8))

        resp = client.get("/analytics/matches/registry", headers=_auth_headers(token))
        data = resp.json()
        diag = data["diagnostics"]
        assert "total" in diag
        assert "CPL_MEN" in diag
        assert "WCPL" in diag
        assert "gender_men" in diag
        assert "gender_women" in diag
        assert "gender_unknown" in diag
        assert "historical_import" in diag
        assert "delivery_complete" in diag
        assert "analyst_ready" in diag

    def test_registry_completeness_field_present(self, client: TestClient) -> None:
        token = _analyst_token(client)
        _apply_fixture(client, token, _make_cpl_fixture(match_number=9))

        resp = client.get("/analytics/matches/registry", headers=_auth_headers(token))
        data = resp.json()
        for entry in data["entries"]:
            assert entry["data_completeness"] in (
                "metadata_only", "innings_totals", "phase_level", "delivery_complete"
            ), f"Unexpected completeness: {entry['data_completeness']}"

    def test_entry_has_all_required_fields(self, client: TestClient) -> None:
        token = _analyst_token(client)
        _apply_fixture(client, token, _make_cpl_fixture(match_number=10))

        resp = client.get("/analytics/matches/registry", headers=_auth_headers(token))
        data = resp.json()
        required = {
            "match_id", "match_title", "team_a", "team_b",
            "competition_code", "gender_category", "age_category",
            "format", "source_type", "data_completeness",
            "has_delivery_data", "has_phase_data", "has_scorecard_data",
            "analyst_ready",
        }
        for entry in data["entries"]:
            for field in required:
                assert field in entry, f"Missing field: {field}"

    def test_unknown_competition_stays_unknown(self, client: TestClient) -> None:
        token = _analyst_token(client)
        fixture = _make_cpl_fixture(match_number=11, competition="Super50 Cup")
        _apply_fixture(client, token, fixture)

        resp = client.get("/analytics/matches/registry", headers=_auth_headers(token))
        data = resp.json()
        unknown_entries = [e for e in data["entries"] if e["competition_code"] == "unknown"]
        # Super50 should remain unknown
        assert any(
            "Super50" in (e.get("competition_name") or "") for e in unknown_entries
        ), "Super50 should be classified as unknown, not forced into CPL or WCPL"

    def test_season_year_derived_from_season_string(self, client: TestClient) -> None:
        token = _analyst_token(client)
        _apply_fixture(client, token, _make_cpl_fixture(match_number=12, season="2024"))

        resp = client.get("/analytics/matches/registry", headers=_auth_headers(token))
        data = resp.json()
        cpl_entries = [e for e in data["entries"] if e.get("season") == "2024"]
        if cpl_entries:
            assert cpl_entries[0]["season_year"] == 2024
