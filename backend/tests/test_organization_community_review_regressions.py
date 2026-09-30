from __future__ import annotations

from fastapi.testclient import TestClient

from backend.sql_app.models import GameStatus, OrganizationPublicSettings
from backend.tests.school_test_helpers import create_school, register_user
from backend.tests.test_school_competition_publication import (
    _competition_with_fixture,
    _game,
    _team,
)


async def test_logo_url_scheme_is_normalized_before_postgresql_persistence(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "logo-normalization-owner@example.com")
    organization = create_school(school_client, owner, "Normalized Logo School")
    endpoint = f"/api/organizations/{organization['id']}/community-branding"

    invalid = school_client.put(
        endpoint,
        json={"logo_url": "HTTPSX://cdn.example.com/logo.png"},
        headers=owner.headers,
    )
    assert invalid.status_code == 422

    malformed = school_client.put(
        endpoint,
        json={"logo_url": "https://[invalid/logo.png"},
        headers=owner.headers,
    )
    assert malformed.status_code == 422

    for encoded_host in ("%6cocalhost", "127%2e0%2e0%2e1"):
        encoded = school_client.put(
            endpoint,
            json={"logo_url": f"https://{encoded_host}/logo.png"},
            headers=owner.headers,
        )
        assert encoded.status_code == 422

    for browser_loopback in ("127.1", "2130706433", "0x7f000001"):
        loopback = school_client.put(
            endpoint,
            json={"logo_url": f"https://{browser_loopback}/logo.png"},
            headers=owner.headers,
        )
        assert loopback.status_code == 422

    encoded_path = school_client.put(
        endpoint,
        json={"logo_url": "https://cdn.example.com/school%20logos/logo.png"},
        headers=owner.headers,
    )
    assert encoded_path.status_code == 200, encoded_path.text
    assert encoded_path.json()["logo_url"] == "https://cdn.example.com/school%20logos/logo.png"

    accepted = school_client.put(
        endpoint,
        json={"logo_url": "HTTPS://cdn.example.com/logo.png"},
        headers=owner.headers,
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["logo_url"] == "https://cdn.example.com/logo.png"

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored = await session.get(OrganizationPublicSettings, organization["id"])
        assert stored is not None
        assert stored.logo_url == "https://cdn.example.com/logo.png"


async def test_public_community_suppresses_standings_with_unresolved_completed_game(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "unresolved-standings-owner@example.com")
    organization = create_school(school_client, owner, "Unresolved Standings School")
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
        result="Match abandoned",
    )
    linked = school_client.put(
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}"
        f"/fixtures/{fixture['id']}/game",
        json={"game_id": game.id},
        headers=owner.headers,
    )
    assert linked.status_code == 200, linked.text
    published_homepage = school_client.put(
        f"/api/organizations/{organization['id']}/public-settings/publish",
        headers=owner.headers,
    )
    assert published_homepage.status_code == 200, published_homepage.text
    published_competition = school_client.put(
        f"/api/organizations/{organization['id']}/competitions/{competition['id']}"
        "/community-publication/publish",
        headers=owner.headers,
    )
    assert published_competition.status_code == 200, published_competition.text

    public_identifier = published_homepage.json()["public_identifier"]
    response = school_client.get(f"/api/public/organizations/{public_identifier}/community")
    assert response.status_code == 200, response.text
    public_competition = response.json()["competitions"][0]
    assert public_competition["fixtures"][0]["result"] == "Match abandoned"
    assert public_competition["standings"] == []
