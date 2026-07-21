"""
Unit tests for the PromotionEngine module.
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from src.evolution.promotion_engine import PromotionEngine, ArchitecturePromotion


class TestPromotionEngine:
    """Test cases for the PromotionEngine class."""

    def test_init(self):
        """Test initialization of PromotionEngine."""
        engine = PromotionEngine()
        assert isinstance(engine, PromotionEngine)
        assert hasattr(engine, 'promotion_criteria')
        assert isinstance(engine.promotion_criteria, dict)

    @pytest.mark.asyncio
    async def test_evaluate_for_promotion_should_promote(self):
        """Test promotion evaluation when candidate should be promoted."""
        engine = PromotionEngine()
        candidate_id = uuid.uuid4()
        baseline_id = uuid.uuid4()
        
        # Candidate significantly better than baseline
        candidate_fitness = 0.9
        candidate_failure_rate = 0.01
        baseline_fitness = 0.7
        baseline_failure_rate = 0.02
        
        result = await engine.evaluate_for_promotion(
            candidate_id, candidate_fitness, candidate_failure_rate,
            baseline_id, baseline_fitness, baseline_failure_rate
        )
        
        # Should return a promotion (not None)
        assert result is not None
        assert isinstance(result, ArchitecturePromotion)
        assert result.candidate_id == candidate_id
        assert result.baseline_id == baseline_id
        assert result.improvement_percentage > 0  # Should be positive improvement
        assert isinstance(result.details, dict)
        assert isinstance(result.promotion_decision_factors, dict)
        assert result.promoted_at is not None

    @pytest.mark.asyncio
    async def test_evaluate_for_promotion_should_not_promote_insufficient_improvement(self):
        """Test promotion evaluation when improvement is insufficient."""
        engine = PromotionEngine()
        candidate_id = uuid.uuid4()
        baseline_id = uuid.uuid4()
        
        # Candidate slightly better but not enough (less than 5% threshold)
        candidate_fitness = 0.72
        candidate_failure_rate = 0.01
        baseline_fitness = 0.7
        baseline_failure_rate = 0.02
        
        result = await engine.evaluate_for_promotion(
            candidate_id, candidate_fitness, candidate_failure_rate,
            baseline_id, baseline_fitness, baseline_failure_rate
        )
        
        # Should not return a promotion
        assert result is None

    @pytest.mark.asyncio
    async def test_evaluate_for_promotion_should_not_promote_worse_failure_rate(self):
        """Test promotion evaluation when candidate has worse failure rate."""
        engine = PromotionEngine()
        candidate_id = uuid.uuid4()
        baseline_id = uuid.uuid4()
        
        # Candidate better fitness but worse failure rate
        candidate_fitness = 0.8
        candidate_failure_rate = 0.05  # Worse than baseline
        baseline_fitness = 0.7
        baseline_failure_rate = 0.02
        
        result = await engine.evaluate_for_promotion(
            candidate_id, candidate_fitness, candidate_failure_rate,
            baseline_id, baseline_fitness, baseline_failure_rate
        )
        
        # Should not return a promotion due to worse failure rate
        assert result is None

    @pytest.mark.asyncio
    async def test_evaluate_for_promotion_zero_baseline_fitness(self):
        """Test promotion evaluation with zero baseline fitness (edge case)."""
        engine = PromotionEngine()
        candidate_id = uuid.uuid4()
        baseline_id = uuid.uuid4()
        
        # Zero baseline fitness (should be handled gracefully)
        candidate_fitness = 0.8
        candidate_failure_rate = 0.01
        baseline_fitness = 0.0
        baseline_failure_rate = 0.02
        
        result = await engine.evaluate_for_promotion(
            candidate_id, candidate_fitness, candidate_failure_rate,
            baseline_id, baseline_fitness, baseline_failure_rate
        )
        
        # Should handle zero baseline fitness without error
        # May or may not promote depending on calculations
        assert result is None or isinstance(result, ArchitecturePromotion)

    @pytest.mark.asyncio
    async def test_evaluate_for_promotion_deterministic(self):
        """Test that promotion evaluation is deterministic for same inputs."""
        engine = PromotionEngine()
        candidate_id = uuid.uuid4()
        baseline_id = uuid.uuid4()
        
        candidate_fitness = 0.85
        candidate_failure_rate = 0.02
        baseline_fitness = 0.7
        baseline_failure_rate = 0.03
        
        # Evaluate twice with same inputs
        result1 = await engine.evaluate_for_promotion(
            candidate_id, candidate_fitness, candidate_failure_rate,
            baseline_id, baseline_fitness, baseline_failure_rate
        )
        result2 = await engine.evaluate_for_promotion(
            candidate_id, candidate_fitness, candidate_failure_rate,
            baseline_id, baseline_fitness, baseline_failure_rate
        )
        
        # Results should be identical
        if result1 is None and result2 is None:
            assert True  # Both None is fine
        elif result1 is not None and result2 is not None:
            assert result1.candidate_id == result2.candidate_id
            assert result1.baseline_id == result2.baseline_id
            assert result1.improvement_percentage == result2.improvement_percentage
            assert result1.promotion_decision_factors == result2.promotion_decision_factors
        else:
            # One is None and other is not - this would indicate non-determinism
            assert False, "Evaluation should be deterministic"

    @pytest.mark.asyncio
    async def test_evaluate_for_promotion_different_candidates(self):
        """Test that different candidates get different evaluations."""
        engine = PromotionEngine()
        candidate_id1 = uuid.uuid4()
        candidate_id2 = uuid.uuid4()
        baseline_id = uuid.uuid4()
        
        # Ensure they're different
        assert candidate_id1 != candidate_id2
        
        candidate_fitness = 0.8
        candidate_failure_rate = 0.02
        baseline_fitness = 0.7
        baseline_failure_rate = 0.03
        
        result1 = await engine.evaluate_for_promotion(
            candidate_id1, candidate_fitness, candidate_failure_rate,
            baseline_id, baseline_fitness, baseline_failure_rate
        )
        result2 = await engine.evaluate_for_promotion(
            candidate_id2, candidate_fitness, candidate_failure_rate,
            baseline_id, baseline_fitness, baseline_failure_rate
        )
        
        # Should have different promotion IDs if both promote
        if result1 is not None and result2 is not None:
            assert result1.promotion_id != result2.promotion_id
        # The decision factors should be different due to different seeds
        if result1 is not None and result2 is not None:
            assert result1.promotion_decision_factors.get('evaluation_seed') != \
                   result2.promotion_decision_factors.get('evaluation_seed')

    def test_architecture_promotion_model(self):
        """Test the ArchitecturePromotion model."""
        promotion = ArchitecturePromotion(
            promotion_id=uuid.uuid4(),
            candidate_id=uuid.uuid4(),
            baseline_id=uuid.uuid4(),
            promoted_at=datetime.now(timezone.utc),
            improvement_percentage=25.5,
            details={"test": "data"},
            promotion_decision_factors={"score": 0.8}
        )
        
        assert isinstance(promotion.promotion_id, uuid.UUID)
        assert isinstance(promotion.candidate_id, uuid.UUID)
        assert isinstance(promotion.baseline_id, uuid.UUID)
        assert promotion.improvement_percentage == 25.5
        assert promotion.details == {"test": "data"}
        assert promotion.promotion_decision_factors == {"score": 0.8}
        assert isinstance(promotion.promoted_at, datetime)
