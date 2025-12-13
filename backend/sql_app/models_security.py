"""
SQLAlchemy models for security logging (request_logs, auth_events, rate_limit_events)
"""
import datetime as dt
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from backend.sql_app.database import Base

class RequestLog(Base):
    __tablename__ = "request_logs"
    id = Column(Integer, primary_key=True)
    ts = Column(Integer, nullable=False, index=True)  # epoch seconds
    method = Column(String(10), nullable=False)
    path = Column(String(200), nullable=False)
    status = Column(Integer, nullable=False)
    ip = Column(String(64), nullable=True, index=True)
    userAgent = Column(String(200), nullable=True)
    userId = Column(String(64), nullable=True, index=True)
    latencyMs = Column(Integer, nullable=True)

class AuthEvent(Base):
    __tablename__ = "auth_events"
    id = Column(Integer, primary_key=True)
    ts = Column(Integer, nullable=False, index=True)
    email = Column(String(128), nullable=True, index=True)
    userId = Column(String(64), nullable=True, index=True)
    ip = Column(String(64), nullable=True, index=True)
    userAgent = Column(String(200), nullable=True)
    eventType = Column(String(32), nullable=False)
    success = Column(Boolean, nullable=False)

class RateLimitEvent(Base):
    __tablename__ = "rate_limit_events"
    id = Column(Integer, primary_key=True)
    ts = Column(Integer, nullable=False, index=True)
    ip = Column(String(64), nullable=True, index=True)
    userId = Column(String(64), nullable=True, index=True)
    key = Column(String(64), nullable=False)
    limitName = Column(String(64), nullable=False)
