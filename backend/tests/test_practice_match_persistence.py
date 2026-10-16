from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from backend.api.schemas.organizations import OrganizationCreate
from backend.api.schemas.school_matches import PracticeMatchCreate, PracticeMatchSideSelection
from backend.routes.school_matches import create_private_practice_match
from backend.services import organization_service
from backend.services.practice_match_persistence_service import persist_practice_match_setup
from backend.services.practice_match_setup_service import (
    PracticeSideSelection,
    prepare_practice_match_setup,
)
from backend.sql_app.database import SessionLocal
from backend.sql_app.models import (
    Game,
    OrganizationMembership,
    PlayerProfile,
    SchoolPlayerMembership,
    SchoolTeamPlayerMembership,
    Team,
    User,
)


async def _side(
    session: object, *, organization_id: str, owner_id: str, prefix: str, player_count: int = 2
) -> PracticeSideSelection:
    squad_id = str(uuid.uuid4())
    session.add(  # type: ignore[attr-defined]
        Team(
            id=squad_id,
            organization_id=organization_id,
            owner_user_id=owner_id,
            name=f"{prefix} squad",
            status="active",
            players=[],
            competitions=[],
        )
    )
    ids: list[str] = []
    for index in range(player_count):
        profile_id, membership_id, team_membership_id = (
            str(uuid.uuid4()),
            str(uuid.uuid4()),
            str(uuid.uuid4()),
        )
        session.add(PlayerProfile(player_id=profile_id, player_name=f"{prefix}-{index}"))  # type: ignore[attr-defined]
        session.add(  # type: ignore[attr-defined]
            SchoolPlayerMembership(
                id=membership_id,
                organization_id=organization_id,
                player_profile_id=profile_id,
                status="active",
                created_by_user_id=owner_id,
            )
        )
        session.add(  # type: ignore[attr-defined]
            SchoolTeamPlayerMembership(
                id=team_membership_id,
                organization_id=organization_id,
                team_id=squad_id,
                school_player_membership_id=membership_id,
                status="active",
                created_by_user_id=owner_id,
            )
        )
        ids.append(team_membership_id)
    await session.commit()  # type: ignore[attr-defined]
    return PracticeSideSelection(
        source_squad_id=squad_id,
        participant_membership_ids=tuple(ids),
        captain_membership_id=ids[0],
        wicketkeeper_membership_id=ids[1],
    )


async def _prepared_setup(organization_type: str = "school") -> tuple[str, str, object]:
    async with SessionLocal() as session:
        owner = User(
            id=str(uuid.uuid4()),
            email=f"practice-persist-{organization_type}@example.com",
            hashed_password="test-only",
        )
        session.add(owner)
        await session.commit()
        organization, _ = await organization_service.create_organization(
            session,
            payload=OrganizationCreate(name=f"Persist {organization_type}", organization_type=organization_type),
            actor=owner,
        )
        team_a = await _side(session, organization_id=organization.id, owner_id=owner.id, prefix="A")
        team_b = await _side(session, organization_id=organization.id, owner_id=owner.id, prefix="B")
        setup = await prepare_practice_match_setup(
            session,
            organization_id=organization.id,
            actor_user_id=owner.id,
            team_a=team_a,
            team_b=team_b,
        )
        return organization.id, owner.id, setup


@pytest.mark.parametrize("organization_type", ["school", "club"])
async def test_persistence_creates_private_unstarted_practice_draft(
    organization_type: str,
) -> None:
    organization_id, owner_id, setup = await _prepared_setup(organization_type)
    async with SessionLocal() as session:
        game = await persist_practice_match_setup(
            session, organization_id=organization_id, actor_user_id=owner_id, setup=setup
        )
        assert game.match_purpose == "practice"
        assert game.status.value == "not_started"
        assert game.publication_state == "private"
        assert game.created_by_user_id == owner_id
        assert game.team_a["school_source"]["organization_id"] == organization_id
        assert game.team_b["school_source"]["organization_id"] == organization_id
        assert game.match_rules is not None
        assert (
            game.match_rules["sides"]["team_a"]["source_squad_id"]
            == game.team_a["school_source"]["team_id"]
        )


async def test_persistence_reauthorizes_disabled_and_unrelated_memberships() -> None:
    organization_id, owner_id, setup = await _prepared_setup()
    async with SessionLocal() as session:
        membership = await session.scalar(
            select(OrganizationMembership).where(
                OrganizationMembership.organization_id == organization_id,
                OrganizationMembership.user_id == owner_id,
            )
        )
        assert membership is not None
        membership.status = "disabled"
        await session.commit()
        with pytest.raises(organization_service.OrganizationServiceError):
            await persist_practice_match_setup(
                session, organization_id=organization_id, actor_user_id=owner_id, setup=setup
            )
    async with SessionLocal() as session:
        outsider = User(
            id=str(uuid.uuid4()), email="practice-outsider@example.com", hashed_password="test-only"
        )
        session.add(outsider)
        await session.commit()
        with pytest.raises(organization_service.OrganizationServiceError):
            await persist_practice_match_setup(
                session, organization_id=organization_id, actor_user_id=outsider.id, setup=setup
            )
        assert (
            await session.scalar(
                select(func.count(Game.id)).where(Game.created_by_user_id == owner_id)
            )
            == 0
        )


async def test_persistence_rolls_back_when_roster_revalidation_fails() -> None:
    organization_id, owner_id, setup = await _prepared_setup()
    async with SessionLocal() as session:
        member_id = setup.team_b.school_team_player_membership_ids[0]
        membership = await session.get(SchoolTeamPlayerMembership, member_id)
        assert membership is not None
        membership.status = "inactive"
        await session.commit()
        with pytest.raises(Exception) as exc_info:
            await persist_practice_match_setup(
                session, organization_id=organization_id, actor_user_id=owner_id, setup=setup
            )
        assert getattr(exc_info.value, "status_code", None) == 422
    async with SessionLocal() as session:
        assert (
            await session.scalar(
                select(func.count(Game.id)).where(Game.created_by_user_id == owner_id)
            )
            == 0
        )


async def test_persistence_rolls_back_after_commit_failure(monkeypatch: pytest.MonkeyPatch) -> None:
    organization_id, owner_id, setup = await _prepared_setup()
    async with SessionLocal() as session:
        async def reject_commit() -> None:
            raise RuntimeError("test commit failure")

        monkeypatch.setattr(session, "commit", reject_commit)
        with pytest.raises(RuntimeError, match="test commit failure"):
            await persist_practice_match_setup(
                session, organization_id=organization_id, actor_user_id=owner_id, setup=setup
            )
        assert (
            await session.scalar(
                select(func.count(Game.id)).where(Game.created_by_user_id == owner_id)
            )
            == 0
        )


async def test_persistence_supports_split_sides_from_one_squad_with_stable_identities() -> None:
    async with SessionLocal() as session:
        owner = User(
            id=str(uuid.uuid4()), email="practice-shared-squad@example.com", hashed_password="test-only"
        )
        session.add(owner)
        await session.commit()
        organization, _ = await organization_service.create_organization(
            session,
            payload=OrganizationCreate(name="Shared practice", organization_type="school"),
            actor=owner,
        )
        shared = await _side(
            session,
            organization_id=organization.id,
            owner_id=owner.id,
            prefix="Shared",
            player_count=4,
        )
        team_a = PracticeSideSelection(
            source_squad_id=shared.source_squad_id,
            participant_membership_ids=shared.participant_membership_ids[:2],
        )
        team_b = PracticeSideSelection(
            source_squad_id=shared.source_squad_id,
            participant_membership_ids=shared.participant_membership_ids[2:],
        )
        setup = await prepare_practice_match_setup(
            session,
            organization_id=organization.id,
            actor_user_id=owner.id,
            team_a=team_a,
            team_b=team_b,
        )
        game = await persist_practice_match_setup(
            session, organization_id=organization.id, actor_user_id=owner.id, setup=setup
        )
        assert game.team_a["school_source"]["team_id"] == shared.source_squad_id
        assert game.team_b["school_source"]["team_id"] == shared.source_squad_id
        assert set(game.team_a["playing_xi"]).isdisjoint(game.team_b["playing_xi"])


async def test_dedicated_private_creation_route_creates_draft_without_match_day_roles() -> None:
    organization_id, owner_id, setup = await _prepared_setup("club")
    payload = PracticeMatchCreate(
        team_a=PracticeMatchSideSelection(
            source_squad_id=setup.team_a.source_squad_id,
            participant_membership_ids=list(setup.team_a.school_team_player_membership_ids),
        ),
        team_b=PracticeMatchSideSelection(
            source_squad_id=setup.team_b.source_squad_id,
            participant_membership_ids=list(setup.team_b.school_team_player_membership_ids),
        ),
    )
    async with SessionLocal() as session:
        owner = await session.get(User, owner_id)
        assert owner is not None
        response = await create_private_practice_match(
            organization_id=organization_id,
            payload=payload,
            current_user=owner,
            db=session,
        )
        game = await session.get(Game, response.game_id)
        assert game is not None
        assert response.match_purpose == game.match_purpose == "practice"
        assert response.status == game.status.value == "not_started"
        assert game.team_a_captain_id is None and game.team_b_keeper_id is None
