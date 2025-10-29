from __future__ import annotations

from typing import Any

from fastapi.testclient import TestClient

from backend.main import app  # socketio.ASGIApp wrapping the FastAPI app

client = TestClient(app)


def _create_game_and_post_result() -> str:
    # Create a game via the real backend
    create_resp = client.post(
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
    assert create_resp.status_code == 200, create_resp.text
    game_id = create_resp.json()["id"]

    result_body = {
        "match_id": game_id,
        "winner": "Team A",
        "team_a_score": 150,
        "team_b_score": 120,
    }
    post_resp = client.post(f"/games/{game_id}/results", json=result_body)
    assert post_resp.status_code in (200, 201), post_resp.text

    return game_id


def test_results_endpoint_with_valid_id():
    game_id = _create_game_and_post_result()
    response = client.get(f"/games/{game_id}/results")
    assert response.status_code == 200


def test_results_endpoint():
    _ = _create_game_and_post_result()

    response = client.get("/games/results")
    assert response.status_code == 200
    results = response.json()
    print("DEBUG: /games/results response:", results)
    assert isinstance(results, list)
    assert results, "expected at least one result"

    result: dict[str, Any] = results[0]
    assert "match_id" in result
    assert "winner" in result
    assert "team_a_score" in result
    assert "team_b_score" in result

    assert isinstance(result["match_id"], str)
    assert isinstance(result["winner"], (str, type(None)))
    assert isinstance(result["team_a_score"], int)
    assert isinstance(result["team_b_score"], int)
