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

## Coach Pro Plus: Video Analysis Worker (Local Dev)

Coach Pro Plus video analysis runs in a background worker container (CPU-only) and is queued in the Postgres DB.

### Start API + worker

```bash
docker compose -f docker-compose.dev.yml up -d --build api analysis_worker
```

### Logs

```bash
docker compose -f docker-compose.dev.yml logs -f api
docker compose -f docker-compose.dev.yml logs -f analysis_worker
```

### Expected job lifecycle

- `queued` → `quick_running` → `quick_done` → `deep_running` → `done`
- If deep is disabled: `queued` → `quick_running` → `quick_done` → `done`
- Failures end in: `failed`

The job payload includes `stage` and `progress_pct` (quick stage 0–50, deep stage 50–100).

### 3) Iteration workflow

The backend service mounts your repo into the container (`./:/app`), so code edits on your host are reflected in the container immediately. Restart the backend service to pick up dependency changes:

```bash
docker compose -f docker-compose.dev.yml restart api
docker compose -f docker-compose.dev.yml restart analysis_worker
```

If you add new Python packages, update `backend/requirements.txt` and restart:

```bash
docker compose -f docker-compose.dev.yml up -d --build api analysis_worker
```

### Notes

- For local testing without Postgres, set `CRICKSY_IN_MEMORY_DB=1` in your shell and run tests on your host. When using Compose, the file sets `CRICKSY_IN_MEMORY_DB=0` for the backend container so it uses the Postgres service.
- If you later add a Dockerfile for a faster build (recommended), switch the `backend` service to `build:` instead of installing requirements on each start.

#### MediaPipe model access (required for successful analysis)

The worker needs the MediaPipe Pose Landmarker model at `/app/mediapipe_models/pose_landmarker_full.task`.

- If the file is missing, it will try to download from S3 using:
	- `MODEL_S3_BUCKET` (default: `cricksy-coach-videos-prod`)
	- `MODEL_S3_KEY` (default: `mediapipe/pose_landmarker_full.task`)
	- `MODEL_LOCAL_PATH` (default: `/app/mediapipe_models/pose_landmarker_full.task`)

If your IAM policy restricts S3 access to the `coach_plus/dev-test/...` prefix, you must either:
- Allow `s3:GetObject`/`s3:HeadObject` for the single model key above, OR
- Upload the model under an allowed prefix and set `MODEL_S3_KEY` accordingly.

**Option 2 (prefix-only IAM): upload the model to an allowed key**

1) Download `pose_landmarker_full.task` to your machine (keep it private; it’s a binary model file).

2) Upload it to S3 under the allowed prefix (runs inside the `api` container using your mounted AWS creds):

```bash
docker compose -f docker-compose.dev.yml exec -T api sh -lc "cd /app && python -m backend.scripts.upload_mediapipe_model_to_s3 /path/on/host/pose_landmarker_full.task"
```

If you don’t have an easy container-visible path, copy it into the container first:

```bash
docker cp /path/on/host/pose_landmarker_full.task cricksy_scorer-api-1:/tmp/pose_landmarker_full.task
docker compose -f docker-compose.dev.yml exec -T api sh -lc "cd /app && python -m backend.scripts.upload_mediapipe_model_to_s3 /tmp/pose_landmarker_full.task"
```

3) Ensure `.env` sets `MODEL_S3_KEY=coach_plus/dev-test/mediapipe/pose_landmarker_full.task` (default in `docker-compose.dev.yml`).

4) Restart the worker:

```bash
docker compose -f docker-compose.dev.yml restart analysis_worker
```
