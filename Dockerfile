# ============================================
# Stage 1: Build dependencies with uv
# ============================================
FROM ghcr.io/astral-sh/uv:python3.12-bookworm-slim AS builder

WORKDIR /build

# Set longer timeout for slow Docker Desktop networking
ENV UV_HTTP_TIMEOUT=300

# Install system build deps (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy dependency spec for caching
COPY pyproject.toml LICENSE README.md ./

# Install all deps in one go with --no-deps (avoids CUDA downloads on arm64)
RUN uv pip install --no-cache --prefix=/install --no-deps \
    fastapi uvicorn pydantic pydantic-settings python-multipart python-dotenv \
    httpx aiohttp requests \
    openai anthropic huggingface-hub \
    langchain langchain-core langchain-openai langchain-anthropic langchain-community langchain-text-splitters langgraph langgraph-checkpoint-postgres \
    qdrant-client chromadb \
    sqlalchemy alembic asyncpg psycopg redis aiosqlite \
    python-jose passlib slowapi \
    prometheus-client structlog sentry-sdk \
    selenium playwright fake-useragent beautifulsoup4 aiofiles feedparser wikipedia-api youtube-transcript-api langdetect pypdf pandas numpy scikit-learn matplotlib seaborn \
    neo4j networkx \
    celery flower tenacity \
    click rich pillow psutil schedule textblob spacy tiktoken uuid6 pyyaml tabulate apscheduler arxiv keyring opencv-python prompt-toolkit textual edge-tts piper-tts faster-whisper webrtcvad sounddevice gunicorn

# Install torch/cpu separately (no CUDA on arm64)
RUN uv pip install --no-cache --prefix=/install torch torchvision --index-url https://download.pytorch.org/whl/cpu

# Install ML packages that may need compilation
RUN uv pip install --no-cache --prefix=/install sentence-transformers transformers mlx-lm ctranslate2

# Install selfsmart package (no deps since already installed above)
RUN uv pip install --no-cache --prefix=/install --no-deps .

# ============================================
# Stage 2: Production runtime (minimal)
# ============================================
FROM python:3.12-slim AS runtime

# Install only runtime system deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 curl libgomp1 \
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

CMD ["gunicorn", "src.api.main:app", "--workers", "4", "--worker-class", "uvicorn.workers.UvicornWorker", "--bind", "0.0.0.0:8000", "--timeout", "120", "--keep-alive", "5"]