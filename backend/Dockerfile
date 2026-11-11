FROM ubuntu:24.04 AS runtime-base
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
      ca-certificates python3.12 libgomp1 libglib2.0-0t64 libgl1; \
    dpkg --compare-versions "$(dpkg-query -W -f='${Version}' libc6)" ge '2.39-0ubuntu8.9'; \
    dpkg --compare-versions "$(dpkg-query -W -f='${Version}' zlib1g)" ge '1:1.3.dfsg-3.1ubuntu2.3'; \
    mkdir -p /app/mediapipe_models; \
    rm -rf /var/lib/apt/lists/*
# Keep Ubuntu's bootstrap wheels out of the final runtime image.
FROM runtime-base AS dependencies
RUN set -eux; \
    apt-get update; \
    DEBIAN_FRONTEND=noninteractive apt-get -y --no-install-recommends install python3.12-venv; \
    python3.12 -m venv /opt/venv; \
    python -m pip install --no-cache-dir --upgrade pip==26.3; \
    rm -rf /var/lib/apt/lists/*
COPY backend/requirements.txt ./requirements.txt
COPY backend/packaging/repair_wheels.py backend/packaging/wheel-pins.json /opt/wheel-repair/
RUN python /opt/wheel-repair/repair_wheels.py --output /opt/repaired-wheels \
    && python -m pip install --default-timeout=600 --no-cache-dir \
      /opt/repaired-wheels/mediapipe-0.10.31-1cricksy-py3-none-linux_x86_64.whl \
      /opt/repaired-wheels/xgboost-1.7.6-1cricksy-py3-none-manylinux_2_17_x86_64.manylinux2014_x86_64.whl \
      -r requirements.txt \
    && python -m pip check
# pip 26.3 retains the runtime dependency check with patched vendored urllib3.
FROM runtime-base AS runtime
COPY --from=dependencies /opt/venv /opt/venv
COPY --from=dependencies /opt/repaired-wheels/wheel-provenance.json /opt/wheel-provenance.json
RUN python -m pip check
COPY backend/requirements.txt ./requirements.txt
COPY backend/ ./backend
COPY backend/ml_models/ ./backend/ml_models/
COPY backend/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh
ENTRYPOINT ["./entrypoint.sh"]
