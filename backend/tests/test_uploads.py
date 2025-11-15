"""Tests for upload routes and functionality."""
from __future__ import annotations

import os
import uuid
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


# Skip tests if S3 credentials not available (CI-safe)
def _has_s3_config() -> bool:
    """Check if S3 configuration is available."""
    return bool(
        os.getenv("S3_ACCESS_KEY_ID")
        and os.getenv("S3_SECRET_ACCESS_KEY")
    )


pytestmark = pytest.mark.skipif(
    not _has_s3_config(),
    reason="S3 credentials not configured (set S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY)",
)


@pytest.fixture
def mock_s3():
    """Mock S3 client for testing without real S3."""
    with patch("backend.utils.s3._get_s3_client") as mock:
        mock_client = MagicMock()
        mock_client.generate_presigned_url.return_value = "https://example.com/upload"
        mock.return_value = mock_client
        yield mock_client


class TestUploadRoutes:
    """Test upload API routes."""

    def test_initiate_upload_creates_record(self, client: TestClient, mock_s3):
        """Test that initiating upload creates database record."""
        response = client.post(
            "/api/uploads/initiate",
            json={
                "filename": "test_scorecard.png",
                "content_type": "image/png",
                "file_size": 102400,
                "uploader_name": "Test User",
            },
        )

        assert response.status_code == 200
        data = response.json()

        assert "upload_id" in data
        assert data["upload_method"] == "PUT"
        assert data["s3_bucket"] == "cricksy-uploads"
        assert "upload_url" in data

    def test_initiate_upload_file_too_large(self, client: TestClient):
        """Test that large files are rejected."""
        response = client.post(
            "/api/uploads/initiate",
            json={
                "filename": "huge_file.png",
                "content_type": "image/png",
                "file_size": 50 * 1024 * 1024,  # 50MB
            },
        )

        assert response.status_code == 413

    def test_complete_upload_updates_status(self, client: TestClient, mock_s3):
        """Test completing upload updates status."""
        # First initiate
        init_response = client.post(
            "/api/uploads/initiate",
            json={
                "filename": "test.png",
                "content_type": "image/png",
            },
        )
        upload_id = init_response.json()["upload_id"]

        # Mock Celery task
        with patch("backend.routes.uploads.process_scorecard_task") as mock_task:
            mock_task.delay = MagicMock()

            # Complete upload
            response = client.post(
                "/api/uploads/complete",
                json={"upload_id": upload_id},
            )

            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "uploaded"

    def test_get_upload_status(self, client: TestClient, mock_s3):
        """Test getting upload status."""
        # Create upload
        init_response = client.post(
            "/api/uploads/initiate",
            json={"filename": "test.png"},
        )
        upload_id = init_response.json()["upload_id"]

        # Get status
        response = client.get(f"/api/uploads/status/{upload_id}")

        assert response.status_code == 200
        data = response.json()
        assert data["upload_id"] == upload_id
        assert data["status"] == "pending"
        assert data["filename"] == "test.png"

    def test_apply_upload_requires_confirmation(self, client: TestClient, mock_s3):
        """Test that apply requires confirmation."""
        # Create and mark as parsed
        init_response = client.post(
            "/api/uploads/initiate",
            json={"filename": "test.png"},
        )
        upload_id = init_response.json()["upload_id"]

        # Try to apply without confirmation
        response = client.post(
            "/api/uploads/apply",
            json={
                "upload_id": upload_id,
                "confirmation": False,
            },
        )

        assert response.status_code == 400
        assert "confirmation required" in response.json()["detail"].lower()

    def test_apply_upload_wrong_status(self, client: TestClient, mock_s3):
        """Test that apply requires parsed status."""
        # Create upload (will be in pending state)
        init_response = client.post(
            "/api/uploads/initiate",
            json={"filename": "test.png"},
        )
        upload_id = init_response.json()["upload_id"]

        # Try to apply (should fail - not in parsed state)
        response = client.post(
            "/api/uploads/apply",
            json={
                "upload_id": upload_id,
                "confirmation": True,
            },
        )

        assert response.status_code == 400
        assert "parsed" in response.json()["detail"].lower()


class TestUploadFeatureFlag:
    """Test upload feature flag."""

    def test_uploads_disabled_when_flag_off(self, client: TestClient):
        """Test that uploads return 503 when feature disabled."""
        with patch("backend.routes.uploads.settings") as mock_settings:
            mock_settings.ENABLE_UPLOADS = False

            response = client.post(
                "/api/uploads/initiate",
                json={"filename": "test.png"},
            )

            assert response.status_code == 503
            assert "not enabled" in response.json()["detail"].lower()


# Additional tests can be added without S3 skip marker
class TestUploadModel:
    """Test upload model."""

    def test_upload_status_enum(self):
        """Test upload status enum values."""
        from backend.sql_app.models.upload import UploadStatus

        assert UploadStatus.pending.value == "pending"
        assert UploadStatus.uploaded.value == "uploaded"
        assert UploadStatus.processing.value == "processing"
        assert UploadStatus.parsed.value == "parsed"
        assert UploadStatus.applied.value == "applied"
        assert UploadStatus.failed.value == "failed"
        assert UploadStatus.rejected.value == "rejected"
