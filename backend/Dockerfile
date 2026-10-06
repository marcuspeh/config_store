# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# curl is used by the compose healthcheck; git is required by uv to
# resolve the `logging-sdk` git dependency.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl git \
    && rm -rf /var/lib/apt/lists/*

RUN pip install uv

# Deps first for layer caching; logging-sdk comes from GitHub via uv sources.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Copy only this service's source tree.
COPY app ./app

# Drop privileges.
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

EXPOSE 6002

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "6002"]