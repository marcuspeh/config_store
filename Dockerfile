# syntax=docker/dockerfile:1
# Build context: the repository root (one level above this directory).
# The `config_store.main:app` entry point needs the package to live at
# /app/config_store, with /app on sys.path.

FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# curl is used by the compose healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python deps first for layer caching.
COPY config_store/requirements.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# Copy only this service's source tree.
COPY config_store/ /app/config_store/

# Drop privileges.
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

EXPOSE 8002

CMD ["uvicorn", "config_store.main:app", "--host", "0.0.0.0", "--port", "8002"]
