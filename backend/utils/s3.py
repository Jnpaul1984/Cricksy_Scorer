"""S3/MinIO utilities for presigned URLs and file operations.

Supports both AWS S3 (production) and MinIO (development) via S3-compatible API.
"""
from __future__ import annotations

import os
from typing import Any
from datetime import timedelta

try:
    import boto3
    from botocore.client import Config
    from botocore.exceptions import ClientError
except ImportError:
    boto3 = None  # type: ignore
    Config = None  # type: ignore
    ClientError = Exception  # type: ignore


def _get_s3_client() -> Any:
    """
    Create and return an S3 client configured for either AWS S3 or MinIO.

    Environment variables:
    - S3_ENDPOINT_URL: If set, use this endpoint (MinIO dev, e.g., http://localhost:9000)
    - S3_ACCESS_KEY_ID: Access key (required)
    - S3_SECRET_ACCESS_KEY: Secret key (required)
    - S3_REGION: AWS region (default: us-east-1)
    - S3_USE_PATH_STYLE: If "1", use path-style addressing (required for MinIO)
    """
    if boto3 is None:
        raise RuntimeError(
            "boto3 is not installed. Install with: pip install boto3"
        )

    endpoint_url = os.getenv("S3_ENDPOINT_URL")
    access_key = os.getenv("S3_ACCESS_KEY_ID")
    secret_key = os.getenv("S3_SECRET_ACCESS_KEY")
    region = os.getenv("S3_REGION", "us-east-1")
    use_path_style = os.getenv("S3_USE_PATH_STYLE", "0") == "1"

    if not access_key or not secret_key:
        raise ValueError(
            "S3_ACCESS_KEY_ID and S3_SECRET_ACCESS_KEY must be set in environment"
        )

    config = Config(signature_version='s3v4', s3={'addressing_style': 'path'} if use_path_style else None)

    return boto3.client(
        "s3",
        endpoint_url=endpoint_url,
        aws_access_key_id=access_key,
        aws_secret_access_key=secret_key,
        region_name=region,
        config=config,
    )


def generate_presigned_upload_url(
    bucket: str,
    key: str,
    expires_in: int = 3600,
    content_type: str | None = None,
) -> dict[str, Any]:
    """
    Generate a presigned URL for uploading a file to S3/MinIO.

    Args:
        bucket: S3 bucket name
        key: Object key (path) in the bucket
        expires_in: URL expiration time in seconds (default: 1 hour)
        content_type: Optional content type for the upload

    Returns:
        dict with 'url' and 'fields' for POST upload (or just 'url' for PUT)

    Example:
        >>> result = generate_presigned_upload_url("my-bucket", "uploads/file.jpg")
        >>> # Frontend does: PUT result['url'] with file content
    """
    s3_client = _get_s3_client()

    params = {
        "Bucket": bucket,
        "Key": key,
    }

    if content_type:
        params["ContentType"] = content_type

    try:
        url = s3_client.generate_presigned_url(
            "put_object",
            Params=params,
            ExpiresIn=expires_in,
        )
        return {"url": url, "method": "PUT"}
    except ClientError as e:
        raise RuntimeError(f"Failed to generate presigned URL: {e}") from e


def generate_presigned_download_url(
    bucket: str,
    key: str,
    expires_in: int = 3600,
) -> str:
    """
    Generate a presigned URL for downloading a file from S3/MinIO.

    Args:
        bucket: S3 bucket name
        key: Object key (path) in the bucket
        expires_in: URL expiration time in seconds (default: 1 hour)

    Returns:
        Presigned URL string

    Example:
        >>> url = generate_presigned_download_url("my-bucket", "uploads/file.jpg")
        >>> # Frontend does: GET url
    """
    s3_client = _get_s3_client()

    try:
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expires_in,
        )
        return url
    except ClientError as e:
        raise RuntimeError(f"Failed to generate presigned URL: {e}") from e


def check_object_exists(bucket: str, key: str) -> bool:
    """
    Check if an object exists in S3/MinIO.

    Args:
        bucket: S3 bucket name
        key: Object key (path) in the bucket

    Returns:
        True if object exists, False otherwise
    """
    s3_client = _get_s3_client()

    try:
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response['Error']['Code'] == '404':
            return False
        raise


def delete_object(bucket: str, key: str) -> bool:
    """
    Delete an object from S3/MinIO.

    Args:
        bucket: S3 bucket name
        key: Object key (path) in the bucket

    Returns:
        True if deleted successfully
    """
    s3_client = _get_s3_client()

    try:
        s3_client.delete_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        raise RuntimeError(f"Failed to delete object: {e}") from e


def get_default_bucket() -> str:
    """Get the default S3/MinIO bucket from environment."""
    bucket = os.getenv("S3_UPLOAD_BUCKET", "cricksy-uploads")
    return bucket
