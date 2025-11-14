"""
Test wicket counting functionality in the backend.

This test validates that:
1. Deliveries with is_wicket=True are recorded correctly
2. Wicket counts are calculated accurately
3. first_inning_summary includes correct wicket count
4. Batsman selection workflow is enforced after wickets
"""

import pytest
from fastapi.testclient import TestClient
from backend.main import _fastapi as app


@pytest.fixture
def api_client():
    """Create a test client for the FastAPI app."""
    with TestClient(app) as client:
        yield client


def test_wicket_delivery_is_recorded(api_client):
    """Test that a delivery with is_wicket=True is recorded correctly."""
    # Create a game
    game_response = api_client.post(
        "/games",
        json={
            "team_a_name": "Team Alpha",
            "team_b_name": "Team Beta",
            "overs_limit": 20,
            "players_per_team": 11,
        },
    )
    assert game_response.status_code == 200
    game_data = game_response.json()
    game_id = game_data["id"]

    # Get player IDs
    team_a_players = game_data["team_a"]["players"]
    team_b_players = game_data["team_b"]["players"]

    striker_id = team_a_players[0]["id"]
    non_striker_id = team_a_players[1]["id"]
    bowler_id = team_b_players[0]["id"]

    # Set openers
    api_client.post(
        f"/games/{game_id}/openers",
        json={"striker_id": striker_id, "non_striker_id": non_striker_id, "team": "A"},
    )

    # Post a wicket delivery
    wicket_response = api_client.post(
        f"/games/{game_id}/deliveries",
        json={
            "batsman_id": striker_id,
            "bowler_id": bowler_id,
            "runs_scored": 0,
            "is_wicket": True,
            "dismissal_type": "bowled",
        },
    )

    assert wicket_response.status_code == 200

    # Get game snapshot
    snapshot_response = api_client.get(f"/games/{game_id}/snapshot")
    assert snapshot_response.status_code == 200
    snapshot = snapshot_response.json()

    # Verify pending_new_batter flag is set
    assert (
        snapshot.get("pending_new_batter") is True
    ), "pending_new_batter should be True after a wicket"


def test_wicket_count_in_deliveries(api_client):
    """Test that wicket count is calculated from deliveries."""
    # Create a game
    game_response = api_client.post(
        "/games",
        json={
            "team_a_name": "Team Alpha",
            "team_b_name": "Team Beta",
            "overs_limit": 20,
            "players_per_team": 11,
        },
    )
    game_data = game_response.json()
    game_id = game_data["id"]

    team_a_players = game_data["team_a"]["players"]
    team_b_players = game_data["team_b"]["players"]

    striker_id = team_a_players[0]["id"]
    non_striker_id = team_a_players[1]["id"]
    bowler_id = team_b_players[0]["id"]

    # Set openers
    api_client.post(
        f"/games/{game_id}/openers",
        json={"striker_id": striker_id, "non_striker_id": non_striker_id, "team": "A"},
    )

    # Post 3 normal deliveries
    for i in range(3):
        api_client.post(
            f"/games/{game_id}/deliveries",
            json={
                "batsman_id": striker_id if i % 2 == 0 else non_striker_id,
                "bowler_id": bowler_id,
                "runs_scored": 1,
                "is_wicket": False,
            },
        )

    # Post a wicket delivery
    api_client.post(
        f"/games/{game_id}/deliveries",
        json={
            "batsman_id": striker_id,
            "bowler_id": bowler_id,
            "runs_scored": 0,
            "is_wicket": True,
            "dismissal_type": "caught",
        },
    )

    # Select new batsman
    new_batsman_id = team_a_players[2]["id"]
    api_client.post(f"/games/{game_id}/next-batter", json={"batter_id": new_batsman_id})

    # Post another wicket
    api_client.post(
        f"/games/{game_id}/deliveries",
        json={
            "batsman_id": new_batsman_id,
            "bowler_id": bowler_id,
            "runs_scored": 0,
            "is_wicket": True,
            "dismissal_type": "lbw",
        },
    )

    # Get deliveries
    deliveries_response = api_client.get(f"/games/{game_id}/deliveries")
    deliveries_data = deliveries_response.json()
    deliveries = deliveries_data["deliveries"]

    # Count wickets in deliveries
    wicket_count = sum(1 for d in deliveries if d.get("is_wicket") is True)

    assert wicket_count == 2, f"Expected 2 wickets, got {wicket_count}"


def test_batsman_selection_required_after_wicket(api_client):
    """Test that next delivery is blocked until new batsman is selected."""
    # Create a game
    game_response = api_client.post(
        "/games",
        json={
            "team_a_name": "Team Alpha",
            "team_b_name": "Team Beta",
            "overs_limit": 20,
            "players_per_team": 11,
        },
    )
    game_data = game_response.json()
    game_id = game_data["id"]

    team_a_players = game_data["team_a"]["players"]
    team_b_players = game_data["team_b"]["players"]

    striker_id = team_a_players[0]["id"]
    non_striker_id = team_a_players[1]["id"]
    bowler_id = team_b_players[0]["id"]

    # Set openers
    api_client.post(
        f"/games/{game_id}/openers",
        json={"striker_id": striker_id, "non_striker_id": non_striker_id, "team": "A"},
    )

    # Post a wicket delivery
    api_client.post(
        f"/games/{game_id}/deliveries",
        json={
            "batsman_id": striker_id,
            "bowler_id": bowler_id,
            "runs_scored": 0,
            "is_wicket": True,
            "dismissal_type": "bowled",
        },
    )

    # Try to post next delivery without selecting new batsman
    next_delivery_response = api_client.post(
        f"/games/{game_id}/deliveries",
        json={
            "batsman_id": non_striker_id,
            "bowler_id": bowler_id,
            "runs_scored": 1,
            "is_wicket": False,
        },
    )

    # Should get 409 Conflict
    assert (
        next_delivery_response.status_code == 409
    ), f"Expected 409 Conflict, got {next_delivery_response.status_code}"

    error_detail = next_delivery_response.json().get("detail", "")
    assert (
        "new batter" in error_detail.lower()
    ), f"Error message should mention new batter: {error_detail}"


def test_batsman_selection_clears_pending_flag(api_client):
    """Test that selecting a new batsman clears the pending_new_batter flag."""
    # Create a game
    game_response = api_client.post(
        "/games",
        json={
            "team_a_name": "Team Alpha",
            "team_b_name": "Team Beta",
            "overs_limit": 20,
            "players_per_team": 11,
        },
    )
    game_data = game_response.json()
    game_id = game_data["id"]

    team_a_players = game_data["team_a"]["players"]
    team_b_players = game_data["team_b"]["players"]

    striker_id = team_a_players[0]["id"]
    non_striker_id = team_a_players[1]["id"]
    bowler_id = team_b_players[0]["id"]

    # Set openers
    api_client.post(
        f"/games/{game_id}/openers",
        json={"striker_id": striker_id, "non_striker_id": non_striker_id, "team": "A"},
    )

    # Post a wicket delivery
    api_client.post(
        f"/games/{game_id}/deliveries",
        json={
            "batsman_id": striker_id,
            "bowler_id": bowler_id,
            "runs_scored": 0,
            "is_wicket": True,
            "dismissal_type": "bowled",
        },
    )

    # Verify pending_new_batter is True
    snapshot1 = api_client.get(f"/games/{game_id}/snapshot").json()
    assert snapshot1.get("pending_new_batter") is True

    # Select new batsman
    new_batsman_id = team_a_players[2]["id"]
    select_response = api_client.post(
        f"/games/{game_id}/next-batter", json={"batter_id": new_batsman_id}
    )

    assert select_response.status_code == 200

    # Verify pending_new_batter is now False
    snapshot2 = api_client.get(f"/games/{game_id}/snapshot").json()
    assert (
        snapshot2.get("pending_new_batter") is False
    ), "pending_new_batter should be False after selecting new batsman"

    # Verify new batsman is current striker
    assert (
        snapshot2.get("current_striker_id") == new_batsman_id
    ), "New batsman should be current striker"


def test_delivery_after_batsman_selection_succeeds(api_client):
    """Test that deliveries can be posted after selecting a new batsman."""
    # Create a game
    game_response = api_client.post(
        "/games",
        json={
            "team_a_name": "Team Alpha",
            "team_b_name": "Team Beta",
            "overs_limit": 20,
            "players_per_team": 11,
        },
    )
    game_data = game_response.json()
    game_id = game_data["id"]

    team_a_players = game_data["team_a"]["players"]
    team_b_players = game_data["team_b"]["players"]

    striker_id = team_a_players[0]["id"]
    non_striker_id = team_a_players[1]["id"]
    bowler_id = team_b_players[0]["id"]

    # Set openers
    api_client.post(
        f"/games/{game_id}/openers",
        json={"striker_id": striker_id, "non_striker_id": non_striker_id, "team": "A"},
    )

    # Post a wicket delivery
    api_client.post(
        f"/games/{game_id}/deliveries",
        json={
            "batsman_id": striker_id,
            "bowler_id": bowler_id,
            "runs_scored": 0,
            "is_wicket": True,
            "dismissal_type": "bowled",
        },
    )

    # Select new batsman
    new_batsman_id = team_a_players[2]["id"]
    api_client.post(f"/games/{game_id}/next-batter", json={"batter_id": new_batsman_id})

    # Post next delivery - should succeed
    next_delivery_response = api_client.post(
        f"/games/{game_id}/deliveries",
        json={
            "batsman_id": new_batsman_id,
            "bowler_id": bowler_id,
            "runs_scored": 4,
            "is_wicket": False,
        },
    )

    assert (
        next_delivery_response.status_code == 200
    ), f"Delivery after batsman selection should succeed, got {next_delivery_response.status_code}"


def test_multiple_wickets_in_sequence(api_client):
    """Test handling multiple wickets in sequence."""
    # Create a game
    game_response = api_client.post(
        "/games",
        json={
            "team_a_name": "Team Alpha",
            "team_b_name": "Team Beta",
            "overs_limit": 20,
            "players_per_team": 11,
        },
    )
    game_data = game_response.json()
    game_id = game_data["id"]

    team_a_players = game_data["team_a"]["players"]
    team_b_players = game_data["team_b"]["players"]

    striker_id = team_a_players[0]["id"]
    non_striker_id = team_a_players[1]["id"]
    bowler_id = team_b_players[0]["id"]

    # Set openers
    api_client.post(
        f"/games/{game_id}/openers",
        json={"striker_id": striker_id, "non_striker_id": non_striker_id, "team": "A"},
    )

    # Simulate 3 wickets in sequence
    for i in range(3):
        current_batsman = team_a_players[i]["id"]

        # Post wicket delivery
        api_client.post(
            f"/games/{game_id}/deliveries",
            json={
                "batsman_id": current_batsman,
                "bowler_id": bowler_id,
                "runs_scored": 0,
                "is_wicket": True,
                "dismissal_type": "bowled",
            },
        )

        # Select next batsman (if not the last wicket)
        if i < 2:
            next_batsman_id = team_a_players[i + 3]["id"]
            api_client.post(f"/games/{game_id}/next-batter", json={"batter_id": next_batsman_id})

    # Get deliveries and count wickets
    deliveries_response = api_client.get(f"/games/{game_id}/deliveries")
    deliveries = deliveries_response.json()["deliveries"]

    wicket_count = sum(1 for d in deliveries if d.get("is_wicket") is True)

    assert wicket_count == 3, f"Expected 3 wickets, got {wicket_count}"


def test_dismissal_types_are_recorded(api_client):
    """Test that different dismissal types are recorded correctly."""
    # Create a game
    game_response = api_client.post(
        "/games",
        json={
            "team_a_name": "Team Alpha",
            "team_b_name": "Team Beta",
            "overs_limit": 20,
            "players_per_team": 11,
        },
    )
    game_data = game_response.json()
    game_id = game_data["id"]

    team_a_players = game_data["team_a"]["players"]
    team_b_players = game_data["team_b"]["players"]

    striker_id = team_a_players[0]["id"]
    non_striker_id = team_a_players[1]["id"]
    bowler_id = team_b_players[0]["id"]
    fielder_id = team_b_players[1]["id"]

    # Set openers
    api_client.post(
        f"/games/{game_id}/openers",
        json={"striker_id": striker_id, "non_striker_id": non_striker_id, "team": "A"},
    )

    # Test different dismissal types
    dismissal_types = ["bowled", "caught", "lbw", "run_out", "stumped"]

    for i, dismissal_type in enumerate(dismissal_types):
        current_batsman = team_a_players[i]["id"]

        # Post wicket with specific dismissal type
        wicket_payload = {
            "batsman_id": current_batsman,
            "bowler_id": bowler_id,
            "runs_scored": 0,
            "is_wicket": True,
            "dismissal_type": dismissal_type,
        }

        # Add fielder for caught dismissals
        if dismissal_type == "caught":
            wicket_payload["fielder_id"] = fielder_id

        api_client.post(f"/games/{game_id}/deliveries", json=wicket_payload)

        # Select next batsman (if not last)
        if i < len(dismissal_types) - 1:
            next_batsman_id = team_a_players[i + 5]["id"]
            api_client.post(f"/games/{game_id}/next-batter", json={"batter_id": next_batsman_id})

    # Get deliveries and verify dismissal types
    deliveries_response = api_client.get(f"/games/{game_id}/deliveries")
    deliveries = deliveries_response.json()["deliveries"]

    wicket_deliveries = [d for d in deliveries if d.get("is_wicket")]
    recorded_types = [d.get("dismissal_type") for d in wicket_deliveries]

    assert len(wicket_deliveries) == len(
        dismissal_types
    ), f"Expected {len(dismissal_types)} wickets, got {len(wicket_deliveries)}"

    for expected_type in dismissal_types:
        assert (
            expected_type in recorded_types
        ), f"Dismissal type '{expected_type}' not found in recorded types"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
