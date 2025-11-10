"""S3/MinIO utilities for presigned URLs and file operations."""
from __future__ import annotations

import uuid
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from backend.config import settings


def get_s3_client() -> Any:
    """
    Get configured boto3 S3 client.
    
    Supports both AWS S3 (production) and MinIO (development).
    """
    config_params: dict[str, Any] = {
        "region_name": settings.S3_REGION,
        "aws_access_key_id": settings.S3_ACCESS_KEY,
        "aws_secret_access_key": settings.S3_SECRET_KEY,
    }
    
    if settings.S3_ENDPOINT:
        # MinIO or custom S3-compatible endpoint
        config_params["endpoint_url"] = settings.S3_ENDPOINT
        config_params["config"] = Config(signature_version="s3v4")
    
    return boto3.client("s3", **config_params)


def generate_upload_key(filename: str, uploader_id: str) -> str:
    """
    Generate a unique S3 key for an upload.
    
    Format: uploads/{uploader_id}/{uuid}/{filename}
    """
    unique_id = str(uuid.uuid4())
    # Sanitize filename to prevent path traversal
    safe_filename = filename.replace("/", "_").replace("\\", "_")
    return f"uploads/{uploader_id}/{unique_id}/{safe_filename}"


def generate_presigned_put_url(s3_key: str, content_type: str, expires_in: int = 3600) -> str:
    """
    Generate a presigned URL for uploading a file directly to S3.
    
    Args:
        s3_key: The S3 object key
        content_type: MIME type of the file
        expires_in: URL expiration time in seconds (default 1 hour)
    
    Returns:
        Presigned PUT URL
    """
    client = get_s3_client()
    
    try:
        url = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.S3_BUCKET,
                "Key": s3_key,
                "ContentType": content_type,
            },
            ExpiresIn=expires_in,
        )
        return url
    except ClientError as e:
        raise RuntimeError(f"Failed to generate presigned URL: {e}") from e


def generate_presigned_get_url(s3_key: str, expires_in: int = 3600) -> str:
    """
    Generate a presigned URL for downloading a file from S3.
    
    Args:
        s3_key: The S3 object key
        expires_in: URL expiration time in seconds (default 1 hour)
    
    Returns:
        Presigned GET URL
    """
    client = get_s3_client()
    
    try:
        url = client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.S3_BUCKET,
                "Key": s3_key,
            },
            ExpiresIn=expires_in,
        )
        return url
    except ClientError as e:
        raise RuntimeError(f"Failed to generate presigned URL: {e}") from e


def download_file_from_s3(s3_key: str, local_path: str) -> None:
    """
    Download a file from S3 to a local path.
    
    Args:
        s3_key: The S3 object key
        local_path: Local filesystem path to save the file
    """
    client = get_s3_client()
    
    try:
        client.download_file(settings.S3_BUCKET, s3_key, local_path)
    except ClientError as e:
        raise RuntimeError(f"Failed to download file from S3: {e}") from e


def check_s3_connection() -> bool:
    """
    Check if S3/MinIO connection is working.
    
    Returns:
        True if connection is successful, False otherwise
    """
    if not settings.S3_ACCESS_KEY or not settings.S3_SECRET_KEY:
        return False
    
    try:
        client = get_s3_client()
        # Try to head the bucket to verify credentials
        client.head_bucket(Bucket=settings.S3_BUCKET)
        return True
    except Exception:
        return False
