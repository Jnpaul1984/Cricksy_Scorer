# S3 Presigned Upload Implementation - Code Diffs

## Files Created

### 1. `backend/services/s3_service.py`

```python
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
```

### 2. `backend/services/sqs_service.py`

```python
"""
SQS Service - Handles message queueing for video analysis jobs.
"""

from __future__ import annotations

import json
from typing import Any

import boto3
from botocore.exceptions import ClientError

from backend.config import settings


class SQSService:
    """Service for SQS operations."""

    def __init__(self):
        """Initialize SQS client."""
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
            params = {
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
        except ClientError as e:
            raise RuntimeError(f"Failed to send SQS message: {str(e)}") from e

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

                messages.append({
                    "id": msg.get("MessageId"),
                    "receipt_handle": msg.get("ReceiptHandle"),
                    "body": body,
                    "attributes": msg.get("Attributes", {}),
                    "message_attributes": msg.get("MessageAttributes", {}),
                })

            return messages
        except ClientError as e:
            raise RuntimeError(f"Failed to receive SQS messages: {str(e)}") from e

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
        except ClientError as e:
            raise RuntimeError(f"Failed to delete SQS message: {str(e)}") from e


# Global instance
sqs_service = SQSService()
```

## Files Modified

### `backend/routes/coach_pro_plus.py`

#### Imports (Added)

```python
# New imports
from backend.services.s3_service import s3_service
from backend.services.sqs_service import sqs_service
from backend.config import settings
```

#### Schemas (Added)

```python
class VideoUploadInitiateRequest(BaseModel):
    """Request schema for initiating a video upload"""

    session_id: str
    sample_fps: int = Field(default=10, ge=1, le=30)
    include_frames: bool = Field(default=False)


class VideoUploadInitiateResponse(BaseModel):
    """Response schema for upload initiate with presigned URL"""

    job_id: str
    session_id: str
    presigned_url: str
    expires_in: int
    s3_bucket: str
    s3_key: str


class VideoUploadCompleteRequest(BaseModel):
    """Request schema for completing a video upload"""

    job_id: str


class VideoUploadCompleteResponse(BaseModel):
    """Response schema for upload completion"""

    job_id: str
    status: str
    sqs_message_id: str | None = None
    message: str
```

#### New Endpoints

**POST /api/coaches/plus/videos/upload/initiate**

```python
@router.post("/videos/upload/initiate", response_model=VideoUploadInitiateResponse)
async def initiate_video_upload(
    request: VideoUploadInitiateRequest,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> VideoUploadInitiateResponse:
    """
    Initiate a video upload by creating an analysis job and generating a presigned PUT URL.

    Flow:
    1. Validate session exists and user owns it
    2. Create VideoAnalysisJob with status "queued"
    3. Generate S3 presigned PUT URL
    4. Return URL + job details for client to upload to

    Key: coach_plus/{owner_type}/{owner_id}/{session_id}/{video_id}/original.mp4
    """
    # Verify feature access
    if not await _check_feature_access(current_user, "video_upload_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_upload_enabled",
        )

    # Verify user is coach_pro_plus or org_pro
    if current_user.role not in (RoleEnum.coach_pro_plus, RoleEnum.org_pro):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Coach Pro Plus users can upload videos",
        )

    # Validate session exists and user owns it
    result = await db.execute(select(VideoSession).where(VideoSession.id == request.session_id))
    session = result.scalar_one_or_none()

    if not session:
        raise HTTPException(status_code=404, detail="Video session not found")

    # Check ownership
    if current_user.role == RoleEnum.coach_pro_plus:
        if session.owner_id != current_user.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this session",
            )
    else:
        # Org users see org sessions
        if session.owner_type == OwnerTypeEnum.org and session.owner_id != current_user.org_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have access to this session",
            )

    # Create analysis job
    job_id = str(uuid4())
    job = VideoAnalysisJob(
        id=job_id,
        session_id=request.session_id,
        sample_fps=request.sample_fps,
        include_frames=request.include_frames,
        status=VideoAnalysisJobStatus.queued,
    )

    db.add(job)
    await db.commit()

    # Generate S3 presigned URL
    # Key format: coach_plus/{owner_type}/{owner_id}/{session_id}/{video_id}/original.mp4
    video_id = str(uuid4())
    s3_key = f"coach_plus/{session.owner_type.value}/{session.owner_id}/{request.session_id}/{video_id}/original.mp4"

    try:
        presigned_url = s3_service.generate_presigned_put_url(
            bucket=settings.S3_COACH_VIDEOS_BUCKET,
            key=s3_key,
            expires_in=settings.S3_UPLOAD_URL_EXPIRES_SECONDS,
        )
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate upload URL: {str(e)}",
        ) from e

    return VideoUploadInitiateResponse(
        job_id=job_id,
        session_id=request.session_id,
        presigned_url=presigned_url,
        expires_in=settings.S3_UPLOAD_URL_EXPIRES_SECONDS,
        s3_bucket=settings.S3_COACH_VIDEOS_BUCKET,
        s3_key=s3_key,
    )
```

**POST /api/coaches/plus/videos/upload/complete**

```python
@router.post("/videos/upload/complete", response_model=VideoUploadCompleteResponse)
async def complete_video_upload(
    request: VideoUploadCompleteRequest,
    current_user: Annotated[User, Depends(security.get_current_active_user)],
    db: AsyncSession = Depends(get_db),
) -> VideoUploadCompleteResponse:
    """
    Complete a video upload by updating job status and enqueuing to SQS.

    Flow:
    1. Validate job exists and user owns session
    2. Update job status to "uploaded"
    3. Send message to SQS queue for async processing
    4. Return confirmation with SQS message ID

    After this, the video analysis worker will:
    - Receive message from SQS
    - Extract frames from video
    - Compute pose metrics
    - Update job status to "completed"
    """
    # Verify feature access
    if not await _check_feature_access(current_user, "video_upload_enabled"):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Insufficient feature access: video_upload_enabled",
        )

    # Verify user is coach_pro_plus or org_pro
    if current_user.role not in (RoleEnum.coach_pro_plus, RoleEnum.org_pro):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only Coach Pro Plus users can upload videos",
        )

    # Fetch job
    result = await db.execute(select(VideoAnalysisJob).where(VideoAnalysisJob.id == request.job_id))
    job = result.scalar_one_or_none()

    if not job:
        raise HTTPException(status_code=404, detail="Analysis job not found")

    # Check ownership via session
    session = job.session
    if current_user.role == RoleEnum.coach_pro_plus and session.owner_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have access to this job",
        )

    # Update job status to "uploaded"
    job.status = VideoAnalysisJobStatus.processing

    # Prepare SQS message
    message_body = {
        "job_id": job.id,
        "session_id": job.session_id,
        "sample_fps": job.sample_fps,
        "include_frames": job.include_frames,
    }

    # Send to SQS queue
    try:
        message_id = sqs_service.send_message(
            queue_url=settings.SQS_VIDEO_ANALYSIS_QUEUE_URL,
            message_body=message_body,
        )
        job.sqs_message_id = message_id
    except RuntimeError as e:
        job.status = VideoAnalysisJobStatus.failed
        job.error_message = f"Failed to enqueue job: {str(e)}"
        await db.commit()

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue video for processing: {str(e)}",
        ) from e

    # Commit changes
    await db.commit()

    return VideoUploadCompleteResponse(
        job_id=job.id,
        status=job.status.value,
        sqs_message_id=message_id,
        message="Video uploaded and queued for analysis",
    )
```

## Usage Flow

### Step 1: Create Video Session
```bash
curl -X POST http://localhost:8000/api/coaches/plus/sessions \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Batting Technique Review",
    "player_ids": ["player1", "player2"]
  }'
```
Returns: `session_id`

### Step 2: Initiate Upload
```bash
curl -X POST http://localhost:8000/api/coaches/plus/videos/upload/initiate \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "session_id": "<session_id>",
    "sample_fps": 15,
    "include_frames": true
  }'
```
Returns:
```json
{
  "job_id": "...",
  "session_id": "...",
  "presigned_url": "https://bucket.s3.amazonaws.com/...",
  "expires_in": 3600,
  "s3_bucket": "...",
  "s3_key": "coach_plus/coach/user123/session_id/video_id/original.mp4"
}
```

### Step 3: Upload Video to S3
```bash
curl -X PUT '<presigned_url>' \
  -H "Content-Type: video/mp4" \
  --data-binary @video.mp4
```

### Step 4: Complete Upload
```bash
curl -X POST http://localhost:8000/api/coaches/plus/videos/upload/complete \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{
    "job_id": "<job_id>"
  }'
```
Returns:
```json
{
  "job_id": "...",
  "status": "processing",
  "sqs_message_id": "...",
  "message": "Video uploaded and queued for analysis"
}
```

## Architecture

### S3 Key Structure
```
coach_plus/{owner_type}/{owner_id}/{session_id}/{video_id}/original.mp4
```

Example:
```
coach_plus/coach/user_123/session_456/video_789/original.mp4
coach_plus/org/org_abc/session_456/video_789/original.mp4
```

### Job Status Transitions
```
queued → processing → completed (or failed)
```

### SQS Message Format
```json
{
  "job_id": "...",
  "session_id": "...",
  "sample_fps": 15,
  "include_frames": true
}
```

## Error Handling

- **Missing session**: 404 "Video session not found"
- **No access to session**: 403 "You don't have access to this session"
- **Missing job**: 404 "Analysis job not found"
- **Failed S3 presigned URL**: 500 "Failed to generate upload URL: ..."
- **Failed SQS enqueue**: 500 "Failed to queue video for processing: ..."
  - Also updates job status to "failed" with error_message

## Configuration Required

Ensure these environment variables are set:
- `AWS_REGION` - S3/SQS region
- `S3_COACH_VIDEOS_BUCKET` - Bucket for video storage
- `S3_UPLOAD_URL_EXPIRES_SECONDS` - Presigned URL expiration (default 3600)
- `SQS_VIDEO_ANALYSIS_QUEUE_URL` - Queue URL for async processing

These are already configured in backend/config.py and Terraform.
