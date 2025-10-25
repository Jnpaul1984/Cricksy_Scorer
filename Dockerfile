# Multi-stage build: build deps once, run on a minimal, non-root image.

# ========== Builder ==========
FROM python:3.12-slim AS builder

ENV PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

# System deps that are commonly needed for wheels (kept minimal).
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Copy only the backend requirements to leverage Docker layer caching
COPY backend/requirements.txt /app/backend/requirements.txt

# Create a virtualenv with pinned deps
RUN python -m venv /opt/venv && /opt/venv/bin/pip install --upgrade pip \
  && /opt/venv/bin/pip install -r /app/backend/requirements.txt

# Copy only the runtime backend source (avoid copying tests and misc)
COPY backend /app/backend

# ========== Runtime ==========
FROM python:3.12-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

# Create non-root user
RUN useradd -r -u 10001 -g root appuser

WORKDIR /app

# Copy venv from builder and app code
COPY --from=builder /opt/venv /opt/venv
COPY --from=builder /app/backend /app/backend

# Expose app port
EXPOSE 8000

# HEALTHCHECK without adding curl/wget (use Python stdlib)
HEALTHCHECK --interval=10s --timeout=3s --retries=5 --start-period=20s CMD \
  python -c "import urllib.request,sys; \
u='http://127.0.0.1:8000/health'; \
  sys.exit(0) if urllib.request.urlopen(u, timeout=2).getcode()==200 else sys.exit(1)" || exit 1

# Drop privileges
USER appuser

# Default command:
# Use uvicorn directly (gunicorn optional if added to requirements).
# Note: Using 1 worker by default because Socket.IO in-memory state doesn't span processes.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
