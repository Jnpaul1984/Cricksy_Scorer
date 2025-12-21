#!/usr/bin/env python3
"""
Test script for Player Career Analyzer

Run after backend is running: python test_player_career.py
"""

import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path.parent))

from backend.services.player_career_analyzer import get_player_career_summary


def test_player_career_analyzer():
    """Test the player career analyzer with sample data"""
    print("=" * 70)
    print("TESTING PLAYER CAREER ANALYZER")
    print("=" * 70)

    # Test Case 1: Aggressive Finisher
    print("\n📊 Test 1: Aggressive Finisher (High SR, Boundaries)")
    print("-" * 70)

    batting_records_1 = [
        {
            "runs": 45,
            "balls_faced": 32,
            "fours": 4,
            "sixes": 1,
            "is_out": True,
            "how_out": "caught",
        },
        {"runs": 52, "balls_faced": 38, "fours": 5, "sixes": 1, "is_out": False, "how_out": None},
        {
            "runs": 38,
            "balls_faced": 28,
            "fours": 3,
            "sixes": 1,
            "is_out": True,
            "how_out": "bowled",
        },
        {"runs": 55, "balls_faced": 40, "fours": 4, "sixes": 2, "is_out": False, "how_out": None},
        {"runs": 48, "balls_faced": 35, "fours": 4, "sixes": 1, "is_out": True, "how_out": "lbw"},
    ]

    summary_1 = get_player_career_summary(
        player_id="player_001",
        player_name="Virat Kohli",
        batting_records=batting_records_1,
        bowling_records=[],
    )

    print(f"Name: {summary_1['player_name']}")
    print(
        f"Specialization: {summary_1['specialization']} ({summary_1['specialization_confidence']:.0%})"
    )
    print(f"Career Summary: {summary_1['career_summary']}")
    print(f"\nBatting Stats:")
    print(f"  Matches: {summary_1['batting_stats']['matches']}")
    print(f"  Average: {summary_1['batting_stats']['average']}")
    print(f"  Strike Rate: {summary_1['batting_stats']['strike_rate']}")
    print(f"  Consistency: {summary_1['batting_stats']['consistency_score']:.1f}%")
    print(f"  Boundary %: {summary_1['batting_stats']['boundary_percentage']:.1f}%")
    print(f"\nRecent Form: {summary_1['recent_form']['trend']}")
    print(f"Highlights:")
    for highlight in summary_1["career_highlights"]:
        print(f"  {highlight}")
    assert summary_1["specialization"] in [
        "Finisher",
        "Batter",
    ], f"Expected Finisher, got {summary_1['specialization']}"
    print("✅ Test 1 PASSED")

    # Test Case 2: Consistent Opener
    print("\n📊 Test 2: Consistent Opener (High Avg, Moderate SR)")
    print("-" * 70)

    batting_records_2 = [
        {"runs": 65, "balls_faced": 85, "fours": 6, "sixes": 0, "is_out": False, "how_out": None},
        {
            "runs": 58,
            "balls_faced": 78,
            "fours": 5,
            "sixes": 0,
            "is_out": True,
            "how_out": "caught",
        },
        {"runs": 72, "balls_faced": 92, "fours": 7, "sixes": 0, "is_out": False, "how_out": None},
        {
            "runs": 51,
            "balls_faced": 68,
            "fours": 4,
            "sixes": 0,
            "is_out": True,
            "how_out": "bowled",
        },
        {"runs": 61, "balls_faced": 80, "fours": 6, "sixes": 0, "is_out": False, "how_out": None},
    ]

    summary_2 = get_player_career_summary(
        player_id="player_002",
        player_name="Rohit Sharma",
        batting_records=batting_records_2,
        bowling_records=[],
    )

    print(f"Name: {summary_2['player_name']}")
    print(
        f"Specialization: {summary_2['specialization']} ({summary_2['specialization_confidence']:.0%})"
    )
    print(f"Average: {summary_2['batting_stats']['average']}")
    print(f"Strike Rate: {summary_2['batting_stats']['strike_rate']}")
    print(f"Consistency: {summary_2['batting_stats']['consistency_score']:.1f}%")
    print(f"\nHighlights:")
    for highlight in summary_2["career_highlights"]:
        print(f"  {highlight}")
    assert summary_2["specialization"] in [
        "Opener",
        "Batter",
    ], f"Expected Opener, got {summary_2['specialization']}"
    print("✅ Test 2 PASSED")

    # Test Case 3: All-rounder
    print("\n📊 Test 3: All-rounder (Batting + Bowling)")
    print("-" * 70)

    batting_records_3 = [
        {
            "runs": 42,
            "balls_faced": 50,
            "fours": 3,
            "sixes": 1,
            "is_out": True,
            "how_out": "caught",
        },
        {"runs": 38, "balls_faced": 45, "fours": 3, "sixes": 0, "is_out": False, "how_out": None},
        {"runs": 45, "balls_faced": 52, "fours": 4, "sixes": 0, "is_out": True, "how_out": "lbw"},
        {"runs": 50, "balls_faced": 58, "fours": 4, "sixes": 1, "is_out": False, "how_out": None},
        {
            "runs": 60,
            "balls_faced": 65,
            "fours": 5,
            "sixes": 1,
            "is_out": True,
            "how_out": "caught",
        },
        {"runs": 35, "balls_faced": 40, "fours": 2, "sixes": 1, "is_out": False, "how_out": None},
        {
            "runs": 48,
            "balls_faced": 55,
            "fours": 3,
            "sixes": 1,
            "is_out": True,
            "how_out": "bowled",
        },
        {"runs": 55, "balls_faced": 62, "fours": 4, "sixes": 1, "is_out": False, "how_out": None},
        {
            "runs": 42,
            "balls_faced": 48,
            "fours": 3,
            "sixes": 1,
            "is_out": True,
            "how_out": "caught",
        },
        {"runs": 39, "balls_faced": 45, "fours": 2, "sixes": 1, "is_out": False, "how_out": None},
    ]

    bowling_records_3 = [
        {"overs_bowled": 4.0, "maidens": 1, "runs_conceded": 28, "wickets_taken": 1},
        {"overs_bowled": 3.5, "maidens": 0, "runs_conceded": 32, "wickets_taken": 2},
        {"overs_bowled": 4.0, "maidens": 1, "runs_conceded": 25, "wickets_taken": 1},
        {"overs_bowled": 3.0, "maidens": 1, "runs_conceded": 21, "wickets_taken": 2},
        {"overs_bowled": 4.0, "maidens": 0, "runs_conceded": 29, "wickets_taken": 1},
        {"overs_bowled": 3.5, "maidens": 1, "runs_conceded": 26, "wickets_taken": 2},
    ]

    summary_3 = get_player_career_summary(
        player_id="player_003",
        player_name="Ben Stokes",
        batting_records=batting_records_3,
        bowling_records=bowling_records_3,
    )

    print(f"Name: {summary_3['player_name']}")
    print(
        f"Specialization: {summary_3['specialization']} ({summary_3['specialization_confidence']:.0%})"
    )
    print(f"\nBatting Stats:")
    print(f"  Matches: {summary_3['batting_stats']['matches']}")
    print(f"  Total Runs: {summary_3['batting_stats']['total_runs']}")
    print(f"  Average: {summary_3['batting_stats']['average']}")
    print(f"\nBowling Stats:")
    print(f"  Matches: {summary_3['bowling_stats']['matches']}")
    print(f"  Wickets: {summary_3['bowling_stats']['total_wickets']}")
    print(f"  Economy: {summary_3['bowling_stats']['economy_rate']}")
    print(f"\nHighlights:")
    for highlight in summary_3["career_highlights"]:
        print(f"  {highlight}")
    assert (
        summary_3["specialization"] == "All-rounder"
    ), f"Expected All-rounder, got {summary_3['specialization']}"
    print("✅ Test 3 PASSED")

    # Test Case 4: Pure Bowler
    print("\n📊 Test 4: Pure Bowler (Excellent Economy)")
    print("-" * 70)

    bowling_records_4 = [
        {"overs_bowled": 4.0, "maidens": 2, "runs_conceded": 18, "wickets_taken": 2},
        {"overs_bowled": 4.0, "maidens": 1, "runs_conceded": 22, "wickets_taken": 2},
        {"overs_bowled": 4.0, "maidens": 2, "runs_conceded": 16, "wickets_taken": 3},
        {"overs_bowled": 4.0, "maidens": 1, "runs_conceded": 24, "wickets_taken": 2},
        {"overs_bowled": 4.0, "maidens": 2, "runs_conceded": 20, "wickets_taken": 3},
    ]

    summary_4 = get_player_career_summary(
        player_id="player_004",
        player_name="Jasprit Bumrah",
        batting_records=[],
        bowling_records=bowling_records_4,
    )

    print(f"Name: {summary_4['player_name']}")
    print(
        f"Specialization: {summary_4['specialization']} ({summary_4['specialization_confidence']:.0%})"
    )
    print(f"\nBowling Stats:")
    print(f"  Matches: {summary_4['bowling_stats']['matches']}")
    print(f"  Wickets: {summary_4['bowling_stats']['total_wickets']}")
    print(f"  Economy: {summary_4['bowling_stats']['economy_rate']}")
    print(f"  Maiden %: {summary_4['bowling_stats']['maiden_percentage']:.1f}%")
    print(f"\nHighlights:")
    for highlight in summary_4["career_highlights"]:
        print(f"  {highlight}")
    assert (
        summary_4["specialization"] == "Bowler"
    ), f"Expected Bowler, got {summary_4['specialization']}"
    print("✅ Test 4 PASSED")

    print("\n" + "=" * 70)
    print("✅ ALL TESTS PASSED!")
    print("=" * 70)
    print("\nCareer Analyzer Features:")
    print("- Specialization Detection: Opener, Finisher, Bowler, All-rounder, Batter")
    print("- Batting Analysis: Average, SR, Consistency, Boundaries, Centuries/Fifties")
    print("- Bowling Analysis: Wickets, Economy, Maidens, Effectiveness")
    print("- Recent Form Tracking: Trend (improving/declining/stable), Recent Average")
    print("- Best Performances: Best batting & bowling records")
    print("- Career Highlights: AI-generated achievement summary")
    print("- Confidence Scoring: 0-1 confidence in specialization classification")


if __name__ == "__main__":
    test_player_career_analyzer()
