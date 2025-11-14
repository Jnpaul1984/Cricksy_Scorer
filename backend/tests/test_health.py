import os
import sys

import pytest
from fastapi.testclient import TestClient

# Ensure backend is on path for local runs
sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from backend.main import app


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def test_health(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    data = (
        resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
    )
    # accept either {"status":"ok"} or any simple text "ok"
    if isinstance(data, dict) and "status" in data:
        assert str(data["status"]).lower() in {"ok", "healthy", "up"}
    else:
        assert "ok" in resp.text.lower()
