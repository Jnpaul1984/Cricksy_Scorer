from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import Any
from backend.security import get_current_active_user
from backend.services.mcp_tools.util import audit_log

router = APIRouter()


class UsageSummaryIn(BaseModel):
    since: str
    until: str
    groupBy: str


class UsageSummaryOut(BaseModel):
    totals: dict[str, Any]
    byFeature: list[dict[str, Any]] = []
    byUser: list[dict[str, Any]] = []
    byOrg: list[dict[str, Any]] = []


@router.post("/usage.summary", response_model=UsageSummaryOut)
async def usage_summary(body: UsageSummaryIn, user=Depends(get_current_active_user)):
    # TODO: Query usage_log
    result = UsageSummaryOut(totals={}, byFeature=[], byUser=[], byOrg=[])
    await audit_log("usage.summary", user, body)
    return result
