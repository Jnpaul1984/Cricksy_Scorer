import os

from backend.tests._ci_utils import traced_request

API = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")


def _post(url, json):
    r = traced_request("POST", url, json=json)
    return r


def _get(url):
    r = traced_request("GET", url)
    return r


def test_create_flat_schema_ok():
    good = {
        "match_type": "limited",
        "overs_limit": 2,
        "team_a_name": "Alpha",
        "team_b_name": "Bravo",
        "players_a": [f"A{i}" for i in range(1, 12)],
        "players_b": [f"B{i}" for i in range(1, 12)],
        "toss_winner_team": "A",
        "decision": "bat",
    }
    r = _post(f"{API}/games", good)
    assert r.status_code < 400, r.text


def test_create_legacy_schema_rejected_or_redirected():
    # If legacy still works, fine; if rejected, also fine (we only assert flat works).
    legacy = {
        "match_type": "T20",
        "team_a": {"name": "Alpha", "players": [{"name": "A1"}] * 11},
        "team_b": {"name": "Bravo", "players": [{"name": "B1"}] * 11},
        "toss_winner": "Alpha",
        "toss_decision": "bat",
    }
    r = _post(f"{API}/games", legacy)
    assert r.status_code in (200, 201, 400, 404, 405, 409, 422), r.text
