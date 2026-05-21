"""Tests for bulk ZIP source payload reattach endpoints.

Endpoints tested:
  POST /api/historical-import/json/backfill/source-zip/dry-run
  POST /api/historical-import/json/backfill/source-zip/apply
"""

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

from backend.main import fastapi_app
from backend.sql_app import models
from backend.sql_app.database import get_db

os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:////tmp/cricksy_source_zip_test.db")
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


# ---------------------------------------------------------------------------
# Shared helpers (mirrors test_historical_import_reprocess.py)
# ---------------------------------------------------------------------------


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
    return login_resp.json()


def login_user(client: TestClient, email: str, password: str = "secret123") -> str:
    resp = client.post(
        "/auth/login",
        data={"username": email, "password": password},
        headers={"content-type": "application/x-www-form-urlencoded"},
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["access_token"]


from sqlalchemy.ext.asyncio import async_sessionmaker


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


def _register_analyst(client: TestClient) -> str:
    email = f"szbackfill-{uuid.uuid4().hex[:8]}@example.com"
    user_data = register_user(client, email)
    asyncio.get_event_loop().run_until_complete(
        _set_user_role(
            client.session_maker,  # type: ignore[attr-defined]
            email,
            models.RoleEnum.analyst_pro,
        )
    )
    return login_user(client, email)


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
                for side in ("batter", "bowler", "non_striker"):
                    name = (delivery or {}).get(side)
                    if isinstance(name, str) and name:
                        registry_people[name] = uuid.uuid4().hex
    info["registry"] = {"people": registry_people}
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


def _make_zip(entries: dict[str, bytes]) -> bytes:
    """Build a ZIP in memory from a dict of {filename: content}."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


DRY_RUN_URL = "/api/historical-import/json/backfill/source-zip/dry-run"
APPLY_URL = "/api/historical-import/json/backfill/source-zip/apply"


# ---------------------------------------------------------------------------
# Dry-run tests
# ---------------------------------------------------------------------------


def test_source_zip_dry_run_maps_one_json_to_existing_record(client: TestClient) -> None:
    """ZIP dry-run maps one known JSON to one existing missing-source record."""
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, game_id = _create_and_apply_batch(client, token, payload)

    zip_bytes = _make_zip({"1018873.json": json.dumps(payload).encode("utf-8")})
    resp = client.post(
        DRY_RUN_URL,
        headers=_auth_headers(token),
        files={"file": ("cpl_batch.zip", zip_bytes, "application/zip")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "preview_ready"
    assert body["summary"]["exact_match_count"] >= 1
    file_result = next(f for f in body["files"] if f["file_name"] == "1018873.json")
    assert file_result["match_confidence"] == "exact_match"
    assert file_result["blocked_from_apply"] is False
    assert file_result["matched_target"]["batch_id"] == batch_id
    assert file_result["matched_target"]["match_id"] == game_id
    assert "teams" in file_result["matched_target"]["matched_on"]
    assert file_result["metadata"]["registry_people_available"] is True
    assert file_result["metadata"]["expected_deliveries"] > 0
    assert file_result["metadata"]["expected_wickets"] > 0


def test_source_zip_dry_run_maps_multiple_jsons_to_multiple_records(
    client: TestClient,
) -> None:
    """ZIP dry-run maps multiple JSONs to multiple records."""
    token = _register_analyst(client)
    payload_a = _cpl_payload_with_registry()
    payload_b = deepcopy(payload_a)
    # Tweak b slightly so it's a separate import
    info_b = payload_b.setdefault("info", {})
    info_b["match_number"] = 999
    batch_a, game_a = _create_and_apply_batch(client, token, payload_a)
    batch_b, game_b = _create_and_apply_batch(client, token, payload_b)

    zip_bytes = _make_zip(
        {
            "match_a.json": json.dumps(payload_a).encode("utf-8"),
            "match_b.json": json.dumps(payload_b).encode("utf-8"),
        }
    )
    resp = client.post(
        DRY_RUN_URL,
        headers=_auth_headers(token),
        files={"file": ("multi.zip", zip_bytes, "application/zip")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    # Both files must be scanned and reported
    file_names = {f["file_name"] for f in body["files"]}
    assert "match_a.json" in file_names
    assert "match_b.json" in file_names
    # At least one mapping should be reported (exact, likely, or ambiguous)
    summary = body["summary"]
    total_mapped = (
        summary["exact_match_count"]
        + summary["likely_match_count"]
        + summary["ambiguous_count"]
        + summary["no_match_count"]
    )
    assert total_mapped >= 2


def test_source_zip_dry_run_exact_filename_hint_wins(client: TestClient) -> None:
    """Exact filename/source-hint match is reported correctly."""
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, _game_id = _create_and_apply_batch(client, token, payload)

    zip_bytes = _make_zip({"exact_hint.json": json.dumps(payload).encode("utf-8")})
    resp = client.post(
        DRY_RUN_URL,
        headers=_auth_headers(token),
        files={"file": ("hints.zip", zip_bytes, "application/zip")},
    )
    assert resp.status_code == 200, resp.text
    result = resp.json()["files"][0]
    assert result["match_confidence"] in ("exact_match", "likely_match")
    assert result["blocked_from_apply"] is False


def test_source_zip_dry_run_reports_no_match(client: TestClient) -> None:
    """No match is reported and blocked from apply."""
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    _create_and_apply_batch(client, token, payload)

    no_match_payload = deepcopy(payload)
    no_match_payload.setdefault("info", {})["dates"] = ["2030-01-01"]

    zip_bytes = _make_zip({"no_match.json": json.dumps(no_match_payload).encode("utf-8")})
    resp = client.post(
        DRY_RUN_URL,
        headers=_auth_headers(token),
        files={"file": ("nomatch.zip", zip_bytes, "application/zip")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["summary"]["no_match_count"] >= 1
    result = body["files"][0]
    assert result["match_confidence"] == "no_match"
    assert result["blocked_from_apply"] is True


def test_source_zip_dry_run_reports_ambiguous_match(client: TestClient) -> None:
    """Ambiguous match is reported and blocked from apply."""
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_a, _ = _create_and_apply_batch(client, token, payload)
    dup_payload = deepcopy(payload)
    dup_payload["ambiguous_marker"] = uuid.uuid4().hex
    _create_and_apply_batch(client, token, dup_payload)

    zip_bytes = _make_zip({"ambig.json": json.dumps(payload).encode("utf-8")})
    resp = client.post(
        DRY_RUN_URL,
        headers=_auth_headers(token),
        files={"file": ("ambig.zip", zip_bytes, "application/zip")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["summary"]["ambiguous_count"] >= 1
    result = body["files"][0]
    assert result["match_confidence"] == "ambiguous"
    assert result["blocked_from_apply"] is True
    assert len(result["candidate_matches"]) >= 2


def test_source_zip_dry_run_reports_malformed_json_safely(client: TestClient) -> None:
    """Malformed JSON is reported without crashing."""
    token = _register_analyst(client)
    zip_bytes = _make_zip({"bad.json": b"not valid json {{{"})
    resp = client.post(
        DRY_RUN_URL,
        headers=_auth_headers(token),
        files={"file": ("malformed.zip", zip_bytes, "application/zip")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["summary"]["malformed_count"] >= 1
    result = body["files"][0]
    assert result["file_name"] == "bad.json"
    assert result["status"] in ("invalid", "unsupported", "error")
    assert result["blocked_from_apply"] is True


def test_source_zip_dry_run_reports_unsafe_zip_entry(client: TestClient) -> None:
    """Unsafe ZIP path (path traversal) is reported, not raised as HTTP exception."""
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()

    # Build a ZIP with a path-traversal filename by writing the raw ZipInfo
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        info = zipfile.ZipInfo("../etc/passwd.json")
        zf.writestr(info, json.dumps(payload))
    zip_bytes = buf.getvalue()

    resp = client.post(
        DRY_RUN_URL,
        headers=_auth_headers(token),
        files={"file": ("unsafe.zip", zip_bytes, "application/zip")},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["summary"]["unsafe_count"] >= 1
    unsafe_file = next((f for f in body["files"] if "unsafe" in f["message"].lower()), None)
    assert unsafe_file is not None
    assert unsafe_file["blocked_from_apply"] is True


def test_source_zip_dry_run_is_read_only(client: TestClient) -> None:
    """Dry-run mutates nothing."""
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, game_id = _create_and_apply_batch(client, token, payload)

    games_before = _count_games(client)
    deliveries_before = _count_delivery_rows(client)

    zip_bytes = _make_zip({"read_only_check.json": json.dumps(payload).encode("utf-8")})
    resp = client.post(
        DRY_RUN_URL,
        headers=_auth_headers(token),
        files={"file": ("ro.zip", zip_bytes, "application/zip")},
    )
    assert resp.status_code == 200, resp.text

    assert _count_games(client) == games_before
    assert _count_delivery_rows(client) == deliveries_before

    # Source payload NOT stored during dry-run
    game = _load_game(client, game_id)
    phases = game.phases if isinstance(game.phases, dict) else {}
    hist_meta = phases.get("historical_import") or {}
    assert isinstance(hist_meta, dict)
    assert "source_payload_reattach" not in hist_meta


def test_source_zip_dry_run_rejects_non_zip(client: TestClient) -> None:
    """Non-ZIP upload is rejected with 415."""
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    resp = client.post(
        DRY_RUN_URL,
        headers=_auth_headers(token),
        files={
            "file": (
                "single.json",
                json.dumps(payload).encode("utf-8"),
                "application/json",
            )
        },
    )
    assert resp.status_code == 415, resp.text


# ---------------------------------------------------------------------------
# Apply tests
# ---------------------------------------------------------------------------


def test_source_zip_apply_attaches_exact_mapping_without_delivery_mutation(
    client: TestClient,
) -> None:
    """Apply only exact/likely selected mappings; no delivery/player rows are created."""
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, game_id = _create_and_apply_batch(client, token, payload)

    games_before = _count_games(client)
    deliveries_before = _count_delivery_rows(client)

    zip_bytes = _make_zip({"apply_test.json": json.dumps(payload).encode("utf-8")})
    selected = json.dumps([{"file_name": "apply_test.json", "batch_id": batch_id}])

    resp = client.post(
        APPLY_URL,
        headers=_auth_headers(token),
        files={"file": ("apply.zip", zip_bytes, "application/zip")},
        data={"confirm": "true", "selected_mappings": selected},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["status"] == "applied"
    assert body["applied_count"] == 1
    assert body["results"][0]["status"] == "reattached"

    # No delivery or game rows created
    assert _count_games(client) == games_before
    assert _count_delivery_rows(client) == deliveries_before

    # Game now shows source_json_retained
    game = _load_game(client, game_id)
    phases = game.phases if isinstance(game.phases, dict) else {}
    hist_meta = phases.get("historical_import") or {}
    assert isinstance(hist_meta, dict)
    assert hist_meta.get("source_json_retained") is True
    assert isinstance(hist_meta.get("source_payload_reattach"), dict)
    reattach = hist_meta["source_payload_reattach"]
    assert reattach["workflow"] == "bulk_zip_source_reattach"

    # Batch also updated
    batch = _load_batch(client, batch_id)
    assert isinstance(batch.dry_run_summary, dict)
    reattach_from_batch = batch.dry_run_summary.get("source_payload_reattach")
    assert isinstance(reattach_from_batch, dict)
    assert reattach_from_batch["match_confidence"] == "exact_match"


def test_source_zip_apply_is_idempotent(client: TestClient) -> None:
    """Same ZIP re-upload is idempotent — second apply skips already-retained records."""
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, _game_id = _create_and_apply_batch(client, token, payload)

    zip_bytes = _make_zip({"idem.json": json.dumps(payload).encode("utf-8")})
    selected = json.dumps([{"file_name": "idem.json", "batch_id": batch_id}])

    # First apply: succeeds
    resp1 = client.post(
        APPLY_URL,
        headers=_auth_headers(token),
        files={"file": ("idem.zip", zip_bytes, "application/zip")},
        data={"confirm": "true", "selected_mappings": selected},
    )
    assert resp1.status_code == 200, resp1.text
    assert resp1.json()["applied_count"] == 1

    # Second apply on same batch → already retained → skipped (idempotent, not error)
    resp2 = client.post(
        APPLY_URL,
        headers=_auth_headers(token),
        files={"file": ("idem.zip", zip_bytes, "application/zip")},
        data={"confirm": "true", "selected_mappings": selected},
    )
    assert resp2.status_code == 200, resp2.text
    body2 = resp2.json()
    assert body2["skipped_count"] == 1
    assert body2["applied_count"] == 0


def test_source_zip_apply_blocks_ambiguous_mapping(client: TestClient) -> None:
    """Ambiguous mappings are blocked from apply."""
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_a, _ = _create_and_apply_batch(client, token, payload)
    dup = deepcopy(payload)
    dup["ambiguous_marker"] = uuid.uuid4().hex
    _create_and_apply_batch(client, token, dup)

    zip_bytes = _make_zip({"ambig_apply.json": json.dumps(payload).encode("utf-8")})
    selected = json.dumps([{"file_name": "ambig_apply.json", "batch_id": batch_a}])

    resp = client.post(
        APPLY_URL,
        headers=_auth_headers(token),
        files={"file": ("ambig.zip", zip_bytes, "application/zip")},
        data={"confirm": "true", "selected_mappings": selected},
    )
    assert resp.status_code == 422, resp.text


def test_source_zip_apply_blocks_overwrite_of_existing_retained_source(
    client: TestClient,
) -> None:
    """Existing retained source overwrite is blocked."""
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, game_id = _create_and_apply_batch(client, token, payload)

    zip_bytes = _make_zip({"overwrite.json": json.dumps(payload).encode("utf-8")})
    selected = json.dumps([{"file_name": "overwrite.json", "batch_id": batch_id}])

    # First apply
    r1 = client.post(
        APPLY_URL,
        headers=_auth_headers(token),
        files={"file": ("ow.zip", zip_bytes, "application/zip")},
        data={"confirm": "true", "selected_mappings": selected},
    )
    assert r1.status_code == 200, r1.text
    assert r1.json()["applied_count"] == 1

    # Second apply on same batch → must be skipped (overwrite blocked)
    r2 = client.post(
        APPLY_URL,
        headers=_auth_headers(token),
        files={"file": ("ow.zip", zip_bytes, "application/zip")},
        data={"confirm": "true", "selected_mappings": selected},
    )
    assert r2.status_code == 200, r2.text
    body2 = r2.json()
    assert body2["skipped_count"] == 1
    assert body2["applied_count"] == 0


def test_source_zip_apply_requires_confirm_true(client: TestClient) -> None:
    """Apply without confirm=true returns 422."""
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, _ = _create_and_apply_batch(client, token, payload)

    zip_bytes = _make_zip({"no_confirm.json": json.dumps(payload).encode("utf-8")})
    selected = json.dumps([{"file_name": "no_confirm.json", "batch_id": batch_id}])

    resp = client.post(
        APPLY_URL,
        headers=_auth_headers(token),
        files={"file": ("nc.zip", zip_bytes, "application/zip")},
        data={"confirm": "false", "selected_mappings": selected},
    )
    assert resp.status_code == 422, resp.text


def test_source_zip_apply_follow_up_message_present(client: TestClient) -> None:
    """Apply response includes the post-apply instruction."""
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, _ = _create_and_apply_batch(client, token, payload)

    zip_bytes = _make_zip({"msg_check.json": json.dumps(payload).encode("utf-8")})
    selected = json.dumps([{"file_name": "msg_check.json", "batch_id": batch_id}])

    resp = client.post(
        APPLY_URL,
        headers=_auth_headers(token),
        files={"file": ("msg.zip", zip_bytes, "application/zip")},
        data={"confirm": "true", "selected_mappings": selected},
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "reprocess" in body["follow_up_message"].lower()
    assert "delivery" in body["follow_up_message"].lower()


def test_source_zip_apply_audit_shows_source_retained_after_apply(
    client: TestClient,
) -> None:
    """After apply, backfill audit shows source_json_retained=True."""
    token = _register_analyst(client)
    payload = _cpl_payload_with_registry()
    batch_id, _game_id = _create_and_apply_batch(client, token, payload)

    zip_bytes = _make_zip({"audit_check.json": json.dumps(payload).encode("utf-8")})
    selected = json.dumps([{"file_name": "audit_check.json", "batch_id": batch_id}])

    apply_resp = client.post(
        APPLY_URL,
        headers=_auth_headers(token),
        files={"file": ("audit.zip", zip_bytes, "application/zip")},
        data={"confirm": "true", "selected_mappings": selected},
    )
    assert apply_resp.status_code == 200, apply_resp.text
    assert apply_resp.json()["applied_count"] == 1

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
