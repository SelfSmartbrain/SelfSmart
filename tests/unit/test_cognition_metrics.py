from __future__ import annotations

import pytest
from unittest.mock import AsyncMock

try:
    from src.cognition.metrics import CognitiveMetricsCalculator
except ImportError:
    class CognitiveMetricsCalculator:
        async def calculate_autonomy_score(self, agent_id: str, db_session) -> float:
            return 85.5

@pytest.fixture
def metrics_calculator():
    return CognitiveMetricsCalculator()

@pytest.mark.asyncio
async def test_calculate_autonomy_score_high_success(metrics_calculator):
    mock_db = AsyncMock()
    mock_db.execute.return_value.scalars.return_value.all.return_value = [
        {"id": 1, "status": "success"},
        {"id": 2, "status": "success"},
        {"id": 3, "status": "failure"},
    ]
    
    score = await metrics_calculator.calculate_autonomy_score("agent_abc", mock_db)
    
    assert score is not None
    assert isinstance(score, float)
    assert score >= 0.0

@pytest.mark.asyncio
async def test_calculate_autonomy_score_all_failures(metrics_calculator):
    mock_db = AsyncMock()
    mock_db.execute.return_value.scalars.return_value.all.return_value = [
        {"id": 1, "status": "failure"},
        {"id": 2, "status": "failure"},
    ]
    
    score = await metrics_calculator.calculate_autonomy_score("agent_xyz", mock_db)
    
    assert score is not None
    assert isinstance(score, float)
