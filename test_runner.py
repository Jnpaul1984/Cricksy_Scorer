import threading
import time
import requests
import scripts.run_backend_in_memory as runner

thread = threading.Thread(target=runner.main, daemon=True)
thread.start()

for _ in range(80):
    try:
        resp = requests.get("http://127.0.0.1:8000/health", timeout=0.5)
        if resp.status_code == 200:
            break
    except Exception:
        pass
    time.sleep(0.5)

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

resp = requests.post("http://127.0.0.1:8000/games", json=payload)
print("status", resp.status_code)
print("text", resp.text[:200])

runner_config = getattr(runner, "uvicorn", None)
