"""Model re-export helper for refreshing serialized ML models."""

import pickle  # nosec
from pathlib import Path

import joblib


def fix_model(old_path: Path, new_path: Path, model_name: str) -> bool:
    """Load an existing model and re-save it with current dependencies."""
    print("=" * 60)
    print(f"Fixing: {model_name}")
    print("=" * 60)

    if not old_path.exists():
        print(f"ERROR: Model file not found: {old_path}")
        return False

    try:
        print(f"Loading model from {old_path}")
        with open(old_path, "rb") as handle:
            model = pickle.load(handle)  # nosec

        print("Model loaded successfully")
        print(f"   Type: {type(model).__name__}")

        if hasattr(model, "predict"):
            print("   - Has predict method")
        if hasattr(model, "predict_proba"):
            print("   - Has predict_proba method")
        if hasattr(model, "feature_names_in_"):
            print(f"   - Feature count: {len(model.feature_names_in_)}")

        print(f"\nRe-saving model to {new_path}")
        joblib.dump(model, new_path, compress=3)

        print("Verifying re-saved model...")
        joblib.load(new_path)
        print("Verification successful")

        backup_path = old_path.with_suffix(".pkl.backup")
        old_path.rename(backup_path)
        print(f"Original backed up to {backup_path.name}")

        new_path.rename(old_path)
        print(f"Fixed model written to {old_path.name}")
        return True

    except Exception as exc:
        print(f"ERROR: {exc}")
        print(
            "\nAction required: re-export the model inside the original training environment."
        )
        print("If you have access to the training code:")
        print("    1. Load the model in the original environment")
        print("    2. Run joblib.dump(model, 'model_name.pkl', compress=3)")
        print("    3. Replace the file inside backend/ml_models/")
        return False


def main() -> None:
    """CLI entrypoint for refreshing all known models."""
    base_path = Path(__file__).parent / "ml_models"

    print("=" * 60)
    print("MODEL FIX UTILITY")
    print("=" * 60)
    print("Current library versions:")

    try:
        import sklearn  # type: ignore[import-not-found]

        print(f"  scikit-learn: {sklearn.__version__}")
    except ImportError:
        print("  scikit-learn: Not installed")

    try:
        import xgboost  # type: ignore[import-not-found]

        print(f"  xgboost: {xgboost.__version__}")
    except ImportError:
        print("  xgboost: Not installed")

    models_to_fix: list[tuple[str, Path, Path]] = [
        (
            "T20 Win Predictor",
            base_path / "win_probability" / "t20_win_predictor_v2.pkl",
            base_path / "win_probability" / "t20_win_predictor_v2_fixed.pkl",
        ),
        (
            "ODI Score Predictor",
            base_path / "score_predictor" / "odi_score_predictor_v2.pkl",
            base_path / "score_predictor" / "odi_score_predictor_v2_fixed.pkl",
        ),
    ]

    results: list[tuple[str, bool]] = []
    for name, path, temp_path in models_to_fix:
        success = fix_model(path, temp_path, name)
        results.append((name, success))

    print("\nSUMMARY")
    print("=" * 60)
    for name, success in results:
        status = "OK" if success else "NEEDS ATTENTION"
        print(f"{status:<17} - {name}")

    if all(flag for _, flag in results):
        print("\nAll models refreshed successfully.")
    else:
        print("\nSome models still need manual exports.")
        print("Refer to the instructions above for the remaining files.")
    print("=" * 60)


if __name__ == "__main__":
    main()
