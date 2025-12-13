"""
MCP Domain Server for Cricksy Scorer

Exposes tool contracts as HTTP endpoints for agent/LLM use.
Modules: db_tools, usage_tools, error_tools, analytics_tools
"""

from fastapi import FastAPI
from backend.services.mcp_tools import db_tools, usage_tools, error_tools, analytics_tools, system_tools, security_tools

app = FastAPI(title="Cricksy MCP Tool Server")

# Mount tool routers
app.include_router(db_tools.router, prefix="/tools/db")
app.include_router(usage_tools.router, prefix="/tools/usage")
app.include_router(error_tools.router, prefix="/tools/errors")
app.include_router(analytics_tools.router, prefix="/tools/analytics")
app.include_router(system_tools.router, prefix="/tools/system")
app.include_router(security_tools.router, prefix="/tools/security")
