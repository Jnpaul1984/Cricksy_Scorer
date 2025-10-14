import os, time, json
from backend.tests._ci_utils import traced_request

API = os.getenv("API_BASE", "http://localhost:8000").rstrip("/")

def _req(m,u,**k): return traced_request(m,u,**k)
def _post(url,json): r=_req("POST",url,json=json); assert r.status_code<400, r.text; return r.json()
def _get(url): r=_req("GET",url); assert r.status_code<400, r.text; return r.json()

def test_smoke_create_and_one_ball():
    payload = {
        "match_type": "limited",
        "overs_limit": 2,
        "team_a_name": "Alpha", "team_b_name": "Bravo",
        "players_a": [f"A{i}" for i in range(1,12)],
        "players_b": [f"B{i}" for i in range(1,12)],
        "toss_winner_team": "A", "decision": "bat",
    }
    g = _post(f"{API}/games", payload)
    gid = g.get("id") or g.get("gid") or (g.get("game") or {}).get("id")
    assert gid, f"no gid in {g}"

    g = _get(f"{API}/games/{gid}")
    a, b = g["team_a"], g["team_b"]
    s_id, ns_id = a["players"][0]["id"], a["players"][1]["id"]
    bowler = b["players"][0]["id"]

    # IMPORTANT for your backend: runs_off_bat must be 0 on legal balls
    ball = {
        "striker_id": s_id,
        "non_striker_id": ns_id,
        "bowler_id": bowler,
        "runs_scored": 1,
        "runs_off_bat": 0,     # <-- per your API’s validation
        "is_wicket": False
    }
    _post(f"{API}/games/{gid}/deliveries", ball)

    g2 = _get(f"{API}/games/{gid}")
    assert g2.get("total_runs", 0) >= 1
