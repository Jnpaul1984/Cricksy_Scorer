FROM ubuntu:24.04
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH" \
    ENV=ci
RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends upgrade; \
    DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends install \
      ca-certificates python3.12 python3.12-venv libgomp1 libglib2.0-0t64 libgl1; \
    dpkg --compare-versions "$(dpkg-query -W -f='${Version}' libc6)" ge '2.39-0ubuntu8.9'; \
    dpkg --compare-versions "$(dpkg-query -W -f='${Version}' zlib1g)" ge '1:1.3.dfsg-3.1ubuntu2.3'; \
    python3.12 -m venv /opt/venv; \
    mkdir -p /app/mediapipe_models; \
    rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./requirements.txt
RUN python -m pip install --default-timeout=600 --no-cache-dir -r requirements.txt \
    && python -m pip check
COPY backend/ ./backend
COPY backend/ml_models/ ./backend/ml_models/
COPY backend/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
