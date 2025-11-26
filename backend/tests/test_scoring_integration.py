"""
Integration tests for core scoring system.

Tests complete workflows:
- Creating a game and scoring deliveries via API
- Real-time WebSocket updates during scoring
- Undo functionality via API
- Data persistence and retrieval through full stack

Relevant scoring routes exercised below (trimmed for clarity):

POST /games/{game_id}/deliveries (backend.routes.gameplay.add_delivery)
    async def add_delivery(...):
        # validates/wires input, applies mid-over bowler rules,
        # mutates runtime state, emits live_bus updates, returns snapshot

POST /games/{game_id}/undo-last (backend.routes.gameplay.undo_last_delivery)
    async def undo_last_delivery(...):
        # pops the last delivery from ledger, replays scorecard,
        # persists and emits the updated snapshot

POST /games/{game_id}/innings/start (backend.routes.gameplay.start_next_innings)
    async def start_next_innings(...):
        # archives prior innings, resets runtime, wires new striker/bowler

POST /games/{game_id}/overs/change_bowler (backend.routes.gameplay.change_bowler_mid_over)
    async def change_bowler_mid_over(...):
        # verifies over-in-progress, enforces single change per over,
        # updates current_bowler_id and emits snapshot

GET /games/{game_id}/snapshot (backend.routes.gameplay.get_snapshot)
    async def get_snapshot(...):
        # rebuilds runtime fields, dedupes ledger, returns canonical view
"""

import os
from typing import Any

import pytest
from starlette.testclient import TestClient

# Set in-memory mode for tests
os.environ["CRICKSY_IN_MEMORY_DB"] = "1"

from backend.app import create_app
from backend.services import live_bus
from backend.sql_app import crud


class MockSocketIOServer:
    """Mock Socket.IO server for testing real-time updates."""

    def __init__(self):
        self.emitted_events = []

    async def emit(self, event, data, *, room=None, namespace=None):
        """Record emitted events."""
        self.emitted_events.append(
            {"event": event, "data": data, "room": room, "namespace": namespace}
        )

    def clear_events(self):
        """Clear recorded events."""
        self.emitted_events = []


@pytest.fixture
def client():
    """Create test client with in-memory database and mock Socket.IO."""
    # Create app
    _, fastapi_app = create_app()

    # Setup mock socket for testing
    mock_sio = MockSocketIOServer()
    live_bus.set_socketio_server(mock_sio)

    # Attach mock_sio to app state so tests can access it
    fastapi_app.state.mock_sio = mock_sio

    with TestClient(fastapi_app) as test_client:
        yield test_client


DEFAULT_GAME_PAYLOAD = {
    "match_type": "limited",
    "overs_limit": 20,
    "team_a_name": "Team Alpha",
    "team_b_name": "Team Beta",
    "players_a": [f"Alpha{i}" for i in range(1, 12)],
    "players_b": [f"Beta{i}" for i in range(1, 12)],
    "toss_winner_team": "Team Alpha",
    "decision": "bat",
}


def _extract_game_id(payload: dict[str, Any]) -> str:
    return payload.get("id") or payload.get("gid") or (payload.get("game") or {}).get("id")


def _bootstrap_game(client: TestClient) -> tuple[str, list[dict[str, Any]], list[dict[str, Any]]]:
    response = client.post("/games", json=DEFAULT_GAME_PAYLOAD)
    assert response.status_code in (200, 201), response.text
    data = response.json()
    game_id = _extract_game_id(data)
    assert game_id, f"Unable to extract game id from payload: {data}"
    details = client.get(f"/games/{game_id}")
    assert details.status_code == 200, details.text
    detail_json = details.json()
    return game_id, detail_json["team_a"]["players"], detail_json["team_b"]["players"]


def _post_delivery(client: TestClient, game_id: str, payload: dict[str, Any]) -> dict[str, Any]:
    response = client.post(f"/games/{game_id}/deliveries", json=payload)
    assert response.status_code == 200, response.text
    return response.json()


def _snapshot(client: TestClient, game_id: str) -> dict[str, Any]:
    response = client.get(f"/games/{game_id}/snapshot")
    assert response.status_code == 200, response.text
    return response.json()


def _game_state(client: TestClient, game_id: str) -> dict[str, Any]:
    response = client.get(f"/games/{game_id}")
    assert response.status_code == 200, response.text
    return response.json()


async def _force_game_status(game_id: str, status: str = "in_progress") -> None:
    game = await crud.get_game(None, game_id=game_id)
    assert game is not None, "Unable to locate game for status adjustment"
    game.status = status
    await crud.update_game(None, game_model=game)


def test_create_game_and_score_delivery(client):
    """Test creating a game and scoring a delivery."""
    # Create a new game
    game_payload = {
        "match_type": "limited",
        "overs_limit": 20,
        "team_a_name": "Team Alpha",
        "team_b_name": "Team Beta",
        "players_a": [f"Alpha{i}" for i in range(1, 12)],
        "players_b": [f"Beta{i}" for i in range(1, 12)],
        "toss_winner_team": "Team Alpha",
        "decision": "bat",
    }

    response = client.post("/games", json=game_payload)
    assert response.status_code in [200, 201]
    game = response.json()
    game_id = game.get("id") or game.get("gid") or game.get("game", {}).get("id")
    assert game_id

    # Get game details
    response = client.get(f"/games/{game_id}")
    assert response.status_code == 200
    game_details = response.json()

    # Extract player IDs
    striker_id = game_details["team_a"]["players"][0]["id"]
    non_striker_id = game_details["team_a"]["players"][1]["id"]
    bowler_id = game_details["team_b"]["players"][0]["id"]

    # Clear any setup events
    mock_sio = client.app.state.mock_sio
    mock_sio.clear_events()

    # Score a delivery
    delivery_payload = {
        "striker_id": striker_id,
        "non_striker_id": non_striker_id,
        "bowler_id": bowler_id,
        "runs_scored": 4,
        "runs_off_bat": 0,
        "is_wicket": False,
    }

    response = client.post(f"/games/{game_id}/deliveries", json=delivery_payload)
    assert response.status_code == 200
    snapshot = response.json()

    # Verify snapshot contains updated state
    assert "score" in snapshot
    assert snapshot["score"]["runs"] >= 4
    assert snapshot["score"]["wickets"] == 0

    # Verify real-time update was emitted
    state_updates = [e for e in mock_sio.emitted_events if e["event"] == "state:update"]
    assert len(state_updates) >= 1
    last_update = state_updates[-1]
    assert last_update["room"] == game_id
    assert last_update["data"]["id"] == game_id


def test_undo_delivery(client):
    """Test undoing a delivery."""
    # Create a new game
    game_payload = {
        "match_type": "limited",
        "overs_limit": 20,
        "team_a_name": "Team Alpha",
        "team_b_name": "Team Beta",
        "players_a": [f"Alpha{i}" for i in range(1, 12)],
        "players_b": [f"Beta{i}" for i in range(1, 12)],
        "toss_winner_team": "Team Alpha",
        "decision": "bat",
    }

    response = client.post("/games", json=game_payload)
    assert response.status_code in [200, 201]
    game = response.json()
    game_id = game.get("id") or game.get("gid") or game.get("game", {}).get("id")

    # Get game details
    response = client.get(f"/games/{game_id}")
    game_details = response.json()

    # Extract player IDs
    striker_id = game_details["team_a"]["players"][0]["id"]
    non_striker_id = game_details["team_a"]["players"][1]["id"]
    bowler_id = game_details["team_b"]["players"][0]["id"]

    # Score a delivery
    delivery_payload = {
        "striker_id": striker_id,
        "non_striker_id": non_striker_id,
        "bowler_id": bowler_id,
        "runs_scored": 4,
        "runs_off_bat": 0,
        "is_wicket": False,
    }

    response = client.post(f"/games/{game_id}/deliveries", json=delivery_payload)
    assert response.status_code == 200
    snapshot_after_scoring = response.json()
    runs_after_scoring = snapshot_after_scoring.get("score", {}).get("runs", 0)

    # Clear events
    mock_sio = client.app.state.mock_sio
    mock_sio.clear_events()

    # Undo the delivery
    response = client.post(f"/games/{game_id}/undo-last")
    assert response.status_code == 200
    snapshot_after_undo = response.json()

    # Verify state reverted
    runs_after_undo = snapshot_after_undo.get("score", {}).get("runs", 0)
    assert runs_after_undo < runs_after_scoring

    # Verify real-time update was emitted for undo
    state_updates = [e for e in mock_sio.emitted_events if e["event"] == "state:update"]
    assert len(state_updates) >= 1
    last_update = state_updates[-1]
    assert last_update["room"] == game_id


def test_multiple_deliveries_and_undo(client):
    """Test scoring multiple deliveries and undoing last one."""
    # Create a new game
    game_payload = {
        "match_type": "limited",
        "overs_limit": 20,
        "team_a_name": "Team Alpha",
        "team_b_name": "Team Beta",
        "players_a": [f"Alpha{i}" for i in range(1, 12)],
        "players_b": [f"Beta{i}" for i in range(1, 12)],
        "toss_winner_team": "Team Alpha",
        "decision": "bat",
    }

    response = client.post("/games", json=game_payload)
    assert response.status_code in [200, 201]
    game = response.json()
    game_id = game.get("id") or game.get("gid") or game.get("game", {}).get("id")

    # Get game details
    response = client.get(f"/games/{game_id}")
    game_details = response.json()

    # Extract player IDs
    striker_id = game_details["team_a"]["players"][0]["id"]
    non_striker_id = game_details["team_a"]["players"][1]["id"]
    bowler_id = game_details["team_b"]["players"][0]["id"]

    # Score multiple deliveries
    delivery_payloads = [
        {"runs_scored": 1, "runs_off_bat": 0},
        {"runs_scored": 2, "runs_off_bat": 0},
        {"runs_scored": 4, "runs_off_bat": 0},
    ]

    for payload in delivery_payloads:
        payload.update(
            {
                "striker_id": striker_id,
                "non_striker_id": non_striker_id,
                "bowler_id": bowler_id,
                "is_wicket": False,
            }
        )
        response = client.post(f"/games/{game_id}/deliveries", json=payload)
        assert response.status_code == 200

    # Get state after all deliveries
    response = client.get(f"/games/{game_id}/snapshot")
    assert response.status_code == 200
    snapshot_before_undo = response.json()
    runs_before_undo = snapshot_before_undo.get("score", {}).get("runs", 0)

    # Undo last delivery (4 runs)
    response = client.post(f"/games/{game_id}/undo-last")
    assert response.status_code == 200
    snapshot_after_undo = response.json()
    runs_after_undo = snapshot_after_undo.get("score", {}).get("runs", 0)

    # Verify only last delivery was undone
    assert runs_after_undo == runs_before_undo - 4


def test_undo_with_no_deliveries(client):
    """Test that undoing with no deliveries returns error."""
    # Create a new game
    game_payload = {
        "match_type": "limited",
        "overs_limit": 20,
        "team_a_name": "Team Alpha",
        "team_b_name": "Team Beta",
        "players_a": [f"Alpha{i}" for i in range(1, 12)],
        "players_b": [f"Beta{i}" for i in range(1, 12)],
        "toss_winner_team": "Team Alpha",
        "decision": "bat",
    }

    response = client.post("/games", json=game_payload)
    assert response.status_code in [200, 201]
    game = response.json()
    game_id = game.get("id") or game.get("gid") or game.get("game", {}).get("id")

    # Try to undo without any deliveries
    response = client.post(f"/games/{game_id}/undo-last")
    assert response.status_code == 409  # Conflict
    error = response.json()
    assert "Nothing to undo" in error.get("detail", "")


def test_get_deliveries_endpoint(client):
    """Test retrieving deliveries via API."""
    # Create a new game
    game_payload = {
        "match_type": "limited",
        "overs_limit": 20,
        "team_a_name": "Team Alpha",
        "team_b_name": "Team Beta",
        "players_a": [f"Alpha{i}" for i in range(1, 12)],
        "players_b": [f"Beta{i}" for i in range(1, 12)],
        "toss_winner_team": "Team Alpha",
        "decision": "bat",
    }

    response = client.post("/games", json=game_payload)
    assert response.status_code in [200, 201]
    game = response.json()
    game_id = game.get("id") or game.get("gid") or game.get("game", {}).get("id")

    # Get game details
    response = client.get(f"/games/{game_id}")
    game_details = response.json()

    # Extract player IDs
    striker_id = game_details["team_a"]["players"][0]["id"]
    non_striker_id = game_details["team_a"]["players"][1]["id"]
    bowler_id = game_details["team_b"]["players"][0]["id"]

    # Score some deliveries
    for i in range(3):
        delivery_payload = {
            "striker_id": striker_id,
            "non_striker_id": non_striker_id,
            "bowler_id": bowler_id,
            "runs_scored": i + 1,
            "runs_off_bat": 0,
            "is_wicket": False,
        }
        response = client.post(f"/games/{game_id}/deliveries", json=delivery_payload)
        assert response.status_code == 200

    # Get deliveries
    response = client.get(f"/games/{game_id}/deliveries")
    assert response.status_code == 200
    deliveries_data = response.json()

    # Verify deliveries returned
    assert "deliveries" in deliveries_data
    assert len(deliveries_data["deliveries"]) == 3
    assert deliveries_data["count"] == 3


def test_get_recent_deliveries_endpoint(client):
    """Test retrieving recent deliveries via API."""
    # Create a new game
    game_payload = {
        "match_type": "limited",
        "overs_limit": 20,
        "team_a_name": "Team Alpha",
        "team_b_name": "Team Beta",
        "players_a": [f"Alpha{i}" for i in range(1, 12)],
        "players_b": [f"Beta{i}" for i in range(1, 12)],
        "toss_winner_team": "Team Alpha",
        "decision": "bat",
    }

    response = client.post("/games", json=game_payload)
    assert response.status_code in [200, 201]
    game = response.json()
    game_id = game.get("id") or game.get("gid") or game.get("game", {}).get("id")

    # Get game details
    response = client.get(f"/games/{game_id}")
    game_details = response.json()

    # Extract player IDs
    striker_id = game_details["team_a"]["players"][0]["id"]
    non_striker_id = game_details["team_a"]["players"][1]["id"]
    bowler_id = game_details["team_b"]["players"][0]["id"]

    # Score 5 deliveries
    for i in range(5):
        delivery_payload = {
            "striker_id": striker_id,
            "non_striker_id": non_striker_id,
            "bowler_id": bowler_id,
            "runs_scored": i + 1,
            "runs_off_bat": 0,
            "is_wicket": False,
        }
        response = client.post(f"/games/{game_id}/deliveries", json=delivery_payload)
        assert response.status_code == 200

    # Get recent deliveries (limit 3)
    response = client.get(f"/games/{game_id}/recent_deliveries?limit=3")
    assert response.status_code == 200
    recent_data = response.json()

    # Verify only 3 most recent deliveries returned
    assert "deliveries" in recent_data
    assert len(recent_data["deliveries"]) == 3
    assert recent_data["count"] == 3


def test_real_time_updates_for_wicket(client):
    """Test real-time updates when a wicket is taken."""
    # Create a new game
    game_payload = {
        "match_type": "limited",
        "overs_limit": 20,
        "team_a_name": "Team Alpha",
        "team_b_name": "Team Beta",
        "players_a": [f"Alpha{i}" for i in range(1, 12)],
        "players_b": [f"Beta{i}" for i in range(1, 12)],
        "toss_winner_team": "Team Alpha",
        "decision": "bat",
    }

    response = client.post("/games", json=game_payload)
    assert response.status_code in [200, 201]
    game = response.json()
    game_id = game.get("id") or game.get("gid") or game.get("game", {}).get("id")

    # Get game details
    response = client.get(f"/games/{game_id}")
    game_details = response.json()

    # Extract player IDs
    striker_id = game_details["team_a"]["players"][0]["id"]
    non_striker_id = game_details["team_a"]["players"][1]["id"]
    bowler_id = game_details["team_b"]["players"][0]["id"]

    # Clear events
    mock_sio = client.app.state.mock_sio
    mock_sio.clear_events()

    # Score a wicket
    delivery_payload = {
        "striker_id": striker_id,
        "non_striker_id": non_striker_id,
        "bowler_id": bowler_id,
        "runs_scored": 0,
        "runs_off_bat": 0,
        "is_wicket": True,
        "dismissal_type": "bowled",
        "dismissed_player_id": striker_id,
    }

    response = client.post(f"/games/{game_id}/deliveries", json=delivery_payload)
    assert response.status_code == 200
    snapshot = response.json()

    # Verify wicket recorded
    assert snapshot.get("score", {}).get("wickets", 0) >= 1

    # Verify real-time update was emitted
    state_updates = [e for e in mock_sio.emitted_events if e["event"] == "state:update"]
    assert len(state_updates) >= 1
    last_update = state_updates[-1]
    assert last_update["room"] == game_id
    assert last_update["data"]["snapshot"].get("score", {}).get("wickets", 0) >= 1


def test_snapshot_endpoint(client):
    """Test getting game snapshot via API."""
    # Create a new game
    game_payload = {
        "match_type": "limited",
        "overs_limit": 20,
        "team_a_name": "Team Alpha",
        "team_b_name": "Team Beta",
        "players_a": [f"Alpha{i}" for i in range(1, 12)],
        "players_b": [f"Beta{i}" for i in range(1, 12)],
        "toss_winner_team": "Team Alpha",
        "decision": "bat",
    }

    response = client.post("/games", json=game_payload)
    assert response.status_code in [200, 201]
    game = response.json()
    game_id = game.get("id") or game.get("gid") or game.get("game", {}).get("id")

    # Get snapshot
    response = client.get(f"/games/{game_id}/snapshot")
    assert response.status_code == 200
    snapshot = response.json()

    # Verify snapshot has required fields
    assert "score" in snapshot
    assert "runs" in snapshot["score"]
    assert "wickets" in snapshot["score"]
    assert "overs" in snapshot["score"]
    assert "status" in snapshot
    assert "teams" in snapshot
    assert "players" in snapshot


def test_complete_over_scenario(client):
    """Test scoring a complete over (6 legal balls)."""
    # Create a new game
    game_payload = {
        "match_type": "limited",
        "overs_limit": 20,
        "team_a_name": "Team Alpha",
        "team_b_name": "Team Beta",
        "players_a": [f"Alpha{i}" for i in range(1, 12)],
        "players_b": [f"Beta{i}" for i in range(1, 12)],
        "toss_winner_team": "Team Alpha",
        "decision": "bat",
    }

    response = client.post("/games", json=game_payload)
    assert response.status_code in [200, 201]
    game = response.json()
    game_id = game.get("id") or game.get("gid") or game.get("game", {}).get("id")

    # Get game details
    response = client.get(f"/games/{game_id}")
    game_details = response.json()

    # Extract player IDs
    striker_id = game_details["team_a"]["players"][0]["id"]
    non_striker_id = game_details["team_a"]["players"][1]["id"]
    bowler_id = game_details["team_b"]["players"][0]["id"]

    # Clear events
    mock_sio = client.app.state.mock_sio
    mock_sio.clear_events()

    # Score 6 legal balls to complete an over
    for i in range(6):
        delivery_payload = {
            "striker_id": striker_id,
            "non_striker_id": non_striker_id,
            "bowler_id": bowler_id,
            "runs_scored": 1,
            "runs_off_bat": 0,
            "is_wicket": False,
        }
        response = client.post(f"/games/{game_id}/deliveries", json=delivery_payload)
        assert response.status_code == 200

    # Get final snapshot
    response = client.get(f"/games/{game_id}/snapshot")
    assert response.status_code == 200
    snapshot = response.json()

    # Verify over completed
    assert snapshot.get("score", {}).get("overs", 0) >= 1
    assert snapshot.get("score", {}).get("runs", 0) >= 6

    # Verify real-time updates were sent for each ball
    state_updates = [e for e in mock_sio.emitted_events if e["event"] == "state:update"]
    assert len(state_updates) >= 6  # At least 6 updates (one per ball)


def test_full_over_updates_snapshot(client: TestClient):
    """Ensure six legal deliveries over HTTP yield the correct snapshot totals."""
    game_id, batters, bowlers = _bootstrap_game(client)
    striker_id = batters[0]["id"]
    non_striker_id = batters[1]["id"]
    bowler_id = bowlers[0]["id"]
    runs_sequence = [0, 1, 2, 3, 4, 6]

    for runs in runs_sequence:
        _post_delivery(
            client,
            game_id,
            {
                "striker_id": striker_id,
                "non_striker_id": non_striker_id,
                "bowler_id": bowler_id,
                "runs_scored": runs,
                "runs_off_bat": 0,
                "is_wicket": False,
            },
        )

    snapshot = _snapshot(client, game_id)
    score = snapshot["score"]
    assert score["runs"] == sum(runs_sequence)
    assert score["wickets"] == 0
    overs_value = float(score["overs"])
    assert pytest.approx(overs_value, rel=1e-9) == 1.0


def test_extras_do_not_advance_legal_ball_count(client: TestClient):
    """Wides/no-balls should count toward extras without incrementing legal balls."""
    game_id, batters, bowlers = _bootstrap_game(client)
    striker_id = batters[0]["id"]
    non_striker_id = batters[1]["id"]
    bowler_id = bowlers[0]["id"]

    wide_payload = {
        "striker_id": striker_id,
        "non_striker_id": non_striker_id,
        "bowler_id": bowler_id,
        "runs_scored": 2,
        "runs_off_bat": 0,
        "extra": "wd",
        "is_wicket": False,
    }
    no_ball_payload = {
        "striker_id": striker_id,
        "non_striker_id": non_striker_id,
        "bowler_id": bowler_id,
        "runs_off_bat": 3,
        "extra": "nb",
        "is_wicket": False,
    }
    legal_payload = {
        "striker_id": striker_id,
        "non_striker_id": non_striker_id,
        "bowler_id": bowler_id,
        "runs_scored": 1,
        "runs_off_bat": 0,
        "is_wicket": False,
    }

    for payload in (wide_payload, no_ball_payload, legal_payload):
        _post_delivery(client, game_id, payload)

    snapshot = _snapshot(client, game_id)
    extras = snapshot.get("extras_totals", {})
    assert extras.get("wides") == 2
    assert extras.get("no_balls") == 1
    assert extras.get("total") == 3

    details = _game_state(client, game_id)
    assert details["balls_this_over"] == 1  # only the legal ball counted


def test_wicket_flow_matches_snapshot_and_deliveries(client: TestClient):
    """Record a wicket and ensure both snapshot and deliveries ledger align."""
    game_id, batters, bowlers = _bootstrap_game(client)
    striker_id = batters[0]["id"]
    non_striker_id = batters[1]["id"]
    bowler_id = bowlers[0]["id"]

    # Prime the over with a single to rotate strike, then take a wicket
    _post_delivery(
        client,
        game_id,
        {
            "striker_id": striker_id,
            "non_striker_id": non_striker_id,
            "bowler_id": bowler_id,
            "runs_scored": 1,
            "runs_off_bat": 0,
            "is_wicket": False,
        },
    )
    wicket_payload = {
        "striker_id": non_striker_id,  # strike rotated on the single
        "non_striker_id": striker_id,
        "bowler_id": bowler_id,
        "runs_scored": 0,
        "runs_off_bat": 0,
        "is_wicket": True,
        "dismissal_type": "bowled",
        "dismissed_player_id": non_striker_id,
    }
    _post_delivery(client, game_id, wicket_payload)

    snapshot = _snapshot(client, game_id)
    assert snapshot["score"]["wickets"] == 1
    fall = snapshot.get("fall_of_wickets") or []
    assert fall, "Expected fall-of-wickets entry"
    assert fall[-1]["dismissal_type"] == "bowled"
    assert fall[-1]["wicket"] == 1

    deliveries_resp = client.get(f"/games/{game_id}/deliveries", params={"limit": 1})
    assert deliveries_resp.status_code == 200, deliveries_resp.text
    latest = deliveries_resp.json()["deliveries"][0]
    assert latest["is_wicket"] is True
    assert latest["dismissal_type"] == "bowled"
    assert latest["dismissed_player_id"] == non_striker_id


def test_undo_last_delivery_reverts_snapshot_and_ledger(client: TestClient):
    """Undo should remove the last delivery and restore prior score."""
    game_id, batters, bowlers = _bootstrap_game(client)
    striker_id = batters[0]["id"]
    non_striker_id = batters[1]["id"]
    bowler_id = bowlers[0]["id"]

    first = {
        "striker_id": striker_id,
        "non_striker_id": non_striker_id,
        "bowler_id": bowler_id,
        "runs_scored": 4,
        "runs_off_bat": 0,
        "is_wicket": False,
    }
    second = {
        "striker_id": striker_id,
        "non_striker_id": non_striker_id,
        "bowler_id": bowler_id,
        "runs_scored": 1,
        "runs_off_bat": 0,
        "is_wicket": False,
    }

    _post_delivery(client, game_id, first)
    _post_delivery(client, game_id, second)

    undo_response = client.post(f"/games/{game_id}/undo-last")
    assert undo_response.status_code == 200, undo_response.text
    undo_snapshot = undo_response.json()
    assert undo_snapshot["score"]["runs"] == 4
    assert undo_snapshot["score"]["wickets"] == 0

    deliveries = client.get(f"/games/{game_id}/deliveries")
    assert deliveries.status_code == 200
    assert deliveries.json()["count"] == 1

    state = _game_state(client, game_id)
    assert state["total_runs"] == 4
    assert state["balls_this_over"] == 1


async def test_mid_over_bowler_change_reflects_in_snapshot(client: TestClient):
    """Changing the bowler mid-over should update snapshot + runtime state."""
    game_id, batters, bowlers = _bootstrap_game(client)
    striker_id = batters[0]["id"]
    non_striker_id = batters[1]["id"]
    opening_bowler = bowlers[0]["id"]
    new_bowler = bowlers[1]["id"]

    # First delivery to start the over
    _post_delivery(
        client,
        game_id,
        {
            "striker_id": striker_id,
            "non_striker_id": non_striker_id,
            "bowler_id": opening_bowler,
            "runs_scored": 0,
            "runs_off_bat": 0,
            "is_wicket": False,
        },
    )

    # In-memory repo stores GameStatus enums; normalize to literal for route validation
    await _force_game_status(game_id, "in_progress")

    change_resp = client.post(
        f"/games/{game_id}/overs/change_bowler", json={"new_bowler_id": new_bowler}
    )
    assert change_resp.status_code == 200, change_resp.text
    change_snapshot = change_resp.json()
    assert change_snapshot["current_bowler_id"] == new_bowler
    assert change_snapshot["mid_over_change_used"] is True

    # Next ball should reflect the new bowler both in ledger and snapshot
    _post_delivery(
        client,
        game_id,
        {
            "striker_id": striker_id,
            "non_striker_id": non_striker_id,
            "bowler_id": new_bowler,
            "runs_scored": 2,
            "runs_off_bat": 0,
            "is_wicket": False,
        },
    )

    snapshot = _snapshot(client, game_id)
    assert snapshot.get("current_bowler", {}).get("id") == new_bowler
    state = _game_state(client, game_id)
    if "current_bowler_id" in state:
        assert state["current_bowler_id"] == new_bowler
    else:
        # Some lightweight responses omit runtime fields; snapshot assertion above suffices.
        assert snapshot.get("current_bowler", {}).get("id") == new_bowler
