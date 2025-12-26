"""
S3 Service - Handles presigned URL generation and S3 operations.
"""

from __future__ import annotations

from typing import Any

from backend.config import settings


def _import_boto3():
    """Lazy import of boto3 to avoid hard dependencies in tests."""
    try:
        import boto3
        from botocore.exceptions import ClientError
        return boto3, ClientError
    except ImportError as e:
        raise ImportError(
            f"boto3 is not installed. Please install it: pip install boto3"
        ) from e


class S3Service:
    """Service for S3 operations."""

    def __init__(self):
        """Initialize S3 client."""
        boto3, ClientError = _import_boto3()
        self.boto3 = boto3
        self.ClientError = ClientError
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
        except self.ClientError as e:
            raise RuntimeError(f"Failed to generate presigned URL: {e!s}") from e

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
        except self.ClientError as e:
            if e.response["Error"]["Code"] == "404":
                raise RuntimeError(f"Object not found: {key}") from e
            raise RuntimeError(f"Failed to get object metadata: {e!s}") from e


# Global instance (created lazily when first accessed)
_s3_service_instance: S3Service | None = None


def _get_s3_service() -> S3Service:
    global _s3_service_instance
    if _s3_service_instance is None:
        _s3_service_instance = S3Service()
    return _s3_service_instance


# Expose through module attribute (will be created when first imported and used)
s3_service = None  # type: ignore[assignment]


class _LazyProxy:
    """Lazy proxy that creates S3Service on first access."""

    def __getattr__(self, name: str) -> Any:
        return getattr(_get_s3_service(), name)


# Replace the module-level s3_service with lazy proxy
s3_service = _LazyProxy()  # type: ignore[assignment]
