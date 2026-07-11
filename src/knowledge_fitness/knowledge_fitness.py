"""knowledge_fitness.py

Measures the fitness of knowledge structures based on accuracy,
reuse, predictive power, and impact.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)


class FitnessMetric(str, Enum):
    """Types of fitness metrics."""
    ACCURACY = "accuracy"
    REUSE = "reuse"
    PREDICTIVE_POWER = "predictive_power"
    IMPACT = "impact"
    CONFIDENCE = "confidence"
    NOVELTY = "novelty"
    GENERALITY = "generality"


@dataclass
class FitnessScore:
    """Fitness score for a knowledge item."""
    knowledge_id: str
    metrics: Dict[FitnessMetric, float] = field(default_factory=dict)
    overall_fitness: float = 0.0
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "knowledge_id": self.knowledge_id,
            "metrics": {k.value: v for k, v in self.metrics.items()},
            "overall_fitness": self.overall_fitness,
            "timestamp": self.timestamp.isoformat(),
        }


class KnowledgeFitness:
    """Measures and tracks knowledge fitness over time."""
    
    def __init__(self):
        self.fitness_scores: Dict[str, FitnessScore] = {}
        self.usage_history: Dict[str, List[Dict[str, Any]]] = {}
        self.prediction_history: Dict[str, List[Tuple[bool, float]]] = {}  # knowledge_id -> [(correct, confidence)]
        logger.info("KnowledgeFitness initialized")
    
    def calculate_accuracy(
        self,
        knowledge_id: str,
        correct_predictions: int,
        total_predictions: int,
    ) -> float:
        """Calculate accuracy metric."""
        if total_predictions == 0:
            return 0.0
        return correct_predictions / total_predictions
    
    def calculate_reuse(
        self,
        knowledge_id: str,
        usage_count: int,
        total_possible_uses: int,
    ) -> float:
        """Calculate reuse metric."""
        if total_possible_uses == 0:
            return 0.0
        return min(1.0, usage_count / total_possible_uses)
    
    def calculate_predictive_power(
        self,
        knowledge_id: str,
    ) -> float:
        """Calculate predictive power from prediction history."""
        if knowledge_id not in self.prediction_history:
            return 0.0
        
        predictions = self.prediction_history[knowledge_id]
        if not predictions:
            return 0.0
        
        # Weight by confidence
        weighted_score = 0.0
        total_weight = 0.0
        
        for correct, confidence in predictions:
            weight = confidence
            weighted_score += (1.0 if correct else 0.0) * weight
            total_weight += weight
        
        return weighted_score / total_weight if total_weight > 0 else 0.0
    
    def calculate_impact(
        self,
        knowledge_id: str,
        outcomes: List[float],
    ) -> float:
        """Calculate impact metric from outcomes."""
        if not outcomes:
            return 0.0
        
        # Average outcome, normalized to 0-1
        avg_outcome = sum(outcomes) / len(outcomes)
        
        # Assume outcomes are in range [-1, 1], map to [0, 1]
        return (avg_outcome + 1) / 2
    
    def calculate_novelty(
        self,
        knowledge_id: str,
        similar_knowledge: List[str],
    ) -> float:
        """Calculate novelty metric (inverse of similarity)."""
        if not similar_knowledge:
            return 1.0  # Completely novel
        
        # Simple heuristic: fewer similar items = higher novelty
        return max(0.0, 1.0 - len(similar_knowledge) / 10.0)
    
    def calculate_generality(
        self,
        knowledge_id: str,
        applicable_contexts: int,
        total_contexts: int,
    ) -> float:
        """Calculate generality metric (breadth of applicability)."""
        if total_contexts == 0:
            return 0.0
        return applicable_contexts / total_contexts
    
    def record_usage(
        self,
        knowledge_id: str,
        context: Dict[str, Any],
        success: bool,
        outcome: float = 0.0,
    ) -> None:
        """Record usage of knowledge."""
        if knowledge_id not in self.usage_history:
            self.usage_history[knowledge_id] = []
        
        self.usage_history[knowledge_id].append({
            "context": context,
            "success": success,
            "outcome": outcome,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        
        logger.debug(f"Recorded usage for knowledge {knowledge_id}")
    
    def record_prediction(
        self,
        knowledge_id: str,
        correct: bool,
        confidence: float,
    ) -> None:
        """Record a prediction made using knowledge."""
        if knowledge_id not in self.prediction_history:
            self.prediction_history[knowledge_id] = []
        
        self.prediction_history[knowledge_id].append((correct, confidence))
    
    def calculate_fitness(
        self,
        knowledge_id: str,
        metrics: Optional[Dict[FitnessMetric, float]] = None,
        weights: Optional[Dict[FitnessMetric, float]] = None,
    ) -> FitnessScore:
        """Calculate overall fitness score."""
        if metrics is None:
            metrics = {}
        
        # Calculate missing metrics from history
        if FitnessMetric.ACCURACY not in metrics:
            if knowledge_id in self.prediction_history:
                predictions = self.prediction_history[knowledge_id]
                correct = sum(1 for c, _ in predictions if c)
                metrics[FitnessMetric.ACCURACY] = self.calculate_accuracy(knowledge_id, correct, len(predictions))
        
        if FitnessMetric.REUSE not in metrics:
            if knowledge_id in self.usage_history:
                usage_count = len(self.usage_history[knowledge_id])
                metrics[FitnessMetric.REUSE] = self.calculate_reuse(knowledge_id, usage_count, 100)
        
        if FitnessMetric.PREDICTIVE_POWER not in metrics:
            metrics[FitnessMetric.PREDICTIVE_POWER] = self.calculate_predictive_power(knowledge_id)
        
        if FitnessMetric.IMPACT not in metrics:
            if knowledge_id in self.usage_history:
                outcomes = [u.get("outcome", 0.0) for u in self.usage_history[knowledge_id]]
                metrics[FitnessMetric.IMPACT] = self.calculate_impact(knowledge_id, outcomes)
        
        # Default weights
        default_weights = {
            FitnessMetric.ACCURACY: 0.3,
            FitnessMetric.REUSE: 0.2,
            FitnessMetric.PREDICTIVE_POWER: 0.25,
            FitnessMetric.IMPACT: 0.15,
            FitnessMetric.NOVELTY: 0.05,
            FitnessMetric.GENERALITY: 0.05,
        }
        
        if weights:
            default_weights.update(weights)
        
        # Calculate weighted average
        overall_fitness = 0.0
        total_weight = 0.0
        
        for metric, weight in default_weights.items():
            if metric in metrics:
                overall_fitness += metrics[metric] * weight
                total_weight += weight
        
        if total_weight > 0:
            overall_fitness /= total_weight
        
        fitness_score = FitnessScore(
            knowledge_id=knowledge_id,
            metrics=metrics,
            overall_fitness=overall_fitness,
        )
        
        self.fitness_scores[knowledge_id] = fitness_score
        logger.info(f"Calculated fitness for {knowledge_id}: {overall_fitness:.3f}")
        return fitness_score
    
    def get_fitness(self, knowledge_id: str) -> Optional[FitnessScore]:
        """Get fitness score for a knowledge item."""
        return self.fitness_scores.get(knowledge_id)
    
    def get_top_knowledge(
        self,
        n: int = 10,
        metric: Optional[FitnessMetric] = None,
    ) -> List[Tuple[str, float]]:
        """Get top knowledge by fitness."""
        if metric:
            # Sort by specific metric
            scored = [
                (kid, score.metrics.get(metric, 0.0))
                for kid, score in self.fitness_scores.items()
            ]
        else:
            # Sort by overall fitness
            scored = [(kid, score.overall_fitness) for kid, score in self.fitness_scores.items()]
        
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:n]
    
    def compare_fitness(
        self,
        knowledge_id_a: str,
        knowledge_id_b: str,
    ) -> Optional[Dict[str, Any]]:
        """Compare fitness between two knowledge items."""
        score_a = self.fitness_scores.get(knowledge_id_a)
        score_b = self.fitness_scores.get(knowledge_id_b)
        
        if not score_a or not score_b:
            return None
        
        comparison = {
            "knowledge_a": knowledge_id_a,
            "knowledge_b": knowledge_id_b,
            "overall_fitness_a": score_a.overall_fitness,
            "overall_fitness_b": score_b.overall_fitness,
            "winner": knowledge_id_a if score_a.overall_fitness > score_b.overall_fitness else knowledge_id_b,
            "metric_comparison": {},
        }
        
        # Compare individual metrics
        all_metrics = set(score_a.metrics.keys()) | set(score_b.metrics.keys())
        for metric in all_metrics:
            val_a = score_a.metrics.get(metric, 0.0)
            val_b = score_b.metrics.get(metric, 0.0)
            comparison["metric_comparison"][metric.value] = {
                "a": val_a,
                "b": val_b,
                "better": "a" if val_a > val_b else "b" if val_b > val_a else "tie",
            }
        
        return comparison
    
    def get_fitness_trend(
        self,
        knowledge_id: str,
        window_size: int = 10,
    ) -> List[float]:
        """Get fitness trend over time (requires historical data)."""
        # For now, return current fitness
        # In a full implementation, this would track historical fitness scores
        score = self.fitness_scores.get(knowledge_id)
        return [score.overall_fitness] if score else []
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get fitness statistics."""
        if not self.fitness_scores:
            return {
                "total_knowledge_items": 0,
                "average_fitness": 0.0,
            }
        
        fitness_values = [score.overall_fitness for score in self.fitness_scores.values()]
        
        metric_averages = {}
        for metric in FitnessMetric:
            values = [
                score.metrics.get(metric, 0.0)
                for score in self.fitness_scores.values()
            ]
            if values:
                metric_averages[metric.value] = sum(values) / len(values)
        
        return {
            "total_knowledge_items": len(self.fitness_scores),
            "average_fitness": sum(fitness_values) / len(fitness_values),
            "max_fitness": max(fitness_values),
            "min_fitness": min(fitness_values),
            "average_metrics": metric_averages,
            "total_usages": sum(len(history) for history in self.usage_history.values()),
            "total_predictions": sum(len(history) for history in self.prediction_history.values()),
        }
