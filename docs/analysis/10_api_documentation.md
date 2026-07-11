# 10. API Documentation

ModelX exposes a highly modular, RESTful API built on FastAPI. 
The API acts as the primary interface for triggering workflows, managing memory, and observing cognitive states.

## General Setup
- **Base Path:** `/api/v1`
- **Framework:** FastAPI
- **OpenAPI/Swagger:** Available at `/docs` (when `ENVIRONMENT != production`)
- **Authentication:** JWT via Bearer token (or `X-API-Key` header for service accounts).

## Core API Domains (Routes)

1. **Authentication (`/auth`)**
   - Handles login, token generation, and user management.
2. **Health (`/health`)**
   - Returns system readiness and liveness checks (verifying DB, Redis, Qdrant).
3. **Goals (`/goals`)**
   - CRUD operations for high-level objectives assigned to agents.
4. **Tasks (`/tasks`)**
   - Sub-objectives that belong to goals. Triggers the `TaskRuntime` execution.
5. **Memory (`/memory`)**
   - Direct endpoints to query or update the agent's short-term, long-term, and episodic memory.
6. **Knowledge (`/knowledge`)**
   - RAG ingestion endpoints (e.g., upload PDF) and semantic search endpoints.
7. **Reflections (`/reflections`)**
   - Endpoints to retrieve the agent's self-reflection logs and failure analyses.
8. **Meta-Learning (`/meta`)**
   - Exposes metrics from the `LearningVelocityTracker` and `SkillDiscovery` engines.
9. **Vision / Multimodal (`/vision`)**
   - Endpoints for processing images and extracting OCR text.
10. **Swarm (`/swarm`)**
    - Multi-agent coordination endpoints (e.g., creating an agent society, broadcasting messages).
11. **Dashboard (`/dashboard`)**
    - Aggregated metrics for frontend visualization.

## Rate Limiting & Streaming
- **Rate Limiting:** Managed via Redis (implied by Redis inclusion in `docker-compose.yml` and cache requirements).
- **Streaming:** FastAPI natively supports Server-Sent Events (SSE). It is highly probable that execution outputs (e.g., LLM tokens or thought processes) can be streamed to the client via chunked transfers.
