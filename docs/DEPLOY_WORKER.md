# OCR Worker Deployment Guide

This document describes how to deploy and run the Celery OCR worker for processing scorecard uploads.

## Prerequisites

- Python 3.12+
- Redis server running
- S3 or MinIO accessible
- Tesseract OCR installed on worker machine
- PostgreSQL database (same as backend)

## Environment Variables

All environment variables from `backend/config.py` must be set. Key variables for workers:

### Required
```bash
# Database
DATABASE_URL=postgresql+asyncpg://user:pass@host:5432/cricksy

# Redis/Celery
CRICKSY_REDIS_URL=redis://localhost:6379/0
CRICKSY_CELERY_BROKER_URL=redis://localhost:6379/0
CRICKSY_CELERY_RESULT_BACKEND=redis://localhost:6379/0

# S3/MinIO
CRICKSY_S3_ENDPOINT_URL=http://localhost:9000  # MinIO dev, leave empty for AWS
CRICKSY_S3_ACCESS_KEY=your-access-key
CRICKSY_S3_SECRET_KEY=your-secret-key
CRICKSY_S3_BUCKET=cricksy-uploads
CRICKSY_S3_REGION=us-east-1

# Feature flags
CRICKSY_ENABLE_UPLOADS=1
CRICKSY_ENABLE_OCR=1
```

### Optional
```bash
# Logging
CRICKSY_LOG_LEVEL=INFO  # DEBUG, INFO, WARNING, ERROR
```

## Installing Tesseract

### Ubuntu/Debian
```bash
sudo apt-get update
sudo apt-get install -y tesseract-ocr tesseract-ocr-eng
```

### macOS
```bash
brew install tesseract
```

### Windows
Download installer from: https://github.com/UB-Mannheim/tesseract/wiki

### Docker
```dockerfile
FROM python:3.12-slim

# Install Tesseract
RUN apt-get update && \
    apt-get install -y tesseract-ocr tesseract-ocr-eng && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copy and install requirements
COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy worker code
COPY backend /app/backend
WORKDIR /app

CMD ["celery", "-A", "backend.worker.celery_app", "worker", "--loglevel=info", "-Q", "ocr"]
```

## Running the Worker

### Development (Local)

1. **Start Redis:**
```bash
# Using Docker
docker run -d -p 6379:6379 redis:7-alpine

# Or install locally
# Ubuntu: sudo apt-get install redis-server && redis-server
# macOS: brew install redis && redis-server
```

2. **Start MinIO (for dev):**
```bash
docker run -d -p 9000:9000 -p 9001:9001 \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"
```

3. **Install dependencies:**
```bash
cd backend
pip install -r requirements.txt
```

4. **Start worker:**
```bash
cd /path/to/Cricksy_Scorer
celery -A backend.worker.celery_app worker --loglevel=info -Q ocr
```

**Output should show:**
```
[tasks]
  . backend.worker.processor.process_upload_task

[2025-11-10 00:00:00,000: INFO/MainProcess] Connected to redis://localhost:6379/0
[2025-11-10 00:00:00,000: INFO/MainProcess] celery@hostname ready.
```

### Production

#### Using systemd (Linux)

Create `/etc/systemd/system/cricksy-worker.service`:

```ini
[Unit]
Description=Cricksy OCR Worker
After=network.target redis.service

[Service]
Type=forking
User=cricksy
Group=cricksy
WorkingDirectory=/opt/cricksy
Environment="PATH=/opt/cricksy/venv/bin"
EnvironmentFile=/opt/cricksy/.env
ExecStart=/opt/cricksy/venv/bin/celery -A backend.worker.celery_app worker \
    --loglevel=info \
    -Q ocr \
    --pidfile=/var/run/cricksy-worker.pid \
    --logfile=/var/log/cricksy/worker.log \
    --detach

Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**Enable and start:**
```bash
sudo systemctl daemon-reload
sudo systemctl enable cricksy-worker
sudo systemctl start cricksy-worker
sudo systemctl status cricksy-worker
```

#### Using Docker Compose

Add to `docker-compose.yml`:

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data

  minio:
    image: minio/minio
    ports:
      - "9000:9000"
      - "9001:9001"
    environment:
      MINIO_ROOT_USER: minioadmin
      MINIO_ROOT_PASSWORD: minioadmin
    command: server /data --console-address ":9001"
    volumes:
      - minio-data:/data

  worker:
    build:
      context: .
      dockerfile: Dockerfile.worker
    depends_on:
      - redis
      - db
      - minio
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:postgres@db:5432/cricksy
      CRICKSY_REDIS_URL: redis://redis:6379/0
      CRICKSY_CELERY_BROKER_URL: redis://redis:6379/0
      CRICKSY_CELERY_RESULT_BACKEND: redis://redis:6379/0
      CRICKSY_S3_ENDPOINT_URL: http://minio:9000
      CRICKSY_S3_ACCESS_KEY: minioadmin
      CRICKSY_S3_SECRET_KEY: minioadmin
      CRICKSY_S3_BUCKET: cricksy-uploads
      CRICKSY_ENABLE_UPLOADS: 1
      CRICKSY_ENABLE_OCR: 1
    command: celery -A backend.worker.celery_app worker --loglevel=info -Q ocr

volumes:
  redis-data:
  minio-data:
```

**Start:**
```bash
docker-compose up -d worker
```

## Monitoring

### Check Worker Status

```bash
# Using Celery inspect
celery -A backend.worker.celery_app inspect active
celery -A backend.worker.celery_app inspect stats
celery -A backend.worker.celery_app inspect registered
```

### View Logs

```bash
# systemd
sudo journalctl -u cricksy-worker -f

# Docker
docker-compose logs -f worker
```

### Redis Queue Status

```bash
# Connect to Redis
redis-cli

# Check queue length
LLEN ocr

# View pending tasks
LRANGE ocr 0 -1
```

## Scaling Workers

### Multiple Workers (Same Machine)

```bash
# Start 4 worker processes
celery -A backend.worker.celery_app worker --loglevel=info -Q ocr --concurrency=4
```

### Multiple Worker Machines

Run the same worker command on multiple machines, all connecting to the same Redis broker. Celery will automatically distribute tasks.

### Auto-scaling

```bash
# Auto-scale between 2 and 10 workers based on load
celery -A backend.worker.celery_app worker --loglevel=info -Q ocr --autoscale=10,2
```

## Task Monitoring with Flower

Install Flower for web-based monitoring:

```bash
pip install flower
```

Run:
```bash
celery -A backend.worker.celery_app flower --port=5555
```

Access at: http://localhost:5555

## Troubleshooting

### Worker Not Processing Tasks

1. **Check Redis connection:**
```bash
redis-cli ping
# Should return: PONG
```

2. **Verify worker is running:**
```bash
celery -A backend.worker.celery_app inspect active
```

3. **Check queue has tasks:**
```bash
redis-cli LLEN ocr
```

### Tesseract Errors

1. **Verify Tesseract is installed:**
```bash
tesseract --version
```

2. **Check language data:**
```bash
tesseract --list-langs
# Should include 'eng'
```

3. **Test Tesseract:**
```bash
echo "Test" | tesseract stdin stdout
```

### S3/MinIO Connection Errors

1. **Test S3 connection:**
```python
from backend.utils.s3 import get_s3_client
client = get_s3_client()
client.list_buckets()
```

2. **Verify bucket exists:**
```bash
aws s3 ls s3://cricksy-uploads --endpoint-url http://localhost:9000
```

### High Memory Usage

OCR processing can be memory-intensive. Limit concurrent tasks:

```bash
celery -A backend.worker.celery_app worker -Q ocr --concurrency=2 --max-tasks-per-child=100
```

### Failed Tasks Retrying Forever

Set max retries in `backend/worker/processor.py`:
```python
@app.task(bind=True, max_retries=3, default_retry_delay=60)
```

## Performance Tuning

### Prefetch Multiplier

Control how many tasks a worker prefetches:

```bash
# Default is 4, set to 1 for long-running tasks
celery -A backend.worker.celery_app worker -Q ocr --prefetch-multiplier=1
```

### Task Acknowledgment

Tasks are acknowledged late (after completion) to prevent loss on worker crash:
```python
# In celery_app.py
task_acks_late=True
```

### Result Backend

For task result tracking, Redis is used. For production, consider separate Redis instance:

```bash
CRICKSY_CELERY_RESULT_BACKEND=redis://redis-results:6379/0
```

## Security

### Production Checklist

- [ ] Use strong Redis password: `redis-server --requirepass yourpassword`
- [ ] Use TLS for Redis in production
- [ ] Restrict S3 bucket access to worker IAM role (AWS) or credentials (MinIO)
- [ ] Run worker as non-root user
- [ ] Use environment files with restricted permissions (chmod 600)
- [ ] Enable Celery result encryption for sensitive data
- [ ] Set up log rotation for worker logs
- [ ] Monitor failed task rate and set up alerts

## Maintenance

### Purging Failed Tasks

```bash
# Remove all failed tasks
celery -A backend.worker.celery_app purge
```

### Graceful Shutdown

```bash
# Send TERM signal, wait for current tasks to finish
celery -A backend.worker.celery_app control shutdown

# Or with systemd
sudo systemctl stop cricksy-worker
```

### Updating Worker Code

1. Stop worker gracefully
2. Update code
3. Restart worker
4. Verify with: `celery -A backend.worker.celery_app inspect registered`

## Metrics & Alerting

Key metrics to monitor:

- Task success/failure rate
- Task execution time (p50, p95, p99)
- Queue depth
- Worker memory usage
- Redis memory usage
- S3 API latency

Set up alerts for:
- High failure rate (>10%)
- High queue depth (>100 tasks)
- Worker down
- High processing time (>5 minutes)

## Backup & Recovery

### Task Queue Persistence

Redis persistence is enabled by default. For critical deployments:

1. Use Redis AOF (append-only file): `appendonly yes`
2. Regular Redis snapshots
3. Replicate Redis for high availability

### Failed Task Recovery

Failed tasks are stored in result backend. Implement retry logic:

```python
# Manual retry from Python shell
from backend.worker.processor import process_upload_task
process_upload_task.apply_async(args=['upload-id-here'])
```

## Support

For issues:
1. Check worker logs
2. Check Redis logs
3. Check Tesseract installation
4. Review environment variables
5. Test S3 connectivity
6. Check database connectivity

See also:
- `docs/UPLOAD_WORKFLOW.md` - Upload workflow documentation
- `backend/worker/processor.py` - Worker implementation
- `backend/worker/celery_app.py` - Celery configuration
