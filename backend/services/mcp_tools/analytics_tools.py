from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Dict, Any
from backend.security import require_admin_or_analyst
from backend.services.mcp_tools.util import audit_log

router = APIRouter()

class PageviewsIn(BaseModel):
    since: str
    until: str
    groupBy: str
class PageviewsOut(BaseModel):
    totals: int
    byRoute: List[Dict[str, Any]]

@router.post("/events.pageviews", response_model=PageviewsOut)
async def events_pageviews(
    body: PageviewsIn,
    user=Depends(require_admin_or_analyst)
):
    # TODO: Query pageview events
    result = PageviewsOut(totals=0, byRoute=[])
    await audit_log("events.pageviews", user, body)
    return result
