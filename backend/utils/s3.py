"""S3 / Object Storage utilities for presigned URLs and file operations."""

from __future__ import annotations

import logging
from typing import Any

import boto3
from botocore.client import Config
from botocore.exceptions import ClientError

from backend.config import settings

logger = logging.getLogger(__name__)


def get_s3_client() -> Any:
    """Create and return an S3 client using configuration from settings."""
    s3_config = Config(signature_version="s3v4")
    
    client_kwargs: dict[str, Any] = {
        "service_name": "s3",
        "region_name": settings.S3_REGION,
        "config": s3_config,
    }
    
    # Add credentials if provided
    if settings.S3_ACCESS_KEY and settings.S3_SECRET_KEY:
        client_kwargs["aws_access_key_id"] = settings.S3_ACCESS_KEY
        client_kwargs["aws_secret_access_key"] = settings.S3_SECRET_KEY
    
    # Add endpoint URL for MinIO or local testing
    if settings.S3_ENDPOINT_URL:
        client_kwargs["endpoint_url"] = settings.S3_ENDPOINT_URL
    
    return boto3.client(**client_kwargs)


def generate_presigned_put_url(
    s3_key: str,
    content_type: str | None = None,
    expiration: int | None = None,
) -> str:
    """
    Generate a presigned URL for uploading a file to S3.
    
    Args:
        s3_key: The S3 object key (path within bucket)
        content_type: Optional MIME type for the upload
        expiration: URL expiration time in seconds (default from settings)
    
    Returns:
        Presigned PUT URL as a string
    
    Raises:
        ClientError: If URL generation fails
    """
    expiration = expiration or settings.PRESIGNED_URL_EXPIRATION
    
    try:
        s3_client = get_s3_client()
        
        params: dict[str, Any] = {
            "Bucket": settings.S3_BUCKET,
            "Key": s3_key,
        }
        
        # Add content type if provided
        if content_type:
            params["ContentType"] = content_type
        
        url = s3_client.generate_presigned_url(
            ClientMethod="put_object",
            Params=params,
            ExpiresIn=expiration,
        )
        
        logger.info(f"Generated presigned PUT URL for s3_key={s3_key}")
        return url
    
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        raise


def generate_presigned_get_url(
    s3_key: str,
    expiration: int | None = None,
) -> str:
    """
    Generate a presigned URL for downloading a file from S3.
    
    Args:
        s3_key: The S3 object key (path within bucket)
        expiration: URL expiration time in seconds (default from settings)
    
    Returns:
        Presigned GET URL as a string
    
    Raises:
        ClientError: If URL generation fails
    """
    expiration = expiration or settings.PRESIGNED_URL_EXPIRATION
    
    try:
        s3_client = get_s3_client()
        
        url = s3_client.generate_presigned_url(
            ClientMethod="get_object",
            Params={
                "Bucket": settings.S3_BUCKET,
                "Key": s3_key,
            },
            ExpiresIn=expiration,
        )
        
        logger.info(f"Generated presigned GET URL for s3_key={s3_key}")
        return url
    
    except ClientError as e:
        logger.error(f"Failed to generate presigned URL: {e}")
        raise


def download_from_s3(s3_key: str) -> bytes:
    """
    Download a file from S3 and return its content as bytes.
    
    Args:
        s3_key: The S3 object key (path within bucket)
    
    Returns:
        File content as bytes
    
    Raises:
        ClientError: If download fails
    """
    try:
        s3_client = get_s3_client()
        
        response = s3_client.get_object(Bucket=settings.S3_BUCKET, Key=s3_key)
        content = response["Body"].read()
        
        logger.info(f"Downloaded {len(content)} bytes from s3_key={s3_key}")
        return content
    
    except ClientError as e:
        logger.error(f"Failed to download from S3: {e}")
        raise
