"""
Full Match Integration Tests

Tests complete match scenarios from creation to finalization including:
- Match creation with teams and players
- Setting openers
- Posting deliveries for complete innings
- Wicket handling and batsman selection
- Starting second innings
- Match finalization
- Result calculation
"""

import pytest


def test_complete_match_no_wickets(game_helper, assert_helper):
    """Test a complete match with no wickets."""
    # Create game with 2 overs per innings
    game_helper.create_game(overs_limit=2)
    
    # Set openers for first innings
    game_helper.set_openers(team="A")
    
    striker = game_helper.team_a_players[0]["id"]
    non_striker = game_helper.team_a_players[1]["id"]
    bowler1 = game_helper.team_b_players[0]["id"]
    bowler2 = game_helper.team_b_players[1]["id"]
    
    # Play 2 overs (12 balls) - first innings
    for i in range(12):
        batsman = striker if i % 2 == 0 else non_striker
        # Rotate bowlers every 6 balls (1 over)
        current_bowler = bowler1 if (i // 6) % 2 == 0 else bowler2
        response = game_helper.post_delivery(
            batsman_id=batsman,
            bowler_id=current_bowler,
            runs_scored=1
        )
        assert response.status_code == 200
    
    # Start second innings
    striker2 = game_helper.team_b_players[0]["id"]
    non_striker2 = game_helper.team_b_players[1]["id"]
    bowler3 = game_helper.team_a_players[0]["id"]
    bowler4 = game_helper.team_a_players[1]["id"]
    
    game_helper.start_next_innings(
        striker_id=striker2,
        non_striker_id=non_striker2,
        opening_bowler_id=bowler3
    )
    
    # Play 2 overs - second innings
    for i in range(12):
        batsman = striker2 if i % 2 == 0 else non_striker2
        # Rotate bowlers every 6 balls (1 over)
        current_bowler = bowler3 if (i // 6) % 2 == 0 else bowler4
        response = game_helper.post_delivery(
            batsman_id=batsman,
            bowler_id=current_bowler,
            runs_scored=1
        )
        assert response.status_code == 200
    
    # Finalize
    game_helper.finalize_game()
    
    # Verify
    snapshot = game_helper.get_snapshot()
    deliveries = game_helper.get_deliveries()
    
    assert len(deliveries) == 24
    assert_helper.assert_wicket_count(deliveries, 0)
    assert_helper.assert_runs_scored(deliveries, 24)


def test_complete_match_with_wickets(game_helper, assert_helper):
    """Test a complete match with wickets and batsman selection."""
    # Create game with 2 overs per innings
    game_helper.create_game(overs_limit=2)
    
    # Set openers for first innings
    game_helper.set_openers(team="A")
    
    striker = game_helper.team_a_players[0]["id"]
    non_striker = game_helper.team_a_players[1]["id"]
    bowler1 = game_helper.team_b_players[0]["id"]
    bowler2 = game_helper.team_b_players[1]["id"]
    
    # Post 3 normal deliveries (first over)
    for i in range(3):
        response = game_helper.post_delivery(
            batsman_id=striker,
            bowler_id=bowler1,
            runs_scored=1
        )
        assert response.status_code == 200
    
    # Post a wicket delivery (4th ball of first over)
    response = game_helper.post_delivery(
        batsman_id=striker,
        bowler_id=bowler1,
        runs_scored=0,
        is_wicket=True,
        dismissal_type="bowled"
    )
    assert response.status_code == 200
    
    # Verify needs_new_batter flag (computed from is_out status)
    snapshot = game_helper.get_snapshot()
    assert_helper.assert_pending_batsman(snapshot, True)
    
    # Select new batsman
    new_batsman = game_helper.team_a_players[2]["id"]
    game_helper.select_next_batsman(new_batsman)
    
    # Verify flag cleared
    snapshot = game_helper.get_snapshot()
    assert_helper.assert_pending_batsman(snapshot, False)
    
    # Complete first over (2 more balls)
    for i in range(2):
        response = game_helper.post_delivery(
            batsman_id=new_batsman,
            bowler_id=bowler1,
            runs_scored=1
        )
        assert response.status_code == 200
    
    # Second over (6 balls with different bowler)
    for i in range(6):
        batsman = new_batsman if i % 2 == 0 else non_striker
        response = game_helper.post_delivery(
            batsman_id=batsman,
            bowler_id=bowler2,
            runs_scored=1
        )
        assert response.status_code == 200
    
    # Start second innings
    striker2 = game_helper.team_b_players[0]["id"]
    non_striker2 = game_helper.team_b_players[1]["id"]
    bowler3 = game_helper.team_a_players[0]["id"]
    bowler4 = game_helper.team_a_players[1]["id"]
    
    game_helper.start_next_innings(
        striker_id=striker2,
        non_striker_id=non_striker2,
        opening_bowler_id=bowler3
    )
    
    # Play second innings (2 overs = 12 balls, no wickets)
    for i in range(12):
        batsman = striker2 if i % 2 == 0 else non_striker2
        current_bowler = bowler3 if (i // 6) % 2 == 0 else bowler4
        response = game_helper.post_delivery(
            batsman_id=batsman,
            bowler_id=current_bowler,
            runs_scored=1
        )
        assert response.status_code == 200
    
    # Finalize
    game_helper.finalize_game()
    
    # Verify
    deliveries = game_helper.get_deliveries()
    assert_helper.assert_wicket_count(deliveries, 1)
    
    # First innings should have 11 runs (3 + 0 + 2 + 6)
    first_innings_deliveries = [d for d in deliveries if d.get("inning") == 1]
    assert_helper.assert_runs_scored(first_innings_deliveries, 11)


def test_match_with_multiple_wickets(game_helper, assert_helper):
    """Test a match with multiple wickets in sequence."""
    # Create game
    game_helper.create_game()
    game_helper.set_openers(team="A")
    
    striker = game_helper.team_a_players[0]["id"]
    bowler = game_helper.team_b_players[0]["id"]
    
    # Post 3 wickets in sequence
    for i in range(3):
        current_batsman = game_helper.team_a_players[i]["id"]
        
        # Post wicket
        response = game_helper.post_delivery(
            batsman_id=current_batsman,
            bowler_id=bowler,
            runs_scored=0,
            is_wicket=True,
            dismissal_type="bowled"
        )
        assert response.status_code == 200
        
        # Verify pending flag
        snapshot = game_helper.get_snapshot()
        assert_helper.assert_pending_batsman(snapshot, True)
        
        # Select next batsman (if not last wicket)
        if i < 2:
            next_batsman = game_helper.team_a_players[i + 3]["id"]
            game_helper.select_next_batsman(next_batsman)
            
            # Verify flag cleared
            snapshot = game_helper.get_snapshot()
            assert_helper.assert_pending_batsman(snapshot, False)
    
    # Verify wicket count
    deliveries = game_helper.get_deliveries()
    assert_helper.assert_wicket_count(deliveries, 3)


def test_match_with_different_dismissal_types(game_helper, assert_helper):
    """Test a match with various dismissal types."""
    # Create game
    game_helper.create_game()
    game_helper.set_openers(team="A")
    
    bowler = game_helper.team_b_players[0]["id"]
    fielder = game_helper.team_b_players[1]["id"]
    
    dismissal_types = [
        ("bowled", None),
        ("caught", fielder),
        ("lbw", None),
        ("run_out", fielder),
        ("stumped", None)
    ]
    
    for i, (dismissal_type, fielder_id) in enumerate(dismissal_types):
        batsman = game_helper.team_a_players[i]["id"]
        
        # Post wicket with specific dismissal type
        response = game_helper.post_delivery(
            batsman_id=batsman,
            bowler_id=bowler,
            runs_scored=0,
            is_wicket=True,
            dismissal_type=dismissal_type,
            fielder_id=fielder_id
        )
        assert response.status_code == 200
        
        # Select next batsman
        if i < len(dismissal_types) - 1:
            next_batsman = game_helper.team_a_players[i + 5]["id"]
            game_helper.select_next_batsman(next_batsman)
    
    # Verify all dismissal types recorded
    deliveries = game_helper.get_deliveries()
    wicket_deliveries = [d for d in deliveries if d.get("is_wicket")]
    
    assert len(wicket_deliveries) == len(dismissal_types)
    
    recorded_types = [d.get("dismissal_type") for d in wicket_deliveries]
    expected_types = [dt[0] for dt in dismissal_types]
    
    for expected in expected_types:
        assert expected in recorded_types, \
            f"Dismissal type '{expected}' not found in recorded types"


def test_match_with_extras(game_helper, assert_helper):
    """Test a match with various extra types."""
    # Create game
    game_helper.create_game()
    game_helper.set_openers(team="A")
    
    striker = game_helper.team_a_players[0]["id"]
    bowler = game_helper.team_b_players[0]["id"]
    
    # Post deliveries with different extras
    extras = [
        {"extra_type": "wd", "runs_scored": 1},  # Wide
        {"extra_type": "nb", "runs_scored": 1, "runs_off_bat": 0},  # No ball
        {"extra_type": "b", "runs_scored": 1},  # Bye
        {"extra_type": "lb", "runs_scored": 1},  # Leg bye
    ]
    
    for extra in extras:
        response = game_helper.post_delivery(
            batsman_id=striker,
            bowler_id=bowler,
            **extra
        )
        assert response.status_code == 200
    
    # Post normal delivery
    response = game_helper.post_delivery(
        batsman_id=striker,
        bowler_id=bowler,
        runs_scored=4
    )
    assert response.status_code == 200
    
    # Verify
    deliveries = game_helper.get_deliveries()
    assert len(deliveries) == 5
    
    # Check extras are recorded
    extras_deliveries = [d for d in deliveries if d.get("extra_type")]
    assert len(extras_deliveries) == 4


def test_complete_20_over_match(game_helper, assert_helper):
    """Test a complete 20-over match."""
    # Create game
    game_helper.create_game(overs_limit=20)
    game_helper.set_openers(team="A")
    
    striker = game_helper.team_a_players[0]["id"]
    non_striker = game_helper.team_a_players[1]["id"]
    bowler1 = game_helper.team_b_players[0]["id"]
    bowler2 = game_helper.team_b_players[1]["id"]
    
    # Play 20 overs (120 balls) - first innings
    for i in range(120):
        batsman = striker if i % 2 == 0 else non_striker
        runs = 1 if i % 6 < 4 else 4  # Mix of 1s and 4s
        # Rotate bowlers every over
        current_bowler = bowler1 if (i // 6) % 2 == 0 else bowler2
        
        response = game_helper.post_delivery(
            batsman_id=batsman,
            bowler_id=current_bowler,
            runs_scored=runs
        )
        assert response.status_code == 200
    
    # Start second innings
    striker2 = game_helper.team_b_players[0]["id"]
    non_striker2 = game_helper.team_b_players[1]["id"]
    bowler3 = game_helper.team_a_players[0]["id"]
    bowler4 = game_helper.team_a_players[1]["id"]
    
    game_helper.start_next_innings(
        striker_id=striker2,
        non_striker_id=non_striker2,
        opening_bowler_id=bowler3
    )
    
    # Play 20 overs - second innings
    for i in range(120):
        batsman = striker2 if i % 2 == 0 else non_striker2
        runs = 1 if i % 6 < 5 else 6  # Mix of 1s and 6s
        # Rotate bowlers every over
        current_bowler = bowler3 if (i // 6) % 2 == 0 else bowler4
        
        response = game_helper.post_delivery(
            batsman_id=batsman,
            bowler_id=current_bowler,
            runs_scored=runs
        )
        assert response.status_code == 200
    
    # Finalize
    game_helper.finalize_game()
    
    # Verify
    snapshot = game_helper.get_snapshot()
    deliveries = game_helper.get_deliveries()
    
    # Second innings may end early if target is reached
    assert len(deliveries) >= 120  # At least first innings complete
    assert len(deliveries) <= 240  # At most both innings complete
    assert snapshot.get("result") is not None


def test_match_with_wickets_and_extras(game_helper, assert_helper):
    """Test a match combining wickets and extras."""
    # Create game
    game_helper.create_game()
    game_helper.set_openers(team="A")
    
    striker = game_helper.team_a_players[0]["id"]
    bowler = game_helper.team_b_players[0]["id"]
    
    # Post normal delivery
    game_helper.post_delivery(striker, bowler, runs_scored=1)
    
    # Post wide
    game_helper.post_delivery(
        striker, bowler, 
        runs_scored=1, 
        extra_type="wd"
    )
    
    # Post wicket
    game_helper.post_delivery(
        striker, bowler,
        runs_scored=0,
        is_wicket=True,
        dismissal_type="bowled"
    )
    
    # Select new batsman
    new_batsman = game_helper.team_a_players[2]["id"]
    game_helper.select_next_batsman(new_batsman)
    
    # Post no-ball with runs
    game_helper.post_delivery(
        new_batsman, bowler,
        runs_scored=5,
        extra_type="nb",
        runs_off_bat=4
    )
    
    # Post normal delivery
    game_helper.post_delivery(new_batsman, bowler, runs_scored=4)
    
    # Verify
    deliveries = game_helper.get_deliveries()
    assert len(deliveries) == 5
    assert_helper.assert_wicket_count(deliveries, 1)
    
    extras_count = sum(1 for d in deliveries if d.get("extra_type"))
    assert extras_count == 2


def test_innings_transition(game_helper, assert_helper):
    """Test the transition between innings."""
    # Create game with 1 over per innings
    game_helper.create_game(overs_limit=1)
    game_helper.set_openers(team="A")
    
    striker = game_helper.team_a_players[0]["id"]
    bowler = game_helper.team_b_players[0]["id"]
    
    # Play first innings (6 balls)
    for i in range(6):
        response = game_helper.post_delivery(
            batsman_id=striker,
            bowler_id=bowler,
            runs_scored=2
        )
        assert response.status_code == 200
    
    # Get snapshot after first innings
    snapshot1 = game_helper.get_snapshot()
    assert snapshot1.get("current_inning") == 1
    
    # Start second innings
    striker2 = game_helper.team_b_players[0]["id"]
    non_striker2 = game_helper.team_b_players[1]["id"]
    bowler2 = game_helper.team_a_players[0]["id"]
    
    game_helper.start_next_innings(
        striker_id=striker2,
        non_striker_id=non_striker2,
        opening_bowler_id=bowler2
    )
    
    # Get snapshot after starting second innings
    snapshot2 = game_helper.get_snapshot()
    assert snapshot2.get("current_inning") == 2
    
    # Verify first innings summary exists
    assert_helper.assert_innings_summary(snapshot2, runs=12, overs=1)
    
    # Play second innings (6 balls)
    for i in range(6):
        response = game_helper.post_delivery(
            batsman_id=striker2,
            bowler_id=bowler2,
            runs_scored=1
        )
        assert response.status_code == 200
    
    # Finalize and verify result
    game_helper.finalize_game()
    snapshot3 = game_helper.get_snapshot()
    
    assert snapshot3.get("result") is not None
    result_text = snapshot3["result"].get("result_text", "")
    assert len(result_text) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])




