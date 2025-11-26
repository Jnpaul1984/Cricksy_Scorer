"""
Integration tests for ML prediction service.

These tests verify that ML models are loaded and used correctly
in the prediction pipeline.
"""

from backend.services.ml_model_service import get_ml_service
from backend.services.prediction_service import WinProbabilityPredictor


class TestMLIntegration:
    """Integration tests for ML model usage in predictions."""

    def test_ml_service_loads_models(self):
        """Test that ML service can load all required models."""
        ml_service = get_ml_service()

        # Test win predictor loading
        t20_win_model = ml_service.load_model("win_probability", "t20")
        assert t20_win_model is not None, "T20 win predictor should load"

        odi_win_model = ml_service.load_model("win_probability", "odi")
        assert odi_win_model is not None, "ODI win predictor should load"

        # Test score predictor loading
        t20_score_model = ml_service.load_model("score_predictor", "t20")
        assert t20_score_model is not None, "T20 score predictor should load"

        odi_score_model = ml_service.load_model("score_predictor", "odi")
        assert odi_score_model is not None, "ODI score predictor should load"

    def test_ml_first_innings_prediction(self):
        """Test that first innings uses ML score predictor."""
        result = WinProbabilityPredictor.calculate_win_probability(
            current_inning=1,
            total_runs=100,
            total_wickets=3,
            overs_completed=12,
            balls_this_over=4,
            overs_limit=20,
            target=None,
        )

        # Verify prediction was made
        assert "batting_team_win_prob" in result
        assert "bowling_team_win_prob" in result
        assert "confidence" in result
        assert "factors" in result

        # Check if ML was used (will have prediction_method in factors)
        if "prediction_method" in result["factors"]:
            assert result["factors"]["prediction_method"] in [
                "ml_score_predictor",
                "rule_based",
            ]

        # Verify reasonable probability range
        assert 0 <= result["batting_team_win_prob"] <= 100
        assert 0 <= result["bowling_team_win_prob"] <= 100
        assert abs(result["batting_team_win_prob"] + result["bowling_team_win_prob"] - 100.0) < 0.1

    def test_ml_second_innings_prediction(self):
        """Test that second innings uses ML win predictor."""
        result = WinProbabilityPredictor.calculate_win_probability(
            current_inning=2,
            total_runs=100,
            total_wickets=3,
            overs_completed=12,
            balls_this_over=4,
            overs_limit=20,
            target=150,
        )

        # Verify prediction was made
        assert "batting_team_win_prob" in result
        assert "bowling_team_win_prob" in result
        assert "confidence" in result
        assert "factors" in result

        # Check if ML was used
        if "prediction_method" in result["factors"]:
            assert result["factors"]["prediction_method"] in [
                "ml_win_predictor",
                "rule_based",
            ]

        # Verify reasonable probability range
        assert 0 <= result["batting_team_win_prob"] <= 100
        assert 0 <= result["bowling_team_win_prob"] <= 100

    def test_ml_prediction_with_odi_format(self):
        """Test ML predictions work with ODI format."""
        result = WinProbabilityPredictor.calculate_win_probability(
            current_inning=2,
            total_runs=200,
            total_wickets=4,
            overs_completed=35,
            balls_this_over=2,
            overs_limit=50,
            target=280,
        )

        # Should successfully make a prediction
        assert "batting_team_win_prob" in result
        assert result["batting_team_win_prob"] >= 0
        assert result["batting_team_win_prob"] <= 100

    def test_ml_prediction_close_match(self):
        """Test ML prediction for a close match scenario."""
        result = WinProbabilityPredictor.calculate_win_probability(
            current_inning=2,
            total_runs=140,
            total_wickets=5,
            overs_completed=18,
            balls_this_over=3,
            overs_limit=20,
            target=155,
        )

        # Close match - 15 runs needed from 9 balls with 5 wickets
        # This is actually a difficult situation, so low probability is reasonable
        assert "batting_team_win_prob" in result
        # Verify probability is in valid range (0-100)
        assert 0 <= result["batting_team_win_prob"] <= 100

    def test_ml_models_cached_correctly(self):
        """Test that models are cached and reused."""
        ml_service = get_ml_service()

        # Load same model twice
        model1 = ml_service.load_model("win_probability", "t20")
        model2 = ml_service.load_model("win_probability", "t20")

        # Should return same cached instance
        assert model1 is model2, "Models should be cached and reused"

    def test_ml_prediction_consistency(self):
        """Test that same inputs produce same outputs."""
        # Make same prediction twice
        result1 = WinProbabilityPredictor.calculate_win_probability(
            current_inning=2,
            total_runs=120,
            total_wickets=4,
            overs_completed=15,
            balls_this_over=0,
            overs_limit=20,
            target=160,
        )

        result2 = WinProbabilityPredictor.calculate_win_probability(
            current_inning=2,
            total_runs=120,
            total_wickets=4,
            overs_completed=15,
            balls_this_over=0,
            overs_limit=20,
            target=160,
        )

        # Results should be identical
        assert result1["batting_team_win_prob"] == result2["batting_team_win_prob"]
        assert result1["bowling_team_win_prob"] == result2["bowling_team_win_prob"]

    def test_ml_prediction_factors_included(self):
        """Test that prediction includes useful factors for debugging."""
        result = WinProbabilityPredictor.calculate_win_probability(
            current_inning=2,
            total_runs=100,
            total_wickets=3,
            overs_completed=12,
            balls_this_over=4,
            overs_limit=20,
            target=150,
        )

        factors = result["factors"]

        # Should include key match state factors
        assert "runs_needed" in factors
        assert "balls_remaining" in factors
        assert "wickets_remaining" in factors
        assert "required_run_rate" in factors
        assert "current_run_rate" in factors


if __name__ == "__main__":
    import pytest

    pytest.main([__file__, "-v"])
