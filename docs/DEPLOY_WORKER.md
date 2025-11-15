# Worker Deployment Guide

This guide covers deploying and running Celery workers for background OCR processing.

## Architecture

The worker system uses:
- **Celery**: Distributed task queue
- **Redis**: Message broker and result backend
- **Tesseract**: OCR engine
- **S3/MinIO**: File storage

## Prerequisites

### System Requirements
- Python 3.10+
- Redis server
- Tesseract OCR engine
- Access to S3 or MinIO

### Install Tesseract

**Ubuntu/Debian**:
```bash
sudo apt-get update
sudo apt-get install tesseract-ocr tesseract-ocr-eng
```

**macOS**:
```bash
brew install tesseract
```

**Windows**:
Download installer from: https://github.com/UB-Mannheim/tesseract/wiki

Verify installation:
```bash
tesseract --version
```

### Install Redis

**Ubuntu/Debian**:
```bash
sudo apt-get install redis-server
sudo systemctl start redis
```

**macOS**:
```bash
brew install redis
brew services start redis
```

**Docker** (recommended for development):
```bash
docker run -d -p 6379:6379 --name redis redis:7-alpine
```

Verify Redis:
```bash
redis-cli ping
# Should return: PONG
```

## Development Setup

### 1. Install Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 2. Configure Environment

Create `.env` file or export variables:

```bash
# Database
DATABASE_URL=postgresql+asyncpg://postgres:password@localhost:5432/cricksy_scorer

# Redis (Celery)
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0

# S3/MinIO (Development)
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_USE_PATH_STYLE=1
S3_UPLOAD_BUCKET=cricksy-uploads

# Feature Flags
ENABLE_UPLOADS=1
ENABLE_OCR=1
```

### 3. Start MinIO (Development)

**Using Docker**:
```bash
docker run -d \
  -p 9000:9000 \
  -p 9001:9001 \
  --name minio \
  -e MINIO_ROOT_USER=minioadmin \
  -e MINIO_ROOT_PASSWORD=minioadmin \
  minio/minio server /data --console-address ":9001"
```

**Create bucket**:
1. Open MinIO console: http://localhost:9001
2. Login with `minioadmin` / `minioadmin`
3. Create bucket named `cricksy-uploads`
4. Set bucket policy to allow uploads (or use presigned URLs)

### 4. Start Celery Worker

**Single worker**:
```bash
cd backend
celery -A backend.worker.celery_app worker --loglevel=info
```

**With concurrency**:
```bash
celery -A backend.worker.celery_app worker --loglevel=info --concurrency=4
```

**With auto-reload (development)**:
```bash
celery -A backend.worker.celery_app worker --loglevel=info --autoreload
```

### 5. Monitor Worker

**Celery Flower** (web-based monitoring):
```bash
pip install flower
celery -A backend.worker.celery_app flower
# Open http://localhost:5555
```

**Redis CLI**:
```bash
redis-cli monitor
```

## Production Deployment

### Using Systemd (Linux)

Create `/etc/systemd/system/cricksy-worker.service`:

```ini
[Unit]
Description=Cricksy Scorer Celery Worker
After=network.target redis.service

[Service]
Type=forking
User=cricksy
Group=cricksy
WorkingDirectory=/opt/cricksy/backend
Environment="PATH=/opt/cricksy/venv/bin"
Environment="DATABASE_URL=postgresql+asyncpg://..."
Environment="CELERY_BROKER_URL=redis://..."
Environment="S3_ACCESS_KEY_ID=..."
Environment="S3_SECRET_ACCESS_KEY=..."
ExecStart=/opt/cricksy/venv/bin/celery -A backend.worker.celery_app worker \
    --loglevel=info \
    --concurrency=4 \
    --pidfile=/var/run/cricksy-worker.pid \
    --logfile=/var/log/cricksy/worker.log
ExecStop=/bin/kill -TERM $MAINPID
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl daemon-reload
sudo systemctl enable cricksy-worker
sudo systemctl start cricksy-worker
sudo systemctl status cricksy-worker
```

### Using Docker Compose

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
    volumes:
      - minio-data:/data
    command: server /data --console-address ":9001"

  worker:
    build: .
    command: celery -A backend.worker.celery_app worker --loglevel=info --concurrency=4
    environment:
      DATABASE_URL: postgresql+asyncpg://postgres:password@db:5432/cricksy_scorer
      CELERY_BROKER_URL: redis://redis:6379/0
      CELERY_RESULT_BACKEND: redis://redis:6379/0
      S3_ENDPOINT_URL: http://minio:9000
      S3_ACCESS_KEY_ID: minioadmin
      S3_SECRET_ACCESS_KEY: minioadmin
      S3_USE_PATH_STYLE: 1
      ENABLE_UPLOADS: 1
      ENABLE_OCR: 1
    depends_on:
      - db
      - redis
      - minio
    volumes:
      - ./backend:/app/backend

volumes:
  redis-data:
  minio-data:
```

Start with:
```bash
docker-compose up -d worker
docker-compose logs -f worker
```

### AWS Production Setup

#### 1. Configure S3

Use real AWS S3 (not MinIO):

```bash
# Remove MinIO-specific settings
unset S3_ENDPOINT_URL
unset S3_USE_PATH_STYLE

# Set AWS credentials
export S3_ACCESS_KEY_ID=your-aws-access-key
export S3_SECRET_ACCESS_KEY=your-aws-secret-key
export S3_REGION=us-east-1
export S3_UPLOAD_BUCKET=cricksy-prod-uploads
```

Create S3 bucket:
```bash
aws s3 mb s3://cricksy-prod-uploads --region us-east-1
```

Set bucket policy for private access (presigned URLs only).

#### 2. Configure Redis

Use AWS ElastiCache Redis:

```bash
export CELERY_BROKER_URL=redis://your-elasticache-endpoint:6379/0
export CELERY_RESULT_BACKEND=redis://your-elasticache-endpoint:6379/0
```

Or use Redis Cloud, Upstash, etc.

#### 3. Deploy Workers

Options:
- **ECS/Fargate**: Run workers as ECS tasks
- **EC2**: Run workers on EC2 instances with systemd
- **Kubernetes**: Deploy as Deployment/StatefulSet
- **Lambda**: Not recommended (long-running tasks)

## Scaling

### Horizontal Scaling

Add more workers:
```bash
# Worker 1
celery -A backend.worker.celery_app worker -n worker1@%h --loglevel=info

# Worker 2
celery -A backend.worker.celery_app worker -n worker2@%h --loglevel=info

# Worker 3
celery -A backend.worker.celery_app worker -n worker3@%h --loglevel=info
```

### Concurrency

Adjust based on CPU cores:
```bash
# Auto-detect cores
celery -A backend.worker.celery_app worker --concurrency=0

# Manual setting
celery -A backend.worker.celery_app worker --concurrency=8
```

### Queue Priorities

Add task routing:
```python
# backend/worker/celery_app.py
app.conf.task_routes = {
    'backend.worker.processor.process_scorecard_task': {'queue': 'ocr'},
    # Other tasks...
}
```

Start workers for specific queues:
```bash
celery -A backend.worker.celery_app worker -Q ocr --loglevel=info
```

## Monitoring

### Health Checks

Check worker status:
```bash
celery -A backend.worker.celery_app inspect active
celery -A backend.worker.celery_app inspect stats
celery -A backend.worker.celery_app inspect registered
```

### Logging

View logs:
```bash
# Systemd
sudo journalctl -u cricksy-worker -f

# Docker
docker-compose logs -f worker

# Direct
tail -f /var/log/cricksy/worker.log
```

Configure log level:
```bash
celery -A backend.worker.celery_app worker --loglevel=debug
```

### Metrics

Use Celery Flower:
```bash
celery -A backend.worker.celery_app flower --port=5555
```

Or integrate with:
- Prometheus + Grafana
- Datadog
- New Relic
- Sentry (for errors)

## Troubleshooting

### Worker won't start

Check:
1. Redis is running: `redis-cli ping`
2. Python dependencies installed
3. Tesseract installed: `tesseract --version`
4. Environment variables set
5. Database accessible

### Tasks not executing

Check:
1. Worker is running and connected to Redis
2. Task is properly registered: `celery -A backend.worker.celery_app inspect registered`
3. No syntax errors in task code
4. Queue name matches

### OCR failing

Check:
1. Tesseract installed and in PATH
2. Image file accessible in S3/MinIO
3. S3 credentials correct
4. Image format supported (PNG, JPEG, etc.)

### Memory issues

Solutions:
1. Reduce concurrency
2. Set `worker_max_tasks_per_child` to restart workers periodically
3. Monitor memory usage: `celery -A backend.worker.celery_app inspect stats`
4. Use worker pools: `--pool=solo` or `--pool=gevent`

### Database connection issues

Workers need database access:
1. Check `DATABASE_URL` is set correctly
2. Use connection pooling with limits
3. Close connections properly in tasks
4. Consider using `psycopg2` (sync) instead of `asyncpg` in workers

## Security

### Credentials

- **Never commit credentials** to version control
- Use environment variables or secret managers (AWS Secrets Manager, Vault, etc.)
- Rotate credentials regularly
- Use IAM roles when possible (AWS)

### Network

- Workers should access Redis and Database via private network
- Use VPC/Security Groups to restrict access
- Enable TLS for Redis connections in production
- Use VPN or bastion hosts for worker access

### S3/MinIO

- Use presigned URLs (not public buckets)
- Set short expiration times (1 hour)
- Limit IAM permissions to specific operations
- Enable versioning and logging

## Performance Optimization

### Image Processing

- Compress images before uploading
- Use appropriate image formats (JPEG for photos, PNG for screenshots)
- Resize large images before OCR (Tesseract works better with DPI ~300)

### Task Optimization

- Set appropriate timeouts
- Use task retries with exponential backoff
- Batch similar tasks when possible
- Cache frequently accessed data

### Redis

- Use Redis Sentinel for high availability
- Enable persistence if needed (RDB/AOF)
- Monitor memory usage
- Set maxmemory policy

## Testing Workers

### Unit Tests

Test task logic without Celery:
```python
from backend.worker.processor import process_scorecard_task

result = process_scorecard_task.apply(args=["upload-id"]).get()
```

### Integration Tests

Test with real Celery:
```bash
# Start worker
celery -A backend.worker.celery_app worker --loglevel=info &

# Run tests
pytest backend/tests/test_worker.py -v

# Stop worker
pkill -f "celery worker"
```

### Load Testing

Use Locust or similar:
```python
from locust import task, User

class UploadUser(User):
    @task
    def upload_and_process(self):
        # Simulate upload workflow
        pass
```

## Related Documentation
- `UPLOAD_WORKFLOW.md`: Upload and OCR workflow
- `AI_ETHICS.md`: Privacy and ethics policies
- Celery docs: https://docs.celeryq.dev/
