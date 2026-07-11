# SelfSmart AI - Roadmap

**⚠️ IMPORTANT: This document describes planned features that are NOT currently implemented.**

The current SelfSmart system is a RAG-enhanced chatbot with manual fine-tuning scripts. The features below are aspirational and require significant engineering work.

---

## Phase 1: Automation (NOT IMPLEMENTED)

### Automated Training Pipeline
- **Status**: NOT IMPLEMENTED
- **Description**: Currently, LoRA and DPO training require manual script execution. This phase would add:
  - Cron job or scheduler for automatic training runs
  - CI/CD pipeline for model training and validation
  - Automatic model deployment on successful training
- **Dependencies**: Model versioning, evaluation gates, data versioning

### Scheduled Data Collection
- **Status**: PARTIALLY IMPLEMENTED
- **Description**: The `continuous_learner.py` has scheduling logic but requires manual trigger. This phase would add:
  - Automated cron jobs for periodic web crawling
  - Configurable crawl schedules (hourly, daily, weekly)
  - Automatic RAG vector store updates
- **Current State**: Manual execution via `build_dataset.py` and `ingest_data.py`

---

## Phase 2: Autonomous Agents (NOT IMPLEMENTED)

### Autonomous Market Analyst
- **Status**: NOT IMPLEMENTED
- **Description**: Deployed agent that automatically:
  - Scrapes financial RSS feeds, SEC filings, and social sentiment
  - Stores quotes in RAG for immediate Q&A
  - Fine-tunes itself on macro-trends overnight
- **Required Work**: 
  - Domain-specific data sources
  - Automated training pipeline
  - Evaluation metrics for financial accuracy

### Corporate Intelligence Hub
- **Status**: NOT IMPLEMENTED
- **Description**: Connected to internal systems:
  - Slack integration for conversation indexing
  - Jira/Confluence integration for documentation
  - Continuous learning of company jargon and culture
- **Required Work**:
  - Authentication with internal systems
  - Data source connectors
  - Privacy and access controls

### Personalized Research Assistant
- **Status**: NOT IMPLEMENTED
- **Description**: Domain-specific research assistant:
  - Digests academic papers (PubMed, arXiv)
  - Tracks legal rulings and regulations
  - Updates knowledge base weekly
- **Required Work**:
  - Academic paper parsing
  - Citation tracking
  - Domain-specific evaluation metrics

---

## Phase 3: Production-Grade MLOps (NOT IMPLEMENTED)

### Model Registry
- **Status**: NOT IMPLEMENTED
- **Description**: 
  - MLflow or similar model versioning system
  - Automatic checkpoint tagging with metadata
  - Model lineage tracking (data hash, eval scores)
- **Current State**: Checkpoints saved to `./model_checkpoints` with no versioning

### Automated Evaluation Gates
- **Status**: NOT IMPLEMENTED
- **Description**:
  - Pre-training evaluation on golden dataset
  - Post-training regression detection
  - Automatic rollback on quality degradation
- **Current State**: No automated evaluation exists

### Blue-Green Deployment
- **Status**: NOT IMPLEMENTED
- **Description**:
  - Zero-downtime model swapping
  - A/B testing for new models
  - Automatic rollback on error rates
- **Current State**: Model loading requires server restart

### Monitoring and Alerting
- **Status**: NOT IMPLEMENTED
- **Description**:
  - Prometheus metrics for all components
  - Grafana dashboards for system health
  - Alerting on training failures, RAG degradation
- **Current State**: Basic logging only, no metrics

---

## Phase 4: Architecture Improvements (NOT IMPLEMENTED)

### Microservices Architecture
- **Status**: NOT IMPLEMENTED
- **Description**:
  - Separate RAG service
  - Separate inference service
  - Separate training service
  - API gateway for orchestration
- **Current State**: Monolithic FastAPI application

### Circuit Breakers and Fallbacks
- **Status**: NOT IMPLEMENTED
- **Description**:
  - Graceful degradation on ChromaDB failure
  - Fallback to API LLM when MLX unavailable
  - Rate limiting per dependency
- **Current State**: Single points of failure exist

### Health Check Endpoints
- **Status**: NOT IMPLEMENTED
- **Description**:
  - `/health` for overall system status
  - `/health/rag` for ChromaDB connectivity
  - `/health/inference` for MLX/API status
  - `/health/dependencies` for external APIs
- **Current State**: Basic `/health` endpoint only

---

## Implementation Priority

**Immediate (Next 90 Days)**:
1. Model versioning (Issue #8)
2. Data versioning (Issue #7)
3. Basic evaluation metrics (Issue #19)
4. Health check endpoints (Issue #16)

**Short-term (3-6 Months)**:
5. Automated training pipeline
6. Scheduled data collection
7. Circuit breakers for dependencies
8. Monitoring and alerting

**Long-term (6-12 Months)**:
9. Microservices architecture
10. Autonomous agent frameworks
11. Domain-specific connectors
12. Blue-green deployment

---

## Contributing to Roadmap

If you want to work on a roadmap item:
1. Check if dependencies are implemented
2. Create a design document for the feature
3. Submit a PR with clear "NOT IMPLEMENTED" removal
4. Update this ROADMAP.md upon completion
