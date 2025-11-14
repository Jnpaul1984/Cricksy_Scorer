"""
Train Win Probability Models for T20 and ODI Cricket Matches
=============================================================

This script processes historical match snapshots and trains XGBoost models
to predict win probabilities based on match state.
"""

from pathlib import Path
from typing import Literal

import joblib
import pandas as pd
import xgboost as xgb
from sklearn.metrics import accuracy_score, classification_report, roc_auc_score
from sklearn.model_selection import train_test_split


def load_match_data(match_format: Literal["t20", "odi"]) -> pd.DataFrame:
    """
    Load all CSV files for a specific match format.

    Args:
        match_format: Either 't20' or 'odi'

    Returns:
        DataFrame with all match data
    """
    print(f"\n{'='*60}")
    print(f"Loading {match_format.upper()} match data...")
    print(f"{'='*60}")

    snapshots_dir = Path(__file__).parent / "snapshots" / match_format
    csv_files = list(snapshots_dir.glob("*.csv"))

    print(f"Found {len(csv_files)} match files")

    if len(csv_files) == 0:
        raise ValueError(f"No CSV files found in {snapshots_dir}")

    # Load all files
    dfs = []
    for i, file in enumerate(csv_files):
        try:
            df = pd.read_csv(file)
            df["match_id"] = file.stem  # Use filename as match ID
            dfs.append(df)

            if (i + 1) % 500 == 0:
                print(f"  Loaded {i + 1}/{len(csv_files)} files...")
        except Exception as e:
            print(f"  ⚠️  Error loading {file.name}: {e}")

    combined_df = pd.concat(dfs, ignore_index=True)
    print(f"\n✓ Loaded {len(combined_df):,} total match states from {len(dfs)} matches")
    print(f"  Columns: {list(combined_df.columns)}")

    return combined_df


def engineer_features(df: pd.DataFrame, match_format: str) -> pd.DataFrame:
    """
    Create features for win probability prediction.

    Features needed for ODI win predictor (from your model):
    - over_progress
    - balls_left
    - wickets_left
    - run_rate
    - run_rate_last_3
    - acceleration
    - dot_ratio_last_6
    - boundary_density_last_3
    - required_run_rate
    - runs_needed
    - + 2 more
    """
    print(f"\nEngineering features for {match_format.upper()}...")

    df = df.copy()

    # Basic features
    total_overs = 20 if match_format == "t20" else 50

    df["over_progress"] = df["completed_overs"] / total_overs
    df["balls_left"] = df["balls_remaining"]
    df["wickets_left"] = 10 - df["wickets"]
    df["run_rate"] = df["total_runs"] / df["completed_overs"].replace(0, 0.1)

    # Group by match to calculate rolling features
    def calc_rolling_features(group):
        # Run rate last 3 overs
        group["run_rate_last_3"] = (
            group["total_runs"].diff(periods=min(3, len(group))).fillna(0) / 3
        )

        # Acceleration (difference between current RR and last 3 overs RR)
        group["acceleration"] = group["run_rate"] - group["run_rate_last_3"]

        # Dots and boundaries (simplified - using run patterns)
        group["dot_ratio_last_6"] = (
            (group["total_runs"].diff().fillna(0) == 0).rolling(6, min_periods=1).mean()
        )
        group["boundary_density_last_3"] = (
            (group["total_runs"].diff().fillna(0) >= 4).rolling(3, min_periods=1).mean()
        )

        return group

    df = df.groupby("match_id", group_keys=False).apply(calc_rolling_features)

    # Target-based features
    df["runs_needed"] = df["final_score"] - df["total_runs"]
    df["required_run_rate"] = df["runs_needed"] / (df["balls_remaining"] / 6).replace(0, 0.1)

    # Additional features
    df["wickets_per_over"] = df["wickets"] / df["completed_overs"].replace(0, 0.1)
    df["runs_per_wicket"] = df["total_runs"] / df["wickets"].replace(0, 1)

    # Fill any remaining NaNs
    df = df.fillna(0)

    print("✓ Feature engineering complete")
    print(f"  Total features: {df.shape[1]}")

    return df


def create_target_variable(df: pd.DataFrame) -> pd.DataFrame:
    """
    Create binary target: did the batting team reach/exceed the final score?

    For training, we'll use:
    - 1 if current trajectory suggests they'll win (runs >= final_score at end)
    - 0 if they'll lose

    Simplified: use actual final score vs par score logic
    """
    df = df.copy()

    # Calculate if team is "winning" at this point
    # Winning = on pace to beat final score
    df["target"] = (
        df["total_runs"]
        / df["completed_overs"].replace(0, 0.1)
        * (df["completed_overs"] + df["balls_remaining"] / 6)
        > df["final_score"]
    ).astype(int)

    return df


def train_win_predictor(match_format: Literal["t20", "odi"]) -> None:
    """Train and save win probability predictor for specified format."""

    print(f"\n{'='*70}")
    print(f"TRAINING {match_format.upper()} WIN PROBABILITY PREDICTOR")
    print(f"{'='*70}")

    # Load data
    df = load_match_data(match_format)

    # Engineer features
    df = engineer_features(df, match_format)

    # Create target
    df = create_target_variable(df)

    # Select features (matching your model's expected features)
    feature_cols = [
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

    X = df[feature_cols]
    y = df["target"]

    print(f"\nDataset shape: {X.shape}")
    loss_count = (y == 0).sum()
    loss_pct = (y == 0).mean() * 100
    win_count = (y == 1).sum()
    win_pct = (y == 1).mean() * 100
    print(
        "Target distribution:"
        f"\n  Loss (0): {loss_count:,} ({loss_pct:.1f}%)"
        f"\n  Win (1): {win_count:,} ({win_pct:.1f}%)"
    )

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    print(f"\nTraining set: {X_train.shape[0]:,} samples")
    print(f"Test set: {X_test.shape[0]:,} samples")

    # Train XGBoost model
    print("\nTraining XGBoost Classifier...")

    model = xgb.XGBClassifier(
        n_estimators=800,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="logloss",
        early_stopping_rounds=50,
    )

    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    # Evaluate
    print(f"\n{'='*60}")
    print("MODEL EVALUATION")
    print(f"{'='*60}")

    y_pred = model.predict(X_test)
    y_pred_proba = model.predict_proba(X_test)[:, 1]

    accuracy = accuracy_score(y_test, y_pred)
    roc_auc = roc_auc_score(y_test, y_pred_proba)

    print(f"\nAccuracy: {accuracy:.4f}")
    print(f"ROC AUC: {roc_auc:.4f}")
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=["Loss", "Win"]))

    # Feature importance
    print("\nTop 10 Feature Importances:")
    feature_importance = pd.DataFrame(
        {"feature": feature_cols, "importance": model.feature_importances_}
    ).sort_values("importance", ascending=False)

    for _, row in feature_importance.head(10).iterrows():
        print(f"  {row['feature']:.<30} {row['importance']:.4f}")

    # Save model
    output_dir = Path(__file__).parent / "ml_models" / "win_probability"
    output_path = output_dir / f"{match_format}_win_predictor_v3.pkl"

    print(f"\n{'='*60}")
    print(f"Saving model to: {output_path}")
    joblib.dump(model, output_path, compress=3)
    print("✓ Model saved successfully!")

    # Save metadata
    metadata = {
        "model_type": "XGBClassifier",
        "match_format": match_format,
        "n_estimators": 800,
        "features": feature_cols,
        "training_samples": len(X_train),
        "test_accuracy": float(accuracy),
        "test_roc_auc": float(roc_auc),
        "trained_date": pd.Timestamp.now().isoformat(),
    }

    import json

    metadata_path = output_dir / f"{match_format}_win_predictor_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✓ Metadata saved to: {metadata_path}")
    print(f"{'='*60}\n")


def main():
    """Train both T20 and ODI win predictors."""
    print("=" * 70)
    print("CRICKET WIN PROBABILITY MODEL TRAINER")
    print("=" * 70)

    for match_format in ["t20", "odi"]:
        try:
            train_win_predictor(match_format)
        except Exception as e:
            print(f"\n❌ Error training {match_format.upper()} model: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 70)
    print("TRAINING COMPLETE!")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Run analyze_models.py to verify the new models")
    print("2. Integrate with the prediction service")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
