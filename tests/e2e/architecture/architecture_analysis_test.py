from __future__ import annotations

import pytest
import asyncio

@pytest.mark.asyncio
async def test_architecture_analysis_loop():
    # Mocking the e2e flow for architecture analysis and candidate generation
    from src.agents.architecture_nodes import (
        architecture_analysis, dependency_analysis, component_analysis,
        bottleneck_detection, hypothesis_generation, candidate_generation,
        sandbox_benchmarking, benchmark_reporting, AgentStateDict
    )

    state: AgentStateDict = {
        "architecture_id": "arch_123",
        "version": "v1.0"
    }

    state = await architecture_analysis(state)
    assert state.get("status") == "architecture_analysis_complete"

    state = await dependency_analysis(state)
    assert state.get("status") == "dependency_analysis_complete"

    state = await component_analysis(state)
    assert state.get("status") == "component_analysis_complete"

    state = await bottleneck_detection(state)
    assert state.get("status") == "bottleneck_detection_complete"

    state = await hypothesis_generation(state)
    assert state.get("status") == "hypothesis_generation_complete"

    state = await candidate_generation(state)
    assert state.get("status") == "candidate_generation_complete"

    state = await sandbox_benchmarking(state)
    assert state.get("status") == "sandbox_benchmarking_complete"

    state = await benchmark_reporting(state)
    assert state.get("status") == "benchmark_reporting_complete"
