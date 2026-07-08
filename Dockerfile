# syntax=docker/dockerfile:1
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_SYSTEM_PYTHON=1

WORKDIR /app

# curl is used by the compose healthcheck.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl \
    && rm -rf /var/lib/apt/lists/*

# Install uv for fast Python package management.
RUN pip install uv

# Install Python deps first for layer caching.
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen

# Copy only this service's source tree.
COPY . /app/

# Drop privileges.
RUN useradd --create-home --shell /bin/bash app \
    && chown -R app:app /app
USER app

EXPOSE 6002

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "6002"]