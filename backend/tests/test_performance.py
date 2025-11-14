"""
Performance benchmarks for Cricksy Scorer backend.

These tests measure the performance of key operations to identify bottlenecks
and ensure the application can handle realistic workloads.
"""

import time
import pytest
from fastapi.testclient import TestClient
from backend.main import _fastapi as app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_game(client):
    """Create a sample game for performance testing."""
    response = client.post(
        "/games",
        json={
            "team_a_name": "Team A",
            "team_b_name": "Team B",
            "players_a": [f"PlayerA{i}" for i in range(1, 12)],
            "players_b": [f"PlayerB{i}" for i in range(1, 12)],
            "overs_limit": 20,
            "toss_winner_team": "A",
            "decision": "bat",
        },
    )
    assert response.status_code == 200
    game_data = response.json()

    # Set openers
    team_a_players = game_data["team_a"]["players"]
    team_b_players = game_data["team_b"]["players"]

    response = client.post(
        f"/games/{game_data['id']}/set-openers",
        json={
            "striker_id": team_a_players[0]["id"],
            "non_striker_id": team_a_players[1]["id"],
            "opening_bowler_id": team_b_players[0]["id"],
        },
    )
    assert response.status_code == 200

    return {
        "client": client,
        "game_id": game_data["id"],
        "team_a_players": team_a_players,
        "team_b_players": team_b_players,
    }


class TestGameCreationPerformance:
    """Performance tests for game creation."""

    def test_create_game_performance(self, client):
        """
        Benchmark: Creating a new game.
        Target: < 100ms per game creation.
        """
        iterations = 10
        times = []

        for i in range(iterations):
            start = time.time()
            response = client.post(
                "/games",
                json={
                    "team_a_name": f"Team A {i}",
                    "team_b_name": f"Team B {i}",
                    "players_a": [f"PlayerA{j}" for j in range(1, 12)],
                    "players_b": [f"PlayerB{j}" for j in range(1, 12)],
                    "overs_limit": 20,
                    "toss_winner_team": "A",
                    "decision": "bat",
                },
            )
            end = time.time()

            assert response.status_code == 200
            times.append((end - start) * 1000)  # Convert to ms

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print("\n=== Game Creation Performance ===")
        print(f"Iterations: {iterations}")
        print(f"Average: {avg_time:.2f}ms")
        print(f"Min: {min_time:.2f}ms")
        print(f"Max: {max_time:.2f}ms")

        # Assert performance target
        assert (
            avg_time < 100
        ), f"Game creation too slow: {avg_time:.2f}ms (target: <100ms)"


class TestDeliveryPerformance:
    """Performance tests for delivery posting."""

    def test_single_delivery_performance(self, client):
        """
        Benchmark: Posting a single delivery.
        Target: < 50ms per delivery.
        """
        # Create game and set openers
        response = client.post(
            "/games",
            json={
                "team_a_name": "Team A",
                "team_b_name": "Team B",
                "players_a": [f"PlayerA{i}" for i in range(1, 12)],
                "players_b": [f"PlayerB{i}" for i in range(1, 12)],
                "overs_limit": 20,
                "toss_winner_team": "A",
                "decision": "bat",
            },
        )
        game_data = response.json()
        game_id = game_data["id"]
        team_a_players = game_data["team_a"]["players"]
        team_b_players = game_data["team_b"]["players"]

        response = client.post(
            f"/games/{game_id}/openers",
            json={
                "striker_id": team_a_players[0]["id"],
                "non_striker_id": team_a_players[1]["id"],
                "opening_bowler_id": team_b_players[0]["id"],
            },
        )
        assert (
            response.status_code == 200
        ), f"Set openers failed: {response.status_code} - {response.json()}"

        bowler1_id = team_b_players[0]["id"]
        bowler2_id = team_b_players[1]["id"]

        iterations = 20
        times = []

        for i in range(iterations):
            bowler_id = bowler1_id if (i // 6) % 2 == 0 else bowler2_id
            start = time.time()
            response = client.post(
                f"/games/{game_id}/deliveries",
                json={
                    "bowler_id": bowler_id,
                    "runs_scored": 1,
                },
            )
            end = time.time()

            if response.status_code != 200:
                print(f"\nDelivery {i}: {response.status_code} - {response.json()}")
            assert response.status_code == 200
            times.append((end - start) * 1000)

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print("\n=== Single Delivery Performance ===")
        print(f"Iterations: {iterations}")
        print(f"Average: {avg_time:.2f}ms")
        print(f"Min: {min_time:.2f}ms")
        print(f"Max: {max_time:.2f}ms")

        assert (
            avg_time < 50
        ), f"Delivery posting too slow: {avg_time:.2f}ms (target: <50ms)"

    def test_full_over_performance(self, client):
        """
        Benchmark: Posting a full over (6 deliveries).
        Target: < 300ms per over.
        """
        # Create game and set openers
        response = client.post(
            "/games",
            json={
                "team_a_name": "Team A",
                "team_b_name": "Team B",
                "players_a": [f"PlayerA{i}" for i in range(1, 12)],
                "players_b": [f"PlayerB{i}" for i in range(1, 12)],
                "overs_limit": 20,
                "toss_winner_team": "A",
                "decision": "bat",
            },
        )
        game_data = response.json()
        game_id = game_data["id"]
        team_a_players = game_data["team_a"]["players"]
        team_b_players = game_data["team_b"]["players"]

        response = client.post(
            f"/games/{game_id}/openers",
            json={
                "striker_id": team_a_players[0]["id"],
                "non_striker_id": team_a_players[1]["id"],
                "opening_bowler_id": team_b_players[0]["id"],
            },
        )
        assert (
            response.status_code == 200
        ), f"Set openers failed: {response.status_code} - {response.json()}"

        bowler1_id = team_b_players[0]["id"]
        bowler2_id = team_b_players[1]["id"]

        start = time.time()
        for i in range(12):  # 2 overs to test bowler rotation
            bowler_id = bowler1_id if (i // 6) % 2 == 0 else bowler2_id
            response = client.post(
                f"/games/{game_id}/deliveries",
                json={
                    "bowler_id": bowler_id,
                    "runs_scored": 1,
                },
            )
            assert response.status_code == 200
        end = time.time()

        total_time = (end - start) * 1000
        avg_per_delivery = total_time / 12

        print("\n=== Two Overs Performance ===")
        print(f"Total time: {total_time:.2f}ms")
        print(f"Average per delivery: {avg_per_delivery:.2f}ms")

        assert (
            total_time < 600
        ), f"Two overs too slow: {total_time:.2f}ms (target: <600ms)"


class TestSnapshotPerformance:
    """Performance tests for snapshot retrieval."""

    def test_snapshot_performance(self, client):
        """
        Benchmark: Retrieving game snapshot.
        Target: < 50ms per snapshot.
        """
        # Create game and set openers
        response = client.post(
            "/games",
            json={
                "team_a_name": "Team A",
                "team_b_name": "Team B",
                "players_a": [f"PlayerA{i}" for i in range(1, 12)],
                "players_b": [f"PlayerB{i}" for i in range(1, 12)],
                "overs_limit": 20,
                "toss_winner_team": "A",
                "decision": "bat",
            },
        )
        game_data = response.json()
        game_id = game_data["id"]
        team_a_players = game_data["team_a"]["players"]
        team_b_players = game_data["team_b"]["players"]

        response = client.post(
            f"/games/{game_id}/openers",
            json={
                "striker_id": team_a_players[0]["id"],
                "non_striker_id": team_a_players[1]["id"],
                "opening_bowler_id": team_b_players[0]["id"],
            },
        )
        assert (
            response.status_code == 200
        ), f"Set openers failed: {response.status_code} - {response.json()}"

        # Post some deliveries first to make the snapshot more realistic
        bowler1_id = team_b_players[0]["id"]
        bowler2_id = team_b_players[1]["id"]
        for i in range(12):  # 2 overs
            bowler_id = bowler1_id if (i // 6) % 2 == 0 else bowler2_id
            client.post(
                f"/games/{game_id}/deliveries",
                json={
                    "bowler_id": bowler_id,
                    "runs_scored": 2,
                },
            )

        iterations = 20
        times = []

        for i in range(iterations):
            start = time.time()
            response = client.get(f"/games/{game_id}/snapshot")
            end = time.time()

            assert response.status_code == 200
            times.append((end - start) * 1000)

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print("\n=== Snapshot Retrieval Performance ===")
        print(f"Iterations: {iterations}")
        print(f"Average: {avg_time:.2f}ms")
        print(f"Min: {min_time:.2f}ms")
        print(f"Max: {max_time:.2f}ms")

        assert (
            avg_time < 50
        ), f"Snapshot retrieval too slow: {avg_time:.2f}ms (target: <50ms)"


class TestFullMatchPerformance:
    """Performance tests for complete match scenarios."""

    def test_complete_match_performance(self, client):
        """
        Benchmark: Playing a complete 2-over match (24 deliveries).
        Target: < 2 seconds total.
        """
        # Create game
        response = client.post(
            "/games",
            json={
                "team_a_name": "Team A",
                "team_b_name": "Team B",
                "players_a": [f"PlayerA{i}" for i in range(1, 12)],
                "players_b": [f"PlayerB{i}" for i in range(1, 12)],
                "overs_limit": 2,
                "toss_winner_team": "A",
                "decision": "bat",
            },
        )
        game_data = response.json()
        game_id = game_data["id"]

        team_a_players = game_data["team_a"]["players"]
        team_b_players = game_data["team_b"]["players"]

        # Set openers
        response = client.post(
            f"/games/{game_id}/openers",
            json={
                "striker_id": team_a_players[0]["id"],
                "non_striker_id": team_a_players[1]["id"],
                "opening_bowler_id": team_b_players[0]["id"],
            },
        )
        assert (
            response.status_code == 200
        ), f"Set openers failed: {response.status_code} - {response.json()}"

        start = time.time()

        # First innings: 2 overs (12 deliveries)
        for i in range(12):
            bowler = (
                team_b_players[0]["id"]
                if (i // 6) % 2 == 0
                else team_b_players[1]["id"]
            )
            response = client.post(
                f"/games/{game_id}/deliveries",
                json={
                    "bowler_id": bowler,
                    "runs_scored": 3,
                },
            )
            assert response.status_code == 200

        # Start second innings
        response = client.post(
            f"/games/{game_id}/innings/start",
            json={
                "striker_id": team_b_players[0]["id"],
                "non_striker_id": team_b_players[1]["id"],
                "opening_bowler_id": team_a_players[0]["id"],
            },
        )
        if response.status_code != 200:
            print(
                f"\nStart next innings failed: {response.status_code} - {response.json()}"
            )
        assert (
            response.status_code == 200
        ), f"Start next innings failed: {response.status_code} - {response.json()}"

        # Second innings: 2 overs (12 deliveries)
        for i in range(12):
            bowler = (
                team_a_players[0]["id"]
                if (i // 6) % 2 == 0
                else team_a_players[1]["id"]
            )
            response = client.post(
                f"/games/{game_id}/deliveries",
                json={
                    "bowler_id": bowler,
                    "runs_scored": 3,
                },
            )
            if response.status_code != 200:
                print(
                    f"\nSecond innings delivery {i}: {response.status_code} - {response.json()}"
                )
            assert response.status_code == 200

        end = time.time()

        total_time = end - start
        avg_per_delivery = (total_time / 24) * 1000  # ms per delivery

        print("\n=== Complete 2-Over Match Performance ===")
        print("Total deliveries: 24")
        print(f"Total time: {total_time:.2f}s")
        print(f"Average per delivery: {avg_per_delivery:.2f}ms")

        assert (
            total_time < 2
        ), f"Complete match too slow: {total_time:.2f}s (target: <2s)"


class TestDLSPerformance:
    """Performance tests for DLS calculations."""

    def test_dls_calculation_performance(self):
        """
        Benchmark: DLS target calculation.
        Target: < 10ms per calculation.
        """
        from dls import compute_dls_target

        iterations = 100
        times = []

        for i in range(iterations):
            start = time.time()
            result = compute_dls_target(
                team1_score=180,
                team1_wickets_lost=6,
                team1_overs_left_at_end=0,  # Team 1 completed 20 overs
                format_overs=20,
                team2_wkts_lost_now=0,
                team2_overs_left_now=15,  # Team 2 has 15 overs
            )
            end = time.time()

            assert result.target is not None
            times.append((end - start) * 1000)

        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print("\n=== DLS Calculation Performance ===")
        print(f"Iterations: {iterations}")
        print(f"Average: {avg_time:.2f}ms")
        print(f"Min: {min_time:.2f}ms")
        print(f"Max: {max_time:.2f}ms")

        assert (
            avg_time < 10
        ), f"DLS calculation too slow: {avg_time:.2f}ms (target: <10ms)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
