"""
Model Re-export Utility
=======================
This script helps re-export models that have version compatibility issues.

Run this script on the machine where you originally trained the models,
or provide the original training environment.

Usage:
    python fix_models.py
"""

import pickle
from pathlib import Path

import joblib


def fix_model(old_path: Path, new_path: Path, model_name: str):
    """
    Attempt to load and re-save a model with current library versions.

    Args:
        old_path: Path to the problematic model
        new_path: Path where to save the fixed model
        model_name: Descriptive name for logging
    """
    print(f"\n{'='*60}")
    print(f"Fixing: {model_name}")
    print(f"{'='*60}")

    if not old_path.exists():
        print(f"❌ Model file not found: {old_path}")
        return False

    try:
        # Try loading with pickle first
        print(f"📂 Loading model from: {old_path}")
        with open(old_path, "rb") as f:
            model = pickle.load(f)

        print("✅ Model loaded successfully!")
        print(f"   Type: {type(model).__name__}")

        # Check if it has the expected methods
        if hasattr(model, "predict"):
            print("   ✓ Has predict method")
        if hasattr(model, "predict_proba"):
            print("   ✓ Has predict_proba method")

        # Show features if available
        if hasattr(model, "feature_names_in_"):
            print(f"   ✓ Features: {len(model.feature_names_in_)} features")

        # Re-save using joblib (recommended for sklearn/xgboost)
        print(f"\n💾 Re-saving model to: {new_path}")
        joblib.dump(model, new_path, compress=3)

        # Verify the new file
        print("🔍 Verifying re-saved model...")
        joblib.load(new_path)
        print("✅ Verification successful!")

        # Backup the old file
        backup_path = old_path.with_suffix(".pkl.backup")
        old_path.rename(backup_path)
        print(f"📦 Original backed up to: {backup_path.name}")

        # Move new file to original location
        new_path.rename(old_path)
        print(f"✅ Fixed model saved to: {old_path.name}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        print("\n⚠️  This model needs to be re-exported from the original training environment.")
        print("    If you have access to the training code, please:")
        print("    1. Load the model in the original environment")
        print("    2. Use joblib.dump(model, 'model_name.pkl', compress=3)")
        print("    3. Replace the file in ml_models/")
        return False


def main():
    """Main function to fix problematic models."""
    base_path = Path(__file__).parent / "ml_models"

    print("=" * 60)
    print("MODEL FIX UTILITY")
    print("=" * 60)
    print("Current library versions:")
    try:
        import sklearn

        print(f"  scikit-learn: {sklearn.__version__}")
    except ImportError:
        print("  scikit-learn: Not installed")

    try:
        import xgboost

        print(f"  xgboost: {xgboost.__version__}")
    except ImportError:
        print("  xgboost: Not installed")

    # Models to fix
    models_to_fix = [
        {
            "name": "T20 Win Predictor",
            "path": base_path / "win_probability" / "t20_win_predictor_v2.pkl",
            "temp_path": base_path / "win_probability" / "t20_win_predictor_v2_fixed.pkl",
        },
        {
            "name": "ODI Score Predictor",
            "path": base_path / "score_predictor" / "odi_score_predictor_v2.pkl",
            "temp_path": base_path / "score_predictor" / "odi_score_predictor_v2_fixed.pkl",
        },
    ]

    results = []
    for model_info in models_to_fix:
        success = fix_model(model_info["path"], model_info["temp_path"], model_info["name"])
        results.append((model_info["name"], success))

    # Summary
    print(f"\n{'='*60}")
    print("SUMMARY")
    print(f"{'='*60}")
    for name, success in results:
        status = "✅ FIXED" if success else "❌ NEEDS MANUAL FIX"
        print(f"{status}: {name}")

    all_fixed = all(success for _, success in results)
    if all_fixed:
        print("\n🎉 All models fixed successfully!")
    else:
        print("\n⚠️  Some models need manual re-export from training environment")
        print("\nAlternative: If you can't access the training environment,")
        print("consider retraining the models or using the working models only.")

    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()
