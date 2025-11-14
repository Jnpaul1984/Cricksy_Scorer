# Upload Workflow Documentation

## Overview

The upload pipeline enables users to upload scorecard photos, PDFs, or videos, which are then processed via OCR to extract delivery data. This data is presented in a preview UI for manual verification before being applied to a match ledger.

## Architecture

```
Client → Initiate Upload → S3 Presigned URL
Client → Upload to S3 directly
Client → Complete Upload → Backend → Enqueue Processing Job
Worker → Download from S3 → OCR → Parse → Update DB
Client → Poll Status → Get Parsed Preview
Client → Review & Edit Preview
Client → Apply to Game → Persist Deliveries
```

## API Endpoints

### POST /api/uploads/initiate

Initiate a new upload and receive a presigned S3 URL for direct upload.

**Request:**
```json
{
  "filename": "scorecard.pdf",
  "file_type": "application/pdf",
  "game_id": "optional-game-id"
}
```

**Response:**
```json
{
  "upload_id": "uuid",
  "s3_key": "uploads/{upload_id}/{filename}",
  "presigned_url": "https://s3.amazonaws.com/...",
  "expires_in": 3600
}
```

### POST /api/uploads/complete

Mark an upload as complete and enqueue processing.

**Request:**
```json
{
  "upload_id": "uuid",
  "s3_key": "uploads/{upload_id}/{filename}",
  "size": 1024000,
  "checksum": "optional-md5"
}
```

**Response (202 Accepted):**
```json
{
  "upload_id": "uuid",
  "status": "processing",
  "message": "Upload complete, processing enqueued"
}
```

### GET /api/uploads/{upload_id}/status

Get the current status and parsed preview of an upload.

**Response:**
```json
{
  "upload_id": "uuid",
  "status": "ready",
  "filename": "scorecard.pdf",
  "file_type": "application/pdf",
  "game_id": "optional-game-id",
  "parsed_preview": {
    "deliveries": [
      {
        "over": 1,
        "ball": 1,
        "bowler": "Smith",
        "batsman": "Jones",
        "runs": 4,
        "is_wicket": false,
        "extras": 0
      }
    ],
    "metadata": {
      "total_deliveries": 120,
      "parser_version": "prototype_v1"
    }
  },
  "metadata": {
    "size": 1024000
  },
  "created_at": "2025-11-10T00:00:00Z",
  "updated_at": "2025-11-10T00:05:00Z"
}
```

### POST /api/uploads/{upload_id}/apply

Apply parsed deliveries to a game after manual verification.

**Request:**
```json
{
  "game_id": "target-game-id"
}
```

**Response:**
```json
{
  "upload_id": "uuid",
  "game_id": "target-game-id",
  "deliveries_applied": 120,
  "message": "Successfully applied 120 deliveries"
}
```

## Frontend Workflow

### 1. Upload Component

The `UploadScorecard.vue` component handles the initial upload:

1. User selects a file (photo/PDF/video)
2. Component calls `/api/uploads/initiate`
3. Component uploads file directly to S3 using presigned URL
4. Component calls `/api/uploads/complete`
5. Component redirects to review view

### 2. Review Component

The `UploadReview.vue` component handles preview and confirmation:

1. Poll `/api/uploads/{id}/status` until status is "ready"
2. Display parsed deliveries in editable table
3. Allow user to edit/correct parsed data
4. User confirms and clicks "Apply to Game"
5. Component calls `/api/uploads/{id}/apply`
6. Deliveries are persisted to match ledger

## Upload Status Flow

```
pending → processing → ready
                    ↘ failed
```

- **pending**: Upload initiated, waiting for file
- **processing**: Worker is processing the file
- **ready**: Processing complete, preview available
- **failed**: Processing failed, see metadata.error

## Configuration

### Environment Variables

```bash
# Feature flags
CRICKSY_ENABLE_UPLOADS=1
CRICKSY_ENABLE_OCR=1

# S3 Configuration
CRICKSY_S3_BUCKET=cricksy-uploads
CRICKSY_S3_REGION=us-east-1
CRICKSY_S3_ACCESS_KEY=your-access-key
CRICKSY_S3_SECRET_KEY=your-secret-key
CRICKSY_S3_ENDPOINT_URL=http://localhost:9000  # For MinIO

# URL Expiration
CRICKSY_PRESIGNED_URL_EXPIRATION=3600  # seconds

# Redis for worker
CRICKSY_REDIS_URL=redis://localhost:6379/0
```

### S3 / MinIO Setup

For local development, use MinIO:

```bash
# Run MinIO in Docker
docker run -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"

# Create bucket
aws --endpoint-url http://localhost:9000 \
  s3 mb s3://cricksy-uploads
```

## OCR Processing

### Supported File Types

- **Images**: PNG, JPEG, GIF (via Pillow + Tesseract)
- **PDFs**: Multi-page PDFs (via pdf2image + Tesseract)
- **Videos**: Not yet implemented (future enhancement)

### OCR Engine

Current prototype uses **Tesseract OCR**. For production, consider:
- PaddleOCR for better accuracy on scorecards
- Custom models trained on cricket scorecard formats

### Parser Logic

The `parse_scorecard.py` module uses rule-based pattern matching:

```python
# Pattern: Over.Ball Bowler Batsman Runs Wicket
# Example: "1.1 Smith Jones 4 No"
```

This is a **prototype parser** and should be enhanced for production with:
- More sophisticated pattern matching
- ML-based entity extraction
- Support for different scorecard formats
- Better error handling and validation

## Security Considerations

1. **Presigned URLs**: Limited expiration time (default 1 hour)
2. **File Size Limits**: Enforce max file size in frontend and S3 bucket policy
3. **MIME Type Validation**: Validate file types on upload
4. **Manual Verification**: Require human review before applying to ledger
5. **User Authentication**: TODO - Add auth checks to all endpoints
6. **Rate Limiting**: TODO - Add rate limits to prevent abuse

## Testing

### Unit Tests

Run upload API tests:

```bash
cd backend
pytest tests/test_uploads.py -v
```

### Integration Tests

Test full workflow with MinIO:

```bash
# Start MinIO
docker-compose up -d minio

# Enable uploads
export CRICKSY_ENABLE_UPLOADS=1
export CRICKSY_S3_ENDPOINT_URL=http://localhost:9000

# Run integration tests
pytest tests/integration/test_upload_workflow.py -v
```

### Manual Testing

1. Start backend with uploads enabled
2. Use Postman or curl to test endpoints
3. Upload a test scorecard image/PDF
4. Check worker logs for processing status
5. Verify parsed preview in status endpoint

## Troubleshooting

### Upload initiation fails

- Check S3 credentials are valid
- Verify bucket exists and is accessible
- Check presigned URL expiration settings

### Worker processing fails

- Check Redis connection
- Verify Celery worker is running
- Check worker logs for OCR errors
- Ensure Tesseract is installed: `sudo apt-get install tesseract-ocr`
- For PDFs, install poppler: `sudo apt-get install poppler-utils`

### OCR accuracy issues

- Ensure image quality is good (min 300 DPI)
- Try preprocessing images (contrast, rotation)
- Consider using PaddleOCR instead of Tesseract
- Train custom models on cricket scorecard data

## Future Enhancements

1. **Video Support**: Extract frames and run OCR on key frames
2. **Batch Upload**: Upload multiple scorecards at once
3. **Auto-correction**: ML model to suggest corrections
4. **Format Detection**: Auto-detect scorecard format and use appropriate parser
5. **Real-time Preview**: Stream OCR results as processing happens
6. **Collaborative Review**: Multiple users can review and edit preview
7. **Audit Trail**: Track all edits made during review
