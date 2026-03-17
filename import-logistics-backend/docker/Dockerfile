# docker/Dockerfile
# Multi-stage build — dev image stays light, prod image is hardened

# ── Base ──────────────────────────────────────────────────────────────
FROM python:3.11-slim AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# System deps needed by psycopg2, python-magic, Playwright
RUN apt-get update && apt-get install -y --no-install-recommends \
    libmagic1 \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# ── Development stage ─────────────────────────────────────────────────
FROM base AS development

COPY requirements-dev.txt* .
RUN pip install --no-cache-dir -r requirements-dev.txt 2>/dev/null || true

COPY . .

# ── Production stage ──────────────────────────────────────────────────
FROM base AS production

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

COPY . .

# Pre-install Playwright browsers (needed for JS scraping)
RUN playwright install chromium --with-deps 2>/dev/null || true

# Set correct permissions
RUN mkdir -p /app/uploads /app/celerybeat && \
    chown -R appuser:appuser /app

USER appuser

EXPOSE 8000

CMD ["gunicorn", "app.main:app", "-c", "docker/gunicorn.conf.py"]