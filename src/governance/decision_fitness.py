"""decision_fitness.py

Phase 16G: Decision Fitness Metrics

Measures the quality and fitness of decisions.
Metrics:
- Accuracy
- Risk
- Impact
- Regret
- Efficiency
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


@dataclass
class DecisionFitness:
    """Fitness metrics for a decision."""
    decision_id: str = ""
    accuracy: float = 0.0  # How well the decision achieved its goals
    risk_score: float = 0.0  # Overall risk level
    impact_score: float = 0.0  # Magnitude of impact
    regret_score: float = 0.0  # Opportunity cost (lower is better)
    efficiency_score: float = 0.0  # Resource efficiency
    overall_fitness: float = 0.0  # Composite score
    confidence: float = 0.0  # Confidence in the assessment
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "decision_id": self.decision_id,
            "accuracy": self.accuracy,
            "risk_score": self.risk_score,
            "impact_score": self.impact_score,
            "regret_score": self.regret_score,
            "efficiency_score": self.efficiency_score,
            "overall_fitness": self.overall_fitness,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


class DecisionFitnessCalculator:
    """Calculates fitness metrics for decisions."""
    
    def __init__(self):
        self.fitness_history: Dict[str, DecisionFitness] = {}
        logger.info("DecisionFitnessCalculator initialized")
    
    def calculate_fitness(
        self,
        decision_data: Dict[str, Any],
        outcome: Optional[Dict[str, Any]] = None,
    ) -> DecisionFitness:
        """Calculate fitness metrics for a decision."""
        decision_id = decision_data.get("id", "")
        
        fitness = DecisionFitness(decision_id=decision_id)
        
        # Calculate individual metrics
        fitness.accuracy = self._calculate_accuracy(decision_data, outcome)
        fitness.risk_score = self._calculate_risk_score(decision_data)
        fitness.impact_score = self._calculate_impact_score(decision_data, outcome)
        fitness.regret_score = self._calculate_regret_score(decision_data, outcome)
        fitness.efficiency_score = self._calculate_efficiency_score(decision_data, outcome)
        
        # Calculate overall fitness
        fitness.overall_fitness = self._calculate_overall_fitness(fitness)
        
        # Calculate confidence
        fitness.confidence = self._calculate_confidence(decision_data, outcome)
        
        # Store fitness
        self.fitness_history[decision_id] = fitness
        
        logger.info(f"Calculated fitness for decision {decision_id}: {fitness.overall_fitness:.2f}")
        
        return fitness
    
    def _calculate_accuracy(
        self,
        decision_data: Dict[str, Any],
        outcome: Optional[Dict[str, Any]],
    ) -> float:
        """Calculate how well the decision achieved its goals."""
        if outcome is None:
            # Predict accuracy based on decision data
            confidence = decision_data.get("confidence", 0.5)
            return confidence
        
        # Actual accuracy based on outcome
        success = outcome.get("success", False)
        
        if success:
            # Check if expected outcomes were achieved
            expected = decision_data.get("expected_outcome", {})
            actual = outcome.get("actual_outcome", {})
            
            if expected and actual:
                # Simple comparison - in production, use more sophisticated comparison
                matches = sum(1 for k in expected.keys() if k in actual)
                total = len(expected)
                return matches / total if total > 0 else 0.5
        
        return 0.0 if not success else 0.8
    
    def _calculate_risk_score(self, decision_data: Dict[str, Any]) -> float:
        """Calculate overall risk score."""
        options = decision_data.get("options", [])
        selected_id = decision_data.get("selected_option_id")
        selected = next((opt for opt in options if opt.get("id") == selected_id), None)
        
        if selected:
            return selected.get("risk_score", 0.5)
        
        return 0.5
    
    def _calculate_impact_score(
        self,
        decision_data: Dict[str, Any],
        outcome: Optional[Dict[str, Any]],
    ) -> float:
        """Calculate the magnitude of impact."""
        if outcome:
            # Use actual impact from outcome
            impact = outcome.get("impact", 0.5)
            return impact
        
        # Predict impact from decision data
        options = decision_data.get("options", [])
        selected_id = decision_data.get("selected_option_id")
        selected = next((opt for opt in options if opt.get("id") == selected_id), None)
        
        if selected:
            benefits = selected.get("benefits", [])
            impact = min(1.0, len(benefits) * 0.2)
            return impact
        
        return 0.5
    
    def _calculate_regret_score(
        self,
        decision_data: Dict[str, Any],
        outcome: Optional[Dict[str, Any]],
    ) -> float:
        """Calculate opportunity cost (regret)."""
        options = decision_data.get("options", [])
        selected_id = decision_data.get("selected_option_id")
        selected = next((opt for opt in options if opt.get("id") == selected_id), None)
        
        if not selected or not options:
            return 0.0
        
        # Find the best alternative
        alternatives = [opt for opt in options if opt.get("id") != selected_id]
        
        if not alternatives:
            return 0.0
        
        best_alternative = max(alternatives, key=lambda x: x.get("utility_score", 0))
        
        # Regret is the difference between best alternative and selected
        selected_utility = selected.get("utility_score", 0)
        best_utility = best_alternative.get("utility_score", 0)
        
        regret = max(0, best_utility - selected_utility)
        
        return regret
    
    def _calculate_efficiency_score(
        self,
        decision_data: Dict[str, Any],
        outcome: Optional[Dict[str, Any]],
    ) -> float:
        """Calculate resource efficiency."""
        context = decision_data.get("context", {})
        resources = context.get("available_resources", {})
        
        if not resources:
            return 0.5
        
        # Simple efficiency metric: impact / resource usage
        impact = self._calculate_impact_score(decision_data, outcome)
        resource_count = len(resources)
        
        # Normalize resource count (assume 5 resources is "normal")
        normalized_resources = min(1.0, resource_count / 5.0)
        
        if normalized_resources > 0:
            efficiency = impact / normalized_resources
            return min(1.0, efficiency)
        
        return 0.5
    
    def _calculate_overall_fitness(self, fitness: DecisionFitness) -> float:
        """Calculate composite fitness score."""
        # Weighted average of metrics
        weights = {
            "accuracy": 0.3,
            "risk": 0.2,  # Lower risk is better, so we use (1 - risk)
            "impact": 0.25,
            "regret": 0.1,  # Lower regret is better, so we use (1 - regret)
            "efficiency": 0.15,
        }
        
        overall = (
            fitness.accuracy * weights["accuracy"] +
            (1 - fitness.risk_score) * weights["risk"] +
            fitness.impact_score * weights["impact"] +
            (1 - fitness.regret_score) * weights["regret"] +
            fitness.efficiency_score * weights["efficiency"]
        )
        
        return overall
    
    def _calculate_confidence(
        self,
        decision_data: Dict[str, Any],
        outcome: Optional[Dict[str, Any]],
    ) -> float:
        """Calculate confidence in the fitness assessment."""
        if outcome:
            # High confidence when we have actual outcome data
            return 0.9
        
        # Lower confidence when predicting
        decision_confidence = decision_data.get("confidence", 0.5)
        return decision_confidence * 0.8
    
    def get_fitness(self, decision_id: str) -> Optional[DecisionFitness]:
        """Get fitness metrics for a decision."""
        return self.fitness_history.get(decision_id)
    
    def get_fitness_statistics(self) -> Dict[str, Any]:
        """Get statistics about decision fitness."""
        total_decisions = len(self.fitness_history)
        
        if total_decisions == 0:
            return {"total_decisions": 0}
        
        avg_fitness = sum(f.overall_fitness for f in self.fitness_history.values()) / total_decisions
        avg_accuracy = sum(f.accuracy for f in self.fitness_history.values()) / total_decisions
        avg_risk = sum(f.risk_score for f in self.fitness_history.values()) / total_decisions
        
        return {
            "total_decisions": total_decisions,
            "average_fitness": avg_fitness,
            "average_accuracy": avg_accuracy,
            "average_risk": avg_risk,
            "high_fitness_decisions": len([f for f in self.fitness_history.values() if f.overall_fitness > 0.8]),
            "low_fitness_decisions": len([f for f in self.fitness_history.values() if f.overall_fitness < 0.4]),
        }
