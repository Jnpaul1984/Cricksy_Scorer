import pytest
from fastapi.testclient import TestClient

from backend.main import app, fastapi_app
from backend.sql_app.database import get_db

RETIRED_DIAGNOSTIC_PATHS = (
    "/health/admin",
    "/health/db",
    "/health/cors-config",
)

SYNTHETIC_SENSITIVE_VALUES = (
    "admin@example.test",
    "$2b$12$synthetic-password-hash",
    "synthetic-alembic-revision",
    "synthetic database exception detail",
)

_NO_DEPENDENCY_OVERRIDE = object()


@pytest.fixture
def client():
    with TestClient(app) as client:
        yield client


def test_health(client: TestClient):
    resp = client.get("/health")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_healthz(client: TestClient):
    """Regression: /healthz must be a stable alias of /health with the same locked contract."""
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}


def test_safe_health_endpoints_do_not_access_the_database(client: TestClient):
    db_dependency_was_called = False

    async def fail_if_database_is_accessed():
        nonlocal db_dependency_was_called
        db_dependency_was_called = True
        raise AssertionError("safe health probes must not access the database")

    previous_override = fastapi_app.dependency_overrides.get(get_db, _NO_DEPENDENCY_OVERRIDE)
    fastapi_app.dependency_overrides[get_db] = fail_if_database_is_accessed
    try:
        for path in ("/health", "/healthz"):
            response = client.get(path)

            assert response.status_code == 200
            assert response.json() == {"status": "ok"}
    finally:
        if previous_override is _NO_DEPENDENCY_OVERRIDE:
            fastapi_app.dependency_overrides.pop(get_db, None)
        else:
            fastapi_app.dependency_overrides[get_db] = previous_override

    assert not db_dependency_was_called


def test_diagnostic_health_routes_are_not_registered():
    registered_paths = {route.path for route in fastapi_app.routes if hasattr(route, "path")}
    documented_paths = set(fastapi_app.openapi()["paths"])

    assert "/health" in registered_paths
    assert "/healthz" in registered_paths
    assert registered_paths.isdisjoint(RETIRED_DIAGNOSTIC_PATHS)
    assert documented_paths.isdisjoint(RETIRED_DIAGNOSTIC_PATHS)


def test_retired_health_diagnostics_cannot_disclose_synthetic_sensitive_values(
    client: TestClient,
):
    db_dependency_was_called = False

    async def fail_if_database_is_accessed():
        nonlocal db_dependency_was_called
        db_dependency_was_called = True
        raise AssertionError("retired health diagnostics must not access the database")

    previous_override = fastapi_app.dependency_overrides.get(get_db, _NO_DEPENDENCY_OVERRIDE)
    fastapi_app.dependency_overrides[get_db] = fail_if_database_is_accessed
    try:
        for path in RETIRED_DIAGNOSTIC_PATHS:
            response = client.get(path)

            assert response.status_code == 404
            assert response.json() == {"detail": "Not Found"}
            for sensitive_value in SYNTHETIC_SENSITIVE_VALUES:
                assert sensitive_value not in response.text
    finally:
        if previous_override is _NO_DEPENDENCY_OVERRIDE:
            fastapi_app.dependency_overrides.pop(get_db, None)
        else:
            fastapi_app.dependency_overrides[get_db] = previous_override

    assert not db_dependency_was_called
