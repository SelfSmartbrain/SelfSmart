# =============================================================================
# Autonomous Agent Platform — Production Dockerfile
# =============================================================================
# Multi-stage build for minimal image size

# Stage 1: Build dependencies
FROM python:3.12-slim AS builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && \
    apt-get install -y --no-install-recommends gcc libpq-dev && \
    rm -rf /var/lib/apt/lists/*

# Copy package metadata and source before building the wheel.
COPY pyproject.toml README.md LICENSE ./
COPY src/ ./src/
COPY modelx_voice/ ./modelx_voice/

# Install Python dependencies
RUN pip install --no-cache-dir --prefix=/install .

# Stage 2: Runtime
FROM python:3.12-slim AS runtime

WORKDIR /app

# Install runtime dependencies only
RUN apt-get update && \
    apt-get install -y --no-install-recommends libpq5 curl && \
    rm -rf /var/lib/apt/lists/* && \
    # Create non-root user
    groupadd -r agent && \
    useradd -r -g agent -d /app -s /sbin/nologin agent

# Copy installed packages from builder
COPY --from=builder /install /usr/local

# Copy application code
COPY src/ ./src/
COPY modelx_voice/ ./modelx_voice/
COPY alembic/ ./alembic/
COPY alembic.ini ./

# Create workspace directory
RUN mkdir -p /app/workspace && chown -R agent:agent /app

# Switch to non-root user
USER agent

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=15s \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/health')" || exit 1

# Run with uvicorn
CMD ["python", "-m", "uvicorn", "src.api.main:app", \
     "--host", "0.0.0.0", \
     "--port", "8000", \
     "--workers", "4", \
     "--loop", "uvloop", \
     "--http", "httptools", \
     "--log-level", "info"]
