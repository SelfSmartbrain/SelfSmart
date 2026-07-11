# Phase 18 Project Plan — Close the Inherited Gaps

**Goal**: Every component reaches ✅ Verified status before Phase 19 starts.

**Timeline**: Week 1-3
**Discipline**: No Phase 18+ work extends a component that is still ❌ or ⚠. Extension is earned by closing the gap.

---

## Task 18.1: Orchestrator Protection in SelfPatchSafetyGate (DO FIRST)

**Priority**: CRITICAL — Highest-severity open item from prior report

### Current State
- `src/agents/orchestrator.py` exists but is NOT in `CRITICAL_PATHS`
- `src/agents/` directory not covered by safety gate
- Test `test_rejects_patch_targeting_orchestrator` expects protection but it's not enforced

### Implementation Steps
1. Add `src/agents/orchestrator.py` to `CRITICAL_PATHS` in `src/safety/self_patch_safety_gate.py`
2. Add `src/agents/` directory to `CRITICAL_PATHS` for broader coverage
3. Run adversarial test: `pytest tests/adversarial/test_self_patch_safety_gate_rejects_bad_patches.py::test_rejects_patch_targeting_orchestrator -v`
4. Verify patch is rejected or requires human approval

### Acceptance Criteria
- [ ] `src/agents/orchestrator.py` is in CRITICAL_PATHS
- [ ] `src/agents/` directory is in CRITICAL_PATHS
- [ ] Adversarial test passes independently
- [ ] No code path exists that can apply orchestrator patches automatically

### Files to Modify
- `src/safety/self_patch_safety_gate.py` (lines 132-140)

---

## Task 18.2: AutonomyRecovery — Real Failure-Type Branching

**Priority**: HIGH

### Current State
- 15+ failure type labels exist in `FailureType` enum
- `failure_strategy_map` maps types to strategies
- Logic uses `retry_count` to select strategy from list
- Exponential backoff calculation implemented
- **Needs verification** that logic actually works as intended

### Implementation Steps
1. Run adversarial test: `pytest tests/adversarial/test_failure_type_specific_recovery.py -v`
2. If test fails, debug why failure types don't produce different actions
3. Ensure backoff values are strictly increasing across attempts
4. Verify transient vs non-retryable failures produce different strategies

### Acceptance Criteria
- [ ] `test_network_timeout_vs_validation_error_differ` passes
- [ ] `test_exponential_backoff_actually_increases` passes
- [ ] Backoff values strictly increase across at least 4 attempts
- [ ] Network timeouts produce retry strategy
- [ ] Validation errors produce different strategy (not retry)

### Files to Review/Modify
- `src/autonomy/autonomy_recovery.py` (if fixes needed)

---

## Task 18.3: AssumptionDetector — Wire to One Real State Check

**Priority**: HIGH

### Current State
- `test_assumption` only checks dict key existence, not actual values
- Line 323: `if available_resources: test_passed = True` — doesn't validate values
- Test comments explicitly identify this as the bug

### Implementation Steps
1. Implement real verification for ONE assumption category (database row-count claims)
2. Add actual database query to check row counts
3. Update `test_assumption` to validate actual values against ground truth
4. Use this as reference implementation before generalizing

### Acceptance Criteria
- [ ] Assumption that is objectively false against seeded ground truth is detected as false
- [ ] Retesting after underlying state changes flips the result
- [ ] `test_false_assumption_is_detected_as_false` passes
- [ ] `test_assumption_flips_on_retest_after_state_changes` passes

### Files to Modify
- `src/governance/assumption_detector.py` (lines 298-356)
- May need database session integration

---

## Task 18.4: ObjectiveManager — Decide and Commit, Don't Relabel Quietly

**Priority**: MEDIUM

### Current State
- `generate_next_objective` uses 5 hardcoded templates (lines 269-275)
- No LLM call despite method name suggesting autonomous generation
- Docstring admits "minimal implementation" and "should be replaced with LLM-based"

### Decision Required
Choose **one** path:

**Path A**: Implement real LLM-based generation
- Add LLM call to reason about what should follow completed objective
- Return None when no good next objective exists
- Requires LLM integration and prompt engineering

**Path B**: Rename and document honestly
- Rename method to `suggest_followup_template()`
- Update docstring to clearly indicate templated suggestion
- Remove "autonomous" language from public API surface

### Implementation Steps (Path A)
1. Add LLM client to ObjectiveManager
2. Design prompt for objective generation
3. Implement generation logic with ability to return None
4. Update tests

### Implementation Steps (Path B)
1. Rename `generate_next_objective` to `suggest_followup_template`
2. Update all call sites
3. Update docstring to be explicit about templated nature
4. Update any user-facing documentation

### Acceptance Criteria
- [ ] Public method name matches actual mechanism
- [ ] User-facing documentation matches actual mechanism
- [ ] No mislabeling between "autonomous generation" and "templated suggestion"

### Files to Modify
- `src/autonomy/objective_manager.py` (lines 244-341)
- Any call sites throughout codebase

---

## Task 18.5: Build Missing Execution Loop Harness

**Priority**: MEDIUM

### Current State
- No CLI entry point for real SIGKILL-and-restart testing
- Test `test_checkpoint_survives_hard_kill.py` exists but needs harness
- Current testing is in-process only, not real process-kill recovery

### Implementation Steps
1. Create CLI entry point in `src/cli/` (e.g., `execution_loop_harness.py`)
2. Implement separate process execution mode
3. Add SIGKILL handling and checkpoint recovery logic
4. Enable real process-kill testing (not in-process proxy)

### Acceptance Criteria
- [ ] CLI entry point exists and is executable
- [ ] Can run execution loop in separate process
- [ ] SIGKILL-and-restart test works against two real process invocations
- [ ] Original adversarial test `test_checkpoint_survives_sigkill` passes without scope reduction

### Files to Create
- `src/cli/execution_loop_harness.py` (new file)

### Files to Review
- `tests/adversarial/test_checkpoint_survives_hard_kill.py`
- `src/autonomy/checkpoint_manager.py`

---

## Phase 18 Exit Criteria

Before Phase 19 starts, ALL of the following must be true:

- [ ] **18.1**: Orchestrator is protected by SelfPatchSafetyGate (adversarial test passes)
- [ ] **18.2**: AutonomyRecovery has real failure-type branching (both tests pass)
- [ ] **18.3**: AssumptionDetector checks real state (both tests pass)
- [ ] **18.4**: ObjectiveManager is honestly labeled (path A or B implemented)
- [ ] **18.5**: Execution loop harness exists (SIGKILL test passes on real processes)

**Verification Discipline**: Each fix must be confirmed by an adversarial test run independently of the implementation pass that produced the fix — separation-of-roles principle.

---

## Sequencing Notes

- **18.1 blocks everything** — start here, do alone first
- **18.2-18.5 can run in parallel** after 18.1 completes
- **Phase 19 can start** as soon as 18.1 lands (instrumentation doesn't depend on other fixes)
- **No Phase 20 work** until 18.4 decision is made and implemented

---

## Risk Mitigation

- **Don't let 18.1 be partial** — orchestrator protection must be complete before moving on
- **Don't skip adversarial tests** — each fix must be independently verified
- **Don't defer 18.4 decision** — choose path A or B explicitly, no middle ground
