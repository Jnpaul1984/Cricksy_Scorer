# Upload Workflow Documentation

This document describes the upload and OCR workflow for processing scorecard images and documents.

## Overview

The upload feature allows users to upload scorecard images (photos, PDFs, etc.) which are then processed using OCR (Optical Character Recognition) to extract match data. Users can review and verify the extracted data before applying it to the game ledger.

## Architecture

```
┌─────────┐      ┌──────────┐      ┌─────────┐      ┌──────────┐
│ Frontend│─────▶│ FastAPI  │─────▶│ S3/MinIO│      │  Celery  │
│         │      │ Backend  │      │         │      │  Worker  │
└─────────┘      └──────────┘      └─────────┘      └──────────┘
                       │                                    │
                       │            ┌──────────┐            │
                       └───────────▶│PostgreSQL│◀───────────┘
                                    └──────────┘
```

## Workflow Steps

### 1. Initiate Upload

**Endpoint**: `POST /api/uploads/initiate`

**Request**:
```json
{
  "filename": "scorecard.jpg",
  "content_type": "image/jpeg",
  "file_size": 102400,
  "uploader_name": "John Smith",
  "uploader_session_id": "abc123"
}
```

**Response**:
```json
{
  "upload_id": "uuid-here",
  "upload_url": "https://s3.../presigned-url",
  "upload_method": "PUT",
  "expires_in": 3600,
  "s3_key": "uploads/uuid-here/scorecard.jpg",
  "s3_bucket": "cricksy-uploads"
}
```

**What happens**:
- Backend creates Upload record in `pending` state
- Generates presigned S3/MinIO URL for direct upload
- Returns URL to frontend

### 2. Upload File

**Action**: Frontend uploads file directly to S3/MinIO using presigned URL

**Method**: `PUT` to presigned URL with file content

**Note**: This happens client-side, bypassing the backend for efficient large file uploads.

### 3. Complete Upload

**Endpoint**: `POST /api/uploads/complete`

**Request**:
```json
{
  "upload_id": "uuid-here"
}
```

**Response**:
```json
{
  "upload_id": "uuid-here",
  "status": "uploaded",
  "message": "Upload complete, processing queued"
}
```

**What happens**:
- Backend updates status to `uploaded`
- Queues Celery task for OCR processing (if `ENABLE_OCR=true`)
- Returns immediately (processing is async)

### 4. Processing (Background)

**Worker Task**: `process_scorecard_task`

**Process**:
1. Update status to `processing`
2. Download image from S3/MinIO
3. Run Tesseract OCR to extract text
4. Parse text into structured data (prototype-level)
5. Update status to `parsed` (or `failed` on error)

**Note**: This happens asynchronously in a Celery worker.

### 5. Poll Status

**Endpoint**: `GET /api/uploads/status/{upload_id}`

**Response**:
```json
{
  "upload_id": "uuid-here",
  "status": "parsed",
  "filename": "scorecard.jpg",
  "created_at": "2024-11-10T10:00:00Z",
  "updated_at": "2024-11-10T10:01:30Z",
  "processed_at": "2024-11-10T10:01:30Z",
  "parsed_data": {
    "teams": [
      {"name": "Team A"},
      {"name": "Team B"}
    ],
    "innings": [
      {"runs": 250, "wickets": 8}
    ],
    "parse_notes": ["Manual verification required"]
  }
}
```

**What happens**:
- Frontend polls this endpoint to check processing status
- When status is `parsed`, displays `parsed_data` for review

### 6. Review and Apply

**Endpoint**: `POST /api/uploads/apply`

**Request**:
```json
{
  "upload_id": "uuid-here",
  "game_id": "game-uuid-here",
  "confirmation": true
}
```

**Response**:
```json
{
  "upload_id": "uuid-here",
  "status": "applied",
  "game_id": "game-uuid-here",
  "message": "Upload data applied successfully"
}
```

**What happens**:
- Validates user confirmation
- Validates upload is in `parsed` state
- Applies parsed data to game ledger (TODO: implement)
- Updates status to `applied`
- Emits WebSocket event for live updates (TODO: implement)

## Configuration

### Environment Variables

#### S3/MinIO Configuration
```bash
# For MinIO (development)
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_USE_PATH_STYLE=1
S3_UPLOAD_BUCKET=cricksy-uploads

# For AWS S3 (production)
S3_ENDPOINT_URL=  # Leave empty for AWS
S3_ACCESS_KEY_ID=your-aws-key
S3_SECRET_ACCESS_KEY=your-aws-secret
S3_REGION=us-east-1
S3_UPLOAD_BUCKET=cricksy-prod-uploads
```

#### Feature Flags
```bash
ENABLE_UPLOADS=1  # Enable/disable upload feature
ENABLE_OCR=1      # Enable/disable OCR processing
```

#### Upload Limits
```bash
MAX_UPLOAD_SIZE_MB=10  # Maximum file size in MB
```

#### Worker Configuration
```bash
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

## Database Schema

### uploads table

| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| uploader_name | VARCHAR(255) | Optional user name |
| uploader_session_id | VARCHAR(255) | Optional session ID |
| filename | VARCHAR(512) | Original filename |
| content_type | VARCHAR(128) | MIME type |
| file_size | INTEGER | Size in bytes |
| s3_key | VARCHAR(1024) | S3 object key |
| s3_bucket | VARCHAR(255) | S3 bucket name |
| status | VARCHAR(50) | Workflow status (enum) |
| parsed_data | JSONB | OCR results |
| error_message | TEXT | Error details if failed |
| game_id | UUID | Link to game (when applied) |
| created_at | TIMESTAMP | Creation time |
| updated_at | TIMESTAMP | Last update time |
| processed_at | TIMESTAMP | When OCR completed |
| applied_at | TIMESTAMP | When applied to ledger |

## Status Flow

```
pending → uploaded → processing → parsed → applied
                         │           │
                         └──failed   └──rejected
```

## OCR Processing (Prototype)

The current OCR implementation is **prototype-level** and requires **manual verification**.

### Limitations
- Basic text extraction only
- No advanced image preprocessing
- Simple pattern matching for parsing
- Low confidence scores
- Requires manual review before applying

### Future Improvements
- Advanced image preprocessing (deskew, denoise, contrast adjustment)
- ML-based entity recognition
- Support for multiple scorecard formats
- Confidence scoring
- Automated validation against cricket rules
- Support for handwritten scorecards

## Security Considerations

### Upload Validation
- File size limits enforced (default: 10MB)
- Content type validation recommended
- Presigned URLs expire after 1 hour
- User confirmation required before applying data

### Data Privacy
- Uploaded files stored in private S3/MinIO bucket
- Access controlled via IAM/bucket policies
- Parsed data includes user consent tracking
- See `docs/AI_ETHICS.md` for privacy policies

### Error Handling
- Failed uploads don't block system
- Errors logged but not exposed to unauthorized users
- Graceful degradation when S3/OCR unavailable

## Testing

### Unit Tests
Run upload tests:
```bash
cd backend
pytest tests/test_uploads.py -v
```

### Integration Tests
Test with real S3/MinIO:
```bash
# Set credentials
export S3_ACCESS_KEY_ID=...
export S3_SECRET_ACCESS_KEY=...

# Run tests
pytest tests/test_uploads.py -v
```

Tests skip automatically if credentials not set (CI-safe).

### Manual Testing
1. Start MinIO locally (see DEPLOY_WORKER.md)
2. Start backend: `uvicorn backend.main:app --reload`
3. Start Celery worker: `celery -A backend.worker.celery_app worker --loglevel=info`
4. Use frontend or curl to test workflow

## Troubleshooting

### Upload fails with 503
- Check `ENABLE_UPLOADS` feature flag
- Verify S3/MinIO credentials
- Check S3 bucket exists and is accessible

### OCR not processing
- Check `ENABLE_OCR` feature flag
- Verify Celery worker is running
- Check Redis connection
- Verify Tesseract is installed

### Presigned URL errors
- Check S3 endpoint URL configuration
- Verify IAM permissions for S3
- Check bucket CORS configuration

### Worker errors
- Check Celery logs: `celery -A backend.worker.celery_app worker --loglevel=debug`
- Verify database connection from worker
- Check Tesseract installation: `tesseract --version`

## Related Documentation
- `DEPLOY_WORKER.md`: Worker deployment guide
- `AI_ETHICS.md`: Privacy and ethics policies
- API docs: http://localhost:8000/docs
