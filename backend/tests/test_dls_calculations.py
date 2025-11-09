"""
Comprehensive tests for DLS (Duckworth-Lewis-Stern) calculations.

These tests verify the accuracy and correctness of DLS target calculations
for rain-affected matches in both T20 and ODI formats.
"""

import pytest
import math
from pathlib import Path
from dls import (
    ResourceTable,
    DLSEnv,
    compute_dls_target,
    revised_target,
    total_resources_team1,
    total_resources_team2,
    compute_state_from_ledger,
    InningsState,
)


class TestResourceTable:
    """Tests for the ResourceTable class and resource lookup."""

    def test_resource_table_loads_from_json(self):
        """Test that resource tables can be loaded from JSON files."""
        # This should load the T20 table
        from dls import _resource_table_for_format
        
        table = _resource_table_for_format(20)
        assert table is not None
        assert table.max_overs == 20
        
        # Check that resources at start are 100%
        R_start = table.R(20, 0)
        assert 95.0 <= R_start <= 100.0, "Resources at start should be ~100%"
        
        # Check that resources at end are 0%
        R_end = table.R(0, 0)
        assert R_end == 0.0, "Resources at end should be 0%"

    def test_resource_decreases_with_overs(self):
        """Test that resources decrease as overs are bowled."""
        from dls import _resource_table_for_format
        
        table = _resource_table_for_format(20)
        
        # Resources should decrease as overs are bowled
        R_20 = table.R(20, 0)  # Start of innings
        R_10 = table.R(10, 0)  # Halfway through
        R_0 = table.R(0, 0)    # End of innings
        
        assert R_20 > R_10 > R_0, "Resources should decrease with overs bowled"

    def test_resource_decreases_with_wickets(self):
        """Test that resources decrease as wickets fall."""
        from dls import _resource_table_for_format
        
        table = _resource_table_for_format(20)
        
        # Resources should decrease as wickets fall (at same overs remaining)
        R_0w = table.R(10, 0)  # 10 overs left, 0 wickets
        R_5w = table.R(10, 5)  # 10 overs left, 5 wickets
        R_9w = table.R(10, 9)  # 10 overs left, 9 wickets
        
        assert R_0w > R_5w > R_9w, "Resources should decrease with wickets lost"

    def test_resource_interpolation(self):
        """Test that fractional overs are interpolated correctly."""
        from dls import _resource_table_for_format
        
        table = _resource_table_for_format(20)
        
        # Get resources for whole overs
        R_10 = table.R(10.0, 0)
        R_11 = table.R(11.0, 0)
        
        # Get resource for fractional over
        R_10_5 = table.R(10.5, 0)
        
        # Interpolated value should be between the two
        assert R_10 < R_10_5 < R_11, "Fractional overs should be interpolated"
        
        # Should be approximately halfway
        expected = (R_10 + R_11) / 2
        assert abs(R_10_5 - expected) < 2.0, "Interpolation should be approximately linear"


class TestDLSBasicCalculations:
    """Tests for basic DLS calculation scenarios."""

    def test_no_interruption_same_target(self):
        """Test that with no interruption, target is team1_score + 1."""
        result = compute_dls_target(
            team1_score=150,
            team1_wickets_lost=5,
            team1_overs_left_at_end=0.0,  # Completed innings
            format_overs=20,
            team2_wkts_lost_now=0,
            team2_overs_left_now=20.0,  # Full innings available
        )
        
        # With full resources, target should be close to team1_score + 1
        assert result.target >= 150, "Target should be at least team1 score"
        assert result.target <= 152, "Target should be approximately team1 score + 1"

    def test_reduced_overs_reduced_target(self):
        """Test that fewer overs available reduces the target."""
        # Team 1 scores 150 in 20 overs
        # Team 2 has only 10 overs
        result = compute_dls_target(
            team1_score=150,
            team1_wickets_lost=5,
            team1_overs_left_at_end=0.0,
            format_overs=20,
            team2_wkts_lost_now=0,
            team2_overs_left_now=10.0,  # Only 10 overs available
        )
        
        # Target should be significantly less than 150
        assert result.target < 150, "Target should be reduced with fewer overs"
        assert result.target > 50, "Target should be reasonable for 10 overs"

    def test_wickets_affect_resources(self):
        """Test that wickets lost affect available resources."""
        # Same scenario, but team 2 has lost wickets
        result_no_wickets = compute_dls_target(
            team1_score=150,
            team1_wickets_lost=5,
            team1_overs_left_at_end=0.0,
            format_overs=20,
            team2_wkts_lost_now=0,  # No wickets lost
            team2_overs_left_now=10.0,
        )
        
        result_with_wickets = compute_dls_target(
            team1_score=150,
            team1_wickets_lost=5,
            team1_overs_left_at_end=0.0,
            format_overs=20,
            team2_wkts_lost_now=5,  # 5 wickets lost
            team2_overs_left_now=10.0,
        )
        
        # Target should be lower when team 2 has lost wickets
        assert result_with_wickets.target < result_no_wickets.target, \
            "Target should be lower when chasing team has lost wickets"


class TestDLSRealisticScenarios:
    """Tests for realistic DLS scenarios based on actual cricket matches."""

    def test_t20_rain_interruption_scenario(self):
        """
        Test a realistic T20 scenario:
        - Team 1 scores 180/6 in 20 overs
        - Rain reduces Team 2's innings to 15 overs
        - Calculate revised target
        """
        result = compute_dls_target(
            team1_score=180,
            team1_wickets_lost=6,
            team1_overs_left_at_end=0.0,
            format_overs=20,
            team2_wkts_lost_now=0,
            team2_overs_left_now=15.0,
        )
        
        # Target should be between 115-130 (roughly 64-72% of 180)
        # DLS is conservative with reduced overs
        assert 115 <= result.target <= 135, \
            f"Target {result.target} seems unreasonable for 15-over chase of 180"
        
        # Resources should be calculated
        assert 0 < result.R1_total <= 100, "Team 1 resources should be 0-100%"
        assert 0 < result.R2_total <= 100, "Team 2 resources should be 0-100%"

    def test_mid_innings_interruption(self):
        """
        Test interruption during Team 2's chase:
        - Team 1 scored 160/5 in 20 overs
        - Team 2 is 80/2 after 10 overs when rain stops play
        - Overs reduced to 15 total
        - Calculate revised target
        """
        result = compute_dls_target(
            team1_score=160,
            team1_wickets_lost=5,
            team1_overs_left_at_end=0.0,
            format_overs=20,
            team2_wkts_lost_now=2,
            team2_overs_left_now=5.0,  # 5 overs remaining (15 total - 10 bowled)
        )
        
        # Par score should be calculated
        assert result.par_score > 0, "Par score should be calculated"
        
        # The target is the TOTAL target, not remaining runs
        # With reduced overs mid-innings, target should be positive
        assert result.target > 0, "Target should be positive"
        assert result.target < 160, "Target should be less than team 1 score due to reduced overs"

    def test_odi_scenario(self):
        """
        Test a 50-over ODI scenario:
        - Team 1 scores 280/7 in 50 overs
        - Rain reduces Team 2's innings to 40 overs
        """
        result = compute_dls_target(
            team1_score=280,
            team1_wickets_lost=7,
            team1_overs_left_at_end=0.0,
            format_overs=50,
            team2_wkts_lost_now=0,
            team2_overs_left_now=40.0,
        )
        
        # Target should be between 220-250 (roughly 80-90% of 280)
        assert 210 <= result.target <= 260, \
            f"Target {result.target} seems unreasonable for 40-over chase of 280"


class TestDLSEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_zero_overs_remaining(self):
        """Test calculation when no overs are remaining."""
        result = compute_dls_target(
            team1_score=150,
            team1_wickets_lost=5,
            team1_overs_left_at_end=0.0,
            format_overs=20,
            team2_wkts_lost_now=0,
            team2_overs_left_now=0.0,  # No overs remaining
        )
        
        # With no overs, target should be minimal
        assert result.target >= 1, "Target should be at least 1"
        assert result.R2_total == 0.0, "Resources should be 0 with no overs"

    def test_all_wickets_lost(self):
        """Test calculation when all wickets are lost."""
        result = compute_dls_target(
            team1_score=150,
            team1_wickets_lost=10,  # All out
            team1_overs_left_at_end=5.0,  # Some overs remaining
            format_overs=20,
            team2_wkts_lost_now=9,  # 9 wickets down
            team2_overs_left_now=10.0,
        )
        
        # Calculation should handle all-out scenario
        assert result.target > 0, "Target should be positive"
        assert result.R2_total > 0, "Resources should be positive with overs remaining"

    def test_very_low_score(self):
        """Test calculation with very low team 1 score."""
        result = compute_dls_target(
            team1_score=50,
            team1_wickets_lost=9,
            team1_overs_left_at_end=0.0,
            format_overs=20,
            team2_wkts_lost_now=0,
            team2_overs_left_now=15.0,
        )
        
        # Target should be reasonable even for low scores
        assert result.target >= 1, "Target should be at least 1"
        assert result.target <= 60, "Target should be close to team 1 score"

    def test_very_high_score(self):
        """Test calculation with very high team 1 score."""
        result = compute_dls_target(
            team1_score=250,
            team1_wickets_lost=3,
            team1_overs_left_at_end=0.0,
            format_overs=20,
            team2_wkts_lost_now=0,
            team2_overs_left_now=20.0,
        )
        
        # Target should be close to team 1 score + 1
        assert result.target >= 250, "Target should be at least team 1 score"
        assert result.target <= 252, "Target should be approximately team 1 score + 1"


class TestDLSHelperFunctions:
    """Tests for DLS helper functions."""

    def test_compute_state_from_ledger_legal_deliveries(self):
        """Test that legal deliveries are counted correctly."""
        deliveries = [
            {"runs_scored": 1, "extra": None, "is_wicket": False},
            {"runs_scored": 4, "extra": None, "is_wicket": False},
            {"runs_scored": 0, "extra": None, "is_wicket": True},
            {"runs_scored": 6, "extra": None, "is_wicket": False},
        ]
        
        state = compute_state_from_ledger(deliveries)
        
        assert state.balls_bowled == 4, "Should count 4 legal deliveries"
        assert state.wickets_lost == 1, "Should count 1 wicket"

    def test_compute_state_from_ledger_with_extras(self):
        """Test that wides and no-balls don't count as legal deliveries."""
        deliveries = [
            {"runs_scored": 1, "extra": None, "is_wicket": False},
            {"runs_scored": 1, "extra": "wd", "is_wicket": False},  # Wide
            {"runs_scored": 1, "extra": "nb", "is_wicket": False},  # No ball
            {"runs_scored": 4, "extra": None, "is_wicket": False},
        ]
        
        state = compute_state_from_ledger(deliveries)
        
        assert state.balls_bowled == 2, "Should count only 2 legal deliveries (excluding wide and no-ball)"
        assert state.wickets_lost == 0, "Should count 0 wickets"

    def test_revised_target_calculation(self):
        """Test the revised target calculation formula."""
        # Standard DLS formula: floor(S1 * (R2/R1)) + 1
        target = revised_target(
            S1=150,
            R1_total=100.0,  # Team 1 used 100% resources
            R2_total=75.0,   # Team 2 has 75% resources
        )
        
        # Expected: floor(150 * (75/100)) + 1 = floor(112.5) + 1 = 113
        assert target == 113, f"Expected 113, got {target}"

    def test_revised_target_with_partial_resources(self):
        """Test revised target when team 1 didn't use all resources."""
        target = revised_target(
            S1=120,
            R1_total=80.0,   # Team 1 used 80% resources (e.g., all out early)
            R2_total=100.0,  # Team 2 has full resources
        )
        
        # Expected: floor(120 * (100/80)) + 1 = floor(150) + 1 = 151
        assert target == 151, f"Expected 151, got {target}"


class TestDLSResourceCalculations:
    """Tests for resource calculations for both teams."""

    def test_team2_resources_full_innings(self):
        """Test that team 2 has full resources at start of innings."""
        from dls import _resource_table_for_format
        
        table = _resource_table_for_format(20)
        env = DLSEnv(table=table, G=150.0)
        
        R2 = total_resources_team2(
            env=env,
            max_overs_current=20,
            delivered_balls_so_far=0,
            wickets_lost_so_far=0,
        )
        
        # Should have close to 100% resources
        assert 95.0 <= R2 <= 100.0, f"Team 2 should have ~100% resources at start, got {R2}"

    def test_team2_resources_decrease_with_balls(self):
        """Test that team 2 resources decrease as balls are bowled."""
        from dls import _resource_table_for_format
        
        table = _resource_table_for_format(20)
        env = DLSEnv(table=table, G=150.0)
        
        R2_start = total_resources_team2(
            env=env,
            max_overs_current=20,
            delivered_balls_so_far=0,
            wickets_lost_so_far=0,
        )
        
        R2_mid = total_resources_team2(
            env=env,
            max_overs_current=20,
            delivered_balls_so_far=60,  # 10 overs
            wickets_lost_so_far=0,
        )
        
        R2_end = total_resources_team2(
            env=env,
            max_overs_current=20,
            delivered_balls_so_far=120,  # 20 overs
            wickets_lost_so_far=0,
        )
        
        assert R2_start > R2_mid > R2_end, "Resources should decrease as balls are bowled"
        assert R2_end == 0.0, "Resources should be 0 at end of innings"

    def test_team1_resources_no_interruptions(self):
        """Test team 1 resources with no interruptions."""
        from dls import _resource_table_for_format
        
        table = _resource_table_for_format(20)
        env = DLSEnv(table=table, G=150.0)
        
        deliveries = []  # Empty ledger
        interruptions = []  # No interruptions
        
        R1 = total_resources_team1(
            env=env,
            max_overs_initial=20,
            deliveries=deliveries,
            interruptions=interruptions,
        )
        
        # With no interruptions, should have full resources
        assert 95.0 <= R1 <= 100.0, f"Team 1 should have ~100% resources with no interruptions, got {R1}"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

