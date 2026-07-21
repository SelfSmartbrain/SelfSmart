"""
Unit tests for the CandidateEvaluator module.
"""

import pytest
import uuid
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

from src.evolution.candidate_evaluator import CandidateEvaluator, EvaluationResult


class TestCandidateEvaluator:
    """Test cases for the CandidateEvaluator class."""

    def test_init(self):
        """Test initialization of CandidateEvaluator."""
        evaluator = CandidateEvaluator()
        assert isinstance(evaluator, CandidateEvaluator)
        assert hasattr(evaluator, 'metric_weights')
        assert hasattr(evaluator, 'metric_categories')
        assert isinstance(evaluator.metric_weights, dict)
        assert isinstance(evaluator.metric_categories, dict)

    @pytest.mark.asyncio
    async def test_evaluate_candidate_basic(self):
        """Test evaluating a candidate with basic metrics."""
        evaluator = CandidateEvaluator()
        candidate_id = uuid.uuid4()
        
        metrics = {
            "throughput": 100.0,
            "accuracy": 0.95,
            "error_rate": 0.02
        }
        
        result = await evaluator.evaluate_candidate(candidate_id, metrics)
        
        assert isinstance(result, EvaluationResult)
        assert result.candidate_id == candidate_id
        assert isinstance(result.fitness_score, float)
        assert 0.0 <= result.fitness_score <= 1.0
        assert isinstance(result.failure_rate, float)
        assert 0.0 <= result.failure_rate <= 1.0
        assert result.metrics == metrics
        assert isinstance(result.evaluation_details, dict)
        assert isinstance(result.evaluated_at, datetime)

    @pytest.mark.asyncio
    async def test_evaluate_candidate_empty_metrics(self):
        """Test evaluating a candidate with empty metrics."""
        evaluator = CandidateEvaluator()
        candidate_id = uuid.uuid4()
        
        result = await evaluator.evaluate_candidate(candidate_id, {})
        
        assert isinstance(result, EvaluationResult)
        assert result.candidate_id == candidate_id
        assert result.fitness_score == 0.0
        assert result.failure_rate == 0.0
        assert result.metrics == {}
        assert isinstance(result.evaluation_details, dict)

    @pytest.mark.asyncio
    async def test_evaluate_candidate_different_metrics(self):
        """Test evaluating a candidate with different metric combinations."""
        evaluator = CandidateEvaluator()
        candidate_id = uuid.uuid4()
        
        # Test with performance metrics
        perf_metrics = {
            "throughput": 150.0,
            "response_time": 0.05,  # Lower is better, but we'll treat as-is for simplicity
            "latency": 0.03
        }
        perf_result = await evaluator.evaluate_candidate(candidate_id, perf_metrics)
        
        # Test with accuracy metrics
        acc_metrics = {
            "accuracy": 0.92,
            "precision": 0.89,
            "recall": 0.94,
            "f1_score": 0.91
        }
        acc_result = await evaluator.evaluate_candidate(candidate_id, acc_metrics)
        
        # Test with reliability metrics
        rel_metrics = {
            "error_rate": 0.01,
            "failure_rate": 0.005,
            "uptime": 0.99
        }
        rel_result = await evaluator.evaluate_candidate(candidate_id, rel_metrics)
        
        # All should produce valid results
        for result in [perf_result, acc_result, rel_result]:
            assert isinstance(result, EvaluationResult)
            assert 0.0 <= result.fitness_score <= 1.0
            assert 0.0 <= result.failure_rate <= 1.0

    @pytest.mark.asyncio
    async def test_evaluate_candidate_deterministic(self):
        """Test that evaluation is deterministic for the same candidate."""
        evaluator = CandidateEvaluator()
        candidate_id = uuid.uuid4()
        
        metrics = {
            "throughput": 100.0,
            "accuracy": 0.9,
            "error_rate": 0.05
        }
        
        # Evaluate twice with same inputs
        result1 = await evaluator.evaluate_candidate(candidate_id, metrics)
        result2 = await evaluator.evaluate_candidate(candidate_id, metrics)
        
        # Should be identical (deterministic)
        assert result1.fitness_score == result2.fitness_score
        assert result1.failure_rate == result2.failure_rate
        assert result1.metrics == result2.metrics
        assert result1.evaluation_details["evaluation_seed"] == result2.evaluation_details["evaluation_seed"]

    @pytest.mark.asyncio
    async def test_evaluate_candidate_different_candidates(self):
        """Test that different candidates get different evaluations."""
        evaluator = CandidateEvaluator()
        candidate_id1 = uuid.uuid4()
        candidate_id2 = uuid.uuid4()
        
        # Ensure they're different
        assert candidate_id1 != candidate_id2
        
        metrics = {
            "throughput": 100.0,
            "accuracy": 0.9,
            "error_rate": 0.05
        }
        
        result1 = await evaluator.evaluate_candidate(candidate_id1, metrics)
        result2 = await evaluator.evaluate_candidate(candidate_id2, metrics)
        
        # While scores might be similar due to same metrics, the evaluation details should differ
        # due to different seeds
        assert result1.candidate_id == candidate_id1
        assert result2.candidate_id == candidate_id2
        # The evaluation seeds should be different
        assert result1.evaluation_details["evaluation_seed"] != result2.evaluation_details["evaluation_seed"]

    def test_evaluation_result_model(self):
        """Test the EvaluationResult model."""
        result = EvaluationResult(
            evaluation_id=uuid.uuid4(),
            candidate_id=uuid.uuid4(),
            fitness_score=0.85,
            failure_rate=0.05,
            metrics={"accuracy": 0.9, "speed": 1.2},
            evaluation_details={"test": "info"},
            evaluated_at=datetime.now(timezone.utc)
        )
        
        assert isinstance(result.evaluation_id, uuid.UUID)
        assert isinstance(result.candidate_id, uuid.UUID)
        assert result.fitness_score == 0.85
        assert result.failure_rate == 0.05
        assert result.metrics == {"accuracy": 0.9, "speed": 1.2}
        assert result.evaluation_details == {"test": "info"}
        assert isinstance(result.evaluated_at, datetime)
