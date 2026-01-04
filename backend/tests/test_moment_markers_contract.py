"""
Contract validation tests for Video Moment Markers API.

These tests ensure the API contract defined in docs/COACHING_CONTRACT.md
is never broken by backend changes.
"""

import pytest
from fastapi import status
from httpx import AsyncClient

from backend.sql_app.models import RoleEnum, User, VideoMomentType, VideoSession


@pytest.mark.asyncio
async def test_create_marker_response_schema(
    async_client: AsyncClient,
    test_user: User,
    test_video_session: VideoSession,
    auth_headers: dict,
):
    """Test that create marker response matches contract schema."""
    response = await async_client.post(
        f"/api/coaches/markers/sessions/{test_video_session.id}/markers",
        json={
            "timestamp_ms": 5000,
            "moment_type": "catch",
            "description": "Great diving catch",
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    # Contract: All required fields must be present
    assert "id" in data
    assert "video_session_id" in data
    assert "timestamp_ms" in data
    assert "moment_type" in data
    assert "description" in data  # Must be present even if null
    assert "created_by" in data
    assert "created_at" in data

    # Contract: Field types must match
    assert isinstance(data["id"], str)
    assert isinstance(data["video_session_id"], str)
    assert isinstance(data["timestamp_ms"], int)
    assert isinstance(data["moment_type"], str)
    assert data["description"] is None or isinstance(data["description"], str)
    assert isinstance(data["created_by"], str)
    assert isinstance(data["created_at"], str)

    # Contract: Enum values must be valid
    assert data["moment_type"] in [e.value for e in VideoMomentType]

    # Contract: Values must match request
    assert data["video_session_id"] == test_video_session.id
    assert data["timestamp_ms"] == 5000
    assert data["moment_type"] == "catch"
    assert data["description"] == "Great diving catch"
    assert data["created_by"] == test_user.id

    # Contract: ISO 8601 datetime format
    from datetime import datetime
    datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))


@pytest.mark.asyncio
async def test_list_markers_response_schema(
    async_client: AsyncClient,
    test_video_session: VideoSession,
    auth_headers: dict,
):
    """Test that list markers response matches contract schema."""
    response = await async_client.get(
        f"/api/coaches/markers/sessions/{test_video_session.id}/markers",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Contract: Response must be an array
    assert isinstance(data, list)

    # If not empty, verify each marker follows contract
    for marker in data:
        assert "id" in marker
        assert "video_session_id" in marker
        assert "timestamp_ms" in marker
        assert "moment_type" in marker
        assert "description" in marker
        assert "created_by" in marker
        assert "created_at" in marker


@pytest.mark.asyncio
async def test_list_markers_ordering(
    async_client: AsyncClient,
    test_video_session: VideoSession,
    auth_headers: dict,
):
    """Test that markers are returned ordered by timestamp_ms ascending."""
    # Create markers in non-chronological order
    await async_client.post(
        f"/api/coaches/markers/sessions/{test_video_session.id}/markers",
        json={"timestamp_ms": 3000, "moment_type": "throw"},
        headers=auth_headers,
    )

    await async_client.post(
        f"/api/coaches/markers/sessions/{test_video_session.id}/markers",
        json={"timestamp_ms": 1000, "moment_type": "setup"},
        headers=auth_headers,
    )

    await async_client.post(
        f"/api/coaches/markers/sessions/{test_video_session.id}/markers",
        json={"timestamp_ms": 2000, "moment_type": "catch"},
        headers=auth_headers,
    )

    # List markers
    response = await async_client.get(
        f"/api/coaches/markers/sessions/{test_video_session.id}/markers",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Contract: Markers must be ordered by timestamp_ms ascending
    timestamps = [marker["timestamp_ms"] for marker in data]
    assert timestamps == sorted(timestamps)


@pytest.mark.asyncio
async def test_create_marker_validation_errors(
    async_client: AsyncClient,
    test_video_session: VideoSession,
    auth_headers: dict,
):
    """Test that validation errors match contract format."""
    # Invalid moment_type enum
    response = await async_client.post(
        f"/api/coaches/markers/sessions/{test_video_session.id}/markers",
        json={
            "timestamp_ms": 5000,
            "moment_type": "invalid_type",
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()
    assert "detail" in data
    assert "X-Error-Code" in response.headers or "code" in data

    # Negative timestamp
    response = await async_client.post(
        f"/api/coaches/markers/sessions/{test_video_session.id}/markers",
        json={
            "timestamp_ms": -100,
            "moment_type": "catch",
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY

    # Missing required field
    response = await async_client.post(
        f"/api/coaches/markers/sessions/{test_video_session.id}/markers",
        json={
            "moment_type": "catch",
            # Missing timestamp_ms
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_create_marker_session_not_found(
    async_client: AsyncClient,
    auth_headers: dict,
):
    """Test 404 Not Found for non-existent session."""
    response = await async_client.post(
        "/api/coaches/markers/sessions/00000000-0000-0000-0000-000000000000/markers",
        json={
            "timestamp_ms": 5000,
            "moment_type": "catch",
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_update_marker_response_schema(
    async_client: AsyncClient,
    test_video_session: VideoSession,
    auth_headers: dict,
):
    """Test that update marker response matches contract schema."""
    # Create marker
    create_response = await async_client.post(
        f"/api/coaches/markers/sessions/{test_video_session.id}/markers",
        json={
            "timestamp_ms": 5000,
            "moment_type": "catch",
            "description": "Original description",
        },
        headers=auth_headers,
    )
    marker_id = create_response.json()["id"]

    # Update marker
    update_response = await async_client.patch(
        f"/api/coaches/markers/markers/{marker_id}",
        json={
            "timestamp_ms": 6000,
            "moment_type": "dive",
            "description": "Updated description",
        },
        headers=auth_headers,
    )

    assert update_response.status_code == status.HTTP_200_OK
    data = update_response.json()

    # Contract: Response must match create schema
    assert "id" in data
    assert "timestamp_ms" in data
    assert "moment_type" in data
    assert "description" in data
    assert data["timestamp_ms"] == 6000
    assert data["moment_type"] == "dive"
    assert data["description"] == "Updated description"


@pytest.mark.asyncio
async def test_delete_marker_response(
    async_client: AsyncClient,
    test_video_session: VideoSession,
    auth_headers: dict,
):
    """Test that delete marker returns 204 No Content."""
    # Create marker
    create_response = await async_client.post(
        f"/api/coaches/markers/sessions/{test_video_session.id}/markers",
        json={
            "timestamp_ms": 5000,
            "moment_type": "catch",
        },
        headers=auth_headers,
    )
    marker_id = create_response.json()["id"]

    # Delete marker
    delete_response = await async_client.delete(
        f"/api/coaches/markers/markers/{marker_id}",
        headers=auth_headers,
    )

    assert delete_response.status_code == status.HTTP_204_NO_CONTENT
    # Contract: No content in response body
    assert delete_response.content == b""


@pytest.mark.asyncio
async def test_enum_stability(
    async_client: AsyncClient,
    test_video_session: VideoSession,
    auth_headers: dict,
):
    """Test that all contract-defined enum values are accepted."""
    # Contract: VideoMomentType enum values
    valid_moment_types = ["setup", "catch", "throw", "dive", "stumping", "other"]

    for moment_type in valid_moment_types:
        response = await async_client.post(
            f"/api/coaches/markers/sessions/{test_video_session.id}/markers",
            json={
                "timestamp_ms": 5000,
                "moment_type": moment_type,
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["moment_type"] == moment_type


@pytest.mark.asyncio
async def test_moment_type_filter(
    async_client: AsyncClient,
    test_video_session: VideoSession,
    auth_headers: dict,
):
    """Test that moment_type filtering works as per contract."""
    # Create markers with different types
    await async_client.post(
        f"/api/coaches/markers/sessions/{test_video_session.id}/markers",
        json={"timestamp_ms": 1000, "moment_type": "catch"},
        headers=auth_headers,
    )

    await async_client.post(
        f"/api/coaches/markers/sessions/{test_video_session.id}/markers",
        json={"timestamp_ms": 2000, "moment_type": "throw"},
        headers=auth_headers,
    )

    await async_client.post(
        f"/api/coaches/markers/sessions/{test_video_session.id}/markers",
        json={"timestamp_ms": 3000, "moment_type": "catch"},
        headers=auth_headers,
    )

    # Filter by moment_type
    response = await async_client.get(
        f"/api/coaches/markers/sessions/{test_video_session.id}/markers?moment_type=catch",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # All returned markers should be catches
    for marker in data:
        assert marker["moment_type"] == "catch"


@pytest.mark.asyncio
async def test_marker_ownership_enforcement(
    async_client: AsyncClient,
    test_video_session: VideoSession,
    other_user: User,
    auth_headers: dict,
    other_auth_headers: dict,
):
    """Test that users can only update/delete their own markers."""
    # Create marker as test_user
    create_response = await async_client.post(
        f"/api/coaches/markers/sessions/{test_video_session.id}/markers",
        json={"timestamp_ms": 5000, "moment_type": "catch"},
        headers=auth_headers,
    )
    marker_id = create_response.json()["id"]

    # Try to update as other_user (should fail)
    update_response = await async_client.patch(
        f"/api/coaches/markers/markers/{marker_id}",
        json={"timestamp_ms": 6000},
        headers=other_auth_headers,
    )

    assert update_response.status_code == status.HTTP_403_FORBIDDEN

    # Try to delete as other_user (should fail)
    delete_response = await async_client.delete(
        f"/api/coaches/markers/markers/{marker_id}",
        headers=other_auth_headers,
    )

    assert delete_response.status_code == status.HTTP_403_FORBIDDEN
