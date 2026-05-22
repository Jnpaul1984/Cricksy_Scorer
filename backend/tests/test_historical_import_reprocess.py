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
from sqlalchemy import func, select
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


def _seed_players(client: TestClient, names: list[str]) -> None:
    async def _insert() -> None:
        async with client.session_maker() as session:  # type: ignore[attr-defined]
            max_player_id = (await session.scalar(select(func.max(models.Player.id)))) or 0
            for offset, name in enumerate(names, start=1):
                session.add(models.Player(id=max_player_id + offset, name=name))
            await session.commit()

    asyncio.get_event_loop().run_until_complete(_insert())


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


def test_backfill_diagnosis_reports_missing_source_json_without_mutation(
    client: TestClient,
) -> None:
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


def test_cpl_reset_reimport_dry_run_returns_scope_without_mutation(client: TestClient) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    _batch_id, game_id = _create_and_apply_batch(client, token, payload)
    before_game = _load_game(client, game_id)
    assert before_game.deliveries in (None, [])

    zip_payload = _build_zip({"1019645.json": json.dumps(payload).encode("utf-8")})
    resp = client.post(
        "/api/historical-import/json/cpl-reset-reimport/dry-run",
        headers=_auth_headers(token),
        files={"file": ("cpl.zip", zip_payload, "application/zip")},
        data={"max_batch_size": "25"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "preview_ready"
    assert data["records_safe_to_reset"] >= 1
    assert data["expected_deliveries"] > 0
    assert data["source_bundle_preview"] is not None
    assert len(data["source_file_mapping"]) >= 1

    after_game = _load_game(client, game_id)
    assert after_game.deliveries in (None, [])


def test_cpl_reset_reimport_apply_requires_confirm(client: TestClient) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    zip_payload = _build_zip({"1019645.json": json.dumps(payload).encode("utf-8")})

    resp = client.post(
        "/api/historical-import/json/cpl-reset-reimport/apply",
        headers=_auth_headers(token),
        files={"file": ("cpl.zip", zip_payload, "application/zip")},
        data={"confirm": "false", "max_batch_size": "25"},
    )
    assert resp.status_code == 422, resp.text
    assert "confirm must be true" in resp.text


def test_cpl_reset_reimport_apply_from_zip_is_idempotent(client: TestClient) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    _batch_id, game_id = _create_and_apply_batch(client, token, payload)
    zip_payload = _build_zip({"1019645.json": json.dumps(payload).encode("utf-8")})

    first = client.post(
        "/api/historical-import/json/cpl-reset-reimport/apply",
        headers=_auth_headers(token),
        files={"file": ("cpl.zip", zip_payload, "application/zip")},
        data={"confirm": "true", "max_batch_size": "25"},
    )
    assert first.status_code == 200, first.text
    first_data = first.json()
    assert first_data["status"] == "applied"
    assert first_data["matches_imported"] == 1
    assert first_data["deliveries_imported"] > 0
    assert first_data["reimport_report"]["selected_matches"] == 1
    first_game = _load_game(client, game_id)
    first_count = len(first_game.deliveries or [])
    assert first_count > 0
    assert first_data["reimport_report"]["selected_batches"] == 1

    second = client.post(
        "/api/historical-import/json/cpl-reset-reimport/apply",
        headers=_auth_headers(token),
        files={"file": ("cpl.zip", zip_payload, "application/zip")},
        data={"confirm": "true", "max_batch_size": "25"},
    )
    assert second.status_code == 200, second.text
    second_data = second.json()
    assert second_data["status"] == "applied"
    second_game = _load_game(client, game_id)
    assert len(second_game.deliveries or []) == first_count


def test_cpl_reset_reimport_apply_reports_failed_when_rebuild_cannot_run(
    client: TestClient,
) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    _batch_id, game_id = _create_and_apply_batch(client, token, payload)

    dry_run = client.post(
        "/api/historical-import/json/cpl-reset-reimport/dry-run",
        headers=_auth_headers(token),
        json={"match_ids": [game_id], "max_batch_size": 25},
    )
    assert dry_run.status_code == 200, dry_run.text
    assert dry_run.json()["records_blocked_from_reset"] >= 1

    apply = client.post(
        "/api/historical-import/json/cpl-reset-reimport/apply",
        headers=_auth_headers(token),
        json={"confirm": True, "match_ids": [game_id], "max_batch_size": 25},
    )
    assert apply.status_code == 200, apply.text
    data = apply.json()
    assert data["status"] == "failed"
    assert data["deliveries_imported"] == 0
    assert data["matches_imported"] == 0
    assert any("missing_source_json" in err for err in data["errors"])
    assert _load_game(client, game_id).deliveries in (None, [])


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


def test_backfill_apply_reports_mapping_breakdown_and_reasons(client: TestClient) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    info = payload.setdefault("info", {})
    assert isinstance(info, dict)
    registry = info.setdefault("registry", {}).setdefault("people", {})
    assert isinstance(registry, dict)
    player_names = [name for name in registry if isinstance(name, str)]
    assert len(player_names) >= 2
    ambiguous_name = player_names[0]
    missing_source_id_name = player_names[1]
    registry.pop(missing_source_id_name, None)
    info["venue"] = ""
    _seed_players(client, [ambiguous_name, ambiguous_name])

    batch_id, _ = _create_and_apply_batch(client, token, payload)
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
    data = apply.json()
    assert data["processed_matches"] == 1
    assert data["resolved_players"] >= 0
    assert data["ambiguous_players"] >= 1
    assert data["unresolved_venues"] == 1
    result = data["results"][0]
    assert result["ambiguous_players"] >= 1
    assert any(
        row.get("reason") == "ambiguous_match"
        for row in result.get("ambiguous_player_reasons", [])
        if isinstance(row, dict)
    )
    assert any(
        row.get("source_player_name") == missing_source_id_name
        and row.get("reason") == "missing_source_id"
        for row in result.get("unresolved_player_reasons", [])
        if isinstance(row, dict)
    )
    assert result["unresolved_venue_reasons"][0]["reason"] == "empty_raw_venue"

    repeat = client.post(
        "/api/historical-import/json/backfill-reprocess/apply",
        headers=_auth_headers(token),
        json={
            "confirm": True,
            "batch_ids": [batch_id],
            "max_batch_size": 25,
            "source_payloads_by_batch": {batch_id: payload},
        },
    )
    assert repeat.status_code == 200, repeat.text
    repeat_data = repeat.json()
    assert repeat_data["mappings_created"] == 0


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
            "file": (
                "repair-probable.json",
                json.dumps(probable_payload).encode("utf-8"),
                "application/json",
            )
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
        files={
            "file": (
                "mismatch.json",
                json.dumps(mismatch_payload).encode("utf-8"),
                "application/json",
            )
        },
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
        files={
            "file": (
                "repair-2.json",
                json.dumps(changed_payload).encode("utf-8"),
                "application/json",
            )
        },
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


def test_backfill_apply_via_retained_json_is_idempotent(client: TestClient) -> None:
    """Applying via retained JSON when deliveries were already imported must succeed
    idempotently (allow_reprocess path) and must not create duplicate deliveries."""
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, game_id = _create_and_apply_batch(client, token, payload)

    # Reattach source JSON so apply can load it from local storage.
    reattach = client.post(
        f"/api/historical-import/json/backfill/{batch_id}/reattach-source-json",
        headers=_auth_headers(token),
        files={"file": ("repair.json", json.dumps(payload).encode("utf-8"), "application/json")},
    )
    assert reattach.status_code == 200, reattach.text

    # First apply via retained JSON (deliveries_imported=False at this point).
    first = client.post(
        "/api/historical-import/json/backfill-reprocess/apply",
        headers=_auth_headers(token),
        json={"confirm": True, "batch_ids": [batch_id], "max_batch_size": 25},
    )
    assert first.status_code == 200, first.text
    first_data = first.json()
    assert first_data["processed_matches"] == 1, first_data
    first_count = len(_load_game(client, game_id).deliveries or [])
    assert first_count > 0

    # Second apply via retained JSON (deliveries_imported=True now — idempotent reprocess).
    second = client.post(
        "/api/historical-import/json/backfill-reprocess/apply",
        headers=_auth_headers(token),
        json={"confirm": True, "batch_ids": [batch_id], "max_batch_size": 25},
    )
    assert second.status_code == 200, second.text
    second_data = second.json()
    # The record must not produce a 500; it must be processed successfully.
    assert second_data["processed_matches"] == 1, second_data
    second_count = len(_load_game(client, game_id).deliveries or [])
    # No duplicates: delivery count must stay the same.
    assert second_count == first_count, (
        f"Duplicate deliveries detected after idempotent reprocess: "
        f"expected {first_count}, got {second_count}"
    )


def test_backfill_apply_returns_structured_error_on_unknown_batch(client: TestClient) -> None:
    """Apply with an unknown batch_id must return a 200 with the record marked
    failed (not a bare 500), and the response body must be structured JSON."""
    token = _register_analyst(client)

    resp = client.post(
        "/api/historical-import/json/backfill-reprocess/apply",
        headers=_auth_headers(token),
        json={
            "confirm": True,
            "batch_ids": ["00000000-0000-0000-0000-000000000000"],
            "max_batch_size": 25,
        },
    )
    # Must be a valid structured response (not a bare 500).
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert "status" in data
    assert "processed_matches" in data
    # The unknown batch should be skipped/blocked, not crash the whole request.
    assert data["processed_matches"] == 0


def test_backfill_apply_no_duplicate_deliveries_after_reprocess(client: TestClient) -> None:
    """Repeated applies of the same eligible record must never insert duplicate deliveries."""
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, game_id = _create_and_apply_batch(client, token, payload)

    # Apply once via inline payload.
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
    assert first.json()["processed_matches"] == 1
    count_after_first = len(_load_game(client, game_id).deliveries or [])
    assert count_after_first > 0

    # Apply a second time (reprocess) via inline payload.
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
    count_after_second = len(_load_game(client, game_id).deliveries or [])
    assert count_after_second == count_after_first, (
        f"Duplicate deliveries after reprocess: expected {count_after_first}, "
        f"got {count_after_second}"
    )

    # Apply a third time — still no duplicates.
    third = client.post(
        "/api/historical-import/json/backfill-reprocess/apply",
        headers=_auth_headers(token),
        json={
            "confirm": True,
            "batch_ids": [batch_id],
            "max_batch_size": 25,
            "source_payloads_by_batch": {batch_id: payload},
        },
    )
    assert third.status_code == 200, third.text
    count_after_third = len(_load_game(client, game_id).deliveries or [])
    assert count_after_third == count_after_first, (
        f"Duplicate deliveries after third apply: expected {count_after_first}, "
        f"got {count_after_third}"
    )


# ---------------------------------------------------------------------------
# CPL reset/reimport status-honesty regression tests (Issue: false "applied"
# when expected_deliveries > 0 but deliveries_imported == 0)
# ---------------------------------------------------------------------------


def test_cpl_reset_reimport_apply_status_applied_when_deliveries_present(
    client: TestClient,
) -> None:
    """Applied zip with a valid CPL payload must return status=applied and deliveries_imported > 0."""
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    _batch_id, _game_id = _create_and_apply_batch(client, token, payload)
    zip_payload = _build_zip({"1019645.json": json.dumps(payload).encode("utf-8")})

    resp = client.post(
        "/api/historical-import/json/cpl-reset-reimport/apply",
        headers=_auth_headers(token),
        files={"file": ("cpl.zip", zip_payload, "application/zip")},
        data={"confirm": "true", "max_batch_size": "25"},
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()
    assert data["status"] == "applied", (
        f"Expected status=applied but got {data['status']!r}. "
        f"errors={data.get('errors')}, deliveries_imported={data.get('deliveries_imported')}"
    )
    assert (
        data["deliveries_imported"] > 0
    ), "deliveries_imported must be > 0 for a valid reimport with expected deliveries"
    assert data["errors"] == [], f"Expected no errors but got: {data['errors']}"


def test_cpl_reset_reimport_apply_zero_deliveries_returns_failed_not_applied(
    client: TestClient,
) -> None:
    """When expected_deliveries > 0 but the game has zero deliveries after the operation,
    the response must be status=failed (not applied) with an explicit error.

    Regression test for: CPL reset/reimport false applied status when actual delivery
    count is zero.
    """
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    _batch_id, game_id = _create_and_apply_batch(client, token, payload)

    # Call apply WITHOUT a source payload so the backfill is blocked (missing_source_json).
    # This produces: processed_matches=0, deliveries_imported=0, expected_deliveries>0.
    # The endpoint must NOT return status=applied in this case.
    apply = client.post(
        "/api/historical-import/json/cpl-reset-reimport/apply",
        headers=_auth_headers(token),
        json={"confirm": True, "match_ids": [game_id], "max_batch_size": 25},
    )
    assert apply.status_code == 200, apply.text
    data = apply.json()

    assert data["status"] == "failed", (
        f"Expected status=failed when deliveries_imported=0 and expected_deliveries>0, "
        f"but got status={data['status']!r}"
    )
    assert data["deliveries_imported"] == 0
    assert (
        len(data["errors"]) > 0
    ), "errors must be non-empty when delivery rebuild produces zero rows"
    # The response must contain an explicit error about zero rows or missing source.
    errors_combined = " ".join(data["errors"])
    assert (
        "missing_source_json" in errors_combined or "delivery_rebuild_zero_rows" in errors_combined
    ), f"Expected an explicit delivery or source error, got: {data['errors']}"
    # The game must not have gained deliveries.
    assert _load_game(client, game_id).deliveries in (None, [])


def test_cpl_reset_reimport_apply_zero_deliveries_explicit_error_message(
    client: TestClient,
) -> None:
    """When expected_deliveries > 0 and deliveries_imported == 0, the errors field must contain
    an explicit error message (not be empty).

    Uses a source_payloads_by_batch override that is structurally valid (has deliveries) but
    whose hash does not match the stored batch hash. The audit marks the batch eligible
    (expected_deliveries > 0) but apply_historical_deliveries fails the hash gate, leaving
    deliveries_imported == 0. The endpoint must add a delivery_rebuild_zero_rows error.
    """
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, _game_id = _create_and_apply_batch(client, token, payload)

    # Build a structurally valid payload that differs from the original (different hash).
    mismatch_payload = deepcopy(payload)
    mismatch_payload.setdefault("info", {})["_test_marker"] = "hash_mismatch_sentinel"

    apply = client.post(
        "/api/historical-import/json/cpl-reset-reimport/apply",
        headers=_auth_headers(token),
        json={
            "confirm": True,
            "batch_ids": [batch_id],
            "max_batch_size": 25,
            "source_payloads_by_batch": {batch_id: mismatch_payload},
        },
    )
    assert apply.status_code == 200, apply.text
    data = apply.json()

    # Audit sees deliveries in mismatch_payload → expected_deliveries > 0
    # Apply fails hash check → deliveries_imported == 0
    assert (
        data["expected_deliveries"] > 0
    ), "Fixture must have expected_deliveries > 0 for this test to be meaningful"
    assert (
        data["deliveries_imported"] == 0
    ), "Hash-mismatched payload must not result in any deliveries being imported"
    # The key requirement: errors must be non-empty (not silently succeed)
    assert data[
        "errors"
    ], "errors must be non-empty when expected_deliveries > 0 and deliveries_imported == 0"
    assert data["status"] in (
        "failed",
        "partial",
    ), f"status must be 'failed' or 'partial', not {data['status']!r}"


def test_cpl_reset_reimport_apply_processed_matches_does_not_imply_success(
    client: TestClient,
) -> None:
    """processed_matches > 0 must not by itself produce status=applied when deliveries are zero.

    This test simulates the scenario where the apply path processes a match but the
    game ends up with zero deliveries (e.g., source missing / blocked). The endpoint
    must return status=failed or status=partial, never status=applied.
    """
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    _batch_id, game_id = _create_and_apply_batch(client, token, payload)

    # No source payload provided → batch is blocked; processed_matches stays 0.
    apply = client.post(
        "/api/historical-import/json/cpl-reset-reimport/apply",
        headers=_auth_headers(token),
        json={"confirm": True, "match_ids": [game_id], "max_batch_size": 25},
    )
    assert apply.status_code == 200, apply.text
    data = apply.json()

    # Whether blocked (processed=0) or somehow processed with 0 deliveries, the rule holds:
    # if expected > 0 and deliveries_imported == 0, status must not be "applied".
    if data["expected_deliveries"] > 0 and data["deliveries_imported"] == 0:
        assert data["status"] != "applied", (
            "status must not be 'applied' when expected_deliveries > 0 and deliveries_imported == 0. "
            f"Got status={data['status']!r}, errors={data.get('errors')}"
        )


def test_cpl_reset_reimport_apply_idempotent_second_run_reports_honest_count(
    client: TestClient,
) -> None:
    """A second apply on the same game must still show deliveries_imported > 0 (total in game),
    not 0 (delta), and status must be 'applied'.

    This validates that the fix uses deliveries_after (total in game post-op) rather than
    deliveries_rebuilt (delta), so a reimport of already-imported data is still honest.
    """
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    _batch_id, game_id = _create_and_apply_batch(client, token, payload)
    zip_payload = _build_zip({"1019645.json": json.dumps(payload).encode("utf-8")})

    # First apply
    first = client.post(
        "/api/historical-import/json/cpl-reset-reimport/apply",
        headers=_auth_headers(token),
        files={"file": ("cpl.zip", zip_payload, "application/zip")},
        data={"confirm": "true", "max_batch_size": "25"},
    )
    assert first.status_code == 200, first.text
    first_data = first.json()
    assert first_data["status"] == "applied"
    assert first_data["deliveries_imported"] > 0
    first_game_count = len(_load_game(client, game_id).deliveries or [])
    assert first_game_count > 0

    # Second apply (reimport of the same game that already has deliveries)
    second = client.post(
        "/api/historical-import/json/cpl-reset-reimport/apply",
        headers=_auth_headers(token),
        files={"file": ("cpl.zip", zip_payload, "application/zip")},
        data={"confirm": "true", "max_batch_size": "25"},
    )
    assert second.status_code == 200, second.text
    second_data = second.json()

    # The second run must still report status=applied and deliveries_imported > 0
    # (total in game, not delta which would be 0).
    assert second_data["status"] == "applied", (
        f"Second reimport must still be 'applied'. Got {second_data['status']!r}. "
        f"errors={second_data.get('errors')}"
    )
    assert (
        second_data["deliveries_imported"] > 0
    ), "deliveries_imported must reflect total deliveries in game (not delta) on second apply"
    # No new deliveries should have been created (idempotency).
    second_game_count = len(_load_game(client, game_id).deliveries or [])
    assert second_game_count == first_game_count


def test_cpl_reset_reimport_apply_counts_stringified_delivery_json(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If DB returns deliveries as JSON text, apply must still report persisted counts."""
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, _game_id = _create_and_apply_batch(client, token, payload)

    async def _fake_apply_historical_deliveries(
        db: Any,
        *,
        batch_id: str,
        confirm: bool,
        raw_payload: bytes,
        allow_reprocess: bool = False,
    ) -> tuple[dict[str, Any] | None, list[str], str | None]:
        from backend.services.historical_import_delivery_service import extract_normalized_innings

        batch = await db.scalar(
            select(models.HistoricalImportBatch).where(models.HistoricalImportBatch.id == batch_id)
        )
        assert batch is not None and batch.applied_game_id
        game = await db.scalar(select(models.Game).where(models.Game.id == batch.applied_game_id))
        assert game is not None
        innings = extract_normalized_innings(json.loads(raw_payload.decode("utf-8")))
        all_deliveries = [d for inn in innings for d in inn["deliveries"]]

        phases = game.phases if isinstance(game.phases, dict) else {}
        hist_meta = (
            phases.get("historical_import")
            if isinstance(phases.get("historical_import"), dict)
            else {}
        )
        hist_meta["deliveries_imported"] = True
        phases["historical_import"] = hist_meta
        game.phases = phases
        # Simulate legacy environments that surface JSON columns as text.
        game.deliveries = json.dumps(all_deliveries)
        db.add(game)
        await db.commit()
        return (
            {
                "game_id": game.id,
                "deliveries_imported": len(all_deliveries),
                "innings_processed": len(innings),
                "totals_validation": [],
            },
            [],
            None,
        )

    monkeypatch.setattr(
        "backend.services.historical_import_reprocess_service.apply_historical_deliveries",
        _fake_apply_historical_deliveries,
    )

    apply = client.post(
        "/api/historical-import/json/cpl-reset-reimport/apply",
        headers=_auth_headers(token),
        json={
            "confirm": True,
            "batch_ids": [batch_id],
            "max_batch_size": 25,
            "source_payloads_by_batch": {batch_id: payload},
        },
    )
    assert apply.status_code == 200, apply.text
    data = apply.json()

    assert data["expected_deliveries"] > 0
    assert data["status"] == "applied", data
    assert data["deliveries_imported"] == data["expected_deliveries"], data
    assert data["errors"] == [], data["errors"]


def test_analyst_deliveries_reads_stringified_game_deliveries(client: TestClient) -> None:
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, game_id = _create_and_apply_batch(client, token, payload)

    apply = client.post(
        "/api/historical-import/json/cpl-reset-reimport/apply",
        headers=_auth_headers(token),
        json={
            "confirm": True,
            "batch_ids": [batch_id],
            "max_batch_size": 25,
            "source_payloads_by_batch": {batch_id: payload},
        },
    )
    assert apply.status_code == 200, apply.text
    apply_data = apply.json()
    assert apply_data["status"] == "applied", apply_data

    game = _load_game(client, game_id)
    assert isinstance(game.deliveries, list) and len(game.deliveries) > 0

    async def _stringify_deliveries() -> None:
        async with client.session_maker() as session:  # type: ignore[attr-defined]
            db_game = await session.scalar(select(models.Game).where(models.Game.id == game_id))
            assert db_game is not None
            db_game.deliveries = json.dumps(game.deliveries)
            session.add(db_game)
            await session.commit()

    asyncio.get_event_loop().run_until_complete(_stringify_deliveries())

    deliveries_resp = client.get(
        "/api/analyst/deliveries",
        headers=_auth_headers(token),
        params={"match_id": game_id},
    )
    assert deliveries_resp.status_code == 200, deliveries_resp.text
    deliveries_data = deliveries_resp.json()
    assert deliveries_data["total"] == len(game.deliveries), deliveries_data
