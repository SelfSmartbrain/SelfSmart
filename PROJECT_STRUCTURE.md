# SelfSmart AI — Project Structure

This document reflects the **actual** project structure as of the production-readiness audit.

## Root Layout

```
selfsmart/
├── .github/workflows/ci.yml          # GitHub Actions CI/CD
├── .dockerignore                     # Docker build exclusions
├── .env                              # Local environment (git-ignored)
├── .env.example                      # Template for .env
├── .pre-commit-config.yaml           # Pre-commit hooks
├── alembic/                          # Database migrations
├── alembic.ini                       # Alembic config
├── Dockerfile                        # Production multi-stage build
├── docker-compose.yml                # Local stack (Postgres, Qdrant, Redis, etc.)
├── infrastructure/
│   └── kubernetes/deployment.yaml    # K8s manifests (Deployment, Service, HPA, Ingress, etc.)
├── frontend/                         # Next.js 16 + React 19 + Tailwind
│   ├── src/
│   │   ├── app/                      # App Router (pages, layouts, error boundaries)
│   │   ├── components/               # Shared UI components
│   │   ├── hooks/                    # Custom React hooks
│   │   ├── lib/                      # Utilities (apiUrl helper)
│   │   └── store/                    # Zustand state
│   ├── package.json                  # Pinned exact versions
│   └── .env.local.example            # Frontend env template
├── modelx_voice/                     # Voice assistant package
├── pyproject.toml                    # Single source of truth for deps (prod + dev + training + voice)
├── README.md
├── sdk/
│   └── python/                       # SelfSmart SDK (pip install -e sdk/python)
│       ├── pyproject.toml
│       └── selfsmart_sdk/
│           ├── __init__.py
│           └── client.py
├── scripts/                          # Build / helper scripts
│   ├── build_dataset.py
│   └── ...
├── src/                              # Backend source (Python 3.12)
│   ├── api/                          # FastAPI application
│   │   ├── main.py                   # create_app() — sole entry point
│   │   ├── routes/                   # API route modules
│   │   │   ├── auth_routes.py
│   │   │   ├── chat.py
│   │   │   ├── conversations.py
│   │   │   ├── feedback.py
│   │   │   ├── health.py
│   │   │   ├── learning.py
│   │   │   ├── legacy_auth.py
│   │   │   └── stats.py
│   │   ├── deps/                     # Dependency injection
│   │   ├── middleware/               # CORS, correlation-id, logging
│   │   ├── rate_limit/               # slowapi limiter
│   │   ├── schemas/                  # Pydantic request/response models
│   │   └── services/                 # Shared runtime services
│   ├── cli/                          # Typer CLI commands
│   ├── config/                       # Configuration
│   │   ├── logging.py                # Structured logging (structlog)
│   │   └── settings.py               # Pydantic Settings (required SECRET_KEY)
│   ├── db/                           # Database layer (SQLAlchemy 2.0 async)
│   │   ├── models/                   # ORM models
│   │   ├── repositories/             # Repository pattern
│   │   └── session.py                # AsyncSessionLocal + engine
│   ├── learning/                     # Continuous learning pipeline
│   ├── llm/                          # LLM providers (DeepSeek, Gemini, OpenRouter, Local)
│   ├── rag/                          # RAG service + vector integration
│   ├── monitoring/                   # Prometheus metrics + health checks
│   ├── utils/                        # Shared utilities (auth, sanitizer, datetime)
│   └── workers/                      # Celery beat / task definitions
├── tests/                            # Pytest suite
│   ├── api/test_endpoints.py         # API integration tests
│   ├── unit/
│   ├── integration/
│   └── e2e/
└── web_server.py.archived            # Old monolith (retired)
```

## Key Architectural Notes

| Area | Decision |
|------|----------|
| **Entry Point** | `src/api/main.py:create_app()` — used by Dockerfile, `run_server.sh`, `start_project.sh` |
| **Auth** | JWT (HS256) via `src/utils/auth.py`; `SECRET_KEY` required at startup |
| **Database** | Async SQLAlchemy 2.0 + asyncpg; migrations via Alembic |
| **Vector DB** | Qdrant (primary) + ChromaDB fallback |
| **Queue** | Celery + Redis (broker + results) |
| **LLM Providers** | OpenRouter, DeepSeek, Gemini, Local (MLX) via unified interface |
| **Frontend** | Next.js 16 App Router, React 19, TypeScript, Tailwind CSS |
| **State** | Zustand (client) + TanStack Query (server) |
| **Build** | `pip install -e ".[dev]"` / `npm ci` in `frontend/` |

## Directory Descriptions

| Path | Purpose |
|------|---------|
| `src/api/routes/` | All HTTP endpoints organized by domain (chat, conversations, learning, stats, health, auth) |
| `src/api/deps/legacy_auth.py` | `get_current_user` dependency for `/api/*` endpoints |
| `src/config/settings.py` | Pydantic Settings with production validation (`validate_production()`) |
| `src/db/session.py` | Single async DB session factory; no sync layer |
| `src/monitoring/health.py` | Real dependency probes (Postgres, Redis, Qdrant) |
| `src/utils/auth.py` | JWT create/decode, password hashing, `TokenData` model |
| `frontend/src/lib/api.ts` | `apiUrl(path)` helper — single source for backend URL |
| `frontend/src/app/*/error.tsx` | Next.js error boundaries per route segment |
| `infrastructure/kubernetes/` | Production K8s manifests with HPA, PDB, NetworkPolicy, ServiceMonitor |

## Commands

```bash
# Local development
./start_project.sh              # Sets up venv, installs deps, runs migrations, starts API + Frontend
./run_server.sh                 # Runs API only (src.api.main:app)

# Docker
docker compose up -d            # Full stack (API, Postgres, Qdrant, Redis, Neo4j, Prometheus, Grafana)

# Testing
pytest tests/ -v --cov=src --cov=modelx_voice
cd frontend && npm test

# Linting
ruff check src/ modelx_voice/
black --check src/ modelx_voice/
mypy src/ --ignore-missing-imports
cd frontend && npm run lint

# Database
alembic upgrade head
alembic revision --autogenerate -m "description"
```

## Deprecated / Archived

- `src/web_server.py` → archived as `src/web_server.py.archived` (was the monolith entry point)
- `src/config/database.py` → removed (sync DB layer)
- `src/utils/logging.py` → removed (duplicate of `src/config/logging.py`)
- `src/utils/metrics.py` → removed (duplicate of `src/monitoring/prometheus.py`)
- `requirements*.txt` → removed (all deps in `pyproject.toml`)

---

*Updated during production-readiness audit. Keep this file in sync with actual repo structure.*