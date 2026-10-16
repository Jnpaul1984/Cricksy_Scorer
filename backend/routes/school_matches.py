"""Authenticated organization-scoped School match setup routes."""

from __future__ import annotations

from typing import Annotated, NoReturn

from backend.api.schemas.school_matches import (
    PracticeDelivery,
    PracticeInningsStart,
    PracticeMatchCreate,
    PracticeMatchCreateResponse,
    PracticeMatchStart,
    PracticeMatchStartResponse,
    PracticeOverStart,
    PracticeWorkflowRevision,
    PracticeWorkflowState,
    SchoolMatchCreate,
    SchoolMatchCreateResponse,
)
from backend.security import get_current_active_user
from backend.services import (
    organization_entitlement_service,
    organization_selection_plan_service,
    organization_service,
    practice_match_persistence_service,
    practice_match_setup_service,
    practice_match_workflow_service,
    school_match_service,
)
from backend.sql_app.database import get_db
from backend.sql_app.models import Game, PlayerProfile, User
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(prefix="/api/organizations", tags=["school-matches"])


def _service_error(
    exc: (
        organization_service.OrganizationServiceError
        | organization_entitlement_service.OrganizationCapabilityError
        | organization_selection_plan_service.OrganizationSelectionPlanServiceError
        | school_match_service.SchoolMatchServiceError
    ),
) -> NoReturn:
    if isinstance(exc, organization_entitlement_service.OrganizationCapabilityError):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Organization capability not enabled: {exc.capability}",
        ) from exc
    raise HTTPException(status_code=exc.status_code, detail=exc.detail) from exc


@router.post(
    "/{organization_id}/matches",
    response_model=SchoolMatchCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_school_match(
    organization_id: str,
    payload: SchoolMatchCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> SchoolMatchCreateResponse:
    try:
        game = await school_match_service.create_school_match(
            db,
            organization_id=organization_id,
            payload=payload,
            actor_user_id=current_user.id,
        )
    except (
        organization_service.OrganizationServiceError,
        organization_entitlement_service.OrganizationCapabilityError,
        organization_selection_plan_service.OrganizationSelectionPlanServiceError,
        school_match_service.SchoolMatchServiceError,
    ) as exc:
        _service_error(exc)

    return SchoolMatchCreateResponse(
        game_id=game.id,
        organization_id=organization_id,
        team_a_id=(
            str(game.team_a["school_source"]["team_id"])
            if isinstance(game.team_a.get("school_source"), dict)
            else None
        ),
        team_b_id=(
            str(game.team_b["school_source"]["team_id"])
            if isinstance(game.team_b.get("school_source"), dict)
            else None
        ),
        team_a_name=str(game.team_a["name"]),
        team_b_name=str(game.team_b["name"]),
        team_a_player_profile_ids=[
            str(player["id"])
            for player in game.team_a["players"]
            if player.get("player_profile_id") == player.get("id")
        ],
        team_b_player_profile_ids=[
            str(player["id"])
            for player in game.team_b["players"]
            if player.get("player_profile_id") == player.get("id")
        ],
    )


@router.post(
    "/{organization_id}/practice-matches",
    response_model=PracticeMatchCreateResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_private_practice_match(
    organization_id: str,
    payload: PracticeMatchCreate,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PracticeMatchCreateResponse:
    """Create one organization-private practice draft; no generic scoring route is enabled."""
    try:
        setup = await practice_match_setup_service.prepare_practice_match_setup(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            team_a=practice_match_setup_service.PracticeSideSelection(
                source_squad_id=payload.team_a.source_squad_id,
                participant_membership_ids=tuple(payload.team_a.participant_membership_ids),
                captain_membership_id=payload.team_a.captain_membership_id,
                wicketkeeper_membership_id=payload.team_a.wicketkeeper_membership_id,
            ),
            team_b=practice_match_setup_service.PracticeSideSelection(
                source_squad_id=payload.team_b.source_squad_id,
                participant_membership_ids=tuple(payload.team_b.participant_membership_ids),
                captain_membership_id=payload.team_b.captain_membership_id,
                wicketkeeper_membership_id=payload.team_b.wicketkeeper_membership_id,
            ),
            overs=payload.overs,
        )
        game = await practice_match_persistence_service.persist_practice_match_setup(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            setup=setup,
        )
    except (
        organization_service.OrganizationServiceError,
        organization_entitlement_service.OrganizationCapabilityError,
        school_match_service.SchoolMatchServiceError,
    ) as exc:
        _service_error(exc)
    return PracticeMatchCreateResponse(
        game_id=game.id,
        organization_id=organization_id,
        match_purpose="practice",
        status="not_started",
        publication_state="private",
    )


@router.post(
    "/{organization_id}/practice-matches/{game_id}/start",
    response_model=PracticeMatchStartResponse,
)
async def start_private_practice_match(
    organization_id: str,
    game_id: str,
    payload: PracticeMatchStart,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PracticeMatchStartResponse:
    """Set immutable side-key start context for one private practice draft."""
    try:
        game = await practice_match_persistence_service.start_private_practice_match(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            game_id=game_id,
            first_batting_side=payload.first_batting_side,
        )
    except (
        organization_service.OrganizationServiceError,
        organization_entitlement_service.OrganizationCapabilityError,
        school_match_service.SchoolMatchServiceError,
    ) as exc:
        _service_error(exc)
    practice_start_context = game.practice_start_context
    if practice_start_context is None:
        raise HTTPException(status_code=409, detail="Practice match start context was not persisted")
    return PracticeMatchStartResponse(
        game_id=game.id,
        status="started",
        practice_start_context=practice_start_context,
    )


async def _practice_workflow_state(
    db: AsyncSession, game: Game, organization_id: str, snapshot: dict[str, object]
) -> PracticeWorkflowState:
    """Build a private state response with labels resolved from frozen profile IDs.

    The persisted side snapshot deliberately contains only immutable IDs.  The
    caller has already authorized the organization through the workflow
    service, so this bounded lookup may expose only labels for those frozen
    IDs.  A deleted or otherwise unavailable profile remains scoreable by ID
    and is rendered as a deterministic unavailable participant instead.
    """
    practice_game = game
    side_players = [
        player
        for team in (practice_game.team_a, practice_game.team_b)
        if isinstance(team, dict)
        for player in team.get("players", [])
        if isinstance(player, dict) and isinstance(player.get("id"), str)
    ]
    frozen_ids = {player["id"] for player in side_players}
    names = {
        player_id: player_name.strip()
        for player_id, player_name in (
            await db.execute(
                select(PlayerProfile.player_id, PlayerProfile.player_name).where(
                    PlayerProfile.player_id.in_(frozen_ids)
                )
            )
        ).all()
        if isinstance(player_name, str) and player_name.strip()
    }

    def frozen_side(team: object) -> list[dict[str, str | None]]:
        players = team.get("players", []) if isinstance(team, dict) else []
        return [
            {
                "id": str(player["id"]),
                "label": names.get(str(player["id"]), "Unavailable participant"),
            }
            for player in players if isinstance(player, dict) and player.get("id") is not None
        ]
    return PracticeWorkflowState(
        game_id=str(practice_game.id),
        organization_id=organization_id,
        match_purpose="practice",
        publication_state="private",
        status=str(practice_game.status.value),
        revision=practice_game.practice_workflow_revision,
        practice_start_context=practice_game.practice_start_context,
        frozen_sides={"team_a": frozen_side(practice_game.team_a), "team_b": frozen_side(practice_game.team_b)},
        snapshot=snapshot,
    )


@router.get(
    "/{organization_id}/practice-matches/{game_id}", response_model=PracticeWorkflowState
)
async def get_private_practice_match(
    organization_id: str,
    game_id: str,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PracticeWorkflowState:
    try:
        game, snapshot = await practice_match_workflow_service.read_practice_workflow(
            db, organization_id=organization_id, actor_user_id=current_user.id, game_id=game_id
        )
    except (
        organization_service.OrganizationServiceError,
        organization_entitlement_service.OrganizationCapabilityError,
        school_match_service.SchoolMatchServiceError,
    ) as exc:
        _service_error(exc)
    return await _practice_workflow_state(db, game, organization_id, snapshot)


@router.post(
    "/{organization_id}/practice-matches/{game_id}/innings/start",
    response_model=PracticeWorkflowState,
)
async def start_private_practice_innings(
    organization_id: str,
    game_id: str,
    payload: PracticeInningsStart,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PracticeWorkflowState:
    try:
        game, snapshot = await practice_match_workflow_service.start_practice_innings(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            game_id=game_id,
            expected_revision=payload.expected_revision,
            striker_id=payload.striker_id,
            non_striker_id=payload.non_striker_id,
            opening_bowler_id=payload.opening_bowler_id,
        )
    except (
        organization_service.OrganizationServiceError,
        organization_entitlement_service.OrganizationCapabilityError,
        school_match_service.SchoolMatchServiceError,
    ) as exc:
        _service_error(exc)
    return await _practice_workflow_state(db, game, organization_id, snapshot)


@router.post(
    "/{organization_id}/practice-matches/{game_id}/overs/start",
    response_model=PracticeWorkflowState,
)
async def start_private_practice_over(
    organization_id: str,
    game_id: str,
    payload: PracticeOverStart,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PracticeWorkflowState:
    try:
        game, snapshot = await practice_match_workflow_service.start_practice_over(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            game_id=game_id,
            expected_revision=payload.expected_revision,
            bowler_id=payload.bowler_id,
        )
    except (
        organization_service.OrganizationServiceError,
        organization_entitlement_service.OrganizationCapabilityError,
        school_match_service.SchoolMatchServiceError,
    ) as exc:
        _service_error(exc)
    return await _practice_workflow_state(db, game, organization_id, snapshot)


@router.post(
    "/{organization_id}/practice-matches/{game_id}/deliveries",
    response_model=PracticeWorkflowState,
)
async def score_private_practice_delivery(
    organization_id: str,
    game_id: str,
    payload: PracticeDelivery,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PracticeWorkflowState:
    try:
        game, snapshot = await practice_match_workflow_service.score_practice_delivery(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            game_id=game_id,
            expected_revision=payload.expected_revision,
            striker_id=payload.striker_id,
            non_striker_id=payload.non_striker_id,
            bowler_id=payload.bowler_id,
            runs_scored=payload.runs_scored,
            extra=payload.extra,
            is_wicket=payload.is_wicket,
            dismissal_type=payload.dismissal_type,
            dismissed_player_id=payload.dismissed_player_id,
        )
    except (
        organization_service.OrganizationServiceError,
        organization_entitlement_service.OrganizationCapabilityError,
        school_match_service.SchoolMatchServiceError,
    ) as exc:
        _service_error(exc)
    return await _practice_workflow_state(db, game, organization_id, snapshot)


@router.post(
    "/{organization_id}/practice-matches/{game_id}/undo-last",
    response_model=PracticeWorkflowState,
)
async def undo_last_private_practice_delivery(
    organization_id: str,
    game_id: str,
    payload: PracticeWorkflowRevision,
    current_user: Annotated[User, Depends(get_current_active_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
) -> PracticeWorkflowState:
    try:
        game, snapshot = await practice_match_workflow_service.undo_last_practice_delivery(
            db,
            organization_id=organization_id,
            actor_user_id=current_user.id,
            game_id=game_id,
            expected_revision=payload.expected_revision,
        )
    except (
        organization_service.OrganizationServiceError,
        organization_entitlement_service.OrganizationCapabilityError,
        school_match_service.SchoolMatchServiceError,
    ) as exc:
        _service_error(exc)
    return await _practice_workflow_state(db, game, organization_id, snapshot)
