## SECTION 17: DEVELOPER GUIDE

### Environment Setup
1. **Python**: Require Python 3.11+.
2. **Virtual Env**: `python -m venv venv && source venv/bin/activate`
3. **Dependencies**: `pip install -e .[dev]` (Installs pytest, black, mypy).
4. **Infrastructure**: `docker-compose up -d postgres qdrant redis neo4j`
5. **Migrations**: `alembic upgrade head`

### Adding a New Agent
1. Create `src/agents/new_agent.py`.
2. Define the prompt and input/output Pydantic schemas.
3. Import the agent into `src/agents/orchestrator.py`.
4. Update `AgentStateDict` in `src/agents/state.py` if the agent introduces new state variables.
5. Add a node in `_build_graph()` and map the conditional edges.

### Adding New Memory Types
If you need a new memory classification (e.g., "Visual Memory"):
1. Update Postgres Enums in `src/db/enums.py`.
2. Run `alembic revision --autogenerate -m "Add visual memory"`.
3. Update `MemoryAgent` to route logic appropriately.

---

## SECTION 18: TESTING DOCUMENTATION

ModelX uses `pytest` for all verification.

### Testing Strategy

#### 1. Unit Tests (`tests/unit/`)
- **Scope**: Individual functions, Pydantic validations, Utility classes.
- **Mocking**: All LLM calls and Database I/O must be mocked using `unittest.mock`.
- **Goal**: Fast feedback loop (runs in < 2 seconds).

#### 2. Integration Tests (`tests/integration/`)
- **Scope**: API endpoints, Database Repositories, Qdrant ingestion.
- **Mocking**: LLM calls are mocked. Databases are real (using a `test_db` instance spun up in Docker).
- **Goal**: Ensure schemas and network layers map correctly.

#### 3. E2E Tests (`tests/e2e/`)
- **Scope**: Full LangGraph execution from Goal -> Output.
- **Mocking**: None. Real LLMs and Real DBs are used.
- **Cost Warning**: E2E tests consume actual Anthropic/OpenAI tokens. Run only before merges to `main`.

### Coverage Goals
- Standard: 85%+ branch coverage.
- Excluded from coverage: `alembic/versions/` and generic interfaces.

---

## SECTION 19: PERFORMANCE DOCUMENTATION

ModelX performance is bottlenecked primarily by network I/O (LLM APIs) and context window limitations.

### Targets
- **API Latency**: < 200ms for non-execution endpoints (e.g., getting task status).
- **Orchestration Loop**: ~1-3 seconds per LangGraph node transition.
- **Task Execution**: Highly variable (5 seconds to 5 minutes depending on code execution or research depth).

### Token Usage & Constraints
- Anthropic Claude 3.5 Sonnet supports 200k tokens, but performance degrades above 100k.
- **Target**: Keep `AgentStateDict` message history under 30k tokens.
- **Mechanism**: The `MemoryConsolidator` aggregates old messages into summaries, and LangGraph is configured to pop old raw messages from the state array once they exceed the threshold.

### Resource Requirements
- **PostgreSQL**: 2 CPU, 4GB RAM minimum.
- **Qdrant**: 4 CPU, 16GB RAM recommended for production (vector search is memory intensive).
- **Neo4j**: 2 CPU, 4GB RAM.
- **FastAPI Workers**: 1 CPU, 1GB RAM per worker (I/O bound, not CPU bound).
