"""
Tests for ML feature engineering
"""

import pytest
import numpy as np
from backend.services.ml_features import (
    build_win_predictor_features,
    build_score_predictor_features,
)


class TestWinPredictorFeatures:
    """Tests for win predictor feature engineering."""

    def test_win_predictor_feature_shape(self):
        """Test that win predictor returns 12 features."""
        features = build_win_predictor_features(
            match_format="t20",
            total_runs=100,
            total_wickets=3,
            overs_completed=10,
            balls_this_over=3,
            overs_limit=20,
            target=150,
        )

        assert isinstance(features, np.ndarray)
        assert features.shape == (12,)
        assert features.dtype == np.float32

    def test_win_predictor_odi_format(self):
        """Test win predictor with ODI format."""
        features = build_win_predictor_features(
            match_format="odi",
            total_runs=200,
            total_wickets=4,
            overs_completed=35,
            balls_this_over=2,
            overs_limit=50,
            target=280,
        )

        assert features.shape == (12,)
        # Check some expected values
        assert features[0] > 0  # over_progress should be > 0
        assert features[1] > 0  # balls_left should be positive
        assert features[2] > 0  # wickets_left should be positive

    def test_win_predictor_no_nans(self):
        """Test that no NaNs or Infs are in output."""
        features = build_win_predictor_features(
            match_format="t20",
            total_runs=0,  # Edge case: no runs yet
            total_wickets=0,
            overs_completed=0,
            balls_this_over=0,
            overs_limit=20,
            target=160,
        )

        assert not np.any(np.isnan(features))
        assert not np.any(np.isinf(features))


class TestScorePredictorFeatures:
    """Tests for score predictor feature engineering."""

    def test_score_predictor_feature_shape(self):
        """Test that score predictor returns 22 features."""
        features = build_score_predictor_features(
            match_format="t20",
            total_runs=80,
            total_wickets=2,
            overs_completed=10,
            balls_this_over=4,
            overs_limit=20,
            is_powerplay=False,
        )

        assert isinstance(features, np.ndarray)
        assert features.shape == (22,)
        assert features.dtype == np.float32

    def test_score_predictor_odi_format(self):
        """Test score predictor with ODI format."""
        features = build_score_predictor_features(
            match_format="odi",
            total_runs=150,
            total_wickets=3,
            overs_completed=25,
            balls_this_over=3,
            overs_limit=50,
            is_powerplay=False,
        )

        assert features.shape == (22,)
        # Check some expected values
        assert features[0] == 150  # runs
        assert features[2] == 3  # wickets
        assert features[3] > 0  # run_rate

    def test_score_predictor_powerplay(self):
        """Test score predictor with powerplay flag."""
        features = build_score_predictor_features(
            match_format="t20",
            total_runs=40,
            total_wickets=1,
            overs_completed=5,
            balls_this_over=2,
            overs_limit=20,
            is_powerplay=True,
        )

        # Feature 20 is in_powerplay
        assert features[19] == 1.0  # in_powerplay should be 1.0

    def test_score_predictor_no_nans(self):
        """Test that no NaNs or Infs are in output."""
        features = build_score_predictor_features(
            match_format="t20",
            total_runs=0,  # Edge case: no runs yet
            total_wickets=0,
            overs_completed=0,
            balls_this_over=0,
            overs_limit=20,
            is_powerplay=True,
        )

        assert not np.any(np.isnan(features))
        assert not np.any(np.isinf(features))

    def test_score_predictor_match_phase(self):
        """Test match phase encoding."""
        # T20: early phase (< 6 overs)
        features_early = build_score_predictor_features(
            match_format="t20",
            total_runs=30,
            total_wickets=1,
            overs_completed=4,
            balls_this_over=0,
            overs_limit=20,
        )
        assert features_early[7] == 0  # match_phase_id = 0 (early)

        # T20: death phase (>= 15 overs)
        features_death = build_score_predictor_features(
            match_format="t20",
            total_runs=140,
            total_wickets=5,
            overs_completed=17,
            balls_this_over=3,
            overs_limit=20,
        )
        assert features_death[7] == 2  # match_phase_id = 2 (death)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
