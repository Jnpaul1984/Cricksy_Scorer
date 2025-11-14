from fastapi.testclient import TestClient

from backend import main

client = TestClient(main.fastapi_app)

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
