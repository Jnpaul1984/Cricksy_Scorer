from fastapi import APIRouter, Depends
from pydantic import BaseModel
from typing import List, Optional
from backend.security import require_admin_or_analyst
from backend.services.mcp_tools.util import audit_log

router = APIRouter()

class ErrorsRecentIn(BaseModel):
    since: str
    until: str
    limit: int = 100
class ErrorItem(BaseModel):
    id: str
    timestamp: str
    endpoint: str
    status: int
    stack: str
    user_id: Optional[str]
class ErrorsRecentOut(BaseModel):
    items: List[ErrorItem]

@router.post("/errors.recent", response_model=ErrorsRecentOut)
async def errors_recent(
    body: ErrorsRecentIn,
    user=Depends(require_admin_or_analyst)
):
    # TODO: Query errors table
    result = ErrorsRecentOut(items=[])
    await audit_log("errors.recent", user, body)
    return result
