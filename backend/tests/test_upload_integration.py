"""Integration tests for upload workflow and WebSocket emissions.

These tests verify:
1. Upload workflow from initiate to apply
2. WebSocket emissions for upload events
3. Compact delta emissions
"""

from __future__ import annotations

import os
from unittest.mock import MagicMock, patch

import pytest

# Skip integration tests if required env vars are not set
SKIP_INTEGRATION = not (
    os.getenv("CRICKSY_S3_ACCESS_KEY") and os.getenv("CRICKSY_REDIS_URL")
)

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.skipif(SKIP_INTEGRATION, reason="S3/Redis credentials not available"),
]


class TestUploadIntegration:
    """Integration tests for upload workflow."""

    async def test_full_upload_workflow(self, async_client):
        """Test complete upload workflow: initiate -> upload -> complete -> apply."""
        # This is a placeholder for a full integration test
        # In a real environment with S3 and Redis, this would:
        # 1. Initiate an upload
        # 2. Upload a real image file to the presigned URL
        # 3. Complete the upload
        # 4. Wait for OCR processing
        # 5. Apply the results

    async def test_upload_triggers_websocket_broadcast(self, async_client):
        """Test that applying an upload triggers WebSocket broadcast."""
        # This would test that emit_to_game is called when an upload is applied


class TestWebSocketMetrics:
    """Tests for WebSocket metrics and compact emissions."""

    async def test_ws_metrics_endpoint(self, async_client):
        """Test WebSocket metrics endpoint returns expected data."""
        response = await async_client.get("/api/health/ws-metrics")
        assert response.status_code == 200

        data = response.json()
        assert "total_emits" in data
        assert "total_payload_bytes" in data
        assert "avg_emit_duration_ms" in data
        assert "max_emit_duration_ms" in data
        assert "uptime_seconds" in data

        # Check types
        assert isinstance(data["total_emits"], (int, float))
        assert isinstance(data["total_payload_bytes"], (int, float))
        assert isinstance(data["avg_emit_duration_ms"], (int, float))
        assert isinstance(data["max_emit_duration_ms"], (int, float))
        assert isinstance(data["uptime_seconds"], (int, float))

    async def test_compact_delta_emission(self):
        """Test that emit_compact_delta tracks metrics correctly."""
        from backend.socket_handlers import emit_compact_delta, get_ws_metrics, reset_ws_metrics

        # Reset metrics
        reset_ws_metrics()

        # Mock socket.io server
        mock_sio = MagicMock()
        mock_sio.emit = MagicMock(return_value=None)

        # Emit a delta
        test_delta = {"game_id": "test-123", "score": 100}
        await emit_compact_delta(mock_sio, "score:update", test_delta, "test-room")

        # Check metrics were updated
        metrics = get_ws_metrics()
        assert metrics["total_emits"] == 1
        assert metrics["total_payload_bytes"] > 0
        assert len(metrics["avg_emit_duration_ms"]) > 0  # Should have duration

        # Verify socket.io emit was called
        mock_sio.emit.assert_called_once_with("score:update", test_delta, room="test-room")


class TestRedisAdapter:
    """Tests for Redis adapter configuration."""

    @pytest.mark.skipif(not os.getenv("CRICKSY_REDIS_URL"), reason="Redis not available")
    def test_redis_adapter_initialization(self):
        """Test that Redis adapter can be initialized when enabled."""
        with patch("backend.app.default_settings.USE_REDIS_ADAPTER", True):
            from backend.app import create_app

            app, fastapi_app = create_app()
            # If this doesn't raise an exception, Redis adapter initialized successfully
            assert app is not None
            assert fastapi_app is not None


@pytest.fixture
async def async_client():
    """Fixture for async HTTP client."""
    from httpx import AsyncClient

    from backend.main import app

    async with AsyncClient(app=app, base_url="http://test") as client:
        yield client
