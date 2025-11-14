import os

os.environ["CRICKSY_IN_MEMORY_DB"] = "1"
from fastapi.testclient import TestClient

from backend import main
from backend.main import fastapi_app, get_db
from backend.sql_app import crud
from backend.testsupport.in_memory_crud import InMemoryCrudRepository

repo = InMemoryCrudRepository()


async def fake_get_db():
    yield object()


fastapi_app.dependency_overrides[get_db] = fake_get_db
crud.create_game = repo.create_game
crud.get_game = repo.get_game
crud.update_game = repo.update_game
main.crud.create_game = repo.create_game
main.crud.get_game = repo.get_game
main.crud.update_game = repo.update_game

client = TestClient(fastapi_app)

payload = {
    "team_a_name": "Team Alpha",
    "team_b_name": "Team Beta",
    "players_a": [f"Alpha Player {i}" for i in range(1, 12)],
    "players_b": [f"Beta Player {i}" for i in range(1, 12)],
    "match_type": "limited",
    "overs_limit": 20,
    "dls_enabled": True,
    "toss_winner_team": "Team Alpha",
    "decision": "bat",
}

resp = client.post("/games", json=payload)
print("status:", resp.status_code)
print("body:", resp.text)
