from __future__ import annotations

from fastapi.testclient import TestClient

from backend.sql_app.models import OrganizationPublicSettings
from backend.tests.school_test_helpers import create_school, register_user


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
