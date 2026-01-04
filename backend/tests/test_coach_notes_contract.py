"""
Contract validation tests for Coach Notes API.

These tests ensure the API contract defined in docs/COACHING_CONTRACT.md
is never broken by backend changes.
"""

import pytest
from fastapi import status
from httpx import AsyncClient

from backend.sql_app.models import CoachNoteSeverity, Player, User


@pytest.mark.asyncio
async def test_create_note_response_schema(
    async_client: AsyncClient,
    test_user: User,
    test_player: Player,
    auth_headers: dict,
):
    """Test that create note response matches contract schema."""
    # Create note
    response = await async_client.post(
        f"/api/coaches/players/{test_player.id}/notes",
        json={
            "player_id": test_player.id,
            "note_text": "Great batting technique today",
            "severity": "info",
            "tags": ["footwork", "timing"],
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_201_CREATED
    data = response.json()

    # Contract: All required fields must be present
    assert "id" in data
    assert "coach_id" in data
    assert "player_id" in data
    assert "player_name" in data  # Enriched field
    assert "video_session_id" in data  # Must be present even if null
    assert "video_session_title" in data  # Must be present even if null
    assert "moment_marker_id" in data  # Must be present even if null
    assert "note_text" in data
    assert "tags" in data
    assert "severity" in data
    assert "created_at" in data
    assert "updated_at" in data

    # Contract: Field types must match
    assert isinstance(data["id"], str)
    assert isinstance(data["coach_id"], str)
    assert isinstance(data["player_id"], int)
    assert data["player_name"] is None or isinstance(data["player_name"], str)
    assert data["video_session_id"] is None or isinstance(data["video_session_id"], str)
    assert data["video_session_title"] is None or isinstance(data["video_session_title"], str)
    assert data["moment_marker_id"] is None or isinstance(data["moment_marker_id"], str)
    assert isinstance(data["note_text"], str)
    assert data["tags"] is None or isinstance(data["tags"], list)
    assert isinstance(data["severity"], str)
    assert isinstance(data["created_at"], str)
    assert isinstance(data["updated_at"], str)

    # Contract: Enum values must be valid
    assert data["severity"] in [e.value for e in CoachNoteSeverity]

    # Contract: Enriched fields should be populated when possible
    assert data["coach_id"] == test_user.id
    assert data["player_id"] == test_player.id

    # Contract: ISO 8601 datetime format
    from datetime import datetime

    datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
    datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))


@pytest.mark.asyncio
async def test_list_notes_response_schema(
    async_client: AsyncClient,
    test_player: Player,
    auth_headers: dict,
):
    """Test that list notes response matches contract schema."""
    response = await async_client.get(
        f"/api/coaches/players/{test_player.id}/notes",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # Contract: Response must be an array
    assert isinstance(data, list)

    # If not empty, verify each note follows contract
    for note in data:
        assert "id" in note
        assert "coach_id" in note
        assert "player_id" in note
        assert "player_name" in note
        assert "video_session_id" in note
        assert "video_session_title" in note
        assert "moment_marker_id" in note
        assert "note_text" in note
        assert "tags" in note
        assert "severity" in note
        assert "created_at" in note
        assert "updated_at" in note


@pytest.mark.asyncio
async def test_create_note_error_responses(
    async_client: AsyncClient,
    test_player: Player,
    auth_headers: dict,
):
    """Test that error responses match contract format."""
    # 422 Validation Error - Invalid severity
    response = await async_client.post(
        f"/api/coaches/players/{test_player.id}/notes",
        json={
            "player_id": test_player.id,
            "note_text": "Test note",
            "severity": "invalid_severity",  # Invalid enum
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
    data = response.json()

    # Contract: Error response must have detail field
    assert "detail" in data

    # 422 Validation Error - Missing required field
    response = await async_client.post(
        f"/api/coaches/players/{test_player.id}/notes",
        json={
            "player_id": test_player.id,
            # Missing note_text
        },
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


@pytest.mark.asyncio
async def test_create_note_unauthorized(async_client: AsyncClient, test_player: Player):
    """Test 401 Unauthorized response format."""
    # No auth headers
    response = await async_client.post(
        f"/api/coaches/players/{test_player.id}/notes",
        json={
            "player_id": test_player.id,
            "note_text": "Test note",
        },
    )

    assert response.status_code == status.HTTP_401_UNAUTHORIZED


@pytest.mark.asyncio
async def test_get_note_not_found(async_client: AsyncClient, auth_headers: dict):
    """Test 404 Not Found response format."""
    response = await async_client.get(
        "/api/coaches/notes/00000000-0000-0000-0000-000000000000",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_404_NOT_FOUND
    data = response.json()
    assert "detail" in data


@pytest.mark.asyncio
async def test_update_note_response_schema(
    async_client: AsyncClient,
    test_user: User,
    test_player: Player,
    auth_headers: dict,
):
    """Test that update note response matches contract schema."""
    # First create a note
    create_response = await async_client.post(
        f"/api/coaches/players/{test_player.id}/notes",
        json={
            "player_id": test_player.id,
            "note_text": "Original note",
            "severity": "info",
        },
        headers=auth_headers,
    )
    note_id = create_response.json()["id"]

    # Update the note
    update_response = await async_client.patch(
        f"/api/coaches/notes/{note_id}",
        json={
            "note_text": "Updated note",
            "severity": "improvement",
        },
        headers=auth_headers,
    )

    assert update_response.status_code == status.HTTP_200_OK
    data = update_response.json()

    # Contract: Response must match create schema
    assert "id" in data
    assert "note_text" in data
    assert "severity" in data
    assert data["note_text"] == "Updated note"
    assert data["severity"] == "improvement"


@pytest.mark.asyncio
async def test_delete_note_response(
    async_client: AsyncClient,
    test_player: Player,
    auth_headers: dict,
):
    """Test that delete note returns 204 No Content."""
    # First create a note
    create_response = await async_client.post(
        f"/api/coaches/players/{test_player.id}/notes",
        json={
            "player_id": test_player.id,
            "note_text": "Note to delete",
        },
        headers=auth_headers,
    )
    note_id = create_response.json()["id"]

    # Delete the note
    delete_response = await async_client.delete(
        f"/api/coaches/notes/{note_id}",
        headers=auth_headers,
    )

    assert delete_response.status_code == status.HTTP_204_NO_CONTENT
    # Contract: No content in response body
    assert delete_response.content == b""


@pytest.mark.asyncio
async def test_enum_stability(
    async_client: AsyncClient,
    test_player: Player,
    auth_headers: dict,
):
    """Test that all contract-defined enum values are accepted."""
    # Contract: CoachNoteSeverity enum values
    valid_severities = ["info", "improvement", "critical"]

    for severity in valid_severities:
        response = await async_client.post(
            f"/api/coaches/players/{test_player.id}/notes",
            json={
                "player_id": test_player.id,
                "note_text": f"Testing {severity} severity",
                "severity": severity,
            },
            headers=auth_headers,
        )
        assert response.status_code == status.HTTP_201_CREATED
        assert response.json()["severity"] == severity


@pytest.mark.asyncio
async def test_pagination_params(
    async_client: AsyncClient,
    test_player: Player,
    auth_headers: dict,
):
    """Test that pagination parameters work as per contract."""
    # Create multiple notes
    for i in range(5):
        await async_client.post(
            f"/api/coaches/players/{test_player.id}/notes",
            json={
                "player_id": test_player.id,
                "note_text": f"Note {i}",
            },
            headers=auth_headers,
        )

    # Test with limit
    response = await async_client.get(
        f"/api/coaches/players/{test_player.id}/notes?limit=2",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert len(data) <= 2

    # Test with offset
    response = await async_client.get(
        f"/api/coaches/players/{test_player.id}/notes?offset=2&limit=2",
        headers=auth_headers,
    )
    assert response.status_code == status.HTTP_200_OK


@pytest.mark.asyncio
async def test_severity_filter(
    async_client: AsyncClient,
    test_player: Player,
    auth_headers: dict,
):
    """Test that severity filtering works as per contract."""
    # Create notes with different severities
    await async_client.post(
        f"/api/coaches/players/{test_player.id}/notes",
        json={
            "player_id": test_player.id,
            "note_text": "Info note",
            "severity": "info",
        },
        headers=auth_headers,
    )

    await async_client.post(
        f"/api/coaches/players/{test_player.id}/notes",
        json={
            "player_id": test_player.id,
            "note_text": "Critical note",
            "severity": "critical",
        },
        headers=auth_headers,
    )

    # Filter by severity
    response = await async_client.get(
        f"/api/coaches/players/{test_player.id}/notes?severity=critical",
        headers=auth_headers,
    )

    assert response.status_code == status.HTTP_200_OK
    data = response.json()

    # All returned notes should have critical severity
    for note in data:
        assert note["severity"] == "critical"
