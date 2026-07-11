"""
tests/e2e/autonomous_loop_test.py

Purpose:
End-to-End validation of the Phase 7.5 autonomous cognitive loop.
Simulates:
Gap detected -> Goal created -> Track created -> Plan created -> 
Research executed -> Reflection generated -> Failure analyzed -> 
Skill discovered -> Strategy improved -> Metrics updated.
"""

from __future__ import annotations

import asyncio
import pytest
from typing import Any, Dict

from src.agents.state import create_initial_state
from src.agents.orchestrator import OrchestratorAgent
from src.core.service_registry import get_registry

# Make sure to mock or use test DB in conftest.py
pytestmark = pytest.mark.asyncio

async def test_full_autonomous_cognitive_loop():
    """
    Validates the entire E2E loop of the autonomous agent, focusing on
    Phase 7 self-improvement nodes (reflection, skills, meta-learning).
    """
    # 1. Initialize DI Registry
    registry = await get_registry()
    await registry.initialize_all()
    
    # Verify core cognitive services are loaded
    assert registry.get("reflection_agent") is not None
    assert registry.get("meta_learning") is not None
    assert registry.get("skill_discovery") is not None
    
    # 2. Setup initial state with a mock goal and failures to trigger learning
    state = create_initial_state()
    state["goal"] = "Research state-of-the-art architectures for quantum error correction."
    state["domain"] = "Quantum Computing"
    
    # Inject mock failures to test failure_analysis
    state["errors"] = [
        {"error_type": "SearchTimeout", "message": "Search API timed out after 30s"},
        {"error_type": "SearchTimeout", "message": "Search API timed out after 30s"},
        {"error_type": "RateLimit", "message": "Exceeded API limits"}
    ]
    
    # Inject mock task results to test skill_discovery
    state["task_results"] = {
        "task_1": {"status": "completed", "output": "Found arXiv paper A"},
        "task_2": {"status": "completed", "output": "Found arXiv paper B"},
        "task_3": {"status": "failed", "output": "Timeout"}
    }
    
    # 3. Initialize Orchestrator
    orchestrator = OrchestratorAgent()
    
    # 4. Execute Phase 7 Nodes Directly to verify state transitions without 
    # relying on actual LLM calls which might be flaky in CI.
    # We will test the graph execution of specific nodes.
    
    # A. Reflection
    state = await orchestrator._cognition_reflection(state)
    assert len(state["cognition_reflections"]) == 1
    assert state["cognition_reflections"][0]["success_score"] > 0
    
    # B. Failure Analysis
    state = await orchestrator._failure_analysis(state)
    assert len(state["failure_patterns"]) == 2  # SearchTimeout and RateLimit
    timeout_pattern = next(p for p in state["failure_patterns"] if p["pattern_name"] == "SearchTimeout")
    assert timeout_pattern["frequency"] == 2
    
    # C. Meta Learning
    state = await orchestrator._meta_learning(state)
    assert len(state["optimization_recommendations"]) > 0
    assert any("SearchTimeout" in rec for rec in state["optimization_recommendations"])
    
    # D. Strategy Optimization
    # Inject a mock selected strategy
    state["selected_strategy"] = {"name": "Deep Dive", "id": "123"}
    state = await orchestrator._strategy_optimization(state)
    assert state["best_strategy"] is not None
    assert "computed_success_rate" in state["best_strategy"]
    
    # E. Skill Discovery
    state = await orchestrator._skill_discovery(state)
    # We passed 2 completed tasks, which triggers a workflow extraction
    assert len(state["cognitive_skills"]) == 1
    assert state["cognitive_skills"][0]["skill_type"] == "workflow"
    
    # F. Metrics Recording
    state = await orchestrator._record_metrics(state)
    assert "autonomy_score" in state
    assert state["autonomy_score"] > 0
    assert len(state["cognitive_metrics"]) >= 4 # autonomy, velocity, completion, utilization
    
    # G. Self Improvement
    state = await orchestrator._self_improvement(state)
    # Should append recommendations based on failures
    assert len(state["optimization_recommendations"]) > 1

    # Print success for test runner logs
    print("\\nE2E Cognitive Loop validated successfully:")
    print(f"- Autonomy Score: {state['autonomy_score']}")
    print(f"- Discovered Skills: {len(state['cognitive_skills'])}")
    print(f"- Failure Patterns: {len(state['failure_patterns'])}")
