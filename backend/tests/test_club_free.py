from __future__ import annotations

import json
from io import BytesIO
from typing import Any

import pytest
from fastapi.testclient import TestClient
from openpyxl import Workbook
from sqlalchemy import func, select

from backend.api.schemas.organizations import OrganizationCreate
from backend.services import organization_entitlement_service, organization_service
from backend.sql_app.models import (
    Organization,
    OrganizationEntitlement,
    OrganizationMembership,
    RoleEnum,
    User,
)
from backend.tests.school_test_helpers import (
    add_membership,
    create_club,
    create_school,
    register_user,
)


def _create_team(
    client: TestClient,
    organization_id: str,
    headers: dict[str, str],
    name: str,
) -> dict[str, Any]:
    response = client.post(
        f"/api/organizations/{organization_id}/teams",
        json={"name": name},
        headers=headers,
    )
    assert response.status_code == 201, response.text
    return response.json()


def _side(team: dict[str, Any], roster: list[dict[str, Any]]) -> dict[str, Any]:
    membership_ids = [row["id"] for row in roster]
    assert len(membership_ids) == 11
    return {
        "team_id": team["id"],
        "playing_xi_membership_ids": membership_ids,
        "captain_membership_id": membership_ids[0],
        "wicketkeeper_membership_id": membership_ids[1],
    }


def test_school_and_club_creation_use_one_type_to_plan_contract(
    school_client: TestClient,
) -> None:
    school_owner = register_user(school_client, "club-contract-school@example.com")
    club_owner = register_user(school_client, "club-contract-club@example.com")

    school = create_school(school_client, school_owner, "Existing School Contract")
    club = create_club(school_client, club_owner, "New Club Contract")

    assert school["organization_type"] == "school"
    assert club["organization_type"] == "club"
    school_entitlement = school_client.get(
        f"/api/organizations/{school['id']}/entitlements",
        headers=school_owner.headers,
    )
    club_entitlement = school_client.get(
        f"/api/organizations/{club['id']}/entitlements",
        headers=club_owner.headers,
    )
    assert school_entitlement.status_code == club_entitlement.status_code == 200
    assert school_entitlement.json()["plan_key"] == "school_free"
    assert club_entitlement.json()["plan_key"] == "club_free"
    assert school_entitlement.json()["capabilities"] == club_entitlement.json()["capabilities"]
    assert (
        school_entitlement.json()["excluded_capabilities"]
        == club_entitlement.json()["excluded_capabilities"]
    )

    assert (
        organization_entitlement_service.PLAN_CAPABILITIES["school_free"]
        is organization_entitlement_service.PLAN_CAPABILITIES["club_free"]
        is organization_entitlement_service.FREE_ORGANIZATION_CAPABILITIES
    )
    assert (
        organization_entitlement_service.PLAN_EXCLUDED_CAPABILITIES["school_free"]
        is organization_entitlement_service.PLAN_EXCLUDED_CAPABILITIES["club_free"]
        is organization_entitlement_service.FREE_ORGANIZATION_EXCLUDED_CAPABILITIES
    )

    membership = school_client.get(
        f"/api/organizations/{club['id']}/me",
        headers=club_owner.headers,
    )
    assert membership.status_code == 200
    assert membership.json()["role"] == "owner"

    unsupported = school_client.post(
        "/api/organizations",
        json={"name": "Unsupported League", "organization_type": "league"},
        headers=club_owner.headers,
    )
    assert unsupported.status_code == 422


async def test_club_creation_rolls_back_organization_owner_and_entitlement_together(
    school_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    owner = register_user(school_client, "club-atomic@example.com")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]

    async def fail_provisioning(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("forced Club Free provisioning failure")

    monkeypatch.setattr(
        organization_service,
        "ensure_free_organization_entitlement",
        fail_provisioning,
    )
    async with session_maker() as session:
        actor = await session.get(User, owner.id)
        assert actor is not None
        with pytest.raises(RuntimeError, match="forced Club Free"):
            await organization_service.create_organization(
                session,
                payload=OrganizationCreate(
                    name="Atomic Club",
                    organization_type="club",
                ),
                actor=actor,
            )

    async with session_maker() as session:
        assert (
            await session.scalar(
                select(func.count(Organization.id)).where(Organization.name == "Atomic Club")
            )
            == 0
        )
        assert (
            await session.scalar(
                select(func.count(OrganizationMembership.id)).where(
                    OrganizationMembership.user_id == owner.id
                )
            )
            == 0
        )
        assert await session.scalar(select(func.count(OrganizationEntitlement.id))) == 0


async def test_mismatched_plan_is_ineffective_and_club_tenancy_has_no_global_bypass(
    school_client: TestClient,
) -> None:
    club_owner = register_user(school_client, "club-tenant-owner@example.com")
    school_owner = register_user(school_client, "club-tenant-school@example.com")
    outsider = register_user(school_client, "club-tenant-outsider@example.com")
    club = create_club(school_client, club_owner, "Tenant Club")
    school = create_school(school_client, school_owner, "Tenant School")

    assert (
        school_client.get(
            f"/api/organizations/{club['id']}", headers=school_owner.headers
        ).status_code
        == 404
    )
    assert (
        school_client.get(
            f"/api/organizations/{school['id']}", headers=club_owner.headers
        ).status_code
        == 404
    )

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored_outsider = await session.get(User, outsider.id)
        entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == club["id"]
            )
        )
        assert stored_outsider is not None and entitlement is not None
        stored_outsider.role = RoleEnum.org_pro
        stored_outsider.is_superuser = True
        entitlement.plan_key = "school_free"
        await session.commit()

    mismatch = school_client.get(
        f"/api/organizations/{club['id']}/entitlements",
        headers=club_owner.headers,
    )
    assert mismatch.status_code == 404
    async with session_maker() as session:
        assert not await organization_entitlement_service.organization_has_capability(
            session,
            organization_id=club["id"],
            capability="school_matches_unlimited",
        )

    global_bypass = school_client.get(
        f"/api/organizations/{club['id']}",
        headers=outsider.headers,
    )
    assert global_bypass.status_code == 404


async def test_club_free_shared_cricket_workflow_on_postgresql(
    school_client: TestClient,
) -> None:
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        if session.bind is None or session.bind.dialect.name != "postgresql":
            pytest.skip("Club Free acceptance requires real PostgreSQL")

    owner = register_user(school_client, "club-workflow-owner@example.com")
    scorer = register_user(school_client, "club-workflow-scorer@example.com")
    viewer = register_user(school_client, "club-workflow-viewer@example.com")
    global_outsider = register_user(school_client, "club-workflow-global@example.com")
    club = create_club(school_client, owner, "Cricksy Community Club")
    organization_id = club["id"]
    add_membership(school_client, owner, organization_id, scorer.id, "scorer")
    add_membership(school_client, owner, organization_id, viewer.id, "viewer")

    async with session_maker() as session:
        stored_outsider = await session.get(User, global_outsider.id)
        assert stored_outsider is not None
        stored_outsider.role = RoleEnum.org_pro
        stored_outsider.is_superuser = True
        stored_outsider.org_id = organization_id
        await session.commit()

    first_xi = _create_team(school_client, organization_id, owner.headers, "Club First XI")
    second_xi = _create_team(school_client, organization_id, owner.headers, "Club Second XI")

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.append(["player_name", "student_identifier", "year_group"])
    worksheet.append(["Club XLSX Preview", "XLSX-1", "Senior"])
    xlsx_bytes = BytesIO()
    workbook.save(xlsx_bytes)
    xlsx_preview = school_client.post(
        f"/api/organizations/{organization_id}/player-imports/preview",
        files={
            "file": (
                "club-roster.xlsx",
                xlsx_bytes.getvalue(),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=owner.headers,
    )
    assert xlsx_preview.status_code == 201, xlsx_preview.text
    assert xlsx_preview.json()["file_type"] == "xlsx"
    assert xlsx_preview.json()["row_count"] == 1
    empty_roster = school_client.get(
        f"/api/organizations/{organization_id}/players",
        headers=owner.headers,
    )
    assert empty_roster.status_code == 200
    assert empty_roster.json() == []

    rows = ["player_name,student_identifier,year_group,team_name"]
    rows.extend(
        f"Club A Player {index},CA-{index},Senior,{first_xi['name']}" for index in range(1, 12)
    )
    rows.extend(
        f"Club B Player {index},CB-{index},Senior,{second_xi['name']}" for index in range(1, 12)
    )
    preview = school_client.post(
        f"/api/organizations/{organization_id}/player-imports/preview",
        files={"file": ("club-roster.csv", "\n".join(rows).encode(), "text/csv")},
        headers=owner.headers,
    )
    assert preview.status_code == 201, preview.text
    preview_body = preview.json()
    assert preview_body["row_count"] == 22

    async with session_maker() as session:
        assert (
            await session.scalar(
                select(func.count(OrganizationMembership.id)).where(
                    OrganizationMembership.organization_id == organization_id
                )
            )
            == 3
        )

    applied = school_client.post(
        f"/api/organizations/{organization_id}/player-imports/{preview_body['import_id']}/apply",
        json={"resolutions": []},
        headers=owner.headers,
    )
    assert applied.status_code == 200, applied.text
    assert applied.json()["summary"]["created_players"] == 22
    assert applied.json()["summary"]["team_assignments_created"] == 22

    master_roster = school_client.get(
        f"/api/organizations/{organization_id}/players",
        headers=owner.headers,
    )
    roster_a_response = school_client.get(
        f"/api/organizations/{organization_id}/teams/{first_xi['id']}/players",
        headers=owner.headers,
    )
    roster_b_response = school_client.get(
        f"/api/organizations/{organization_id}/teams/{second_xi['id']}/players",
        headers=owner.headers,
    )
    assert (
        master_roster.status_code
        == roster_a_response.status_code
        == roster_b_response.status_code
        == 200
    )
    assert len(master_roster.json()) == 22
    roster_a = roster_a_response.json()
    roster_b = roster_b_response.json()
    assert len(roster_a) == len(roster_b) == 11

    match_payload = {
        "mode": "school_vs_school",
        "school_side": None,
        "team_a": _side(first_xi, roster_a),
        "team_b": _side(second_xi, roster_b),
        "external_opponent": None,
        "match_type": "limited",
        "overs_limit": 20,
        "days_limit": None,
        "overs_per_day": None,
        "dls_enabled": False,
        "toss_winner_side": "team_a",
        "decision": "bat",
    }
    created_match = school_client.post(
        f"/api/organizations/{organization_id}/matches",
        json=match_payload,
        headers=owner.headers,
    )
    assert created_match.status_code == 201, created_match.text
    game_id = created_match.json()["game_id"]

    external_payload = {
        **match_payload,
        "mode": "school_vs_external",
        "school_side": "team_a",
        "team_b": None,
        "external_opponent": {
            "team_name": "External Visitors",
            "player_names": [f"Visitor {index}" for index in range(1, 12)],
            "captain_index": 0,
            "wicketkeeper_index": 1,
        },
    }
    external_match = school_client.post(
        f"/api/organizations/{organization_id}/matches",
        json=external_payload,
        headers=owner.headers,
    )
    assert external_match.status_code == 201, external_match.text
    assert external_match.json()["team_b_name"] == "External Visitors"

    private_publication = school_client.get(
        f"/api/organizations/{organization_id}/matches/{game_id}/publication",
        headers=owner.headers,
    )
    assert private_publication.status_code == 200
    assert private_publication.json()["publication_state"] == "private"

    owner_snapshot = school_client.get(f"/games/{game_id}/snapshot", headers=owner.headers)
    scorer_snapshot = school_client.get(f"/games/{game_id}/snapshot", headers=scorer.headers)
    viewer_snapshot = school_client.get(f"/games/{game_id}/snapshot", headers=viewer.headers)
    outsider_snapshot = school_client.get(
        f"/games/{game_id}/snapshot",
        headers=global_outsider.headers,
    )
    assert (
        owner_snapshot.status_code
        == scorer_snapshot.status_code
        == viewer_snapshot.status_code
        == 200
    )
    assert outsider_snapshot.status_code == 404
    assert owner_snapshot.json()["school_organization_id"] == organization_id
    assert owner_snapshot.json()["can_score"] is True
    assert scorer_snapshot.json()["can_score"] is True
    assert viewer_snapshot.json()["can_score"] is False

    start_payload = {
        "striker_id": roster_a[0]["player_profile_id"],
        "non_striker_id": roster_a[1]["player_profile_id"],
        "opening_bowler_id": roster_b[0]["player_profile_id"],
    }
    viewer_start = school_client.post(
        f"/games/{game_id}/innings/start",
        json=start_payload,
        headers=viewer.headers,
    )
    assert viewer_start.status_code == 403
    outsider_start = school_client.post(
        f"/games/{game_id}/innings/start",
        json=start_payload,
        headers=global_outsider.headers,
    )
    assert outsider_start.status_code == 404
    scorer_start = school_client.post(
        f"/games/{game_id}/innings/start",
        json=start_payload,
        headers=scorer.headers,
    )
    assert scorer_start.status_code == 200, scorer_start.text

    for path in ("statistics/players", "statistics/teams", "fixtures", "results"):
        response = school_client.get(
            f"/api/organizations/{organization_id}/{path}",
            headers=owner.headers,
        )
        assert response.status_code == 200, (path, response.text)

    competition = school_client.post(
        f"/api/organizations/{organization_id}/competitions",
        json={"name": "Club Championship", "tournament_type": "league"},
        headers=owner.headers,
    )
    assert competition.status_code == 201, competition.text
    competition_id = competition.json()["id"]
    for team in (first_xi, second_xi):
        entrant = school_client.post(
            f"/api/organizations/{organization_id}/competitions/{competition_id}/teams",
            json={"team_id": team["id"]},
            headers=owner.headers,
        )
        assert entrant.status_code == 201, entrant.text
    fixture = school_client.post(
        f"/api/organizations/{organization_id}/competitions/{competition_id}/fixtures",
        json={"team_a_id": first_xi["id"], "team_b_id": second_xi["id"]},
        headers=owner.headers,
    )
    assert fixture.status_code == 201, fixture.text
    linked = school_client.put(
        f"/api/organizations/{organization_id}/competitions/{competition_id}"
        f"/fixtures/{fixture.json()['id']}/game",
        json={"game_id": game_id},
        headers=owner.headers,
    )
    assert linked.status_code == 200, linked.text

    published = school_client.patch(
        f"/api/organizations/{organization_id}/matches/{game_id}/publication",
        json={"publication_state": "published_live"},
        headers=owner.headers,
    )
    assert published.status_code == 200, published.text
    public = school_client.get(f"/public/school-scorecards/{game_id}")
    assert public.status_code == 200, public.text
    assert public.json()["organization_type"] == "club"
    serialized = json.dumps(public.json())
    assert "school_source" not in serialized
    assert "student_identifier" not in serialized
    assert organization_id not in serialized

    other_owner = register_user(school_client, "club-workflow-other@example.com")
    other_club = create_club(school_client, other_owner, "Other Private Club")
    cross_tenant = school_client.get(
        f"/api/organizations/{other_club['id']}/players",
        headers=owner.headers,
    )
    assert cross_tenant.status_code == 404
    assert "other private club" not in cross_tenant.text.lower()
