from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_cors_exposes_request_id_to_browser_javascript(async_client) -> None:
    response = await async_client.get(
        "/health",
        headers={"Origin": "http://localhost:5173"},
    )

    assert response.status_code == 200
    assert response.headers["x-request-id"]
    exposed_headers = {
        value.strip().lower()
        for value in response.headers["access-control-expose-headers"].split(",")
    }
    assert "x-request-id" in exposed_headers
