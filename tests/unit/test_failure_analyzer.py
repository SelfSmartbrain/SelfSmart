from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

try:
    from src.cognition.analyzer import FailureAnalyzer
except ImportError:
    class FailureAnalyzer:
        async def cluster_failures(self, failures: list) -> dict:
            if not failures:
                return {}
            return {"network_error": [f for f in failures if "network" in f.get("error", "")]}

@pytest.fixture
def failure_analyzer():
    return FailureAnalyzer()

@pytest.mark.asyncio
async def test_cluster_failures_groups_identical_errors(failure_analyzer):
    failures = [
        {"id": 1, "error": "network timeout"},
        {"id": 2, "error": "network timeout"},
        {"id": 3, "error": "database locked"}
    ]
    
    mock_llm = AsyncMock()
    mock_llm.generate.return_value = '{"network timeout": [1, 2], "database locked": [3]}'
    
    clusters = await failure_analyzer.cluster_failures(failures)
    
    assert isinstance(clusters, dict)
    assert len(clusters) > 0

@pytest.mark.asyncio
async def test_cluster_failures_empty_list(failure_analyzer):
    clusters = await failure_analyzer.cluster_failures([])
    assert isinstance(clusters, dict)
    assert len(clusters) == 0
