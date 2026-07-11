"""executive_council.py

Executive council for coordinating multiple executive agents.
Enables collective decision-making and resource allocation.
"""

from __future__ import annotations

import uuid
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger
from src.decision.executive_agent import ExecutiveAgent

logger = get_logger(__name__)


class CouncilRole(str, Enum):
    """Roles in the executive council."""
    CHAIR = "chair"
    MEMBER = "member"
    ADVISOR = "advisor"
    OBSERVER = "observer"


class VotingMethod(str, Enum):
    """Voting methods for council decisions."""
    UNANIMOUS = "unanimous"
    MAJORITY = "majority"
    WEIGHTED = "weighted"
    CONSENSUS = "consensus"


@dataclass
class CouncilMember:
    """A member of the executive council."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    role: CouncilRole = CouncilRole.MEMBER
    agent: Optional[ExecutiveAgent] = None
    voting_weight: float = 1.0
    expertise: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "role": self.role.value,
            "voting_weight": self.voting_weight,
            "expertise": self.expertise,
            "metadata": self.metadata,
        }


@dataclass
class CouncilDecision:
    """A decision made by the council."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    proposal: str = ""
    votes: Dict[str, bool] = field(default_factory=dict)  # member_id -> vote
    outcome: Optional[bool] = None
    reasoning: str = ""
    timestamp: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "proposal": self.proposal,
            "votes": self.votes,
            "outcome": self.outcome,
            "reasoning": self.reasoning,
            "timestamp": self.timestamp,
            "metadata": self.metadata,
        }


class ExecutiveCouncil:
    """Executive council for coordinating multiple executive agents."""
    
    def __init__(self, voting_method: VotingMethod = VotingMethod.MAJORITY):
        self.members: Dict[str, CouncilMember] = {}
        self.voting_method = voting_method
        self.decision_history: List[CouncilDecision] = []
        self.chair_id: Optional[str] = None
        logger.info("ExecutiveCouncil initialized")
    
    def add_member(
        self,
        name: str,
        role: CouncilRole = CouncilRole.MEMBER,
        agent: Optional[ExecutiveAgent] = None,
        voting_weight: float = 1.0,
        expertise: Optional[List[str]] = None,
    ) -> CouncilMember:
        """Add a member to the council."""
        member = CouncilMember(
            name=name,
            role=role,
            agent=agent,
            voting_weight=voting_weight,
            expertise=expertise or [],
        )
        
        self.members[member.id] = member
        
        if role == CouncilRole.CHAIR:
            self.chair_id = member.id
        
        logger.info(f"Added council member: {name} as {role.value}")
        return member
    
    def remove_member(self, member_id: str) -> bool:
        """Remove a member from the council."""
        if member_id in self.members:
            del self.members[member_id]
            if self.chair_id == member_id:
                self.chair_id = None
            logger.info(f"Removed council member: {member_id}")
            return True
        return False
    
    def propose_decision(
        self,
        proposal: str,
        proposer_id: str,
    ) -> CouncilDecision:
        """Propose a decision for council vote."""
        from datetime import datetime, timezone
        
        decision = CouncilDecision(
            proposal=proposal,
            timestamp=datetime.now(timezone.utc).isoformat(),
        )
        
        self.decision_history.append(decision)
        logger.info(f"Proposed decision: {proposal}")
        
        return decision
    
    def cast_vote(
        self,
        decision_id: str,
        member_id: str,
        vote: bool,
    ) -> None:
        """Cast a vote on a decision."""
        decision = next(
            (d for d in self.decision_history if d.id == decision_id),
            None,
        )
        
        if decision is None:
            raise ValueError(f"Decision {decision_id} not found")
        
        if member_id not in self.members:
            raise ValueError(f"Member {member_id} not found")
        
        decision.votes[member_id] = vote
        logger.info(f"Member {member_id} voted {vote} on decision {decision_id}")
    
    def tally_votes(self, decision_id: str) -> Dict[str, Any]:
        """Tally votes for a decision."""
        decision = next(
            (d for d in self.decision_history if d.id == decision_id),
            None,
        )
        
        if decision is None:
            raise ValueError(f"Decision {decision_id} not found")
        
        if self.voting_method == VotingMethod.UNANIMOUS:
            outcome = all(decision.votes.values()) if decision.votes else False
        elif self.voting_method == VotingMethod.MAJORITY:
            votes = list(decision.votes.values())
            outcome = sum(votes) > len(votes) / 2 if votes else False
        elif self.voting_method == VotingMethod.WEIGHTED:
            weighted_sum = 0.0
            total_weight = 0.0
            for member_id, vote in decision.votes.items():
                member = self.members.get(member_id)
                if member:
                    weighted_sum += vote * member.voting_weight
                    total_weight += member.voting_weight
            outcome = weighted_sum > total_weight / 2 if total_weight > 0 else False
        else:  # CONSENSUS
            votes = list(decision.votes.values())
            outcome = all(votes) if votes else False
        
        decision.outcome = outcome
        decision.reasoning = self._generate_reasoning(decision, outcome)
        
        return {
            "decision_id": decision_id,
            "outcome": outcome,
            "vote_count": len(decision.votes),
            "votes_for": sum(decision.votes.values()),
            "votes_against": len(decision.votes) - sum(decision.votes.values()),
            "reasoning": decision.reasoning,
        }
    
    def _generate_reasoning(self, decision: CouncilDecision, outcome: bool) -> str:
        """Generate reasoning for the decision outcome."""
        votes_for = sum(decision.votes.values())
        votes_against = len(decision.votes) - votes_for
        
        if outcome:
            return f"Decision approved with {votes_for} votes for and {votes_against} against"
        else:
            return f"Decision rejected with {votes_for} votes for and {votes_against} against"
    
    def get_expert_opinion(
        self,
        topic: str,
        limit: int = 3,
    ) -> List[Dict[str, Any]]:
        """Get opinions from members with relevant expertise."""
        opinions = []
        
        for member in self.members.values():
            if any(exp.lower() in topic.lower() for exp in member.expertise):
                opinions.append({
                    "member_id": member.id,
                    "member_name": member.name,
                    "expertise": member.expertise,
                    "opinion": f"Based on expertise in {member.expertise}, I recommend proceeding with caution on {topic}",
                })
        
        return opinions[:limit]
    
    def allocate_resources(
        self,
        resources: Dict[str, float],
        priorities: Dict[str, float],
    ) -> Dict[str, float]:
        """Allocate resources based on council priorities."""
        total_priority = sum(priorities.values())
        
        allocation = {}
        for item, priority in priorities.items():
            if total_priority > 0:
                allocation[item] = (priority / total_priority) * resources.get("total", 100.0)
            else:
                allocation[item] = 0.0
        
        logger.info(f"Allocated resources: {allocation}")
        return allocation
    
    def get_council_status(self) -> Dict[str, Any]:
        """Get the current status of the council."""
        return {
            "total_members": len(self.members),
            "by_role": {
                role.value: sum(1 for m in self.members.values() if m.role == role)
                for role in CouncilRole
            },
            "chair": self.members.get(self.chair_id).name if self.chair_id else None,
            "voting_method": self.voting_method.value,
            "total_decisions": len(self.decision_history),
            "recent_decisions": [d.to_dict() for d in self.decision_history[-5:]],
        }
    
    def get_member(self, member_id: str) -> Optional[CouncilMember]:
        """Get a member by ID."""
        return self.members.get(member_id)
    
    def list_members(self) -> List[CouncilMember]:
        """List all council members."""
        return list(self.members.values())
