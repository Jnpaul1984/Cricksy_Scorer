from fastapi import APIRouter, Depends
from pydantic import BaseModel
from backend.security import get_current_active_user
from backend.services.mcp_tools.util import audit_log

router = APIRouter()


# ------------------- Schemas -------------------
class FeedbackListIn(BaseModel):
    since: str
    until: str
    limit: int = 100
    offset: int = 0


class FeedbackItem(BaseModel):
    id: str
    submitted_at: str
    user_id: str
    page: str
    type: str
    severity: str
    text: str


class FeedbackListOut(BaseModel):
    items: list[FeedbackItem]


class FeedbackStatsIn(BaseModel):
    since: str
    until: str


class FeedbackStatsOut(BaseModel):
    countsByType: dict
    countsByPage: dict
    countsBySeverity: dict


# ------------------- Endpoints -------------------
@router.post("/feedback.list", response_model=FeedbackListOut)
async def feedback_list(body: FeedbackListIn, user=Depends(get_current_active_user)):
    # TODO: Query DB for feedback_submissions
    result = FeedbackListOut(items=[])
    await audit_log("feedback.list", user, body)
    return result


@router.post("/feedback.stats", response_model=FeedbackStatsOut)
async def feedback_stats(body: FeedbackStatsIn, user=Depends(get_current_active_user)):
    # TODO: Query DB for feedback stats
    result = FeedbackStatsOut(countsByType={}, countsByPage={}, countsBySeverity={})
    await audit_log("feedback.stats", user, body)
    return result
