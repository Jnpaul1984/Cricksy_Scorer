"""
Example Test Organization
==========================

This file demonstrates how to organize and mark tests for different test types.
Copy this pattern to your actual test files.

Test Types:
-----------
1. Unit Tests - Fast, isolated, no external dependencies
2. Integration Tests - Require backend server running
3. E2E Tests - Require full system (backend + frontend)

Usage:
------
Run specific test types:
    pytest -m unit                  # Only unit tests
    pytest -m integration           # Only integration tests
    pytest -m "unit or integration" # Both unit and integration
    pytest -m "not slow"            # Everything except slow tests
"""

import pytest

from backend.sql_app import models, schemas

# ============================================================================
# UNIT TESTS - Fast, isolated, no external dependencies
# ============================================================================


@pytest.mark.unit
def test_player_model_creation():
    """Unit test: Test Player model instantiation"""
    player = models.Player(id="player-123", name="John Doe", role="batsman")
    assert player.id == "player-123"
    assert player.name == "John Doe"
    assert player.role == "batsman"


@pytest.mark.unit
def test_game_schema_validation():
    """Unit test: Test GameCreate schema validation"""
    game_data = {
        "match_type": "limited",
        "overs_limit": 20,
        "team_a_name": "Team A",
        "team_b_name": "Team B",
        "players_a": ["P1", "P2", "P3"],
        "players_b": ["P4", "P5", "P6"],
        "toss_winner_team": "A",
        "decision": "bat",
    }
    game_schema = schemas.GameCreate(**game_data)
    assert game_schema.match_type == "limited"
    assert game_schema.overs_limit == 20


@pytest.mark.unit
def test_utility_function():
    """Unit test: Test a utility function"""
    # Example: Test a helper function
    from backend.dls import calculate_resource_percentage

    # Mock test - replace with actual function
    result = calculate_resource_percentage(50, 10, 5)
    assert isinstance(result, (int, float))


# ============================================================================
# INTEGRATION TESTS - Require backend server running
# ============================================================================


@pytest.mark.integration
async def test_create_game_api():
    """Integration test: Test game creation via API"""
    import httpx

    game_payload = {
        "match_type": "limited",
        "overs_limit": 20,
        "team_a_name": "Alpha",
        "team_b_name": "Bravo",
        "players_a": [f"A{i}" for i in range(1, 12)],
        "players_b": [f"B{i}" for i in range(1, 12)],
        "toss_winner_team": "A",
        "decision": "bat",
    }

    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        response = await client.post("/games", json=game_payload)
        assert response.status_code == 200
        data = response.json()
        assert "id" in data
        assert data["team_a"]["name"] == "Alpha"


@pytest.mark.integration
@pytest.mark.slow
async def test_full_match_flow():
    """Integration test: Test complete match flow"""
    import httpx

    # This test takes longer than 5 seconds
    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        # Create game
        game_response = await client.post("/games", json={...})
        game_id = game_response.json()["id"]

        # Start game
        await client.post(f"/games/{game_id}/start")

        # Set openers
        await client.post(f"/games/{game_id}/set_openers", json={...})

        # Play several deliveries
        for _ in range(10):
            await client.post(f"/games/{game_id}/delivery", json={...})

        # Verify game state
        game_state = await client.get(f"/games/{game_id}")
        assert game_state.status_code == 200


@pytest.mark.integration
@pytest.mark.database
async def test_database_persistence():
    """Integration test: Test database operations"""
    # Tests that require actual database (not in-memory)
    # Skip if CRICKSY_IN_MEMORY_DB is set
    import os

    if os.getenv("CRICKSY_IN_MEMORY_DB"):
        pytest.skip("Skipping database test in in-memory mode")

    # Test database-specific features
    pass


@pytest.mark.integration
@pytest.mark.websocket
async def test_websocket_updates():
    """Integration test: Test WebSocket real-time updates"""
    import socketio

    sio = socketio.AsyncClient()
    await sio.connect("http://localhost:8000")

    # Test WebSocket events
    @sio.on("score_update")
    async def on_score_update(data):
        assert "runs" in data

    await sio.disconnect()


# ============================================================================
# E2E TESTS - Require full system (backend + frontend)
# ============================================================================


@pytest.mark.e2e
@pytest.mark.slow
async def test_full_system_match_simulation():
    """E2E test: Test complete match through frontend and backend"""
    import httpx

    # This test requires both backend and frontend to be running
    # It simulates a complete user journey

    async with httpx.AsyncClient() as client:
        # Verify backend is running
        backend_health = await client.get("http://localhost:8000/health")
        assert backend_health.status_code == 200

        # Verify frontend is accessible
        frontend_health = await client.get("http://localhost:3000")
        assert frontend_health.status_code == 200

        # Perform end-to-end test
        # ... (full test implementation)


# ============================================================================
# SMOKE TESTS - Basic functionality checks
# ============================================================================


@pytest.mark.smoke
async def test_health_endpoint():
    """Smoke test: Verify health endpoint responds"""
    import httpx

    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        response = await client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "ok"


@pytest.mark.smoke
async def test_api_documentation_accessible():
    """Smoke test: Verify API docs are accessible"""
    import httpx

    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        response = await client.get("/docs")
        assert response.status_code == 200


# ============================================================================
# CONTRACT TESTS - API contract validation
# ============================================================================


@pytest.mark.contract
async def test_game_creation_response_schema():
    """Contract test: Verify game creation response matches schema"""
    import httpx

    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        response = await client.post("/games", json={...})
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert "team_a" in data
        assert "team_b" in data
        assert isinstance(data["team_a"]["players"], list)

        # Verify field types
        assert isinstance(data["id"], str)
        assert isinstance(data["overs_limit"], int)


# ============================================================================
# FIXTURES - Shared test setup
# ============================================================================


@pytest.fixture
def sample_game_payload():
    """Fixture: Provide sample game creation payload"""
    return {
        "match_type": "limited",
        "overs_limit": 20,
        "team_a_name": "Team A",
        "team_b_name": "Team B",
        "players_a": [f"A{i}" for i in range(1, 12)],
        "players_b": [f"B{i}" for i in range(1, 12)],
        "toss_winner_team": "A",
        "decision": "bat",
    }


@pytest.fixture
async def created_game(sample_game_payload):
    """Fixture: Create a game and return its ID"""
    import httpx

    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        response = await client.post("/games", json=sample_game_payload)
        game_id = response.json()["id"]
        yield game_id

        # Cleanup (if needed)
        # await client.delete(f"/games/{game_id}")


@pytest.mark.integration
async def test_using_fixture(created_game):
    """Example: Using a fixture in a test"""
    import httpx

    async with httpx.AsyncClient(base_url="http://localhost:8000") as client:
        response = await client.get(f"/games/{created_game}")
        assert response.status_code == 200


# ============================================================================
# PARAMETRIZED TESTS - Test multiple scenarios
# ============================================================================


@pytest.mark.unit
@pytest.mark.parametrize(
    "match_type,overs_limit",
    [
        ("limited", 20),
        ("limited", 50),
        ("unlimited", None),
    ],
)
def test_match_type_validation(match_type, overs_limit):
    """Unit test: Test different match type configurations"""
    game_data = {
        "match_type": match_type,
        "overs_limit": overs_limit,
        "team_a_name": "Team A",
        "team_b_name": "Team B",
        "players_a": ["P1", "P2"],
        "players_b": ["P3", "P4"],
        "toss_winner_team": "A",
        "decision": "bat",
    }

    if match_type == "limited":
        assert overs_limit is not None
    else:
        assert overs_limit is None or overs_limit == 0


# ============================================================================
# SKIP AND XFAIL - Conditional test execution
# ============================================================================


@pytest.mark.unit
@pytest.mark.skip(reason="Feature not yet implemented")
def test_future_feature():
    """Test for a feature that's not yet implemented"""
    pass


@pytest.mark.integration
@pytest.mark.skipif(
    "os.getenv('CRICKSY_IN_MEMORY_DB') == '1'", reason="Requires real database"
)
async def test_database_migration():
    """Test that requires real PostgreSQL database"""
    pass


@pytest.mark.unit
@pytest.mark.xfail(reason="Known bug #123")
def test_known_bug():
    """Test for a known bug that's being tracked"""
    assert False  # This will be marked as expected failure
