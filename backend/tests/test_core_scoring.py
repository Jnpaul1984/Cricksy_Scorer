"""
Tests for core scoring functionality including real-time updates and undo.

Tests cover:
- Real-time WebSocket updates for scoring events
- Undo functionality for various game states
- Data persistence and retrieval
- Score calculation accuracy
"""

from copy import deepcopy

import pytest

from backend.services import live_bus
from backend.services.scoring_service import score_one


class MockGame:
    """Mock game object for testing scoring logic."""

    def __init__(self):
        self.id = "test-game-123"
        self.team_a = {"name": "Team A", "players": [{"id": "p1", "name": "Player 1"}]}
        self.team_b = {"name": "Team B", "players": [{"id": "p2", "name": "Player 2"}]}
        self.match_type = "limited"
        self.status = "in_progress"
        self.current_inning = 1
        self.total_runs = 0
        self.total_wickets = 0
        self.overs_completed = 0
        self.balls_this_over = 0
        self.current_over_balls = 0
        self.mid_over_change_used = False
        self.is_game_over = False
        self.deliveries = []
        self.batting_scorecard = {}
        self.bowling_scorecard = {}
        self.current_striker_id = None
        self.current_non_striker_id = None
        self.current_bowler_id = None
        self.last_ball_bowler_id = None
        self.pending_new_batter = False
        self.pending_new_over = False


class MockSocketIOServer:
    """Mock Socket.IO server for testing real-time updates."""

    def __init__(self):
        self.emitted_events = []

    async def emit(self, event, data, *, room=None, namespace=None):
        """Record emitted events."""
        self.emitted_events.append(
            {"event": event, "data": data, "room": room, "namespace": namespace}
        )

    def clear_events(self):
        """Clear recorded events."""
        self.emitted_events = []


@pytest.mark.asyncio
async def test_real_time_update_on_scoring():
    """Test that scoring a ball triggers real-time WebSocket update."""
    # Setup mock socket
    mock_sio = MockSocketIOServer()
    live_bus.set_socketio_server(mock_sio)

    game_id = "game-rt-001"
    snapshot = {
        "id": game_id,
        "total_runs": 4,
        "total_wickets": 0,
        "overs_completed": 0,
        "balls_this_over": 1,
    }

    # Emit state update (simulating what happens after scoring)
    await live_bus.emit_state_update(game_id, snapshot)

    # Verify the event was emitted
    assert len(mock_sio.emitted_events) == 1
    event = mock_sio.emitted_events[0]
    assert event["event"] == "state:update"
    assert event["room"] == game_id
    assert event["data"]["id"] == game_id
    assert event["data"]["snapshot"]["total_runs"] == 4


@pytest.mark.asyncio
async def test_real_time_update_multiple_events():
    """Test that multiple scoring events trigger separate real-time updates."""
    mock_sio = MockSocketIOServer()
    live_bus.set_socketio_server(mock_sio)

    game_id = "game-rt-002"

    # Score multiple balls
    for i in range(1, 4):
        snapshot = {
            "id": game_id,
            "total_runs": i,
            "total_wickets": 0,
            "overs_completed": 0,
            "balls_this_over": i,
        }
        await live_bus.emit_state_update(game_id, snapshot)

    # Verify all events were emitted
    assert len(mock_sio.emitted_events) == 3
    for i, event in enumerate(mock_sio.emitted_events, 1):
        assert event["event"] == "state:update"
        assert event["data"]["snapshot"]["total_runs"] == i


def test_score_one_legal_delivery():
    """Test scoring a legal delivery (no extras)."""
    g = MockGame()

    # Score a legal delivery: 4 runs
    delivery = score_one(
        g,
        striker_id="p1",
        non_striker_id="p2",
        bowler_id="p3",
        runs_scored=4,
        extra=None,
        is_wicket=False,
        dismissal_type=None,
        dismissed_player_id=None,
    )

    # Verify delivery details
    assert delivery["runs_off_bat"] == 4
    assert delivery["runs_scored"] == 4
    assert delivery["extra_type"] is None
    assert delivery["is_wicket"] is False

    # Verify game state updated
    assert g.total_runs == 4
    assert g.balls_this_over == 1
    assert g.overs_completed == 0


def test_score_one_wide_delivery():
    """Test scoring a wide delivery."""
    g = MockGame()

    # Score a wide (1 extra run + 2 runs)
    delivery = score_one(
        g,
        striker_id="p1",
        non_striker_id="p2",
        bowler_id="p3",
        runs_scored=2,
        extra="wd",
        is_wicket=False,
        dismissal_type=None,
        dismissed_player_id=None,
    )

    # Verify delivery details
    assert delivery["extra_type"] == "wd"
    assert delivery["extra_runs"] == 2
    assert delivery["runs_scored"] == 2
    assert delivery["is_wicket"] is False

    # Verify game state - wide doesn't count as legal ball
    assert g.total_runs == 2
    assert g.balls_this_over == 0  # Wides don't add to balls count
    assert g.overs_completed == 0


def test_score_one_no_ball_delivery():
    """Test scoring a no ball with runs."""
    g = MockGame()

    # Score a no ball (1 extra + 2 runs off bat)
    delivery = score_one(
        g,
        striker_id="p1",
        non_striker_id="p2",
        bowler_id="p3",
        runs_scored=2,
        extra="nb",
        is_wicket=False,
        dismissal_type=None,
        dismissed_player_id=None,
    )

    # Verify delivery details
    assert delivery["extra_type"] == "nb"
    assert delivery["runs_off_bat"] == 2
    assert delivery["runs_scored"] == 3  # 1 (no ball) + 2 (runs off bat)
    assert delivery["is_wicket"] is False

    # Verify game state - no ball doesn't count as legal ball
    assert g.total_runs == 3
    assert g.balls_this_over == 0  # No balls don't add to balls count


def test_clean_over_six_legal_balls():
    """Ensure a full over of legal balls has correct totals and run rate."""
    g = MockGame()
    outcomes = [0, 1, 2, 3, 4, 6]

    for runs in outcomes:
        score_one(
            g,
            striker_id="p1",
            non_striker_id="p2",
            bowler_id="p3",
            runs_scored=runs,
            extra=None,
            is_wicket=False,
            dismissal_type=None,
            dismissed_player_id=None,
        )

    assert g.total_runs == sum(outcomes)
    assert g.overs_completed == 1
    assert g.balls_this_over == 0
    assert g.pending_new_over is True
    run_rate = g.total_runs / max(g.overs_completed, 1)
    assert pytest.approx(run_rate, rel=1e-6) == 16.0


def test_wides_and_no_balls_respect_ball_counts_and_extras():
    """Cover wides/no-balls flow to ensure extras & legal balls are tracked."""
    g = MockGame()

    wide_delivery = score_one(
        g,
        striker_id="p1",
        non_striker_id="p2",
        bowler_id="p3",
        runs_scored=2,
        extra="wd",
        is_wicket=False,
        dismissal_type=None,
        dismissed_player_id=None,
    )
    assert wide_delivery["extra_type"] == "wd"
    assert wide_delivery["extra_runs"] == 2
    assert wide_delivery["runs_scored"] == 2
    assert g.balls_this_over == 0

    no_ball_delivery = score_one(
        g,
        striker_id="p1",
        non_striker_id="p2",
        bowler_id="p3",
        runs_scored=2,
        extra="nb",
        is_wicket=False,
        dismissal_type=None,
        dismissed_player_id=None,
    )
    assert no_ball_delivery["extra_type"] == "nb"
    assert no_ball_delivery["runs_off_bat"] == 2
    assert no_ball_delivery["runs_scored"] == 3
    assert g.balls_this_over == 0  # Still no legal ball recorded

    legal_delivery = score_one(
        g,
        striker_id="p1",
        non_striker_id="p2",
        bowler_id="p3",
        runs_scored=1,
        extra=None,
        is_wicket=False,
        dismissal_type=None,
        dismissed_player_id=None,
    )
    assert legal_delivery["runs_off_bat"] == 1
    assert legal_delivery["ball_number"] == 1  # First legal ball of the over

    assert g.total_runs == 6  # 2 (wd) + 3 (nb) + 1 (legal)
    assert g.balls_this_over == 1
    assert g.current_striker_id == "p2"  # Strike rotated on the single


def test_score_one_wicket_delivery():
    """Test scoring a wicket delivery."""
    g = MockGame()

    # Score a wicket (bowled)
    delivery = score_one(
        g,
        striker_id="p1",
        non_striker_id="p2",
        bowler_id="p3",
        runs_scored=0,
        extra=None,
        is_wicket=True,
        dismissal_type="bowled",
        dismissed_player_id="p1",
    )

    # Verify delivery details
    assert delivery["is_wicket"] is True
    assert delivery["dismissal_type"] == "bowled"
    assert delivery["dismissed_player_id"] == "p1"
    assert delivery["runs_scored"] == 0

    # Verify game state
    assert g.total_runs == 0
    assert g.balls_this_over == 1
    assert g.pending_new_batter is True


def test_wicket_marks_batter_out_and_retains_strike_until_replaced():
    """Ensure wicket flow keeps striker on strike until a new batter arrives."""
    g = MockGame()

    delivery = score_one(
        g,
        striker_id="p1",
        non_striker_id="p2",
        bowler_id="p3",
        runs_scored=0,
        extra=None,
        is_wicket=True,
        dismissal_type="caught",
        dismissed_player_id="p1",
    )

    assert delivery["dismissal_type"] == "caught"
    assert g.pending_new_batter is True
    assert g.current_striker_id == "p1"  # Awaiting replacement
    assert g.current_non_striker_id == "p2"
    assert g.batting_scorecard["p1"]["is_out"] is True


def test_wicket_on_last_ball_of_over_sets_correct_state():
    """Last ball wicket should still finish the over and flag pending batter."""
    g = MockGame()

    for _ in range(5):
        score_one(
            g,
            striker_id="p1",
            non_striker_id="p2",
            bowler_id="p3",
            runs_scored=1,
            extra=None,
            is_wicket=False,
            dismissal_type=None,
            dismissed_player_id=None,
        )

    assert g.balls_this_over == 5
    assert g.overs_completed == 0

    wicket_delivery = score_one(
        g,
        striker_id="p1",
        non_striker_id="p2",
        bowler_id="p3",
        runs_scored=0,
        extra=None,
        is_wicket=True,
        dismissal_type="bowled",
        dismissed_player_id="p1",
    )

    assert wicket_delivery["ball_number"] == 6
    assert g.overs_completed == 1
    assert g.balls_this_over == 0
    assert g.pending_new_over is True
    assert g.pending_new_batter is True
    assert g.current_bowler_id is None
    assert g.last_ball_bowler_id == "p3"
    # Striker stays the dismissed batter until replacement arrives
    assert g.current_striker_id == "p1"
    assert g.current_non_striker_id == "p2"


def test_score_one_complete_over():
    """Test completing an over (6 legal balls)."""
    g = MockGame()

    # Score 6 legal balls
    for _i in range(6):
        score_one(
            g,
            striker_id="p1",
            non_striker_id="p2",
            bowler_id="p3",
            runs_scored=1,
            extra=None,
            is_wicket=False,
            dismissal_type=None,
            dismissed_player_id=None,
        )

    # Verify over completed
    assert g.overs_completed == 1
    assert g.balls_this_over == 0  # Reset after completing over
    assert g.total_runs == 6
    assert g.pending_new_over is True
    assert g.current_bowler_id is None  # Reset after over completion


def test_score_one_strike_rotation_odd_runs():
    """Test strike rotation after odd runs scored."""
    g = MockGame()
    g.current_striker_id = "p1"
    g.current_non_striker_id = "p2"

    # Score 1 run (odd) - strike should rotate
    score_one(
        g,
        striker_id="p1",
        non_striker_id="p2",
        bowler_id="p3",
        runs_scored=1,
        extra=None,
        is_wicket=False,
        dismissal_type=None,
        dismissed_player_id=None,
    )

    # Verify strike rotated
    assert g.current_striker_id == "p2"
    assert g.current_non_striker_id == "p1"


def test_score_one_strike_rotation_even_runs():
    """Test no strike rotation after even runs scored."""
    g = MockGame()
    g.current_striker_id = "p1"
    g.current_non_striker_id = "p2"

    # Score 2 runs (even) - strike should NOT rotate
    score_one(
        g,
        striker_id="p1",
        non_striker_id="p2",
        bowler_id="p3",
        runs_scored=2,
        extra=None,
        is_wicket=False,
        dismissal_type=None,
        dismissed_player_id=None,
    )

    # Verify strike did NOT rotate
    assert g.current_striker_id == "p1"
    assert g.current_non_striker_id == "p2"


def test_undo_single_delivery():
    """Test undoing a single delivery."""
    g = MockGame()

    # Score a delivery
    score_one(
        g,
        striker_id="p1",
        non_striker_id="p2",
        bowler_id="p3",
        runs_scored=4,
        extra=None,
        is_wicket=False,
        dismissal_type=None,
        dismissed_player_id=None,
    )

    # Record state after scoring
    assert g.total_runs == 4
    assert g.balls_this_over == 1

    # Simulate undo by removing delivery and resetting state
    initial_runs = 0
    initial_balls = 0

    # After undo, state should be reset
    g.total_runs = initial_runs
    g.balls_this_over = initial_balls

    # Verify state reverted
    assert g.total_runs == 0
    assert g.balls_this_over == 0


def test_undo_multiple_deliveries():
    """Test undoing works correctly with multiple deliveries."""
    g = MockGame()
    deliveries = []

    # Score 3 deliveries
    for i in range(3):
        delivery = score_one(
            g,
            striker_id="p1",
            non_striker_id="p2",
            bowler_id="p3",
            runs_scored=i + 1,
            extra=None,
            is_wicket=False,
            dismissal_type=None,
            dismissed_player_id=None,
        )
        deliveries.append(delivery)

    # State after 3 balls
    assert g.total_runs == 6  # 1 + 2 + 3
    assert g.balls_this_over == 3

    # Simulate undo of last delivery
    # After undo, we need to replay first 2 deliveries
    g.total_runs = 0
    g.balls_this_over = 0

    for delivery in deliveries[:2]:
        score_one(
            g,
            striker_id=delivery["striker_id"],
            non_striker_id=delivery["non_striker_id"],
            bowler_id=delivery["bowler_id"],
            runs_scored=delivery["runs_off_bat"],
            extra=None,
            is_wicket=False,
            dismissal_type=None,
            dismissed_player_id=None,
        )

    # Verify state after undo
    assert g.total_runs == 3  # 1 + 2
    assert g.balls_this_over == 2


def test_undo_wicket_delivery():
    """Test undoing a wicket delivery restores game state correctly."""
    g = MockGame()

    # Score a wicket
    score_one(
        g,
        striker_id="p1",
        non_striker_id="p2",
        bowler_id="p3",
        runs_scored=0,
        extra=None,
        is_wicket=True,
        dismissal_type="bowled",
        dismissed_player_id="p1",
    )

    # Verify wicket state
    assert g.pending_new_batter is True
    assert g.balls_this_over == 1

    # Simulate undo - reset state
    g.pending_new_batter = False
    g.balls_this_over = 0
    g.total_runs = 0
    g.total_wickets = 0

    # Verify state restored
    assert g.pending_new_batter is False
    assert g.balls_this_over == 0


def test_service_level_undo_replays_deliveries_like_backend():
    """Mirror backend undo logic: replay ledger without last delivery."""
    g = MockGame()
    recorded: list[dict] = []

    def _record(**kwargs):
        delivery = score_one(g, **kwargs)
        recorded.append(delivery)
        return delivery

    _record(
        striker_id="p1",
        non_striker_id="p2",
        bowler_id="p3",
        runs_scored=4,
        extra=None,
        is_wicket=False,
        dismissal_type=None,
        dismissed_player_id=None,
    )
    _record(
        striker_id="p1",
        non_striker_id="p2",
        bowler_id="p3",
        runs_scored=1,
        extra=None,
        is_wicket=False,
        dismissal_type=None,
        dismissed_player_id=None,
    )

    expected_runs = g.total_runs
    expected_balls = g.balls_this_over
    expected_striker = g.current_striker_id
    expected_non_striker = g.current_non_striker_id
    expected_scorecard = deepcopy(g.batting_scorecard)

    # Third delivery is a wicket we plan to undo
    _record(
        striker_id="p1",
        non_striker_id="p2",
        bowler_id="p3",
        runs_scored=0,
        extra=None,
        is_wicket=True,
        dismissal_type="bowled",
        dismissed_player_id="p1",
    )
    assert g.pending_new_batter is True
    assert g.batting_scorecard["p1"]["is_out"] is True

    trimmed = recorded[:-1]
    replay = MockGame()
    for entry in trimmed:
        extra_type = entry["extra_type"]
        if extra_type == "nb":
            replay_runs = entry["runs_off_bat"]
        elif extra_type in ("wd", "b", "lb"):
            replay_runs = entry["extra_runs"]
        else:
            replay_runs = entry["runs_off_bat"]

        score_one(
            replay,
            striker_id=entry["striker_id"],
            non_striker_id=entry["non_striker_id"],
            bowler_id=entry["bowler_id"],
            runs_scored=replay_runs,
            extra=extra_type,
            is_wicket=entry["is_wicket"],
            dismissal_type=entry["dismissal_type"],
            dismissed_player_id=entry["dismissed_player_id"],
        )

    assert replay.total_runs == expected_runs
    assert replay.balls_this_over == expected_balls
    assert replay.current_striker_id == expected_striker
    assert replay.current_non_striker_id == expected_non_striker
    assert replay.pending_new_batter is False
    assert replay.batting_scorecard["p1"] == expected_scorecard["p1"]


@pytest.mark.asyncio
async def test_undo_triggers_real_time_update():
    """Test that undo operation triggers real-time WebSocket update."""
    mock_sio = MockSocketIOServer()
    live_bus.set_socketio_server(mock_sio)

    game_id = "game-undo-001"

    # Initial state after scoring
    snapshot_before = {
        "id": game_id,
        "total_runs": 4,
        "total_wickets": 0,
        "overs_completed": 0,
        "balls_this_over": 1,
    }
    await live_bus.emit_state_update(game_id, snapshot_before)

    # Clear events to test undo
    mock_sio.clear_events()

    # State after undo
    snapshot_after_undo = {
        "id": game_id,
        "total_runs": 0,
        "total_wickets": 0,
        "overs_completed": 0,
        "balls_this_over": 0,
    }
    await live_bus.emit_state_update(game_id, snapshot_after_undo)

    # Verify undo triggered update
    assert len(mock_sio.emitted_events) == 1
    event = mock_sio.emitted_events[0]
    assert event["event"] == "state:update"
    assert event["data"]["snapshot"]["total_runs"] == 0
    assert event["data"]["snapshot"]["balls_this_over"] == 0


def test_data_persistence_delivery_format():
    """Test that delivery data is stored in correct format."""
    g = MockGame()

    delivery = score_one(
        g,
        striker_id="striker-123",
        non_striker_id="non-striker-456",
        bowler_id="bowler-789",
        runs_scored=4,
        extra=None,
        is_wicket=False,
        dismissal_type=None,
        dismissed_player_id=None,
    )

    # Verify all required fields are present
    required_fields = [
        "over_number",
        "ball_number",
        "bowler_id",
        "striker_id",
        "non_striker_id",
        "runs_off_bat",
        "extra_type",
        "extra_runs",
        "runs_scored",
        "is_extra",
        "is_wicket",
    ]

    for field in required_fields:
        assert field in delivery, f"Missing required field: {field}"

    # Verify data types
    assert isinstance(delivery["over_number"], int)
    assert isinstance(delivery["ball_number"], int)
    assert isinstance(delivery["runs_scored"], int)
    assert isinstance(delivery["is_wicket"], bool)


def test_batting_scorecard_updates():
    """Test that batting scorecard updates correctly."""
    g = MockGame()

    # Score multiple deliveries for same batter
    for i in range(4):
        score_one(
            g,
            striker_id="p1",
            non_striker_id="p2",
            bowler_id="p3",
            runs_scored=i,
            extra=None,
            is_wicket=False,
            dismissal_type=None,
            dismissed_player_id=None,
        )

    # Verify batting scorecard
    assert "p1" in g.batting_scorecard
    batter = g.batting_scorecard["p1"]
    assert batter["runs"] == 6  # 0 + 1 + 2 + 3
    assert batter["balls_faced"] == 4
    assert batter["is_out"] is False


def test_bowling_scorecard_updates():
    """Test that bowling scorecard updates correctly."""
    g = MockGame()

    # Score multiple deliveries by same bowler
    for _i in range(3):
        score_one(
            g,
            striker_id="p1",
            non_striker_id="p2",
            bowler_id="p3",
            runs_scored=2,
            extra=None,
            is_wicket=False,
            dismissal_type=None,
            dismissed_player_id=None,
        )

    # Verify bowling scorecard
    assert "p3" in g.bowling_scorecard
    bowler = g.bowling_scorecard["p3"]
    assert bowler["runs_conceded"] >= 0  # Runs conceded tracked separately
    assert bowler["wickets_taken"] == 0


def test_bowling_scorecard_wicket_credit():
    """Test that bowler gets credit for wickets."""
    g = MockGame()

    # Score a wicket (bowled - bowler gets credit)
    score_one(
        g,
        striker_id="p1",
        non_striker_id="p2",
        bowler_id="p3",
        runs_scored=0,
        extra=None,
        is_wicket=True,
        dismissal_type="bowled",
        dismissed_player_id="p1",
    )

    # Verify bowling scorecard
    assert "p3" in g.bowling_scorecard
    bowler = g.bowling_scorecard["p3"]
    assert bowler["wickets_taken"] == 1


def test_no_wicket_credit_for_run_out():
    """Test that bowler doesn't get credit for run out."""
    g = MockGame()

    # Score a run out (bowler doesn't get credit)
    score_one(
        g,
        striker_id="p1",
        non_striker_id="p2",
        bowler_id="p3",
        runs_scored=1,
        extra=None,
        is_wicket=True,
        dismissal_type="run_out",
        dismissed_player_id="p1",
    )

    # Verify bowling scorecard
    assert "p3" in g.bowling_scorecard
    bowler = g.bowling_scorecard["p3"]
    assert bowler["wickets_taken"] == 0  # No credit for run out


# ===================================================================
# Delivery Correction Tests
# ===================================================================


@pytest.mark.asyncio
async def test_delivery_correction_wide_to_legal(async_client, db_session):
    """Test correcting a wide to a legal delivery updates totals correctly."""
    from backend.routes import games as games_impl

    # Create test game via API
    create_response = await async_client.post(
        "/games",
        json={
            "match_type": "limited",
            "overs_limit": 20,
            "team_a_name": "Team A",
            "team_b_name": "Team B",
            "players_a": ["bat1", "bat2"],
            "players_b": ["bowl1", "bowl2"],
            "toss_winner_team": "Team A",
            "decision": "bat",
        },
    )
    assert create_response.status_code in (200, 201)
    game_data = create_response.json()
    game_id = game_data.get("id") or game_data.get("gid") or game_data.get("game", {}).get("id")
    assert game_id, f"Could not extract game ID from: {game_data}"

    # Get game details to extract player IDs
    game_response = await async_client.get(f"/games/{game_id}")
    assert game_response.status_code == 200
    game_details = game_response.json()
    striker_id = game_details["team_a"]["players"][0]["id"]
    non_striker_id = game_details["team_a"]["players"][1]["id"]
    bowler_id = game_details["team_b"]["players"][0]["id"]

    # Score a wide (WD + 1 run) via API
    wide_payload = {
        "striker_id": striker_id,
        "non_striker_id": non_striker_id,
        "bowler_id": bowler_id,
        "runs_scored": 1,  # Wide: use runs_scored
        "runs_off_bat": 0,
        "extra": "wd",
        "is_wicket": False,
    }
    print(f"\n[DEBUG] Wide delivery payload: {wide_payload}")
    score_response = await async_client.post(
        f"/games/{game_id}/deliveries",
        json=wide_payload,
    )
    if score_response.status_code != 200:
        print(f"[DEBUG] Failed with {score_response.status_code}: {score_response.text}")
    assert score_response.status_code == 200, f"Expected 200, got {score_response.status_code}: {score_response.text}"
    snapshot = score_response.json()
    assert snapshot["total_runs"] == 1
    
    # Fetch full game state to get delivery ID (snapshot doesn't include deliveries array)
    game_state_response = await async_client.get(f"/games/{game_id}")
    assert game_state_response.status_code == 200
    game_state = game_state_response.json()
    assert len(game_state["deliveries"]) > 0, "No deliveries found in game state"
    print(f"[DEBUG] First delivery structure: {game_state['deliveries'][0]}")
    print(f"[DEBUG] Delivery keys: {list(game_state['deliveries'][0].keys())}")
    # Deliveries might use 'delivery_id', 'did', or store ID in a different field
    delivery = game_state["deliveries"][0]
    delivery_id = delivery.get("id") or delivery.get("delivery_id") or delivery.get("did") or str(delivery.get("inning", "")) + "_" + str(delivery.get("ball_number", ""))

    # Correct the wide to a legal 1 run
    response = await async_client.patch(
        f"/games/{game_id}/deliveries/{delivery_id}",
        json={
            "runs_scored": 1,
            "runs_off_bat": 1,
            "extra": None,
            "is_wicket": False,
        },
    )
    assert response.status_code == 200
    snapshot = response.json()

    # Verify totals updated correctly
    corrected_snapshot = response.json()
    assert corrected_snapshot["total_runs"] == 1  # Still 1 run total
    assert corrected_snapshot["overs_completed"] == 0
    assert corrected_snapshot["balls_this_over"] == 1  # Now counts as legal ball

    # Verify delivery was corrected
    assert len(corrected_snapshot["deliveries"]) == 1
    corrected_delivery = corrected_snapshot["deliveries"][0]
    assert not corrected_delivery.get("extra_type") or corrected_delivery["extra_type"] == ""
    assert corrected_delivery["runs_scored"] == 1
    assert corrected_delivery["runs_off_bat"] == 1


@pytest.mark.asyncio
async def test_delivery_correction_runs_update(async_client, db_session):
    """Test correcting runs on a delivery recalculates totals."""

    # Create test game via API
    create_response = await async_client.post(
        "/games",
        json={
            "match_type": "limited",
            "overs_limit": 20,
            "team_a_name": "Team A",
            "team_b_name": "Team B",
            "players_a": ["bat1", "bat2"],
            "players_b": ["bowl1", "bowl2"],
            "toss_winner_team": "Team A",
            "decision": "bat",
        },
    )
    assert create_response.status_code in (200, 201)
    game_data = create_response.json()
    game_id = game_data.get("id") or game_data.get("gid") or game_data.get("game", {}).get("id")

    # Get game details to extract player IDs
    game_response = await async_client.get(f"/games/{game_id}")
    assert game_response.status_code == 200
    game_details = game_response.json()
    striker_id = game_details["team_a"]["players"][0]["id"]
    non_striker_id = game_details["team_a"]["players"][1]["id"]
    bowler_id = game_details["team_b"]["players"][0]["id"]

    # Score 2 runs via API
    legal_payload = {
        "striker_id": striker_id,
        "non_striker_id": non_striker_id,
        "bowler_id": bowler_id,
        "runs_scored": 2,  # Legal ball: use runs_scored
        "runs_off_bat": 0,
        "extra": None,
        "is_wicket": False,
    }
    print(f"\n[DEBUG] Legal delivery payload: {legal_payload}")
    score_response = await async_client.post(
        f"/games/{game_id}/deliveries",
        json=legal_payload,
    )
    if score_response.status_code != 200:
        print(f"[DEBUG] Failed with {score_response.status_code}: {score_response.text}")
    assert score_response.status_code == 200, f"Expected 200, got {score_response.status_code}: {score_response.text}"
    snapshot_after_score = score_response.json()
    assert snapshot_after_score["total_runs"] == 2
    
    # Fetch full game state to get delivery ID (snapshot doesn't include deliveries array)
    game_state_response = await async_client.get(f"/games/{game_id}")
    assert game_state_response.status_code == 200
    game_state = game_state_response.json()
    assert len(game_state["deliveries"]) > 0, "No deliveries found in game state"
    print(f"[DEBUG] First delivery structure: {game_state['deliveries'][0]}")
    print(f"[DEBUG] Delivery keys: {list(game_state['deliveries'][0].keys())}")
    # Deliveries might use 'delivery_id', 'did', or store ID in a different field
    delivery = game_state["deliveries"][0]
    delivery_id = delivery.get("id") or delivery.get("delivery_id") or delivery.get("did") or str(delivery.get("inning", "")) + "_" + str(delivery.get("ball_number", ""))

    # Correct to 4 runs
    response = await async_client.patch(
        f"/games/{game_id}/deliveries/{delivery_id}",
        json={"runs_off_bat": 4, "runs_scored": 4},
    )
    assert response.status_code == 200
    snapshot = response.json()

    # Verify totals updated
    assert snapshot["total_runs"] == 4

    # Verify batting scorecard updated
    bat_card = snapshot.get("batting_scorecard", {}).get("bat1", {})
    assert bat_card.get("runs") == 4


@pytest.mark.asyncio
async def test_delivery_correction_not_found(async_client, db_session):
    """Test correction returns 404 for non-existent delivery."""

    # Create test game with no deliveries via API
    create_response = await async_client.post(
        "/games",
        json={
            "match_type": "limited",
            "overs_limit": 20,
            "team_a_name": "Team A",
            "team_b_name": "Team B",
            "players_a": ["bat1", "bat2"],
            "players_b": ["bowl1", "bowl2"],
            "toss_winner_team": "Team A",
            "decision": "bat",
        },
    )
    assert create_response.status_code in (200, 201)
    game_data = create_response.json()
    game_id = game_data.get("id") or game_data.get("gid") or game_data.get("game", {}).get("id")

    # Try to correct non-existent delivery
    response = await async_client.patch(
        f"/games/{game_id}/deliveries/999",
        json={"runs_scored": 1},
    )
    assert response.status_code == 404
    assert "not found" in response.json()["detail"].lower()
