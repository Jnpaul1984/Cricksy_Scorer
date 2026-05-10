from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from backend import security
from backend.services.mental_questionnaire_service import (
    get_player_response_history,
    list_active_questions,
    submit_questionnaire_response,
)
from backend.sql_app.database import get_db
from backend.sql_app.models import RoleEnum, User
from backend.sql_app.schemas import (
    MentalQuestionnaireCategoryTemplateRead,
    MentalQuestionnaireProfileSummaryRead,
    MentalQuestionnaireSubmitRequest,
    MentalQuestionnaireTemplateRead,
)

router = APIRouter(prefix="/api/mental-questionnaires", tags=["mental_questionnaires"])

_ALLOWED_ROLES = {RoleEnum.coach_pro, RoleEnum.coach_pro_plus, RoleEnum.org_pro}


def _ensure_coach_or_admin_access(user: User) -> None:
    if user.is_superuser:
        return
    if user.role not in _ALLOWED_ROLES:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")


@router.get("/template", response_model=MentalQuestionnaireTemplateRead)
async def get_template(
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> MentalQuestionnaireTemplateRead:
    _ensure_coach_or_admin_access(current_user)
    questions = await list_active_questions(db)

    grouped: dict[str, list] = {}
    for question in questions:
        grouped.setdefault(question.category.value, []).append(question)

    categories = [
        MentalQuestionnaireCategoryTemplateRead(category=category, questions=items)
        for category, items in grouped.items()
    ]
    return MentalQuestionnaireTemplateRead(categories=categories)


@router.post(
    "/players/{player_id}/responses",
    response_model=MentalQuestionnaireProfileSummaryRead,
)
async def submit_response(
    player_id: str,
    payload: MentalQuestionnaireSubmitRequest,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> MentalQuestionnaireProfileSummaryRead:
    _ensure_coach_or_admin_access(current_user)
    summary = await submit_questionnaire_response(
        db=db,
        player_id=player_id,
        submitted_by_user_id=current_user.id,
        answers=payload.answers,
    )
    return MentalQuestionnaireProfileSummaryRead.model_validate(summary)


@router.get(
    "/players/{player_id}/profile/latest",
    response_model=MentalQuestionnaireProfileSummaryRead,
)
async def get_latest_profile(
    player_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> MentalQuestionnaireProfileSummaryRead:
    _ensure_coach_or_admin_access(current_user)
    history = await get_player_response_history(db, player_id)
    if not history:
        raise HTTPException(status_code=404, detail="No mental questionnaire responses found")
    return MentalQuestionnaireProfileSummaryRead.model_validate(history[0])


@router.get(
    "/players/{player_id}/responses",
    response_model=list[MentalQuestionnaireProfileSummaryRead],
)
async def get_response_history(
    player_id: str,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> list[MentalQuestionnaireProfileSummaryRead]:
    _ensure_coach_or_admin_access(current_user)
    history = await get_player_response_history(db, player_id)
    return [MentalQuestionnaireProfileSummaryRead.model_validate(item) for item in history]
