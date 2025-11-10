# Worker Deployment Guide

## Overview

The Cricksy Scorer OCR worker processes uploaded scorecard files (photos, PDFs) and extracts delivery data using OCR and pattern matching. This guide covers deployment and operation of the worker infrastructure.

## Architecture

```
┌─────────────┐     ┌──────────┐     ┌─────────────┐
│   FastAPI   │────▶│  Redis   │────▶│   Celery    │
│   Backend   │     │  Broker  │     │   Worker    │
└─────────────┘     └──────────┘     └─────────────┘
                                            │
                                            ▼
                                      ┌──────────┐
                                      │    S3    │
                                      └──────────┘
```

## Components

### 1. Redis Broker

Redis serves as the message broker for Celery, queuing processing jobs.

### 2. Celery Worker

Python process that:
- Pulls jobs from Redis queue
- Downloads files from S3
- Runs OCR (Tesseract/PaddleOCR)
- Parses scorecard data
- Updates database with results

### 3. Backend API

FastAPI application that:
- Creates upload records
- Generates presigned URLs
- Enqueues processing jobs
- Serves parsed results

## Prerequisites

### System Dependencies

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y \
  tesseract-ocr \
  poppler-utils \
  redis-server

# macOS
brew install tesseract poppler redis
```

### Python Dependencies

Already in `requirements.txt`:
- `celery==5.3.4`
- `redis==5.0.1`
- `pillow==10.2.0`
- `pytesseract==0.3.10`
- `pdf2image==1.17.0`
- `boto3==1.34.34`

## Local Development Setup

### 1. Start Redis

```bash
# Option A: Docker
docker run -d --name redis -p 6379:6379 redis:7-alpine

# Option B: System service
sudo systemctl start redis
```

### 2. Configure Environment

```bash
export CRICKSY_ENABLE_UPLOADS=1
export CRICKSY_ENABLE_OCR=1
export CRICKSY_REDIS_URL=redis://localhost:6379/0

# S3 Configuration (or use MinIO for local dev)
export CRICKSY_S3_BUCKET=cricksy-uploads
export CRICKSY_S3_REGION=us-east-1
export CRICKSY_S3_ACCESS_KEY=your-key
export CRICKSY_S3_SECRET_KEY=your-secret
export CRICKSY_S3_ENDPOINT_URL=http://localhost:9000  # MinIO
```

### 3. Start Celery Worker

```bash
cd backend

# Single worker for development
celery -A backend.worker.celery_app worker \
  --loglevel=info \
  --concurrency=2

# With automatic reload on code changes
watchmedo auto-restart \
  --directory=./backend \
  --pattern='*.py' \
  --recursive \
  -- celery -A backend.worker.celery_app worker --loglevel=info
```

### 4. Start FastAPI Backend

```bash
cd backend
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. Test the Pipeline

```bash
# Upload a test file
curl -X POST http://localhost:8000/api/uploads/initiate \
  -H "Content-Type: application/json" \
  -d '{"filename": "test.pdf", "file_type": "application/pdf"}'

# Use returned presigned URL to upload file
# Then complete the upload
curl -X POST http://localhost:8000/api/uploads/complete \
  -H "Content-Type: application/json" \
  -d '{"upload_id": "...", "s3_key": "...", "size": 1024}'

# Check status (poll until ready)
curl http://localhost:8000/api/uploads/{upload_id}/status
```

## Production Deployment

### Docker Compose

Example `docker-compose.yml` addition:

```yaml
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    command: redis-server --appendonly yes

  celery-worker:
    build: ./backend
    command: celery -A backend.worker.celery_app worker --loglevel=info --concurrency=4
    environment:
      - CRICKSY_ENABLE_UPLOADS=1
      - CRICKSY_ENABLE_OCR=1
      - CRICKSY_REDIS_URL=redis://redis:6379/0
      - CRICKSY_S3_BUCKET=${S3_BUCKET}
      - CRICKSY_S3_REGION=${S3_REGION}
      - CRICKSY_S3_ACCESS_KEY=${S3_ACCESS_KEY}
      - CRICKSY_S3_SECRET_KEY=${S3_SECRET_KEY}
      - DATABASE_URL=${DATABASE_URL}
    depends_on:
      - redis
      - db
    volumes:
      - ./backend:/app/backend

  backend:
    build: ./backend
    command: uvicorn backend.main:app --host 0.0.0.0 --port 8000
    environment:
      - CRICKSY_ENABLE_UPLOADS=1
      - CRICKSY_REDIS_URL=redis://redis:6379/0
      # ... other env vars
    depends_on:
      - redis
      - db
    ports:
      - "8000:8000"

volumes:
  redis-data:
```

### Kubernetes Deployment

```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: celery-worker
spec:
  replicas: 3
  selector:
    matchLabels:
      app: celery-worker
  template:
    metadata:
      labels:
        app: celery-worker
    spec:
      containers:
      - name: worker
        image: cricksy-backend:latest
        command: ["celery", "-A", "backend.worker.celery_app", "worker", "--loglevel=info"]
        env:
        - name: CRICKSY_ENABLE_OCR
          value: "1"
        - name: CRICKSY_REDIS_URL
          valueFrom:
            secretKeyRef:
              name: cricksy-secrets
              key: redis-url
        resources:
          requests:
            memory: "512Mi"
            cpu: "500m"
          limits:
            memory: "2Gi"
            cpu: "2000m"
```

## Monitoring

### Celery Flower

Monitor worker health and tasks:

```bash
# Install Flower
pip install flower

# Run Flower dashboard
celery -A backend.worker.celery_app flower --port=5555

# Access dashboard
open http://localhost:5555
```

### Metrics to Monitor

1. **Queue Length**: Number of pending jobs
2. **Task Success Rate**: Percentage of successful vs failed tasks
3. **Processing Time**: Average time per task
4. **Worker Health**: Number of active workers
5. **Memory Usage**: Worker memory consumption
6. **OCR Accuracy**: Deliveries extracted per upload

### Logging

Workers log to stdout/stderr. Configure log aggregation:

```python
# In celery_app.py
import logging
from pythonjsonlogger import jsonlogger

logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
logHandler.setFormatter(formatter)
celery_app.log.setup_loggers(loglevel='INFO', logfile=None)
```

## Scaling

### Horizontal Scaling

Add more worker instances:

```bash
# Docker Compose
docker-compose up -d --scale celery-worker=5

# Kubernetes
kubectl scale deployment celery-worker --replicas=5
```

### Concurrency Tuning

Adjust per-worker concurrency:

```bash
# More concurrent tasks per worker
celery -A backend.worker.celery_app worker --concurrency=8

# Use eventlet for I/O-bound tasks
celery -A backend.worker.celery_app worker --pool=eventlet --concurrency=100
```

### Queue Prioritization

Configure separate queues for urgent vs batch processing:

```python
# In processor.py
@celery_app.task(queue='high_priority')
def process_urgent_upload(upload_id: str):
    ...

@celery_app.task(queue='low_priority')
def process_batch_upload(upload_id: str):
    ...
```

Run dedicated workers per queue:

```bash
celery -A backend.worker.celery_app worker -Q high_priority --concurrency=4
celery -A backend.worker.celery_app worker -Q low_priority --concurrency=2
```

## Troubleshooting

### Worker Won't Start

```bash
# Check Redis connection
redis-cli ping

# Verify Python environment
python -c "from backend.worker.celery_app import celery_app; print(celery_app)"

# Check for import errors
python -m backend.worker.processor
```

### Tasks Failing

```bash
# View Celery logs
celery -A backend.worker.celery_app events

# Inspect failed tasks
celery -A backend.worker.celery_app inspect active
celery -A backend.worker.celery_app inspect reserved

# Retry failed tasks
celery -A backend.worker.celery_app inspect scheduled
```

### OCR Issues

```bash
# Verify Tesseract installation
tesseract --version

# Test Tesseract on sample image
tesseract sample.jpg output.txt

# Check Poppler (for PDFs)
pdfinfo --version
pdftoppm --version
```

### Memory Issues

Workers consuming too much memory:

```bash
# Reduce concurrency
celery -A backend.worker.celery_app worker --concurrency=2

# Enable worker restart after N tasks
celery -A backend.worker.celery_app worker --max-tasks-per-child=10

# Monitor memory
watch -n 1 "ps aux | grep celery"
```

## Security Best Practices

1. **Isolate Workers**: Run workers in separate network namespace
2. **Limit Resources**: Use cgroups/containers to limit CPU/memory
3. **Secure Redis**: Use password auth, disable dangerous commands
4. **Validate Inputs**: Sanitize file paths and S3 keys
5. **Secrets Management**: Use environment variables or secret managers
6. **Network Policies**: Restrict worker network access

## Performance Optimization

### 1. Image Preprocessing

Improve OCR accuracy with preprocessing:

```python
from PIL import Image, ImageEnhance

def preprocess_image(image):
    # Convert to grayscale
    image = image.convert('L')
    
    # Increase contrast
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2.0)
    
    # Increase sharpness
    enhancer = ImageEnhance.Sharpness(image)
    image = enhancer.enhance(2.0)
    
    return image
```

### 2. Parallel Page Processing

Process PDF pages in parallel:

```python
from concurrent.futures import ThreadPoolExecutor

def process_pdf_parallel(images):
    with ThreadPoolExecutor(max_workers=4) as executor:
        results = list(executor.map(_run_ocr_on_image, images))
    return "\n\n".join(results)
```

### 3. Caching

Cache parsed results for duplicate uploads:

```python
import hashlib

def get_cache_key(s3_key: str, checksum: str) -> str:
    return f"parsed:{hashlib.md5(f'{s3_key}:{checksum}'.encode()).hexdigest()}"
```

## Backup and Recovery

### Redis Backup

```bash
# Enable AOF persistence
redis-cli CONFIG SET appendonly yes

# Take snapshot
redis-cli BGSAVE

# Copy RDB file
cp /var/lib/redis/dump.rdb /backup/
```

### Failed Task Recovery

```python
# Retry failed tasks from last 24 hours
from datetime import datetime, timedelta
from celery.result import AsyncResult

# Query failed tasks
failed_tasks = celery_app.control.inspect().failed()
for worker, tasks in failed_tasks.items():
    for task_id in tasks:
        result = AsyncResult(task_id)
        # Retry if failed < 3 times
        if result.retries < 3:
            result.retry()
```

## Additional Resources

- [Celery Documentation](https://docs.celeryq.dev/)
- [Redis Documentation](https://redis.io/documentation)
- [Tesseract Documentation](https://tesseract-ocr.github.io/)
- [PaddleOCR Documentation](https://github.com/PaddlePaddle/PaddleOCR)
