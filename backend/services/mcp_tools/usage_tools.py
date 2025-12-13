from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from backend.security import require_admin_or_analyst
from backend.services.mcp_tools.util import audit_log

router = APIRouter()

class UsageSummaryIn(BaseModel):
    since: str
    until: str
    groupBy: str
class UsageSummaryOut(BaseModel):
    totals: Dict[str, Any]
    byFeature: List[Dict[str, Any]] = []
    byUser: List[Dict[str, Any]] = []
    byOrg: List[Dict[str, Any]] = []

@router.post("/usage.summary", response_model=UsageSummaryOut)
async def usage_summary(
    body: UsageSummaryIn,
    user=Depends(require_admin_or_analyst)
):
    # TODO: Query usage_log
    result = UsageSummaryOut(totals={}, byFeature=[], byUser=[], byOrg=[])
    await audit_log("usage.summary", user, body)
    return result
