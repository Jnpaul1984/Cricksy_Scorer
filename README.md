<!-- Append or merge this section into your existing README.md -->

## Backend: Run API + Postgres with Docker Compose

A lightweight Compose setup is included so you can bring up both the database and the FastAPI app with one command.

### 0) Prepare environment

Copy the example env and adjust as needed (this is used by local tooling and as defaults in Compose):

```bash
cp .env.example .env
```

Note:
- When running inside Compose, the API uses `DATABASE_URL=postgresql+asyncpg://postgres:RubyAnita2018@db:5432/cricksy_scorer` (the `db` service hostname). Your local host `DATABASE_URL` (e.g., `localhost:5555`) is still useful for tools that connect from your host.

### 1) Start both services

```bash
docker compose up -d db backend
```

- `db` exposes Postgres on host port `5555`.
- `backend` exposes the API at `http://localhost:8000`.

The backend container will:
- Install Python dependencies from `backend/requirements.txt`
- Run Alembic migrations against the `db` service
- Start Uvicorn with `backend.main:app`

Logs:

```bash
docker compose logs -f backend
```

Stop:

```bash
docker compose down
```

### 2) Verify

- Health: http://localhost:8000/health
- OpenAPI Docs: http://localhost:8000/docs

### 3) Iteration workflow

The backend service mounts your repo into the container (`./:/app`), so code edits on your host are reflected in the container immediately. Restart the backend service to pick up dependency changes:

```bash
docker compose restart backend
```

If you add new Python packages, update `backend/requirements.txt` and restart:

```bash
docker compose restart backend
```

### Notes

- For local testing without Postgres, set `CRICKSY_IN_MEMORY_DB=1` in your shell and run tests on your host. When using Compose, the file sets `CRICKSY_IN_MEMORY_DB=0` for the backend container so it uses the Postgres service.
- If you later add a Dockerfile for a faster build (recommended), switch the `backend` service to `build:` instead of installing requirements on each start.

## Upload & OCR Features

Cricksy Scorer includes AI-powered scorecard upload and OCR (Optical Character Recognition) capabilities, allowing users to upload images of scorecards that are automatically processed and parsed.

### Quick Start

1. **Start required services** (MinIO for storage, Redis for workers):
   ```bash
   docker-compose up -d redis minio
   ```

2. **Configure environment** (see `.env.example`):
   ```bash
   cp .env.example .env
   # Edit .env to configure S3/MinIO credentials
   ```

3. **Start Celery worker**:
   ```bash
   cd backend
   celery -A backend.worker.celery_app worker --loglevel=info
   ```

4. **Access upload interface** at `http://localhost:5173/uploads`

### Documentation

- **[Upload Workflow](docs/UPLOAD_WORKFLOW.md)**: Complete documentation of the upload and OCR process
- **[Worker Deployment](docs/DEPLOY_WORKER.md)**: Guide for deploying and scaling Celery workers
- **[AI Ethics & Privacy](docs/AI_ETHICS.md)**: Privacy policies, consent requirements, and ethical guidelines

### Key Features

- ✅ Presigned URL uploads (direct to S3/MinIO, no backend bottleneck)
- ✅ Asynchronous OCR processing with Celery workers
- ✅ Manual verification required before applying data
- ✅ Support for MinIO (development) and AWS S3 (production)
- ✅ Privacy-first design with data retention policies
- ✅ Feature flags for easy enable/disable

### AI Ethics & Privacy

**Important**: All AI/OCR features follow strict ethical guidelines:

- 🔒 **Privacy by Design**: Minimal data collection, encrypted storage
- 👤 **Human-in-the-Loop**: Manual verification required for all AI outputs
- 🚫 **No Biometric Profiling**: No facial recognition or player identification
- 📝 **Informed Consent**: Clear consent required before upload
- ⏱️ **Data Retention**: Automatic deletion after 30 days

**Before using upload features**, please review our [AI Ethics & Privacy Policy](docs/AI_ETHICS.md) which covers:
- What data is collected and how it's used
- Your rights (access, deletion, correction, opt-out)
- Forbidden use cases (surveillance, discrimination, commercial exploitation)
- Security measures and incident response

To update this policy, edit `docs/AI_ETHICS.md` and ensure all team members are aware of changes.

### Feature Flags

Control features via environment variables:

```bash
# Enable/disable uploads
ENABLE_UPLOADS=1

# Enable/disable OCR processing
ENABLE_OCR=1
```

When disabled, endpoints return 503 Service Unavailable.
