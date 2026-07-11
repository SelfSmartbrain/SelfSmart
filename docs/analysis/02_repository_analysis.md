# 2. Repository Structure Analysis

The ModelX repository is highly modularized, adopting a Domain-Driven Design (DDD) approach applied to AI cognitive architectures. 

## Root Level Directories

- `/src/` - The primary source code directory containing all backend platform logic.
- `/docs/` - Documentation, architecture diagrams, and analysis reports.
- `/tests/` - Test suites (unit, integration, e2e, adversarial, performance).
- `/docker/` - Dockerfiles, prometheus configs, grafana provisioning, and sandbox setups.
- `/alembic/` - PostgreSQL database migrations.
- `/frontend/` - (Inferred via docker-compose) Next.js frontend application.

## Detailed `src/` Directory Breakdown

The `src/` folder is divided into an unprecedented number of domains (56+ directories), which can be conceptually grouped as follows:

### 1. Platform Core & Infrastructure
- `api/` - FastAPI application entry points, middleware, dependencies, and REST API routes.
- `config/` - System configuration, environment variable mapping (`pydantic-settings`), and logging setups.
- `core/` - Foundational system components, specifically the `ServiceRegistry` for dependency injection.
- `db/` - Database connection management, ORM models, and transaction handling.
- `storage/` - Abstractions for persistence layers.
- `cli/` - Command Line Interface tools (using Click/Prompt Toolkit) for interacting with the platform.
- `runtime/` - Execution engines and loop managers.

### 2. Cognitive Architecture & AI Engines
- `cognition/` - Advanced cognitive modules including `reflection_agent`, `failure_analyzer`, `meta_learning_engine`, `skill_discovery`, and `self_improvement`.
- `cognitive_attention/` - Mechanisms for focusing agent context window on relevant information.
- `cognitive_communication/` - Protocols for inter-agent communication.
- `cognitive_kernel/` - The core "brain" loop orchestrating cognitive functions.
- `mental_models/` - Frameworks for the agent to simulate and predict world states.
- `decision/` - Decision-making algorithms and heuristics.
- `reasoning/` - Advanced reasoning chains (e.g., Chain of Thought, Tree of Thoughts).
- `world_model/` - The agent's internal representation of the external environment.

### 3. Memory & Knowledge Systems
- `memory/` - Implementations of Short-Term, Long-Term, Episodic, and Semantic memory.
- `knowledge/` - Knowledge management and retrieval.
- `knowledge_graph/` - Neo4j integrations for relationship mapping.
- `knowledge_fitness/` & `knowledge_lineage/` & `knowledge_compression/` - Advanced lifecycle management for stored information to prevent context bloat.
- `rag/` - Retrieval-Augmented Generation pipelines (document ingestion, chunking, retrieval).

### 4. Agent Execution & Tooling
- `agents/` - Base agent classes and specific agent persona implementations.
- `agent_society/` & `swarm/` - Multi-agent orchestration and swarm intelligence paradigms.
- `tools/` - The tool registry and concrete tool implementations (e.g., Web Search, File IO).
- `capabilities/` & `capability/` - Abstractions defining what an agent can and cannot do.
- `sandbox/` - Secure code execution environment management.

### 5. Learning & Autonomy
- `learning/` - General learning interfaces.
- `evolution/` - Genetic algorithms or iterative improvement paradigms for prompts/strategies.
- `autonomous_development/` - Mechanisms for the agent to write and improve its own code.
- `autonomy/` - Core autonomous loop managers.
- `self_play/` - Environments for agents to simulate interactions and learn from synthetic experiences.

### 6. Specialized Domains
- `coding/` - Specialized logic for writing, reviewing, and executing code.
- `multimodal/` & `vision/` - Processing and analyzing images/video/speech.
- `scientific_discovery/` - Hypothesizing and research workflows.
- `research_programs/` - Structured long-horizon research plans.
- `theories/` - Internal hypothesis testing frameworks.

### 7. Governance, Monitoring & Evaluation
- `monitoring/` - Observability, metrics tracking, and performance logging.
- `reporting/` - Generating insights and intelligence reports.
- `evaluation/` & `validation/` & `review/` & `testing/` - Evaluating agent performance, checking tool output, and ensuring safety boundaries.
- `safety/` - Prompt injection protection, output sanitization, and guardrails.
- `governance/` - Policy enforcement for autonomous actions.
