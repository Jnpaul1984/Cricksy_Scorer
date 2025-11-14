"""Unit tests for upload functionality.

Tests skip integration scenarios requiring S3/Redis if environment variables are not set.
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest
from fastapi import status

from backend.config import settings
from backend.sql_app.models import Upload, UploadStatus

# Check if S3 credentials are available for integration tests
S3_AVAILABLE = bool(settings.S3_ACCESS_KEY and settings.S3_SECRET_KEY)


class TestUploadModel:
    """Test Upload model."""

    def test_upload_status_enum_values(self):
        """Test that UploadStatus enum has expected values."""
        assert UploadStatus.initiated.value == "initiated"
        assert UploadStatus.uploaded.value == "uploaded"
        assert UploadStatus.processing.value == "processing"
        assert UploadStatus.parsed.value == "parsed"
        assert UploadStatus.applied.value == "applied"
        assert UploadStatus.failed.value == "failed"
        assert UploadStatus.cancelled.value == "cancelled"


class TestInitiateUpload:
    """Test POST /api/uploads/initiate endpoint."""

    @pytest.mark.asyncio
    async def test_initiate_upload_success(self, async_client, async_db):
        """Test successful upload initiation."""
        with patch("backend.routes.uploads.generate_presigned_upload_url") as mock_presigned:
            mock_presigned.return_value = "https://example.com/presigned-url"

            response = await async_client.post(
                "/api/uploads/initiate",
                json={
                    "filename": "scorecard.jpg",
                    "content_type": "image/jpeg",
                    "game_id": "game-123",
                    "user_id": "user-456",
                },
            )

            assert response.status_code == status.HTTP_201_CREATED
            data = response.json()
            assert "upload_id" in data
            assert data["presigned_url"] == "https://example.com/presigned-url"
            assert data["s3_bucket"] == settings.S3_BUCKET
            assert "s3_key" in data
            assert data["expires_in"] == settings.S3_PRESIGNED_URL_EXPIRY

    @pytest.mark.asyncio
    async def test_initiate_upload_invalid_content_type(self, async_client):
        """Test upload initiation with invalid content type."""
        response = await async_client.post(
            "/api/uploads/initiate",
            json={
                "filename": "scorecard.txt",
                "content_type": "text/plain",
            },
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "not allowed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_initiate_upload_feature_disabled(self, async_client):
        """Test upload initiation when feature is disabled."""
        with patch.object(settings, "ENABLE_UPLOADS", False):
            response = await async_client.post(
                "/api/uploads/initiate",
                json={
                    "filename": "scorecard.jpg",
                    "content_type": "image/jpeg",
                },
            )

            assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
            assert "disabled" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_initiate_upload_missing_filename(self, async_client):
        """Test upload initiation with missing filename."""
        response = await async_client.post(
            "/api/uploads/initiate",
            json={
                "content_type": "image/jpeg",
            },
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY


class TestCompleteUpload:
    """Test POST /api/uploads/{upload_id}/complete endpoint."""

    @pytest.mark.asyncio
    async def test_complete_upload_success(self, async_client, async_db):
        """Test marking upload as complete."""
        # Create an initiated upload
        upload = Upload(
            id="test-upload-123",
            filename="test.jpg",
            content_type="image/jpeg",
            s3_bucket="test-bucket",
            s3_key="uploads/test.jpg",
            status=UploadStatus.initiated,
        )
        async_db.add(upload)
        await async_db.commit()

        with patch("backend.routes.uploads.process_upload_task") as mock_task:
            mock_task.delay = MagicMock()

            response = await async_client.post(
                "/api/uploads/test-upload-123/complete",
                json={"file_size": 12345},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["upload_id"] == "test-upload-123"

    @pytest.mark.asyncio
    async def test_complete_upload_not_found(self, async_client):
        """Test completing non-existent upload."""
        response = await async_client.post(
            "/api/uploads/nonexistent/complete",
            json={},
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    @pytest.mark.asyncio
    async def test_complete_upload_wrong_status(self, async_client, async_db):
        """Test completing upload that's not in initiated state."""
        upload = Upload(
            id="test-upload-456",
            filename="test.jpg",
            content_type="image/jpeg",
            s3_bucket="test-bucket",
            s3_key="uploads/test.jpg",
            status=UploadStatus.uploaded,  # Already uploaded
        )
        async_db.add(upload)
        await async_db.commit()

        response = await async_client.post(
            "/api/uploads/test-upload-456/complete",
            json={},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST


class TestGetUploadStatus:
    """Test GET /api/uploads/{upload_id}/status endpoint."""

    @pytest.mark.asyncio
    async def test_get_upload_status_success(self, async_client, async_db):
        """Test retrieving upload status."""
        upload = Upload(
            id="test-upload-789",
            filename="test.jpg",
            content_type="image/jpeg",
            s3_bucket="test-bucket",
            s3_key="uploads/test.jpg",
            status=UploadStatus.parsed,
            parsed_preview={"deliveries": []},
        )
        async_db.add(upload)
        await async_db.commit()

        response = await async_client.get("/api/uploads/test-upload-789/status")

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["upload_id"] == "test-upload-789"
        assert data["status"] == "parsed"
        assert data["filename"] == "test.jpg"
        assert "parsed_preview" in data

    @pytest.mark.asyncio
    async def test_get_upload_status_not_found(self, async_client):
        """Test retrieving status of non-existent upload."""
        response = await async_client.get("/api/uploads/nonexistent/status")

        assert response.status_code == status.HTTP_404_NOT_FOUND


class TestApplyUpload:
    """Test POST /api/uploads/{upload_id}/apply endpoint."""

    @pytest.mark.asyncio
    async def test_apply_upload_success(self, async_client, async_db):
        """Test applying parsed upload data."""
        upload = Upload(
            id="test-upload-apply-1",
            filename="test.jpg",
            content_type="image/jpeg",
            s3_bucket="test-bucket",
            s3_key="uploads/test.jpg",
            status=UploadStatus.parsed,
            parsed_preview={"deliveries": [{"over": 1, "ball": 1}]},
            game_id="game-123",
        )
        async_db.add(upload)
        await async_db.commit()

        with patch("backend.routes.uploads.emit_game_update") as mock_emit:
            response = await async_client.post(
                "/api/uploads/test-upload-apply-1/apply",
                json={"confirm": True},
            )

            assert response.status_code == status.HTTP_200_OK
            data = response.json()
            assert data["upload_id"] == "test-upload-apply-1"
            assert data["game_id"] == "game-123"

    @pytest.mark.asyncio
    async def test_apply_upload_no_confirmation(self, async_client, async_db):
        """Test applying upload without confirmation."""
        upload = Upload(
            id="test-upload-apply-2",
            filename="test.jpg",
            content_type="image/jpeg",
            s3_bucket="test-bucket",
            s3_key="uploads/test.jpg",
            status=UploadStatus.parsed,
            parsed_preview={"deliveries": []},
        )
        async_db.add(upload)
        await async_db.commit()

        response = await async_client.post(
            "/api/uploads/test-upload-apply-2/apply",
            json={"confirm": False},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "confirmation required" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_apply_upload_wrong_status(self, async_client, async_db):
        """Test applying upload that's not in parsed state."""
        upload = Upload(
            id="test-upload-apply-3",
            filename="test.jpg",
            content_type="image/jpeg",
            s3_bucket="test-bucket",
            s3_key="uploads/test.jpg",
            status=UploadStatus.uploaded,  # Not yet parsed
            parsed_preview={},
        )
        async_db.add(upload)
        await async_db.commit()

        response = await async_client.post(
            "/api/uploads/test-upload-apply-3/apply",
            json={"confirm": True},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "parsed" in response.json()["detail"].lower()

    @pytest.mark.asyncio
    async def test_apply_upload_no_parsed_data(self, async_client, async_db):
        """Test applying upload with no parsed preview data."""
        upload = Upload(
            id="test-upload-apply-4",
            filename="test.jpg",
            content_type="image/jpeg",
            s3_bucket="test-bucket",
            s3_key="uploads/test.jpg",
            status=UploadStatus.parsed,
            parsed_preview={},  # Empty preview
        )
        async_db.add(upload)
        await async_db.commit()

        response = await async_client.post(
            "/api/uploads/test-upload-apply-4/apply",
            json={"confirm": True},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST

    @pytest.mark.asyncio
    async def test_apply_upload_missing_required_fields(self, async_client, async_db):
        """Test applying upload with missing required fields."""
        upload = Upload(
            id="test-upload-apply-5",
            filename="test.jpg",
            content_type="image/jpeg",
            s3_bucket="test-bucket",
            s3_key="uploads/test.jpg",
            status=UploadStatus.parsed,
            parsed_preview={"some_field": "value"},  # Missing 'deliveries'
        )
        async_db.add(upload)
        await async_db.commit()

        response = await async_client.post(
            "/api/uploads/test-upload-apply-5/apply",
            json={"confirm": True},
        )

        assert response.status_code == status.HTTP_400_BAD_REQUEST
        assert "required field" in response.json()["detail"].lower()


@pytest.mark.skipif(not S3_AVAILABLE, reason="S3 credentials not available")
class TestS3Integration:
    """Integration tests requiring actual S3/MinIO connection.

    These tests are skipped unless S3 credentials are provided via environment variables.
    """

    @pytest.mark.asyncio
    async def test_s3_presigned_url_generation(self):
        """Test actual presigned URL generation with S3/MinIO."""
        from backend.utils.s3 import generate_presigned_upload_url

        url = generate_presigned_upload_url(
            bucket=settings.S3_BUCKET,
            key="test/upload.jpg",
            content_type="image/jpeg",
            expiration=3600,
        )

        assert url.startswith("http")
        assert settings.S3_BUCKET in url
