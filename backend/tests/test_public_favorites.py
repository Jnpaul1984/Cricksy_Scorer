from __future__ import annotations

from fastapi.testclient import TestClient

from backend.tests.school_test_helpers import add_membership, create_school, register_user
from backend.services.organization_publication_service import team_public_identifier_candidate
from backend.sql_app.models import OrganizationTeamPublication, Team


def _publish(client: TestClient, owner: object, organization_id: str) -> str:
    settings = client.get(f"/api/organizations/{organization_id}/public-settings", headers=owner.headers).json()
    assert client.put(f"/api/organizations/{organization_id}/public-settings/publish", headers=owner.headers).status_code == 200
    return settings["public_identifier"]


def test_staff_public_favorites_are_closed_fresh_and_owner_scoped(school_client: TestClient) -> None:
    owner = register_user(school_client, "favorite-owner@example.com")
    staff = register_user(school_client, "favorite-staff@example.com")
    viewer = register_user(school_client, "favorite-viewer@example.com")
    organization = create_school(school_client, owner, "Favorite School")
    add_membership(school_client, owner, organization["id"], staff.id, "scorer")
    add_membership(school_client, owner, organization["id"], viewer.id, "viewer")
    key = _publish(school_client, owner, organization["id"])

    payload = {"subject_kind": "organization", "subject_public_key": key}
    first = school_client.put("/api/me/public-favorites", json=payload, headers=staff.headers)
    repeated = school_client.put("/api/me/public-favorites", json=payload, headers=staff.headers)
    assert first.status_code == repeated.status_code == 200
    assert first.json()["id"] == repeated.json()["id"]
    assert first.json()["canonical_path"] == f"/community/{key}"
    assert set(first.json()) == {"id", "subject_kind", "public_key", "display_name", "canonical_path", "created_at"}
    assert school_client.get("/api/me/public-favorites", headers=staff.headers).json()["items"]
    assert school_client.get("/api/me/public-favorites", headers=owner.headers).json()["items"] == []
    assert school_client.put("/api/me/public-favorites", json=payload, headers=viewer.headers).status_code == 403
    assert school_client.put("/api/me/public-favorites", json={"subject_kind": "player", "subject_public_key": key}, headers=staff.headers).status_code == 422
    assert school_client.put("/api/me/public-favorites", json={"subject_kind": "organization", "subject_public_key": organization["id"]}, headers=staff.headers).status_code == 404

    assert school_client.put(f"/api/organizations/{organization['id']}/public-settings/unpublish", headers=owner.headers).status_code == 200
    assert school_client.get("/api/me/public-favorites", headers=staff.headers).json()["items"] == []
    # Revocation suppresses display data but does not prevent a user deleting their own preference.
    assert school_client.delete(f"/api/me/public-favorites/{first.json()['id']}", headers=staff.headers).status_code == 204


def test_competition_favorite_uses_an_opaque_key_and_revokes_freshly(school_client: TestClient) -> None:
    owner = register_user(school_client, "competition-favorite-owner@example.com")
    organization = create_school(school_client, owner, "Competition Favorite School")
    organization_key = _publish(school_client, owner, organization["id"])
    competition = school_client.post(
        f"/api/organizations/{organization['id']}/competitions",
        json={"name": "Private Id Never Shared Cup", "tournament_type": "league"},
        headers=owner.headers,
    ).json()
    assert school_client.put(
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}/community-publication/publish",
        headers=owner.headers,
    ).status_code == 200
    public_competition = school_client.get(f"/api/public/organizations/{organization_key}/community").json()["competitions"][0]
    assert public_competition["public_key"].startswith("cmp_")
    assert competition["id"] not in public_competition.values()
    saved = school_client.put("/api/me/public-favorites", json={"subject_kind": "competition", "subject_public_key": public_competition["public_key"]}, headers=owner.headers)
    assert saved.status_code == 200
    assert saved.json()["canonical_path"] == f"/community/{organization_key}#competition-{public_competition['public_key']}"
    assert school_client.put(
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}/community-publication/unpublish",
        headers=owner.headers,
    ).status_code == 200
    assert school_client.get("/api/me/public-favorites", headers=owner.headers).json()["items"] == []


async def test_team_favorite_reuses_authoritative_public_team_resolution(school_client: TestClient) -> None:
    owner = register_user(school_client, "team-favorite-owner@example.com")
    organization = create_school(school_client, owner, "Team Favorite School")
    organization_key = _publish(school_client, owner, organization["id"])
    team_id = "team-favorite-private-id"
    team_key = team_public_identifier_candidate(team_id)
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        session.add(Team(id=team_id, name="Public Team", organization_id=organization["id"], players=[]))
        session.add(OrganizationTeamPublication(
            team_id=team_id, organization_id=organization["id"], public_identifier=team_key,
            publication_state="published", publication_version=2, published_by_user_id=owner.id,
        ))
        await session.commit()
    public = school_client.get(f"/api/public/organizations/{organization_key}/teams/{team_key}")
    assert public.status_code == 200
    assert set(public.json()) == {"public_identifier", "display_name", "aggregate_stats"}
    saved = school_client.put("/api/me/public-favorites", json={"subject_kind": "team", "subject_public_key": team_key}, headers=owner.headers)
    assert saved.status_code == 200
    assert saved.json()["canonical_path"] == f"/community/{organization_key}/teams/{team_key}"
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        publication = await session.get(OrganizationTeamPublication, team_id)
        team = await session.get(Team, team_id)
        assert publication is not None
        assert team is not None
        publication.publication_state = "unpublished"
        await session.commit()
    assert school_client.get("/api/me/public-favorites", headers=owner.headers).json()["items"] == []
    async with school_client.session_maker() as session:  # type: ignore[attr-defined]
        publication = await session.get(OrganizationTeamPublication, team_id)
        team = await session.get(Team, team_id)
        assert publication is not None and team is not None
        publication.publication_state = "published"
        team.status = "archived"
        await session.commit()
    assert school_client.get(f"/api/public/organizations/{organization_key}/teams/{team_key}").status_code == 404
    assert school_client.put("/api/me/public-favorites", json={"subject_kind": "team", "subject_public_key": team_key}, headers=owner.headers).status_code == 404
