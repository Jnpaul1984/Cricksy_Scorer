# Upload Workflow Documentation

## Overview

The upload workflow enables users to upload scorecard images, process them with OCR, and apply the parsed results to the delivery ledger after manual review.

## Architecture

### Components

1. **Backend API** (`backend/routes/uploads.py`)
   - Manages upload lifecycle
   - Generates presigned S3/MinIO URLs
   - Triggers OCR processing
   - Validates and applies parsed data

2. **S3/MinIO Storage** (`backend/utils/s3.py`)
   - Development: MinIO (local S3-compatible storage)
   - Production: AWS S3
   - Direct client uploads via presigned URLs

3. **OCR Worker** (`backend/worker/`)
   - Celery task queue
   - Redis message broker
   - Tesseract OCR processing
   - Scorecard parsing logic

4. **Database** (`backend/sql_app/models/upload.py`)
   - Upload tracking and status
   - Parsed data preview
   - Audit trail

## Upload Flow

### 1. Initiate Upload

**Endpoint**: `POST /api/uploads/initiate`

**Request**:
```json
{
  "filename": "scorecard.jpg",
  "content_type": "image/jpeg"
}
```

**Response**:
```json
{
  "upload_id": "uuid-string",
  "upload_url": "https://s3-endpoint/presigned-url",
  "s3_key": "uploads/uuid/scorecard.jpg",
  "expires_in": 3600
}
```

**Process**:
1. Server generates unique `upload_id`
2. Creates database record with status `pending`
3. Generates presigned S3/MinIO PUT URL
4. Returns URL to client

### 2. Client Upload

The client performs a direct HTTP PUT to the presigned URL:

```javascript
const response = await fetch(uploadUrl, {
  method: 'PUT',
  body: fileBlob,
  headers: {
    'Content-Type': 'image/jpeg'
  }
});
```

This bypasses the backend server and uploads directly to S3/MinIO.

### 3. Complete Upload

**Endpoint**: `POST /api/uploads/complete`

**Request**:
```json
{
  "upload_id": "uuid-string"
}
```

**Process**:
1. Verifies upload exists and is `pending`
2. Updates status to `uploaded`
3. Records `uploaded_at` timestamp
4. Queues OCR processing task (if `ENABLE_OCR=1`)

### 4. OCR Processing

**Background Task**: `process_upload_task`

**Process**:
1. Downloads image from S3/MinIO
2. Runs Tesseract OCR
3. Parses scorecard structure
4. Extracts player names, runs, wickets, overs
5. Stores in `parsed_preview` JSON field
6. Updates status to `completed` (or `failed`)

**Status Flow**:
- `uploaded` → `processing` → `completed` or `failed`

### 5. Review Status

**Endpoint**: `GET /api/uploads/{upload_id}/status`

**Response**:
```json
{
  "upload_id": "uuid-string",
  "status": "completed",
  "filename": "scorecard.jpg",
  "uploaded_at": "2025-11-10T12:00:00Z",
  "processed_at": "2025-11-10T12:00:15Z",
  "parsed_preview": {
    "game_id": "game-123",
    "team_a": "Team A",
    "team_b": "Team B",
    "deliveries": [...]
  },
  "error_message": null
}
```

Frontend polls this endpoint to monitor processing progress.

### 6. Apply Upload

**Endpoint**: `POST /api/uploads/{upload_id}/apply`

**Request**:
```json
{
  "upload_id": "uuid-string",
  "confirm": true
}
```

**Validation**:
- `confirm` must be `true` (explicit user confirmation)
- Status must be `completed`
- `parsed_preview` must be valid

**Process**:
1. Validates parsed data structure
2. Applies deliveries to game ledger
3. Updates status to `applied`
4. Records `applied_at` timestamp
5. Emits WebSocket event for live updates

## Configuration

### Environment Variables

```bash
# Feature Flags
CRICKSY_ENABLE_UPLOADS=1           # Enable upload feature
CRICKSY_ENABLE_OCR=1               # Enable OCR processing

# S3/MinIO Configuration
CRICKSY_S3_ENDPOINT_URL=http://localhost:9000  # MinIO dev (omit for AWS)
CRICKSY_S3_BUCKET=cricksy-uploads
CRICKSY_S3_REGION=us-east-1
CRICKSY_S3_ACCESS_KEY=minioadmin   # Use secrets in production
CRICKSY_S3_SECRET_KEY=minioadmin   # Use secrets in production
CRICKSY_S3_PRESIGNED_EXPIRY=3600   # URL expiry in seconds

# Celery/Redis
CRICKSY_CELERY_BROKER_URL=redis://localhost:6379/0
CRICKSY_CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Feature Flags

Both `ENABLE_UPLOADS` and `ENABLE_OCR` default to enabled (`1`) in development.

For production:
- Set `ENABLE_UPLOADS=0` to disable uploads entirely
- Set `ENABLE_OCR=0` to disable automatic processing (manual entry only)

## Development Setup

### MinIO (Local S3)

```bash
# Run MinIO in Docker
docker run -d \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"

# Create bucket
mc alias set local http://localhost:9000 minioadmin minioadmin
mc mb local/cricksy-uploads
mc anonymous set download local/cricksy-uploads
```

### Redis

```bash
# Run Redis in Docker
docker run -d -p 6379:6379 redis:7-alpine
```

### Celery Worker

```bash
cd backend
celery -A worker.celery_app worker --loglevel=info
```

## Production Setup

See `docs/DEPLOY_WORKER.md` for production deployment instructions.

## Security Considerations

### Presigned URLs

- URLs expire after `S3_PRESIGNED_EXPIRY` seconds (default: 1 hour)
- Direct client upload prevents backend processing load
- Content-Type is enforced in presigned URL

### Manual Review Required

- OCR results are stored in `parsed_preview` but NOT automatically applied
- User must explicitly review and confirm with `confirm=true`
- Apply endpoint validates data structure before persisting

### Secrets Management

- **NEVER** commit S3 credentials to version control
- Use environment variables or secret management service
- Rotate credentials regularly
- Use IAM roles in AWS for production

## Error Handling

### Upload Errors

- Invalid filename → 422 validation error
- S3 unavailable → 500 internal error
- Feature disabled → 503 service unavailable

### OCR Errors

- Download failure → status `failed`, error logged
- OCR failure → status `failed`, error in `error_message`
- Parse failure → status `failed`, partial results may be in `parsed_preview`

### Apply Errors

- Missing confirmation → 400 bad request
- Wrong status → 400 bad request
- Invalid data → 400 bad request
- Database error → 500 internal error

## Testing

### Unit Tests

```bash
cd backend
pytest tests/test_uploads.py
```

Unit tests mock S3 and do not require credentials.

### Integration Tests

Integration tests require environment variables:

```bash
export CRICKSY_S3_ACCESS_KEY=...
export CRICKSY_S3_SECRET_KEY=...
export CRICKSY_REDIS_URL=redis://localhost:6379/1

pytest tests/test_uploads.py
```

Without these variables, integration tests are automatically skipped.

## Monitoring

### Upload Metrics

- Track upload counts by status
- Monitor OCR success/failure rates
- Alert on high failure rates
- Monitor presigned URL usage

### Performance

- Presigned URL generation: < 100ms
- OCR processing: typically 5-30 seconds per image
- Apply operation: < 1 second

## Future Enhancements

1. **Batch Uploads**: Support multiple files in one request
2. **Image Preprocessing**: Auto-rotate, crop, enhance before OCR
3. **Confidence Scores**: Show OCR confidence for manual review
4. **Partial Apply**: Apply only reviewed/corrected fields
5. **Webhooks**: Notify external systems on completion
