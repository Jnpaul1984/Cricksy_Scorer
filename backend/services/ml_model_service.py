"""
ML Model Service for Cricket Predictions
=========================================

Handles loading and inference for ML models:
- Win probability prediction (T20/ODI)
- Score prediction (T20/ODI)
"""

import joblib
from pathlib import Path
from typing import Literal
import logging

logger = logging.getLogger(__name__)


class MLModelService:
    """Service for loading and using ML models for cricket predictions."""

    def __init__(self):
        """Initialize the ML model service."""
        self._models = {}
        self._base_path = Path(__file__).parent.parent / "ml_models"

    def load_model(
        self,
        model_type: Literal["win_probability", "score_predictor"],
        match_format: Literal["t20", "odi"],
    ) -> object | None:
        """
        Load a specific ML model.

        Args:
            model_type: Either 'win_probability' or 'score_predictor'
            match_format: Either 't20' or 'odi'

        Returns:
            Loaded model or None if loading fails
        """
        cache_key = f"{model_type}_{match_format}"

        # Return cached model if already loaded
        if cache_key in self._models:
            return self._models[cache_key]

        try:
            if model_type == "win_probability":
                model_path = (
                    self._base_path / "win_probability" / f"{match_format}_win_predictor_v3.pkl"
                )
            else:  # score_predictor
                if match_format == "t20":
                    model_path = self._base_path / "score_predictor" / "t20_score_predictor.pkl"
                else:
                    model_path = self._base_path / "score_predictor" / "odi_score_predictor_v3.pkl"

            if not model_path.exists():
                logger.warning(f"Model not found: {model_path}")
                return None

            logger.info(f"Loading ML model: {model_path.name}")
            model = joblib.load(model_path)
            self._models[cache_key] = model

            return model

        except Exception as e:
            logger.error(f"Error loading {model_type} model for {match_format}: {e}")
            return None

    def predict_win_probability(
        self, match_format: Literal["t20", "odi"], features: dict | object
    ) -> float | None:
        """
        Predict win probability using ML model.

        Args:
            match_format: 't20' or 'odi'
            features: Dictionary with required features OR numpy array of shape (12,)

        Returns:
            Win probability (0-1) or None if prediction fails
        """
        model = self.load_model("win_probability", match_format)
        if model is None:
            return None

        try:
            import numpy as np
            import pandas as pd

            # Handle both dict and array inputs
            if isinstance(features, dict):
                # Expected features (12):
                required_features = [
                    "over_progress",
                    "balls_left",
                    "wickets_left",
                    "run_rate",
                    "run_rate_last_3",
                    "acceleration",
                    "dot_ratio_last_6",
                    "boundary_density_last_3",
                    "required_run_rate",
                    "runs_needed",
                    "wickets_per_over",
                    "runs_per_wicket",
                ]

                # Build feature vector
                feature_vector = pd.DataFrame([{k: features.get(k, 0) for k in required_features}])
            else:
                # Assume it's a numpy array
                feature_vector = np.array(features).reshape(1, -1)

            # Predict probability
            prob = model.predict_proba(feature_vector)[0, 1]  # Probability of winning

            return float(prob)

        except Exception as e:
            logger.error(f"Error predicting win probability: {e}")
            return None

    def predict_score(
        self, match_format: Literal["t20", "odi"], features: dict | object
    ) -> float | None:
        """
        Predict final score using ML model.

        Args:
            match_format: 't20' or 'odi'
            features: Dictionary with required features OR numpy array of shape (22,)

        Returns:
            Predicted final score or None if prediction fails
        """
        model = self.load_model("score_predictor", match_format)
        if model is None:
            return None

        try:
            import numpy as np
            import pandas as pd

            # Handle both dict and array inputs
            if isinstance(features, dict):
                # Expected features (22):
                required_features = [
                    "runs",
                    "overs",
                    "wickets",
                    "run_rate",
                    "balls_left",
                    "wickets_left",
                    "last_5_runs",
                    "match_phase_id",
                    "dot_ratio_last_over",
                    "strike_rotation_last_6",
                    "run_rate_last_5",
                    "boundary_ratio",
                    "momentum",
                    "wickets_last_5",
                    "run_rate_variance",
                    "overs_remaining",
                    "wickets_per_over",
                    "runs_per_wicket",
                    "balls_per_wicket",
                    "in_powerplay",
                    "projected_score_simple",
                    "balls_remaining",
                ]

                # Build feature vector
                feature_vector = pd.DataFrame([{k: features.get(k, 0) for k in required_features}])
            else:
                # Assume it's a numpy array
                feature_vector = np.array(features).reshape(1, -1)

            # Predict score
            predicted_score = model.predict(feature_vector)[0]

            return float(predicted_score)

        except Exception as e:
            logger.error(f"Error predicting score: {e}")
            return None


# Global instance
_ml_service = None


def get_ml_service() -> MLModelService:
    """Get the global ML model service instance."""
    global _ml_service
    if _ml_service is None:
        _ml_service = MLModelService()
    return _ml_service
