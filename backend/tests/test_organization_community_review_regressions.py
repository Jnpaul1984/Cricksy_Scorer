from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from backend.config import settings as app_settings
from backend.sql_app.models import (
    GameStatus,
    OrganizationEntitlement,
    OrganizationPublicSettings,
    Tournament,
)
from backend.tests.school_test_helpers import create_school, register_user
from backend.tests.test_school_competition_publication import (
    _competition_with_fixture,
    _game,
    _team,
)


async def test_logo_url_scheme_is_normalized_before_postgresql_persistence(
    school_client: TestClient,
    monkeypatch: pytest.MonkeyPatch,
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

    for unicode_local_host in (
        "\uff11\uff12\uff17\u3002\uff10\u3002\uff10\u3002\uff11",
        "\u24db\u24de\u24d2\u24d0\u24db\u24d7\u24de\u24e2\u24e3",
        "local\u115fhost",
    ):
        unicode_local = school_client.put(
            endpoint,
            json={"logo_url": f"https://{unicode_local_host}/logo.png"},
            headers=owner.headers,
        )
        assert unicode_local.status_code == 422

    encoded_path = school_client.put(
        endpoint,
        json={"logo_url": "https://cdn.example.com/school%20logos/logo.png"},
        headers=owner.headers,
    )
    assert encoded_path.status_code == 200, encoded_path.text
    assert encoded_path.json()["logo_url"] == "https://cdn.example.com/school%20logos/logo.png"

    untrusted_host = school_client.put(
        endpoint,
        json={"logo_url": "https://images.untrusted.example/logo.png"},
        headers=owner.headers,
    )
    assert untrusted_host.status_code == 422

    accepted = school_client.put(
        endpoint,
        json={
            "logo_url": "HTTPS://CDN.EXAMPLE.COM/logo.png",
            "logo_alt_text": "Approved crest",
        },
        headers=owner.headers,
    )
    assert accepted.status_code == 200, accepted.text
    assert accepted.json()["logo_url"] == "https://cdn.example.com/logo.png"

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        stored = await session.get(OrganizationPublicSettings, organization["id"])
        assert stored is not None
        assert stored.logo_url == "https://cdn.example.com/logo.png"

    published = school_client.put(
        f"/api/organizations/{organization['id']}/public-settings/publish",
        headers=owner.headers,
    )
    assert published.status_code == 200, published.text
    monkeypatch.setattr(
        app_settings,
        "ORGANIZATION_LOGO_ALLOWED_HOSTS",
        "cricksy-ai.com,www.cricksy-ai.com",
    )
    public = school_client.get(
        f"/api/public/organizations/{published.json()['public_identifier']}/community"
    )
    assert public.status_code == 200, public.text
    assert public.json()["branding"] == {
        "logo_url": None,
        "logo_alt_text": "Normalized Logo School logo",
        "fallback_text": "N",
    }


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


async def test_public_community_hides_scorecard_link_when_capability_is_disabled(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "disabled-scorecard-capability-owner@example.com")
    organization = create_school(school_client, owner, "Disabled Scorecard School")
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
        publication_state="published_final",
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
    community_url = f"/api/public/organizations/{public_identifier}/community"
    initial_fixture = school_client.get(community_url).json()["competitions"][0]["fixtures"][0]
    assert initial_fixture["canonical_scorecard_path"] == initial_fixture["public_scorecard_path"]
    assert initial_fixture["canonical_scorecard_path"].startswith(
        f"/community/{public_identifier}/competitions/cmp_"
    )
    assert initial_fixture["canonical_scorecard_path"].endswith(game.public_scorecard_identifier)
    assert str(game.id) not in initial_fixture["canonical_scorecard_path"]
    # This assertion protects the old API contract separately from the opaque link.
    assert school_client.get(f"/public/school-scorecards/{game.id}").status_code == 200

    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        entitlement = await session.scalar(
            select(OrganizationEntitlement).where(
                OrganizationEntitlement.organization_id == organization["id"]
            )
        )
        assert entitlement is not None
        entitlement.status = "disabled"
        await session.commit()

    disabled_fixture = school_client.get(community_url).json()["competitions"][0]["fixtures"][0]
    assert disabled_fixture["canonical_scorecard_path"] is None
    assert disabled_fixture["public_scorecard_path"] is None
    assert school_client.get(f"/public/school-scorecards/{game.id}").status_code == 404


async def test_community_settings_controls_competitions_beyond_first_hundred(
    school_client: TestClient,
) -> None:
    owner = register_user(school_client, "large-community-settings-owner@example.com")
    organization = create_school(school_client, owner, "Large Community School")
    session_maker = school_client.session_maker  # type: ignore[attr-defined]
    async with session_maker() as session:
        competitions = [
            Tournament(name=f"Cup {index:03d}", organization_id=organization["id"])
            for index in range(101)
        ]
        session.add_all(competitions)
        await session.commit()
        final_competition_id = competitions[-1].id

    settings_url = f"/api/organizations/{organization['id']}/community-settings"
    initial = school_client.get(settings_url, headers=owner.headers)
    assert initial.status_code == 200, initial.text
    assert len(initial.json()["competitions"]) == 101
    assert initial.json()["competitions"][-1]["competition_id"] == final_competition_id

    published = school_client.put(
        f"/api/organizations/{organization['id']}/competitions/{final_competition_id}"
        "/community-publication/publish",
        headers=owner.headers,
    )
    assert published.status_code == 200, published.text
    refreshed = school_client.get(settings_url, headers=owner.headers)
    assert refreshed.status_code == 200, refreshed.text
    assert refreshed.json()["competitions"][-1]["publication_state"] == "published"

    unpublished = school_client.put(
        f"/api/organizations/{organization['id']}/competitions/{final_competition_id}"
        "/community-publication/unpublish",
        headers=owner.headers,
    )
    assert unpublished.status_code == 200, unpublished.text
    final = school_client.get(settings_url, headers=owner.headers)
    assert final.status_code == 200, final.text
    assert final.json()["competitions"][-1]["publication_state"] == "unpublished"
