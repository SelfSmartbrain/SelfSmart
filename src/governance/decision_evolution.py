"""decision_evolution.py

Phase 16F: Decision Evolution Engine

Evolves decision-making strategies over time based on outcomes.
Implements:
- Learning from past decisions
- Strategy adaptation
- Continuous improvement
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


class EvolutionType(str, Enum):
    """Types of evolution."""
    PARAMETER_TUNING = "parameter_tuning"
    STRATEGY_SHIFT = "strategy_shift"
    CONSTRAINT_ADJUSTMENT = "constraint_adjustment"
    OBJECTIVE_REWEIGHTING = "objective_reweighting"


class EvolutionStatus(str, Enum):
    """Status of an evolution."""
    PROPOSED = "proposed"
    TESTING = "testing"
    ADOPTED = "adopted"
    REJECTED = "rejected"
    ROLLED_BACK = "rolled_back"


@dataclass
class EvolutionProposal:
    """A proposal to evolve decision-making."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    evolution_type: EvolutionType = EvolutionType.PARAMETER_TUNING
    description: str = ""
    current_state: Dict[str, Any] = field(default_factory=dict)
    proposed_state: Dict[str, Any] = field(default_factory=dict)
    expected_improvement: float = 0.0
    confidence: float = 0.0
    evidence: List[str] = field(default_factory=list)
    status: EvolutionStatus = EvolutionStatus.PROPOSED
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    tested_at: Optional[datetime] = None
    adopted_at: Optional[datetime] = None
    actual_improvement: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "evolution_type": self.evolution_type.value,
            "description": self.description,
            "current_state": self.current_state,
            "proposed_state": self.proposed_state,
            "expected_improvement": self.expected_improvement,
            "confidence": self.confidence,
            "evidence": self.evidence,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "tested_at": self.tested_at.isoformat() if self.tested_at else None,
            "adopted_at": self.adopted_at.isoformat() if self.adopted_at else None,
            "actual_improvement": self.actual_improvement,
            "metadata": self.metadata,
        }


class DecisionEvolutionEngine:
    """Evolves decision-making strategies over time."""
    
    def __init__(self):
        self.proposals: Dict[str, EvolutionProposal] = {}
        self.decision_history: List[Dict[str, Any]] = []
        self.current_parameters: Dict[str, Any] = {
            "risk_tolerance_default": 0.5,
            "time_horizon_default": "medium",
            "utility_weights": {
                "benefit": 0.7,
                "cost": 0.3,
            },
        }
        logger.info("DecisionEvolutionEngine initialized")
    
    def add_decision(self, decision_data: Dict[str, Any]) -> None:
        """Add a decision to history for learning."""
        self.decision_history.append(decision_data)
        
        # Periodically propose evolutions
        if len(self.decision_history) % 20 == 0:
            self.propose_evolutions()
    
    def propose_evolutions(self) -> List[EvolutionProposal]:
        """Propose evolutions based on decision history."""
        if len(self.decision_history) < 10:
            logger.info("Not enough decisions to propose evolutions")
            return []
        
        proposals = []
        
        # Analyze success patterns
        successful = [
            d for d in self.decision_history
            if d.get("outcome", {}).get("success", False)
        ]
        
        failed = [
            d for d in self.decision_history
            if d.get("outcome") and not d.get("outcome", {}).get("success", False)
        ]
        
        if len(successful) >= 5 and len(failed) >= 3:
            # Propose parameter tuning based on successful decisions
            proposals.extend(self._propose_parameter_tuning(successful, failed))
            
            # Propose strategy shifts
            proposals.extend(self._propose_strategy_shifts(successful, failed))
        
        # Store proposals
        for proposal in proposals:
            self.proposals[proposal.id] = proposal
        
        logger.info(f"Proposed {len(proposals)} evolutions")
        
        return proposals
    
    def _propose_parameter_tuning(
        self,
        successful: List[Dict[str, Any]],
        failed: List[Dict[str, Any]],
    ) -> List[EvolutionProposal]:
        """Propose parameter tuning evolutions."""
        proposals = []
        
        # Analyze risk tolerance in successful vs failed decisions
        success_risks = []
        for decision in successful:
            context = decision.get("context", {})
            risk = context.get("risk_tolerance", 0.5)
            success_risks.append(risk)
        
        fail_risks = []
        for decision in failed:
            context = decision.get("context", {})
            risk = context.get("risk_tolerance", 0.5)
            fail_risks.append(risk)
        
        if success_risks and fail_risks:
            avg_success_risk = sum(success_risks) / len(success_risks)
            avg_fail_risk = sum(fail_risks) / len(fail_risks)
            
            # If successful decisions have different risk tolerance
            if abs(avg_success_risk - avg_fail_risk) > 0.1:
                current_risk = self.current_parameters.get("risk_tolerance_default", 0.5)
                proposed_risk = avg_success_risk
                
                proposal = EvolutionProposal(
                    evolution_type=EvolutionType.PARAMETER_TUNING,
                    description=f"Adjust default risk tolerance from {current_risk:.2f} to {proposed_risk:.2f}",
                    current_state={"risk_tolerance_default": current_risk},
                    proposed_state={"risk_tolerance_default": proposed_risk},
                    expected_improvement=abs(avg_success_risk - avg_fail_risk),
                    confidence=min(1.0, len(successful) / 20),
                    evidence=[
                        f"Successful decisions had avg risk tolerance: {avg_success_risk:.2f}",
                        f"Failed decisions had avg risk tolerance: {avg_fail_risk:.2f}",
                    ],
                )
                proposals.append(proposal)
        
        return proposals
    
    def _propose_strategy_shifts(
        self,
        successful: List[Dict[str, Any]],
        failed: List[Dict[str, Any]],
    ) -> List[EvolutionProposal]:
        """Propose strategy shift evolutions."""
        proposals = []
        
        # Analyze time horizon patterns
        success_horizons = [d.get("context", {}).get("time_horizon") for d in successful]
        fail_horizons = [d.get("context", {}).get("time_horizon") for d in failed]
        
        from collections import Counter
        success_horizon_counts = Counter([h for h in success_horizons if h])
        fail_horizon_counts = Counter([h for h in fail_horizons if h])
        
        # Find time horizons that correlate with success
        for horizon, count in success_horizon_counts.most_common():
            if count >= 3:
                success_rate = count / len(successful)
                fail_count = fail_horizon_counts.get(horizon, 0)
                fail_rate = fail_count / len(failed) if failed else 0
                
                if success_rate > fail_rate + 0.2:
                    current_horizon = self.current_parameters.get("time_horizon_default", "medium")
                    
                    if current_horizon != horizon:
                        proposal = EvolutionProposal(
                            evolution_type=EvolutionType.STRATEGY_SHIFT,
                            description=f"Shift default time horizon from {current_horizon} to {horizon}",
                            current_state={"time_horizon_default": current_horizon},
                            proposed_state={"time_horizon_default": horizon},
                            expected_improvement=success_rate - fail_rate,
                            confidence=min(1.0, count / 10),
                            evidence=[
                                f"{horizon} time horizon success rate: {success_rate:.2f}",
                                f"{horizon} time horizon failure rate: {fail_rate:.2f}",
                            ],
                        )
                        proposals.append(proposal)
        
        return proposals
    
    def adopt_evolution(self, proposal_id: str) -> bool:
        """Adopt an evolution proposal."""
        proposal = self.proposals.get(proposal_id)
        if proposal is None:
            return False
        
        # Apply the evolution
        for key, value in proposal.proposed_state.items():
            self.current_parameters[key] = value
        
        proposal.status = EvolutionStatus.ADOPTED
        proposal.adopted_at = datetime.now(timezone.utc)
        
        logger.info(f"Adopted evolution: {proposal_id}")
        
        return True
    
    def test_evolution(self, proposal_id: str, test_decisions: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Test an evolution proposal against sample decisions."""
        proposal = self.proposals.get(proposal_id)
        if proposal is None:
            return {"error": "Proposal not found"}
        
        # Apply proposed parameters temporarily
        old_parameters = self.current_parameters.copy()
        
        for key, value in proposal.proposed_state.items():
            self.current_parameters[key] = value
        
        # Simulate decisions with new parameters
        # In a real implementation, this would re-run decisions
        test_results = []
        
        for decision in test_decisions:
            # Simple simulation - check if decision would be different
            context = decision.get("context", {})
            
            # Apply new parameters
            for key, value in proposal.proposed_state.items():
                if key in context:
                    context[key] = value
            
            # Check if outcome would improve
            outcome = decision.get("outcome", {})
            if outcome.get("success", False):
                test_results.append(True)
            else:
                test_results.append(False)
        
        # Restore old parameters
        self.current_parameters = old_parameters
        
        # Calculate improvement
        if test_results:
            improvement_rate = sum(test_results) / len(test_results)
        else:
            improvement_rate = 0.0
        
        proposal.status = EvolutionStatus.TESTING
        proposal.tested_at = datetime.now(timezone.utc)
        proposal.actual_improvement = improvement_rate
        
        return {
            "proposal_id": proposal_id,
            "improvement_rate": improvement_rate,
            "test_count": len(test_results),
            "recommended": improvement_rate > proposal.expected_improvement * 0.8,
        }
    
    def get_proposal(self, proposal_id: str) -> Optional[EvolutionProposal]:
        """Get an evolution proposal by ID."""
        return self.proposals.get(proposal_id)
    
    def get_current_parameters(self) -> Dict[str, Any]:
        """Get current decision parameters."""
        return self.current_parameters.copy()
    
    def get_evolution_statistics(self) -> Dict[str, Any]:
        """Get statistics about evolutions."""
        total_proposals = len(self.proposals)
        
        by_status = {
            status.value: len([p for p in self.proposals.values() if p.status == status])
            for status in EvolutionStatus
        }
        
        by_type = {
            e_type.value: len([p for p in self.proposals.values() if p.evolution_type == e_type])
            for e_type in EvolutionType
        }
        
        adopted = len([p for p in self.proposals.values() if p.status == EvolutionStatus.ADOPTED])
        
        return {
            "total_proposals": total_proposals,
            "by_status": by_status,
            "by_type": by_type,
            "adopted_count": adopted,
            "current_parameters": self.current_parameters,
            "decisions_analyzed": len(self.decision_history),
        }
