import os
import time
import requests

BASE = os.getenv("BASE_URL", "http://localhost:8000")

def test_health_ok():
    # small retry to handle slow boot if run immediately
    for _ in range(30):
        try:
            r = requests.get(f"{BASE}/health", timeout=2)
            if r.status_code == 200:
                assert r.json().get("status") == "ok"
                return
        except Exception:
            pass
        time.sleep(1)
    raise AssertionError("API /health did not return 200 within timeout")



