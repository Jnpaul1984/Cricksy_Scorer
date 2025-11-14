"""Tests for upload endpoints."""
from __future__ import annotations

import os
from typing import Any
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from backend.main import app

# Skip integration tests unless env vars are set
SKIP_INTEGRATION = not (
    os.getenv("CRICKSY_S3_ACCESS_KEY") and 
    os.getenv("CRICKSY_S3_SECRET_KEY")
)

# Marker for integration tests
pytestmark = pytest.mark.skipif(
    SKIP_INTEGRATION,
    reason="Integration tests require S3 credentials (set CRICKSY_S3_ACCESS_KEY and CRICKSY_S3_SECRET_KEY)"
)


@pytest.fixture
def client() -> TestClient:
    """Create a test client."""
    return TestClient(app)


@pytest.fixture
def mock_s3_client():
    """Mock boto3 S3 client."""
    with patch("backend.utils.s3.get_s3_client") as mock:
        client = MagicMock()
        client.generate_presigned_url.return_value = "https://s3.example.com/presigned-url"
        client.head_bucket.return_value = {}
        mock.return_value = client
        yield mock


class TestUploadsEndpoints:
    """Test suite for upload endpoints."""
    
    def test_initiate_upload_disabled(self, client: TestClient):
        """Test initiate upload when feature is disabled."""
        with patch("backend.config.settings.ENABLE_UPLOADS", False):
            response = client.post(
                "/api/uploads/initiate",
                json={
                    "filename": "scorecard.jpg",
                    "content_type": "image/jpeg",
                    "uploader_id": "user123"
                }
            )
            assert response.status_code == 403
            assert "disabled" in response.json()["detail"].lower()
    
    def test_initiate_upload_no_credentials(self, client: TestClient):
        """Test initiate upload without S3 credentials."""
        with patch("backend.config.settings.ENABLE_UPLOADS", True), \
             patch("backend.config.settings.S3_ACCESS_KEY", ""), \
             patch("backend.config.settings.S3_SECRET_KEY", ""):
            response = client.post(
                "/api/uploads/initiate",
                json={
                    "filename": "scorecard.jpg",
                    "content_type": "image/jpeg",
                    "uploader_id": "user123"
                }
            )
            assert response.status_code == 503
            assert "credentials" in response.json()["detail"].lower()
    
    def test_initiate_upload_success(self, client: TestClient, mock_s3_client):
        """Test successful upload initiation."""
        with patch("backend.config.settings.ENABLE_UPLOADS", True), \
             patch("backend.config.settings.S3_ACCESS_KEY", "test-key"), \
             patch("backend.config.settings.S3_SECRET_KEY", "test-secret"):
            response = client.post(
                "/api/uploads/initiate",
                json={
                    "filename": "scorecard.jpg",
                    "content_type": "image/jpeg",
                    "uploader_id": "user123",
                    "game_id": 1
                }
            )
            assert response.status_code == 200
            data = response.json()
            assert "upload_id" in data
            assert "presigned_url" in data
            assert "s3_key" in data
            assert data["expires_in"] == 3600
            assert "user123" in data["s3_key"]
    
    def test_initiate_upload_validation(self, client: TestClient):
        """Test upload initiation validation."""
        with patch("backend.config.settings.ENABLE_UPLOADS", True):
            # Empty filename
            response = client.post(
                "/api/uploads/initiate",
                json={
                    "filename": "",
                    "content_type": "image/jpeg",
                    "uploader_id": "user123"
                }
            )
            assert response.status_code == 422
            
            # Missing required fields
            response = client.post(
                "/api/uploads/initiate",
                json={
                    "filename": "test.jpg"
                }
            )
            assert response.status_code == 422
    
    def test_complete_upload_not_found(self, client: TestClient):
        """Test complete upload with non-existent upload."""
        with patch("backend.config.settings.ENABLE_UPLOADS", True):
            response = client.post(
                "/api/uploads/complete",
                json={"upload_id": 99999}
            )
            assert response.status_code == 404
    
    def test_get_upload_status_not_found(self, client: TestClient):
        """Test get status for non-existent upload."""
        with patch("backend.config.settings.ENABLE_UPLOADS", True):
            response = client.get("/api/uploads/99999/status")
            assert response.status_code == 404
    
    def test_apply_upload_without_confirmation(self, client: TestClient):
        """Test apply upload without explicit confirmation."""
        with patch("backend.config.settings.ENABLE_UPLOADS", True):
            response = client.post(
                "/api/uploads/1/apply",
                json={"confirmation": False}
            )
            assert response.status_code == 400
            assert "confirmation" in response.json()["detail"].lower()
    
    def test_apply_upload_not_found(self, client: TestClient):
        """Test apply upload with non-existent upload."""
        with patch("backend.config.settings.ENABLE_UPLOADS", True):
            response = client.post(
                "/api/uploads/99999/apply",
                json={"confirmation": True}
            )
            assert response.status_code == 404


class TestS3Utilities:
    """Test S3 utility functions."""
    
    def test_generate_upload_key(self):
        """Test S3 key generation."""
        from backend.utils.s3 import generate_upload_key
        
        key = generate_upload_key("test.jpg", "user123")
        assert key.startswith("uploads/user123/")
        assert key.endswith("/test.jpg")
        
        # Test path traversal prevention
        key = generate_upload_key("../../../etc/passwd", "user123")
        assert ".." not in key
        assert "etc_passwd" in key
    
    def test_check_s3_connection_no_credentials(self):
        """Test S3 connection check without credentials."""
        from backend.utils.s3 import check_s3_connection
        
        with patch("backend.config.settings.S3_ACCESS_KEY", ""), \
             patch("backend.config.settings.S3_SECRET_KEY", ""):
            assert check_s3_connection() is False
    
    def test_check_s3_connection_success(self, mock_s3_client):
        """Test successful S3 connection check."""
        from backend.utils.s3 import check_s3_connection
        
        with patch("backend.config.settings.S3_ACCESS_KEY", "test-key"), \
             patch("backend.config.settings.S3_SECRET_KEY", "test-secret"):
            assert check_s3_connection() is True


class TestUploadModel:
    """Test Upload model."""
    
    def test_upload_status_enum(self):
        """Test UploadStatus enum values."""
        from backend.sql_app.models import UploadStatus
        
        assert UploadStatus.pending.value == "pending"
        assert UploadStatus.processing.value == "processing"
        assert UploadStatus.ready.value == "ready"
        assert UploadStatus.failed.value == "failed"
    
    def test_upload_model_repr(self):
        """Test Upload model repr."""
        from backend.sql_app.models import Upload, UploadStatus
        
        upload = Upload(
            id=1,
            uploader_id="user123",
            filename="test.jpg",
            file_type="image/jpeg",
            s3_key="uploads/user123/uuid/test.jpg",
            status=UploadStatus.pending,
            upload_metadata={}
        )
        
        repr_str = repr(upload)
        assert "Upload" in repr_str
        assert "id=1" in repr_str
        assert "test.jpg" in repr_str


# Integration tests that require actual S3/MinIO
@pytest.mark.integration
@pytest.mark.skipif(SKIP_INTEGRATION, reason="Requires S3 credentials")
class TestUploadIntegration:
    """Integration tests for uploads (require S3/MinIO)."""
    
    def test_full_upload_flow(self, client: TestClient):
        """Test complete upload flow with real S3."""
        # This test would require actual S3/MinIO setup
        # For now, it's a placeholder for when integration testing is set up
        pass
