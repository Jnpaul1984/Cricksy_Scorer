"""Script to analyze ML models structure and features."""

import pickle
from pathlib import Path


def analyze_model(model_path: str, model_name: str):
    """Analyze a pickled model and print its properties."""
    print(f"\n{'='*60}")
    print(f"Analyzing: {model_name}")
    print(f"{'='*60}")

    try:
        with open(model_path, "rb") as f:
            model = pickle.load(f)

        print("✓ Model loaded successfully")
        print(f"Type: {type(model).__name__}")
        print(f"Module: {type(model).__module__}")

        # Check for common attributes
        if hasattr(model, "predict_proba"):
            print("✓ Has predict_proba method")

        if hasattr(model, "predict"):
            print("✓ Has predict method")

        if hasattr(model, "feature_names_in_"):
            features = model.feature_names_in_
            print(f"\n✓ Features found: {len(features)} features")
            print("First 10 features:")
            for i, feat in enumerate(features[:10], 1):
                print(f"  {i}. {feat}")
            if len(features) > 10:
                print(f"  ... and {len(features) - 10} more")
        else:
            print("⚠ No feature_names_in_ attribute found")

        if hasattr(model, "n_features_in_"):
            print(f"\nNumber of features expected: {model.n_features_in_}")

        # Check for ensemble methods
        if hasattr(model, "n_estimators"):
            print(f"Ensemble model with {model.n_estimators} estimators")

        # Check for XGBoost specific
        if hasattr(model, "get_booster"):
            print("✓ XGBoost model detected")

    except Exception as e:
        print(f"✗ Error loading model: {e}")


if __name__ == "__main__":
    base_path = Path(__file__).parent / "ml_models"

    print("=" * 60)
    print("ML MODELS ANALYSIS")
    print("=" * 60)

    # Win probability models
    models = {
        "T20 Win Predictor": base_path / "win_probability" / "t20_win_predictor_v2.pkl",
        "ODI Win Predictor": base_path / "win_probability" / "odi_win_predictor.pkl",
        "T20 Score Predictor": base_path / "score_predictor" / "t20_score_predictor.pkl",
        "ODI Score Predictor": base_path / "score_predictor" / "odi_score_predictor_v2.pkl",
    }

    for name, path in models.items():
        if path.exists():
            analyze_model(str(path), name)
        else:
            print(f"\n⚠ Model not found: {path}")

    print(f"\n{'='*60}")
    print("Analysis complete!")
    print(f"{'='*60}\n")
