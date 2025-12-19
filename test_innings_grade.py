#!/usr/bin/env python3
"""
Quick test script to validate Innings Grade Calculator API
Run after backend is running: python test_innings_grade.py
"""

import asyncio
import sys
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent / "backend"
sys.path.insert(0, str(backend_path.parent))

from backend.services.innings_grade_service import InningsGradeCalculator, get_innings_grade


async def test_innings_grade_calculator():
    """Test the innings grade calculator with sample data"""
    print("=" * 60)
    print("TESTING INNINGS GRADE CALCULATOR")
    print("=" * 60)
    
    # Test Case 1: Excellent T20 innings (180+ runs in 20 overs)
    print("\n📊 Test 1: Excellent T20 Innings (180 runs, 20 overs)")
    print("-" * 60)
    result1 = InningsGradeCalculator.calculate_innings_grade(
        total_runs=180,
        total_wickets=2,
        overs_completed=20,
        balls_this_over=0,
        overs_limit=20,
        deliveries=[
            {"runs_scored": 4, "extra": None},
            {"runs_scored": 6, "extra": None},
            {"runs_scored": 4, "extra": None},
            # Simulating ~10 boundaries out of 120 deliveries
        ] + [{"runs_scored": 0, "extra": None} for _ in range(116)],
        is_completed=True
    )
    print(f"Grade: {result1['grade']} ({result1['score_percentage']:.0f}% of par)")
    print(f"Total Runs: {result1['total_runs']}/{result1['wickets_lost']}")
    print(f"Run Rate: {result1['run_rate']:.2f}")
    print(f"Boundary Efficiency: {result1['boundary_percentage']:.1f}%")
    print(f"Factors: {result1['grade_factors']}")
    # 180 runs vs 160 par = 112%, which is B (100-129% range)
    assert result1['grade'] in ['B', 'A', 'A+'], f"Expected B or higher, got {result1['grade']}"
    print("✅ Test 1 PASSED")
    
    # Test Case 2: Average T20 innings (110 runs in 20 overs)
    print("\n📊 Test 2: Average T20 Innings (110 runs, 20 overs)")
    print("-" * 60)
    result2 = InningsGradeCalculator.calculate_innings_grade(
        total_runs=110,
        total_wickets=3,
        overs_completed=20,
        balls_this_over=0,
        overs_limit=20,
        deliveries=[{"runs_scored": 0, "extra": None} for _ in range(120)],
        is_completed=True
    )
    print(f"Grade: {result2['grade']} ({result2['score_percentage']:.0f}% of par)")
    print(f"Total Runs: {result2['total_runs']}/{result2['wickets_lost']}")
    print(f"Run Rate: {result2['run_rate']:.2f}")
    print(f"Factors: {result2['grade_factors']}")
    assert result2['grade'] in ['C', 'D'], f"Expected C or D, got {result2['grade']}"
    print("✅ Test 2 PASSED")
    
    # Test Case 3: Good ODI innings (290 runs in 50 overs, 6 wickets)
    print("\n📊 Test 3: Good ODI Innings (290 runs, 50 overs, 6/10 wickets)")
    print("-" * 60)
    result3 = InningsGradeCalculator.calculate_innings_grade(
        total_runs=290,
        total_wickets=6,
        overs_completed=50,
        balls_this_over=0,
        overs_limit=50,
        deliveries=[{"runs_scored": 0, "extra": None} for _ in range(300)],
        is_completed=True
    )
    print(f"Grade: {result3['grade']} ({result3['score_percentage']:.0f}% of par)")
    print(f"Total Runs: {result3['total_runs']}/{result3['wickets_lost']}")
    print(f"Run Rate: {result3['run_rate']:.2f}")
    print(f"Wicket Efficiency: {result3['wicket_efficiency']:.2f}")
    print(f"Factors: {result3['grade_factors']}")
    assert result3['grade'] in ['A', 'B'], f"Expected A or B, got {result3['grade']}"
    print("✅ Test 3 PASSED")
    
    # Test Case 4: Poor T20 innings (80 runs in 20 overs, 4 wickets)
    print("\n📊 Test 4: Poor T20 Innings (80 runs, 20 overs, 4/10 wickets)")
    print("-" * 60)
    result4 = InningsGradeCalculator.calculate_innings_grade(
        total_runs=80,
        total_wickets=4,
        overs_completed=20,
        balls_this_over=0,
        overs_limit=20,
        deliveries=[{"runs_scored": 0, "extra": None} for _ in range(120)],
        is_completed=True
    )
    print(f"Grade: {result4['grade']} ({result4['score_percentage']:.0f}% of par)")
    print(f"Total Runs: {result4['total_runs']}/{result4['wickets_lost']}")
    print(f"Run Rate: {result4['run_rate']:.2f}")
    print(f"Factors: {result4['grade_factors']}")
    assert result4['grade'] == 'D', f"Expected D, got {result4['grade']}"
    print("✅ Test 4 PASSED")
    
    print("\n" + "=" * 60)
    print("✅ ALL TESTS PASSED!")
    print("=" * 60)
    print("\nInnings Grade System Summary:")
    print("- Grade A+: ≥150% of par score (exceptional)")
    print("- Grade A:  130-149% of par (very good)")
    print("- Grade B:  100-129% of par (good)")
    print("- Grade C:  70-99% of par (average)")
    print("- Grade D:  <70% of par (below average)")
    print("\nPar Scores:")
    print("- T20 (20 overs): 160 runs @ 8.0 RR")
    print("- ODI (50 overs): 270 runs @ 5.4 RR")
    print("- Default: 7.5 runs/over")


if __name__ == "__main__":
    asyncio.run(test_innings_grade_calculator())
