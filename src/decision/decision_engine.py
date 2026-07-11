"""decision_engine.py

Core decision engine that orchestrates option generation, evaluation, and selection.
Provides the central interface for making strategic decisions under uncertainty.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any, Callable
from enum import Enum
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.decision.option_generator import OptionGenerator
from src.decision.decision_evaluator import DecisionEvaluator
from src.decision.risk_engine import RiskEngine
from src.decision.decision_memory import DecisionMemory

logger = get_logger(__name__)


class DecisionStatus(str, Enum):
    """Status of a decision."""
    PENDING = "pending"
    EVALUATING = "evaluating"
    DECIDED = "decided"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class DecisionContext:
    """Context in which a decision is made."""
    current_state: Dict[str, Any] = field(default_factory=dict)
    available_resources: Dict[str, Any] = field(default_factory=dict)
    constraints: List[str] = field(default_factory=list)
    time_horizon: str = "medium"  # short, medium, long
    risk_tolerance: float = 0.5  # 0.0 to 1.0
    objectives: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class DecisionOption:
    """A potential decision option."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    description: str = ""
    action: Dict[str, Any] = field(default_factory=dict)
    expected_outcome: Dict[str, Any] = field(default_factory=dict)
    utility_score: float = 0.0
    risk_score: float = 0.0
    confidence: float = 0.0
    cost: Dict[str, float] = field(default_factory=dict)
    benefits: List[str] = field(default_factory=list)
    drawbacks: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "description": self.description,
            "action": self.action,
            "expected_outcome": self.expected_outcome,
            "utility_score": self.utility_score,
            "risk_score": self.risk_score,
            "confidence": self.confidence,
            "cost": self.cost,
            "benefits": self.benefits,
            "drawbacks": self.drawbacks,
            "metadata": self.metadata,
        }


@dataclass
class Decision:
    """A strategic decision."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    context: DecisionContext = field(default_factory=DecisionContext)
    options: List[DecisionOption] = field(default_factory=list)
    selected_option_id: Optional[str] = None
    status: DecisionStatus = DecisionStatus.PENDING
    reasoning: str = ""
    confidence: float = 0.0
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    decided_at: Optional[datetime] = None
    executed_at: Optional[datetime] = None
    outcome: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "context": {
                "current_state": self.context.current_state,
                "available_resources": self.context.available_resources,
                "constraints": self.context.constraints,
                "time_horizon": self.context.time_horizon,
                "risk_tolerance": self.context.risk_tolerance,
                "objectives": self.context.objectives,
            },
            "options": [opt.to_dict() for opt in self.options],
            "selected_option_id": self.selected_option_id,
            "status": self.status.value,
            "reasoning": self.reasoning,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "decided_at": self.decided_at.isoformat() if self.decided_at else None,
            "executed_at": self.executed_at.isoformat() if self.executed_at else None,
            "outcome": self.outcome,
            "metadata": self.metadata,
        }


class DecisionEngine:
    """Core decision engine for strategic decision-making."""
    
    def __init__(
        self,
        option_generator: Optional[OptionGenerator] = None,
        decision_evaluator: Optional[DecisionEvaluator] = None,
        risk_engine: Optional[RiskEngine] = None,
        decision_memory: Optional[DecisionMemory] = None,
    ):
        self.option_generator = option_generator or OptionGenerator()
        self.decision_evaluator = decision_evaluator or DecisionEvaluator()
        self.risk_engine = risk_engine or RiskEngine()
        self.decision_memory = decision_memory or DecisionMemory()
        self.active_decisions: Dict[str, Decision] = {}
        logger.info("DecisionEngine initialized")
    
    def make_decision(
        self,
        query: str,
        context: Optional[DecisionContext] = None,
        num_options: int = 5,
    ) -> Decision:
        """Make a strategic decision given a query and context."""
        logger.info(f"Making decision for query: {query}")
        
        context = context or DecisionContext()
        decision = Decision(query=query, context=context)
        
        # Generate options
        options = self.option_generator.generate_options(
            query=query,
            context=context,
            num_options=num_options,
        )
        decision.options = options
        
        # Evaluate options
        decision.status = DecisionStatus.EVALUATING
        for option in decision.options:
            evaluation = self.decision_evaluator.evaluate_option(
                option=option,
                context=context,
            )
            option.utility_score = evaluation["utility_score"]
            option.risk_score = evaluation["risk_score"]
            option.confidence = evaluation["confidence"]
            option.expected_outcome = evaluation["expected_outcome"]
        
        # Assess risks
        for option in decision.options:
            risk_assessment = self.risk_engine.assess_risk(
                option=option,
                context=context,
            )
            option.risk_score = risk_assessment["overall_risk"]
            option.metadata["risk_details"] = risk_assessment
        
        # Select best option
        selected_option = self._select_best_option(decision.options, context)
        decision.selected_option_id = selected_option.id
        decision.reasoning = self._generate_reasoning(selected_option, decision.options)
        decision.confidence = selected_option.confidence
        decision.status = DecisionStatus.DECIDED
        decision.decided_at = datetime.now(timezone.utc)
        
        # Store decision
        self.active_decisions[decision.id] = decision
        self.decision_memory.store_decision(decision)
        
        logger.info(f"Decision made: {decision.id} -> {selected_option.id}")
        return decision
    
    def _select_best_option(
        self,
        options: List[DecisionOption],
        context: DecisionContext,
    ) -> DecisionOption:
        """Select the best option based on utility and risk tolerance."""
        if not options:
            raise ValueError("No options to select from")
        
        # Calculate adjusted score considering risk tolerance
        best_option = None
        best_score = -float("inf")
        
        for option in options:
            # Adjust utility by risk based on risk tolerance
            risk_adjustment = option.risk_score * (1.0 - context.risk_tolerance)
            adjusted_score = option.utility_score - risk_adjustment
            
            if adjusted_score > best_score:
                best_score = adjusted_score
                best_option = option
        
        return best_option
    
    def _generate_reasoning(
        self,
        selected_option: DecisionOption,
        all_options: List[DecisionOption],
    ) -> str:
        """Generate explanation for the decision."""
        reasoning_parts = [
            f"Selected option with utility score {selected_option.utility_score:.2f}",
            f"Risk score: {selected_option.risk_score:.2f}",
            f"Confidence: {selected_option.confidence:.2f}",
        ]
        
        if selected_option.benefits:
            reasoning_parts.append(f"Key benefits: {', '.join(selected_option.benefits[:3])}")
        
        if selected_option.drawbacks:
            reasoning_parts.append(f"Considerations: {', '.join(selected_option.drawbacks[:2])}")
        
        return ". ".join(reasoning_parts)
    
    def execute_decision(self, decision_id: str) -> Dict[str, Any]:
        """Execute a selected decision."""
        if decision_id not in self.active_decisions:
            raise ValueError(f"Decision {decision_id} not found")
        
        decision = self.active_decisions[decision_id]
        
        if decision.status != DecisionStatus.DECIDED:
            raise ValueError(f"Decision {decision_id} not in decided state")
        
        logger.info(f"Executing decision: {decision_id}")
        
        # In a real implementation, this would execute the action
        decision.status = DecisionStatus.EXECUTED
        decision.executed_at = datetime.now(timezone.utc)
        
        # Store execution
        self.decision_memory.update_decision(decision)
        
        return {
            "decision_id": decision_id,
            "status": "executed",
            "executed_at": decision.executed_at.isoformat(),
        }
    
    def record_outcome(self, decision_id: str, outcome: Dict[str, Any]) -> None:
        """Record the outcome of a decision."""
        if decision_id not in self.active_decisions:
            raise ValueError(f"Decision {decision_id} not found")
        
        decision = self.active_decisions[decision_id]
        decision.outcome = outcome
        
        # Update memory with outcome
        self.decision_memory.record_outcome(decision_id, outcome)
        
        logger.info(f"Recorded outcome for decision: {decision_id}")
    
    def get_decision(self, decision_id: str) -> Optional[Decision]:
        """Get a decision by ID."""
        return self.active_decisions.get(decision_id)
    
    def list_decisions(self, status: Optional[DecisionStatus] = None) -> List[Decision]:
        """List all decisions, optionally filtered by status."""
        if status:
            return [d for d in self.active_decisions.values() if d.status == status]
        return list(self.active_decisions.values())
    
    def get_decision_statistics(self) -> Dict[str, Any]:
        """Get statistics about decisions."""
        decisions = list(self.active_decisions.values())
        
        if not decisions:
            return {"total_decisions": 0}
        
        return {
            "total_decisions": len(decisions),
            "by_status": {
                status.value: sum(1 for d in decisions if d.status == status)
                for status in DecisionStatus
            },
            "average_confidence": sum(d.confidence for d in decisions) / len(decisions),
            "decisions_with_outcomes": sum(1 for d in decisions if d.outcome),
        }
