"""
S3 Model Upload Utilities for Training Pipeline
================================================

Handles uploading trained models to S3 with versioning and metadata.
"""

import json
import logging
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Literal

logger = logging.getLogger(__name__)


def upload_model_to_s3(
    model_path: Path,
    model_type: Literal["win_probability", "score_predictor"],
    match_format: Literal["t20", "odi"],
    metrics: dict[str, Any] | None = None,
    feature_names: list[str] | None = None,
) -> bool:
    """
    Upload trained model to S3 with versioning.

    Creates the following structure in S3:
    - models/{model_name}/v1/ (model.pkl, metrics.json, schema.json)
    - models/{model_name}/v2/ (...)
    - models/{model_name}/latest.json (points to current version)

    Args:
        model_path: Path to .pkl file
        model_type: "win_probability" or "score_predictor"
        match_format: "t20" or "odi"
        metrics: Training metrics (accuracy, MAE, etc.)
        feature_names: List of feature names expected by model

    Returns:
        True if upload successful, False otherwise
    """
    # Check if S3 is configured
    s3_bucket = os.getenv("S3_MODEL_BUCKET", "")
    if not s3_bucket:
        logger.warning("S3_MODEL_BUCKET not set, skipping S3 upload")
        return False

    if not model_path.exists():
        logger.error("Model file not found: %s", model_path)
        return False

    try:
        import boto3

        s3 = boto3.client("s3")

        # Generate model name and version
        model_name = _get_model_name(model_type, match_format)
        version = _get_next_version(s3, s3_bucket, model_name)

        logger.info("Uploading %s version %s to S3...", model_name, version)

        # Upload model file
        s3_prefix = f"models/{model_name}/{version}"
        model_key = f"{s3_prefix}/model.pkl"
        s3.upload_file(str(model_path), s3_bucket, model_key)
        logger.info("  OK Uploaded model.pkl")

        # Upload metrics
        if metrics:
            metrics_key = f"{s3_prefix}/metrics.json"
            metrics_json = json.dumps(metrics, indent=2)
            s3.put_object(Bucket=s3_bucket, Key=metrics_key, Body=metrics_json)
            logger.info("  OK Uploaded metrics.json")

        # Upload schema
        if feature_names:
            schema = {
                "feature_names": feature_names,
                "n_features": len(feature_names),
                "model_type": model_type,
                "match_format": match_format,
            }
            schema_key = f"{s3_prefix}/schema.json"
            schema_json = json.dumps(schema, indent=2)
            s3.put_object(Bucket=s3_bucket, Key=schema_key, Body=schema_json)
            logger.info("  OK Uploaded schema.json")

        # Update latest.json pointer
        latest_metadata = {
            "version": version,
            "updated_at": datetime.now(UTC).isoformat(),
            "s3_prefix": s3_prefix,
            "model_name": model_name,
            "metrics": metrics or {},
        }
        latest_key = f"models/{model_name}/latest.json"
        latest_json = json.dumps(latest_metadata, indent=2)
        s3.put_object(Bucket=s3_bucket, Key=latest_key, Body=latest_json)
        logger.info("  OK Updated latest.json -> %s", version)

        logger.info("Successfully uploaded %s to s3://%s/%s", model_name, s3_bucket, s3_prefix)
        return True

    except Exception as e:
        logger.error("Failed to upload model to S3: %s", e)
        return False


def _get_model_name(
    model_type: Literal["win_probability", "score_predictor"],
    match_format: Literal["t20", "odi"],
) -> str:
    """Generate model name for S3 paths."""
    if model_type == "win_probability":
        return f"{match_format}_win_predictor"
    return f"{match_format}_score_predictor"


def _get_next_version(s3_client, bucket: str, model_name: str) -> str:
    """
    Determine next version number for model.

    Scans S3 for existing versions (v1, v2, v3, ...) and returns next number.

    Returns:
        Version string like "v1", "v2", etc.
    """
    try:
        prefix = f"models/{model_name}/"
        response = s3_client.list_objects_v2(Bucket=bucket, Prefix=prefix, Delimiter="/")

        # Extract version numbers from common prefixes
        versions = []
        if "CommonPrefixes" in response:
            for obj in response["CommonPrefixes"]:
                prefix_path = obj["Prefix"]
                # Extract version from path like "models/t20_win_predictor/v3/"
                parts = prefix_path.rstrip("/").split("/")
                if len(parts) >= 3 and parts[-1].startswith("v"):
                    try:
                        version_num = int(parts[-1][1:])  # Strip "v" prefix
                        versions.append(version_num)
                    except ValueError:
                        continue

        # Return next version
        next_version = max(versions, default=0) + 1
        return f"v{next_version}"

    except Exception as e:
        logger.warning("Error determining next version, defaulting to v1: %s", e)
        return "v1"


def upload_training_snapshots_to_s3(snapshots_dir: Path, match_format: str) -> bool:
    """
    Upload training data snapshots to S3 for archival/audit.

    Args:
        snapshots_dir: Directory containing CSV files
        match_format: "t20" or "odi"

    Returns:
        True if successful
    """
    s3_bucket = os.getenv("S3_MODEL_BUCKET", "")
    if not s3_bucket:
        return False

    try:
        import boto3

        s3 = boto3.client("s3")

        # Upload all CSV files
        csv_files = list(snapshots_dir.glob("*.csv"))
        if not csv_files:
            logger.warning("No CSV files found in %s", snapshots_dir)
            return False

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        s3_prefix = f"snapshots/{match_format}/{timestamp}"

        logger.info("Uploading %d snapshots to s3://%s/%s", len(csv_files), s3_bucket, s3_prefix)

        for csv_file in csv_files:
            s3_key = f"{s3_prefix}/{csv_file.name}"
            s3.upload_file(str(csv_file), s3_bucket, s3_key)

        logger.info("Successfully uploaded training snapshots")
        return True

    except Exception as e:
        logger.error("Failed to upload snapshots: %s", e)
        return False
