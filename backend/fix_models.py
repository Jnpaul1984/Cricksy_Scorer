"""
Model Re-export Utility
=======================

This script reloads serialized models with the currently installed
versions of scikit-learn / XGBoost and re-saves them with joblib so they
work with our production environment.

Run this script on the machine where you originally trained the models,
or reproduce the original environment (matching library versions).

Usage:
    python fix_models.py
"""

from __future__ import annotations

import pickle
from dataclasses import dataclass
from pathlib import Path

import joblib

BANNER = "=" * 60


@dataclass(frozen=True)
class ModelSpec:
    """Specification describing a model file that needs re-export."""

    name: str
    path: Path
    temp_path: Path


def fix_model(old_path: Path, new_path: Path, model_name: str) -> bool:
    """
    Attempt to load and re-save a model with current library versions.

    Args:
        old_path: Path to the problematic model.
        new_path: Temporary output path for the re-saved model.
        model_name: Descriptive name for logging.
    """

    print(f"\n{BANNER}")
    print(f"Fixing: {model_name}")
    print(BANNER)

    if not old_path.exists():
        print(f"[!] Model file not found: {old_path}")
        return False

    try:
        print(f"[.] Loading model from: {old_path}")
        with open(old_path, "rb") as fh:
            model = pickle.load(fh)

        print("[+] Model loaded successfully!")
        print(f"    Type: {type(model).__name__}")

        if hasattr(model, "predict"):
            print("    - Has predict method")
        if hasattr(model, "predict_proba"):
            print("    - Has predict_proba method")
        if hasattr(model, "feature_names_in_"):
            num_features = len(model.feature_names_in_)  # type: ignore[attr-defined]
            print(f"    - Features: {num_features} columns")

        print(f"[.] Re-saving model to: {new_path}")
        joblib.dump(model, new_path, compress=3)

        print("[.] Verifying re-saved model...")
        joblib.load(new_path)
        print("[+] Verification successful!")

        backup_path = old_path.with_suffix(".pkl.backup")
        old_path.rename(backup_path)
        print(f"[.] Original backed up to: {backup_path.name}")

        new_path.rename(old_path)
        print(f"[+] Fixed model saved to: {old_path.name}")
        return True
    except Exception as exc:  # pylint: disable=broad-except
        print(f"[!] Error: {exc}")
        print("\nManual re-export required:")
        print("    1. Load the model in the original training environment.")
        print("    2. Call joblib.dump(model, 'model_name.pkl', compress=3).")
        print("    3. Replace the file in backend/ml_models/.")
        return False


def main() -> None:
    """Main function to fix problematic models."""
    base_path = Path(__file__).parent / "ml_models"

    print(BANNER)
    print("MODEL FIX UTILITY")
    print(BANNER)
    print("Current library versions:")

    try:
        import sklearn  # local import to avoid hard dependency at module load

        print(f"  scikit-learn: {sklearn.__version__}")  # type: ignore[attr-defined]
    except ImportError:
        print("  scikit-learn: Not installed")

    try:
        import xgboost  # local import to avoid hard dependency at module load

        print(f"  xgboost: {xgboost.__version__}")  # type: ignore[attr-defined]
    except ImportError:
        print("  xgboost: Not installed")

    models_to_fix: list[ModelSpec] = [
        ModelSpec(
            name="T20 Win Predictor",
            path=base_path / "win_probability" / "t20_win_predictor_v2.pkl",
            temp_path=base_path / "win_probability" / "t20_win_predictor_v2_fixed.pkl",
        ),
        ModelSpec(
            name="ODI Score Predictor",
            path=base_path / "score_predictor" / "odi_score_predictor_v2.pkl",
            temp_path=base_path / "score_predictor" / "odi_score_predictor_v2_fixed.pkl",
        ),
    ]

    results: list[tuple[str, bool]] = []
    for spec in models_to_fix:
        success = fix_model(spec.path, spec.temp_path, spec.name)
        results.append((spec.name, success))

    print(f"\n{BANNER}")
    print("SUMMARY")
    print(BANNER)
    for name, success in results:
        status = "[+] FIXED" if success else "[!] NEEDS MANUAL FIX"
        print(f"{status}: {name}")

    if all(success for _, success in results):
        print("\nAll models fixed successfully!")
    else:
        print("\nSome models need manual re-export from the training environment.")
        print("If you cannot access that environment, consider retraining the models.")

    print(f"{BANNER}\n")


if __name__ == "__main__":
    main()
