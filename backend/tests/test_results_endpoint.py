from fastapi.testclient import TestClient
from typing import Any, Dict
import uuid

import backend.main as main
from backend.main import app  # socketio.ASGIApp wrapping the FastAPI app
from backend.routes import games_router as gr

client = TestClient(app)


# ---- Lightweight DB override for games_router endpoints ----
class _FakeGame:
    def __init__(self, gid: str):
        self.id = gid
        self.result = None  # stored as JSON string in real model


class _FakeResult:
    def __init__(self, game: _FakeGame | None = None, games: list[_FakeGame] | None = None):
        self._game = game
        self._games = games or []

    def scalar_one_or_none(self):
        return self._game

    class _Scalars:
        def __init__(self, games: list[_FakeGame]):
            self._games = games

        def all(self):
            return self._games

    def scalars(self):
        return _FakeResult._Scalars(self._games)


class _FakeSession:
    # Shared across requests so state persists between POST and GET
    current_id: str | None = None

    def __init__(self):
        self.games: dict[str, _FakeGame] = {}

    async def execute(self, query):  # type: ignore[no-untyped-def]
        # If there's any WHERE criteria, assume it's a by-id lookup
        crit = getattr(query, "_where_criteria", [])
        if not crit:
            wc = getattr(query, "whereclause", None)
            if wc is not None:
                crit = [wc]
        if crit:
            # Try to detect if it's an ID equality
            by_id = False
            try:
                for c in crit:
                    left = getattr(c, "left", None)
                    if getattr(left, "key", None) == "id" or getattr(left, "name", None) == "id":
                        by_id = True
                        break
            except Exception:
                by_id = False

            if by_id:
                gid = _FakeSession.current_id or "00000000-0000-0000-0000-000000000000"
                g = self.games.get(gid) or _FakeGame(gid)
                self.games[gid] = g
                return _FakeResult(game=g)
            # Otherwise treat as a list query
            rows = [g for g in self.games.values() if g.result]
            return _FakeResult(games=rows)
        # Otherwise, assume list of games with results
        rows = [g for g in self.games.values() if g.result]
        return _FakeResult(games=rows)

    async def commit(self):  # type: ignore[no-untyped-def]
        return None


_FAKE_SESSION = _FakeSession()


async def _override_get_db():
    yield _FAKE_SESSION


# Install the dependency override for the router's imported get_db reference
main._fastapi.dependency_overrides[gr.get_db] = _override_get_db  # type: ignore[attr-defined]


def _create_game_and_post_result() -> str:
    # Use a random UUID for game_id and make the fake session aware of it
    game_id = str(uuid.uuid4())
    _FakeSession.current_id = game_id

    # Post a result for that game via the router endpoint
    result_body = {
        "match_id": game_id,
        "winner": "Team A",
        "team_a_score": 150,
        "team_b_score": 120,
    }
    r2 = client.post(f"/games/{game_id}/results", json=result_body)
    assert r2.status_code in (200, 201), f"post result failed: {r2.text}"
    return game_id


def test_results_endpoint_with_valid_id():
    game_id = _create_game_and_post_result()
    response = client.get(f"/games/{game_id}/results")
    assert response.status_code == 200


def test_results_endpoint():
    # Ensure at least one result exists
    _ = _create_game_and_post_result()

    response = client.get("/games/results")
    assert response.status_code == 200
    results = response.json()
    assert isinstance(results, list)  # Ensure results is a list
    assert len(results) >= 1

    # Further assertions on at least one result
    result: Dict[str, Any] = results[0]
    assert "match_id" in result
    assert "winner" in result
    assert "team_a_score" in result
    assert "team_b_score" in result

    # Type checks
    assert isinstance(result["match_id"], str)
    assert isinstance(result["winner"], (str, type(None)))  # Winner can be None
    assert isinstance(result["team_a_score"], int)
    assert isinstance(result["team_b_score"], int)



