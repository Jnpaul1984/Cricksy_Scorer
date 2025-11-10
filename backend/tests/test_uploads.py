"""Tests for upload API endpoints."""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def enable_uploads(monkeypatch):
    """Enable uploads feature for testing."""
    monkeypatch.setenv("CRICKSY_ENABLE_UPLOADS", "1")
    # Reload config to pick up env changes
    from backend import config
    config.settings = config.Settings()


@pytest.fixture
def client_with_uploads(enable_uploads):
    """Create a test client with uploads enabled."""
    from backend.main import fastapi_app
    return TestClient(fastapi_app)


def test_initiate_upload_success(client_with_uploads):
    """Test successful upload initiation."""
    with patch("backend.utils.s3.generate_presigned_put_url") as mock_s3:
        mock_s3.return_value = "https://s3.example.com/presigned-url"
        
        response = client_with_uploads.post(
            "/api/uploads/initiate",
            json={
                "filename": "scorecard.pdf",
                "file_type": "application/pdf",
                "game_id": None,
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "upload_id" in data
        assert "s3_key" in data
        assert "presigned_url" in data
        assert data["presigned_url"] == "https://s3.example.com/presigned-url"
        assert "expires_in" in data


def test_initiate_upload_with_game_id(client_with_uploads):
    """Test upload initiation with game_id."""
    with patch("backend.utils.s3.generate_presigned_put_url") as mock_s3:
        mock_s3.return_value = "https://s3.example.com/presigned-url"
        
        response = client_with_uploads.post(
            "/api/uploads/initiate",
            json={
                "filename": "scorecard.jpg",
                "file_type": "image/jpeg",
                "game_id": "test-game-123",
            },
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "upload_id" in data


def test_complete_upload_success(client_with_uploads):
    """Test completing an upload."""
    # First initiate an upload
    with patch("backend.utils.s3.generate_presigned_put_url") as mock_s3:
        mock_s3.return_value = "https://s3.example.com/presigned-url"
        
        init_response = client_with_uploads.post(
            "/api/uploads/initiate",
            json={
                "filename": "scorecard.pdf",
                "file_type": "application/pdf",
            },
        )
        upload_data = init_response.json()
    
    # Mock the enqueue function
    with patch("backend.routes.uploads.enqueue_processing_job") as mock_enqueue:
        mock_enqueue.return_value = "task-123"
        
        # Now complete it
        response = client_with_uploads.post(
            "/api/uploads/complete",
            json={
                "upload_id": upload_data["upload_id"],
                "s3_key": upload_data["s3_key"],
                "size": 1024,
                "checksum": "abc123",
            },
        )
        
        assert response.status_code == 202
        data = response.json()
        assert data["upload_id"] == upload_data["upload_id"]
        assert data["status"] == "processing"


def test_complete_upload_key_mismatch(client_with_uploads):
    """Test completing upload with mismatched s3_key."""
    # First initiate an upload
    with patch("backend.utils.s3.generate_presigned_put_url") as mock_s3:
        mock_s3.return_value = "https://s3.example.com/presigned-url"
        
        init_response = client_with_uploads.post(
            "/api/uploads/initiate",
            json={
                "filename": "scorecard.pdf",
                "file_type": "application/pdf",
            },
        )
        upload_data = init_response.json()
    
    # Try to complete with wrong s3_key
    response = client_with_uploads.post(
        "/api/uploads/complete",
        json={
            "upload_id": upload_data["upload_id"],
            "s3_key": "wrong/key",
            "size": 1024,
        },
    )
    
    assert response.status_code == 400
    assert "mismatch" in response.json()["detail"].lower()


def test_get_upload_status(client_with_uploads):
    """Test getting upload status."""
    # First initiate an upload
    with patch("backend.utils.s3.generate_presigned_put_url") as mock_s3:
        mock_s3.return_value = "https://s3.example.com/presigned-url"
        
        init_response = client_with_uploads.post(
            "/api/uploads/initiate",
            json={
                "filename": "scorecard.pdf",
                "file_type": "application/pdf",
            },
        )
        upload_data = init_response.json()
    
    # Get status
    response = client_with_uploads.get(
        f"/api/uploads/{upload_data['upload_id']}/status"
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["upload_id"] == upload_data["upload_id"]
    assert data["status"] == "pending"
    assert data["filename"] == "scorecard.pdf"
    assert data["file_type"] == "application/pdf"


def test_get_upload_status_not_found(client_with_uploads):
    """Test getting status for non-existent upload."""
    response = client_with_uploads.get(
        "/api/uploads/nonexistent-id/status"
    )
    
    assert response.status_code == 404


def test_apply_upload_not_ready(client_with_uploads):
    """Test applying upload that is not ready."""
    # First initiate an upload
    with patch("backend.utils.s3.generate_presigned_put_url") as mock_s3:
        mock_s3.return_value = "https://s3.example.com/presigned-url"
        
        init_response = client_with_uploads.post(
            "/api/uploads/initiate",
            json={
                "filename": "scorecard.pdf",
                "file_type": "application/pdf",
            },
        )
        upload_data = init_response.json()
    
    # Try to apply it (should fail as it's still pending)
    response = client_with_uploads.post(
        f"/api/uploads/{upload_data['upload_id']}/apply",
        json={"game_id": "test-game-123"},
    )
    
    assert response.status_code == 400
    assert "not ready" in response.json()["detail"].lower()


def test_uploads_disabled_by_default():
    """Test that uploads are disabled by default."""
    from backend.main import fastapi_app
    client = TestClient(fastapi_app)
    
    response = client.post(
        "/api/uploads/initiate",
        json={
            "filename": "scorecard.pdf",
            "file_type": "application/pdf",
        },
    )
    
    # Should return 503 or 404 when disabled
    assert response.status_code in [404, 503]
