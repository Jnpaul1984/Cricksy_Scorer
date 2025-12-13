import pytest
from starlette.testclient import TestClient
from backend.app import create_app
from backend.sql_app import models_security
from backend.sql_app.database import get_db_session

app = create_app()
client = TestClient(app)

def test_request_logging_no_secrets(monkeypatch):
    # Simulate a request with auth header and token
    db = get_db_session()
    db.query(models_security.RequestLog).delete()
    db.commit()
    headers = {
        "Authorization": "Bearer secret-token",
        "user-agent": "pytest-agent"
    }
    resp = client.get("/docs", headers=headers)
    # Check that no auth header/token is stored in request_logs
    logs = db.query(models_security.RequestLog).all()
    for log in logs:
        assert "token" not in (log.userAgent or "")
        assert "token" not in (log.path or "")
        assert "token" not in (log.ip or "")
