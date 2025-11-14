"""S3/MinIO utilities for presigned URL generation and file operations."""

from __future__ import annotations

import logging
from typing import Any

import boto3
from backend.config import settings
from botocore.client import Config
from botocore.exceptions import BotoCoreError, ClientError

logger = logging.getLogger(__name__)


def get_s3_client() -> Any:
    """
    Create and return an S3 client configured for MinIO (dev) or AWS S3 (prod).

    Uses settings from backend.config:
    - S3_ENDPOINT_URL: If set, connects to MinIO (dev), otherwise AWS S3 (prod)
    - S3_ACCESS_KEY, S3_SECRET_KEY: Credentials (use placeholders if not set)
    - S3_REGION: AWS region

    Returns:
        boto3.client: Configured S3 client
    """
    # Use placeholders if credentials are not set (for testing/CI)
    access_key = settings.S3_ACCESS_KEY or "placeholder-access-key"
    secret_key = settings.S3_SECRET_KEY or "placeholder-secret-key"

    client_config = Config(signature_version="s3v4")

    if settings.S3_ENDPOINT_URL:
        # MinIO development setup
        logger.info(f"Creating S3 client for MinIO at {settings.S3_ENDPOINT_URL}")
        return boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=client_config,
            region_name=settings.S3_REGION,
        )
    else:
        # AWS S3 production setup
        logger.info("Creating S3 client for AWS S3")
        return boto3.client(
            "s3",
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            config=client_config,
            region_name=settings.S3_REGION,
        )


def generate_presigned_upload_url(
    s3_key: str, content_type: str = "image/jpeg", expiry: int | None = None
) -> str | None:
    """
    Generate a presigned URL for uploading a file to S3/MinIO.

    Args:
        s3_key: S3 object key (path)
        content_type: MIME type of the file
        expiry: URL expiration time in seconds (default from settings)

    Returns:
        str: Presigned upload URL or None if generation fails
    """
    if not settings.ENABLE_UPLOADS:
        logger.warning("Uploads are disabled via ENABLE_UPLOADS flag")
        return None

    try:
        client = get_s3_client()
        expiry = expiry or settings.S3_PRESIGNED_EXPIRY

        url = client.generate_presigned_url(
            "put_object",
            Params={
                "Bucket": settings.S3_BUCKET,
                "Key": s3_key,
                "ContentType": content_type,
            },
            ExpiresIn=expiry,
        )
        logger.info(f"Generated presigned upload URL for key: {s3_key}")
        return url
    except (BotoCoreError, ClientError) as e:
        logger.error(f"Failed to generate presigned upload URL: {e}")
        return None


def generate_presigned_download_url(s3_key: str, expiry: int | None = None) -> str | None:
    """
    Generate a presigned URL for downloading a file from S3/MinIO.

    Args:
        s3_key: S3 object key (path)
        expiry: URL expiration time in seconds (default from settings)

    Returns:
        str: Presigned download URL or None if generation fails
    """
    try:
        client = get_s3_client()
        expiry = expiry or settings.S3_PRESIGNED_EXPIRY

        url = client.generate_presigned_url(
            "get_object",
            Params={
                "Bucket": settings.S3_BUCKET,
                "Key": s3_key,
            },
            ExpiresIn=expiry,
        )
        logger.info(f"Generated presigned download URL for key: {s3_key}")
        return url
    except (BotoCoreError, ClientError) as e:
        logger.error(f"Failed to generate presigned download URL: {e}")
        return None


def check_s3_connection() -> bool:
    """
    Check if S3/MinIO connection is working.

    Returns:
        bool: True if connection is successful, False otherwise
    """
    try:
        client = get_s3_client()
        # Try to head the bucket to verify access
        client.head_bucket(Bucket=settings.S3_BUCKET)
        logger.info(f"Successfully connected to S3 bucket: {settings.S3_BUCKET}")
        return True
    except (BotoCoreError, ClientError) as e:
        logger.warning(f"S3 connection check failed: {e}")
        return False
