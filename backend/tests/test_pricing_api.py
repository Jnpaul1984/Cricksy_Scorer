"""
Test pricing API endpoints.

Ensures frontend can fetch pricing from /pricing routes.
"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_all_pricing(async_client: AsyncClient) -> None:
    """Test GET /pricing returns all plans."""
    response = await async_client.get("/pricing/")
    assert response.status_code == 200

    data = response.json()
    assert "individual_plans" in data
    assert "venue_plans" in data
    assert "scoring_is_free" in data
    assert data["scoring_is_free"] is True
    assert "contract_version" in data
    assert "last_updated" in data

    # Verify Scorers Pro is present
    individual_plans = data["individual_plans"]
    player_pro = next((p for p in individual_plans if p["id"] == "player_pro"), None)
    assert player_pro is not None
    assert player_pro["name"] == "Scorers Pro"
    assert player_pro["price_monthly_usd"] == 1.99


@pytest.mark.asyncio
async def test_get_individual_plan(async_client: AsyncClient) -> None:
    """Test GET /pricing/individual/{plan_id} returns single plan."""
    response = await async_client.get("/pricing/individual/player_pro")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == "player_pro"
    assert data["name"] == "Scorers Pro"
    assert data["price_monthly_usd"] == 1.99
    assert "tagline" in data
    assert "features" in data


@pytest.mark.asyncio
async def test_get_individual_plan_not_found(async_client: AsyncClient) -> None:
    """Test GET /pricing/individual/{plan_id} returns 404 for invalid plan."""
    response = await async_client.get("/pricing/individual/invalid_plan")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_venue_plan(async_client: AsyncClient) -> None:
    """Test GET /pricing/venue/{plan_id} returns single venue plan."""
    response = await async_client.get("/pricing/venue/venue_scoring_pro")
    assert response.status_code == 200

    data = response.json()
    assert data["id"] == "venue_scoring_pro"
    assert "name" in data
    assert "price_monthly_usd" in data
    assert "features" in data


@pytest.mark.asyncio
async def test_scorers_pro_pricing(async_client: AsyncClient) -> None:
    """Test Scorers Pro has correct pricing and features."""
    response = await async_client.get("/pricing/individual/player_pro")
    assert response.status_code == 200

    data = response.json()
    assert data["name"] == "Scorers Pro"
    assert data["price_monthly_usd"] == 1.99
    assert data["tagline"] == "Profile, stats, and exports for social media"

    # Verify AI quotas are reduced
    features = data["features"]
    assert features["ai_reports_per_month"] == 15
    assert features["tokens_limit"] == 30000
