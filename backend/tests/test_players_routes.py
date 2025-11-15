from __future__ import annotations

import os

from fastapi.testclient import TestClient

from backend.app import create_app


def test_award_achievement_and_profile_flow():
    # Ensure create_app wires in-memory DB
    os.environ["CRICKSY_IN_MEMORY_DB"] = "1"
    _asgi_app, fastapi_app = create_app()

    payload = {
        "game_id": None,
        "achievement_type": "century",
        "title": "Century Master",
        "description": "Scored 150 runs in a match",
        "badge_icon": "💯",
        "metadata": {"runs": 150, "balls": 120},
    }

    with TestClient(fastapi_app) as client:
        # Awarding an achievement without an existing profile should 404
        resp = client.post("/api/players/player-test-001/achievements", json=payload)
        assert resp.status_code == 404

        # Requesting achievements should return a list (empty when no data)
        resp2 = client.get("/api/players/player-test-001/achievements")
        assert resp2.status_code == 200
        assert isinstance(resp2.json(), list)

        # Leaderboard endpoint should be wired and return a valid shape
        resp3 = client.get("/api/players/leaderboard")
        assert resp3.status_code == 200
        data3 = resp3.json()
        assert "metric" in data3 and "entries" in data3
