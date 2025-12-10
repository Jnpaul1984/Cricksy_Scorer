from __future__ import annotations

# ruff: noqa: E402
import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

# Ensure the repository root is on sys.path so "import backend.*" works even when
# the current working directory is the backend folder (common in containers).
ROOT_DIR = Path(__file__).resolve().parents[2]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from alembic import context
from backend.sql_app.models import Base
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import create_async_engine

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
# This line sets up loggers basically.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# add your model's MetaData object here
# for 'autogenerate' support
# from myapp import mymodel
# target_metadata = mymodel.Base.metadata
target_metadata = Base.metadata

# other values from the config, defined by the needs of env.py,
# can be acquired:
# my_important_option = config.get_main_option("my_important_option")
# ... etc.


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode.

    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well.  By skipping the Engine creation
    we don't even need a DBAPI to be available.

    Calls to context.execute() here emit the given string to the
    script output.

    """
    # Prefer DATABASE_URL env if provided, else fall back to alembic.ini
    url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    """Helper function to run the migrations."""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run migrations in 'online' mode.

    In this scenario we need to create an Engine
    and associate a connection with the context.

    """
    # Prefer DATABASE_URL env if provided, else fall back to alembic.ini
    url = os.getenv("DATABASE_URL", config.get_main_option("sqlalchemy.url"))
    # Create an async engine from the resolved URL
    connectable = create_async_engine(
        url,
        poolclass=pool.NullPool,
    )

    # Connect to the database asynchronously
    async with connectable.connect() as connection:
        # Run the migrations within the connection's context
        await connection.run_sync(do_run_migrations)

    # Dispose of the engine
    await connectable.dispose()


# At the end of the file, find the existing call to run_migrations_online()
# and wrap it in asyncio.run()
if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
