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


def _cricsheet_delivery(
    batter: str,
    non_striker: str,
    bowler: str,
    *,
    runs: int = 1,
) -> dict[str, object]:
    return {
        "batter": batter,
        "non_striker": non_striker,
        "bowler": bowler,
        "runs": {"batter": runs, "extras": 0, "total": runs},
    }


def _build_test_match_payload() -> dict[str, object]:
    return {
        "meta": {"data_version": "0.92"},
        "info": {
            "match_type": "Test",
            "venue": "Providence Stadium",
            "dates": ["2024-03-01", "2024-03-02", "2024-03-03"],
            "season": "2024",
            "event": {"name": "ICC Test Championship", "match_number": 3},
            "teams": ["West Indies", "India"],
            "players": {
                "West Indies": ["K Brathwaite", "T Chanderpaul", "J Holder"],
                "India": ["R Sharma", "Rahul Sharma", "R Ashwin", "R Dravid"],
            },
            "registry": {
                "people": {
                    "K Brathwaite": "wi-1",
                    "T Chanderpaul": "wi-2",
                    "R Sharma": "in-1",
                    "R Ashwin": "in-2",
                    "R Dravid": "in-3",
                }
            },
            "outcome": {"result": "draw"},
        },
        "innings": [
            {
                "West Indies": {
                    "runs": 250,
                    "wickets": 10,
                    "overs": [
                        {
                            "over": 0,
                            "deliveries": [
                                _cricsheet_delivery(
                                    "K Brathwaite",
                                    "T Chanderpaul",
                                    "R Ashwin",
                                )
                            ],
                        }
                    ],
                }
            },
            {
                "India": {
                    "runs": 300,
                    "wickets": 10,
                    "overs": [
                        {
                            "over": 0,
                            "deliveries": [_cricsheet_delivery("R Sharma", "R Dravid", "J Holder")],
                        }
                    ],
                }
            },
            {
                "West Indies": {
                    "runs": 180,
                    "wickets": 8,
                    "overs": [
                        {
                            "over": 0,
                            "deliveries": [
                                _cricsheet_delivery(
                                    "T Chanderpaul",
                                    "J Holder",
                                    "R Ashwin",
                                )
                            ],
                        }
                    ],
                }
            },
            {
                "India": {
                    "runs": 90,
                    "wickets": 2,
                    "overs": [
                        {
                            "over": 0,
                            "deliveries": [
                                _cricsheet_delivery(
                                    "Rahul Sharma",
                                    "R Dravid",
                                    "J Holder",
                                )
                            ],
                        }
                    ],
                }
            },
        ],
    }


@pytest.mark.parametrize(
    (
        "fixture_path",
        "expected_teams",
        "expected_result",
        "expected_venue",
        "expected_match_number",
    ),
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
    assert data["schema_classification"]["adapter_version"] == "10s.0"
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
        response = client.post(
            "/api/historical-import/json/dry-run", json=_load_cricsheet_fixture()
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "valid"
    assert data["detected_format"] == "cricsheet_json"
    assert data["schema_classification"]["source_schema_category"] == "cricsheet_style_json"
    assert data["teams_preview"] == ["Sanitized Strikers", "Sanitized Royals"]
    assert data["innings_count"] == 2
    assert data["delivery_count"] == 24
    assert data["diagnostics"]["classification"]["competition_code"] == "UNKNOWN"
    assert data["diagnostics"]["classification"]["format_category"] == "T20"
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
            files={
                "file": ("simulated_t20_match.json", FIXTURE_PATH.read_bytes(), "application/json")
            },
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


def test_dry_run_multi_day_test_payload_reports_readiness_and_identity_risks() -> None:
    with TestClient(app) as client:
        response = client.post(
            "/api/historical-import/json/dry-run", json=_build_test_match_payload()
        )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "valid"
    assert data["innings_count"] == 4
    assert data["diagnostics"]["classification"]["competition_code"] == "INTERNATIONAL_TEST_SERIES"
    assert data["diagnostics"]["classification"]["format_category"] == "Test"
    assert data["diagnostics"]["classification"]["completeness_grade"] == "multi_day_complete"
    assert data["diagnostics"]["classification"]["analysis_readiness"] == "limited"
    assert data["diagnostics"]["multi_day"]["is_multi_day"] is True
    assert data["diagnostics"]["multi_day"]["date_range"]["day_count"] == 3
    assert data["diagnostics"]["multi_day"]["innings_order"] == [
        "West Indies",
        "India",
        "West Indies",
        "India",
    ]
    assert "Rahul Sharma" in data["diagnostics"]["player_identity_risks"]["missing_player_ids"]
    assert data["canonical_preview"]["competition_context"]["analysis_readiness"] == "limited"
    assert (
        data["canonical_preview"]["competition_context"]["competition_code"]
        == "INTERNATIONAL_TEST_SERIES"
    )


@pytest.mark.parametrize(
    ("event_name", "expected_category", "expected_competition_type"),
    [
        ("Caribbean Premier League", "franchise_tournament_json", "franchise_league"),
        ("ICC World Cup", "international_match_json", "international_tournament"),
        ("County Club League", "domestic_club_match_json", "domestic_league"),
        ("School Championship", "school_academy_match_json", "school_or_custom"),
        ("Academy Development League", "domestic_club_match_json", "domestic_league"),
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


def test_dry_run_reports_custom_competition_and_unresolved_venue_conservatively() -> None:
    payload = _cricsheet_minimal_payload("Island Invitational Friendly")
    info = payload["info"]
    assert isinstance(info, dict)
    info["venue"] = "Village Park"
    info["dates"] = []
    info["teams"] = ["Custom XI", "Community XI"]

    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["status"] == "valid"
    assert data["diagnostics"]["classification"]["competition_code"] == "CUSTOM"
    assert data["diagnostics"]["classification"]["gender_category"] == "unknown"
    assert data["diagnostics"]["venue_check"]["unknown_venues"] == ["Village Park"]
    assert data["diagnostics"]["scan_summary"]["expected_matches"] == 1
    assert any(issue["code"] == "MISSING_DATE" for issue in data["warnings"])


def test_dry_run_maps_english_domestic_t20_and_resolves_kennington_oval() -> None:
    payload = _cricsheet_minimal_payload("Vitality Blast")
    info = payload["info"]
    assert isinstance(info, dict)
    info["teams"] = ["Surrey", "Lancashire"]
    info["venue"] = "Kennington Oval, London"
    info["city"] = "London"

    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["diagnostics"]["classification"]["competition_code"] == "T20_BLAST"
    assert data["diagnostics"]["classification"]["competition_type"] == "domestic_league"
    assert (
        data["diagnostics"]["venue_check"]["venue_canonical"] == "Kennington Oval, London, England"
    )
    assert data["diagnostics"]["venue_check"]["venue_country"] == "England"
    assert data["diagnostics"]["venue_check"]["venue_confidence"] in {"high", "medium"}
    assert data["canonical_preview"]["venue_context"]["country"] == "England"
    assert not any(issue["code"] == "UNKNOWN_COMPETITION" for issue in data["warnings"])
    assert not any(issue["code"] == "COMPETITION_TYPE_UNKNOWN" for issue in data["warnings"])


def test_dry_run_cpl_context_resolves_queens_park_oval_country() -> None:
    payload = _cricsheet_minimal_payload("Caribbean Premier League")
    info = payload["info"]
    assert isinstance(info, dict)
    info["teams"] = ["Trinbago Knight Riders", "Barbados Royals"]
    info["venue"] = "Queen's Park Oval"
    info["city"] = "Port of Spain"

    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["diagnostics"]["classification"]["competition_code"] == "CPL_MEN"
    assert (
        data["diagnostics"]["venue_check"]["venue_canonical"]
        == "Queen's Park Oval, Port of Spain, Trinidad and Tobago"
    )
    assert data["diagnostics"]["venue_check"]["venue_country"] == "Trinidad and Tobago"
    assert data["diagnostics"]["venue_check"]["venue_resolution_source"] == "alias_registry"


def test_dry_run_ambiguous_oval_stays_unresolved_without_context() -> None:
    payload = _cricsheet_minimal_payload("Unknown Cup")
    info = payload["info"]
    assert isinstance(info, dict)
    info["venue"] = "The Oval"
    info["teams"] = ["Team A", "Team B"]
    info.pop("city", None)

    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["diagnostics"]["venue_check"]["unknown_venues"] == ["The Oval"]
    assert data["diagnostics"]["venue_check"]["unresolved_reason"] == "ambiguous_without_context"
    assert any(issue["code"] == "UNKNOWN_VENUE_ALIAS" for issue in data["warnings"])


def test_dry_run_unknown_competition_remains_unknown() -> None:
    payload = _cricsheet_minimal_payload("Neighborhood Showdown")

    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["diagnostics"]["classification"]["competition_code"] == "UNKNOWN"
    assert any(issue["code"] == "UNKNOWN_COMPETITION" for issue in data["warnings"])
    warning = next(issue for issue in data["warnings"] if issue["code"] == "UNKNOWN_COMPETITION")
    assert "safe unknown classification" in warning["message"]


def test_dry_run_maps_wcpl_separately_when_metadata_indicates_women() -> None:
    payload = _cricsheet_minimal_payload("Women's Caribbean Premier League")
    info = payload["info"]
    assert isinstance(info, dict)
    info["gender"] = "female"

    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["diagnostics"]["classification"]["competition_code"] == "WCPL"
    assert data["diagnostics"]["classification"]["gender_category"] == "women"


def test_dry_run_test_without_international_context_maps_to_domestic_multi_day() -> None:
    payload = _cricsheet_minimal_payload("County Championship")
    info = payload["info"]
    assert isinstance(info, dict)
    info["match_type"] = "Test"
    info["teams"] = ["Surrey", "Lancashire"]
    info["dates"] = ["2026-05-20", "2026-05-21", "2026-05-22"]

    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["diagnostics"]["classification"]["format_category"] == "Test"
    assert data["diagnostics"]["classification"]["competition_code"] == "DOMESTIC_MULTI_DAY"
    assert data["diagnostics"]["classification"]["competition_type"] == "domestic_league"


def test_dry_run_classifies_one_day_cup_odm_and_edgbaston_context() -> None:
    payload = _cricsheet_minimal_payload("One-Day Cup")
    info = payload["info"]
    assert isinstance(info, dict)
    info["match_type"] = "ODM"
    info["teams"] = ["Durham", "Warwickshire"]
    info["venue"] = "Edgbaston, Birmingham"
    info["city"] = "Birmingham"
    info["dates"] = ["2023-08-20"]

    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["diagnostics"]["classification"]["competition_code"] == "ONE_DAY_CUP"
    assert data["diagnostics"]["classification"]["competition_type"] == "domestic_cup"
    assert data["diagnostics"]["classification"]["format_category"] == "ODI"
    assert data["diagnostics"]["classification"]["competition_region"] == "England"
    assert data["diagnostics"]["venue_check"]["venue_canonical"] == "Edgbaston, Birmingham, England"
    assert data["diagnostics"]["venue_check"]["venue_country"] == "England"
    assert not any(
        issue["code"] in {"UNKNOWN_COMPETITION", "UNKNOWN_VENUE_ALIAS", "COMPETITION_TYPE_UNKNOWN"}
        for issue in data["warnings"]
    )


def test_dry_run_classifies_international_test_series_and_adelaide_context() -> None:
    payload = _cricsheet_minimal_payload("South Africa in Australia Test Series")
    info = payload["info"]
    assert isinstance(info, dict)
    info["match_type"] = "Test"
    info["teams"] = ["Australia", "South Africa"]
    info["venue"] = "Adelaide Oval"
    info["city"] = "Adelaide"
    info["dates"] = ["2016-11-24", "2016-11-25", "2016-11-26"]

    with TestClient(app) as client:
        response = client.post("/api/historical-import/json/dry-run", json=payload)

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["diagnostics"]["classification"]["competition_code"] == "INTERNATIONAL_TEST_SERIES"
    assert data["diagnostics"]["classification"]["competition_type"] == "international_series"
    assert data["diagnostics"]["classification"]["format_category"] == "Test"
    assert (
        data["diagnostics"]["venue_check"]["venue_canonical"]
        == "Adelaide Oval, Adelaide, Australia"
    )
    assert data["diagnostics"]["venue_check"]["venue_country"] == "Australia"


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
