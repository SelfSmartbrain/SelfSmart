# 3. Architecture Analysis

ModelX employs a microservices-inspired, highly decoupled internal architecture built around FastAPI and LangGraph, backed by polyglot persistence.

## Overall System Architecture

The architecture relies on a multi-tier persistence model connected to a centralized API, which orchestrates various cognitive engines.

```mermaid
graph TD
    Client[Client Apps / CLI / Frontend] -->|REST / HTTP| API[FastAPI Server]
    
    subgraph Core Platform
        API --> Registry[Service Registry]
        Registry --> Cog[Cognitive Engines]
        Registry --> Mem[Memory System]
        Registry --> Exec[Execution Runtime]
    end
    
    subgraph Persistence Layer
        Mem --> PG[(PostgreSQL)]
        Mem --> QD[(Qdrant Vector DB)]
        Mem --> N4J[(Neo4j Graph DB)]
        Exec --> Redis[(Redis Cache)]
    end
    
    subgraph AI Layer
        Cog --> LLM[LLM Providers]
        Cog --> LangGraph[LangGraph Workflows]
    end
    
    subgraph Execution
        Exec --> Sandbox[Isolated Code Sandbox]
        Exec --> Worker[APScheduler Worker]
    end
```

## Component Relationships

- **Service Registry (`src/core/service_registry.py`)**: Acts as the central nervous system, lazily loading and managing singletons of `PerformanceTracker`, `LearningVelocityTracker`, `CognitionReflectionAgent`, `FailureAnalyzer`, `MetaLearningEngine`, etc.
- **API (`src/api/main.py`)**: Mounts highly segmented routers (Goals, Tasks, Memory, Knowledge, Reflections, Meta, Vision, Swarm).
- **Execution Engine**: Leverages LangGraph for stateful workflow execution, with PostgreSQL (`langgraph-checkpoint-postgres`) providing checkpointing and recovery.

## API Request Lifecycle

```mermaid
sequenceDiagram
    participant User
    participant FastAPI
    participant Middleware
    participant ServiceRegistry
    participant Engine
    participant DB

    User->>FastAPI: POST /api/v1/tasks
    FastAPI->>Middleware: Auth & Rate Limit Check
    Middleware->>ServiceRegistry: Inject dependencies
    ServiceRegistry->>Engine: Process Task
    Engine->>DB: Fetch/Store Context (PG/Qdrant)
    Engine-->>FastAPI: Result
    FastAPI-->>User: 200 OK Response
```

## Data Persistence Strategy

The system utilizes specialized databases for different data shapes:
1. **PostgreSQL**: Relational data, user accounts, agent metadata, configuration, execution checkpoints.
2. **Qdrant**: High-dimensional vector embeddings for semantic search, RAG, and semantic memory.
3. **Neo4j**: Graph relationships, knowledge lineage, and conceptual mapping.
4. **Redis**: Ephemeral cache, rate limiting, and fast key-value lookups.

## Sandboxing & Execution
Code execution is isolated via a dedicated Docker container (`sandbox` service in `docker-compose.yml`), constrained with `no-new-privileges`, memory limits, and a read-only filesystem (with a `tmpfs` volume), ensuring the host system is protected from maliciously generated or buggy agent code.
