from __future__ import annotations

import asyncio
import json
import os
import uuid
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


def _create_and_apply_batch(client: TestClient, token: str, payload: dict[str, Any]) -> tuple[str, str]:
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
