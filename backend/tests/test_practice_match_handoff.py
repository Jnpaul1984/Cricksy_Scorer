from __future__ import annotations

import uuid

import pytest
from sqlalchemy import func, select

from backend.api.schemas.organizations import OrganizationCreate
from backend.services import organization_service
from backend.services.practice_match_setup_service import (
    PracticeSideSelection,
    prepare_practice_match_setup,
    serialize_practice_match_setup,
    validate_practice_match_readiness,
)
from backend.sql_app.models import (
    Game,
    PlayerProfile,
    SchoolPlayerMembership,
    SchoolTeamPlayerMembership,
    Team,
    User,
)


async def _seed_practice_side(
    session: object,
    *,
    organization_id: str,
    owner_user_id: str,
    source_squad_id: str,
    prefix: str,
) -> PracticeSideSelection:
    team = Team(
        id=source_squad_id,
        organization_id=organization_id,
        owner_user_id=owner_user_id,
        name=f"{prefix} source",
        status="active",
        players=[],
        competitions=[],
    )
    session.add(team)  # type: ignore[attr-defined]
    membership_ids: list[str] = []
    for index in range(2):
        profile_id = str(uuid.uuid4())
        school_membership_id = str(uuid.uuid4())
        team_membership_id = str(uuid.uuid4())
        session.add(PlayerProfile(player_id=profile_id, player_name=f"{prefix} {index}"))  # type: ignore[attr-defined]
        session.add(  # type: ignore[attr-defined]
            SchoolPlayerMembership(
                id=school_membership_id,
                organization_id=organization_id,
                player_profile_id=profile_id,
                status="active",
                created_by_user_id=owner_user_id,
            )
        )
        session.add(  # type: ignore[attr-defined]
            SchoolTeamPlayerMembership(
                id=team_membership_id,
                organization_id=organization_id,
                team_id=source_squad_id,
                school_player_membership_id=school_membership_id,
                status="active",
                created_by_user_id=owner_user_id,
            )
        )
        membership_ids.append(team_membership_id)
    await session.commit()  # type: ignore[attr-defined]
    return PracticeSideSelection(
        source_squad_id=source_squad_id,
        participant_membership_ids=tuple(membership_ids),
        captain_membership_id=None,
        wicketkeeper_membership_id=None,
    )


@pytest.mark.parametrize("organization_type", ["school", "club"])
async def test_real_free_organization_authorization_serializes_without_game_writes(
    organization_type: str,
) -> None:
    from backend.sql_app.database import SessionLocal

    async with SessionLocal() as session:
        owner = User(
            id=str(uuid.uuid4()),
            email=f"practice-{organization_type}@example.com",
            hashed_password="test-only",
        )
        session.add(owner)
        await session.commit()
        organization, _membership = await organization_service.create_organization(
            session,
            payload=OrganizationCreate(
                name=f"Practice {organization_type}", organization_type=organization_type
            ),
            actor=owner,
        )
        team_a = await _seed_practice_side(
            session,
            organization_id=organization.id,
            owner_user_id=owner.id,
            source_squad_id=str(uuid.uuid4()),
            prefix="A",
        )
        team_b = await _seed_practice_side(
            session,
            organization_id=organization.id,
            owner_user_id=owner.id,
            source_squad_id=str(uuid.uuid4()),
            prefix="B",
        )
        setup = await prepare_practice_match_setup(
            session,
            organization_id=organization.id,
            actor_user_id=owner.id,
            team_a=team_a,
            team_b=team_b,
        )
        handoff = serialize_practice_match_setup(setup)
        assert handoff["match_purpose"] == "practice"
        assert handoff["match_rules"]["sides"] == {  # type: ignore[index]
            "team_a": {
                "source_squad_id": team_a.source_squad_id,
                "canonical_player_ids": handoff["team_a"]["canonical_player_ids"],  # type: ignore[index]
            },
            "team_b": {
                "source_squad_id": team_b.source_squad_id,
                "canonical_player_ids": handoff["team_b"]["canonical_player_ids"],  # type: ignore[index]
            },
        }
        assert await session.scalar(select(func.count(Game.id))) == 0
        with pytest.raises(Exception, match="requires captain and wicketkeeper"):
            validate_practice_match_readiness(setup)
