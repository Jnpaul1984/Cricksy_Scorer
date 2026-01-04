# backend/conftest.py
"""
Backend-specific pytest configuration.

This file imports the shared fixtures from the root conftest.py and makes them
available to all tests in the backend directory.
"""

import asyncio
import contextlib
import os
import sys

import pytest
import pytest_asyncio

# Force AnyIO to use asyncio backend unless explicitly overridden.
os.environ.setdefault("ANYIO_BACKEND", "asyncio")

# Set test environment variables BEFORE importing backend modules
if "DATABASE_URL" not in os.environ:
    os.environ["CRICKSY_IN_MEMORY_DB"] = "1"
    os.environ["DATABASE_URL"] = "sqlite+aiosqlite:///:memory?cache=shared"
    os.environ["APP_SECRET_KEY"] = "test-secret-key"

# On Windows, use the selector event loop policy
if sys.platform.startswith("win"):
    with contextlib.suppress(Exception):
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


@pytest.fixture(scope="session")
def event_loop():
    """
    Create a session-scoped event loop for the entire test session.
    """
    from backend.sql_app.database import reset_engine

    reset_engine()

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    yield loop
    loop.close()


@pytest_asyncio.fixture(scope="session")
async def _setup_db():
    """
    Session-scoped fixture to set up the database engine and create tables.
    """
    from backend.sql_app.database import Base, get_engine

    engine = get_engine()

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest_asyncio.fixture(autouse=True)
async def reset_db(_setup_db):
    """Reset the database state before each test."""
    import backend.security
    from backend.sql_app.database import Base, get_engine

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)

    # Clear in-memory user cache (critical for tests using IN_MEMORY_DB)
    backend.security._in_memory_users.clear()

    # Clear in-memory coaching models cache
    try:
        from backend import app

        app._in_memory_video_sessions.clear()
        app._in_memory_moment_markers.clear()
        app._in_memory_coach_notes.clear()
        app._in_memory_players.clear()
    except (ImportError, AttributeError):
        pass


@pytest_asyncio.fixture
async def db_session(_setup_db):
    """Provide a database session for tests."""
    from backend.sql_app.database import get_session_local

    async with get_session_local()() as session:
        yield session


@pytest_asyncio.fixture
async def async_client(_setup_db):
    """Provide an async HTTP client for testing endpoints."""
    from httpx import ASGITransport, AsyncClient

    from backend.app import create_app

    # create_app returns (socketio.ASGIApp, FastAPI) - use the FastAPI app for testing
    _, fastapi_app = create_app()
    transport = ASGITransport(app=fastapi_app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client


@pytest_asyncio.fixture
async def analyst_pro_token(db_session):
    """Create an analyst_pro user and return their token."""
    import backend.security as security
    from backend.sql_app.models import User

    # Create a User model instance with analyst_pro role
    user = User(
        id="analyst-test-user-id",
        email="analyst@test.com",
        hashed_password=security.get_password_hash("testpass"),
        role="analyst_pro",
        is_active=True,  # User must be active to pass auth checks
    )
    # Add to database for Postgres tests
    db_session.add(user)
    await db_session.commit()
    await db_session.refresh(user)

    # Also add to in-memory user cache for in-memory DB tests
    security.add_in_memory_user(user)

    # Generate a token - sub should be user.id, email is separate field
    token = security.create_access_token({"sub": user.id, "email": user.email, "role": user.role})
    return token


@pytest_asyncio.fixture
async def test_game(db_session):
    """Create a test game fixture."""
    from backend.sql_app.models import Game, GameStatus

    game = Game(
        match_type="T20",
        overs_limit=20,
        team_a={"id": "team_a_id", "name": "Team Alpha", "players": []},
        team_b={"id": "team_b_id", "name": "Team Beta", "players": []},
        status=GameStatus.live,
        deliveries=[],
    )
    db_session.add(game)
    await db_session.commit()
    await db_session.refresh(game)
    return game


@pytest_asyncio.fixture
async def test_game_with_deliveries(db_session):
    """Create a test game with sample deliveries."""
    from backend.sql_app.models import Game, GameStatus

    # Create sample deliveries for powerplay
    deliveries = []
    for over in range(6):
        for ball in range(1, 7):
            runs = 4 if (over == 2 and ball == 3) else (6 if (over == 4 and ball == 5) else 1)
            is_wicket = over == 3 and ball == 2
            deliveries.append(
                {
                    "over_number": over,
                    "ball_number": ball,
                    "runs_scored": runs,
                    "is_wicket": is_wicket,
                    "dismissal_type": "caught" if is_wicket else None,
                }
            )

    game = Game(
        match_type="T20",
        overs_limit=20,
        team_a={"id": "team_a_id", "name": "Team Alpha", "players": []},
        team_b={"id": "team_b_id", "name": "Team Beta", "players": []},
        status=GameStatus.live,
        deliveries=deliveries,
        result="Team Alpha won by 20 runs",
    )
    db_session.add(game)
    await db_session.commit()
    await db_session.refresh(game)
    return game


# ============================================================================
# Coaching Feature Contract Test Fixtures
# ============================================================================


@pytest_asyncio.fixture
async def test_user(reset_db):
    """Create a test coach user with coach_pro_plus role."""
    import backend.security as security
    from backend.sql_app.database import get_db
    from backend.sql_app.models import RoleEnum, User

    async for db in get_db():
        user = User(
            id="test-coach-001",
            email="coach@test.com",
            hashed_password="test_hashed_password",  # noqa: S106
            role=RoleEnum.coach_pro_plus,
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        await db.commit()

        # Add to in-memory cache for in-memory DB tests
        security.add_in_memory_user(user)

        return user


@pytest_asyncio.fixture
async def test_player(reset_db, test_user):
    """Create a test player for coach notes."""
    from backend.sql_app.database import get_db
    from backend.sql_app.models import Player
    from backend import app

    async for db in get_db():
        player = Player(
            id=1,
            name="Test Player",
            country="Test Country",
            role="Batsman",
        )
        db.add(player)
        await db.commit()

        # Add to in-memory storage for in-memory DB tests
        app._in_memory_players[player.id] = player

        return player


@pytest_asyncio.fixture
async def test_video_session(reset_db, test_user):
    """Create a test video session for moment markers."""
    from backend.sql_app.database import get_db
    from backend.sql_app.models import OwnerTypeEnum, VideoSession, VideoSessionStatus
    from backend import app

    async for db in get_db():
        session = VideoSession(
            id="test-session-001",
            owner_type=OwnerTypeEnum.coach,
            owner_id=test_user.id,
            title="Test Video Session",
            player_ids=["player1", "player2"],
            status=VideoSessionStatus.uploaded,
            min_duration_seconds=300,
        )
        db.add(session)
        await db.commit()

        # Add to in-memory storage for in-memory DB tests
        app._in_memory_video_sessions[session.id] = session

        return session


@pytest_asyncio.fixture
async def other_user(reset_db):
    """Create another test user for ownership tests."""
    import backend.security as security
    from backend.sql_app.database import get_db
    from backend.sql_app.models import RoleEnum, User

    async for db in get_db():
        user = User(
            id="test-coach-002",
            email="coach2@test.com",
            hashed_password="test_hashed_password",  # noqa: S106
            role=RoleEnum.coach_pro_plus,
            is_active=True,
            is_superuser=False,
        )
        db.add(user)
        await db.commit()

        # Add to in-memory cache for in-memory DB tests
        security.add_in_memory_user(user)

        return user


@pytest_asyncio.fixture
async def auth_headers(test_user):
    """Generate auth headers for test_user."""
    from backend.security import create_access_token

    token = create_access_token(
        {"sub": test_user.id, "email": test_user.email, "role": test_user.role.value}
    )
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture
async def other_auth_headers(other_user):
    """Generate auth headers for other_user."""
    from backend.security import create_access_token

    token = create_access_token(
        {"sub": other_user.id, "email": other_user.email, "role": other_user.role.value}
    )
    return {"Authorization": f"Bearer {token}"}
