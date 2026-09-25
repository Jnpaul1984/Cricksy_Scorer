from __future__ import annotations

import os

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from sqlalchemy import text


@pytest_asyncio.fixture(scope="session")
async def _setup_db():
    """Use Alembic schema for explicit Phase 7B/7C PostgreSQL validation."""
    from backend.sql_app.database import Base, get_engine

    engine = get_engine()
    use_migrated_postgres = (
        os.getenv("PHASE7B_POSTGRES_MIGRATED_TESTS") == "1" and engine.dialect.name == "postgresql"
    )
    if not use_migrated_postgres:
        async with engine.begin() as connection:
            await connection.run_sync(Base.metadata.create_all)

    yield engine
    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def reset_db(_setup_db):
    """Reset focused tables without rebuilding protected PostgreSQL enum models."""
    import backend.security
    from backend.sql_app.database import Base, get_engine

    engine = get_engine()
    use_migrated_postgres = (
        os.getenv("PHASE7B_POSTGRES_MIGRATED_TESTS") == "1" and engine.dialect.name == "postgresql"
    )
    async with engine.begin() as connection:
        if use_migrated_postgres:
            await connection.execute(
                text(
                    "TRUNCATE TABLE organization_player_availability_history, "
                    "organization_player_availability, organization_availability_targets, "
                    "organization_event_roster_players, "
                    "organization_event_teams, organization_events, "
                    "fixtures, tournament_teams, tournaments, games, "
                    "school_player_imports, "
                    "school_team_player_memberships, "
                    "school_player_memberships, teams, "
                    "organization_entitlements, organization_memberships, "
                    "organizations, player_profiles, users "
                    "RESTART IDENTITY CASCADE"
                )
            )
        else:
            await connection.run_sync(Base.metadata.drop_all)
            await connection.run_sync(Base.metadata.create_all)
    backend.security._in_memory_users.clear()


@pytest.fixture
def school_client(reset_db) -> TestClient:
    """Client bound to the real SQLAlchemy session used by Phase 7B tests."""
    from backend.main import fastapi_app
    from backend.sql_app.database import SessionLocal, get_db, reset_engine

    if os.getenv("PHASE7B_POSTGRES_MIGRATED_TESTS") == "1":
        # TestClient owns a separate event loop; rebuild the lazy engine so
        # database.py selects NullPool while PYTEST_CURRENT_TEST is present.
        reset_engine()

    async def override_get_db():
        async with SessionLocal() as session:
            yield session

    fastapi_app.dependency_overrides[get_db] = override_get_db
    with TestClient(fastapi_app) as client:
        client.session_maker = SessionLocal  # type: ignore[attr-defined]
        yield client
    fastapi_app.dependency_overrides.pop(get_db, None)
