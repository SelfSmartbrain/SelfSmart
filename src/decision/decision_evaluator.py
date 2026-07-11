"""decision_evaluator.py

Evaluates decision options based on multiple criteria.
Scores options on utility, risk, and expected outcomes.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional
from dataclasses import dataclass

from src.config.logging import get_logger

if TYPE_CHECKING:
    from src.decision.decision_engine import DecisionContext, DecisionOption

logger = get_logger(__name__)


class DecisionEvaluator:
    """Evaluates decision options based on multiple criteria."""
    
    def __init__(self):
        self.evaluation_criteria = {
            "utility": 0.4,
            "feasibility": 0.2,
            "impact": 0.2,
            "alignment": 0.1,
            "speed": 0.1,
        }
        logger.info("DecisionEvaluator initialized")
    
    def evaluate_option(
        self,
        option: DecisionOption,
        context: DecisionContext,
    ) -> Dict[str, Any]:
        """Evaluate a decision option comprehensively."""
        logger.info(f"Evaluating option: {option.description}")
        
        # Evaluate each criterion
        utility_score = self._evaluate_utility(option, context)
        feasibility_score = self._evaluate_feasibility(option, context)
        impact_score = self._evaluate_impact(option, context)
        alignment_score = self._evaluate_alignment(option, context)
        speed_score = self._evaluate_speed(option, context)
        
        # Calculate weighted score
        weighted_score = (
            utility_score * self.evaluation_criteria["utility"] +
            feasibility_score * self.evaluation_criteria["feasibility"] +
            impact_score * self.evaluation_criteria["impact"] +
            alignment_score * self.evaluation_criteria["alignment"] +
            speed_score * self.evaluation_criteria["speed"]
        )
        
        # Estimate expected outcome
        expected_outcome = self._estimate_outcome(option, context)
        
        # Calculate confidence
        confidence = self._calculate_confidence(
            utility_score,
            feasibility_score,
            impact_score,
        )
        
        return {
            "utility_score": weighted_score,
            "utility_breakdown": {
                "utility": utility_score,
                "feasibility": feasibility_score,
                "impact": impact_score,
                "alignment": alignment_score,
                "speed": speed_score,
            },
            "risk_score": 1.0 - weighted_score,  # Simple inverse
            "confidence": confidence,
            "expected_outcome": expected_outcome,
        }
    
    def _evaluate_utility(
        self,
        option: DecisionOption,
        context: DecisionContext,
    ) -> float:
        """Evaluate the utility of an option."""
        score = 0.5  # Base score
        
        # Consider benefits
        if option.benefits:
            benefit_score = min(1.0, len(option.benefits) * 0.15)
            score += benefit_score * 0.5
        
        # Consider drawbacks
        if option.drawbacks:
            drawback_penalty = min(0.5, len(option.drawbacks) * 0.1)
            score -= drawback_penalty
        
        # Consider confidence
        score += (option.confidence - 0.5) * 0.3
        
        return max(0.0, min(1.0, score))
    
    def _evaluate_feasibility(
        self,
        option: DecisionOption,
        context: DecisionContext,
    ) -> float:
        """Evaluate the feasibility of an option."""
        score = 0.7  # Base score
        
        # Check resource constraints
        if context.available_resources:
            # Simple heuristic: if action requires resources we have, higher score
            action_type = option.action.get("type", "")
            if action_type in ["maintain", "incremental", "pilot"]:
                score += 0.2
            elif action_type in ["full_commitment", "innovate"]:
                score -= 0.1
        
        # Check constraints
        if context.constraints:
            # More constraints might reduce feasibility
            constraint_factor = max(0.5, 1.0 - len(context.constraints) * 0.05)
            score *= constraint_factor
        
        return max(0.0, min(1.0, score))
    
    def _evaluate_impact(
        self,
        option: DecisionOption,
        context: DecisionContext,
    ) -> float:
        """Evaluate the potential impact of an option."""
        score = 0.5  # Base score
        
        action_type = option.action.get("type", "")
        
        # Higher impact for bolder actions
        if action_type in ["full_commitment", "innovate", "rapid"]:
            score += 0.3
        elif action_type in ["phased", "pilot", "hybrid"]:
            score += 0.15
        elif action_type in ["maintain", "incremental"]:
            score += 0.05
        
        # Consider time horizon
        if context.time_horizon == "long":
            # Long-term favors bolder actions
            if action_type in ["full_commitment", "innovate"]:
                score += 0.1
        elif context.time_horizon == "short":
            # Short-term favors quick actions
            if action_type in ["maintain", "incremental"]:
                score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _evaluate_alignment(
        self,
        option: DecisionOption,
        context: DecisionContext,
    ) -> float:
        """Evaluate alignment with objectives."""
        if not context.objectives:
            return 0.7  # Neutral score if no objectives
        
        score = 0.5
        
        # Simple heuristic: check if benefits align with objectives
        for objective in context.objectives:
            for benefit in option.benefits:
                if objective.lower() in benefit.lower():
                    score += 0.1
        
        return max(0.0, min(1.0, score))
    
    def _evaluate_speed(
        self,
        option: DecisionOption,
        context: DecisionContext,
    ) -> float:
        """Evaluate how quickly the option can be executed."""
        score = 0.5
        
        action_type = option.action.get("type", "")
        
        # Faster actions get higher speed scores
        if action_type in ["maintain", "incremental"]:
            score += 0.3
        elif action_type in ["pilot", "rapid"]:
            score += 0.2
        elif action_type in ["phased", "hybrid"]:
            score += 0.1
        elif action_type in ["research", "consult"]:
            score -= 0.1
        
        return max(0.0, min(1.0, score))
    
    def _estimate_outcome(
        self,
        option: DecisionOption,
        context: DecisionContext,
    ) -> Dict[str, Any]:
        """Estimate the expected outcome of an option."""
        return {
            "probability_of_success": option.confidence,
            "expected_benefits": option.benefits,
            "expected_drawbacks": option.drawbacks,
            "time_to_result": self._estimate_time_to_result(option),
            "resource_consumption": self._estimate_resource_consumption(option, context),
        }
    
    def _estimate_time_to_result(self, option: DecisionOption) -> str:
        """Estimate time to see results."""
        action_type = option.action.get("type", "")
        
        time_map = {
            "maintain": "immediate",
            "incremental": "1-2 weeks",
            "pilot": "2-4 weeks",
            "phased": "1-3 months",
            "full_commitment": "3-6 months",
            "innovate": "3-6 months",
            "rapid": "1-2 weeks",
            "research": "1-2 weeks",
            "consult": "1-2 weeks",
        }
        
        return time_map.get(action_type, "1-3 months")
    
    def _estimate_resource_consumption(
        self,
        option: DecisionOption,
        context: DecisionContext,
    ) -> Dict[str, float]:
        """Estimate resource consumption."""
        action_type = option.action.get("type", "")
        
        # Simple heuristic estimates
        if action_type in ["maintain"]:
            return {"time": 0.1, "compute": 0.1, "financial": 0.1}
        elif action_type in ["incremental", "pilot"]:
            return {"time": 0.3, "compute": 0.3, "financial": 0.3}
        elif action_type in ["phased", "hybrid"]:
            return {"time": 0.5, "compute": 0.5, "financial": 0.5}
        elif action_type in ["full_commitment", "innovate"]:
            return {"time": 0.8, "compute": 0.8, "financial": 0.8}
        else:
            return {"time": 0.4, "compute": 0.4, "financial": 0.4}
    
    def _calculate_confidence(
        self,
        utility_score: float,
        feasibility_score: float,
        impact_score: float,
    ) -> float:
        """Calculate overall confidence in the evaluation."""
        # Confidence is higher when scores are consistent
        scores = [utility_score, feasibility_score, impact_score]
        mean_score = sum(scores) / len(scores)
        variance = sum((s - mean_score) ** 2 for s in scores) / len(scores)
        
        # Lower variance = higher confidence
        confidence = mean_score * (1.0 - variance)
        
        return max(0.0, min(1.0, confidence))
    
    def compare_options(
        self,
        options: List[DecisionOption],
        context: DecisionContext,
    ) -> List[Dict[str, Any]]:
        """Compare multiple options and return rankings."""
        evaluations = []
        
        for option in options:
            evaluation = self.evaluate_option(option, context)
            evaluations.append({
                "option_id": option.id,
                "description": option.description,
                "evaluation": evaluation,
            })
        
        # Sort by utility score
        evaluations.sort(key=lambda x: x["evaluation"]["utility_score"], reverse=True)
        
        return evaluations
