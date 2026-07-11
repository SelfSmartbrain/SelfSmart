from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.world_model.belief_engine import BeliefEngine
from src.world_model.prediction_engine import PredictionEngine, PredictionResult

logger = get_logger(__name__)

class AccuracyMetrics(BaseModel):
    total_predictions: int
    correct_predictions: int
    accuracy_score: float
    brier_score: float
    model_config = {"from_attributes": True}

class BenchmarkResult(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    run_time: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    prediction_metrics: AccuracyMetrics
    belief_calibration_score: float
    model_config = {"from_attributes": True}

class WorldModelBenchmarkRunner:
    """Evaluates hypothesis accuracy, prediction accuracy, and belief calibration over time."""

    def __init__(self, belief_engine: BeliefEngine, prediction_engine: PredictionEngine) -> None:
        self.belief_engine = belief_engine
        self.prediction_engine = prediction_engine
        logger.info("WorldModelBenchmarkRunner initialized.")

    async def run_benchmark(self) -> BenchmarkResult:
        """Runs the benchmarking process on resolved predictions and beliefs."""
        logger.info("Running World Model benchmark...")

        predictions = await self.prediction_engine.list_predictions(resolved_only=True)
        prediction_metrics = await self._evaluate_predictions(predictions)
        calibration_score = await self._evaluate_beliefs()

        result = BenchmarkResult(
            prediction_metrics=prediction_metrics,
            belief_calibration_score=calibration_score
        )
        logger.info(f"Benchmark completed with accuracy score: {prediction_metrics.accuracy_score:.2f}")
        return result

    async def _evaluate_predictions(self, predictions: List[PredictionResult]) -> AccuracyMetrics:
        """Calculates prediction accuracy and Brier score."""
        if not predictions:
            return AccuracyMetrics(
                total_predictions=0,
                correct_predictions=0,
                accuracy_score=0.0,
                brier_score=0.0
            )

        correct = 0
        brier_sum = 0.0

        for p in predictions:
            if p.actual_outcome is None:
                continue

            prob = p.predicted_success_probability
            outcome = 1.0 if p.actual_outcome else 0.0

            # Count as correct if prob >= 0.5 and actual is True, or prob < 0.5 and actual is False
            if (prob >= 0.5 and p.actual_outcome) or (prob < 0.5 and not p.actual_outcome):
                correct += 1

            # Brier score calculation: (probability - outcome)^2
            brier_sum += (prob - outcome) ** 2

        total = len(predictions)
        return AccuracyMetrics(
            total_predictions=total,
            correct_predictions=correct,
            accuracy_score=correct / total,
            brier_score=brier_sum / total
        )

    async def _evaluate_beliefs(self) -> float:
        """Evaluates calibration of beliefs."""
        beliefs = await self.belief_engine.list_beliefs()
        if not beliefs:
            return 0.0

        # Simple calibration metric (mock behavior)
        total_confidence = sum(b.confidence for b in beliefs)
        return total_confidence / len(beliefs)
