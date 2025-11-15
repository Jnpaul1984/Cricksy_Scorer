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
      # Upgrade installed packages (pick up distro security fixes) \
      apt-get -y --no-install-recommends upgrade; \
      # Install curl, ca-certificates and build tools (ensure package present) \
      apt-get -y --no-install-recommends install curl ca-certificates build-essential; \
      # Try to explicitly upgrade curl package if a newer candidate exists (do not fail build if no candidate) \
      apt-get -y --only-upgrade install curl || true; \
      rm -rf /var/lib/apt/lists/*; \
    elif command -v apk >/dev/null 2>&1; then \
      # Alpine: install/upgrade curl and ca-certificates \
      apk update && apk add --no-cache curl ca-certificates build-base; \
      apk upgrade curl || true; \
    else \
      echo "No known package manager found; skipping curl install"; \
    fi

# Install backend dependencies: requirements live in backend/
COPY backend/requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy only the backend app code into /app
COPY backend/ .

# Uvicorn will now find /app/main.py -> module "main"
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
