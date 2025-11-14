"""
Tests for the live event bus module.
"""

import pytest

from backend.services import live_bus


class MockSocketIOServer:
    """Mock Socket.IO server for testing."""

    def __init__(self):
        self.emitted_events = []

    async def emit(self, event, data, *, room=None, namespace=None):
        """Record emitted events."""
        self.emitted_events.append(
            {"event": event, "data": data, "room": room, "namespace": namespace}
        )


@pytest.mark.asyncio
async def test_set_socketio_server():
    """Test setting the Socket.IO server."""
    # Reset the global state
    live_bus._sio_server = None

    mock_sio = MockSocketIOServer()
    live_bus.set_socketio_server(mock_sio)

    assert live_bus._sio_server is mock_sio


@pytest.mark.asyncio
async def test_emit_with_server_set():
    """Test emitting events when server is set."""
    mock_sio = MockSocketIOServer()
    live_bus.set_socketio_server(mock_sio)

    await live_bus.emit("test:event", {"data": "value"}, room="room1")

    assert len(mock_sio.emitted_events) == 1
    assert mock_sio.emitted_events[0]["event"] == "test:event"
    assert mock_sio.emitted_events[0]["data"] == {"data": "value"}
    assert mock_sio.emitted_events[0]["room"] == "room1"


@pytest.mark.asyncio
async def test_emit_without_server_set():
    """Test emitting events when server is not set (should be no-op)."""
    # Reset the global state
    live_bus._sio_server = None

    # Should not raise an error
    await live_bus.emit("test:event", {"data": "value"}, room="room1")


@pytest.mark.asyncio
async def test_emit_state_update():
    """Test the convenience method for state updates."""
    mock_sio = MockSocketIOServer()
    live_bus.set_socketio_server(mock_sio)

    game_id = "game123"
    snapshot = {"status": "in_progress", "runs": 42}

    await live_bus.emit_state_update(game_id, snapshot)

    assert len(mock_sio.emitted_events) == 1
    assert mock_sio.emitted_events[0]["event"] == "state:update"
    assert mock_sio.emitted_events[0]["data"] == {"id": game_id, "snapshot": snapshot}
    assert mock_sio.emitted_events[0]["room"] == game_id


@pytest.mark.asyncio
async def test_emit_game_update():
    """Test the convenience method for game updates."""
    mock_sio = MockSocketIOServer()
    live_bus.set_socketio_server(mock_sio)

    game_id = "game456"
    payload = {"type": "score_update", "runs": 10}

    await live_bus.emit_game_update(game_id, payload)

    assert len(mock_sio.emitted_events) == 1
    assert mock_sio.emitted_events[0]["event"] == "game:update"
    assert mock_sio.emitted_events[0]["data"] == payload
    assert mock_sio.emitted_events[0]["room"] == game_id


def test_publish_game_update_without_server():
    """Test sync wrapper when server is not set (should be no-op)."""
    # Reset the global state
    live_bus._sio_server = None

    # Should not raise an error
    live_bus.publish_game_update("game789", {"update": "value"})


@pytest.mark.asyncio
async def test_emit_handles_server_error_gracefully():
    """Test that emit handles server errors gracefully."""

    class BrokenSocketIOServer:
        async def emit(self, event, data, *, room=None, namespace=None):
            raise Exception("Server error")

    broken_sio = BrokenSocketIOServer()
    live_bus.set_socketio_server(broken_sio)

    # Should not raise an error
    await live_bus.emit("test:event", {"data": "value"}, room="room1")
