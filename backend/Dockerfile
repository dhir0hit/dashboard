# Backend: FastAPI + uvicorn
# Listens on 8000. Configuration comes from env vars (see .env.example).
FROM python:3.12-slim AS runtime

# Curl is useful for the compose healthcheck; nothing else is added to keep
# the image small.
RUN apt-get update \
 && apt-get install -y --no-install-recommends curl ca-certificates \
 && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install deps first for better layer caching.
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt

# Application code. The package is `app` so we copy it to /app/app.
COPY app /app/app

# Volume mount points — keep state out of the image so containers are
# reproducible. docker-compose mounts named volumes here.
VOLUME ["/data", "/app/wallpapers"]

# Runtime config. CONFIG_DB points into /data so the SQLite file persists
# across container restarts via the mounted volume.
ENV HOST=0.0.0.0 \
    PORT=8000 \
    CONFIG_DB=/data/config.db

EXPOSE 8000

HEALTHCHECK --interval=15s --timeout=3s --start-period=10s --retries=3 \
  CMD curl -fsS http://127.0.0.1:8000/health || exit 1

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]