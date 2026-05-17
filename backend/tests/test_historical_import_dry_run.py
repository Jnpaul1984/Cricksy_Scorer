from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.main import app


FIXTURE_PATH = Path(__file__).resolve().parent / "simulated_t20_match.json"
CRICSHEET_FIXTURE_PATH = Path(__file__).resolve().parent / "sanitized_cricsheet_t20.json"
CRICSHEET_635215_FIXTURE_PATH = Path(__file__).resolve().parent / "sanitized_cricsheet_635215.json"
CRICSHEET_635216_FIXTURE_PATH = Path(__file__).resolve().parent / "sanitized_cricsheet_635216.json"


def _load_fixture() -> dict[str, object]:
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))


def _load_cricsheet_fixture() -> dict[str, object]:
    return json.loads(CRICSHEET_FIXTURE_PATH.read_text(encoding="utf-8"))


def _cricsheet_minimal_payload(event_name: str) -> dict[str, object]:
    return {
        "meta": {"data_version": "0.92"},
        "info": {
            "match_type": "T20",
            "venue": "Sample Ground",
            "dates": ["2025-01-01"],
            "season": "2025",
            "event": {"name": event_name, "match_number": 1},
            "teams": ["Team A", "Team B"],
        },
        "innings": [
            {
                "Team A": {
                    "overs": [
                        {
                            "over": 0,
                            "deliveries": [
                                {
                                    "batter": "A1",
                                    "non_striker": "A2",
                                    "bowler": "B1",
                                    "runs": {"batter": 1, "extras": 0, "total": 1},
                                }
                            ],
                        }
                    ]
                }
            },
            {
                "Team B": {
                    "overs": [
                        {
                            "over": 0,
                            "deliveries": [
                                {
                                    "batter": "B1",
                                    "non_striker": "B2",
                                    "bowler": "A1",
                                    "runs": {"batter": 0, "extras": 0, "total": 0},
                                }
                            ],
                        }
                    ]
                }
            },
        ],
    }


@pytest.mark.parametrize(
    ("fixture_path", "expected_teams", "expected_result", "expected_venue", "expected_match_number"),
    [
        (
            CRICSHEET_635215_FIXTURE_PATH,
            ["Barbados Tridents", "St Lucia Zouks"],
            "Barbados Tridents won by 17 runs",
            "Kensington Oval, Bridgetown",
            1,
        ),
        (
            CRICSHEET_635216_FIXTURE_PATH,
            ["Guyana Amazon Warriors", "Trinidad & Tobago Red Steel"],
            "Guyana Amazon Warriors won by 19 runs",
            "Providence Stadium",
            2,
        ),
    ],
)
def test_dry_run_real_structure_metadata_and_innings_team_mapping(
    fixture_path: Path,
    expected_teams: list[str],
    expected_result: str,
    expected_venue: str,
    expected_match_number: int,
) -> None:
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))

    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "valid"
    assert data["detected_format"] == "cricsheet_json"
    assert data["schema_classification"]["source_schema"] == "cricsheet_json"
    assert data["schema_classification"]["adapter_id"] == "historical_json_competition_adapter"
    assert data["schema_classification"]["adapter_version"] == "10b.1"
    assert data["schema_classification"]["source_schema_category"] == "franchise_tournament_json"
    assert data["teams_preview"] == expected_teams
    assert [inning["team"] for inning in data["innings_preview"]] == expected_teams
    assert data["metadata_preview"]["result"] == expected_result
    assert data["metadata_preview"]["venue"] == expected_venue
    assert data["metadata_preview"]["event_name"] == "Caribbean Premier League"
    assert data["metadata_preview"]["season"] == "2013"
    assert data["metadata_preview"]["match_number"] == expected_match_number
    assert len(data["metadata_preview"]["source_dates"]) == 1
    assert data["innings_preview"][0]["legal_balls"] == 6
    assert data["innings_preview"][0]["overs"] == 1.0
    assert data["innings_preview"][1]["legal_balls"] == 6
    assert data["innings_preview"][1]["overs"] == 1.0


def test_dry_run_json_payload_valid_preview() -> None:
    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=_load_fixture())

    assert response.status_code == 200, response.text
    data = response.json()

    assert data["status"] == "valid"
    assert data["detected_format"] == "cricksy_fixture"
    assert data["schema_classification"]["source_schema_category"] == "cricksy_internal_json"
    assert data["canonical_preview"]["competition_context"]["competition_type"] == "unknown"
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
    assert data["schema_classification"]["source_schema_category"] == "cricsheet_style_json"
    assert data["teams_preview"] == ["Sanitized Strikers", "Sanitized Royals"]
    assert data["innings_count"] == 2
    assert data["delivery_count"] == 24
    assert sorted(data["canonical_preview"].keys()) == [
        "competition_context",
        "delivery_events",
        "innings_summaries",
        "match_metadata",
        "player_identity_mapping",
        "result_metadata",
        "source_provenance",
        "squad_roster_snapshot",
        "team_context",
        "tournament_season_context",
        "validation_report",
        "venue_context",
    ]


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
    assert data["canonical_preview"] is None
    assert any(issue["code"] == "INVALID_JSON" for issue in data["errors"])


def test_dry_run_unsupported_shape_returns_structured_error() -> None:
    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json={"foo": "bar"})

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "unsupported"
    assert data["canonical_preview"] is None
    assert data["schema_classification"]["source_schema_category"] == "unknown_unsupported_json"
    assert any(issue["code"] == "UNSUPPORTED_FORMAT" for issue in data["errors"])


@pytest.mark.parametrize(
    ("event_name", "expected_category", "expected_competition_type"),
    [
        ("Caribbean Premier League", "franchise_tournament_json", "franchise"),
        ("ICC World Cup", "international_match_json", "international"),
        ("County Club League", "domestic_club_match_json", "domestic"),
        ("School Championship", "school_academy_match_json", "school"),
        ("Academy Development League", "school_academy_match_json", "academy"),
    ],
)
def test_dry_run_schema_classification_expands_by_competition_type(
    event_name: str,
    expected_category: str,
    expected_competition_type: str,
) -> None:
    payload = _cricsheet_minimal_payload(event_name)
    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "valid"
    assert data["schema_classification"]["source_schema_category"] == expected_category
    assert (
        data["canonical_preview"]["competition_context"]["competition_type"]
        == expected_competition_type
    )


def test_dry_run_missing_innings_and_deliveries_flags_errors() -> None:
    payload = {"matchType": "T20", "teams": ["A", "B"]}

    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["status"] in {"invalid", "unsupported"}
    assert data["canonical_preview"] is None
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
    assert data["canonical_preview"] is None
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
    assert data["canonical_preview"] is None
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
