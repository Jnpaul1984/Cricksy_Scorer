from __future__ import annotations

import asyncio
import io
import json
import os
import uuid
import zipfile
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from backend.main import fastapi_app
from backend.sql_app import models
from backend.sql_app.database import get_db

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////tmp/cricksy_reprocess_test.db")
os.environ.setdefault("APP_SECRET_KEY", "test-secret-key")
os.environ.setdefault("CRICKSY_IN_MEMORY_DB", "1")


FIXTURE_PATH = Path(__file__).resolve().parent / "sanitized_cricsheet_635215.json"


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


def _cpl_payload_with_registry() -> dict[str, Any]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    payload = deepcopy(payload)
    info = payload.setdefault("info", {})
    registry_people: dict[str, str] = {}
    for inning in payload.get("innings", []):
        if not isinstance(inning, dict):
            continue
        innings_obj = next(iter(inning.values()), {})
        overs = innings_obj.get("overs") if isinstance(innings_obj, dict) else []
        for over in overs if isinstance(overs, list) else []:
            deliveries = over.get("deliveries") if isinstance(over, dict) else []
            for delivery in deliveries if isinstance(deliveries, list) else []:
                for key in ("batter", "bowler", "non_striker"):
                    name = str(delivery.get(key) or "").strip()
                    if name and name not in registry_people:
                        registry_people[name] = f"cricsheet::{name.lower().replace(' ', '_')}"
    info["registry"] = {"people": registry_people}
    payload["info"] = info
    return payload


def _create_and_apply_batch(
    client: TestClient, token: str, payload: dict[str, Any]
) -> tuple[str, str]:
    dry_run = client.post(
        "/api/historical-import/json/dry-run",
        headers=_auth_headers(token),
        params={"record_preview": "true"},
        json=payload,
    )
    assert dry_run.status_code == 200, dry_run.text
    batch_id = dry_run.json()["record_id"]
    apply = client.post(
        f"/api/historical-import/json/batches/{batch_id}/apply",
        headers=_auth_headers(token),
        json={"confirm": True},
    )
    assert apply.status_code == 200, apply.text
    return batch_id, apply.json()["applied_game_id"]


def _create_sparse_historical_pair(client: TestClient) -> tuple[str, str]:
    async def _create() -> tuple[str, str]:
        async with client.session_maker() as session:  # type: ignore[attr-defined]
            batch_id = str(uuid.uuid4())
            game_id = str(uuid.uuid4())
            game = models.Game(
                id=game_id,
                phases={"historical_import": {"batch_id": batch_id}},
            )
            batch = models.HistoricalImportBatch(
                id=batch_id,
                source_format="json",
                source_hash_sha256=uuid.uuid4().hex,
                status="valid",
                is_finalized=True,
                applied_game_id=game_id,
            )
            session.add(game)
            session.add(batch)
            await session.commit()
            return batch_id, game_id

    return asyncio.get_event_loop().run_until_complete(_create())


def _register_analyst(client: TestClient) -> str:
    email = f"reprocess-{uuid.uuid4().hex[:8]}@example.com"
    user = register_user(client, email)
    asyncio.get_event_loop().run_until_complete(
        _set_user_role(client.session_maker, user["email"], models.RoleEnum.analyst_pro)  # type: ignore[attr-defined]
    )
    return login_user(client, user["email"])


def _load_game(client: TestClient, game_id: str) -> models.Game:
    async def _query() -> models.Game:
        async with client.session_maker() as session:  # type: ignore[attr-defined]
            result = await session.execute(select(models.Game).where(models.Game.id == game_id))
            return result.scalar_one()

    return asyncio.get_event_loop().run_until_complete(_query())


def _load_batch(client: TestClient, batch_id: str) -> models.HistoricalImportBatch:
    async def _query() -> models.HistoricalImportBatch:
        async with client.session_maker() as session:  # type: ignore[attr-defined]
            result = await session.execute(
                select(models.HistoricalImportBatch).where(
                    models.HistoricalImportBatch.id == batch_id
                )
            )
            return result.scalar_one()

    return asyncio.get_event_loop().run_until_complete(_query())


def _count_games(client: TestClient) -> int:
    async def _query() -> int:
        async with client.session_maker() as session:  # type: ignore[attr-defined]
            result = await session.execute(select(models.Game))
            return len(result.scalars().all())

    return asyncio.get_event_loop().run_until_complete(_query())


def _count_delivery_rows(client: TestClient) -> int:
    async def _query() -> int:
        async with client.session_maker() as session:  # type: ignore[attr-defined]
            result = await session.execute(select(models.Delivery))
            return len(result.scalars().all())

    return asyncio.get_event_loop().run_until_complete(_query())


def _count_player_rows(client: TestClient) -> int:
    async def _query() -> int:
        async with client.session_maker() as session:  # type: ignore[attr-defined]
            result = await session.execute(select(models.Player))
            return len(result.scalars().all())

    return asyncio.get_event_loop().run_until_complete(_query())


def _build_zip(entries: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, content in entries.items():
            archive.writestr(name, content)
    return stream.getvalue()


def test_backfill_audit_identifies_eligible_without_mutation(client: TestClient) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, game_id = _create_and_apply_batch(client, token, payload)

    before_game = _load_game(client, game_id)
    assert before_game.deliveries in (None, [])

    resp = client.post(
        "/api/historical-import/json/backfill-reprocess/audit",
        headers=_auth_headers(token),
        json={
            "batch_ids": [batch_id],
            "max_batch_size": 25,
            "source_payloads_by_batch": {batch_id: payload},
        },
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["eligible_matches"] == 1
    record = data["records"][0]
    assert record["eligible"] is True
    assert record["expected_deliveries"] > 0
    assert record["registry_people_available"] is True
    assert record["team_1"]
    assert record["team_2"]
    assert record["match_date"]
    assert record["venue"]
    assert record["competition"]
    assert record["season"]
    assert record["known_score_summary"]
    assert record["match_identity_label"]
    assert "original_filename" in record

    after_game = _load_game(client, game_id)
    assert after_game.deliveries in (None, [])


def test_backfill_audit_blocks_when_source_json_missing(client: TestClient) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, _game_id = _create_and_apply_batch(client, token, payload)

    resp = client.post(
        "/api/historical-import/json/backfill-reprocess/audit",
        headers=_auth_headers(token),
        json={"batch_ids": [batch_id], "max_batch_size": 25},
    )
    assert resp.status_code == 200, resp.text
    record = resp.json()["records"][0]
    assert record["eligible"] is False
    assert record["missing_source_json"] is True


def test_backfill_audit_returns_null_identity_fields_when_unavailable(client: TestClient) -> None:
    token = _register_analyst(client)
    batch_id, _ = _create_sparse_historical_pair(client)

    resp = client.post(
        "/api/historical-import/json/backfill-reprocess/audit",
        headers=_auth_headers(token),
        json={"batch_ids": [batch_id], "max_batch_size": 25},
    )
    assert resp.status_code == 200, resp.text
    record = resp.json()["records"][0]
    assert record["team_1"] is None
    assert record["team_2"] is None
    assert record["match_date"] is None
    assert record["venue"] is None
    assert record["competition"] is None
    assert record["season"] is None
    assert record["known_score_summary"] is None
    assert record["match_identity_label"] is None


def test_backfill_diagnosis_reports_missing_source_json_without_mutation(client: TestClient) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, game_id = _create_and_apply_batch(client, token, payload)
    before_game = _load_game(client, game_id)
    before_deliveries = list(before_game.deliveries or [])
    before_delivery_rows = _count_delivery_rows(client)

    resp = client.post(
        "/api/historical-import/json/backfill-reprocess/diagnose",
        headers=_auth_headers(token),
        json={"batch_ids": [batch_id], "max_batch_size": 25},
    )
    assert resp.status_code == 200, resp.text
    record = resp.json()["records"][0]
    assert record["source_json_retained"] is False
    assert record["skip_or_failure_reason"] == "missing_source_json"
    assert record["recommended_next_action"] == (
        "Source JSON missing. Reattach original JSON before delivery diagnosis or reprocess can run."
    )

    after_game = _load_game(client, game_id)
    assert list(after_game.deliveries or []) == before_deliveries
    assert _count_delivery_rows(client) == before_delivery_rows


def test_backfill_diagnosis_detects_known_delivery_schema(client: TestClient) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, _ = _create_and_apply_batch(client, token, payload)

    resp = client.post(
        "/api/historical-import/json/backfill-reprocess/diagnose",
        headers=_auth_headers(token),
        json={
            "batch_ids": [batch_id],
            "max_batch_size": 25,
            "source_payloads_by_batch": {batch_id: payload},
        },
    )
    assert resp.status_code == 200, resp.text
    record = resp.json()["records"][0]
    assert record["delivery_path_detected"] is True
    assert record["expected_deliveries"] > 0
    assert record["detected_delivery_path"] in {
        "innings[].overs[].deliveries[]",
        "innings[].<team>.overs[].deliveries[]",
    }


def test_backfill_diagnosis_reports_no_delivery_path_detected(client: TestClient) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    innings = payload.get("innings")
    assert isinstance(innings, list)
    for entry in innings:
        if not isinstance(entry, dict):
            continue
        innings_obj = next(iter(entry.values()), {}) if len(entry) == 1 else entry
        if isinstance(innings_obj, dict):
            innings_obj.pop("overs", None)
            innings_obj.pop("deliveries", None)
            innings_obj.pop("balls", None)
            innings_obj["wickets"] = 6
            innings_obj["runs"] = 150
    batch_id, _ = _create_and_apply_batch(client, token, _cpl_payload_with_registry())

    resp = client.post(
        "/api/historical-import/json/backfill-reprocess/diagnose",
        headers=_auth_headers(token),
        json={
            "batch_ids": [batch_id],
            "max_batch_size": 25,
            "source_payloads_by_batch": {batch_id: payload},
        },
    )
    assert resp.status_code == 200, resp.text
    record = resp.json()["records"][0]
    assert record["delivery_path_detected"] is False
    assert record["skip_or_failure_reason"] == "no_delivery_path_detected"
    assert record["expected_wickets"] > 0


def test_backfill_diagnosis_detects_alternate_overs_delivery_schema(client: TestClient) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    info = payload.setdefault("info", {})
    assert isinstance(info, dict)
    info["teams"] = ["A", "B"]
    payload["innings"] = [
        {
            "A": {
                "team": "A",
                "overs": [
                    {
                        "over": 0,
                        "deliveries": [
                            {
                                "batter": "P1",
                                "bowler": "P2",
                                "non_striker": "P3",
                                "runs": {"batter": 1, "extras": 0, "total": 1},
                            }
                        ],
                    }
                ],
                "wickets": 0,
            }
        }
    ]
    batch_id, _ = _create_and_apply_batch(client, token, _cpl_payload_with_registry())

    resp = client.post(
        "/api/historical-import/json/backfill-reprocess/diagnose",
        headers=_auth_headers(token),
        json={
            "batch_ids": [batch_id],
            "max_batch_size": 25,
            "source_payloads_by_batch": {batch_id: payload},
        },
    )
    assert resp.status_code == 200, resp.text
    record = resp.json()["records"][0]
    assert record["expected_deliveries"] == 1
    assert record["delivery_path_detected"] is True
    assert any(
        candidate in record["delivery_path_candidates"]
        for candidate in ["innings[].overs[].deliveries[]", "innings[].<team>.overs[].deliveries[]"]
    )


def test_backfill_diagnosis_is_read_only_for_delivery_rows(client: TestClient) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, game_id = _create_and_apply_batch(client, token, payload)
    before_delivery_rows = _count_delivery_rows(client)
    before_game = _load_game(client, game_id)
    assert before_game.deliveries in (None, [])

    resp = client.post(
        "/api/historical-import/json/backfill-reprocess/diagnose",
        headers=_auth_headers(token),
        json={
            "batch_ids": [batch_id],
            "max_batch_size": 25,
            "source_payloads_by_batch": {batch_id: payload},
        },
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["records"][0]["expected_deliveries"] > 0
    assert _count_delivery_rows(client) == before_delivery_rows
    assert _load_game(client, game_id).deliveries in (None, [])


def test_backfill_apply_rebuilds_deliveries_and_is_idempotent(client: TestClient) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, game_id = _create_and_apply_batch(client, token, payload)

    first = client.post(
        "/api/historical-import/json/backfill-reprocess/apply",
        headers=_auth_headers(token),
        json={
            "confirm": True,
            "batch_ids": [batch_id],
            "max_batch_size": 25,
            "source_payloads_by_batch": {batch_id: payload},
        },
    )
    assert first.status_code == 200, first.text
    first_data = first.json()
    assert first_data["processed_matches"] == 1

    first_game = _load_game(client, game_id)
    first_count = len(first_game.deliveries or [])
    assert first_count > 0
    first_ball = first_game.deliveries[0]
    assert first_ball.get("batter_source_player_id") is not None

    second = client.post(
        "/api/historical-import/json/backfill-reprocess/apply",
        headers=_auth_headers(token),
        json={
            "confirm": True,
            "batch_ids": [batch_id],
            "max_batch_size": 25,
            "source_payloads_by_batch": {batch_id: payload},
        },
    )
    assert second.status_code == 200, second.text
    second_game = _load_game(client, game_id)
    second_count = len(second_game.deliveries or [])
    assert second_count == first_count


def test_backfill_apply_reflects_in_players_deliveries_dashboard_and_case_study(
    client: TestClient,
) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, game_id = _create_and_apply_batch(client, token, payload)

    apply = client.post(
        "/api/historical-import/json/backfill-reprocess/apply",
        headers=_auth_headers(token),
        json={
            "confirm": True,
            "batch_ids": [batch_id],
            "max_batch_size": 25,
            "source_payloads_by_batch": {batch_id: payload},
        },
    )
    assert apply.status_code == 200, apply.text

    players = client.get("/api/analyst/players", headers=_auth_headers(token))
    assert players.status_code == 200, players.text
    assert players.json()["total"] > 0

    deliveries = client.get(
        f"/api/analyst/deliveries?match_id={game_id}",
        headers=_auth_headers(token),
    )
    assert deliveries.status_code == 200, deliveries.text
    assert deliveries.json()["total"] > 0

    summary = client.get("/analytics/historical-stats/summary", headers=_auth_headers(token))
    assert summary.status_code == 200, summary.text
    assert summary.json()["total_eligible_matches"] >= 1

    case_study = client.get(
        f"/analytics/matches/{game_id}/case-study",
        headers=_auth_headers(token),
    )
    assert case_study.status_code == 200, case_study.text


def test_source_reattach_dry_run_matches_existing_historical_record(client: TestClient) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, game_id = _create_and_apply_batch(client, token, payload)

    response = client.post(
        "/api/historical-import/json/source-reattach/dry-run",
        headers=_auth_headers(token),
        files={"file": ("repair.json", json.dumps(payload).encode("utf-8"), "application/json")},
    )
    assert response.status_code == 200, response.text
    result = response.json()["files"][0]
    assert result["match_confidence"] == "exact_match"
    assert result["blocked_from_apply"] is False
    assert result["matched_target"]["batch_id"] == batch_id
    assert result["matched_target"]["match_id"] == game_id
    assert "teams" in result["matched_target"]["matched_on"]
    assert result["metadata"]["registry_people_available"] is True
    assert result["metadata"]["expected_deliveries"] > 0
    assert result["metadata"]["expected_wickets"] > 0


def test_source_reattach_dry_run_blocks_no_match_and_ambiguous_candidates(
    client: TestClient,
) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, _ = _create_and_apply_batch(client, token, payload)

    no_match_payload = deepcopy(payload)
    info = no_match_payload.setdefault("info", {})
    assert isinstance(info, dict)
    info["dates"] = ["2014-01-01"]
    response = client.post(
        "/api/historical-import/json/source-reattach/dry-run",
        headers=_auth_headers(token),
        files={
            "file": (
                "repair-no-match.json",
                json.dumps(no_match_payload).encode("utf-8"),
                "application/json",
            )
        },
    )
    assert response.status_code == 200, response.text
    no_match_result = response.json()["files"][0]
    assert no_match_result["match_confidence"] == "no_match"
    assert no_match_result["blocked_from_apply"] is True

    duplicate_payload = deepcopy(payload)
    duplicate_payload["reattach_probe"] = "duplicate-target"
    duplicate_batch_id, _ = _create_and_apply_batch(client, token, duplicate_payload)
    assert duplicate_batch_id != batch_id

    ambiguous_response = client.post(
        "/api/historical-import/json/source-reattach/dry-run",
        headers=_auth_headers(token),
        files={
            "file": (
                "repair-ambiguous.json",
                json.dumps(payload).encode("utf-8"),
                "application/json",
            )
        },
    )
    assert ambiguous_response.status_code == 200, ambiguous_response.text
    ambiguous_result = ambiguous_response.json()["files"][0]
    assert ambiguous_result["match_confidence"] == "ambiguous"
    assert ambiguous_result["blocked_from_apply"] is True
    assert len(ambiguous_result["candidate_matches"]) >= 2


def test_source_reattach_apply_attaches_provenance_without_duplicate_games(
    client: TestClient,
) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, game_id = _create_and_apply_batch(client, token, payload)
    game_count_before = _count_games(client)
    game_before = _load_game(client, game_id)
    assert game_before.deliveries in (None, [])

    dry_run = client.post(
        "/api/historical-import/json/source-reattach/dry-run",
        headers=_auth_headers(token),
        files={"file": ("repair.json", json.dumps(payload).encode("utf-8"), "application/json")},
    )
    assert dry_run.status_code == 200, dry_run.text
    selected = json.dumps([{"file_name": "repair.json", "batch_id": batch_id}])

    apply = client.post(
        "/api/historical-import/json/source-reattach/apply",
        headers=_auth_headers(token),
        files={"file": ("repair.json", json.dumps(payload).encode("utf-8"), "application/json")},
        data={"confirm": "true", "selected_mappings": selected},
    )
    assert apply.status_code == 200, apply.text
    body = apply.json()
    assert body["status"] == "applied"
    assert body["reattached_count"] == 1
    assert body["results"][0]["status"] == "reattached"

    batch_after = _load_batch(client, batch_id)
    assert isinstance(batch_after.dry_run_summary, dict)
    reattach = batch_after.dry_run_summary.get("source_payload_reattach")
    assert isinstance(reattach, dict)
    assert reattach["match_confidence"] == "exact_match"
    assert isinstance(reattach["storage"]["raw"], dict)

    game_after = _load_game(client, game_id)
    assert game_after.deliveries in (None, [])
    assert _count_games(client) == game_count_before
    phases = game_after.phases if isinstance(game_after.phases, dict) else {}
    hist_meta = (
        phases.get("historical_import") if isinstance(phases.get("historical_import"), dict) else {}
    )
    assert hist_meta.get("source_json_retained") is True
    assert isinstance(hist_meta.get("source_payload_reattach"), dict)

    audit = client.post(
        "/api/historical-import/json/backfill-reprocess/audit",
        headers=_auth_headers(token),
        json={"batch_ids": [batch_id], "max_batch_size": 25},
    )
    assert audit.status_code == 200, audit.text
    record = audit.json()["records"][0]
    assert record["source_json_retained"] is True
    assert record["registry_people_available"] is True
    assert record["eligible"] is True
    assert record["expected_deliveries"] > 0

    reprocess = client.post(
        "/api/historical-import/json/backfill-reprocess/apply",
        headers=_auth_headers(token),
        json={"confirm": True, "batch_ids": [batch_id], "max_batch_size": 25},
    )
    assert reprocess.status_code == 200, reprocess.text
    assert reprocess.json()["processed_matches"] == 1
    assert len(_load_game(client, game_id).deliveries or []) > 0


def test_source_reattach_apply_rejects_ambiguous_selection(client: TestClient) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_a, _ = _create_and_apply_batch(client, token, payload)
    duplicate_payload = deepcopy(payload)
    duplicate_payload["reattach_probe"] = "duplicate-target"
    _create_and_apply_batch(client, token, duplicate_payload)

    response = client.post(
        "/api/historical-import/json/source-reattach/apply",
        headers=_auth_headers(token),
        files={"file": ("repair.json", json.dumps(payload).encode("utf-8"), "application/json")},
        data={
            "confirm": "true",
            "selected_mappings": json.dumps([{"file_name": "repair.json", "batch_id": batch_a}]),
        },
    )
    assert response.status_code == 422, response.text
    assert response.json()["detail"]


def test_backfill_record_source_reattach_exact_match_and_idempotent(client: TestClient) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, game_id = _create_and_apply_batch(client, token, payload)

    first = client.post(
        f"/api/historical-import/json/backfill/{batch_id}/reattach-source-json",
        headers=_auth_headers(token),
        files={"file": ("repair.json", json.dumps(payload).encode("utf-8"), "application/json")},
    )
    assert first.status_code == 200, first.text
    first_body = first.json()
    assert first_body["status"] == "reattached"
    assert first_body["validation_confidence"] == "exact_match"
    assert first_body["record_id"] == batch_id
    assert first_body["match_id"] == game_id

    second = client.post(
        f"/api/historical-import/json/backfill/{batch_id}/reattach-source-json",
        headers=_auth_headers(token),
        files={"file": ("repair.json", json.dumps(payload).encode("utf-8"), "application/json")},
    )
    assert second.status_code == 200, second.text
    second_body = second.json()
    assert second_body["status"] == "already_retained"
    assert second_body["source_hash_sha256"] == first_body["source_hash_sha256"]


def test_backfill_record_source_reattach_probable_match(client: TestClient) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, _ = _create_and_apply_batch(client, token, payload)

    probable_payload = deepcopy(payload)
    info = probable_payload.get("info")
    assert isinstance(info, dict)
    info.pop("event", None)

    response = client.post(
        f"/api/historical-import/json/backfill/{batch_id}/reattach-source-json",
        headers=_auth_headers(token),
        files={
            "file": ("repair-probable.json", json.dumps(probable_payload).encode("utf-8"), "application/json")
        },
    )
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "reattached"
    assert body["validation_confidence"] == "probable_match"


def test_backfill_record_source_reattach_rejects_malformed_and_mismatch(client: TestClient) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, _ = _create_and_apply_batch(client, token, payload)

    malformed = client.post(
        f"/api/historical-import/json/backfill/{batch_id}/reattach-source-json",
        headers=_auth_headers(token),
        files={"file": ("broken.json", b"{not-json", "application/json")},
    )
    assert malformed.status_code == 422, malformed.text

    mismatch_payload = deepcopy(payload)
    info = mismatch_payload.get("info")
    assert isinstance(info, dict)
    info["teams"] = ["Mismatch XI", "Other XI"]
    mismatch = client.post(
        f"/api/historical-import/json/backfill/{batch_id}/reattach-source-json",
        headers=_auth_headers(token),
        files={"file": ("mismatch.json", json.dumps(mismatch_payload).encode("utf-8"), "application/json")},
    )
    assert mismatch.status_code == 409, mismatch.text


def test_backfill_record_source_reattach_overwrite_protection(client: TestClient) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, _ = _create_and_apply_batch(client, token, payload)

    first = client.post(
        f"/api/historical-import/json/backfill/{batch_id}/reattach-source-json",
        headers=_auth_headers(token),
        files={"file": ("repair.json", json.dumps(payload).encode("utf-8"), "application/json")},
    )
    assert first.status_code == 200, first.text

    changed_payload = deepcopy(payload)
    changed_payload["reattach_probe"] = "different-hash"
    second = client.post(
        f"/api/historical-import/json/backfill/{batch_id}/reattach-source-json",
        headers=_auth_headers(token),
        files={"file": ("repair-2.json", json.dumps(changed_payload).encode("utf-8"), "application/json")},
    )
    assert second.status_code == 409, second.text
    assert "already retains a different source payload" in second.text


def test_backfill_record_source_reattach_makes_diagnosis_diagnosable_without_mutation(
    client: TestClient,
) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, game_id = _create_and_apply_batch(client, token, payload)
    before_deliveries = _count_delivery_rows(client)
    before_players = _count_player_rows(client)
    before_game_deliveries = list(_load_game(client, game_id).deliveries or [])

    reattach = client.post(
        f"/api/historical-import/json/backfill/{batch_id}/reattach-source-json",
        headers=_auth_headers(token),
        files={"file": ("repair.json", json.dumps(payload).encode("utf-8"), "application/json")},
    )
    assert reattach.status_code == 200, reattach.text

    diagnosis = client.post(
        "/api/historical-import/json/backfill-reprocess/diagnose",
        headers=_auth_headers(token),
        json={"batch_ids": [batch_id], "max_batch_size": 25},
    )
    assert diagnosis.status_code == 200, diagnosis.text
    record = diagnosis.json()["records"][0]
    assert record["source_json_retained"] is True
    assert record["skip_or_failure_reason"] != "missing_source_json"
    assert record["expected_deliveries"] > 0

    assert _count_delivery_rows(client) == before_deliveries
    assert _count_player_rows(client) == before_players
    assert list(_load_game(client, game_id).deliveries or []) == before_game_deliveries
