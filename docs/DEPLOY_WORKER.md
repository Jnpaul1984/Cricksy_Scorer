# Worker Deployment Guide

## Overview

This guide covers deploying the Cricksy Scorer OCR worker system for production and development environments.

## Components

1. **Celery Worker** - Processes OCR tasks asynchronously
2. **Redis** - Message broker and result backend
3. **S3/MinIO** - Object storage for uploaded images
4. **Tesseract OCR** - Image text extraction engine
5. **PostgreSQL** - Database for upload tracking

## Environment Variables

### Required Variables

```bash
# Feature Flags
CRICKSY_ENABLE_UPLOADS=1           # Enable upload feature
CRICKSY_ENABLE_OCR=1               # Enable OCR processing

# Database
DATABASE_URL=postgresql://user:password@host:5432/dbname

# S3/MinIO Configuration
CRICKSY_S3_ENDPOINT_URL=           # Set for MinIO dev, omit for AWS S3
CRICKSY_S3_BUCKET=cricksy-uploads
CRICKSY_S3_REGION=us-east-1
CRICKSY_S3_ACCESS_KEY=<secret>     # Use AWS IAM or MinIO credentials
CRICKSY_S3_SECRET_KEY=<secret>     # NEVER commit these values
CRICKSY_S3_PRESIGNED_EXPIRY=3600   # URL expiry in seconds

# Celery/Redis
CRICKSY_CELERY_BROKER_URL=redis://redis-host:6379/0
CRICKSY_CELERY_RESULT_BACKEND=redis://redis-host:6379/0

# Redis for Socket.IO (Week 3)
CRICKSY_REDIS_URL=redis://redis-host:6379/1
CRICKSY_USE_REDIS_ADAPTER=1        # Enable for multi-server deployments
```

### Optional Variables

```bash
# Logging
CRICKSY_LOG_LEVEL=INFO             # DEBUG, INFO, WARNING, ERROR

# API Configuration
CRICKSY_API_TITLE=Cricksy Scorer API
CRICKSY_CORS_ORIGINS=https://yourdomain.com,https://www.yourdomain.com
```

## Development Setup

### 1. Install Dependencies

#### Backend

```bash
cd backend
pip install -r requirements.txt
```

Required system packages:
- Python 3.12+
- Tesseract OCR
- PostgreSQL client libraries

#### Install Tesseract OCR

**Ubuntu/Debian:**
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr libtesseract-dev
```

**macOS:**
```bash
brew install tesseract
```

**Windows:**
Download installer from: https://github.com/UB-Mannheim/tesseract/wiki

### 2. Start Redis

```bash
docker run -d -p 6379:6379 --name cricksy-redis redis:7-alpine
```

Or using Docker Compose:

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
```

### 3. Start MinIO (Development S3)

```bash
docker run -d \
  -p 9000:9000 \
  -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  --name cricksy-minio \
  minio/minio server /data --console-address ":9001"
```

Create the bucket:

```bash
# Install MinIO client
brew install minio/stable/mc  # or download from https://min.io/download

# Configure alias
mc alias set local http://localhost:9000 minioadmin minioadmin

# Create bucket
mc mb local/cricksy-uploads

# Set public read policy (for presigned URLs)
mc anonymous set download local/cricksy-uploads
```

### 4. Configure Environment

Create `.env` file in backend directory:

```bash
# Development environment
CRICKSY_ENABLE_UPLOADS=1
CRICKSY_ENABLE_OCR=1

DATABASE_URL=postgresql://postgres:password@localhost:5432/cricksy_scorer

CRICKSY_S3_ENDPOINT_URL=http://localhost:9000
CRICKSY_S3_BUCKET=cricksy-uploads
CRICKSY_S3_REGION=us-east-1
CRICKSY_S3_ACCESS_KEY=minioadmin
CRICKSY_S3_SECRET_KEY=minioadmin

CRICKSY_CELERY_BROKER_URL=redis://localhost:6379/0
CRICKSY_CELERY_RESULT_BACKEND=redis://localhost:6379/0

CRICKSY_REDIS_URL=redis://localhost:6379/1
CRICKSY_USE_REDIS_ADAPTER=0
```

### 5. Run Database Migrations

```bash
cd backend
alembic upgrade head
```

### 6. Start Celery Worker

```bash
cd backend
celery -A worker.celery_app worker --loglevel=info
```

For development with auto-reload:

```bash
celery -A worker.celery_app worker --loglevel=info --pool=solo
```

### 7. Start Backend API

```bash
cd backend
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### 8. Start Frontend

```bash
cd frontend
npm install
npm run dev
```

## Production Deployment

### 1. AWS S3 Setup

#### Create S3 Bucket

```bash
aws s3 mb s3://cricksy-uploads-prod --region us-east-1
```

#### Configure CORS

Create `cors.json`:

```json
{
  "CORSRules": [
    {
      "AllowedOrigins": ["https://yourdomain.com"],
      "AllowedMethods": ["GET", "PUT"],
      "AllowedHeaders": ["*"],
      "MaxAgeSeconds": 3600
    }
  ]
}
```

Apply CORS:

```bash
aws s3api put-bucket-cors --bucket cricksy-uploads-prod --cors-configuration file://cors.json
```

#### Create IAM User

Create an IAM user with this policy:

```json
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
```

Save the access key and secret key for environment variables.

### 2. Redis Deployment

#### Option A: Managed Redis (Recommended)

Use AWS ElastiCache, Redis Cloud, or similar:

```bash
CRICKSY_CELERY_BROKER_URL=redis://your-redis.cloud.redislabs.com:12345
CRICKSY_CELERY_RESULT_BACKEND=redis://your-redis.cloud.redislabs.com:12345
CRICKSY_REDIS_URL=redis://your-redis.cloud.redislabs.com:12345
```

#### Option B: Self-Hosted Redis

Deploy Redis with persistence:

```yaml
services:
  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    ports:
      - "6379:6379"
    volumes:
      - /data/redis:/data
    restart: unless-stopped
```

### 3. Celery Worker Deployment

#### Option A: Systemd Service

Create `/etc/systemd/system/cricksy-worker.service`:

```ini
[Unit]
Description=Cricksy Scorer Celery Worker
After=network.target redis.service postgresql.service

[Service]
Type=forking
User=cricksy
Group=cricksy
WorkingDirectory=/opt/cricksy/backend
EnvironmentFile=/opt/cricksy/backend/.env
ExecStart=/opt/cricksy/venv/bin/celery -A worker.celery_app worker \
  --loglevel=info \
  --concurrency=2 \
  --max-tasks-per-child=100 \
  --time-limit=300 \
  --soft-time-limit=270
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable cricksy-worker
sudo systemctl start cricksy-worker
sudo systemctl status cricksy-worker
```

#### Option B: Docker Container

```dockerfile
FROM python:3.12-slim

# Install Tesseract
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    libtesseract-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy application
WORKDIR /app
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

# Run worker
CMD ["celery", "-A", "worker.celery_app", "worker", "--loglevel=info"]
```

Docker Compose:

```yaml
services:
  celery-worker:
    build: .
    environment:
      - DATABASE_URL=postgresql://...
      - CRICKSY_CELERY_BROKER_URL=redis://redis:6379/0
      - CRICKSY_S3_ACCESS_KEY=${S3_ACCESS_KEY}
      - CRICKSY_S3_SECRET_KEY=${S3_SECRET_KEY}
    depends_on:
      - redis
      - postgres
    restart: unless-stopped
```

### 4. Monitoring

#### Celery Monitoring

Use Flower for web-based monitoring:

```bash
pip install flower
celery -A worker.celery_app flower --port=5555
```

#### Health Checks

Monitor these endpoints:

- `GET /api/health` - API health
- Redis connection check
- S3 connection check
- Worker queue length

#### Metrics to Track

- Upload count by status
- OCR success/failure rate
- Average processing time
- Worker queue depth
- Redis memory usage
- S3 storage usage

### 5. Scaling

#### Horizontal Scaling

Run multiple worker instances:

```bash
# Worker 1
celery -A worker.celery_app worker --hostname=worker1@%h

# Worker 2
celery -A worker.celery_app worker --hostname=worker2@%h
```

#### Concurrency

Adjust worker concurrency based on CPU:

```bash
celery -A worker.celery_app worker --concurrency=4
```

For I/O-bound tasks (OCR), use more workers than CPU cores.

## Security Considerations

### 1. Secrets Management

**Never commit secrets!** Use:

- Environment variables
- AWS Secrets Manager
- HashiCorp Vault
- Kubernetes Secrets

### 2. S3 Security

- Use bucket policies to restrict access
- Enable versioning for data recovery
- Enable server-side encryption
- Use VPC endpoints for AWS services
- Rotate IAM credentials regularly

### 3. Redis Security

- Enable password authentication
- Use TLS for connections
- Restrict network access
- Enable persistence for data durability

### 4. Rate Limiting

Implement rate limiting on upload endpoints:

```python
# Example using slowapi
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@app.post("/api/uploads/initiate")
@limiter.limit("10/minute")
async def initiate_upload(...):
    ...
```

## Troubleshooting

### Worker Not Processing Tasks

1. Check Redis connection:
   ```bash
   redis-cli ping
   ```

2. Check Celery can connect:
   ```bash
   celery -A worker.celery_app inspect ping
   ```

3. Check task queue:
   ```bash
   celery -A worker.celery_app inspect active
   ```

### OCR Failures

1. Verify Tesseract is installed:
   ```bash
   tesseract --version
   ```

2. Check image download from S3:
   - Verify S3 credentials
   - Check presigned URL expiry
   - Verify network connectivity

3. Check worker logs:
   ```bash
   celery -A worker.celery_app events
   ```

### Database Connection Issues

1. Check DATABASE_URL format:
   - Async: `postgresql+asyncpg://...`
   - Sync (worker): `postgresql://...`

2. Verify database connectivity:
   ```bash
   psql $DATABASE_URL -c "SELECT 1"
   ```

## Backup and Recovery

### Database Backups

```bash
pg_dump -h localhost -U postgres cricksy_scorer > backup.sql
```

### Redis Backups

Redis automatically persists to disk (if configured). Copy RDB file:

```bash
cp /var/lib/redis/dump.rdb /backups/redis-$(date +%Y%m%d).rdb
```

### S3 Backups

Enable versioning and cross-region replication in AWS S3 console.

## Performance Tuning

### Celery

```python
# celery_app.py
celery_app.conf.update(
    task_time_limit=300,           # 5 minutes max
    task_soft_time_limit=270,      # Soft limit at 4.5 minutes
    worker_prefetch_multiplier=1,  # Process one task at a time
    worker_max_tasks_per_child=100,# Restart worker after 100 tasks
)
```

### Redis

```
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru
```

### S3

- Use CloudFront CDN for frequently accessed images
- Enable Transfer Acceleration for faster uploads
- Use multipart uploads for large files

## Support

For issues or questions:
- Check logs: `journalctl -u cricksy-worker -f`
- Review Celery docs: https://docs.celeryq.dev/
- Review project docs: `docs/UPLOAD_WORKFLOW.md`
