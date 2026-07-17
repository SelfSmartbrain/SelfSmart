# ============================================
# Stage 1: Build dependencies
# ============================================
FROM python:3.12-slim AS builder

WORKDIR /build

# Install system build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy only dependency spec for caching
COPY pyproject.toml .
RUN pip install --no-cache-dir --prefix=/install .

# ============================================
# Stage 2: Production runtime
# ============================================
FROM python:3.12-slim AS runtime

# Install only runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /sbin/nologin appuser

WORKDIR /app

# Copy installed Python packages
COPY --from=builder /install /usr/local

# Copy application code only
COPY src/ ./src/
COPY alembic/ ./alembic/
COPY alembic.ini .

# Set ownership
RUN chown -R appuser:appuser /app

USER appuser

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=15s \
    CMD curl -f http://localhost:8000/health || exit 1

CMD ["python", "-m", "uvicorn", "src.api.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
