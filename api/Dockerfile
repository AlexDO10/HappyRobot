# Pinned base image for reproducible builds.
FROM python:3.12.7-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PORT=8000

WORKDIR /app

# uv for fast, reproducible installs (pinned).
COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/

# Stable layer: dependencies. Cached unless pyproject.toml changes.
COPY pyproject.toml ./
RUN uv pip install --system --no-cache \
    "fastapi>=0.115" "uvicorn[standard]>=0.32" "pydantic>=2.9" \
    "pydantic-settings>=2.6" "httpx>=0.27" "python-dotenv>=1.0"

# Volatile layers: application code and data.
COPY app ./app
COPY data ./data

EXPOSE 8000

# Exec form. The managed host injects $PORT; default 8000 for local runs.
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
