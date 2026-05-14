"""Phase 5P — deterministic model training dataset builder tests."""

from __future__ import annotations

import asyncio
import datetime as dt
import json
import os
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
from backend.services.model_training_dataset_builder import (
    DatasetBuildRequest,
    build_model_training_dataset,
)
from backend.sql_app import models
from backend.sql_app.database import get_db

FIXTURE_PATH = Path(__file__).resolve().parent / "simulated_t20_match.json"


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


def _register_analyst(client: TestClient) -> str:
    import uuid as _uuid

    email = f"phase5p-analyst-{_uuid.uuid4().hex[:8]}@example.com"
    user = register_user(client, email)
    asyncio.get_event_loop().run_until_complete(
        set_role(client, user["email"], models.RoleEnum.analyst_pro)
    )
    return login_user(client, email)


def _apply_historical_fixture(client: TestClient, token: str) -> tuple[str, str]:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))

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


async def _update_batch_status(
    session_maker: async_sessionmaker,
    batch_id: str,
    *,
    status: str,
    error_count: int = 0,
    source_hash_sha256: str | None = None,
    semantic_key: str | None = None,
) -> None:
    async with session_maker() as session:
        batch = await session.get(models.HistoricalImportBatch, batch_id)
        assert batch is not None
        batch.status = status
        batch.error_count = error_count
        if source_hash_sha256 is not None:
            batch.source_hash_sha256 = source_hash_sha256
        if semantic_key is not None:
            batch.semantic_key = semantic_key
        await session.commit()


async def _clear_innings_summary(session_maker: async_sessionmaker, game_id: str) -> None:
    async with session_maker() as session:
        game = await session.get(models.Game, game_id)
        assert game is not None
        phases = dict(game.phases) if isinstance(game.phases, dict) else {}
        phases["historical_innings_summary"] = []
        game.phases = phases
        await session.commit()


async def _snapshot_truth(session_maker: async_sessionmaker, game_id: str) -> dict[str, Any]:
    async with session_maker() as session:
        game = await session.get(models.Game, game_id)
        assert game is not None
        return {
            "total_runs": game.total_runs,
            "total_wickets": game.total_wickets,
            "overs_completed": game.overs_completed,
            "result": game.result,
            "phases": json.dumps(game.phases, sort_keys=True),
            "deliveries": json.dumps(game.deliveries, sort_keys=True),
        }


async def _build(session_maker: async_sessionmaker, *, generated_at: dt.datetime | None = None) -> dict[str, Any]:
    async with session_maker() as session:
        return await build_model_training_dataset(
            session,
            DatasetBuildRequest(generated_at=generated_at),
        )


def test_includes_eligible_validated_match(client: TestClient) -> None:
    token = _register_analyst(client)
    _batch_id, game_id = _apply_historical_fixture(client, token)

    artifact = asyncio.get_event_loop().run_until_complete(_build(client.session_maker))  # type: ignore[attr-defined]

    assert artifact["dataset_schema_version"] == "training_dataset_v1"
    assert artifact["included_match_count"] == 1
    assert artifact["excluded_match_count"] == 0
    assert artifact["row_count"] >= 1
    assert game_id in artifact["included_match_ids"]


def test_excludes_invalid_and_duplicate_and_missing_innings(client: TestClient) -> None:
    token = _register_analyst(client)
    invalid_batch, _invalid_game = _apply_historical_fixture(client, token)
    _dup_batch_a, dup_game_a = _apply_historical_fixture(client, token)
    _dup_batch_b, dup_game_b = _apply_historical_fixture(client, token)
    _missing_batch, missing_game = _apply_historical_fixture(client, token)

    asyncio.get_event_loop().run_until_complete(
        _update_batch_status(client.session_maker, invalid_batch, status="invalid", error_count=1)  # type: ignore[attr-defined]
    )
    asyncio.get_event_loop().run_until_complete(
        _update_batch_status(
            client.session_maker,  # type: ignore[attr-defined]
            _missing_batch,
            status="valid",
            source_hash_sha256="f" * 64,
            semantic_key="phase5p-missing-innings",
        )
    )
    asyncio.get_event_loop().run_until_complete(
        _clear_innings_summary(client.session_maker, missing_game)  # type: ignore[attr-defined]
    )

    artifact = asyncio.get_event_loop().run_until_complete(_build(client.session_maker))  # type: ignore[attr-defined]

    assert artifact["included_match_count"] == 1
    assert dup_game_a in artifact["included_match_ids"] or dup_game_b in artifact["included_match_ids"]

    reasons = artifact["exclusion_reasons"]
    assert reasons.get("invalid_status_invalid") == 1
    assert reasons.get("missing_required_innings_data") == 1
    assert reasons.get("duplicate_source_hash") == 1


def test_output_is_deterministic_for_same_inputs(client: TestClient) -> None:
    token = _register_analyst(client)
    _apply_historical_fixture(client, token)

    fixed_time = dt.datetime(2026, 5, 14, 12, 0, 0, tzinfo=dt.UTC)
    artifact_one = asyncio.get_event_loop().run_until_complete(
        _build(client.session_maker, generated_at=fixed_time)  # type: ignore[attr-defined]
    )
    artifact_two = asyncio.get_event_loop().run_until_complete(
        _build(client.session_maker, generated_at=fixed_time)  # type: ignore[attr-defined]
    )

    assert artifact_one == artifact_two


def test_metadata_and_provenance_present(client: TestClient) -> None:
    token = _register_analyst(client)
    _apply_historical_fixture(client, token)

    artifact = asyncio.get_event_loop().run_until_complete(_build(client.session_maker))  # type: ignore[attr-defined]

    assert artifact["dataset_schema_version"] == "training_dataset_v1"
    assert "generated_at" in artifact
    assert artifact["build_fingerprint"]
    assert artifact["provenance"]["source"] == "historical_import_registry"
    assert artifact["provenance"]["read_only"] is True
    assert set(artifact["parameters"].keys()) == {"source_format", "match_type", "season", "competition"}


def test_builder_does_not_mutate_official_match_truth(client: TestClient) -> None:
    token = _register_analyst(client)
    _batch_id, game_id = _apply_historical_fixture(client, token)

    before = asyncio.get_event_loop().run_until_complete(
        _snapshot_truth(client.session_maker, game_id)  # type: ignore[attr-defined]
    )

    _ = asyncio.get_event_loop().run_until_complete(_build(client.session_maker))  # type: ignore[attr-defined]

    after = asyncio.get_event_loop().run_until_complete(
        _snapshot_truth(client.session_maker, game_id)  # type: ignore[attr-defined]
    )

    assert before == after


def test_empty_case_returns_valid_empty_artifact(client: TestClient) -> None:
    artifact = asyncio.get_event_loop().run_until_complete(_build(client.session_maker))  # type: ignore[attr-defined]

    assert artifact["dataset_schema_version"] == "training_dataset_v1"
    assert artifact["included_match_count"] == 0
    assert artifact["excluded_match_count"] == 0
    assert artifact["row_count"] == 0
    assert artifact["rows"] == []
    assert artifact["exclusion_reasons"] == {}
