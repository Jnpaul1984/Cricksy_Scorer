from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.security import get_current_active_user
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
    user_id: str | None


class ErrorsRecentOut(BaseModel):
    items: list[ErrorItem]


@router.post("/errors.recent", response_model=ErrorsRecentOut)
async def errors_recent(body: ErrorsRecentIn, user=Depends(get_current_active_user)):
    # TODO: Query errors table
    result = ErrorsRecentOut(items=[])
    await audit_log("errors.recent", user, body)
    return result
