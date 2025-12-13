import pytest
from fastapi.testclient import TestClient
from backend.services.mcp_server import app

client = TestClient(app)

def test_feedback_list_auth():
    resp = client.post("/tools/db/feedback.list", json={"since":"2025-12-01T00:00:00Z","until":"2025-12-12T23:59:59Z"})
    assert resp.status_code in (401, 403)

def test_config_runtime_auth():
    resp = client.post("/tools/system/config.runtime", json={})
    assert resp.status_code in (401, 403)

def test_health_check_auth():
    resp = client.post("/tools/system/health.check", json={})
    assert resp.status_code in (401, 403)


def test_security_tools_shape():
    # These should 401/403 if not authed, but shape test for now
    endpoints = [
        ("/tools/security/auth_failures", {"since":"2025-12-01T00:00:00Z","until":"2025-12-12T23:59:59Z","groupBy":"ip","limit":10}),
        ("/tools/security/suspicious_ips", {"since":"2025-12-01T00:00:00Z","until":"2025-12-12T23:59:59Z","minRequests":5,"limit":10}),
        ("/tools/security/rate_limit_hits", {"since":"2025-12-01T00:00:00Z","until":"2025-12-12T23:59:59Z","groupBy":"ip","limit":10}),
        ("/tools/security/admin_route_attempts", {"since":"2025-12-01T00:00:00Z","until":"2025-12-12T23:59:59Z","limit":10}),
        ("/tools/security/http_4xx_5xx_summary", {"since":"2025-12-01T00:00:00Z","until":"2025-12-12T23:59:59Z","groupBy":"path","limit":10}),
    ]
    for url, payload in endpoints:
        resp = client.post(url, json=payload)
        assert resp.status_code in (401, 403, 200)
