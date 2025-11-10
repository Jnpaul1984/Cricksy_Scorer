# Worker Deployment Guide

This guide covers deploying and managing the Celery worker for OCR processing of uploaded scorecards.

## Prerequisites

### System Requirements

- Python 3.10+
- Redis (for Celery broker and result backend)
- Tesseract OCR engine
- Poppler (for PDF processing)

### Installing Dependencies

#### Ubuntu/Debian

```bash
# Install Tesseract and Poppler
sudo apt-get update
sudo apt-get install -y tesseract-ocr poppler-utils

# Verify installation
tesseract --version
pdfinfo -v
```

#### macOS

```bash
# Using Homebrew
brew install tesseract poppler

# Verify installation
tesseract --version
pdfinfo -v
```

#### Windows

```powershell
# Using Chocolatey
choco install tesseract poppler

# Or download installers:
# Tesseract: https://github.com/UB-Mannheim/tesseract/wiki
# Poppler: http://blog.alivate.com.au/poppler-windows/
```

### Python Dependencies

```bash
cd backend
pip install -r requirements.txt
```

## Configuration

### Environment Variables

The worker requires the following environment variables:

```bash
# Feature Flags
export CRICKSY_ENABLE_OCR=1

# Redis/Celery
export CRICKSY_REDIS_URL=redis://localhost:6379/0
export CRICKSY_CELERY_BROKER_URL=redis://localhost:6379/0
export CRICKSY_CELERY_RESULT_BACKEND=redis://localhost:6379/0

# S3/MinIO (for downloading files)
export CRICKSY_S3_ENDPOINT=http://localhost:9000  # For MinIO dev
export CRICKSY_S3_REGION=us-east-1
export CRICKSY_S3_BUCKET=cricksy-uploads-dev
export CRICKSY_S3_ACCESS_KEY=your-access-key
export CRICKSY_S3_SECRET_KEY=your-secret-key

# Database
export DATABASE_URL=postgresql://user:pass@localhost/cricksy

# Tesseract (if not in PATH)
export TESSERACT_CMD=/usr/bin/tesseract
```

### Redis Setup

#### Development (Docker)

```bash
docker run -d \
  -p 6379:6379 \
  --name redis \
  redis:7-alpine
```

#### Production

Use a managed Redis service (AWS ElastiCache, Redis Cloud, etc.) or deploy a production-ready Redis cluster.

## Running the Worker

### Development

```bash
cd backend
celery -A worker.celery_app worker --loglevel=info
```

### Production

For production, use a process manager like systemd or supervisord:

#### Using systemd

Create `/etc/systemd/system/cricksy-worker.service`:

```ini
[Unit]
Description=Cricksy OCR Worker
After=network.target redis.service

[Service]
Type=forking
User=cricksy
Group=cricksy
WorkingDirectory=/opt/cricksy/backend
Environment="PATH=/opt/cricksy/venv/bin"
Environment="CRICKSY_ENABLE_OCR=1"
Environment="CRICKSY_REDIS_URL=redis://localhost:6379/0"
# Add other environment variables...

ExecStart=/opt/cricksy/venv/bin/celery -A worker.celery_app worker \
  --loglevel=info \
  --logfile=/var/log/cricksy/worker.log \
  --pidfile=/var/run/cricksy/worker.pid \
  --detach

ExecStop=/opt/cricksy/venv/bin/celery -A worker.celery_app control shutdown

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

#### Using Supervisor

Install supervisor:

```bash
sudo apt-get install supervisor
```

Create `/etc/supervisor/conf.d/cricksy-worker.conf`:

```ini
[program:cricksy-worker]
command=/opt/cricksy/venv/bin/celery -A worker.celery_app worker --loglevel=info
directory=/opt/cricksy/backend
user=cricksy
autostart=true
autorestart=true
redirect_stderr=true
stdout_logfile=/var/log/cricksy/worker.log
environment=CRICKSY_ENABLE_OCR="1",CRICKSY_REDIS_URL="redis://localhost:6379/0"
```

Load and start:

```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start cricksy-worker
```

## Monitoring

### Checking Worker Status

```bash
# Using Celery inspect
celery -A worker.celery_app inspect active
celery -A worker.celery_app inspect stats

# Check logs
tail -f /var/log/cricksy/worker.log
```

### Flower (Web-based Monitoring)

Install Flower:

```bash
pip install flower
```

Run Flower:

```bash
celery -A worker.celery_app flower --port=5555
```

Access at: http://localhost:5555

### Key Metrics to Monitor

1. **Task Queue Length**: Number of pending tasks
2. **Task Execution Time**: How long tasks take to complete
3. **Task Failure Rate**: Percentage of failed tasks
4. **Worker Memory Usage**: Monitor for memory leaks
5. **Redis Connection Status**: Ensure broker is healthy

## Scaling

### Horizontal Scaling

Run multiple worker instances:

```bash
# Worker 1
celery -A worker.celery_app worker --hostname=worker1@%h --loglevel=info

# Worker 2
celery -A worker.celery_app worker --hostname=worker2@%h --loglevel=info
```

### Concurrency

Adjust worker concurrency:

```bash
# Use 4 concurrent processes
celery -A worker.celery_app worker --concurrency=4

# Use gevent for I/O-bound tasks
celery -A worker.celery_app worker --pool=gevent --concurrency=100
```

## Troubleshooting

### Worker Won't Start

Check:
1. Redis is running: `redis-cli ping`
2. Environment variables are set: `env | grep CRICKSY`
3. Python can import the app: `python -c "from backend.worker.celery_app import app"`

### OCR Failures

Check:
1. Tesseract is installed: `tesseract --version`
2. File is accessible from S3
3. File format is supported (image/*, application/pdf)
4. Worker has sufficient memory

### High Memory Usage

Solutions:
1. Set `worker_max_tasks_per_child` in celery_app.py (already set to 50)
2. Reduce concurrency
3. Use gevent pool for I/O-bound tasks
4. Monitor with `celery -A worker.celery_app inspect stats`

### Tasks Stuck in Queue

Check:
1. Workers are running: `celery -A worker.celery_app inspect active`
2. No exceptions in logs
3. Redis queue depth: `redis-cli llen celery`

## Task Lifecycle

```
1. Client calls POST /api/uploads/complete
   └─> Enqueues task: process_upload_task.delay(upload_id)

2. Celery worker picks up task
   └─> Downloads file from S3
   └─> Runs OCR (Tesseract)
   └─> Parses scorecard
   └─> Updates database with parsed_preview
   └─> Sets status to 'ready' or 'failed'

3. Client polls GET /api/uploads/{id}/status
   └─> Gets parsed_preview when ready
```

## Security Considerations

### 1. S3 Access

- Use IAM roles instead of access keys where possible
- Rotate credentials regularly
- Restrict worker IAM policy to read-only on upload bucket

### 2. Resource Limits

- Set task time limits to prevent runaway tasks
- Limit file sizes at upload time
- Set memory limits for worker processes

### 3. Input Validation

- Validate file types before processing
- Sanitize filenames to prevent path traversal
- Check file size before downloading

### 4. Network Security

- Run Redis with authentication: `requirepass your-password`
- Use TLS for Redis connections in production
- Firewall Redis to only accept connections from workers

## Performance Tuning

### OCR Optimization

```python
# In processor.py, configure Tesseract for faster processing
pytesseract.image_to_string(image, config='--psm 6 --oem 3')
```

PSM modes:
- `6`: Uniform block of text (default, good for scorecards)
- `3`: Fully automatic page segmentation (slower but more accurate)

OEM modes:
- `3`: Default, based on what is available (recommended)
- `1`: Neural nets LSTM only (faster but may be less accurate)

### Batch Processing

For bulk uploads, consider:

```bash
# Multiple workers with autoscaling
celery -A worker.celery_app worker \
  --autoscale=10,3 \
  --loglevel=info
```

## Maintenance

### Regular Tasks

1. **Monitor disk space**: OCR processing creates temporary files
2. **Monitor Redis memory**: Set `maxmemory` policy
3. **Review logs**: Look for repeated errors
4. **Update dependencies**: Keep Tesseract and libraries updated

### Backup and Disaster Recovery

- Parsed previews are stored in the database (backed up with DB)
- Original files remain in S3 (configure lifecycle policies)
- Worker state is ephemeral (no backup needed)

## Related Documentation

- [Upload Workflow](./UPLOAD_WORKFLOW.md) - Complete upload workflow
- [AI Ethics & Media Policy](./AI_ETHICS.md) - Ethics and consent guidelines
