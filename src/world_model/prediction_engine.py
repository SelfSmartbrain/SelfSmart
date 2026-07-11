from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any

from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.world_model.belief_engine import BeliefEngine, Belief

logger = get_logger(__name__)

class PredictionRequest(BaseModel):
    target: str
    context: str
    model_config = {"from_attributes": True}

class PredictionResult(BaseModel):
    id: uuid.UUID = Field(default_factory=uuid.uuid4)
    target: str
    predicted_success_probability: float
    reasoning: str
    actual_outcome: Optional[bool] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    resolved_at: Optional[datetime] = None
    model_config = {"from_attributes": True}

class PredictionEngine:
    """Predicts strategy success, research quality, or goal completion based on beliefs."""

    def __init__(self, belief_engine: BeliefEngine) -> None:
        self.belief_engine = belief_engine
        self.predictions: Dict[uuid.UUID, PredictionResult] = {}
        logger.info("PredictionEngine initialized.")

    async def make_prediction(self, request: PredictionRequest) -> PredictionResult:
        """Makes a prediction based on active beliefs and an LLM approximation."""
        logger.info(f"Making prediction for target: {request.target}")

        beliefs = await self.belief_engine.list_beliefs()

        # Simulated prediction logic based on current beliefs (Mocking LLM output)
        avg_confidence = sum(b.confidence for b in beliefs) / len(beliefs) if beliefs else 0.5

        prediction = PredictionResult(
            target=request.target,
            predicted_success_probability=avg_confidence,
            reasoning=f"Generated prediction using {len(beliefs)} active beliefs."
        )

        self.predictions[prediction.id] = prediction
        logger.info(f"Prediction {prediction.id} created with probability {prediction.predicted_success_probability:.2f}")
        return prediction

    async def record_outcome(self, prediction_id: uuid.UUID, actual_success: bool) -> PredictionResult:
        """Records the real-world outcome of a prediction to evaluate accuracy later."""
        if prediction_id not in self.predictions:
            logger.error(f"Prediction {prediction_id} not found.")
            raise ValueError(f"Prediction {prediction_id} not found.")

        prediction = self.predictions[prediction_id]
        prediction.actual_outcome = actual_success
        prediction.resolved_at = datetime.now(timezone.utc)

        logger.info(f"Recorded outcome for prediction {prediction_id}: {actual_success}")
        return prediction

    async def get_prediction(self, prediction_id: uuid.UUID) -> Optional[PredictionResult]:
        """Retrieves a specific prediction."""
        return self.predictions.get(prediction_id)

    async def list_predictions(self, resolved_only: bool = False) -> List[PredictionResult]:
        """Lists all or only resolved predictions."""
        if resolved_only:
            return [p for p in self.predictions.values() if p.actual_outcome is not None]
        return list(self.predictions.values())
