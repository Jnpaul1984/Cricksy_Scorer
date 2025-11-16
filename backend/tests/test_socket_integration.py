"""Integration tests for socket emissions and upload broadcasts."""
from __future__ import annotations

import asyncio
import os
from unittest.mock import MagicMock, patch

import pytest


# Skip if Redis not available
pytestmark = pytest.mark.skipif(
    not os.getenv("REDIS_URL"),
    reason="Redis not configured (set REDIS_URL for integration tests)",
)


class TestSocketEmissions:
    """Test WebSocket/Socket.IO emissions."""

    def test_socket_metrics_endpoint(self, client):
        """Test that ws-metrics endpoint returns metrics."""
        response = client.get("/api/health/ws-metrics")
        assert response.status_code == 200

        data = response.json()
        assert "connections" in data
        assert "disconnections" in data
        assert "joins" in data
        assert "leaves" in data
        assert "messages_sent" in data
        assert "errors" in data
        assert "active_connections" in data
        assert "active_rooms" in data
        assert "timestamp" in data

    @pytest.mark.asyncio
    async def test_compact_delta_emission(self):
        """Test that compact delta events are emitted correctly."""
        from backend.socket_handlers import emit_compact_delta

        mock_sio = MagicMock()
        mock_sio.emit = MagicMock()

        game_id = "test-game-123"
        event_type = "score_update"
        delta = {
            "runs": 4,
            "total_runs": 150,
            "overs": 15.3,
        }

        emit_compact_delta(mock_sio, game_id, event_type, delta)

        # Verify emit was called
        mock_sio.emit.assert_called_once()
        args = mock_sio.emit.call_args

        # Check event name
        assert args[0][0] == "game:delta"

        # Check payload structure
        payload = args[0][1]
        assert payload["type"] == event_type
        assert payload["game_id"] == game_id
        assert payload["delta"] == delta
        assert "timestamp" in payload

        # Check room
        assert args[1]["room"] == game_id

    @pytest.mark.asyncio
    async def test_socket_handler_metrics(self):
        """Test that socket handlers update metrics."""
        from backend.socket_handlers import get_metrics, register_sio

        mock_sio = MagicMock()
        register_sio(mock_sio)

        # Get initial metrics
        initial_metrics = get_metrics()
        initial_connections = initial_metrics["connections"]

        # Simulate connection
        handlers = {}
        for call in mock_sio.on.call_args_list:
            event_name = call[0][0]
            handler = call[0][1] if len(call[0]) > 1 else call[1].get("handler")
            if handler:
                handlers[event_name] = handler

        # Call connect handler
        if "connect" in handlers:
            await handlers["connect"]("test-sid", {}, None)

        # Check metrics updated
        updated_metrics = get_metrics()
        assert updated_metrics["connections"] == initial_connections + 1


class TestUploadBroadcasts:
    """Test that upload events trigger socket broadcasts."""

    @pytest.mark.asyncio
    async def test_upload_completion_broadcast(self, client):
        """Test that completing upload triggers broadcast to interested clients."""
        # This would require full Socket.IO client setup
        # For now, we verify the endpoint behavior

        # Mock S3 and task queue
        with patch("backend.utils.s3.generate_presigned_upload_url") as mock_s3:
            mock_s3.return_value = {
                "url": "https://example.com/upload",
                "method": "PUT",
            }

            # Initiate upload
            response = client.post(
                "/api/uploads/initiate",
                json={
                    "filename": "test.png",
                    "content_type": "image/png",
                },
            )

            assert response.status_code == 200
            upload_id = response.json()["upload_id"]

            # Complete upload (should trigger broadcast in real scenario)
            with patch("backend.routes.uploads.process_scorecard_task") as mock_task:
                mock_task.delay = MagicMock()

                response = client.post(
                    "/api/uploads/complete",
                    json={"upload_id": upload_id},
                )

                assert response.status_code == 200

                # In a real scenario, we would verify Socket.IO emit was called
                # For now, we just verify the endpoint worked
                assert response.json()["status"] == "uploaded"


class TestSocketInstrumentation:
    """Test socket instrumentation and logging."""

    def test_logging_context_added(self):
        """Test that instrumentation adds context to logs."""
        from backend.logging_setup import add_instrumentation_context

        logger = MagicMock()
        event_dict = {
            "event": "test",
            "logger": "backend.socket_handlers",
        }

        result = add_instrumentation_context(logger, "info", event_dict)

        # Check service tag added
        assert result["service"] == "cricksy-scorer"

        # Check component tag added for socket logger
        assert result["component"] == "websocket"

    def test_request_instrumentation(self):
        """Test RequestInstrumentation context manager."""
        from backend.logging_setup import RequestInstrumentation

        with patch("backend.logging_setup.get_logger") as mock_logger_factory:
            mock_logger = MagicMock()
            mock_logger_factory.return_value = mock_logger

            with RequestInstrumentation("test_operation", test_id="123"):
                pass

            # Verify start and completion logged
            assert mock_logger.info.call_count >= 2

            # Verify duration tracked
            calls = [str(call) for call in mock_logger.info.call_args_list]
            completion_call = [c for c in calls if "completed" in c]
            assert len(completion_call) > 0
