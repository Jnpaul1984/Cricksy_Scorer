# Upload Workflow Documentation

## Overview

The Cricksy Scorer upload pipeline allows users to upload scorecard images or PDFs for OCR processing and automatic delivery extraction. This document describes the complete workflow from upload initiation to applying parsed deliveries to a game.

## Architecture

The upload system consists of:

1. **Frontend Upload UI**: Vue components for file selection and upload
2. **Backend API**: FastAPI endpoints for managing uploads
3. **S3/MinIO Storage**: Object storage for uploaded files
4. **Celery Worker**: Asynchronous OCR and parsing worker
5. **Database**: Upload metadata and parsed results

## Workflow Steps

### 1. Initiate Upload

**Endpoint**: `POST /api/uploads/initiate`

**Request**:
```json
{
  "filename": "scorecard.jpg",
  "content_type": "image/jpeg",
  "uploader_id": "user123",
  "game_id": 1
}
```

**Response**:
```json
{
  "upload_id": 42,
  "presigned_url": "https://s3.amazonaws.com/bucket/...?signature=...",
  "s3_key": "uploads/user123/uuid/scorecard.jpg",
  "expires_in": 3600
}
```

The backend generates a presigned S3 PUT URL that allows the client to upload directly to S3 without exposing credentials. An upload record is created in `pending` status.

### 2. Upload File to S3

The client uses the presigned URL to upload the file directly to S3:

```javascript
const response = await fetch(presignedUrl, {
  method: 'PUT',
  headers: {
    'Content-Type': contentType
  },
  body: fileBlob
});
```

### 3. Complete Upload

**Endpoint**: `POST /api/uploads/complete`

**Request**:
```json
{
  "upload_id": 42
}
```

**Response** (HTTP 202 Accepted):
```json
{
  "upload_id": 42,
  "status": "processing",
  "message": "Upload accepted for processing"
}
```

The backend marks the upload as `processing` and enqueues a Celery task to process the file.

### 4. OCR Processing (Asynchronous)

A Celery worker:
1. Downloads the file from S3
2. Extracts text using Tesseract OCR
3. Parses the text into delivery objects using rule-based parser
4. Saves the `parsed_preview` to the upload record
5. Updates status to `ready` (or `failed` if errors occur)

### 5. Poll Upload Status

**Endpoint**: `GET /api/uploads/{upload_id}/status`

**Response**:
```json
{
  "upload_id": 42,
  "filename": "scorecard.jpg",
  "status": "ready",
  "game_id": 1,
  "parsed_preview": {
    "deliveries": [
      {
        "over": 1,
        "ball": 1,
        "batsman": "Player A",
        "bowler": "Player B",
        "runs": 4,
        "is_wicket": false
      }
    ],
    "metadata": {
      "confidence": 0.85,
      "ocr_engine": "tesseract"
    }
  },
  "error_message": null,
  "created_at": "2025-11-10T01:00:00Z",
  "updated_at": "2025-11-10T01:05:00Z"
}
```

Clients should poll this endpoint to check when processing is complete.

### 6. Review and Edit

The frontend displays the `parsed_preview` in a review UI where users can:
- View the extracted deliveries
- Edit individual delivery fields
- Add or remove deliveries
- Verify the accuracy of the OCR results

### 7. Apply to Game

**Endpoint**: `POST /api/uploads/{upload_id}/apply`

**Request**:
```json
{
  "confirmation": true,
  "edited_preview": {
    "deliveries": [...]
  }
}
```

**Response**:
```json
{
  "success": true,
  "message": "Successfully applied 120 deliveries to game 1",
  "deliveries_added": 120
}
```

**Important**: This endpoint requires:
- Explicit confirmation (`confirmation: true`)
- Upload must be in `ready` status
- Upload must be associated with a game
- The parsed preview is validated before application
- **Human verification is mandatory** - OCR results must be reviewed before applying

The deliveries are validated and then added to the game's delivery ledger using the existing scoring service. This ensures the core scoring logic remains unchanged.

## Configuration

### Environment Variables

```bash
# Feature Flags
CRICKSY_ENABLE_UPLOADS=1           # Enable upload feature (default: 1 in dev, 0 in prod)
CRICKSY_ENABLE_OCR=1               # Enable OCR processing (default: 1 in dev, 0 in prod)

# S3/MinIO Configuration
CRICKSY_S3_ENDPOINT=               # Optional: For MinIO dev (e.g., http://localhost:9000)
CRICKSY_S3_REGION=us-east-1        # AWS region
CRICKSY_S3_BUCKET=cricksy-uploads  # S3 bucket name
CRICKSY_S3_ACCESS_KEY=             # S3 access key (REQUIRED)
CRICKSY_S3_SECRET_KEY=             # S3 secret key (REQUIRED)

# Celery/Redis Configuration
CRICKSY_REDIS_URL=redis://localhost:6379/0
CRICKSY_CELERY_BROKER_URL=redis://localhost:6379/0
CRICKSY_CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Development Setup with MinIO

For local development, use MinIO as an S3-compatible storage:

```bash
# Start MinIO
docker run -d \
  -p 9000:9000 \
  -p 9001:9001 \
  --name minio \
  -e "MINIO_ROOT_USER=minioadmin" \
  -e "MINIO_ROOT_PASSWORD=minioadmin" \
  minio/minio server /data --console-address ":9001"

# Configure environment
export CRICKSY_S3_ENDPOINT=http://localhost:9000
export CRICKSY_S3_ACCESS_KEY=minioadmin
export CRICKSY_S3_SECRET_KEY=minioadmin
export CRICKSY_S3_BUCKET=cricksy-uploads-dev

# Create bucket (first time only)
aws --endpoint-url http://localhost:9000 s3 mb s3://cricksy-uploads-dev
```

### Production Setup with AWS S3

```bash
# Create S3 bucket
aws s3 mb s3://cricksy-uploads-prod --region us-east-1

# Create IAM policy (uploads-policy.json)
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:PutObject",
        "s3:GetObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::cricksy-uploads-prod/*"
    },
    {
      "Effect": "Allow",
      "Action": ["s3:ListBucket"],
      "Resource": "arn:aws:s3:::cricksy-uploads-prod"
    }
  ]
}

# Create IAM user and attach policy
aws iam create-user --user-name cricksy-uploader
aws iam put-user-policy --user-name cricksy-uploader \
  --policy-name CricksyUploadsPolicy \
  --policy-document file://uploads-policy.json

# Create access keys
aws iam create-access-key --user-name cricksy-uploader

# Configure environment (use AWS Secrets Manager or similar)
export CRICKSY_S3_ACCESS_KEY=<access-key>
export CRICKSY_S3_SECRET_KEY=<secret-key>
export CRICKSY_S3_BUCKET=cricksy-uploads-prod
# DO NOT set S3_ENDPOINT for AWS S3
```

## Security Considerations

### 1. Presigned URLs
- URLs expire after 1 hour by default
- Each URL is single-use and scoped to a specific S3 key
- Credentials are never exposed to the client

### 2. Upload Validation
- File type validation on both client and server
- Maximum file size enforced at S3 level
- S3 keys include user ID to prevent collisions and aid in auditing

### 3. Human Verification
- **All OCR results require human review before applying**
- The `apply` endpoint requires explicit confirmation
- Parsed previews are validated before application
- Edit capability allows correction of OCR errors

### 4. Secrets Management
- **Never commit S3 credentials to version control**
- Use environment variables or secure secret storage
- Rotate credentials regularly
- Use IAM roles in production where possible

## Error Handling

### Upload Errors

| Error | Status Code | Description |
|-------|-------------|-------------|
| Feature Disabled | 403 | Uploads feature is disabled |
| No Credentials | 503 | S3 credentials not configured |
| Upload Not Found | 404 | Invalid upload_id |
| Invalid Status | 400 | Upload not in expected status |
| No Confirmation | 400 | Apply requires explicit confirmation |
| Invalid Preview | 400 | Parsed preview has invalid format |

### Processing Errors

If OCR processing fails:
- Upload status is set to `failed`
- `error_message` field contains the error details
- The upload can be manually retried or deleted

## Testing

### Unit Tests

Run unit tests (no S3 required):
```bash
cd backend
pytest tests/test_uploads.py -v
```

### Integration Tests

Integration tests require S3 credentials:
```bash
# Set up MinIO for testing
export CRICKSY_S3_ENDPOINT=http://localhost:9000
export CRICKSY_S3_ACCESS_KEY=minioadmin
export CRICKSY_S3_SECRET_KEY=minioadmin

# Run integration tests
pytest tests/test_uploads.py -v -m integration
```

## Monitoring

Key metrics to monitor:

1. **Upload Success Rate**: Percentage of uploads that complete successfully
2. **Processing Time**: Time from upload completion to ready status
3. **OCR Accuracy**: Percentage of deliveries requiring manual correction
4. **Storage Usage**: Total S3 storage consumed
5. **Failed Uploads**: Rate and reasons for upload failures

## Future Enhancements

1. **Batch Uploads**: Support uploading multiple files at once
2. **Video Support**: Extract frames from video for OCR
3. **Live OCR**: Real-time OCR as the game progresses
4. **ML-Based Parser**: Replace rule-based parser with ML model
5. **Confidence Scores**: Per-delivery confidence scores from OCR
6. **Auto-Apply**: Automatically apply high-confidence results
7. **Audit Trail**: Track all edits and who approved the upload

## Related Documentation

- [Deploy Worker Guide](./DEPLOY_WORKER.md) - Celery worker deployment
- [AI Ethics & Media Policy](./AI_ETHICS.md) - Ethics and consent guidelines
- [Core Scoring System](./CORE_SCORING_SYSTEM.md) - Delivery ledger and scoring logic
