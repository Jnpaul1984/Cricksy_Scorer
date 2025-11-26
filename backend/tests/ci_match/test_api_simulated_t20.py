from __future__ import annotations

import json
from collections import deque
from collections.abc import Iterable
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

import backend.main as main
from backend.main import get_db
from backend.sql_app import crud
from backend.testsupport.in_memory_crud import InMemoryCrudRepository


@pytest.fixture()
def api_client(monkeypatch: pytest.MonkeyPatch) -> Iterable[TestClient]:
    repo = InMemoryCrudRepository()

    async def fake_get_db() -> Iterable[object]:
        yield object()

    fastapi_app = main._fastapi
    fastapi_app.dependency_overrides[get_db] = fake_get_db
    monkeypatch.setattr(crud, "create_game", repo.create_game)
    monkeypatch.setattr(crud, "get_game", repo.get_game)
    monkeypatch.setattr(crud, "update_game", repo.update_game)
    monkeypatch.setattr(main.crud, "create_game", repo.create_game)
    monkeypatch.setattr(main.crud, "get_game", repo.get_game)
    monkeypatch.setattr(main.crud, "update_game", repo.update_game)

    client = TestClient(fastapi_app)
    try:
        yield client
    finally:
        fastapi_app.dependency_overrides.pop(get_db, None)
        client.close()


def _load_fixture() -> dict[str, Any]:
    path = Path(__file__).resolve().parents[1] / "simulated_t20_match.json"
    return json.loads(path.read_text(encoding="utf-8"))


def _name_to_id(players: Iterable[dict[str, Any]]) -> dict[str, str]:
    return {p["name"]: str(p["id"]) for p in players}


def _post_json(
    client: TestClient, method: str, url: str, payload: dict[str, Any]
) -> dict[str, Any]:
    response = (
        client.post(url, json=payload)
        if method == "POST"
        else client.put(url, json=payload)
    )
    assert response.status_code < 400, response.text
    return response.json() if response.text else {}


def _play_innings(
    client: TestClient,
    game_id: str,
    innings: dict[str, Any],
    batting_ids: dict[str, str],
    bowling_ids: dict[str, str],
) -> None:
    balls = sorted(innings["balls"], key=lambda b: (b["over"], b["ball"]))

    opening = innings["opening_pair"]
    striker = opening["striker"]
    non_striker = opening["non_striker"]

    seen_batters = [striker, non_striker]
    for entry in balls:
        name = entry["batsman"]
        if name not in seen_batters:
            seen_batters.append(name)
    remaining = deque(seen_batters[2:])

    current_over = None

    for ball in balls:
        over_no = int(ball["over"])
        ball_no = int(ball["ball"])
        bowler_name = ball["bowler"]

        if ball_no == 1 or over_no != current_over:
            _post_json(
                client,
                "POST",
                f"/games/{game_id}/overs/start",
                {"bowler_id": bowling_ids[bowler_name]},
            )
            current_over = over_no

        bat_runs = int(ball.get("runs", 0))
        extra_runs = int(ball.get("extras", 0) or 0)
        extra_type = (ball.get("extraType") or "").lower() or None
        payload: dict[str, Any] = {
            "striker_id": batting_ids[striker],
            "non_striker_id": batting_ids[non_striker],
            "bowler_id": bowling_ids[bowler_name],
            "is_wicket": bool(ball["wicket"]),
        }

        extra_code = None
        if extra_type in {"wd", "wide"}:
            extra_code = "wd"
            payload["extra"] = "wd"
            payload["runs_scored"] = max(1, extra_runs)
        elif extra_type in {"nb", "no_ball", "no-ball"}:
            extra_code = "nb"
            payload["extra"] = "nb"
            payload["runs_off_bat"] = bat_runs
        elif extra_type in {"b", "bye"}:
            extra_code = "b"
            payload["extra"] = "b"
            payload["runs_scored"] = extra_runs
        elif extra_type in {"lb", "leg_bye", "leg-bye"}:
            extra_code = "lb"
            payload["extra"] = "lb"
            payload["runs_scored"] = extra_runs
        else:
            payload["runs_scored"] = bat_runs

        if ball.get("wicketType"):
            payload["dismissal_type"] = ball["wicketType"]
        if ball.get("fielder"):
            payload["fielder_id"] = bowling_ids[ball["fielder"]]

        _post_json(client, "POST", f"/games/{game_id}/deliveries", payload)

        if payload["is_wicket"]:
            if not remaining:
                break
            striker = remaining.popleft()
            _post_json(
                client,
                "POST",
                f"/games/{game_id}/batters/replace",
                {"new_batter_id": batting_ids[striker]},
            )
        else:
            rotates = False
            if extra_code == "wd":
                rotates = False
            elif extra_code == "nb":
                rotates = bat_runs % 2 == 1
            else:
                rotates = payload["runs_scored"] % 2 == 1
            if rotates:
                striker, non_striker = non_striker, striker

        if ball_no == 6:
            striker, non_striker = non_striker, striker


def test_simulated_match_via_api(api_client: TestClient) -> None:
    match = _load_fixture()

    players_a = [f"Alpha Player {i}" for i in range(1, 12)]
    players_b = [f"Beta Player {i}" for i in range(1, 12)]

    create_payload = {
        "team_a_name": match["teams"][0],
        "team_b_name": match["teams"][1],
        "players_a": players_a,
        "players_b": players_b,
        "match_type": "limited",
        "overs_limit": 20,
        "dls_enabled": True,
        "toss_winner_team": match["teams"][0],
        "decision": "bat",
    }

    create_resp = api_client.post("/games", json=create_payload)
    assert create_resp.status_code == 200, create_resp.text
    game = create_resp.json()
    game_id = game["id"]

    team_a_ids = _name_to_id(game["team_a"]["players"])
    team_b_ids = _name_to_id(game["team_b"]["players"])

    first_innings = match["innings"][0]
    second_innings = match["innings"][1]

    _post_json(
        api_client,
        "POST",
        f"/games/{game_id}/innings/start",
        {
            "striker_id": team_a_ids[first_innings["opening_pair"]["striker"]],
            "non_striker_id": team_a_ids[first_innings["opening_pair"]["non_striker"]],
            "opening_bowler_id": team_b_ids[first_innings["bowling_order"][0]],
        },
    )

    _play_innings(api_client, game_id, first_innings, team_a_ids, team_b_ids)

    start_next_payload = {
        "striker_id": team_b_ids[second_innings["opening_pair"]["striker"]],
        "non_striker_id": team_b_ids[second_innings["opening_pair"]["non_striker"]],
        "opening_bowler_id": team_a_ids[second_innings["bowling_order"][0]],
    }
    _post_json(
        api_client, "POST", f"/games/{game_id}/innings/start", start_next_payload
    )

    _play_innings(api_client, game_id, second_innings, team_b_ids, team_a_ids)

    game_detail = api_client.get(f"/games/{game_id}")
    assert game_detail.status_code == 200, game_detail.text
    detail_data = game_detail.json()

    assert detail_data["is_game_over"] is True
    assert detail_data["result"]["winner_team_name"] == match["result"]["winner"]
    assert detail_data["result"]["result_text"].rstrip(".") == match["result"][
        "summary"
    ].rstrip(".")
    assert detail_data["target"] == 158

    snapshot_resp = api_client.get(f"/games/{game_id}/snapshot")
    assert snapshot_resp.status_code == 200, snapshot_resp.text
    snapshot = snapshot_resp.json()

    assert snapshot["score"]["runs"] == second_innings["runs"]
    assert snapshot["score"]["wickets"] == second_innings["wickets"]
    assert snapshot["target"] == 158
    dls_panel = snapshot.get("dls")
    assert isinstance(dls_panel, dict)
