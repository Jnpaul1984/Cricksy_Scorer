"""
ML Model Service for Cricket Predictions
=========================================

Handles loading and inference for ML models:
- Win probability prediction (T20/ODI)
- Score prediction (T20/ODI)
"""

import logging
from pathlib import Path
from typing import Any, Literal, Protocol

import joblib
import numpy as np

logger = logging.getLogger(__name__)


class MLModel(Protocol):
    """Protocol for ML models with predict and predict_proba methods."""

    def predict(self, X: Any) -> Any:
        """Predict method for regression models."""
        ...

    def predict_proba(self, X: Any) -> Any:
        """Predict probability method for classification models."""
        ...


class MLModelService:
    """Service for loading and using ML models for cricket predictions."""

    def __init__(self):
        """Initialize the ML model service."""
        self._models: dict[str, MLModel] = {}
        self._base_path = Path(__file__).parent.parent / "ml_models"

    def load_model(
        self,
        model_type: Literal["win_probability", "score_predictor"],
        match_format: Literal["t20", "odi"],
    ) -> MLModel | None:
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

        model_path = self._resolve_model_path(model_type, match_format)
        model = self._load_model_from_disk(model_path)
        if model is None:
            model = self._build_fallback_model(model_type, match_format)
            logger.warning(
                "Falling back to heuristic %s model for %s format",
                model_type,
                match_format,
            )

        self._models[cache_key] = model
        return model

    def _resolve_model_path(
        self,
        model_type: Literal["win_probability", "score_predictor"],
        match_format: Literal["t20", "odi"],
    ) -> Path:
        if model_type == "win_probability":
            return (
                self._base_path
                / "win_probability"
                / f"{match_format}_win_predictor_v3.pkl"
            )
        if match_format == "t20":
            return self._base_path / "score_predictor" / "t20_score_predictor.pkl"
        return self._base_path / "score_predictor" / "odi_score_predictor_v3.pkl"

    def _load_model_from_disk(self, path: Path) -> MLModel | None:
        if not path.exists():
            logger.warning("Model not found: %s", path)
            return None
        try:
            logger.info("Loading ML model: %s", path.name)
            return joblib.load(path)
        except Exception as exc:
            logger.error("Error loading ML model %s: %s", path, exc)
            return None

    def _build_fallback_model(
        self,
        model_type: Literal["win_probability", "score_predictor"],
        match_format: Literal["t20", "odi"],
    ) -> MLModel:
        if model_type == "win_probability":
            return _FallbackWinProbabilityModel(match_format)
        return _FallbackScorePredictorModel(match_format)

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
                feature_vector = pd.DataFrame(
                    [{k: features.get(k, 0) for k in required_features}]
                )
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
                feature_vector = pd.DataFrame(
                    [{k: features.get(k, 0) for k in required_features}]
                )
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


class _FallbackWinProbabilityModel:
    """Lightweight logistic fallback when trained model files are unavailable."""

    def __init__(self, match_format: Literal["t20", "odi"]):
        self.match_format = match_format

    def predict_proba(self, X: Any) -> np.ndarray:
        arr = self._ensure_array(X)
        # Simple heuristic: compare current vs required run rate + wickets remaining.
        run_rate = arr[:, 3] if arr.shape[1] > 3 else np.zeros(arr.shape[0])
        required = arr[:, 8] if arr.shape[1] > 8 else np.zeros(arr.shape[0])
        wickets_left = arr[:, 2] if arr.shape[1] > 2 else np.full(arr.shape[0], 10.0)
        imbalance = (run_rate - required) + (wickets_left - 5) * 0.5
        if self.match_format == "odi":
            imbalance *= 0.8  # ODI games tolerate slower scoring
        probs = 1 / (1 + np.exp(-imbalance / 4))
        probs = np.clip(probs, 0.01, 0.99)
        return np.column_stack([1 - probs, probs])

    def predict(self, X: Any) -> np.ndarray:
        return (self.predict_proba(X)[:, 1] >= 0.5).astype(int)

    @staticmethod
    def _ensure_array(X: Any) -> np.ndarray:
        arr = np.asarray(X, dtype=float)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)
        return arr


class _FallbackScorePredictorModel:
    """Deterministic linear fallback for score prediction."""

    def __init__(self, match_format: Literal["t20", "odi"]):
        self.overs_limit = 20 if match_format == "t20" else 50

    def predict(self, X: Any) -> np.ndarray:
        arr = np.asarray(X, dtype=float)
        if arr.ndim == 1:
            arr = arr.reshape(1, -1)

        runs = arr[:, 0] if arr.shape[1] > 0 else np.zeros(arr.shape[0])
        overs = arr[:, 1] if arr.shape[1] > 1 else np.zeros(arr.shape[0])
        run_rate = arr[:, 3] if arr.shape[1] > 3 else np.zeros(arr.shape[0])
        overs_completed = np.clip(overs, 1, self.overs_limit)
        remaining_overs = np.maximum(self.overs_limit - overs_completed, 0.1)
        projected = runs + run_rate * remaining_overs
        return np.maximum(projected, runs + 5)

    def predict_proba(self, X: Any) -> np.ndarray:
        # Not used but provided for protocol compatibility.
        pred = self.predict(X)
        scaled = np.clip(pred / (self.overs_limit * 10), 0, 1)
        return np.column_stack([1 - scaled, scaled])
