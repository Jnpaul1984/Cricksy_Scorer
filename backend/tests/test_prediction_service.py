"""
Unit tests for the win probability prediction service.
"""

import pytest
from backend.services.prediction_service import (
    WinProbabilityPredictor,
    get_win_probability,
)


class TestWinProbabilityPredictor:
    """Tests for WinProbabilityPredictor class"""

    def test_first_innings_early_stage(self):
        """Test prediction in early first innings - should have low confidence"""
        result = WinProbabilityPredictor.calculate_win_probability(
            current_inning=1,
            total_runs=15,
            total_wickets=0,
            overs_completed=1,
            balls_this_over=3,
            overs_limit=20,
            target=None,
        )
        
        assert "batting_team_win_prob" in result
        assert "bowling_team_win_prob" in result
        assert "confidence" in result
        
        # Early innings should have near 50-50 and low confidence
        assert 40 <= result["batting_team_win_prob"] <= 60
        assert result["confidence"] < 30
        assert result["batting_team_win_prob"] + result["bowling_team_win_prob"] == 100.0

    def test_first_innings_strong_position(self):
        """Test first innings with strong batting position"""
        result = WinProbabilityPredictor.calculate_win_probability(
            current_inning=1,
            total_runs=120,
            total_wickets=2,
            overs_completed=15,
            balls_this_over=0,
            overs_limit=20,
            target=None,
        )
        
        # Strong position should favor batting team (or be close to neutral)
        assert result["batting_team_win_prob"] >= 45
        assert result["confidence"] > 50

    def test_first_innings_weak_position(self):
        """Test first innings with weak batting position"""
        result = WinProbabilityPredictor.calculate_win_probability(
            current_inning=1,
            total_runs=60,
            total_wickets=7,
            overs_completed=15,
            balls_this_over=0,
            overs_limit=20,
            target=None,
        )
        
        # Weak position should favor bowling team
        assert result["batting_team_win_prob"] < 50

    def test_first_innings_no_overs_limit(self):
        """Test first innings without overs limit"""
        result = WinProbabilityPredictor.calculate_win_probability(
            current_inning=1,
            total_runs=100,
            total_wickets=3,
            overs_completed=10,
            balls_this_over=0,
            overs_limit=None,
            target=None,
        )
        
        # Should return neutral with zero confidence
        assert result["batting_team_win_prob"] == 50.0
        assert result["confidence"] == 0.0

    def test_second_innings_target_achieved(self):
        """Test second innings when target is achieved"""
        result = WinProbabilityPredictor.calculate_win_probability(
            current_inning=2,
            total_runs=151,
            total_wickets=5,
            overs_completed=18,
            balls_this_over=3,
            overs_limit=20,
            target=151,
        )
        
        # Target achieved - batting team should have 100%
        assert result["batting_team_win_prob"] == 100.0
        assert result["bowling_team_win_prob"] == 0.0
        assert result["confidence"] == 100.0

    def test_second_innings_all_out(self):
        """Test second innings when all wickets fallen"""
        result = WinProbabilityPredictor.calculate_win_probability(
            current_inning=2,
            total_runs=140,
            total_wickets=10,
            overs_completed=18,
            balls_this_over=3,
            overs_limit=20,
            target=151,
        )
        
        # All out - bowling team should have 100%
        assert result["batting_team_win_prob"] == 0.0
        assert result["bowling_team_win_prob"] == 100.0
        assert result["confidence"] == 100.0

    def test_second_innings_overs_completed(self):
        """Test second innings when overs are exhausted"""
        result = WinProbabilityPredictor.calculate_win_probability(
            current_inning=2,
            total_runs=140,
            total_wickets=5,
            overs_completed=20,
            balls_this_over=0,
            overs_limit=20,
            target=151,
        )
        
        # Overs done without reaching target - bowling team wins
        assert result["batting_team_win_prob"] == 0.0
        assert result["bowling_team_win_prob"] == 100.0
        assert result["confidence"] == 100.0

    def test_second_innings_comfortable_chase(self):
        """Test second innings with comfortable chase"""
        result = WinProbabilityPredictor.calculate_win_probability(
            current_inning=2,
            total_runs=100,
            total_wickets=2,
            overs_completed=12,
            balls_this_over=0,
            overs_limit=20,
            target=140,
        )
        
        # Need 40 from 48 balls with 8 wickets - should be reasonably balanced
        assert result["batting_team_win_prob"] > 55
        assert "required_run_rate" in result["factors"]
        assert result["factors"]["runs_needed"] == 40

    def test_second_innings_difficult_chase(self):
        """Test second innings with difficult chase"""
        result = WinProbabilityPredictor.calculate_win_probability(
            current_inning=2,
            total_runs=100,
            total_wickets=7,
            overs_completed=18,
            balls_this_over=0,
            overs_limit=20,
            target=160,
        )
        
        # Need 60 from 12 balls with 3 wickets - very difficult
        assert result["batting_team_win_prob"] < 30
        assert result["factors"]["required_run_rate"] > 12

    def test_second_innings_no_target(self):
        """Test second innings without target set"""
        result = WinProbabilityPredictor.calculate_win_probability(
            current_inning=2,
            total_runs=50,
            total_wickets=2,
            overs_completed=5,
            balls_this_over=0,
            overs_limit=20,
            target=None,
        )
        
        # No target - should return neutral
        assert result["batting_team_win_prob"] == 50.0
        assert result["confidence"] == 0.0

    def test_probability_sum_to_100(self):
        """Test that probabilities always sum to 100"""
        test_cases = [
            # (inning, runs, wickets, overs, balls, limit, target)
            (1, 50, 2, 5, 3, 20, None),
            (1, 150, 5, 18, 2, 20, None),
            (2, 100, 3, 10, 0, 20, 150),
            (2, 75, 7, 15, 4, 20, 120),
        ]
        
        for inning, runs, wickets, overs, balls, limit, target in test_cases:
            result = WinProbabilityPredictor.calculate_win_probability(
                current_inning=inning,
                total_runs=runs,
                total_wickets=wickets,
                overs_completed=overs,
                balls_this_over=balls,
                overs_limit=limit,
                target=target,
            )
            
            total = result["batting_team_win_prob"] + result["bowling_team_win_prob"]
            assert abs(total - 100.0) < 0.1, f"Probabilities don't sum to 100: {total}"

    def test_confidence_increases_with_progress(self):
        """Test that confidence increases as match progresses"""
        confidences = []
        
        for overs in [2, 6, 10, 15, 18]:
            result = WinProbabilityPredictor.calculate_win_probability(
                current_inning=1,
                total_runs=overs * 8,
                total_wickets=2,
                overs_completed=overs,
                balls_this_over=0,
                overs_limit=20,
                target=None,
            )
            confidences.append(result["confidence"])
        
        # Confidence should generally increase
        for i in range(len(confidences) - 1):
            assert confidences[i] <= confidences[i + 1]

    def test_factors_included(self):
        """Test that factors are included in result"""
        result = WinProbabilityPredictor.calculate_win_probability(
            current_inning=2,
            total_runs=80,
            total_wickets=3,
            overs_completed=10,
            balls_this_over=3,
            overs_limit=20,
            target=150,
        )
        
        assert "factors" in result
        factors = result["factors"]
        assert "runs_needed" in factors
        assert "balls_remaining" in factors
        assert "required_run_rate" in factors
        assert "wickets_remaining" in factors


class TestGetWinProbabilityFunction:
    """Tests for get_win_probability convenience function"""

    def test_get_win_probability_with_dict(self):
        """Test convenience function with game state dict"""
        game_state = {
            "current_inning": 2,
            "total_runs": 100,
            "total_wickets": 4,
            "overs_completed": 12,
            "balls_this_over": 2,
            "overs_limit": 20,
            "target": 160,
            "match_type": "limited",
        }
        
        result = get_win_probability(game_state)
        
        assert "batting_team_win_prob" in result
        assert "bowling_team_win_prob" in result
        assert result["factors"]["runs_needed"] == 60

    def test_get_win_probability_with_defaults(self):
        """Test convenience function handles missing values"""
        game_state = {
            "overs_limit": 20,
        }
        
        result = get_win_probability(game_state)
        
        # Should use defaults
        assert "batting_team_win_prob" in result
        assert result["batting_team_win_prob"] == 50.0
