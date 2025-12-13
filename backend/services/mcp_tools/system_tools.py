from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.security import get_current_active_user
from backend.services.mcp_tools.util import audit_log
import os

router = APIRouter()


class ConfigRuntimeOut(BaseModel):
    env: str
    version: str
    commit: str
    apiBaseUrl: str


@router.post("/config.runtime", response_model=ConfigRuntimeOut)
async def config_runtime(user=Depends(get_current_active_user)):
    # TODO: Fill with real config
    result = ConfigRuntimeOut(
        env=os.getenv("ENV", "dev"),
        version=os.getenv("VERSION", "v0.0.0"),
        commit=os.getenv("COMMIT", "dev"),
        apiBaseUrl=os.getenv("API_BASE_URL", "http://localhost:8000"),
    )
    await audit_log("config.runtime", user, {})
    return result


class HealthCheckOut(BaseModel):
    backendOk: bool
    dbOk: bool
    queueOk: bool
    lastDeploy: str


@router.post("/health.check", response_model=HealthCheckOut)
async def health_check(user=Depends(get_current_active_user)):
    # TODO: Fill with real health info
    result = HealthCheckOut(
        backendOk=True, dbOk=True, queueOk=True, lastDeploy="2025-12-12T10:00:00Z"
    )
    await audit_log("health.check", user, {})
    return result
