# Test Coverage Improvement Plan
**Date:** 2026-07-21  
**Status:** Approved  

## Scope and Objectives

### Primary Objective
Increase overall test coverage from current levels to 90% by implementing comprehensive unit tests for the identified TODO items (034-043).

### Scope Definition

**In Scope:**
- Unit tests for all listed TODO items (034-043)
- Chat endpoint tests (`/chat` and `/chat/stream`)
- RAG service tests (retrieval, reranking, query enhancement)
- LLM provider tests (Gemini, DeepSeek, provider abstraction)
- Training component tests (DPO/LoRA trainers)
- Conversation manager tests
- Database repository tests (all repository classes)
- Frontend component tests (ChatInterface, ChatMessage, useChatStore, useStream, DashboardContent, KnowledgeContent, SettingsContent)
- Worker/scheduler tests
- MCP client tests
- Rate limiter tests

**Out of Scope:**
- End-to-end/integration tests (unless directly supporting unit test goals)
- Performance/load testing
- Security penetration testing
- UI/UX testing beyond component unit tests
- Documentation improvements (beyond test documentation)

### Success Criteria
1. Achieve ≥90% overall code coverage
2. Each TODO area reaches ≥85% coverage individually
3. All new tests follow existing test patterns and conventions
4. Tests are maintainable and provide meaningful coverage (not just line coverage)
5. Critical paths and edge cases are adequately tested

## Test Strategy and Approach

### Overall Approach
- **Risk-based prioritization:** Start with high-risk/high-impact areas: chat endpoints, LLM providers, database repositories, and RAG service
- **Test Types:** Focus on unit tests with appropriate mocking of external dependencies
- **Testing Frameworks:**
  - Backend (Python): Continue using `pytest` with `pytest-asyncio` for async tests and `unittest.mock` for patching
  - Frontend (React): Use `Jest` and `@testing-library/react` for component tests
  - Mocking: Use `unittest.mock` for Python, `jest.mock()` for JavaScript/TypeScript
- **Test Organization:**
  - Backend tests in `tests/unit/` mirroring source structure (e.g., `tests/unit/test_chat_endpoints.py`)
  - Frontend tests colocated with components in `__tests__` files or in `tests/` directory under `frontend/src` following existing patterns
- **Mocking Strategy:**
  - External APIs (Gemini, DeepSeek): Mock at client/provider level
  - Database: Use in-memory SQLite or mock repository layers where appropriate
  - RAG components: Mock vector store and embedding services
  - Internal services: Mock dependencies at service boundaries (e.g., mock `rag_service` when testing chat endpoints)
- **Coverage-Driven:** Write tests specifically to increase line and branch coverage in target files, focusing on:
  - Normal/expected flows
  - Error conditions and edge cases
  - Input validation and sanitization
  - Boundary conditions
- **Test Data:** Use factories/fixtures for consistent test data where needed
- **Async Testing:** Properly handle async/await patterns with `pytest.mark.asyncio` and async test functions

### Development Process
1. For each target area, first examine existing tests to understand patterns
2. Create test file structure following project conventions
3. Implement tests for core functionality first, then edge cases
4. Run tests frequently to ensure they pass and contribute to coverage
5. Use coverage reports to identify gaps and add tests until targets are met

## Test Coverage Areas

### 1. Chat Endpoint Tests (TODO-034) - 6 hours
**Target:** `src/api/routes/chat.py` and related services
**Focus Areas:**
- Input sanitization via `sanitize_user_message`
- Conversation creation and ownership validation
- Message persistence and retrieval
- RAG integration (conditional based on configuration)
- LLM client interaction and response handling
- Streaming responses and Server-Sent Events formatting
- Error handling and HTTP status codes
- Rate limiting integration
- Learning system integration

**Test Approach:**
- Mock `conversation_manager`, `rag_service`, `llm_client`, and `learner`
- Test both `/chat` (non-streaming) and `/chat/stream` endpoints
- Verify request/response formats match schemas
- Test authentication and authorization flows
- Validate error cases (invalid input, service failures, etc.)

### 2. RAG Service Tests (TODO-035) - 6 hours
**Target:** `src/llm/rag_service.py` and `src/rag/retriever.py`
**Focus Areas:**
- Vector search functionality and similarity scoring
- Cross-encoder reranking logic
- Query enhancement/rewriting capabilities
- Context compression and truncation strategies
- Embedding generation and caching
- Document retrieval and ranking algorithms
- Error handling for vector store failures
- Configuration and feature flag handling

**Test Approach:**
- Mock external vector stores (Pinecone, Weaviate, etc.)
- Mock embedding services
- Test with various document sets and query types
- Verify relevance scoring and ranking behavior
- Test edge cases (empty results, low similarity scores, etc.)

### 3. LLM Provider Tests (TODO-036) - 6 hours
**Target:** `src/llm/gemini_client.py`, `src/llm/deepseek_client.py`, `src/llm/provider.py`
**Focus Areas:**
- API call formatting and parameter handling
- Response parsing and normalization
- Streaming implementation and chunk handling
- Error handling and retry mechanisms
- Provider abstraction and switching logic
- Configuration management and credential handling
- Rate limiting and token counting
- Fallback behaviors

**Test Approach:**
- Mock HTTP clients/APIs for each provider
- Test various response formats and error conditions
- Validate consistent interface across providers
- Test streaming vs. non-streaming modes
- Verify proper error propagation and handling

### 4. DPO/LoRA Trainer Tests (TODO-037) - 4 hours
**Target:** `src/llm_training/dpo_trainer.py` and `src/llm_training/lora_trainer.py`
**Focus Areas:**
- Configuration generation and validation
- Dataset formatting and preprocessing
- Training loop execution (mocked)
- Model saving/loading and version management
- Hyperparameter handling and validation
- Resource cleanup and checkpointing
- Integration with training data pipeline

**Test Approach:**
- Mock ML training frameworks (PyTorch, Transformers, etc.)
- Test with synthetic datasets
- Verify configuration correctness
- Test error handling and recovery scenarios
- Validate output formats and metadata

### 5. Conversation Manager Tests (TODO-038) - 4 hours
**Target:** `src/llm/conversation_manager.py`
**Focus Areas:**
- Conversation creation, retrieval, updating, and deletion
- Message persistence and retrieval
- History management and context windowing
- Ownership and access control enforcement
- Concurrent access handling
- Storage backend interactions
- Metadata and tagging systems

**Test Approach:**
- Mock storage/persistence layer
- Test CRUD operations comprehensively
- Verify ownership and permission checks
- Test edge cases (concurrent modifications, invalid IDs, etc.)
- Validate history truncation and summarization logic

### 6. Database Repository Tests (TODO-039) - 8 hours
**Target:** All files in `src/db/repositories/`
**Focus Areas:**
- CRUD operations for each entity type
- Query building and optimization
- Transaction management and rollback handling
- Connection pooling and resource management
- Error handling and constraint violation responses
- Pagination and filtering implementations
- Relationship handling and joins
- Bulk operations and batch processing

**Test Approach:**
- Use in-memory SQLite database for testing
- Test each repository class independently
- Verify proper SQL generation and execution
- Test edge cases (null values, duplicates, constraints)
- Validate transaction rollback behavior
- Performance test critical queries (where relevant)

### 7. Frontend Component Tests (TODO-040) - 12 hours
**Target:** ChatInterface, ChatMessage, useChatStore, useStreamingChat, DashboardContent, KnowledgeContent, SettingsContent
**Focus Areas:**
- Component rendering with various props
- User interaction handling (clicks, inputs, etc.)
- State management and updates
- API call mocking and response handling
- Loading and error states
- Accessibility compliance (where applicable)
- Responsive behavior testing
- Event propagation and callback handling

**Test Approach:**
- Use React Testing Library and Jest
- Mock API calls and context providers
- Test user interactions and state changes
- Verify rendering with different data states
- Test error and loading states
- Validate accessibility attributes where relevant

### 8. Worker/Scheduler Tests (TODO-041) - 4 hours
**Target:** `src/workers/` directory
**Focus Areas:**
- Job scheduling and queuing mechanisms
- Task execution and result handling
- Error recovery and retry logic
- Resource management and cleanup
- Concurrency and threading considerations
- Schedule parsing and trigger mechanisms
- Monitoring and reporting functionality

**Test Approach:**
- Mock external dependencies (databases, APIs, etc.)
- Test job lifecycle from creation to completion
- Verify scheduling accuracy and timing
- Test failure scenarios and retry mechanisms
- Validate resource cleanup and leak prevention

### 9. MCP Client Tests (TODO-042) - 3 hours
**Target:** `src/tools/mcp_client.py`
**Focus Areas:**
- STDIO transport establishment and communication
- Tool discovery and metadata retrieval
- Function invocation and parameter passing
- Response parsing and error handling
- Connection lifecycle management
- Timeout and retry mechanisms
- Security and permission handling

**Test Approach:**
- Mock subprocess and STDIO communication
- Test various message types and formats
- Verify proper JSON-RPC handling
- Test connection establishment and teardown
- Validate error propagation and handling
- Test timeout and retry behaviors

### 10. Rate Limiter Tests (TODO-043) - 3 hours
**Target:** `src/api/rate_limit_distributed.py`
**Focus Areas:**
- Window-based rate limiting algorithms
- Token bucket or leaky bucket implementations
- Redis integration and connection handling
- Tier-based limit configurations
- Key generation and scoping strategies
- Cleanup and expiration mechanisms
- Distributed coordination and consistency
- Metrics and monitoring integration

**Test Approach:**
- Mock Redis client and operations
- Test various rate limiting scenarios
- Verify window reset and cleanup behavior
- Test different rate limit tiers and configurations
- Validate distributed consensus mechanisms
- Test edge cases (burst traffic, clock skew, etc.)

## Test Environment and Tools

### Development Environment
- **Language Versions:** Python 3.9+, Node.js 18+
- **Testing Frameworks:** pytest (Python), Jest (JavaScript/TypeScript)
- **Mocking Libraries:** unittest.mock (Python), jest.mock() (JS/TS)
- **Coverage Tools:** pytest-cov (Python), Jest coverage (JS/TS)
- **CI/CD:** GitHub Actions (existing)
- **IDE/Editor:** VS Code with appropriate extensions

### Dependencies
- **Python:** pytest, pytest-asyncio, pytest-mock, factory-boy (if needed)
- **JavaScript/TypeScript:** jest, @testing-library/react, @testing-library/jest-dom
- **Database:** sqlite3 (for in-memory testing), possibly pytest-postgresql
- **External Services:** All mocked (no external service dependencies in unit tests)

### Configuration
- **Test Configuration:** Separate test configurations where needed
- **Environment Variables:** Use test-specific values or mocks
- **Secrets/API Keys:** All mocked or using test values
- **Database Connections:** In-memory SQLite for unit tests

### Reporting and Metrics
- **Coverage Reports:** HTML and terminal reports generated on test runs
- **Threshold Enforcement:** CI checks for minimum coverage thresholds
- **Trend Tracking:** Historical coverage data tracking
- **Gap Identification:** Regular reports on uncovered lines/branches

## Risks and Mitigations

### Risks
1. **Test Maintenance Overhead:** Risk of tests becoming brittle and requiring frequent updates
2. **Mock Accuracy:** Risk of mocks not accurately representing real behavior
3. **Coverage Illusion:** Risk of high line coverage but low actual test effectiveness
4. **Test Performance:** Risk of slow test suites slowing down development
5. **Integration Gaps:** Risk of missing integration points between units
6. **Resource Constraints:** Limited time for comprehensive test writing

### Mitigations
1. **Maintainable Tests:**
   - Focus on testing behavior, not implementation details
   - Use descriptive test names following Given/When/Then pattern
   - Keep tests DRY but readable
   - Regular test review and refactoring as part of development process

2. **Accurate Mocks:**
   - Base mocks on actual interface contracts
   - Update mocks when interfaces change
   - Use integration tests to validate critical mock assumptions
   - Prefer behavioral mocking over implementation mocking when possible

3. **Effective Testing:**
   - Prioritize testing business logic and edge cases
   - Use mutation testing tools periodically to assess test quality
   - Focus on paths that handle errors and boundary conditions
   - Review tests for actual value, not just coverage numbers

4. **Performance Management:**
   - Keep unit tests fast (<1ms ideal, <10ms acceptable)
   - Use appropriate test doubles to avoid slow operations
   - Parallelize test execution where possible
   - Mark slow tests appropriately and run them less frequently

5. **Integration Coverage:**
   - Supplement unit tests with targeted integration tests for critical paths
   - Use contract testing where services interact
   - Ensure end-to-end paths are covered by some form of testing

6. **Resource Management:**
   - Time-box testing efforts per component
   - Prioritize by risk and impact
   - Leverage existing test patterns and infrastructure
   - Consider pair programming for complex testing scenarios

## Timeline and Effort Estimates

### Total Estimated Effort: 56 hours

| Task Area | Estimated Hours | Priority Order |
|-----------|----------------|----------------|
| Chat Endpoint Tests (TODO-034) | 6 hours | 1 (High Risk/Impact) |
| RAG Service Tests (TODO-035) | 6 hours | 1 (High Risk/Impact) |
| LLM Provider Tests (TODO-036) | 6 hours | 1 (High Risk/Impact) |
| Database Repository Tests (TODO-039) | 8 hours | 1 (High Risk/Impact) |
| Frontend Component Tests (TODO-040) | 12 hours | 2 (Medium Risk/Impact) |
| Conversation Manager Tests (TODO-038) | 4 hours | 2 (Medium Risk/Impact) |
| Worker/Scheduler Tests (TODO-041) | 4 hours | 2 (Medium Risk/Impact) |
| DPO/LoRA Trainer Tests (TODO-037) | 4 hours | 3 (Lower Risk/Impact) |
| MCP Client Tests (TODO-042) | 3 hours | 3 (Lower Risk/Impact) |
| Rate Limiter Tests (TODO-043) | 3 hours | 3 (Lower Risk/Impact) |
| **Total** | **56 hours** | |

### Suggested Schedule
- **Week 1:** High-priority items (Chat, RAG, LLM Providers, DB Repos) - 26 hours
- **Week 2:** Medium-priority items (Frontend, Conversation, Workers) - 20 hours
- **Week 3:** Low-priority items (Training, MCP, Rate Limiting) + buffer - 10 hours

### Dependencies
- No external dependencies beyond existing test infrastructure
- Can be worked on in parallel by multiple contributors
- Each area is largely independent, allowing for distributed work

## Acceptance Criteria

### Definition of Done for Each Test Area
1. **Test Implementation:**
   - All planned tests written and passing
   - Tests follow existing project patterns and conventions
   - Appropriate use of mocks and test doubles
   - Clear, descriptive test names following Given/When/Then or similar convention

2. **Coverage Requirements:**
   - Individual file/module coverage ≥85%
   - Contribution to overall project coverage ≥90%
   - Critical paths and edge cases covered
   - No significant gaps in logical branches or error handling

3. **Code Quality:**
   - Tests follow project linting and formatting standards
   - No TODO/FIXME comments in test code (unless tracking specific improvements)
   - Tests are readable and maintainable
   - Proper setup and teardown where needed

4. **Integration:**
   - Tests run successfully in local development environment
   - Tests pass in CI/CD pipeline
   - No degradation in build/test performance
   - Coverage reports generated and available

### Overall Project Acceptance
1. Overall code coverage reaches ≥90% (measured across entire codebase)
2. All TODO areas (034-043) have ≥85% coverage
3. All new tests pass consistently in local and CI environments
4. No increase in test flakiness or false positives
5. Documentation updated as needed to reflect testing approach
6. Team review and sign-off on test quality and effectiveness

## References and Related Documents

### Project Documents
- [ARCHITECTURE.md](/ARCHITECTURE.md) - Overall system architecture
- [03_memory_and_rag.md](/docs/03_memory_and_rag.md) - RAG system details
- [05_api_and_workflows.md](/docs/05_api_and_workflows.md) - API and worker details
- [PROJECT_CHANGE_REPORT.md](/PROJECT_CHANGE_REPORT.md) - Recent changes and context

### Testing References
- Existing test patterns in `tests/unit/test_brain.py` (LLM provider testing example)
- Frontend testing patterns in existing frontend test files
- [PYTEST documentation](https://docs.pytest.org/)
- [JEST documentation](https://jestjs.io/)
- [REACT TESTING LIBRARY documentation](https://testing-library.com/docs/react-testing-library/intro/)

### Related Skills and Practices
- [TDD Workflow](/skills/ecc/tdd-workflow/SKILL.md) - Test-driven development approach
- [Python Testing](/skills/ecc/python-testing/SKILL.md) - Python testing patterns
- [React Testing](/skills/ecc/react-testing/SKILL.md) - React component testing
- [Mocking Strategies](/skills/ecc/mocking-patterns/SKILL.md) - Effective mocking techniques

## Open Questions and Decisions Needed

### Resolved Questions
1. **Approach:** Risk-based prioritization selected over sequential or grouped approaches
2. **Target Coverage:** 90% overall with 85% minimum per area
3. **Testing Frameworks:** Continue existing pytest/Jest patterns
4. **Mocking Strategy:** Mock external dependencies, test internal logic

### Open Questions for Clarification
1. **Test Data Strategy:** Should we invest in test data factories (e.g., factory_boy) or use simpler approaches?
2. **Frontend Test Location:** Should frontend tests be colocated with components or in a centralized tests directory?
3. **Performance Testing:** Should we include basic performance assertions in unit tests for critical paths?
4. **Test Data Management:** How should we handle test data that needs to resemble production data (PII considerations, etc.)?
5. **Legacy Code:** How much effort should be spent refactoring untestable code to make it testable vs. testing as-is?

### Decisions Made During Planning
1. We will follow existing test patterns in the codebase rather than introducing new frameworks
2. Each TODO area will be treated as a separate but related workstream
3. We will prioritize testing public interfaces and behaviors over private implementation details
4. Error handling and edge cases will be a key focus of our testing efforts
5. We will leverage mocking extensively to isolate units under test

---
*This document was created following the brainstorming skill process and reviewed according to the spec self-review checklist.*