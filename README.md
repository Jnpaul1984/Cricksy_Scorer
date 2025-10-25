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
