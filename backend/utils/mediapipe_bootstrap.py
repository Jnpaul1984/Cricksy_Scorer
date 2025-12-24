import os
import pathlib
import boto3


def ensure_mediapipe_model():
    s3_uri = os.getenv("MEDIAPIPE_MODEL_S3_URI")
    local_path = os.getenv("MEDIAPIPE_MODEL_PATH")

    if not s3_uri or not local_path:
        print("MediaPipe bootstrap: env vars not set, skipping")
        return

    local_path = pathlib.Path(local_path)
    local_path.parent.mkdir(parents=True, exist_ok=True)

    if local_path.exists():
        print(f"MediaPipe model already present at {local_path}")
        return

    if not s3_uri.startswith("s3://"):
        raise ValueError("Invalid MEDIAPIPE_MODEL_S3_URI")

    bucket, key = s3_uri.replace("s3://", "").split("/", 1)

    print(f"Downloading MediaPipe model from {s3_uri}")
    s3 = boto3.client("s3")
    s3.download_file(bucket, key, str(local_path))
    print("MediaPipe model download complete")
