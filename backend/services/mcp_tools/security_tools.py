"""
Read-only security tools for MCP server: CyberSecurityWatcherAgent
"""
from datetime import datetime
from typing import Literal, Optional
from fastapi import APIRouter, Query
from pydantic import BaseModel, Field

router = APIRouter()

# --- Input/Output Schemas ---

class AuthFailuresInput(BaseModel):
    since: datetime
    until: datetime
    groupBy: Literal["ip", "email", "userAgent"] = Field(...)
    limit: int = Field(ge=1, le=1000, default=100)

class AuthFailureItem(BaseModel):
    key: str
    count: int
    lastSeenAt: datetime

class AuthFailuresOutput(BaseModel):
    items: list[AuthFailureItem]

class SuspiciousIPsInput(BaseModel):
    since: datetime
    until: datetime
    minRequests: int = Field(ge=1, le=1000, default=10)
    limit: int = Field(ge=1, le=1000, default=100)

class SuspiciousIPItem(BaseModel):
    ip: str
    requests: int
    pathsTop: list[str]
    userAgentsTop: list[str]
    lastSeenAt: datetime

class SuspiciousIPsOutput(BaseModel):
    items: list[SuspiciousIPItem]

class RateLimitHitsInput(BaseModel):
    since: datetime
    until: datetime
    groupBy: Literal["ip", "userId"] = Field(...)
    limit: int = Field(ge=1, le=1000, default=100)

class RateLimitHitItem(BaseModel):
    key: str
    count: int
    lastSeenAt: datetime

class RateLimitHitsOutput(BaseModel):
    items: list[RateLimitHitItem]

class AdminRouteAttemptsInput(BaseModel):
    since: datetime
    until: datetime
    limit: int = Field(ge=1, le=1000, default=100)

class AdminRouteAttemptItem(BaseModel):
    ip: str
    path: str
    method: str
    status: int
    userAgent: str
    ts: datetime

class AdminRouteAttemptsOutput(BaseModel):
    items: list[AdminRouteAttemptItem]

class Http4xx5xxSummaryInput(BaseModel):
    since: datetime
    until: datetime
    groupBy: Literal["path", "ip"] = Field(...)
    limit: int = Field(ge=1, le=1000, default=100)

class Http4xx5xxSummaryItem(BaseModel):
    key: str
    count4xx: int
    count5xx: int
    sampleStatuses: list[int]
    lastSeenAt: datetime

class Http4xx5xxSummaryOutput(BaseModel):
    items: list[Http4xx5xxSummaryItem]

# --- Tool Endpoints (stub: TODO wire to DB) ---

@router.post("/security/auth_failures", response_model=AuthFailuresOutput)
def auth_failures(input: AuthFailuresInput):
    """Group failed auth events by ip/email/userAgent."""
    # TODO: Query auth_events table
    return AuthFailuresOutput(items=[])

@router.post("/security/suspicious_ips", response_model=SuspiciousIPsOutput)
def suspicious_ips(input: SuspiciousIPsInput):
    """IPs with high request volume."""
    # TODO: Query request_logs table
    return SuspiciousIPsOutput(items=[])

@router.post("/security/rate_limit_hits", response_model=RateLimitHitsOutput)
def rate_limit_hits(input: RateLimitHitsInput):
    """Group rate limit events by ip/userId."""
    # TODO: Query rate_limit_events table
    return RateLimitHitsOutput(items=[])

@router.post("/security/admin_route_attempts", response_model=AdminRouteAttemptsOutput)
def admin_route_attempts(input: AdminRouteAttemptsInput):
    """Attempts to access admin routes."""
    # TODO: Query request_logs table for /admin paths
    return AdminRouteAttemptsOutput(items=[])

@router.post("/security/http_4xx_5xx_summary", response_model=Http4xx5xxSummaryOutput)
def http_4xx_5xx_summary(input: Http4xx5xxSummaryInput):
    """Summarize 4xx/5xx errors by path/ip."""
    # TODO: Query request_logs table
    return Http4xx5xxSummaryOutput(items=[])
