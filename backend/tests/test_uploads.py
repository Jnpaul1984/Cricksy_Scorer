"""Unit tests for upload functionality."""

from __future__ import annotations

import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from httpx import AsyncClient

# Set environment to skip integration tests by default
SKIP_INTEGRATION = not os.getenv("CRICKSY_S3_ACCESS_KEY") or not os.getenv("CRICKSY_REDIS_URL")

pytestmark = pytest.mark.asyncio


@pytest.fixture
def mock_s3_client():
    """Mock boto3 S3 client."""
    with patch("backend.utils.s3.boto3.client") as mock_client:
        mock_s3 = MagicMock()
        mock_client.return_value = mock_s3
        mock_s3.generate_presigned_url.return_value = "https://example.com/upload-url"
        mock_s3.head_bucket.return_value = {}
        yield mock_s3


class TestUploadRoutes:
    """Test upload API endpoints."""

    @pytest.mark.skipif(SKIP_INTEGRATION, reason="S3 credentials not available")
    async def test_initiate_upload_integration(self, async_client: AsyncClient):
        """Integration test for initiate upload (requires S3 credentials)."""
        response = await async_client.post(
            "/api/uploads/initiate",
            json={"filename": "scorecard.jpg", "content_type": "image/jpeg"},
        )
        assert response.status_code == 200
        data = response.json()
        assert "upload_id" in data
        assert "upload_url" in data
        assert "s3_key" in data
        assert "expires_in" in data

    async def test_initiate_upload_unit(self, async_client: AsyncClient, mock_s3_client):
        """Unit test for initiate upload with mocked S3."""
        with patch("backend.routes.uploads.settings.ENABLE_UPLOADS", True):
            response = await async_client.post(
                "/api/uploads/initiate",
                json={"filename": "scorecard.jpg", "content_type": "image/jpeg"},
            )

            assert response.status_code == 200
            data = response.json()
            assert "upload_id" in data
            assert "upload_url" in data
            assert data["upload_url"] == "https://example.com/upload-url"
            assert "scorecard.jpg" in data["s3_key"]

    async def test_initiate_upload_disabled(self, async_client: AsyncClient, mock_s3_client):
        """Test initiate upload when feature is disabled."""
        with patch("backend.routes.uploads.settings.ENABLE_UPLOADS", False):
            response = await async_client.post(
                "/api/uploads/initiate",
                json={"filename": "scorecard.jpg"},
            )
            assert response.status_code == 503
            assert "disabled" in response.json()["detail"].lower()

    async def test_complete_upload(self, async_client: AsyncClient, mock_s3_client):
        """Test completing an upload."""
        # First initiate an upload
        with patch("backend.routes.uploads.settings.ENABLE_UPLOADS", True):
            init_response = await async_client.post(
                "/api/uploads/initiate",
                json={"filename": "test.jpg"},
            )
            upload_id = init_response.json()["upload_id"]

            # Complete the upload
            with patch("backend.routes.uploads.settings.ENABLE_OCR", False):
                complete_response = await async_client.post(
                    "/api/uploads/complete",
                    json={"upload_id": upload_id},
                )
                assert complete_response.status_code == 200
                assert complete_response.json()["status"] == "uploaded"

    async def test_complete_upload_not_found(self, async_client: AsyncClient):
        """Test completing a non-existent upload."""
        response = await async_client.post(
            "/api/uploads/complete",
            json={"upload_id": "non-existent-id"},
        )
        assert response.status_code == 404

    async def test_get_upload_status(self, async_client: AsyncClient, mock_s3_client):
        """Test getting upload status."""
        # Create an upload
        with patch("backend.routes.uploads.settings.ENABLE_UPLOADS", True):
            init_response = await async_client.post(
                "/api/uploads/initiate",
                json={"filename": "test.jpg"},
            )
            upload_id = init_response.json()["upload_id"]

            # Get status
            status_response = await async_client.get(f"/api/uploads/{upload_id}/status")
            assert status_response.status_code == 200
            data = status_response.json()
            assert data["upload_id"] == upload_id
            assert data["status"] == "pending"
            assert data["filename"] == "test.jpg"

    async def test_get_upload_status_not_found(self, async_client: AsyncClient):
        """Test getting status for non-existent upload."""
        response = await async_client.get("/api/uploads/non-existent-id/status")
        assert response.status_code == 404

    async def test_apply_upload_requires_confirmation(self, async_client: AsyncClient, mock_s3_client):
        """Test that apply endpoint requires explicit confirmation."""
        # Create and complete an upload
        with patch("backend.routes.uploads.settings.ENABLE_UPLOADS", True):
            init_response = await async_client.post(
                "/api/uploads/initiate",
                json={"filename": "test.jpg"},
            )
            upload_id = init_response.json()["upload_id"]

            # Try to apply without confirmation
            apply_response = await async_client.post(
                f"/api/uploads/{upload_id}/apply",
                json={"upload_id": upload_id, "confirm": False},
            )
            assert apply_response.status_code == 400
            assert "confirmation" in apply_response.json()["detail"].lower()

    async def test_apply_upload_requires_completed_status(self, async_client: AsyncClient, mock_s3_client):
        """Test that apply endpoint requires completed status."""
        # Create an upload (status will be 'pending')
        with patch("backend.routes.uploads.settings.ENABLE_UPLOADS", True):
            init_response = await async_client.post(
                "/api/uploads/initiate",
                json={"filename": "test.jpg"},
            )
            upload_id = init_response.json()["upload_id"]

            # Try to apply with pending status
            apply_response = await async_client.post(
                f"/api/uploads/{upload_id}/apply",
                json={"upload_id": upload_id, "confirm": True},
            )
            assert apply_response.status_code == 400
            assert "completed" in apply_response.json()["detail"].lower()

    async def test_apply_upload_success(self, async_client: AsyncClient, mock_s3_client):
        """Test successful application of upload."""
        # This test would require mocking the database to set status to 'completed'
        # For now, we test the validation logic above
        pass


class TestS3Utils:
    """Test S3 utility functions."""

    def test_get_s3_client_minio(self, mock_s3_client):
        """Test S3 client creation for MinIO."""
        with patch("backend.utils.s3.settings.S3_ENDPOINT_URL", "http://localhost:9000"):
            from backend.utils.s3 import get_s3_client

            client = get_s3_client()
            assert client is not None

    def test_get_s3_client_aws(self, mock_s3_client):
        """Test S3 client creation for AWS."""
        with patch("backend.utils.s3.settings.S3_ENDPOINT_URL", None):
            from backend.utils.s3 import get_s3_client

            client = get_s3_client()
            assert client is not None

    def test_generate_presigned_upload_url(self, mock_s3_client):
        """Test presigned upload URL generation."""
        with patch("backend.utils.s3.settings.ENABLE_UPLOADS", True):
            from backend.utils.s3 import generate_presigned_upload_url

            url = generate_presigned_upload_url("test-key", "image/jpeg")
            assert url == "https://example.com/upload-url"
            mock_s3_client.generate_presigned_url.assert_called_once()

    def test_generate_presigned_upload_url_disabled(self, mock_s3_client):
        """Test presigned URL generation when uploads disabled."""
        with patch("backend.utils.s3.settings.ENABLE_UPLOADS", False):
            from backend.utils.s3 import generate_presigned_upload_url

            url = generate_presigned_upload_url("test-key", "image/jpeg")
            assert url is None

    def test_generate_presigned_download_url(self, mock_s3_client):
        """Test presigned download URL generation."""
        from backend.utils.s3 import generate_presigned_download_url

        url = generate_presigned_download_url("test-key")
        assert url == "https://example.com/upload-url"

    def test_check_s3_connection_success(self, mock_s3_client):
        """Test successful S3 connection check."""
        from backend.utils.s3 import check_s3_connection

        result = check_s3_connection()
        assert result is True
        mock_s3_client.head_bucket.assert_called_once()

    def test_check_s3_connection_failure(self, mock_s3_client):
        """Test failed S3 connection check."""
        from backend.utils.s3 import check_s3_connection

        mock_s3_client.head_bucket.side_effect = Exception("Connection failed")
        result = check_s3_connection()
        assert result is False


@pytest.fixture
async def async_client():
    """Fixture for async HTTP client."""
    from backend.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
