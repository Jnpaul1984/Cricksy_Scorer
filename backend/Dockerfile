# syntax=docker/dockerfile:1
FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ENV=ci

# Ensure curl and ca-certificates are present and up-to-date on common bases.
RUN set -eux; \
    if command -v apt-get >/dev/null 2>&1; then \
      apt-get update; \
      apt-get -y --no-install-recommends upgrade; \
      apt-get -y --no-install-recommends install curl ca-certificates build-essential; \
      apt-get -y --only-upgrade install curl || true; \
      rm -rf /var/lib/apt/lists/*; \
    elif command -v apk >/dev/null 2>&1; then \
      apk update && apk add --no-cache curl ca-certificates build-base; \
      apk upgrade curl || true; \
    else \
      echo "No known package manager found; skipping curl install"; \
    fi

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- dev-only deps for CI ---
COPY requirements-dev.txt .
RUN if [ "$ENV" = "ci" ]; then pip install --no-cache-dir -r requirements-dev.txt; fi

COPY . .
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
