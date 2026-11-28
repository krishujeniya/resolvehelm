# ==============================================================================
# ResolveHelm Multi-Stage Dockerfile
# Stage 1: Build React Dashboard
# Stage 2: Python 3.13 Runtime with uv
# ==============================================================================

# Stage 1: Frontend Build
FROM node:22-bookworm-slim AS frontend-builder
WORKDIR /app/dashboard
COPY dashboard/package*.json ./
RUN npm ci
COPY dashboard/ ./
RUN npm run build

# Stage 2: Production Python Runtime
FROM python:3.13-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PORT=8000

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install uv binary directly from official image
COPY --from=ghcr.io/astral-sh/uv:0.8.22 /uv /uvx /bin/

# Create non-root application user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy dependency configuration and install packages
COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

# Copy application source code
COPY app/ ./app/
COPY knowledge_base/ ./knowledge_base/
COPY scripts/ ./scripts/
COPY supabase/ ./supabase/

# Copy compiled frontend assets from Stage 1 into dashboard/dist
COPY --from=frontend-builder /app/dashboard/dist ./dashboard/dist

# Install the application wheel
RUN uv sync --frozen --no-dev

# Set permissions
RUN chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
