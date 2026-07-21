# Test Coverage Improvement Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement comprehensive unit tests to increase overall code coverage to 90% by addressing all TODO items 034-043.

**Architecture:** This plan follows a risk-based prioritizing high-impact areas first) LLM providers, databases, frontend components, then integrating with existing test infrastructure.

**Tech Stack:** Python (pytest, pytest-asyncio, unittest.mock), JavaScript/TypeScript (Jest, @testing-library/react), SQLite for in-memory testing

## Global Constraints

- Maintain existing test patterns and conventions
- Use pytest for Python backend tests
- Use Jest and React Testing Library for frontend tests
- Mock external dependencies appropriately
- Achieve ≥90% overall coverage with ≥85% per area
- All tests must pass in local and CI environments
- Follow existing code style and formatting standards
- Make frequent, small commits with descriptive messages

---

### Phase 1: High Priority Areas (Weeks 1-2)

#### Task 1: Set up test environment and baseline measurements

**Files:**
- Create: `docs/superpowers/plans/2026-07-21-test-coverage-baseline.md`
- Modify: `.gitignore:0` (if needed for coverage reports)

**Interfaces:**
- None (establishing baseline)

- [ ] **Step 1: Run existing tests to establish baseline coverage**
```bash
# Run backend tests
python -m pytest tests/ --cov=src --cov-report=term-missing

# Run frontend tests if they exist
# npm test -- --coverage (adjust based on actual setup)
```
Expected: See current coverage percentages

- [ ] **Step 2: Document baseline coverage numbers**
```markdown
# Baseline Coverage Measurement

## Backend Coverage
- Overall: XX%
- By module:
  - src/api/routes/: XX%
  - src/llm/: XX%
  - src/db/repositories/: XX%
  - etc.

## Frontend Coverage
- Overall: XX%
- By component:
  - ChatInterface: XX%
  - etc.
```
Expected: Document created with baseline metrics

- [ ] **Step 3: Commit baseline documentation**
```bash
git add docs/superpowers/plans/2026-07-21-test-coverage-baseline.md
git commit -m "docs: record baseline coverage measurements"
```
Expected: Baseline documentation committed

#### Task 2: Implement Chat Endpoint Tests (TODO-034)

**Files:**
- Create: `tests/unit/test_chat_endpoints.py`
- Create: `tests/unit/test_chat_stream_endpoint.py`
- Modify: None (if no existing test files)

**Interfaces:**
- Consumes: Functions from `src/api/routes/chat.py`
- Produces: Test coverage for chat endpoints

- [ ] **Step 1: Write failing test for basic chat endpoint**
```python
import pytest
from unittest.mock import AsyncMock, patch
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_chat_endpoint_success():
    """Test successful chat request"""
    with patch('src.api.routes.chat.conversation_manager') as mock_conv_mgr, \
         patch('src.api.routes.chat.rag_service') as mock_rag, \
         patch('src.api.routes.chat.get_llm_client') as mock_llm, \
         patch('src.api.routes.chat.learner') as mock_learner:
        
        # Setup mocks
        mock_conv_mgr.create_conversation = AsyncMock(return_value="test-conv-id")
        mock_conv_mgr.get_conversation_owner = AsyncMock(return_value="test@example.com")
        mock_conv_mgr.add_message = AsyncMock()
        mock_conv_mgr.get_conversation_messages = AsyncMock(return_value=[])
        mock_rag.use_rag = False
        mock_llm_instance = AsyncMock()
        mock_llm_instance.chat_completion = AsyncMock(return_value=type('obj', (object,), {
            'choices': [type('obj', (object,), {'message': type('obj', (object,), {'content': 'Test response'})})],
            'usage': {'prompt_tokens': 10, 'completion_tokens': 20}
        })())
        mock_llm.return_value = mock_llm_instance
        mock_learner.is_active = False
        
        # Make request
        response = client.post(
            "/chat",
            json={"message": "Hello"},
            headers={"Authorization": "Bearer test-token"}
        )
        
        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert "response" in data
        assert data["response"] == "Test response"
        assert "conversation_id" in data
```

- [ ] **Step 2: Run test to verify it fails**
```bash
python -m pytest tests/unit/test_chat_endpoints.py::test_chat_endpoint_success -v
```
Expected: FAIL with import or attribute errors

- [ ] **Step 3: Implement minimal solution to make test pass**
```bash
# Actually, we're writing tests for existing code, so this step is about
# ensuring our test setup is correct and the test passes with existing implementation
# If the test fails due to our test setup, we fix the test, not the implementation
```

- [ ] **Step 4: Run test to verify it passes**
```bash
python -m pytest tests/unit/test_chat_endpoints.py::test_chat_endpoint_success -v
```
Expected: PASS (assuming existing implementation works)

- [ ] **Step 5: Commit initial chat endpoint tests**
```bash
git add tests/unit/test_chat_endpoints.py
git commit -m "feat: add basic chat endpoint tests"
```
Expected: Test file committed

[Continue with additional tests for chat endpoint covering:
- Streaming endpoint
- Error cases
- Authentication/authorization
- RAG integration
- Input sanitization
- Conversation ownership validation
etc.]

#### Task 3: Implement RAG Service Tests (TODO-035)

**Files:**
- Create: `tests/unit/test_rag_service.py`
- Create: `tests/unit/test_retriever.py`

**Interfaces:**
- Consumes: Functions from `src/llm/rag_service.py` and `src/rag/retriever.py`
- Produces: Test coverage for RAG services

[Similar structure to Task 2 - write failing tests, run them, verify they pass with existing code, commit]

#### Task 4: Implement LLM Provider Tests (TODO-036)

**Files:**
- Create: `tests/unit/test_gemini_client.py`
- Create: `tests/unit/test_deepseek_client.py`
- Create: `tests/unit/test_provider.py`

**Interfaces:**
- Consumes: Functions from `src/llm/gemini_client.py`, `src/llm/deepseek_client.py`, `src/llm/provider.py`
- Produces: Test coverage for LLM providers

[Similar structure]

#### Task 5: Implement Database Repository Tests (TODO-039)

**Files:**
- Create: `tests/unit/test_repository_base.py`
- Create: `tests/unit/test_user_repo.py`
- Create: `tests/unit/test_session_repo.py`
- [Continue for each repository file]

**Interfaces:**
- Consumes: Functions from `src/db/repositories/*.py`
- Produces: Test coverage for database repositories

[Similar structure, using in-memory SQLite for database tests]

### Phase 2: Medium Priority Areas (Week 3)

#### Task 6: Implement Frontend Component Tests (TODO-040)

**Files:**
- Create: `frontend/src/components/ChatInterface/__tests__/ChatInterface.test.js`
- Create: `frontend/src/components/ChatMessage/__tests__/ChatMessage.test.js`
- Create: `frontend/src/hooks/__tests__/useChatStore.test.js`
- [Continue for each component/hook]

**Interfaces:**
- Consumes: Components from `frontend/src/`
- Produces: Test coverage for frontend components

[Similar structure but using Jest and React Testing Library]

#### Task 7: Implement Conversation Manager Tests (TODO-038)

**Files:**
- Create: `tests/unit/test_conversation_manager.py`

**Interfaces:**
- Consumes: Functions from `src/llm/conversation_manager.py`
- Produces: Test coverage for conversation manager

[Similar structure]

#### Task 8: Implement Worker/Scheduler Tests (TODO-041)

**Files:**
- Create: `tests/unit/test_worker_base.py`
- Create: `tests/unit/test_specific_workers.py` [as needed]

**Interfaces:**
- Consumes: Functions from `src/workers/`
- Produces: Test coverage for workers/schedulers

[Similar structure]

### Phase 3: Lower Priority Areas (Week 4)

#### Task 9: Implement DPO/LoRA Trainer Tests (TODO-037)

**Files:**
- Create: `tests/unit/test_dpo_trainer.py`
- Create: `tests/unit/test_lora_trainer.py`

**Interfaces:**
- Consumes: Functions from `src/llm_training/dpo_trainer.py` and `src/llm_training/lora_trainer.py`
- Produces: Test coverage for training components

[Similar structure]

#### Task 10: Implement MCP Client Tests (TODO-042)

**Files:**
- Create: `tests/unit/test_mcp_client.py`

**Interfaces:**
- Consumes: Functions from `src/tools/mcp_client.py`
- Produces: Test coverage for MCP client

[Similar structure]

#### Task 11: Implement Rate Limiter Tests (TODO-043)

**Files:**
- Create: `tests/unit/test_rate_limit_distributed.py`

**Interfaces:**
- Consumes: Functions from `src/api/rate_limit_distributed.py`
- Produces: Test coverage for rate limiter

[Similar structure]

#### Task 12: Final Coverage Measurement and Report

**Files:**
- Modify: `docs/superpowers/plans/2026-07-21-test-coverage-final.md`

**Interfaces:**
- None (reporting)

- [ ] **Step 1: Run final coverage measurements**
```bash
# Run all tests with coverage
python -m pytest tests/ --cov=src --cov-report=html --cov-report=term-missing

# For frontend if applicable
# npm test -- --coverage
```
Expected: Coverage reports generated

- [ ] **Step 2: Document final coverage**
```markdown
# Final Coverage Measurement

## Target: ≥90% overall coverage with ≥85% per area

## Results
- Overall Coverage: XX%
- Target Met: [YES/NO]

## By Area
- Chat Endpoints: XX% [TARGET: ≥85%]
- RAG Service: XX% [TARGET: ≥85%]
- LLM Providers: XX% [TARGET: ≥85%]
- Database Repositories: XX% [TARGET: ≥85%]
- Frontend Components: XX% [TARGET: ≥85%]
- Conversation Manager: XX% [TARGET: ≥85%]
- Workers/Schedulers: XX% [TARGET: ≥85%]
- DPO/LoRA Trainers: XX% [TARGET: ≥85%]
- MCP Client: XX% [TARGET: ≥85%]
- Rate Limiter: XX% [TARGET: ≥85%]
```
Expected: Final coverage document created

- [ ] **Step 3: Commit final documentation and any additional tests**
```bash
git add docs/superpowers/plans/2026-07-21-test-coverage-final.md
git commit -m "docs: record final coverage measurements"
```
Expected: Final documentation committed

## Acceptance Criteria Verification

- [ ] Overall code coverage reaches ≥90%
- [ ] Each TODO area (034-043) achieves ≥85% coverage
- [ ] All new tests follow existing test patterns and conventions
- [ ] Tests are maintainable and provide meaningful coverage
- [ ] Critical paths and edge cases are adequately tested
- [ ] All tests pass in local development environment
- [ ] All tests pass in CI/CD pipeline
- [ ] No significant increase in test flakiness