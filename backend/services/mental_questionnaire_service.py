from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import desc, select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.sql_app.models import (
    MentalQuestionnaireAnswer,
    MentalQuestionnaireCategory,
    MentalQuestionnaireCategoryScore,
    MentalQuestionnaireQuestion,
    MentalQuestionnaireSession,
    PlayerProfile,
)
from backend.sql_app.schemas import MentalQuestionnaireAnswerInput

_DEFAULT_QUESTIONS: list[tuple[MentalQuestionnaireCategory, str, int]] = [
    (
        MentalQuestionnaireCategory.mental_toughness,
        "I stay focused and bounce back quickly after setbacks in training or matches.",
        1,
    ),
    (
        MentalQuestionnaireCategory.mental_toughness,
        "I keep my effort level strong even when situations become difficult.",
        2,
    ),
    (
        MentalQuestionnaireCategory.pressure_handling,
        "I stay calm and execute my skills when the game pressure rises.",
        1,
    ),
    (
        MentalQuestionnaireCategory.pressure_handling,
        "I can improve under pressure by sticking to my process and routines.",
        2,
    ),
    (
        MentalQuestionnaireCategory.game_awareness,
        "I read match situations well and adjust decisions for the team.",
        1,
    ),
    (
        MentalQuestionnaireCategory.game_awareness,
        "I understand field settings, bowler plans, and scoring options clearly.",
        2,
    ),
    (
        MentalQuestionnaireCategory.training_habits,
        "I follow training plans with discipline and complete key practice tasks.",
        1,
    ),
    (
        MentalQuestionnaireCategory.training_habits,
        "I prepare consistently with recovery, reflection, and game-readiness habits.",
        2,
    ),
]


def _summary_text(overall_average: float) -> str:
    if overall_average >= 4.2:
        return "Overall mental profile shows clear strengths with strong habits and focused coaching continuity."
    if overall_average >= 3.5:
        return "Overall mental profile is progressing well with strengths and clear growth opportunities."
    if overall_average >= 2.8:
        return "Overall mental profile shows balanced progress with specific development areas for coaching focus."
    return "Overall mental profile highlights important development areas and coaching focus opportunities."


def _strength_line(category: str, average_score: float) -> str:
    return f"{category} is a strength (average {average_score:.2f}/5)."


def _development_line(category: str, average_score: float) -> str:
    return (
        f"{category} is a development area and growth opportunity "
        f"(average {average_score:.2f}/5) for improvement focus."
    )


def _build_profile(
    *,
    category_scores: list[tuple[str, float]],
) -> tuple[float, str, list[str], list[str]]:
    overall_average = round(mean(score for _, score in category_scores), 2)
    ordered_desc = sorted(category_scores, key=lambda item: (-item[1], item[0]))
    ordered_asc = sorted(category_scores, key=lambda item: (item[1], item[0]))
    strengths = [_strength_line(cat, score) for cat, score in ordered_desc[:2]]
    development_areas = [_development_line(cat, score) for cat, score in ordered_asc[:2]]
    return overall_average, _summary_text(overall_average), strengths, development_areas


async def ensure_default_questions(db: AsyncSession) -> None:
    existing = await db.execute(select(MentalQuestionnaireQuestion.id).limit(1))
    if existing.scalar_one_or_none() is not None:
        return

    for category, question_text, display_order in _DEFAULT_QUESTIONS:
        db.add(
            MentalQuestionnaireQuestion(
                category=category,
                question_text=question_text,
                display_order=display_order,
                is_active=True,
            )
        )
    await db.commit()


async def list_active_questions(db: AsyncSession) -> list[MentalQuestionnaireQuestion]:
    await ensure_default_questions(db)
    result = await db.execute(
        select(MentalQuestionnaireQuestion)
        .where(MentalQuestionnaireQuestion.is_active.is_(True))
        .order_by(MentalQuestionnaireQuestion.category, MentalQuestionnaireQuestion.display_order)
    )
    return list(result.scalars().all())


async def submit_questionnaire_response(
    *,
    db: AsyncSession,
    player_id: str,
    submitted_by_user_id: str,
    answers: list[MentalQuestionnaireAnswerInput],
) -> dict[str, Any]:
    player = await db.get(PlayerProfile, player_id)
    if player is None:
        raise HTTPException(status_code=404, detail="Player profile not found")

    questions = await list_active_questions(db)
    active_question_ids = {question.id for question in questions}
    provided_question_ids = [answer.question_id for answer in answers]

    if len(provided_question_ids) != len(set(provided_question_ids)):
        raise HTTPException(status_code=400, detail="Duplicate question answers are not allowed")

    if set(provided_question_ids) != active_question_ids:
        raise HTTPException(
            status_code=400,
            detail="All active questionnaire questions must be answered exactly once",
        )

    questions_by_id = {question.id: question for question in questions}
    category_map: dict[str, list[int]] = defaultdict(list)
    for answer in answers:
        question = questions_by_id.get(answer.question_id)
        if question is None:
            raise HTTPException(status_code=400, detail="Invalid question_id in answers")
        category_map[question.category.value].append(answer.score)

    category_scores = [
        (category, round(mean(scores), 2)) for category, scores in sorted(category_map.items())
    ]
    overall_average, overall_summary, strengths, development_areas = _build_profile(
        category_scores=category_scores
    )

    session = MentalQuestionnaireSession(
        player_id=player_id,
        submitted_by_user_id=submitted_by_user_id,
        overall_average_score=overall_average,
        overall_summary=overall_summary,
        strengths=strengths,
        development_areas=development_areas,
    )
    db.add(session)
    await db.flush()

    for answer in answers:
        db.add(
            MentalQuestionnaireAnswer(
                session_id=session.id,
                question_id=answer.question_id,
                score=answer.score,
            )
        )
    for category, average_score in category_scores:
        db.add(
            MentalQuestionnaireCategoryScore(
                session_id=session.id,
                category=MentalQuestionnaireCategory(category),
                average_score=average_score,
            )
        )

    await db.commit()
    await db.refresh(session)

    return {
        "session_id": session.id,
        "player_id": session.player_id,
        "submitted_by_user_id": session.submitted_by_user_id,
        "overall_average_score": session.overall_average_score,
        "overall_summary": session.overall_summary,
        "strengths": session.strengths,
        "development_areas": session.development_areas,
        "category_scores": [
            {"category": category, "average_score": average_score}
            for category, average_score in category_scores
        ],
        "created_at": session.created_at,
    }


async def get_player_response_history(db: AsyncSession, player_id: str) -> list[dict[str, Any]]:
    sessions_result = await db.execute(
        select(MentalQuestionnaireSession)
        .where(MentalQuestionnaireSession.player_id == player_id)
        .order_by(desc(MentalQuestionnaireSession.created_at))
    )
    sessions = list(sessions_result.scalars().all())

    history: list[dict[str, Any]] = []
    for session in sessions:
        score_result = await db.execute(
            select(MentalQuestionnaireCategoryScore)
            .where(MentalQuestionnaireCategoryScore.session_id == session.id)
            .order_by(MentalQuestionnaireCategoryScore.category)
        )
        category_scores = [
            {"category": score.category.value, "average_score": score.average_score}
            for score in score_result.scalars().all()
        ]
        history.append(
            {
                "session_id": session.id,
                "player_id": session.player_id,
                "submitted_by_user_id": session.submitted_by_user_id,
                "overall_average_score": session.overall_average_score,
                "overall_summary": session.overall_summary,
                "strengths": session.strengths,
                "development_areas": session.development_areas,
                "category_scores": category_scores,
                "created_at": session.created_at,
            }
        )
    return history
