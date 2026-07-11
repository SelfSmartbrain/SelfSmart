"""decision_marketplace.py

Phase 15I: Decision Marketplace

Enables multiple agents to propose competing decisions and strategies.
Agents compete on predicted value, and the best proposal is selected.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


class ProposalStatus(str, Enum):
    """Status of a decision proposal."""
    PENDING = "pending"
    UNDER_REVIEW = "under_review"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    SUPERSEDED = "superseded"


@dataclass
class DecisionProposal:
    """A proposal for a decision from an agent."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent_id: str = ""
    agent_name: str = ""
    decision_query: str = ""
    proposed_action: Dict[str, Any] = field(default_factory=dict)
    expected_outcome: Dict[str, Any] = field(default_factory=dict)
    predicted_value: float = 0.0
    confidence: float = 0.0
    risk_assessment: Dict[str, float] = field(default_factory=dict)
    reasoning: str = ""
    evidence: List[str] = field(default_factory=list)
    cost_estimate: Dict[str, float] = field(default_factory=dict)
    time_estimate: float = 0.0
    status: ProposalStatus = ProposalStatus.PENDING
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    reviewed_at: Optional[datetime] = None
    score: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "agent_id": self.agent_id,
            "agent_name": self.agent_name,
            "decision_query": self.decision_query,
            "proposed_action": self.proposed_action,
            "expected_outcome": self.expected_outcome,
            "predicted_value": self.predicted_value,
            "confidence": self.confidence,
            "risk_assessment": self.risk_assessment,
            "reasoning": self.reasoning,
            "evidence": self.evidence,
            "cost_estimate": self.cost_estimate,
            "time_estimate": self.time_estimate,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "reviewed_at": self.reviewed_at.isoformat() if self.reviewed_at else None,
            "score": self.score,
            "metadata": self.metadata,
        }


@dataclass
class MarketplaceListing:
    """A listing in the decision marketplace."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    query: str = ""
    description: str = ""
    context: Dict[str, Any] = field(default_factory=dict)
    proposals: List[DecisionProposal] = field(default_factory=list)
    deadline: Optional[datetime] = None
    status: str = "open"  # open, closed, awarded
    selected_proposal_id: Optional[str] = None
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    closed_at: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "query": self.query,
            "description": self.description,
            "context": self.context,
            "proposals": [p.to_dict() for p in self.proposals],
            "deadline": self.deadline.isoformat() if self.deadline else None,
            "status": self.status,
            "selected_proposal_id": self.selected_proposal_id,
            "created_at": self.created_at.isoformat(),
            "closed_at": self.closed_at.isoformat() if self.closed_at else None,
            "metadata": self.metadata,
        }


class DecisionMarketplace:
    """Marketplace for competing decision proposals."""
    
    def __init__(self):
        self.listings: Dict[str, MarketplaceListing] = {}
        self.proposals: Dict[str, DecisionProposal] = {}
        self.agent_reputation: Dict[str, float] = {}  # agent_id -> reputation score
        logger.info("DecisionMarketplace initialized")
    
    def create_listing(
        self,
        query: str,
        description: str = "",
        context: Optional[Dict[str, Any]] = None,
        deadline: Optional[datetime] = None,
    ) -> MarketplaceListing:
        """Create a new listing for decision proposals."""
        listing = MarketplaceListing(
            query=query,
            description=description,
            context=context or {},
            deadline=deadline,
        )
        
        self.listings[listing.id] = listing
        logger.info(f"Created marketplace listing: {listing.id}")
        
        return listing
    
    def submit_proposal(
        self,
        listing_id: str,
        agent_id: str,
        agent_name: str,
        proposed_action: Dict[str, Any],
        expected_outcome: Dict[str, Any],
        predicted_value: float,
        confidence: float,
        reasoning: str,
        evidence: Optional[List[str]] = None,
        cost_estimate: Optional[Dict[str, float]] = None,
        time_estimate: float = 0.0,
        risk_assessment: Optional[Dict[str, float]] = None,
    ) -> DecisionProposal:
        """Submit a proposal to a listing."""
        listing = self.listings.get(listing_id)
        if listing is None:
            raise ValueError(f"Listing {listing_id} not found")
        
        if listing.status != "open":
            raise ValueError(f"Listing {listing_id} is not open for proposals")
        
        if listing.deadline and datetime.now(timezone.utc) > listing.deadline:
            raise ValueError(f"Listing {listing_id} has passed deadline")
        
        proposal = DecisionProposal(
            agent_id=agent_id,
            agent_name=agent_name,
            decision_query=listing.query,
            proposed_action=proposed_action,
            expected_outcome=expected_outcome,
            predicted_value=predicted_value,
            confidence=confidence,
            reasoning=reasoning,
            evidence=evidence or [],
            cost_estimate=cost_estimate or {},
            time_estimate=time_estimate,
            risk_assessment=risk_assessment or {},
        )
        
        listing.proposals.append(proposal)
        self.proposals[proposal.id] = proposal
        
        logger.info(f"Submitted proposal {proposal.id} to listing {listing_id}")
        
        return proposal
    
    def evaluate_proposals(
        self,
        listing_id: str,
        value_weight: float = 0.4,
        confidence_weight: float = 0.3,
        risk_weight: float = 0.2,
        reputation_weight: float = 0.1,
    ) -> List[DecisionProposal]:
        """Evaluate and score all proposals for a listing."""
        listing = self.listings.get(listing_id)
        if listing is None:
            raise ValueError(f"Listing {listing_id} not found")
        
        scored_proposals = []
        
        for proposal in listing.proposals:
            # Calculate composite score
            value_score = proposal.predicted_value
            confidence_score = proposal.confidence
            
            # Calculate risk score (lower risk = higher score)
            if proposal.risk_assessment:
                avg_risk = sum(proposal.risk_assessment.values()) / len(proposal.risk_assessment)
                risk_score = 1.0 - avg_risk
            else:
                risk_score = 0.5
            
            # Get reputation score
            reputation_score = self.agent_reputation.get(proposal.agent_id, 0.5)
            
            # Composite score
            proposal.score = (
                value_score * value_weight +
                confidence_score * confidence_weight +
                risk_score * risk_weight +
                reputation_score * reputation_weight
            )
            
            scored_proposals.append(proposal)
        
        # Sort by score descending
        scored_proposals.sort(key=lambda p: p.score, reverse=True)
        
        logger.info(f"Evaluated {len(scored_proposals)} proposals for listing {listing_id}")
        
        return scored_proposals
    
    def select_proposal(
        self,
        listing_id: str,
        proposal_id: Optional[str] = None,
    ) -> DecisionProposal:
        """Select the winning proposal for a listing."""
        listing = self.listings.get(listing_id)
        if listing is None:
            raise ValueError(f"Listing {listing_id} not found")
        
        if proposal_id is None:
            # Auto-select best proposal
            scored_proposals = self.evaluate_proposals(listing_id)
            if not scored_proposals:
                raise ValueError(f"No proposals to select from for listing {listing_id}")
            selected = scored_proposals[0]
        else:
            selected = next(
                (p for p in listing.proposals if p.id == proposal_id),
                None,
            )
            if selected is None:
                raise ValueError(f"Proposal {proposal_id} not found")
        
        # Update statuses
        selected.status = ProposalStatus.ACCEPTED
        selected.reviewed_at = datetime.now(timezone.utc)
        
        # Mark others as rejected
        for proposal in listing.proposals:
            if proposal.id != selected.id:
                proposal.status = ProposalStatus.REJECTED
        
        listing.selected_proposal_id = selected.id
        listing.status = "awarded"
        listing.closed_at = datetime.now(timezone.utc)
        
        # Update agent reputation
        self._update_reputation(selected.agent_id, success=True)
        
        logger.info(f"Selected proposal {selected.id} for listing {listing_id}")
        
        return selected
    
    def _update_reputation(self, agent_id: str, success: bool) -> None:
        """Update agent reputation based on outcome."""
        current_rep = self.agent_reputation.get(agent_id, 0.5)
        
        if success:
            # Increase reputation
            new_rep = min(1.0, current_rep + 0.05)
        else:
            # Decrease reputation
            new_rep = max(0.0, current_rep - 0.1)
        
        self.agent_reputation[agent_id] = new_rep
        logger.info(f"Updated reputation for agent {agent_id}: {current_rep:.2f} -> {new_rep:.2f}")
    
    def record_outcome(
        self,
        proposal_id: str,
        actual_outcome: Dict[str, Any],
        success: bool,
    ) -> None:
        """Record the actual outcome of a selected proposal."""
        proposal = self.proposals.get(proposal_id)
        if proposal is None:
            raise ValueError(f"Proposal {proposal_id} not found")
        
        proposal.metadata["actual_outcome"] = actual_outcome
        proposal.metadata["success"] = success
        
        # Update reputation based on success
        self._update_reputation(proposal.agent_id, success)
        
        logger.info(f"Recorded outcome for proposal {proposal_id}: success={success}")
    
    def get_listing(self, listing_id: str) -> Optional[MarketplaceListing]:
        """Get a listing by ID."""
        return self.listings.get(listing_id)
    
    def get_proposal(self, proposal_id: str) -> Optional[DecisionProposal]:
        """Get a proposal by ID."""
        return self.proposals.get(proposal_id)
    
    def list_listings(self, status: Optional[str] = None) -> List[MarketplaceListing]:
        """List all listings, optionally filtered by status."""
        if status:
            return [l for l in self.listings.values() if l.status == status]
        return list(self.listings.values())
    
    def list_proposals(self, listing_id: str) -> List[DecisionProposal]:
        """List all proposals for a listing."""
        listing = self.listings.get(listing_id)
        if listing is None:
            return []
        return listing.proposals
    
    def get_agent_reputation(self, agent_id: str) -> float:
        """Get an agent's reputation score."""
        return self.agent_reputation.get(agent_id, 0.5)
    
    def get_marketplace_statistics(self) -> Dict[str, Any]:
        """Get statistics about the marketplace."""
        total_listings = len(self.listings)
        total_proposals = len(self.proposals)
        
        accepted_proposals = sum(
            1 for p in self.proposals.values() if p.status == ProposalStatus.ACCEPTED
        )
        
        avg_confidence = (
            sum(p.confidence for p in self.proposals.values()) / total_proposals
            if total_proposals > 0 else 0.0
        )
        
        return {
            "total_listings": total_listings,
            "total_proposals": total_proposals,
            "accepted_proposals": accepted_proposals,
            "acceptance_rate": accepted_proposals / total_proposals if total_proposals > 0 else 0.0,
            "average_confidence": avg_confidence,
            "active_agents": len(self.agent_reputation),
        }
