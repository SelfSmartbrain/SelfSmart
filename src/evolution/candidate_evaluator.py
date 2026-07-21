from __future__ import annotations
import uuid
import hashlib
from datetime import datetime
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
from src.config.logging import get_logger

logger = get_logger(__name__)

class EvaluationResult(BaseModel):
    evaluation_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    candidate_id: uuid.UUID
    fitness_score: float
    failure_rate: float
    metrics: Dict[str, float] = Field(default_factory=dict)
    evaluation_details: Dict[str, Any] = Field(default_factory=dict)
    evaluated_at: datetime = Field(default_factory=datetime.utcnow)
    
    model_config = {"from_attributes": True}

class CandidateEvaluator:
    def __init__(self) -> None:
        # Define weights for different metric categories
        self.metric_weights = {
            "performance": 0.3,      # throughput, latency, etc.
            "accuracy": 0.25,        # precision, recall, F1, etc.
            "reliability": 0.2,      # error rate, uptime, etc.
            "efficiency": 0.15,      # resource usage, cost, etc.
            "scalability": 0.1       # concurrency, throughput under load, etc.
        }
        
        # Define metric categories and their typical metrics
        self.metric_categories = {
            "performance": ["throughput", "response_time", "latency", "processing_speed"],
            "accuracy": ["accuracy", "precision", "recall", "f1_score", "quality_score"],
            "reliability": ["error_rate", "failure_rate", "uptime", "availability"],
            "efficiency": ["resource_usage", "cost_per_operation", "energy_efficiency", "memory_efficiency"],
            "scalability": ["concurrent_users", "throughput_scaling", "load_handling_capacity"]
        }

    async def evaluate_candidate(
        self,
        candidate_id: uuid.UUID,
        metrics: Dict[str, float]
    ) -> EvaluationResult:
        logger.info(f"Evaluating metrics for candidate {candidate_id}")
        
        # Generate deterministic but candidate-specific evaluation details
        seed_str = str(candidate_id)
        seed = int(hashlib.sha256(seed_str.encode()).hexdigest(), 16)
        
        # Categorize metrics
        categorized_metrics = self._categorize_metrics(metrics)
        
        # Calculate scores for each category
        category_scores = {}
        for category, weight in self.metric_weights.items():
            category_metrics = categorized_metrics.get(category, {})
            if category_metrics:
                # Normalize and weight the metrics in this category
                category_score = self._calculate_category_score(category, category_metrics)
                category_scores[category] = category_score * weight
            else:
                category_scores[category] = 0.0
        
        # Calculate overall fitness score
        fitness_score = sum(category_scores.values())
        
        # Calculate failure rate based on reliability metrics
        # If no reliability metrics were provided, assume failure_rate is 0 (as in the original implementation)
        reliability_keys = set(self.metric_categories.get("reliability", []))
        had_reliability_metrics = any(key in reliability_keys for key in metrics.keys())
        
        if not had_reliability_metrics:
            failure_rate = 0.0
        else:
            # Calculate failure rate based on reliability metrics
            # For simplicity, we'll use the reliability category score inversely
            # A perfect reliability score (1.0) should give failure_rate of 0.0
            # A zero reliability score should give failure_rate of 1.0
            reliability_raw = category_scores.get("reliability", 0.0)
            reliability_weight = self.metric_weights.get("reliability", 0.2)
            if reliability_weight > 0:
                # Normalize the reliability contribution to 0-1 range
                # Max possible contribution is reliability_weight (when score=1.0)
                reliability_normalized = min(reliability_raw / reliability_weight, 1.0)
                failure_rate = max(0.0, 1.0 - reliability_normalized)
            else:
                failure_rate = 0.0
        
        # Generate evaluation details
        evaluation_details = {
            "evaluation_method": "weighted_category_scoring",
            "metrics_provided": list(metrics.keys()),
            "metrics_categorized": {k: list(v.keys()) for k, v in categorized_metrics.items()},
            "category_scores": {k: round(v, 4) for k, v in category_scores.items()},
            "weights_used": self.metric_weights,
            "evaluation_seed": seed
        }
        
        result = EvaluationResult(
            candidate_id=candidate_id,
            fitness_score=round(fitness_score, 4),
            failure_rate=round(failure_rate, 4),
            metrics=metrics,
            evaluation_details=evaluation_details
        )
        
        return result

    def _categorize_metrics(self, metrics: Dict[str, float]) -> Dict[str, Dict[str, float]]:
        """Categorize metrics into predefined groups based on their names."""
        categorized = {category: {} for category in self.metric_categories.keys()}
        uncategorized = {}
        
        for metric_name, value in metrics.items():
            metric_lower = metric_name.lower()
            categorized_flag = False
            
            for category, keywords in self.metric_categories.items():
                if any(keyword in metric_lower for keyword in keywords):
                    categorized[category][metric_name] = value
                    categorized_flag = True
                    break
            
            if not categorized_flag:
                uncategorized[metric_name] = value
        
        # Add uncategorized metrics to a special category
        if uncategorized:
            categorized["other"] = uncategorized
            
        return categorized

    def _calculate_category_score(self, category: str, metrics: Dict[str, float]) -> float:
        """Calculate a normalized score for a category based on its metrics."""
        if not metrics:
            return 0.0
        
        # For simplicity, we'll assume higher values are better for most metrics
        # In a real implementation, this would depend on the specific metric
        values = list(metrics.values())
        
        # Normalize values to 0-1 range (simplified approach)
        if len(values) == 1:
            # For single value, return clamped value directly
            return min(max(values[0], 0.0), 1.0)
        else:
            min_val = min(values)
            max_val = max(values)
            if max_val == min_val:
                # All values are the same, return middle of range
                return 0.5
            else:
                normalized = [(v - min_val) / (max_val - min_val) for v in values]
                # Return the average of normalized values
                return sum(normalized) / len(normalized)
