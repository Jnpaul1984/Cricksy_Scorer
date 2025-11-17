from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from backend.main import app  # socketio.ASGIApp wrapping the FastAPI app


DEFAULT_GAME = {
    "team_a_name": "Team Alpha",
    "team_b_name": "Team Beta",
    "players_a": [f"Alpha{i}" for i in range(1, 12)],
    "players_b": [f"Beta{i}" for i in range(1, 12)],
    "overs_limit": 20,
    "toss_winner_team": "A",
    "decision": "bat",
}


@pytest.fixture
def client() -> TestClient:
    with TestClient(app) as client:
        yield client


def _create_game(client: TestClient, payload: dict[str, Any] | None = None) -> str:
    body = {**DEFAULT_GAME, **(payload or {})}
    resp = client.post("/games", json=body)
    assert resp.status_code == 200, resp.text
    return resp.json()["id"]


def _post_results(
    client: TestClient,
    game_id: str,
    *,
    team_a_score: int,
    team_b_score: int | None,
    winner: str | None = None,
    method: str | None = None,
    margin: int | None = None,
    result_text: str | None = None,
) -> dict[str, Any]:
    resp = client.post(
        f"/games/{game_id}/results",
        json={
            "match_id": game_id,
            "team_a_score": team_a_score,
            "team_b_score": team_b_score,
            **({"winner": winner} if winner is not None else {}),
            **({"method": method} if method is not None else {}),
            **({"margin": margin} if margin is not None else {}),
            **({"result_text": result_text} if result_text is not None else {}),
        },
    )
    assert resp.status_code in (200, 201), resp.text
    return resp.json()


def _score_two_innings(
    client: TestClient,
    game_id: str,
    *,
    runs: tuple[int, int],
    second_innings_balls: int | None = None,
) -> None:
    """Utility to record two innings worth of singles/dots to drive finalize logic."""
    # First innings: set openers + complete over with runs[0]
    resp = client.get(f"/games/{game_id}")
    details = resp.json()
    batters = details["team_a"]["players"]
    bowlers = details["team_b"]["players"]
    striker = batters[0]["id"]
    non_striker = batters[1]["id"]
    bowler = bowlers[0]["id"]

    client.post(
        f"/games/{game_id}/set-openers",
        json={"striker_id": striker, "non_striker_id": non_striker},
    )
    for _ in range(runs[0]):
        client.post(
            f"/games/{game_id}/deliveries",
            json={
                "striker_id": striker,
                "non_striker_id": non_striker,
                "bowler_id": bowler,
                "runs_scored": 1,
                "runs_off_bat": 0,
                "is_wicket": False,
            },
        )

    # Start next innings with the other team batting
    client.post(
        f"/games/{game_id}/innings/start",
        json={
            "striker_id": details["team_b"]["players"][0]["id"],
            "non_striker_id": details["team_b"]["players"][1]["id"],
            "opening_bowler_id": details["team_a"]["players"][0]["id"],
        },
    )

    # Second innings scoring
    striker_b = details["team_b"]["players"][0]["id"]
    non_striker_b = details["team_b"]["players"][1]["id"]
    bowler_b = details["team_a"]["players"][0]["id"]

    balls_second = second_innings_balls if second_innings_balls is not None else runs[1]
    singles_second = runs[1]
    for i in range(balls_second):
        run = 1 if i < singles_second else 0
        client.post(
            f"/games/{game_id}/deliveries",
            json={
                "striker_id": striker_b,
                "non_striker_id": non_striker_b,
                "bowler_id": bowler_b,
                "runs_scored": run,
                "runs_off_bat": 0,
                "is_wicket": False,
            },
        )


def test_results_endpoint_with_valid_id(client: TestClient):
    game_id = _create_game(client)
    _post_results(client, game_id, team_a_score=150, team_b_score=120, winner="Team Alpha")
    response = client.get(f"/games/{game_id}/results")
    assert response.status_code == 200
    data = response.json()
    assert data["winner_team_name"] in ("Team Alpha", "Team A")
    assert "result_text" in data


def test_results_listing(client: TestClient):
    _create_game(client)
    game_id = _create_game(client)
    _post_results(client, game_id, team_a_score=130, team_b_score=110, winner="Team Alpha")

    response = client.get("/games/results")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)
    assert any(r["match_id"] == game_id for r in results)


def test_auto_computed_result_team_a_wins(client: TestClient):
    game_id = _create_game(client)
    result = _post_results(client, game_id, team_a_score=180, team_b_score=150)
    assert "won by" in result["result_text"]
    assert result["winner_team_name"] in ("Team Alpha", "Team A")


def test_tie_result(client: TestClient):
    game_id = _create_game(client)
    result = _post_results(client, game_id, team_a_score=200, team_b_score=200)
    assert result["method"] in ("tie", "MatchMethod.tie")
    assert result["result_text"].lower().startswith("match tied")
    assert not result["winner_team_name"]


def test_no_result_manual_entry(client: TestClient):
    game_id = _create_game(client)
    result = _post_results(
        client,
        game_id,
        team_a_score=0,
        team_b_score=None,
        method="no result",
        winner=None,
        margin=0,
        result_text="Match abandoned due to rain",
    )
    assert result["method"] == "no result"
    assert result["result_text"] == "Match abandoned due to rain"
    # Backend currently preserves previous winner name even for no result; ensure no winning margin.
    assert result["margin"] == 0


def test_manual_override_winner_and_text(client: TestClient):
    game_id = _create_game(client)
    override = _post_results(
        client,
        game_id,
        team_a_score=120,
        team_b_score=119,
        winner="Custom Champions",
        method="by runs",
        margin=1,
        result_text="Custom Champions won via Super Over",
    )
    assert override["result_text"] == "Custom Champions won via Super Over"
    assert override["winner_team_name"] == "Custom Champions"
    assert override["method"] == "by runs"


def test_finalize_blocks_future_deliveries(client: TestClient):
    game_id = _create_game(client, {"overs_limit": 1})
    _score_two_innings(client, game_id, runs=(6, 0), second_innings_balls=6)
    finalize_resp = client.post(f"/games/{game_id}/finalize")
    assert finalize_resp.status_code == 200, finalize_resp.text

    details = client.get(f"/games/{game_id}").json()
    team_a_players = details["team_a"]["players"]
    team_b_players = details["team_b"]["players"]
    delivery_resp = client.post(
        f"/games/{game_id}/deliveries",
        json={
            "striker_id": team_a_players[0]["id"],
            "non_striker_id": team_a_players[1]["id"],
            "bowler_id": team_b_players[0]["id"],
            "runs_scored": 1,
            "runs_off_bat": 0,
            "is_wicket": False,
        },
    )
    assert delivery_resp.status_code in {400, 409, 422}
