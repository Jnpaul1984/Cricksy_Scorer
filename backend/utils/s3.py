"""S3/MinIO presigned URL utilities for upload handling.

Supports both MinIO (development) and AWS S3 (production) via endpoint_url configuration.
"""

from __future__ import annotations

import logging
from typing import Any

import boto3
from backend.config import settings
from botocore.client import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)


def get_s3_client() -> Any:
    """Get configured S3 client (MinIO or AWS).

    Returns boto3 S3 client configured based on settings.
    - If S3_ENDPOINT_URL is set, connects to MinIO (dev)
    - Otherwise connects to AWS S3 (production)
    """
    config = Config(signature_version="s3v4")

    client_kwargs = {
        "service_name": "s3",
        "region_name": settings.S3_REGION,
        "config": config,
    }

    # Add credentials if provided (required for MinIO, optional for AWS with IAM roles)
    if settings.S3_ACCESS_KEY and settings.S3_SECRET_KEY:
        client_kwargs["aws_access_key_id"] = settings.S3_ACCESS_KEY
        client_kwargs["aws_secret_access_key"] = settings.S3_SECRET_KEY

    # Add endpoint URL for MinIO (dev) or leave blank for AWS (prod)
    if settings.S3_ENDPOINT_URL:
        client_kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
        logger.debug(f"Using MinIO endpoint: {settings.S3_ENDPOINT_URL}")

    return boto3.client(**client_kwargs)


def generate_presigned_upload_url(
    bucket: str, key: str, content_type: str, expiration: int | None = None
) -> str:
    """Generate presigned URL for uploading a file to S3/MinIO.

    Args:
        bucket: S3 bucket name
        key: Object key (path) in bucket
        content_type: MIME type of file to upload
        expiration: URL expiration time in seconds (default from settings)

    Returns:
        Presigned URL string

    Raises:
        ClientError: If unable to generate presigned URL
    """
    if expiration is None:
        expiration = settings.S3_PRESIGNED_URL_EXPIRY

    try:
        s3_client = get_s3_client()
        url = s3_client.generate_presigned_url(
            "put_object",
            Params={"Bucket": bucket, "Key": key, "ContentType": content_type},
            ExpiresIn=expiration,
        )
        logger.debug(f"Generated presigned upload URL for {bucket}/{key}")
        return url
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        raise


def generate_presigned_download_url(
    bucket: str, key: str, expiration: int | None = None
) -> str:
    """Generate presigned URL for downloading a file from S3/MinIO.

    Args:
        bucket: S3 bucket name
        key: Object key (path) in bucket
        expiration: URL expiration time in seconds (default from settings)

    Returns:
        Presigned URL string

    Raises:
        ClientError: If unable to generate presigned URL
    """
    if expiration is None:
        expiration = settings.S3_PRESIGNED_URL_EXPIRY

    try:
        s3_client = get_s3_client()
        url = s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": bucket, "Key": key},
            ExpiresIn=expiration,
        )
        logger.debug(f"Generated presigned download URL for {bucket}/{key}")
        return url
    except ClientError as e:
        logger.error(f"Failed to generate presigned download URL: {e}")
        raise


def check_object_exists(bucket: str, key: str) -> bool:
    """Check if an object exists in S3/MinIO.

    Args:
        bucket: S3 bucket name
        key: Object key (path) in bucket

    Returns:
        True if object exists, False otherwise
    """
    try:
        s3_client = get_s3_client()
        s3_client.head_object(Bucket=bucket, Key=key)
        return True
    except ClientError as e:
        if e.response["Error"]["Code"] == "404":
            return False
        logger.error(f"Error checking object existence: {e}")
        raise


def delete_object(bucket: str, key: str) -> None:
    """Delete an object from S3/MinIO.

    Args:
        bucket: S3 bucket name
        key: Object key (path) in bucket

    Raises:
        ClientError: If unable to delete object
    """
    try:
        s3_client = get_s3_client()
        s3_client.delete_object(Bucket=bucket, Key=key)
        logger.info(f"Deleted object {bucket}/{key}")
    except ClientError as e:
        logger.error(f"Failed to delete object: {e}")
        raise
