# Upload Workflow Documentation

This document describes the scorecard upload and OCR processing workflow in Cricksy Scorer.

## Overview

The upload system allows users to upload scorecard images (or PDFs) which are then:
1. Stored in S3/MinIO
2. Processed by an OCR worker using Tesseract
3. Parsed into structured scorecard data
4. Reviewed and confirmed by a human before being applied to the game

## Architecture

```
Client → Backend API → S3/MinIO
              ↓
         Celery Worker (OCR)
              ↓
         Parse & Store Preview
              ↓
     Human Review (Frontend)
              ↓
    Apply to Delivery Ledger
```

## Feature Flags

The upload system can be controlled via environment variables:

- `CRICKSY_ENABLE_UPLOADS` - Enable/disable upload feature (default: `1` in development)
- `CRICKSY_ENABLE_OCR` - Enable/disable OCR processing (default: `1` in development)

## Endpoints

### 1. Initiate Upload

**POST** `/api/uploads/initiate`

Generates a presigned URL for direct upload to S3/MinIO.

**Request:**
```json
{
  "filename": "scorecard.jpg",
  "content_type": "image/jpeg",
  "game_id": "game-123",  // optional
  "user_id": "user-456"    // optional
}
```

**Response (201):**
```json
{
  "upload_id": "uuid-here",
  "presigned_url": "https://s3.../presigned-url",
  "s3_bucket": "cricksy-uploads",
  "s3_key": "uploads/uuid-here/scorecard.jpg",
  "expires_in": 3600
}
```

**Allowed Content Types:**
- `image/jpeg`
- `image/png`
- `image/jpg`
- `application/pdf`

### 2. Complete Upload

**POST** `/api/uploads/{upload_id}/complete`

Called after the client successfully uploads the file to S3/MinIO. This triggers OCR processing.

**Request:**
```json
{
  "file_size": 12345  // optional, in bytes
}
```

**Response (200):**
```json
{
  "message": "Upload marked as complete",
  "upload_id": "uuid-here"
}
```

### 3. Get Upload Status

**GET** `/api/uploads/{upload_id}/status`

Retrieve the current status and parsed preview of an upload.

**Response (200):**
```json
{
  "upload_id": "uuid-here",
  "status": "parsed",
  "filename": "scorecard.jpg",
  "game_id": "game-123",
  "parsed_preview": {
    "deliveries": [...],
    "teams": {...},
    "metadata": {...}
  },
  "error_message": null,
  "created_at": "2025-11-10T01:00:00Z",
  "updated_at": "2025-11-10T01:05:00Z",
  "processed_at": "2025-11-10T01:05:00Z",
  "applied_at": null
}
```

**Status Values:**
- `initiated` - Presigned URL generated, awaiting upload
- `uploaded` - File uploaded to S3/MinIO
- `processing` - OCR worker processing
- `parsed` - OCR complete, data ready for review
- `applied` - Data confirmed and applied to delivery ledger
- `failed` - Processing failed (check `error_message`)
- `cancelled` - User cancelled

### 4. Apply Upload

**POST** `/api/uploads/{upload_id}/apply`

Apply parsed data to the delivery ledger after human review and confirmation.

**Request:**
```json
{
  "confirm": true,  // REQUIRED - explicit confirmation
  "validated_data": {  // OPTIONAL - corrected/validated data
    "deliveries": [...],
    "teams": {...}
  }
}
```

**Response (200):**
```json
{
  "message": "Upload data applied successfully",
  "upload_id": "uuid-here",
  "game_id": "game-123"
}
```

**Important:** This endpoint:
- Requires `confirm: true` - users must explicitly confirm
- Validates that `parsed_preview` contains required fields (`deliveries`)
- Does NOT modify core scoring logic
- Triggers a WebSocket broadcast to notify connected clients

## Client Workflow

### Upload Flow

```javascript
// 1. Initiate upload
const { upload_id, presigned_url } = await fetch('/api/uploads/initiate', {
  method: 'POST',
  body: JSON.stringify({
    filename: file.name,
    content_type: file.type,
    game_id: currentGameId
  })
}).then(r => r.json())

// 2. Upload file directly to S3/MinIO
await fetch(presigned_url, {
  method: 'PUT',
  body: file,
  headers: { 'Content-Type': file.type }
})

// 3. Mark upload complete
await fetch(`/api/uploads/${upload_id}/complete`, {
  method: 'POST',
  body: JSON.stringify({ file_size: file.size })
})

// 4. Poll for status until parsed
let status = 'processing'
while (status === 'processing' || status === 'uploaded') {
  await sleep(2000)
  const data = await fetch(`/api/uploads/${upload_id}/status`).then(r => r.json())
  status = data.status
}

// 5. Show parsed preview for review
showReviewUI(data.parsed_preview)

// 6. After user confirms, apply data
await fetch(`/api/uploads/${upload_id}/apply`, {
  method: 'POST',
  body: JSON.stringify({
    confirm: true,
    validated_data: userCorrectedData  // optional
  })
})
```

## Configuration

### Environment Variables

**S3/MinIO:**
- `CRICKSY_S3_ENDPOINT_URL` - MinIO endpoint for dev (leave empty for AWS prod)
- `CRICKSY_S3_ACCESS_KEY` - S3 access key ID
- `CRICKSY_S3_SECRET_KEY` - S3 secret access key
- `CRICKSY_S3_BUCKET` - Bucket name (default: `cricksy-uploads`)
- `CRICKSY_S3_REGION` - S3 region (default: `us-east-1`)
- `CRICKSY_S3_PRESIGNED_URL_EXPIRY` - URL expiration in seconds (default: `3600`)

**Redis/Celery:**
- `CRICKSY_REDIS_URL` - Redis URL for Celery (default: `redis://localhost:6379/0`)
- `CRICKSY_CELERY_BROKER_URL` - Celery broker URL (default: same as REDIS_URL)
- `CRICKSY_CELERY_RESULT_BACKEND` - Celery result backend (default: same as REDIS_URL)

### Development Setup (MinIO)

For local development, use MinIO as an S3-compatible storage:

```bash
# Run MinIO with Docker
docker run -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"

# Set environment variables
export CRICKSY_S3_ENDPOINT_URL=http://localhost:9000
export CRICKSY_S3_ACCESS_KEY=minioadmin
export CRICKSY_S3_SECRET_KEY=minioadmin
export CRICKSY_S3_BUCKET=cricksy-uploads

# Create bucket (if needed)
# Access MinIO console at http://localhost:9001
```

### Production Setup (AWS S3)

For production, use actual AWS S3:

```bash
# Leave S3_ENDPOINT_URL unset for AWS
export CRICKSY_S3_ACCESS_KEY=your-aws-access-key
export CRICKSY_S3_SECRET_KEY=your-aws-secret-key
export CRICKSY_S3_BUCKET=your-production-bucket
export CRICKSY_S3_REGION=us-east-1

# Ensure bucket exists and has proper CORS configuration
```

## Security

### No Secrets in Code

- **DO NOT** commit S3 credentials to source control
- Use environment variables or secrets management
- Use IAM roles in production when possible

### Upload Validation

- Content type validation (images and PDFs only)
- File size limits (enforced at client and S3 level)
- Presigned URLs expire after 1 hour by default

### Human Verification Required

- OCR results are **prototype-level** and require human review
- The `/apply` endpoint requires explicit `confirm: true`
- Users should review `parsed_preview` before applying

## Error Handling

### Upload Errors

- If presigned URL generation fails → 500 error, check S3 credentials
- If file upload to S3 fails → Client-side error, retry or regenerate URL
- If OCR processing fails → Status becomes `failed`, check `error_message`

### Common Issues

1. **"Upload feature is currently disabled"** → Set `CRICKSY_ENABLE_UPLOADS=1`
2. **S3 connection errors** → Verify credentials and endpoint URL
3. **OCR not triggering** → Check Redis connection and Celery worker status
4. **Confirmation required error** → Ensure `confirm: true` in apply request

## Testing

Tests are in `backend/tests/test_uploads.py`. Integration tests requiring S3 are automatically skipped unless credentials are present:

```bash
# Run unit tests (no S3 required)
pytest backend/tests/test_uploads.py -v

# Run with S3 integration tests
export CRICKSY_S3_ACCESS_KEY=test-key
export CRICKSY_S3_SECRET_KEY=test-secret
pytest backend/tests/test_uploads.py -v
```

## Monitoring

Future enhancements will include:
- Upload metrics (success rate, processing time)
- OCR accuracy tracking
- Alert on high failure rates
- Storage usage monitoring

See `docs/DEPLOY_WORKER.md` for worker deployment and monitoring details.
