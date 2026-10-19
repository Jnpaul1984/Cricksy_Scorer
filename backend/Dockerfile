FROM python:3.12-slim

WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    ENV=ci

# Ensure model cache directory exists (model is downloaded at runtime; not baked into image)
RUN mkdir -p /app/mediapipe_models

# Keep only certificates needed for HTTPS calls at runtime. Health checks use the
# Python standard library, so curl (and its SASL dependency chain) is not needed.
RUN set -eux; \
    if command -v apt-get >/dev/null 2>&1; then \
      apt-get update; \
      # Upgrade installed packages (pick up distro security fixes) \
      apt-get -y --no-install-recommends upgrade; \
      apt-get -y --no-install-recommends install ca-certificates; \
      rm -rf /var/lib/apt/lists/*; \
    elif command -v apk >/dev/null 2>&1; then \
      apk update && apk add --no-cache ca-certificates; \
    else \
      echo "No known package manager found; skipping certificate install"; \
    fi

# Install backend dependencies (requirements live in backend/)
COPY backend/requirements.txt ./requirements.txt
RUN pip install --default-timeout=600 --no-cache-dir -r requirements.txt

# Preserve the backend package structure inside the container
COPY backend/ ./backend

# Copy ML models into the image (enables predictions without external dependencies)
COPY backend/ml_models/ ./backend/ml_models/

# Copy and set entrypoint script
COPY backend/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

# Start the FastAPI app via entrypoint (runs migrations first)
ENTRYPOINT ["./entrypoint.sh"]
