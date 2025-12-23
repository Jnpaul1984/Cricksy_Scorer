"""
S3 Service - Handles presigned URL generation and S3 operations.
"""

from __future__ import annotations

import boto3
from botocore.exceptions import ClientError

from backend.config import settings


class S3Service:
    """Service for S3 operations."""

    def __init__(self):
        """Initialize S3 client."""
        self.s3_client = boto3.client("s3", region_name=settings.AWS_REGION)

    def generate_presigned_put_url(
        self,
        bucket: str,
        key: str,
        expires_in: int | None = None,
    ) -> str:
        """
        Generate a presigned PUT URL for uploading to S3.

        Args:
            bucket: S3 bucket name
            key: S3 object key (path)
            expires_in: URL expiration time in seconds (defaults to config value)

        Returns:
            Presigned PUT URL

        Raises:
            ClientError: If S3 operation fails
        """
        if expires_in is None:
            expires_in = settings.S3_UPLOAD_URL_EXPIRES_SECONDS

        try:
            url = self.s3_client.generate_presigned_url(
                "put_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in,
            )
            return url
        except ClientError as e:
            raise RuntimeError(f"Failed to generate presigned URL: {str(e)}") from e

    def get_object_metadata(self, bucket: str, key: str) -> dict:
        """
        Get metadata for an S3 object.

        Args:
            bucket: S3 bucket name
            key: S3 object key

        Returns:
            Dictionary with object metadata

        Raises:
            ClientError: If object doesn't exist or S3 operation fails
        """
        try:
            response = self.s3_client.head_object(Bucket=bucket, Key=key)
            return {
                "size": response.get("ContentLength"),
                "last_modified": response.get("LastModified"),
                "etag": response.get("ETag"),
            }
        except ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise RuntimeError(f"Object not found: {key}") from e
            raise RuntimeError(f"Failed to get object metadata: {str(e)}") from e


# Global instance
s3_service = S3Service()
