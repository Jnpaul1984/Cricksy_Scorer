from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from sqlalchemy.orm import declarative_base

# The database URL tells SQLAlchemy where our database is located.
SQLALCHEMY_DATABASE_URL = "postgresql+asyncpg://postgres:RubyAnita2018@localhost:5555/cricksy_scorer"

# The engine is the main entry point for SQLAlchemy to talk to the DB.
engine = create_async_engine(SQLALCHEMY_DATABASE_URL)

# A session is what we use to actually execute queries.
SessionLocal = async_sessionmaker(autocommit=False, autoflush=False, bind=engine)

# This is a base class that our table models will inherit from.
Base = declarative_base()
