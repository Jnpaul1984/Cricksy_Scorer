from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

from backend.main import app


FIXTURE_PATH = Path(__file__).resolve().parent / "simulated_t20_match.json"
CRICSHEET_FIXTURE_PATH = Path(__file__).resolve().parent / "sanitized_cricsheet_t20.json"


def _load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _load_cricsheet_fixture() -> dict[str, object]:
    return json.loads(CRICSHEET_FIXTURE_PATH.read_text(encoding="utf-8"))


def test_dry_run_json_payload_valid_preview() -> None:
    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=_load_fixture())

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "valid"
    assert data["detected_format"] == "cricksy_fixture"
    assert data["innings_count"] == 2
    assert data["delivery_count"] > 0
    assert data["no_persistence"] is True
    assert len(data["duplicate_detection"]["source_hash_sha256"]) == 64
    assert "Alpha Player 1" in data["player_names_found"]


def test_dry_run_sanitized_cricsheet_fixture_valid_preview() -> None:
    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=_load_cricsheet_fixture())

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "valid"
    assert data["detected_format"] == "cricsheet_json"
    assert data["teams_preview"] == ["Sanitized Royals", "Sanitized Strikers"]
    assert data["innings_count"] == 2
    assert data["delivery_count"] == 24


def test_dry_run_accepts_multipart_json_file() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/dry-run",
            files={"file": ("simulated_t20_match.json", FIXTURE_PATH.read_bytes(), "application/json")},
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "valid"
    assert data["detected_sections"]["innings"] is True


def test_dry_run_invalid_json_payload_returns_structured_error() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/dry-run",
            files={"file": ("broken.json", b"{this-is-not-json", "application/json")},
        )

    assert response.status_code == 400
    data = response.json()
    assert data["status"] == "invalid"
    assert any(issue["code"] == "INVALID_JSON" for issue in data["errors"])


def test_dry_run_unsupported_shape_returns_structured_error() -> None:
    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json={"foo": "bar"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unsupported"
    assert any(issue["code"] == "UNSUPPORTED_FORMAT" for issue in data["errors"])


def test_dry_run_missing_innings_and_deliveries_flags_errors() -> None:
    payload = {"matchType": "T20", "teams": ["A", "B"]}

    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"invalid", "unsupported"}
    assert any(issue["code"] == "MISSING_INNINGS" for issue in data["errors"])


def test_dry_run_innings_without_delivery_events_flags_error() -> None:
    payload = {
        "matchType": "T20",
        "teams": ["A", "B"],
        "innings": [{"team": "A", "runs": 120, "wickets": 5}],
    }

    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "invalid"
    assert any(issue["code"] == "MISSING_DELIVERY_EVENTS" for issue in data["errors"])


def test_dry_run_requires_two_teams_in_metadata() -> None:
    payload = {
        "matchType": "T20",
        "teams": ["A"],
        "innings": [
            {
                "team": "A",
                "balls": [{"over": 1, "ball": 1, "runs": 1, "batsman": "A1", "bowler": "B1"}],
            }
        ],
    }

    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "invalid"
    assert any(issue["code"] == "MISSING_TEAMS" for issue in data["errors"])


def test_dry_run_does_not_create_games() -> None:
    with TestClient(app) as client:
        before = client.get("/games/results")
        assert before.status_code == 200
        before_games = before.json()
        assert isinstance(before_games, list)

        response = client.post("/api/historical-import/json/dry-run", json=_load_fixture())
        assert response.status_code == 200

        after = client.get("/games/results")
        assert after.status_code == 200
        after_games = after.json()
        assert isinstance(after_games, list)

    assert len(after_games) == len(before_games)
