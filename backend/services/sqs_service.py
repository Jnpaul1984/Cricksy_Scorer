"""
SQS Service - Handles message queueing for video analysis jobs.
"""

from __future__ import annotations

import json
from typing import Any

from backend.config import settings


def _import_boto3():
    """Lazy import of boto3 to avoid hard dependencies in tests."""
    try:
        import boto3
        from botocore.exceptions import ClientError

        return boto3, ClientError
    except ImportError as e:
        raise ImportError("boto3 is not installed. Please install it: pip install boto3") from e


class SQSService:
    """Service for SQS operations."""

    def __init__(self):
        """Initialize SQS client."""
        boto3, ClientError = _import_boto3()
        self.boto3 = boto3
        self.ClientError = ClientError
        self.sqs_client = boto3.client("sqs", region_name=settings.AWS_REGION)

    def send_message(
        self,
        queue_url: str,
        message_body: dict[str, Any],
        message_attributes: dict[str, Any] | None = None,
    ) -> str:
        """
        Send a message to SQS queue.

        Args:
            queue_url: SQS queue URL
            message_body: Message body as dictionary (will be JSON serialized)
            message_attributes: Optional message attributes

        Returns:
            Message ID

        Raises:
            ClientError: If SQS operation fails
        """
        try:
            # Serialize message body to JSON
            body = json.dumps(message_body)

            # Prepare send parameters
            params: dict[str, Any] = {
                "QueueUrl": queue_url,
                "MessageBody": body,
            }

            # Add message attributes if provided
            if message_attributes:
                params["MessageAttributes"] = message_attributes

            # Send message
            response = self.sqs_client.send_message(**params)
            message_id = response.get("MessageId")

            if not message_id:
                raise RuntimeError("No MessageId in SQS response")

            return message_id
        except self.ClientError as e:
            raise RuntimeError(f"Failed to send SQS message: {e!s}") from e

    def receive_messages(
        self,
        queue_url: str,
        max_messages: int = 1,
        wait_time_seconds: int = 0,
    ) -> list[dict[str, Any]]:
        """
        Receive messages from SQS queue.

        Args:
            queue_url: SQS queue URL
            max_messages: Maximum number of messages to receive (1-10)
            wait_time_seconds: Long polling wait time (0-20 seconds)

        Returns:
            List of messages

        Raises:
            ClientError: If SQS operation fails
        """
        try:
            response = self.sqs_client.receive_message(
                QueueUrl=queue_url,
                MaxNumberOfMessages=max_messages,
                WaitTimeSeconds=wait_time_seconds,
            )

            messages = []
            for msg in response.get("Messages", []):
                try:
                    body = json.loads(msg.get("Body", "{}"))
                except json.JSONDecodeError:
                    body = msg.get("Body")

                messages.append(
                    {
                        "id": msg.get("MessageId"),
                        "receipt_handle": msg.get("ReceiptHandle"),
                        "body": body,
                        "attributes": msg.get("Attributes", {}),
                        "message_attributes": msg.get("MessageAttributes", {}),
                    }
                )

            return messages
        except self.ClientError as e:
            raise RuntimeError(f"Failed to receive SQS messages: {e!s}") from e

    def delete_message(self, queue_url: str, receipt_handle: str) -> None:
        """
        Delete a message from SQS queue.

        Args:
            queue_url: SQS queue URL
            receipt_handle: Message receipt handle

        Raises:
            ClientError: If SQS operation fails
        """
        try:
            self.sqs_client.delete_message(
                QueueUrl=queue_url,
                ReceiptHandle=receipt_handle,
            )
        except self.ClientError as e:
            raise RuntimeError(f"Failed to delete SQS message: {e!s}") from e


# Global instance (created lazily when first accessed)
_sqs_service_instance: SQSService | None = None


def _get_sqs_service() -> SQSService:
    global _sqs_service_instance
    if _sqs_service_instance is None:
        _sqs_service_instance = SQSService()
    return _sqs_service_instance


class _LazyProxy:
    """Lazy proxy that creates SQSService on first access."""

    def __getattr__(self, name: str) -> Any:
        return getattr(_get_sqs_service(), name)


# Expose through module attribute (will be created when first imported and used)
sqs_service: Any = _LazyProxy()
