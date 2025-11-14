import os
import time
import requests

from backend.tests._ci_utils import traced_request

BASE = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")
USE_INPROC = os.getenv("CRICKSY_IN_MEMORY_DB") == "1"


def _get(url: str):
    if USE_INPROC:
        return traced_request("GET", url, timeout=2)
    return requests.get(url, timeout=2)


def test_health_ok():
    # small retry to handle slow boot if run immediately
    for _ in range(30):
        try:
            r = _get(f"{BASE}/health")
            if r.status_code == 200:
                assert r.json().get("status") == "ok"
                return
        except Exception:
            pass
        time.sleep(1)
    raise AssertionError("API /health did not return 200 within timeout")
