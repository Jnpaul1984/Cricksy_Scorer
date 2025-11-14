"""
Integration tests for core scoring system.

Tests complete workflows:
- Creating a game and scoring deliveries via API
- Real-time WebSocket updates during scoring
- Undo functionality via API
- Data persistence and retrieval through full stack
"""

import os

import pytest
from starlette.testclient import TestClient

# Set in-memory mode for tests
os.environ["CRICKSY_IN_MEMORY_DB"] = "1"

from backend.app import create_app
from backend.services import live_bus


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
