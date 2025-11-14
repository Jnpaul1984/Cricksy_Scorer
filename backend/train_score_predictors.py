"""
Train Score Prediction Models for T20 and ODI Cricket Matches
==============================================================

This script processes historical match snapshots and trains XGBoost models
to predict final scores based on current match state.
"""

import pandas as pd
import numpy as np
from pathlib import Path
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
import xgboost as xgb
import joblib
from typing import Literal


def load_match_data(match_format: Literal["t20", "odi"]) -> pd.DataFrame:
    """Load all CSV files for a specific match format."""
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
            df["match_id"] = file.stem
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
    Create features for score prediction.

    Features needed (from T20 score predictor):
    - runs, overs, wickets, run_rate, balls_left, wickets_left
    - last_5_runs, match_phase_id, dot_ratio_last_over, strike_rotation_last_6
    - etc.
    """
    print(f"\nEngineering features for {match_format.upper()}...")

    df = df.copy()

    # Basic features
    total_overs = 20 if match_format == "t20" else 50
    total_balls = total_overs * 6

    df["runs"] = df["total_runs"]
    df["overs"] = df["completed_overs"]
    df["wickets"] = df["wickets"]
    df["run_rate"] = df["total_runs"] / df["completed_overs"].replace(0, 0.1)
    df["balls_left"] = df["balls_remaining"]
    df["wickets_left"] = 10 - df["wickets"]

    # Match phase (early/middle/death)
    if match_format == "t20":
        df["match_phase_id"] = (
            pd.cut(
                df["completed_overs"],
                bins=[0, 6, 15, 20],
                labels=[0, 1, 2],
                include_lowest=True,
            )
            .cat.codes.fillna(0)
            .astype(int)
        )
    else:  # ODI
        df["match_phase_id"] = (
            pd.cut(
                df["completed_overs"],
                bins=[0, 10, 40, 50],
                labels=[0, 1, 2],
                include_lowest=True,
            )
            .cat.codes.fillna(0)
            .astype(int)
        )

    # Group by match to calculate rolling features
    def calc_rolling_features(group):
        # Last 5 runs
        group["last_5_runs"] = (
            group["total_runs"].diff(periods=min(5, len(group))).fillna(0)
        )

        # Dot ratio last over (simplified)
        group["dot_ratio_last_over"] = (
            (group["total_runs"].diff().fillna(0) == 0).rolling(6, min_periods=1).mean()
        )

        # Strike rotation (runs scored in singles/twos)
        group["strike_rotation_last_6"] = (
            group["total_runs"]
            .diff()
            .fillna(0)
            .rolling(6, min_periods=1)
            .apply(lambda x: (x[x.between(1, 2)].sum() / x.sum() if x.sum() > 0 else 0))
        )

        # Run rate last 5 overs
        group["run_rate_last_5"] = (
            group["total_runs"].diff(periods=min(5, len(group))).fillna(0) / 5
        )

        # Boundaries ratio
        group["boundary_ratio"] = (
            (group["total_runs"].diff().fillna(0) >= 4)
            .rolling(10, min_periods=1)
            .mean()
        )

        # Momentum (acceleration)
        group["momentum"] = (
            group["run_rate"].diff().fillna(0).rolling(3, min_periods=1).mean()
        )

        # Wickets fallen recently
        group["wickets_last_5"] = (
            group["wickets"].diff(periods=min(5, len(group))).fillna(0)
        )

        # Run rate variance (consistency)
        group["run_rate_variance"] = (
            group["run_rate"].rolling(5, min_periods=1).std().fillna(0)
        )

        return group

    df = df.groupby("match_id", group_keys=False).apply(calc_rolling_features)

    # Additional context features
    df["overs_remaining"] = df["balls_remaining"] / 6
    df["wickets_per_over"] = df["wickets"] / df["completed_overs"].replace(0, 0.1)
    df["runs_per_wicket"] = df["total_runs"] / df["wickets"].replace(0, 1)
    df["balls_per_wicket"] = (df["completed_overs"] * 6) / df["wickets"].replace(0, 1)

    # Powerplay flag
    df["in_powerplay"] = df["is_powerplay"]

    # Projected score based on current RR
    df["projected_score_simple"] = df["total_runs"] + (
        df["run_rate"] * df["overs_remaining"]
    )

    # Fill any remaining NaNs
    df = df.fillna(0)

    print(f"✓ Feature engineering complete")
    print(f"  Total features: {df.shape[1]}")

    return df


def train_score_predictor(match_format: Literal["t20", "odi"]) -> None:
    """Train and save score predictor for specified format."""

    print(f"\n{'='*70}")
    print(f"TRAINING {match_format.upper()} SCORE PREDICTOR")
    print(f"{'='*70}")

    # Load data
    df = load_match_data(match_format)

    # Engineer features
    df = engineer_features(df, match_format)

    # Target is the final score
    y = df["final_score"]

    # Select features (22 features like T20 score predictor)
    feature_cols = [
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

    X = df[feature_cols]

    print(f"\nDataset shape: {X.shape}")
    print(f"Target statistics:")
    print(f"  Mean final score: {y.mean():.1f}")
    print(f"  Std: {y.std():.1f}")
    print(f"  Min: {y.min()}, Max: {y.max()}")

    # Split data
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    print(f"\nTraining set: {X_train.shape[0]:,} samples")
    print(f"Test set: {X_test.shape[0]:,} samples")

    # Train XGBoost model
    print(f"\nTraining XGBoost Regressor...")

    model = xgb.XGBRegressor(
        n_estimators=400,
        max_depth=6,
        learning_rate=0.05,
        subsample=0.8,
        colsample_bytree=0.8,
        random_state=42,
        eval_metric="rmse",
        early_stopping_rounds=50,
    )

    model.fit(X_train, y_train, eval_set=[(X_test, y_test)], verbose=False)

    # Evaluate
    print(f"\n{'='*60}")
    print(f"MODEL EVALUATION")
    print(f"{'='*60}")

    y_pred = model.predict(X_test)

    mae = mean_absolute_error(y_test, y_pred)
    rmse = np.sqrt(mean_squared_error(y_test, y_pred))
    r2 = r2_score(y_test, y_pred)

    print(f"\nMean Absolute Error (MAE): {mae:.2f} runs")
    print(f"Root Mean Squared Error (RMSE): {rmse:.2f} runs")
    print(f"R² Score: {r2:.4f}")

    # Sample predictions
    print(f"\nSample Predictions (first 10):")
    print(f"{'Actual':<10} {'Predicted':<10} {'Error':<10}")
    print("-" * 30)
    for actual, pred in list(zip(y_test, y_pred))[:10]:
        error = abs(actual - pred)
        print(f"{actual:<10.0f} {pred:<10.1f} {error:<10.1f}")

    # Feature importance
    print(f"\nTop 10 Feature Importances:")
    feature_importance = pd.DataFrame(
        {"feature": feature_cols, "importance": model.feature_importances_}
    ).sort_values("importance", ascending=False)

    for idx, row in feature_importance.head(10).iterrows():
        print(f"  {row['feature']:.<30} {row['importance']:.4f}")

    # Save model
    output_dir = Path(__file__).parent / "ml_models" / "score_predictor"
    output_path = output_dir / f"{match_format}_score_predictor_v3.pkl"

    print(f"\n{'='*60}")
    print(f"Saving model to: {output_path}")
    joblib.dump(model, output_path, compress=3)
    print(f"✓ Model saved successfully!")

    # Save metadata
    metadata = {
        "model_type": "XGBRegressor",
        "match_format": match_format,
        "n_estimators": 400,
        "features": feature_cols,
        "training_samples": len(X_train),
        "test_mae": float(mae),
        "test_rmse": float(rmse),
        "test_r2": float(r2),
        "trained_date": pd.Timestamp.now().isoformat(),
    }

    import json

    metadata_path = output_dir / f"{match_format}_score_predictor_metadata.json"
    with open(metadata_path, "w") as f:
        json.dump(metadata, f, indent=2)

    print(f"✓ Metadata saved to: {metadata_path}")
    print(f"{'='*60}\n")


def main():
    """Train ODI score predictor."""
    print("=" * 70)
    print("CRICKET SCORE PREDICTOR TRAINER")
    print("=" * 70)

    for match_format in ["odi"]:  # Only ODI for now
        try:
            train_score_predictor(match_format)
        except Exception as e:
            print(f"\n❌ Error training {match_format.upper()} model: {e}")
            import traceback

            traceback.print_exc()

    print("\n" + "=" * 70)
    print("TRAINING COMPLETE!")
    print("=" * 70)
    print("\nNext steps:")
    print("1. Verify the model with analyze_models.py")
    print("2. Integrate all models into prediction service")
    print("=" * 70 + "\n")


if __name__ == "__main__":
    main()
