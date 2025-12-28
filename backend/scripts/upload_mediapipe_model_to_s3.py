from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Any, cast

import boto3


def main() -> int:
    if len(sys.argv) < 2:
        print(
            "Usage: python -m backend.scripts.upload_mediapipe_model_to_s3 "
            "<path-to-pose_landmarker_full.task>",
            file=sys.stderr,
        )
        return 2

    src_path = Path(sys.argv[1])
    if not src_path.exists() or not src_path.is_file():
        print(f"Model file not found: {src_path}", file=sys.stderr)
        return 2

    bucket = os.getenv("MODEL_S3_BUCKET", "cricksy-coach-videos-prod")
    key = os.getenv("MODEL_S3_KEY", "coach_plus/dev-test/mediapipe/pose_landmarker_full.task")
    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION") or "us-east-1"

    print(f"Uploading MediaPipe model to s3://{bucket}/{key}")
    print(f"Region: {region}")
    print(f"Source: {src_path} ({src_path.stat().st_size} bytes)")

    s3 = cast(Any, boto3.client("s3", region_name=region))  # pyright: ignore[reportUnknownMemberType]
    s3.upload_file(
        Filename=str(src_path),
        Bucket=bucket,
        Key=key,
        ExtraArgs={"ContentType": "application/octet-stream"},
    )

    # Verify it is readable
    s3.head_object(Bucket=bucket, Key=key)
    print("Upload OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
