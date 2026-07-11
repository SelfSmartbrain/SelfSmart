"""outcome_predictor.py

Predicts outcomes of decisions before execution.
Uses historical data and simulation to forecast results.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
from enum import Enum

from src.config.logging import get_logger
from src.decision.future_simulator import SimulationResult, FutureSimulator
from src.decision.scenario_generator import Scenario, ScenarioGenerator

logger = get_logger(__name__)


class PredictionConfidence(str, Enum):
    """Confidence levels for predictions."""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


@dataclass
class Prediction:
    """A prediction about the outcome of a decision."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    decision_id: str = ""
    predicted_outcome: Dict[str, Any] = field(default_factory=dict)
    confidence: PredictionConfidence = PredictionConfidence.MEDIUM
    probability_distribution: Dict[str, float] = field(default_factory=dict)
    key_factors: List[str] = field(default_factory=list)
    assumptions: List[str] = field(default_factory=list)
    alternative_outcomes: List[Dict[str, Any]] = field(default_factory=list)
    created_at: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "decision_id": self.decision_id,
            "predicted_outcome": self.predicted_outcome,
            "confidence": self.confidence.value,
            "probability_distribution": self.probability_distribution,
            "key_factors": self.key_factors,
            "assumptions": self.assumptions,
            "alternative_outcomes": self.alternative_outcomes,
            "created_at": self.created_at,
            "metadata": self.metadata,
        }


class OutcomePredictor:
    """Predicts outcomes of decisions using simulation and historical data."""
    
    def __init__(
        self,
        scenario_generator: Optional[ScenarioGenerator] = None,
        simulator: Optional[FutureSimulator] = None,
    ):
        self.scenario_generator = scenario_generator or ScenarioGenerator()
        self.simulator = simulator or FutureSimulator()
        self.historical_outcomes: List[Dict[str, Any]] = []
        logger.info("OutcomePredictor initialized")
    
    def predict_outcome(
        self,
        decision_id: str,
        action: Dict[str, Any],
        context: Dict[str, Any],
        num_scenarios: int = 5,
    ) -> Prediction:
        """Predict the outcome of a decision."""
        logger.info(f"Predicting outcome for decision: {decision_id}")
        
        # Generate scenarios
        scenarios = self.scenario_generator.generate_scenarios(
            context=context,
            num_scenarios=num_scenarios,
        )
        
        # Run simulations for each scenario
        simulation_results = []
        for scenario in scenarios:
            initial_state = context.get("initial_state", {})
            result = self.simulator.simulate(
                scenario=scenario,
                action=action,
                initial_state=initial_state,
            )
            simulation_results.append(result)
        
        # Aggregate predictions
        prediction = self._aggregate_predictions(
            decision_id,
            simulation_results,
            scenarios,
        )
        
        logger.info(f"Prediction complete for decision: {decision_id}")
        return prediction
    
    def _aggregate_predictions(
        self,
        decision_id: str,
        simulation_results: List[SimulationResult],
        scenarios: List[Scenario],
    ) -> Prediction:
        """Aggregate simulation results into a prediction."""
        # Calculate weighted outcome based on scenario probabilities
        weighted_outcome = {}
        total_probability = 0.0
        
        for result, scenario in zip(simulation_results, scenarios):
            weight = scenario.probability
            total_probability += weight
            
            for metric, value in result.outcome_metrics.items():
                if isinstance(value, dict):
                    for sub_metric, sub_value in value.items():
                        key = f"{metric}_{sub_metric}"
                        weighted_outcome[key] = weighted_outcome.get(key, 0.0) + sub_value * weight
                else:
                    weighted_outcome[metric] = weighted_outcome.get(metric, 0.0) + value * weight
        
        # Normalize
        if total_probability > 0:
            for key in weighted_outcome:
                weighted_outcome[key] /= total_probability
        
        # Calculate confidence
        avg_confidence = sum(r.confidence for r in simulation_results) / len(simulation_results)
        confidence_level = self._determine_confidence_level(avg_confidence)
        
        # Identify key factors
        key_factors = self._identify_key_factors(simulation_results)
        
        # Extract assumptions
        assumptions = []
        for scenario in scenarios:
            assumptions.extend(scenario.assumptions)
        
        # Generate alternative outcomes
        alternative_outcomes = [
            {
                "scenario": r.scenario_name,
                "outcome": r.outcome_metrics,
                "probability": s.probability,
            }
            for r, s in zip(simulation_results, scenarios)
        ]
        
        # Create probability distribution
        probability_distribution = {
            "success": sum(
                s.probability for r, s in zip(simulation_results, scenarios) if r.success
            ),
            "failure": sum(
                s.probability for r, s in zip(simulation_results, scenarios) if not r.success
            ),
        }
        
        from datetime import datetime, timezone
        
        return Prediction(
            decision_id=decision_id,
            predicted_outcome=weighted_outcome,
            confidence=confidence_level,
            probability_distribution=probability_distribution,
            key_factors=key_factors,
            assumptions=list(set(assumptions)),
            alternative_outcomes=alternative_outcomes,
            created_at=datetime.now(timezone.utc).isoformat(),
        )
    
    def _determine_confidence_level(self, confidence: float) -> PredictionConfidence:
        """Determine confidence level from numerical confidence."""
        if confidence >= 0.7:
            return PredictionConfidence.HIGH
        elif confidence >= 0.4:
            return PredictionConfidence.MEDIUM
        else:
            return PredictionConfidence.LOW
    
    def _identify_key_factors(
        self,
        simulation_results: List[SimulationResult],
    ) -> List[str]:
        """Identify key factors that influence outcomes."""
        factors = []
        
        # Look for variables with high variance across simulations
        if not simulation_results:
            return factors
        
        # Collect all variable names
        all_vars = set()
        for result in simulation_results:
            if "improvement" in result.outcome_metrics:
                all_vars.update(result.outcome_metrics["improvement"].keys())
        
        # Calculate variance for each variable
        variances = {}
        for var in all_vars:
            values = []
            for result in simulation_results:
                if "improvement" in result.outcome_metrics:
                    values.append(result.outcome_metrics["improvement"].get(var, 0.0))
            
            if len(values) > 1:
                mean = sum(values) / len(values)
                variance = sum((v - mean) ** 2 for v in values) / len(values)
                variances[var] = variance
        
        # Top factors by variance
        sorted_factors = sorted(variances.items(), key=lambda x: x[1], reverse=True)
        factors = [f"Variable {var} has high impact" for var, _ in sorted_factors[:3]]
        
        return factors
    
    def add_historical_outcome(self, outcome: Dict[str, Any]) -> None:
        """Add a historical outcome for learning."""
        self.historical_outcomes.append(outcome)
        logger.info("Added historical outcome for learning")
    
    def learn_from_history(self) -> Dict[str, Any]:
        """Learn from historical outcomes to improve predictions."""
        if not self.historical_outcomes:
            return {"message": "No historical data available"}
        
        # Simple learning: identify patterns
        patterns = self._identify_patterns(self.historical_outcomes)
        
        return {
            "patterns_found": len(patterns),
            "patterns": patterns[:5],  # Top 5 patterns
        }
    
    def _identify_patterns(
        self,
        outcomes: List[Dict[str, Any]],
    ) -> List[str]:
        """Identify patterns in historical outcomes."""
        patterns = []
        
        # Simple pattern detection
        successful_outcomes = [o for o in outcomes if o.get("success", False)]
        failed_outcomes = [o for o in outcomes if not o.get("success", True)]
        
        if successful_outcomes:
            avg_confidence = sum(o.get("confidence", 0.5) for o in successful_outcomes) / len(successful_outcomes)
            patterns.append(f"Successful decisions have average confidence {avg_confidence:.2f}")
        
        if failed_outcomes:
            avg_confidence = sum(o.get("confidence", 0.5) for o in failed_outcomes) / len(failed_outcomes)
            patterns.append(f"Failed decisions have average confidence {avg_confidence:.2f}")
        
        return patterns
    
    def compare_predictions(
        self,
        predictions: List[Prediction],
    ) -> Dict[str, Any]:
        """Compare multiple predictions."""
        if not predictions:
            return {}
        
        comparison = {
            "total_predictions": len(predictions),
            "high_confidence": sum(1 for p in predictions if p.confidence == PredictionConfidence.HIGH),
            "medium_confidence": sum(1 for p in predictions if p.confidence == PredictionConfidence.MEDIUM),
            "low_confidence": sum(1 for p in predictions if p.confidence == PredictionConfidence.LOW),
            "average_success_probability": sum(
                p.probability_distribution.get("success", 0.5) for p in predictions
            ) / len(predictions),
        }
        
        return comparison
