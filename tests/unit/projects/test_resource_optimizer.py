"""
Unit tests for the ResourceOptimizer module.
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from src.projects.resource_optimizer import ResourceOptimizer, OptimizationResult


class TestResourceOptimizer:
    """Test cases for the ResourceOptimizer class."""

    def test_init(self):
        """Test initialization of ResourceOptimizer."""
        optimizer = ResourceOptimizer()
        assert isinstance(optimizer, ResourceOptimizer)

    @pytest.mark.asyncio
    async def test_analyze_usage_empty_data(self):
        """Test analyzing usage with empty data."""
        optimizer = ResourceOptimizer()
        project_id = uuid.uuid4()
        
        result = await optimizer.analyze_usage(project_id, [])
        
        assert isinstance(result, OptimizationResult)
        assert result.project_id == project_id
        assert result.saved_tokens >= 0
        assert isinstance(result.recommendations, list)
        assert len(result.recommendations) > 0
        assert "No usage data available" in result.recommendations[0] or \
               "Monitor usage patterns" in result.recommendations[0]

    @pytest.mark.asyncio
    async def test_analyze_usage_with_data(self):
        """Test analyzing usage with sample data."""
        optimizer = ResourceOptimizer()
        project_id = uuid.uuid4()
        
        usage_data = [
            {"tokens_used": 100, "operation_type": "query"},
            {"tokens_used": 150, "operation_type": "completion"},
            {"tokens_used": 200, "operation_type": "query"},
            {"tokens_used": 300, "operation_type": "analysis"}
        ]
        
        result = await optimizer.analyze_usage(project_id, usage_data)
        
        assert isinstance(result, OptimizationResult)
        assert result.project_id == project_id
        assert result.saved_tokens >= 100  # Should be reasonable savings
        assert isinstance(result.recommendations, list)
        assert len(result.recommendations) > 0
        
        # Check that recommendations are relevant
        rec_text = " ".join(result.recommendations).lower()
        assert any(keyword in rec_text for keyword in 
                  ["cache", "batch", "token", "query", "completion"])

    @pytest.mark.asyncio
    async def test_analyze_usage_high_token_usage(self):
        """Test analyzing usage with high token consumption."""
        optimizer = ResourceOptimizer()
        project_id = uuid.uuid4()
        
        usage_data = [
            {"tokens_used": 2000, "operation_type": "complex_reasoning"},
            {"tokens_used": 1800, "operation_type": "detailed_analysis"},
            {"tokens_used": 2200, "operation_type": "research"}
        ]
        
        result = await optimizer.analyze_usage(project_id, usage_data)
        
        assert isinstance(result, OptimizationResult)
        assert result.saved_tokens > 0
        
        # Should suggest reducing token usage for high consumption
        rec_text = " ".join(result.recommendations).lower()
        assert "token" in rec_text or "concise" in rec_text

    @pytest.mark.asyncio
    async def test_apply_optimizations(self):
        """Test applying optimizations."""
        optimizer = ResourceOptimizer()
        
        # Test with positive recommendations
        result = OptimizationResult(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            saved_tokens=500,
            recommendations=["Cache repeated queries", "Use smaller models"],
            evaluated_at=datetime.now(timezone.utc)
        )
        
        success = await optimizer.apply_optimizations(result)
        assert isinstance(success, bool)
        assert success is True  # Should succeed with valid recommendations
        
        # Test with unhelpful recommendations
        result_bad = OptimizationResult(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            saved_tokens=0,
            recommendations=["No usage data available for analysis"],
            evaluated_at=datetime.now(timezone.utc)
        )
        
        success_bad = await optimizer.apply_optimizations(result_bad)
        assert success_bad is False  # Should fail with unhelpful recommendations

    def test_optimization_result_model(self):
        """Test the OptimizationResult model."""
        result = OptimizationResult(
            id=uuid.uuid4(),
            project_id=uuid.uuid4(),
            saved_tokens=1000,
            recommendations=["Test recommendation"],
            evaluated_at=datetime.now(timezone.utc)
        )
        
        assert isinstance(result.id, uuid.UUID)
        assert isinstance(result.project_id, uuid.UUID)
        assert result.saved_tokens == 1000
        assert result.recommendations == ["Test recommendation"]
        assert isinstance(result.evaluated_at, datetime)
