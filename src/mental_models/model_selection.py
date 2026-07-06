"""model_selection.py

Intelligent selection of mental models based on context and task.
Recommends the best model for a given situation.
"""

from __future__ import annotations

from datetime import datetime
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from pydantic import BaseModel, Field

from src.config.logging import get_logger
from .mental_models import MentalModel, ModelType

logger = get_logger(__name__)


class TaskCharacteristics(BaseModel):
    """Characteristics of a task for model selection."""

    has_deadline: bool = False
    is_complex: bool = False
    requires_learning: bool = False
    requires_research: bool = False
    requires_optimization: bool = False
    requires_scheduling: bool = False
    has_uncertainty: bool = False
    is_repetitive: bool = False
    domain: str = ""
    priority: str = "medium"  # low, medium, high


class SelectionScore(BaseModel):
    """Score for a model selection."""

    model_id: str
    model_name: str
    score: float
    reasons: List[str] = Field(default_factory=list)


class ModelSelector:
    """Selects the best mental model for a given task."""

    def __init__(self):
        self.selection_history: List[Dict[str, Any]] = []
        logger.info("ModelSelector initialized")

    def select_model(
        self,
        models: List[MentalModel],
        task_characteristics: TaskCharacteristics,
        context: Optional[Dict[str, Any]] = None,
    ) -> Optional[MentalModel]:
        """Select the best model for a given task."""
        if not models:
            return None

        scored = self._score_models(models, task_characteristics, context)

        if not scored:
            return None

        best = scored[0]
        model = next((m for m in models if m.id == best.model_id), None)

        # Record selection
        self.selection_history.append(
            {
                "model_id": best.model_id,
                "model_name": best.model_name,
                "score": best.score,
                "reasons": best.reasons,
                "task_characteristics": task_characteristics.model_dump(),
                "timestamp": str(datetime.now()),
            }
        )

        logger.info(f"Selected model: {best.model_name} (score: {best.score:.2f})")
        return model

    def _score_models(
        self,
        models: List[MentalModel],
        task: TaskCharacteristics,
        context: Optional[Dict[str, Any]] = None,
    ) -> List[SelectionScore]:
        """Score models based on task characteristics."""
        scored = []

        for model in models:
            score = 0.0
            reasons = []

            # Base score from success rate
            score += model.success_rate * 0.3
            if model.success_rate > 0.8:
                reasons.append("High historical success rate")

            # Type matching
            if task.requires_optimization and model.model_type == ModelType.OPTIMIZATION:
                score += 0.4
                reasons.append("Matches optimization task type")

            if task.requires_scheduling and model.model_type == ModelType.SCHEDULING:
                score += 0.4
                reasons.append("Matches scheduling task type")

            if task.requires_research and model.model_type == ModelType.RESEARCH:
                score += 0.4
                reasons.append("Matches research task type")

            if task.requires_learning and model.model_type == ModelType.LEARNING:
                score += 0.4
                reasons.append("Matches learning task type")

            if task.requires_optimization and model.model_type == ModelType.PLANNING:
                score += 0.3
                reasons.append("Planning model applicable to optimization")

            # Domain matching
            if task.domain and model.domain and task.domain.lower() in model.domain.lower():
                score += 0.2
                reasons.append(f"Domain match: {task.domain}")

            # Complexity handling
            if task.is_complex and len(model.steps) > 3:
                score += 0.15
                reasons.append("Structured approach for complex task")

            # Uncertainty handling
            if task.has_uncertainty and model.model_type in [
                ModelType.PREDICTION,
                ModelType.DECISION,
            ]:
                score += 0.2
                reasons.append("Handles uncertainty well")

            # Deadline pressure
            if task.has_deadline and model.model_type == ModelType.SCHEDULING:
                score += 0.15
                reasons.append("Scheduling model helps with deadlines")

            # Priority boost
            if task.priority == "high" and model.success_rate > 0.7:
                score += 0.1
                reasons.append("Reliable model for high-priority task")

            # Usage boost (frequently used models)
            if model.usage_count > 10:
                score += 0.05
                reasons.append("Well-tested model")

            scored.append(
                SelectionScore(
                    model_id=model.id,
                    model_name=model.name,
                    score=score,
                    reasons=reasons,
                )
            )

        # Sort by score
        scored.sort(key=lambda s: s.score, reverse=True)
        return scored

    def recommend_alternatives(
        self,
        models: List[MentalModel],
        selected_model: MentalModel,
        task: TaskCharacteristics,
        n: int = 3,
    ) -> List[Tuple[MentalModel, List[str]]]:
        """Recommend alternative models."""
        scored = self._score_models(models, task)

        # Filter out the selected model
        alternatives = [
            (m, s.reasons)
            for s in scored
            if s.model_id != selected_model.id
            for m in models
            if m.id == s.model_id
        ]

        return alternatives[:n]

    def get_selection_history(
        self,
        model_id: Optional[str] = None,
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        """Get selection history, optionally filtered by model."""
        history = self.selection_history

        if model_id:
            history = [h for h in history if h.get("model_id") == model_id]

        return history[-limit:]

    def analyze_model_effectiveness(
        self,
        model_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Analyze how effective a model has been in selections."""
        selections = [h for h in self.selection_history if h.get("model_id") == model_id]

        if not selections:
            return None

        avg_score = sum(h.get("score", 0) for h in selections) / len(selections)

        # Extract common reasons
        all_reasons = []
        for h in selections:
            all_reasons.extend(h.get("reasons", []))

        reason_counts = {}
        for reason in all_reasons:
            reason_counts[reason] = reason_counts.get(reason, 0) + 1

        top_reasons = sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)[:5]

        return {
            "model_id": model_id,
            "total_selections": len(selections),
            "average_score": avg_score,
            "top_selection_reasons": top_reasons,
        }

    def get_statistics(self) -> Dict[str, Any]:
        """Get selection statistics."""
        if not self.selection_history:
            return {
                "total_selections": 0,
                "unique_models_selected": 0,
            }

        model_counts = {}
        for h in self.selection_history:
            model_id = h.get("model_id")
            model_counts[model_id] = model_counts.get(model_id, 0) + 1

        return {
            "total_selections": len(self.selection_history),
            "unique_models_selected": len(model_counts),
            "most_selected_model": max(model_counts.items(), key=lambda x: x[1])
            if model_counts
            else None,
        }
