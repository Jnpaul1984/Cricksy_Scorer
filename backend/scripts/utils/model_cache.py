from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

import boto3
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


DEFAULT_MODEL_S3_BUCKET = "cricksy-coach-videos-prod"
DEFAULT_MODEL_S3_KEY = "mediapipe/pose_landmarker_full.task"
DEFAULT_MODEL_LOCAL_PATH = "/app/mediapipe_models/pose_landmarker_full.task"
DEFAULT_AWS_REGION = "us-east-1"


def ensure_mediapipe_model_present() -> str:
    """Ensure the MediaPipe PoseLandmarker model exists locally.

    Uses a simple local cache:
    - If the file exists and size > 0, returns it.
    - Otherwise downloads from S3 to a temp file and atomically renames.

    Env vars:
      MODEL_S3_BUCKET: S3 bucket (default: cricksy-coach-videos-prod)
      MODEL_S3_KEY: S3 key (default: mediapipe/pose_landmarker_full.task)
      MODEL_LOCAL_PATH: local path (default: /app/mediapipe_models/pose_landmarker_full.task)
      AWS_REGION: AWS region for boto3 client (default: us-east-1)

    Raises:
      RuntimeError: on download errors or invalid configuration.
    """

    bucket = os.getenv("MODEL_S3_BUCKET", DEFAULT_MODEL_S3_BUCKET)
    key = os.getenv("MODEL_S3_KEY", DEFAULT_MODEL_S3_KEY)
    local_path_str = os.getenv("MODEL_LOCAL_PATH", DEFAULT_MODEL_LOCAL_PATH)
    region = os.getenv("AWS_REGION", DEFAULT_AWS_REGION)

    if not bucket or not key:
        raise RuntimeError(
            "Missing model S3 location. Set MODEL_S3_BUCKET and MODEL_S3_KEY (or rely on defaults)."
        )

    local_path = Path(local_path_str)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    try:
        if local_path.exists() and local_path.is_file() and local_path.stat().st_size > 0:
            logger.info(f"Model cache hit: {local_path}")
            return str(local_path)
    except OSError as e:
        raise RuntimeError(f"Failed checking model cache at {local_path}: {e!s}") from e

    logger.info(f"Downloading model from s3://{bucket}/{key} to {local_path}")

    s3 = boto3.client("s3", region_name=region)

    tmp_dir = str(local_path.parent)
    with tempfile.NamedTemporaryFile(
        prefix=local_path.name + ".tmp-",
        dir=tmp_dir,
        delete=False,
    ) as tmp:
        tmp_path = Path(tmp.name)

    try:
        s3.download_file(bucket, key, str(tmp_path))
        size = tmp_path.stat().st_size
        if size <= 0:
            raise RuntimeError(f"Downloaded model is empty: {tmp_path}")

        os.replace(str(tmp_path), str(local_path))
        logger.info(f"Model download complete: {local_path} ({size} bytes)")
        return str(local_path)

    except (ClientError, BotoCoreError, OSError, RuntimeError) as e:
        raise RuntimeError(
            f"Failed to download MediaPipe model from s3://{bucket}/{key} to {local_path}: {e!s}"
        ) from e

    finally:
        try:
            if tmp_path.exists():
                tmp_path.unlink(missing_ok=True)
        except Exception:
            # Best-effort cleanup
            pass
