from starlette.testclient import TestClient
from backend.app import create_app
from backend.sql_app import models_security
from backend.sql_app.database import SessionLocal as get_db_session  # type: ignore[attr-defined]

app = create_app()
client = TestClient(app)


def test_request_logging_no_secrets(monkeypatch):
    # Simulate a request with auth header and token
    db = get_db_session()
    db.query(models_security.RequestLog).delete()
    db.commit()
    headers = {"Authorization": "Bearer secret-token", "user-agent": "pytest-agent"}
    client.get("/docs", headers=headers)
    # Check that no auth header/token is stored in request_logs
    logs = db.query(models_security.RequestLog).all()
    for log in logs:
        if "token" in (log.userAgent or ""):
            raise AssertionError("token found in userAgent")
        if "token" in (log.path or ""):
            raise AssertionError("token found in path")
        if "token" in (log.ip or ""):
            raise AssertionError("token found in ip")
