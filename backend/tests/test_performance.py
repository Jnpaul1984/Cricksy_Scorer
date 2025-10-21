"""
Performance benchmarks for Cricksy Scorer backend.

These tests measure the performance of key operations to identify bottlenecks
and ensure the application can handle realistic workloads.
"""

import time
import pytest
from fastapi.testclient import TestClient
from main import _fastapi as app


@pytest.fixture
def client():
    """Create a test client for the FastAPI app."""
    return TestClient(app)


@pytest.fixture
def sample_game(client):
    """Create a sample game for performance testing."""
    response = client.post('/games', json={
        'team_a_name': 'Team A',
        'team_b_name': 'Team B',
        'players_a': [f'PlayerA{i}' for i in range(1, 12)],
        'players_b': [f'PlayerB{i}' for i in range(1, 12)],
        'overs_limit': 20,
        'toss_winner_team': 'A',
        'decision': 'bat'
    })
    assert response.status_code == 200
    game_data = response.json()
    
    # Set openers
    team_a_players = game_data['team_a']['players']
    team_b_players = game_data['team_b']['players']
    
    client.post(f"/games/{game_data['id']}/set-openers", json={
        'striker_id': team_a_players[0]['id'],
        'non_striker_id': team_a_players[1]['id'],
        'opening_bowler_id': team_b_players[0]['id']
    })
    
    return {
        'game_id': game_data['id'],
        'team_a_players': team_a_players,
        'team_b_players': team_b_players
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
            response = client.post('/games', json={
                'team_a_name': f'Team A {i}',
                'team_b_name': f'Team B {i}',
                'players_a': [f'PlayerA{j}' for j in range(1, 12)],
                'players_b': [f'PlayerB{j}' for j in range(1, 12)],
                'overs_limit': 20,
                'toss_winner_team': 'A',
                'decision': 'bat'
            })
            end = time.time()
            
            assert response.status_code == 200
            times.append((end - start) * 1000)  # Convert to ms
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\n=== Game Creation Performance ===")
        print(f"Iterations: {iterations}")
        print(f"Average: {avg_time:.2f}ms")
        print(f"Min: {min_time:.2f}ms")
        print(f"Max: {max_time:.2f}ms")
        
        # Assert performance target
        assert avg_time < 100, f"Game creation too slow: {avg_time:.2f}ms (target: <100ms)"


class TestDeliveryPerformance:
    """Performance tests for delivery posting."""
    
    def test_single_delivery_performance(self, client, sample_game):
        """
        Benchmark: Posting a single delivery.
        Target: < 50ms per delivery.
        """
        game_id = sample_game['game_id']
        bowler1_id = sample_game['team_b_players'][0]['id']
        bowler2_id = sample_game['team_b_players'][1]['id']
        
        iterations = 20
        times = []
        
        for i in range(iterations):
            bowler_id = bowler1_id if (i // 6) % 2 == 0 else bowler2_id
            start = time.time()
            response = client.post(f'/games/{game_id}/deliveries', json={
                'bowler_id': bowler_id,
                'runs_scored': 1,
            })
            end = time.time()
            
            assert response.status_code == 200
            times.append((end - start) * 1000)
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\n=== Single Delivery Performance ===")
        print(f"Iterations: {iterations}")
        print(f"Average: {avg_time:.2f}ms")
        print(f"Min: {min_time:.2f}ms")
        print(f"Max: {max_time:.2f}ms")
        
        assert avg_time < 50, f"Delivery posting too slow: {avg_time:.2f}ms (target: <50ms)"
    
    def test_full_over_performance(self, client, sample_game):
        """
        Benchmark: Posting a full over (6 deliveries).
        Target: < 300ms per over.
        """
        game_id = sample_game['game_id']
        bowler1_id = sample_game['team_b_players'][0]['id']
        bowler2_id = sample_game['team_b_players'][1]['id']
        
        start = time.time()
        for i in range(12):  # 2 overs to test bowler rotation
            bowler_id = bowler1_id if (i // 6) % 2 == 0 else bowler2_id
            response = client.post(f'/games/{game_id}/deliveries', json={
                'bowler_id': bowler_id,
                'runs_scored': 1,
            })
            assert response.status_code == 200
        end = time.time()
        
        total_time = (end - start) * 1000
        avg_per_delivery = total_time / 12
        
        print(f"\n=== Two Overs Performance ===")
        print(f"Total time: {total_time:.2f}ms")
        print(f"Average per delivery: {avg_per_delivery:.2f}ms")
        
        assert total_time < 600, f"Two overs too slow: {total_time:.2f}ms (target: <600ms)"


class TestSnapshotPerformance:
    """Performance tests for snapshot retrieval."""
    
    def test_snapshot_performance(self, client, sample_game):
        """
        Benchmark: Retrieving game snapshot.
        Target: < 50ms per snapshot.
        """
        game_id = sample_game['game_id']
        
        # Post some deliveries first to make the snapshot more realistic
        bowler_id = sample_game['team_b_players'][0]['id']
        for i in range(12):  # 2 overs
            client.post(f'/games/{game_id}/deliveries', json={
                'bowler_id': bowler_id,
                'runs_scored': 2,
            })
        
        iterations = 20
        times = []
        
        for i in range(iterations):
            start = time.time()
            response = client.get(f'/games/{game_id}/snapshot')
            end = time.time()
            
            assert response.status_code == 200
            times.append((end - start) * 1000)
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\n=== Snapshot Retrieval Performance ===")
        print(f"Iterations: {iterations}")
        print(f"Average: {avg_time:.2f}ms")
        print(f"Min: {min_time:.2f}ms")
        print(f"Max: {max_time:.2f}ms")
        
        assert avg_time < 50, f"Snapshot retrieval too slow: {avg_time:.2f}ms (target: <50ms)"


class TestFullMatchPerformance:
    """Performance tests for complete match scenarios."""
    
    def test_complete_t20_match_performance(self, client):
        """
        Benchmark: Playing a complete T20 match (240 deliveries).
        Target: < 15 seconds total.
        """
        # Create game
        response = client.post('/games', json={
            'team_a_name': 'Team A',
            'team_b_name': 'Team B',
            'players_a': [f'PlayerA{i}' for i in range(1, 12)],
            'players_b': [f'PlayerB{i}' for i in range(1, 12)],
            'overs_limit': 20,
            'toss_winner_team': 'A',
            'decision': 'bat'
        })
        game_data = response.json()
        game_id = game_data['id']
        
        team_a_players = game_data['team_a']['players']
        team_b_players = game_data['team_b']['players']
        
        # Set openers
        client.post(f"/games/{game_id}/set-openers", json={
            'striker_id': team_a_players[0]['id'],
            'non_striker_id': team_a_players[1]['id'],
            'opening_bowler_id': team_b_players[0]['id']
        })
        
        start = time.time()
        
        # First innings: 20 overs (120 deliveries)
        for i in range(120):
            bowler = team_b_players[0]['id'] if (i // 6) % 2 == 0 else team_b_players[1]['id']
            response = client.post(f'/games/{game_id}/deliveries', json={
                'bowler_id': bowler,
                'runs_scored': 3,
            })
            assert response.status_code == 200
        
        # Start second innings
        client.post(f"/games/{game_id}/start-next-innings", json={
            'striker_id': team_b_players[0]['id'],
            'non_striker_id': team_b_players[1]['id'],
            'opening_bowler_id': team_a_players[0]['id']
        })
        
        # Second innings: 20 overs (120 deliveries)
        for i in range(120):
            bowler = team_a_players[0]['id'] if (i // 6) % 2 == 0 else team_a_players[1]['id']
            response = client.post(f'/games/{game_id}/deliveries', json={
                'bowler_id': bowler,
                'runs_scored': 3,
            })
            assert response.status_code == 200
        
        end = time.time()
        
        total_time = end - start
        avg_per_delivery = (total_time / 240) * 1000  # ms per delivery
        
        print(f"\n=== Complete T20 Match Performance ===")
        print(f"Total deliveries: 240")
        print(f"Total time: {total_time:.2f}s")
        print(f"Average per delivery: {avg_per_delivery:.2f}ms")
        
        assert total_time < 15, f"Complete match too slow: {total_time:.2f}s (target: <15s)"


class TestDLSPerformance:
    """Performance tests for DLS calculations."""
    
    def test_dls_calculation_performance(self):
        """
        Benchmark: DLS target calculation.
        Target: < 10ms per calculation.
        """
        from dls import dls_target
        
        iterations = 100
        times = []
        
        for i in range(iterations):
            start = time.time()
            target = dls_target(
                s1=180,
                w1=6,
                o1=20,
                o2=15,
                w2=0,
                total_overs=20
            )
            end = time.time()
            
            assert target is not None
            times.append((end - start) * 1000)
        
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)
        
        print(f"\n=== DLS Calculation Performance ===")
        print(f"Iterations: {iterations}")
        print(f"Average: {avg_time:.2f}ms")
        print(f"Min: {min_time:.2f}ms")
        print(f"Max: {max_time:.2f}ms")
        
        assert avg_time < 10, f"DLS calculation too slow: {avg_time:.2f}ms (target: <10ms)"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])

