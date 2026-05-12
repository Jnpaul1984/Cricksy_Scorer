from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app

FIXTURE_PATH = Path(__file__).resolve().parent / "simulated_t20_match.json"


def _load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _build_zip(entries: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return stream.getvalue()


def test_bulk_zip_dry_run_accepts_multiple_valid_json_files() -> None:
    fixture = _load_fixture()
    payload = _build_zip(
        {
            "match_a.json": json.dumps(fixture).encode("utf-8"),
            "match_b.json": json.dumps({**fixture, "matchType": "ODI"}).encode("utf-8"),
        }
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/bulk-zip/dry-run",
            files={"file": ("matches.zip", payload, "application/zip")},
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "preview_ready"
    assert data["json_entries"] == 2
    assert data["summary"]["valid"] == 2
    assert all(file_item["status"] == "valid" for file_item in data["files"])
    assert data["selected_apply_requires_confirm"] is True


def test_bulk_zip_dry_run_rejects_non_zip_upload() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/bulk-zip/dry-run",
            files={"file": ("matches.json", b"{}", "application/json")},
        )

    assert response.status_code == 415, response.text
    assert "zip" in response.json()["detail"].lower()


def test_bulk_zip_dry_run_rejects_unsafe_zip_paths() -> None:
    fixture = _load_fixture()
    payload = _build_zip({"../escape.json": json.dumps(fixture).encode("utf-8")})

    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/bulk-zip/dry-run",
            files={"file": ("unsafe.zip", payload, "application/zip")},
        )

    assert response.status_code == 400, response.text
    assert "unsafe" in response.json()["detail"].lower()


def test_bulk_zip_dry_run_reports_non_json_entries() -> None:
    fixture = _load_fixture()
    payload = _build_zip(
        {
            "match.json": json.dumps(fixture).encode("utf-8"),
            "notes.txt": b"not-json",
        }
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/bulk-zip/dry-run",
            files={"file": ("mixed.zip", payload, "application/zip")},
        )

    assert response.status_code == 200, response.text
    files = {f["file_name"]: f for f in response.json()["files"]}
    assert files["match.json"]["status"] == "valid"
    assert files["notes.txt"]["status"] == "unsupported"


def test_bulk_zip_dry_run_detects_duplicates_within_zip() -> None:
    fixture = _load_fixture()
    raw = json.dumps(fixture).encode("utf-8")
    payload = _build_zip({"a.json": raw, "b.json": raw})

    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/bulk-zip/dry-run",
            files={"file": ("dupes.zip", payload, "application/zip")},
        )

    assert response.status_code == 200, response.text
    files = {f["file_name"]: f for f in response.json()["files"]}
    assert files["a.json"]["status"] == "valid"
    assert files["b.json"]["status"] == "duplicate"
    assert files["b.json"]["duplicate_within_zip"] is True


def test_bulk_zip_dry_run_detects_duplicates_against_existing_batches() -> None:
    fixture = _load_fixture()
    raw = json.dumps(fixture).encode("utf-8")

    with TestClient(app) as client:
        single = client.post(
            "/api/historical-import/json/dry-run",
            json=fixture,
            params={"record_preview": "true"},
        )
        assert single.status_code == 200, single.text
        existing_batch = single.json()["record_id"]

        payload = _build_zip({"dup.json": raw})
        response = client.post(
            "/api/historical-import/json/bulk-zip/dry-run",
            files={"file": ("dupes.zip", payload, "application/zip")},
        )

    assert response.status_code == 200, response.text
    file_result = response.json()["files"][0]
    assert file_result["status"] == "duplicate"
    assert file_result["duplicate_batch_id"] == existing_batch


def test_bulk_zip_dry_run_invalid_json_does_not_block_valid_preview() -> None:
    fixture = _load_fixture()
    payload = _build_zip(
        {
            "ok.json": json.dumps(fixture).encode("utf-8"),
            "bad.json": b"{broken",
        }
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/bulk-zip/dry-run",
            files={"file": ("mixed.zip", payload, "application/zip")},
        )

    assert response.status_code == 200, response.text
    files = {f["file_name"]: f for f in response.json()["files"]}
    assert files["ok.json"]["status"] == "valid"
    assert files["bad.json"]["status"] == "invalid"


def test_bulk_zip_apply_requires_explicit_confirmation() -> None:
    fixture = _load_fixture()
    payload = _build_zip({"ok.json": json.dumps(fixture).encode("utf-8")})

    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/bulk-zip/apply",
            files={"file": ("matches.zip", payload, "application/zip")},
            data={"confirm": "false", "selected_files": json.dumps(["ok.json"])},
        )
        batches = client.get("/api/historical-import/json/batches")

    assert response.status_code == 422, response.text
    assert batches.status_code == 200
    assert batches.json() == []


def test_bulk_zip_apply_only_applies_selected_valid_files() -> None:
    fixture = _load_fixture()
    payload = _build_zip(
        {
            "ok.json": json.dumps(fixture).encode("utf-8"),
            "bad.json": b"{broken",
        }
    )

    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/bulk-zip/apply",
            files={"file": ("matches.zip", payload, "application/zip")},
            data={"confirm": "true", "selected_files": json.dumps(["ok.json", "bad.json"])},
        )
        batches = client.get("/api/historical-import/json/batches").json()

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["applied_count"] == 1
    assert data["skipped_count"] == 1
    result_map = {item["file_name"]: item for item in data["results"]}
    assert result_map["ok.json"]["status"] == "applied"
    applied_game_id = result_map["ok.json"]["applied_game_id"]
    assert applied_game_id is not None
    assert result_map["ok.json"]["batch_id"] is not None
    assert result_map["bad.json"]["status"] == "skipped"

    # Verify the historical import batch is correctly created for the selected valid file.
    # We use batch-local assertions rather than the global /games/results list to avoid
    # brittleness in the full test suite where /games/results mixes in-memory and real-DB
    # state across tests.
    assert len(batches) == 1, "Exactly one historical import batch must be created."
    assert batches[0]["is_finalized"] is True
    assert batches[0]["applied_game_id"] == applied_game_id
    # status=="valid" confirms the batch passed dry-run validation and was created via
    # the historical import path, not the live scoring engine.
    assert batches[0]["status"] == "valid", (
        "Applied batch must have status='valid'; got "
        f"{batches[0]['status']!r}. This confirms the game was created via the "
        "historical import path and not through a live-scoring mutation."
    )
    # bad.json was skipped (not errored), so there must be no apply errors.
    assert data["error_count"] == 0, (
        "Bulk apply must not produce error results when the only non-applied file "
        "is an invalid JSON that should be skipped."
    )
