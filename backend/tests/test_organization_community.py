from __future__ import annotations

import asyncio
import datetime as dt
import importlib
import uuid

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import delete, event, func, select, text
from sqlalchemy.exc import IntegrityError

from backend.api.schemas.organization_publication import OrganizationBrandingUpdate
from backend.api.schemas.organizations import OrganizationMembershipUpdate
from backend.services import organization_publication_service
from backend.services.organization_service import OrganizationServiceError, update_membership
from backend.services.public_leaderboard_service import _rank
from backend.sql_app.models import (
    Fixture,
    GameStatus,
    Organization,
    OrganizationCompetitionPublication,
    OrganizationMembership,
    OrganizationPublicSettings,
    PlayerProfile,
    SchoolPlayerMembership,
    SchoolTeamPlayerMembership,
    Team,
    Tournament,
    TournamentTeam,
)
from backend.tests.school_test_helpers import (
    RegisteredUser,
    add_membership,
    create_club,
    create_school,
    register_user,
)
from backend.tests.test_school_competition_publication import (
    _competition_with_fixture,
    _game,
    _team,
)


def _publish_homepage(client: TestClient, owner: RegisteredUser, organization_id: str) -> str:
    response = client.put(
        f"/api/organizations/{organization_id}/public-settings/publish",
        headers=owner.headers,
    )
    assert response.status_code == 200, response.text
    return response.json()["public_identifier"]


def test_anonymous_leaderboard_ties_are_ranked_deterministically() -> None:
    totals = {
        "internal-b": {"runs": 40, "wickets": 2},
        "internal-a": {"runs": 40, "wickets": 5},
        "internal-c": {"runs": 10, "wickets": 5},
    }
    assert [entry.model_dump() for entry in _rank(totals, metric="runs")] == [
        {"rank": 1, "participant_label": "Participant 1", "value": 40},
        {"rank": 1, "participant_label": "Participant 2", "value": 40},
        {"rank": 3, "participant_label": "Participant 3", "value": 10},
    ]
    assert [entry.model_dump() for entry in _rank(totals, metric="wickets")] == [
        {"rank": 1, "participant_label": "Participant 1", "value": 5},
        {"rank": 1, "participant_label": "Participant 2", "value": 5},
        {"rank": 3, "participant_label": "Participant 3", "value": 2},
    ]


def _set_competition_publication(
    client: TestClient,
    actor: RegisteredUser,
    organization_id: str,
    competition_id: str,
    *,
    publish: bool,
):
    action = "publish" if publish else "unpublish"
    return client.put(
        f"/api/organizations/{organization_id}/competitions/{competition_id}"
        f"/community-publication/{action}",
        headers=actor.headers,
    )


def test_public_community_has_no_enumeration_endpoint_and_safe_not_found_shape(
    school_client: TestClient,
) -> None:
    assert school_client.get("/api/public/organizations").status_code in {404, 405}
    missing = school_client.get("/api/public/organizations/org_aaaaaaaaaaaaaaaaaaaaaaaa/community")
    malformed = school_client.get("/api/public/organizations/not-an-identifier/community")
    assert missing.status_code == malformed.status_code == 404
    assert missing.json() == malformed.json() == {"detail": "Public page not found"}


@pytest.mark.parametrize("organization_type", ["school", "club"])
def test_unpublished_school_and_club_community_return_safe_404(
    school_client: TestClient, organization_type: str
) -> None:
    owner = register_user(school_client, f"unpublished-community-{organization_type}@example.com")
    create = create_school if organization_type == "school" else create_club
    organization = create(school_client, owner, f"Private {organization_type.title()}")
    settings = school_client.get(
        f"/api/organizations/{organization['id']}/public-settings", headers=owner.headers
    ).json()
    response = school_client.get(
        f"/api/public/organizations/{settings['public_identifier']}/community"
    )
    assert response.status_code == 404
    assert response.json() == {"detail": "Public page not found"}


@pytest.mark.parametrize("organization_type", ["school", "club"])
async def test_shared_school_club_homepage_requires_explicit_subordinate_publication(
    school_client: TestClient, organization_type: str
) -> None:
    owner = register_user(school_client, f"community-{organization_type}-owner@example.com")
    create = create_school if organization_type == "school" else create_club
    organization = create(school_client, owner, f"North {organization_type.title()}")
    team_a = await _team(school_client, organization["id"], owner.id, "First XI")
    team_b = await _team(school_client, organization["id"], owner.id, "Second XI")
    competition, fixture = await _competition_with_fixture(
        school_client, owner, organization["id"], team_a, team_b
    )
    game = await _game(
        school_client,
        organization["id"],
        owner.id,
        team_a,
        team_b,
        status=GameStatus.completed,
        result="First XI won by 8 runs",
        publication_state="private",
    )
    linked = school_client.put(
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}"
        f"/fixtures/{fixture['id']}/game",
        json={"game_id": game.id},
        headers=owner.headers,
    )
    assert linked.status_code == 200, linked.text

    private_player_name = f"PRIVATE-{organization_type.upper()}-PLAYER-CANARY"
    private_student_identifier = f"PRIVATE-{organization_type.upper()}-STUDENT-CANARY"
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        player = PlayerProfile(
            player_id=f"private-{organization_type}-player",
            player_name=private_player_name,
            date_of_birth=dt.date(2012, 3, 4),
        )
        session.add(player)
        await session.flush()
        roster_membership = SchoolPlayerMembership(
            organization_id=organization["id"],
            player_profile_id=player.player_id,
            student_identifier=private_student_identifier,
            year_group="PRIVATE-YEAR-CANARY",
            created_by_user_id=owner.id,
        )
        session.add(roster_membership)
        await session.flush()
        session.add(
            SchoolTeamPlayerMembership(
                organization_id=organization["id"],
                team_id=team_a.id,
                school_player_membership_id=roster_membership.id,
                created_by_user_id=owner.id,
            )
        )
        await session.commit()

    public_identifier = _publish_homepage(school_client, owner, organization["id"])
    community_url = f"/api/public/organizations/{public_identifier}/community"
    organization_only = school_client.get(community_url)
    assert organization_only.status_code == 200
    assert organization_only.json()["competitions"] == []

    published = _set_competition_publication(
        school_client, owner, organization["id"], competition["id"], publish=True
    )
    assert published.status_code == 200, published.text
    body = school_client.get(community_url).json()
    assert body["organization_type"] == organization_type
    assert body["display_name"] == f"North {organization_type.title()}"
    assert body["branding"] == {
        "logo_url": None,
        "logo_alt_text": f"North {organization_type.title()} logo",
        "fallback_text": "N",
    }
    assert body["competitions"][0]["team_names"] == ["First XI", "Second XI"]
    projected_fixture = body["competitions"][0]["fixtures"][0]
    assert projected_fixture["result"] == "First XI won by 8 runs"
    assert projected_fixture["public_scorecard_path"] is None
    assert [(row["team_name"], row["points"]) for row in body["competitions"][0]["standings"]] == [
        ("First XI", 2),
        ("Second XI", 0),
    ]

    serialized = str(body)
    for private_value in (
        organization["id"],
        competition["id"],
        fixture["id"],
        team_a.id,
        team_b.id,
        "profile-a",
        "membership-a",
        "SECRET-A",
        private_player_name,
        private_student_identifier,
        "PRIVATE-YEAR-CANARY",
        "2012-03-04",
        "student_identifier",
        "players",
        "roster",
        "email",
        "phone",
        "guardian",
        "medical",
        "availability",
        "attendance",
        "selection",
        "announcement",
    ):
        assert private_value.lower() not in serialized.lower()

    scorecard_publication = school_client.patch(
        f"/api/organizations/{organization['id']}/matches/{game.id}/publication",
        json={"publication_state": "published_final"},
        headers=owner.headers,
    )
    assert scorecard_publication.status_code == 200
    published_fixture = school_client.get(community_url).json()["competitions"][0]["fixtures"][0]
    assert (
        published_fixture["canonical_scorecard_path"] == published_fixture["public_scorecard_path"]
    )
    assert published_fixture["canonical_scorecard_path"] == (
        f"/community/{public_identifier}/competitions/"
        f"{body['competitions'][0]['public_key']}/scorecards/{game.public_scorecard_identifier}"
    )
    # The legacy endpoint remains independently backward-compatible.
    assert school_client.get(f"/public/school-scorecards/{game.id}").status_code == 200

    scorecard_private = school_client.patch(
        f"/api/organizations/{organization['id']}/matches/{game.id}/publication",
        json={"publication_state": "private"},
        headers=owner.headers,
    )
    assert scorecard_private.status_code == 200
    private_fixture = school_client.get(community_url).json()["competitions"][0]["fixtures"][0]
    assert private_fixture["canonical_scorecard_path"] is None
    assert private_fixture["public_scorecard_path"] is None

    assert (
        _set_competition_publication(
            school_client, owner, organization["id"], competition["id"], publish=False
        ).status_code
        == 200
    )
    assert school_client.get(community_url).json()["competitions"] == []


async def test_homepage_unpublish_does_not_mutate_independent_scorecard_publication(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "community-scorecard-owner@example.com")
    organization = create_school(school_client, owner, "Independent School")
    team_a = await _team(school_client, organization["id"], owner.id, "A")
    team_b = await _team(school_client, organization["id"], owner.id, "B")
    game = await _game(
        school_client,
        organization["id"],
        owner.id,
        team_a,
        team_b,
        publication_state="published_live",
    )
    public_identifier = _publish_homepage(school_client, owner, organization["id"])
    assert school_client.get(f"/public/school-scorecards/{game.id}").status_code == 200
    assert (
        school_client.put(
            f"/api/organizations/{organization['id']}/public-settings/unpublish",
            headers=owner.headers,
        ).status_code
        == 200
    )
    assert (
        school_client.get(f"/api/public/organizations/{public_identifier}/community").status_code
        == 404
    )
    assert school_client.get(f"/public/school-scorecards/{game.id}").status_code == 200
    republished = _publish_homepage(school_client, owner, organization["id"])
    assert republished == public_identifier


@pytest.mark.parametrize(
    ("role", "expected_status"),
    [("admin", 200), ("coach", 403), ("scorer", 403), ("viewer", 403)],
)
def test_branding_and_competition_publication_authority_matrix(
    school_client: TestClient, role: str, expected_status: int
) -> None:
    owner = register_user(school_client, f"community-authority-owner-{role}@example.com")
    actor = register_user(school_client, f"community-authority-{role}@example.com")
    organization = create_club(school_client, owner, "Authority Club")
    competition = school_client.post(
        f"/api/organizations/{organization['id']}/competitions",
        json={"name": "Authority Cup", "tournament_type": "league"},
        headers=owner.headers,
    ).json()
    add_membership(school_client, owner, organization["id"], actor.id, role)
    branding = school_client.put(
        f"/api/organizations/{organization['id']}/community-branding",
        json={
            "logo_url": f"https://cdn.example.com/{role}.png",
            "logo_alt_text": "Authority Club crest",
        },
        headers=actor.headers,
    )
    publication = _set_competition_publication(
        school_client, actor, organization["id"], competition["id"], publish=True
    )
    assert branding.status_code == publication.status_code == expected_status


def test_nonmember_disabled_and_cross_tenant_community_mutations_fail_closed(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "community-tenant-owner@example.com")
    outsider = register_user(school_client, "community-tenant-outsider@example.com")
    disabled_admin = register_user(school_client, "community-disabled-admin@example.com")
    organization = create_school(school_client, owner, "Tenant School")
    other = create_club(school_client, outsider, "Other Club")
    competition = school_client.post(
        f"/api/organizations/{organization['id']}/competitions",
        json={"name": "Tenant Cup", "tournament_type": "league"},
        headers=owner.headers,
    ).json()
    foreign_competition = school_client.post(
        f"/api/organizations/{other['id']}/competitions",
        json={"name": "Foreign Cup", "tournament_type": "league"},
        headers=outsider.headers,
    ).json()
    membership = add_membership(
        school_client, owner, organization["id"], disabled_admin.id, "admin"
    )
    assert (
        school_client.patch(
            f"/api/organizations/{organization['id']}/memberships/{membership['id']}",
            json={"status": "disabled"},
            headers=owner.headers,
        ).status_code
        == 200
    )

    for actor in (outsider, disabled_admin):
        assert (
            school_client.put(
                f"/api/organizations/{organization['id']}/community-branding",
                json={"logo_url": "https://cdn.example.com/logo.png"},
                headers=actor.headers,
            ).status_code
            == 404
        )
        assert (
            _set_competition_publication(
                school_client, actor, organization["id"], competition["id"], publish=True
            ).status_code
            == 404
        )

    assert (
        _set_competition_publication(
            school_client, owner, organization["id"], foreign_competition["id"], publish=True
        ).status_code
        == 404
    )


@pytest.mark.parametrize(
    "payload",
    [
        {"logo_url": "http://cdn.example.com/logo.png"},
        {"logo_url": "https://localhost/logo.png"},
        {"logo_url": "https://127.0.0.1/logo.png"},
        {"logo_url": "https://user:pass@cdn.example.com/logo.png"},
        {"logo_url": "https://cdn.example.com/logo.svg"},
        {"logo_url": "https://cdn.example.com/logo.png#fragment"},
        {
            "logo_url": "https://cdn.example.com/logo.png",
            "logo_alt_text": "<script>alert(1)</script>",
        },
        {"logo_url": None, "logo_alt_text": "orphan alt text"},
    ],
)
def test_logo_validation_rejects_unsafe_sources_and_markup(
    school_client: TestClient, payload: dict[str, str | None]
) -> None:
    owner = register_user(school_client, f"logo-validation-{uuid.uuid4()}@example.com")
    organization = create_school(school_client, owner, "Logo School")
    response = school_client.put(
        f"/api/organizations/{organization['id']}/community-branding",
        json=payload,
        headers=owner.headers,
    )
    assert response.status_code == 422


@pytest.mark.parametrize("organization_type", ["school", "club"])
async def test_branding_is_durable_and_public_allowlist_uses_safe_fallback(
    school_client: TestClient, organization_type: str
) -> None:
    owner = register_user(school_client, f"durable-branding-{organization_type}-owner@example.com")
    create = create_school if organization_type == "school" else create_club
    display_name = f"Durable {organization_type.title()}"
    organization = create(school_client, owner, display_name)
    public_identifier = _publish_homepage(school_client, owner, organization["id"])
    fallback = school_client.get(f"/api/public/organizations/{public_identifier}/community").json()[
        "branding"
    ]
    assert fallback == {
        "logo_url": None,
        "logo_alt_text": f"{display_name} logo",
        "fallback_text": "D",
    }
    logo_name = f"durable-{organization_type}"
    response = school_client.put(
        f"/api/organizations/{organization['id']}/community-branding",
        json={
            "logo_url": f"https://cdn.example.com/{logo_name}.webp",
            "logo_alt_text": f"{display_name} crest",
        },
        headers=owner.headers,
    )
    assert response.status_code == 200, response.text
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored = await session.get(OrganizationPublicSettings, organization["id"])
        assert stored is not None
        assert stored.logo_url == f"https://cdn.example.com/{logo_name}.webp"
        assert stored.logo_alt_text == f"{display_name} crest"
        assert stored.branding_version == 2
    public_branding = school_client.get(
        f"/api/public/organizations/{public_identifier}/community"
    ).json()["branding"]
    assert public_branding["logo_url"] == f"https://cdn.example.com/{logo_name}.webp"
    assert public_branding["logo_alt_text"] == f"{display_name} crest"


async def test_public_collections_are_bounded(school_client: TestClient) -> None:
    owner = register_user(school_client, "community-bounds-owner@example.com")
    organization = create_school(school_client, owner, "Bounded School")
    public_identifier = _publish_homepage(school_client, owner, organization["id"])
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        for competition_index in range(10):
            competition = Tournament(
                name=f"Cup {competition_index:02d}",
                organization_id=organization["id"],
            )
            session.add(competition)
            await session.flush()
            session.add(
                OrganizationCompetitionPublication(
                    competition_id=competition.id,
                    organization_id=organization["id"],
                    public_key=organization_publication_service.public_competition_key_candidate(
                        competition.id
                    ),
                    publication_state="published",
                )
            )
            teams: list[Team] = []
            for team_index in range(18):
                team = Team(
                    name=f"Team {competition_index:02d}-{team_index:02d}",
                    organization_id=organization["id"],
                    owner_user_id=owner.id,
                    players=[],
                    competitions=[],
                )
                session.add(team)
                await session.flush()
                teams.append(team)
                session.add(
                    TournamentTeam(
                        tournament_id=competition.id,
                        team_id=team.id,
                        team_name=team.name,
                        team_data={},
                    )
                )
            for fixture_index in range(14):
                session.add(
                    Fixture(
                        tournament_id=competition.id,
                        team_a_id=teams[0].id,
                        team_b_id=teams[1].id,
                        team_a_name=teams[0].name,
                        team_b_name=teams[1].name,
                        match_number=fixture_index + 1,
                    )
                )
        await session.commit()
    statements: list[str] = []
    engine = school_client.session_maker.kw["bind"]  # type: ignore[attr-defined]

    def record_statement(*args: object) -> None:
        statement = str(args[2]).lstrip().upper()
        if statement.startswith("SELECT"):
            statements.append(statement)

    event.listen(engine.sync_engine, "before_cursor_execute", record_statement)
    try:
        body = school_client.get(f"/api/public/organizations/{public_identifier}/community").json()
    finally:
        event.remove(engine.sync_engine, "before_cursor_execute", record_statement)
    assert len(statements) <= 6
    assert len(body["competitions"]) == organization_publication_service.MAX_PUBLIC_COMPETITIONS
    assert all(
        len(competition["team_names"])
        <= organization_publication_service.MAX_PUBLIC_TEAMS_PER_COMPETITION
        for competition in body["competitions"]
    )
    assert all(
        len(competition["fixtures"])
        <= organization_publication_service.MAX_PUBLIC_FIXTURES_PER_COMPETITION
        for competition in body["competitions"]
    )


async def _require_postgres(session_maker: object) -> None:
    async with session_maker() as session:  # type: ignore[operator]
        if session.get_bind().dialect.name != "postgresql":
            pytest.skip("PostgreSQL concurrency proof")


async def test_postgres_concurrent_publication_and_branding_are_coherent(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "community-race-owner@example.com")
    admin = register_user(school_client, "community-race-admin@example.com")
    other_owner = register_user(school_client, "community-race-other-owner@example.com")
    organization = create_club(school_client, owner, "Race Club")
    other_organization = create_school(school_client, other_owner, "Other Race School")
    add_membership(school_client, owner, organization["id"], admin.id, "admin")
    competition = school_client.post(
        f"/api/organizations/{organization['id']}/competitions",
        json={"name": "Race Cup", "tournament_type": "league"},
        headers=owner.headers,
    ).json()
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    await _require_postgres(session_maker)
    async with session_maker() as session:
        await session.execute(
            delete(OrganizationCompetitionPublication).where(
                OrganizationCompetitionPublication.competition_id == competition["id"]
            )
        )
        await session.commit()

    async def publish(actor_user_id: str) -> tuple[str, int]:
        async with session_maker() as session:
            (
                publication,
                _,
            ) = await organization_publication_service.set_competition_publication_state(
                session,
                organization_id=organization["id"],
                competition_id=competition["id"],
                actor_user_id=actor_user_id,
                publish=True,
            )
            return publication.publication_state, publication.publication_version

    assert await asyncio.gather(publish(owner.id), publish(admin.id)) == [
        ("published", 2),
        ("published", 2),
    ]

    async def transition(actor_user_id: str, publish_state: bool) -> None:
        async with session_maker() as session:
            await organization_publication_service.set_competition_publication_state(
                session,
                organization_id=organization["id"],
                competition_id=competition["id"],
                actor_user_id=actor_user_id,
                publish=publish_state,
            )

    await asyncio.gather(transition(owner.id, False), transition(admin.id, True))

    async def brand(organization_id: str, actor_user_id: str, filename: str) -> None:
        async with session_maker() as session:
            await organization_publication_service.update_branding(
                session,
                organization_id=organization_id,
                actor_user_id=actor_user_id,
                payload=OrganizationBrandingUpdate(
                    logo_url=f"https://cdn.example.com/{filename}.png",
                    logo_alt_text=f"{filename} crest",
                ),
            )

    await asyncio.gather(
        brand(organization["id"], owner.id, "owner"),
        brand(organization["id"], admin.id, "admin"),
    )
    await asyncio.gather(
        brand(organization["id"], owner.id, "race-club"),
        brand(other_organization["id"], other_owner.id, "other-race-school"),
    )
    async with session_maker() as session:
        records = (
            await session.scalars(
                select(OrganizationCompetitionPublication).where(
                    OrganizationCompetitionPublication.competition_id == competition["id"]
                )
            )
        ).all()
        settings = await session.get(OrganizationPublicSettings, organization["id"])
        other_settings = await session.get(OrganizationPublicSettings, other_organization["id"])
        assert len(records) == 1
        assert records[0].publication_state in {"published", "unpublished"}
        assert records[0].publication_version in {3, 4}
        assert settings is not None and settings.branding_version == 4
        assert settings.logo_url == "https://cdn.example.com/race-club.png"
        assert other_settings is not None and other_settings.branding_version == 2
        assert other_settings.logo_url == "https://cdn.example.com/other-race-school.png"


async def test_postgres_membership_revocation_winning_race_blocks_competition_publication(
    school_client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = register_user(school_client, "community-revocation-owner@example.com")
    admin = register_user(school_client, "community-revocation-admin@example.com")
    organization = create_school(school_client, owner, "Community Revocation School")
    membership = add_membership(school_client, owner, organization["id"], admin.id, "admin")
    competition = school_client.post(
        f"/api/organizations/{organization['id']}/competitions",
        json={"name": "Revocation Cup", "tournament_type": "league"},
        headers=owner.headers,
    ).json()
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    await _require_postgres(session_maker)
    publication_lock_attempted = asyncio.Event()
    original_lock = organization_publication_service._lock_active_organization

    async def observed_publication_lock(*args: object, **kwargs: object) -> Organization:
        publication_lock_attempted.set()
        return await original_lock(*args, **kwargs)  # type: ignore[arg-type]

    monkeypatch.setattr(
        organization_publication_service,
        "_lock_active_organization",
        observed_publication_lock,
    )
    async with session_maker() as revocation_session:
        locked = await revocation_session.scalar(
            select(Organization).where(Organization.id == organization["id"]).with_for_update()
        )
        assert locked is not None

        async def publish_competition() -> None:
            async with session_maker() as publication_session:
                await organization_publication_service.set_competition_publication_state(
                    publication_session,
                    organization_id=organization["id"],
                    competition_id=competition["id"],
                    actor_user_id=admin.id,
                    publish=True,
                )

        publication_task = asyncio.create_task(publish_competition())
        await asyncio.wait_for(publication_lock_attempted.wait(), timeout=5)
        await update_membership(
            revocation_session,
            organization_id=organization["id"],
            membership_id=membership["id"],
            payload=OrganizationMembershipUpdate(status="disabled"),
            actor_user_id=owner.id,
        )
        with pytest.raises(OrganizationServiceError) as exc_info:
            await publication_task
        assert exc_info.value.status_code == 404

    async with session_maker() as session:
        publication = await session.get(OrganizationCompetitionPublication, competition["id"])
        target = await session.get(OrganizationMembership, membership["id"])
        assert publication is not None and publication.publication_state == "unpublished"
        assert target is not None and target.status == "disabled"


async def test_postgres_database_integrity_rejects_cross_tenant_and_partial_branding(
    school_client: TestClient,
) -> None:
    school_owner = register_user(school_client, "community-integrity-school@example.com")
    club_owner = register_user(school_client, "community-integrity-club@example.com")
    school = create_school(school_client, school_owner, "Integrity School")
    club = create_club(school_client, club_owner, "Integrity Club")
    competition = school_client.post(
        f"/api/organizations/{school['id']}/competitions",
        json={"name": "Integrity Cup", "tournament_type": "league"},
        headers=school_owner.headers,
    ).json()
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    await _require_postgres(session_maker)

    async with session_maker() as session:
        settings = await session.get(OrganizationPublicSettings, school["id"])
        assert settings is not None
        settings.logo_alt_text = "Alt text without a logo"
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()

    async with session_maker() as session:
        await session.execute(
            delete(OrganizationCompetitionPublication).where(
                OrganizationCompetitionPublication.competition_id == competition["id"]
            )
        )
        await session.flush()
        session.add(
            OrganizationCompetitionPublication(
                competition_id=competition["id"],
                organization_id=club["id"],
            )
        )
        with pytest.raises(IntegrityError):
            await session.commit()
        await session.rollback()


async def test_postgres_migration_backfill_is_default_private(school_client: TestClient) -> None:
    owner = register_user(school_client, "community-backfill-owner@example.com")
    organization = create_school(school_client, owner, "Backfill Community School")
    competition = school_client.post(
        f"/api/organizations/{organization['id']}/competitions",
        json={"name": "Backfill Cup", "tournament_type": "league"},
        headers=owner.headers,
    ).json()
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    await _require_postgres(session_maker)
    migration = importlib.import_module(
        "backend.alembic.versions.20260930010000_add_community_publication_and_branding"
    )
    async with session_maker() as session:
        await session.execute(
            delete(OrganizationCompetitionPublication).where(
                OrganizationCompetitionPublication.competition_id == competition["id"]
            )
        )
        # The original migration ran before ``public_key`` existed.  This test
        # intentionally exercises its default-private result against the
        # current schema, so add the later migration's deterministic key while
        # preserving the historical SQL's competition/organization selection.
        # Do not change the historical migration: it must remain executable at
        # its own revision, where the column does not exist yet.
        current_schema_backfill_sql = migration.COMPETITION_PUBLICATION_BACKFILL_SQL.replace(
            "(competition_id, organization_id)",
            "(competition_id, organization_id, public_key)",
        ).replace(
            "SELECT id, organization_id",
            "SELECT id, organization_id, 'cmp_' || substr(md5('cricksy-public-competition:' || id), 1, 24)",
        )
        await session.execute(text(current_schema_backfill_sql))
        await session.commit()
        assert (
            await session.scalar(
                select(func.count(OrganizationCompetitionPublication.competition_id)).where(
                    OrganizationCompetitionPublication.competition_id == competition["id"],
                    OrganizationCompetitionPublication.publication_state == "unpublished",
                )
            )
            == 1
        )
