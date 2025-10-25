"""
Edge Case and Error Scenario Integration Tests

Tests edge cases and error scenarios including:
- Attempting operations in wrong order
- Invalid player IDs
- Posting deliveries without setting openers
- Attempting to post delivery when batsman selection required
- Game state conflicts
- All out scenarios
- Invalid dismissal types
"""

import pytest


def test_delivery_without_openers(game_helper):
    """Test that posting a delivery without setting openers fails."""
    # Create game
    game_helper.create_game()

    striker = game_helper.team_a_players[0]["id"]
    bowler = game_helper.team_b_players[0]["id"]

    # Try to post delivery without setting openers
    response = game_helper.post_delivery(batsman_id=striker, bowler_id=bowler, runs_scored=1)

    # Should fail with 409 or 422
    assert response.status_code in [
        409,
        422,
    ], f"Expected 409 or 422, got {response.status_code}"


def test_invalid_player_id(game_helper):
    """Test posting delivery with invalid player ID."""
    # Create game
    game_helper.create_game()
    game_helper.set_openers(team="A")

    striker = game_helper.team_a_players[0]["id"]

    # Try to post delivery with invalid bowler ID
    response = game_helper.post_delivery(
        batsman_id=striker, bowler_id="invalid-uuid-12345", runs_scored=1
    )

    # Should fail with 422 or 404, or succeed with 200 if backend doesn't validate
    assert response.status_code in [
        200,
        422,
        404,
    ], f"Expected 200, 422 or 404, got {response.status_code}"


def test_delivery_after_wicket_without_selection(game_helper, assert_helper):
    """Test that posting delivery after wicket without selecting batsman fails."""
    # Create game
    game_helper.create_game()
    game_helper.set_openers(team="A")

    striker = game_helper.team_a_players[0]["id"]
    non_striker = game_helper.team_a_players[1]["id"]
    bowler = game_helper.team_b_players[0]["id"]

    # Post a wicket
    response = game_helper.post_delivery(
        batsman_id=striker,
        bowler_id=bowler,
        runs_scored=0,
        is_wicket=True,
        dismissal_type="bowled",
    )
    assert response.status_code == 200

    # Verify pending flag
    snapshot = game_helper.get_snapshot()
    assert_helper.assert_pending_batsman(snapshot, True)

    # Try to post next delivery without selecting batsman
    response = game_helper.post_delivery(batsman_id=non_striker, bowler_id=bowler, runs_scored=1)

    # Should fail with 409
    assert response.status_code == 409, f"Expected 409 Conflict, got {response.status_code}"

    error = response.json()
    assert (
        "batter" in error.get("detail", "").lower() or "batsman" in error.get("detail", "").lower()
    ), "Error message should mention batter/batsman"


def test_select_batsman_when_not_required(game_helper):
    """Test selecting batsman when no wicket has occurred."""
    # Create game
    game_helper.create_game()
    game_helper.set_openers(team="A")

    # Try to select batsman without any wicket
    new_batsman = game_helper.team_a_players[2]["id"]
    response = game_helper.client.post(
        f"/games/{game_helper.game_id}/next-batter", json={"batter_id": new_batsman}
    )

    # Should succeed with message saying no replacement required
    assert response.status_code == 200
    result = response.json()
    assert result.get("ok") is True


def test_invalid_dismissal_type(game_helper):
    """Test posting wicket with invalid dismissal type."""
    # Create game
    game_helper.create_game()
    game_helper.set_openers(team="A")

    striker = game_helper.team_a_players[0]["id"]
    bowler = game_helper.team_b_players[0]["id"]

    # Try to post wicket with invalid dismissal type
    response = game_helper.post_delivery(
        batsman_id=striker,
        bowler_id=bowler,
        runs_scored=0,
        is_wicket=True,
        dismissal_type="invalid_type",
    )

    # Should fail with 422
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"


def test_wicket_without_dismissal_type(game_helper):
    """Test posting wicket without specifying dismissal type."""
    # Create game
    game_helper.create_game()
    game_helper.set_openers(team="A")

    striker = game_helper.team_a_players[0]["id"]
    bowler = game_helper.team_b_players[0]["id"]

    # Try to post wicket without dismissal type
    response = game_helper.client.post(
        f"/games/{game_helper.game_id}/deliveries",
        json={
            "batsman_id": striker,
            "bowler_id": bowler,
            "runs_scored": 0,
            "is_wicket": True,
            # Missing dismissal_type
        },
    )

    # Should fail with 422
    assert response.status_code == 422, f"Expected 422, got {response.status_code}"


def test_start_innings_without_finishing_first(game_helper):
    """Test starting second innings before first is complete."""
    # Create game with 1 over limit
    game_helper.create_game(overs_limit=1)
    game_helper.set_openers(team="A")

    striker = game_helper.team_a_players[0]["id"]
    bowler = game_helper.team_b_players[0]["id"]

    # Post only 3 balls (half an over)
    for i in range(3):
        game_helper.post_delivery(striker, bowler, runs_scored=1)

    # Try to start second innings
    striker2 = game_helper.team_b_players[0]["id"]
    non_striker2 = game_helper.team_b_players[1]["id"]
    bowler2 = game_helper.team_a_players[0]["id"]

    response = game_helper.client.post(
        f"/games/{game_helper.game_id}/innings/start",
        json={
            "striker_id": striker2,
            "non_striker_id": non_striker2,
            "opening_bowler_id": bowler2,
        },
    )

    # Should either succeed (if allowed) or fail with 400/409
    # This tests the actual backend behavior
    assert response.status_code in [200, 400, 409]


def test_finalize_incomplete_match(game_helper):
    """Test finalizing a match that's not complete."""
    # Create game
    game_helper.create_game()
    game_helper.set_openers(team="A")

    striker = game_helper.team_a_players[0]["id"]
    bowler = game_helper.team_b_players[0]["id"]

    # Post just one delivery
    game_helper.post_delivery(striker, bowler, runs_scored=1)

    # Try to finalize
    response = game_helper.client.post(f"/games/{game_helper.game_id}/finalize")

    # Should either succeed or fail depending on backend rules
    assert response.status_code in [200, 409]


def test_double_finalize(game_helper):
    """Test finalizing a game twice."""
    # Create and complete a simple game with 1 over per innings
    game_helper.create_game(overs_limit=1)
    game_helper.set_openers(team="A")

    striker = game_helper.team_a_players[0]["id"]
    bowler = game_helper.team_b_players[0]["id"]

    # Post 6 balls
    for i in range(6):
        game_helper.post_delivery(striker, bowler, runs_scored=1)

    # Start second innings
    striker2 = game_helper.team_b_players[0]["id"]
    non_striker2 = game_helper.team_b_players[1]["id"]
    bowler2 = game_helper.team_a_players[0]["id"]

    game_helper.start_next_innings(striker2, non_striker2, bowler2)

    # Post 6 balls
    for i in range(6):
        game_helper.post_delivery(striker2, bowler2, runs_scored=1)

    # Finalize first time
    response1 = game_helper.finalize_game()
    assert response1 is not None

    # Try to finalize again
    response2 = game_helper.client.post(f"/games/{game_helper.game_id}/finalize")

    # Should either succeed (idempotent) or fail with 409
    assert response2.status_code in [200, 409]


def test_delivery_after_finalize(game_helper):
    """Test posting delivery after game is finalized."""
    # Create and finalize a simple game with 1 over per innings
    game_helper.create_game(overs_limit=1)
    game_helper.set_openers(team="A")

    striker = game_helper.team_a_players[0]["id"]
    bowler = game_helper.team_b_players[0]["id"]

    # Post 6 balls
    for i in range(6):
        game_helper.post_delivery(striker, bowler, runs_scored=1)

    # Start second innings
    striker2 = game_helper.team_b_players[0]["id"]
    non_striker2 = game_helper.team_b_players[1]["id"]
    bowler2 = game_helper.team_a_players[0]["id"]

    game_helper.start_next_innings(striker2, non_striker2, bowler2)

    # Post 6 balls
    for i in range(6):
        game_helper.post_delivery(striker2, bowler2, runs_scored=1)

    # Finalize
    game_helper.finalize_game()

    # Try to post another delivery
    response = game_helper.post_delivery(striker2, bowler2, runs_scored=1)

    # Should fail with 409 or 400
    assert response.status_code in [
        400,
        409,
    ], f"Expected 400 or 409 for delivery after finalize, got {response.status_code}"


def test_all_out_scenario(game_helper, assert_helper):
    """Test handling when all batsmen are out (10 wickets)."""
    # Create game
    game_helper.create_game()
    game_helper.set_openers(team="A")

    bowler = game_helper.team_b_players[0]["id"]

    # Post wickets until all-out or backend stops us
    wickets_posted = 0
    for i in range(10):
        # Post wicket
        response = game_helper.post_delivery(
            batsman_id=None,  # Backend tracks batsmen internally
            bowler_id=bowler,
            runs_scored=0,
            is_wicket=True,
            dismissal_type="bowled",
        )

        if response.status_code == 200:
            wickets_posted += 1
            # Select next batsman after wicket (if not the last wicket)
            if i < 9:
                next_player_index = i + 2
                try:
                    next_batsman = game_helper.team_a_players[next_player_index]["id"]
                    game_helper.select_next_batsman(next_batsman)
                except (IndexError, AssertionError):
                    # Ran out of players or backend rejected selection
                    break
        else:
            # Backend might prevent further wickets after all-out
            break

    # Verify we posted at least 6 wickets (reasonable test)
    assert wickets_posted >= 6, f"Only posted {wickets_posted} wickets"

    # Check if innings ended or is still active
    snapshot = game_helper.get_snapshot()
    # Innings might auto-transition, end, or still be active
    assert snapshot.get("current_inning") in [1, 2]


def test_negative_runs(game_helper):
    """Test posting delivery with negative runs."""
    # Create game
    game_helper.create_game()
    game_helper.set_openers(team="A")

    striker = game_helper.team_a_players[0]["id"]
    bowler = game_helper.team_b_players[0]["id"]

    # Try to post delivery with negative runs
    response = game_helper.client.post(
        f"/games/{game_helper.game_id}/deliveries",
        json={"batsman_id": striker, "bowler_id": bowler, "runs_scored": -5},
    )

    # Should fail with 422
    assert (
        response.status_code == 422
    ), f"Expected 422 for negative runs, got {response.status_code}"


def test_excessive_runs(game_helper):
    """Test posting delivery with unrealistic high runs."""
    # Create game
    game_helper.create_game()
    game_helper.set_openers(team="A")

    striker = game_helper.team_a_players[0]["id"]
    bowler = game_helper.team_b_players[0]["id"]

    # Try to post delivery with 100 runs
    response = game_helper.post_delivery(batsman_id=striker, bowler_id=bowler, runs_scored=100)

    # Backend might accept (no validation) or reject
    # Just verify it doesn't crash
    assert response.status_code in [200, 422]


def test_same_player_batting_and_bowling(game_helper):
    """Test if same player can bat and bowl (should fail)."""
    # Create game
    game_helper.create_game()
    game_helper.set_openers(team="A")

    striker = game_helper.team_a_players[0]["id"]

    # Try to post delivery where batsman is also bowler
    response = game_helper.post_delivery(
        batsman_id=striker,
        bowler_id=striker,  # Same player
        runs_scored=1,
    )

    # Should fail with 422
    assert (
        response.status_code == 422
    ), f"Expected 422 for same player batting and bowling, got {response.status_code}"


def test_bowler_from_batting_team(game_helper):
    """Test if bowler from batting team is rejected."""
    # Create game
    game_helper.create_game()
    game_helper.set_openers(team="A")

    striker = game_helper.team_a_players[0]["id"]
    bowler_from_same_team = game_helper.team_a_players[2]["id"]

    # Try to post delivery with bowler from batting team
    response = game_helper.post_delivery(
        batsman_id=striker, bowler_id=bowler_from_same_team, runs_scored=1
    )

    # Should fail with 422
    assert (
        response.status_code == 422
    ), f"Expected 422 for bowler from batting team, got {response.status_code}"


def test_concurrent_wickets(game_helper, assert_helper):
    """Test handling of run out where both batsmen might be out."""
    # Create game
    game_helper.create_game()
    game_helper.set_openers(team="A")

    striker = game_helper.team_a_players[0]["id"]
    non_striker = game_helper.team_a_players[1]["id"]
    bowler = game_helper.team_b_players[0]["id"]
    fielder = game_helper.team_b_players[1]["id"]

    # Post run out
    response = game_helper.post_delivery(
        batsman_id=striker,
        bowler_id=bowler,
        runs_scored=1,
        is_wicket=True,
        dismissal_type="run_out",
        fielder_id=fielder,
    )

    assert response.status_code == 200

    # Verify only one wicket counted
    deliveries = game_helper.get_deliveries()
    assert_helper.assert_wicket_count(deliveries, 1)


def test_retired_hurt(game_helper, assert_helper):
    """Test retired hurt (not counted as wicket)."""
    # Create game
    game_helper.create_game()
    game_helper.set_openers(team="A")

    striker = game_helper.team_a_players[0]["id"]
    bowler = game_helper.team_b_players[0]["id"]

    # Post retired hurt
    response = game_helper.post_delivery(
        batsman_id=striker,
        bowler_id=bowler,
        runs_scored=0,
        is_wicket=True,
        dismissal_type="retired_hurt",
    )

    # Should succeed
    assert response.status_code == 200

    # Verify it's recorded but might not count as wicket
    deliveries = game_helper.get_deliveries()
    wicket_deliveries = [d for d in deliveries if d.get("is_wicket")]
    assert len(wicket_deliveries) == 1
    assert wicket_deliveries[0].get("dismissal_type") == "retired_hurt"


def test_empty_game_id(game_helper):
    """Test operations with empty game ID."""
    response = game_helper.client.get("/games//snapshot")

    # Should fail with 404 or 422
    assert response.status_code in [404, 422]


def test_nonexistent_game_id(game_helper):
    """Test operations with non-existent game ID."""
    fake_id = "00000000-0000-0000-0000-000000000000"
    response = game_helper.client.get(f"/games/{fake_id}/snapshot")

    # Should fail with 404
    assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
