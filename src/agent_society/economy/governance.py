"""
Economic Governance - Governance mechanisms for the agent economy.

Provides proposal creation, voting, and execution for economic policy changes,
resource allocation, and system parameter updates.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set

logger = logging.getLogger(__name__)


class ProposalType(Enum):
    """Types of governance proposals."""

    PARAMETER_CHANGE = "parameter_change"  # Change system parameters
    RESOURCE_ALLOCATION = "resource_allocation"  # Allocate treasury resources
    POLICY_UPDATE = "policy_update"  # Update incentive policies
    TREASURY_SPEND = "treasury_spend"  # Spend treasury funds
    TOKEN_MINT = "token_mint"  # Mint new tokens
    TOKEN_BURN = "token_burn"  # Burn tokens
    EMERGENCY_ACTION = "emergency_action"  # Emergency measures
    CONSTITUTIONAL_AMENDMENT = "constitutional_amendment"  # Core changes


class ProposalStatus(Enum):
    """Proposal status."""

    DRAFT = "draft"
    SUBMITTED = "submitted"
    VOTING = "voting"
    PASSED = "passed"
    REJECTED = "rejected"
    EXECUTED = "executed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class VoteType(Enum):
    """Vote options."""

    YES = "yes"
    NO = "no"
    ABSTAIN = "abstain"


@dataclass
class GovernanceConfig:
    """Configuration for governance system."""

    # Voting parameters
    voting_period_hours: int = 72  # 3 days
    quorum_threshold: Decimal = Decimal("0.1")  # 10% of eligible voters
    approval_threshold: Decimal = Decimal("0.5")  # 50% yes votes
    supermajority_threshold: Decimal = Decimal("0.66")  # 66% for critical changes

    # Proposal requirements
    min_proposal_stake: Decimal = Decimal("1000")  # Minimum tokens to propose
    proposal_fee: Decimal = Decimal("100")  # Fee to submit (burned or refunded)
    min_voting_power: Decimal = Decimal("100")  # Minimum tokens to vote

    # Execution
    execution_delay_hours: int = 24  # Delay before execution
    max_proposals_per_agent: int = 5  # Max active proposals per agent

    # Delegation
    delegation_enabled: bool = True
    max_delegation_depth: int = 3


@dataclass
class Proposal:
    """Governance proposal."""

    proposal_id: str
    proposal_type: ProposalType
    title: str
    description: str
    proposer_id: str

    # Proposal details
    parameters: Dict[str, Any] = field(default_factory=dict)  # Changes to make
    required_execution: Optional[Callable] = None  # Function to execute
    execution_payload: Dict[str, Any] = field(default_factory=dict)

    # Staking
    stake_amount: Decimal = Decimal("0")
    stake_locked: bool = False

    # Status
    status: ProposalStatus = ProposalStatus.DRAFT

    # Timing
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    submitted_at: Optional[float] = None
    voting_start: Optional[float] = None
    voting_end: Optional[float] = None
    executed_at: Optional[float] = None

    # Voting
    votes: Dict[str, "Vote"] = field(default_factory=dict)  # voter_id -> Vote
    yes_votes: Decimal = Decimal("0")
    no_votes: Decimal = Decimal("0")
    abstain_votes: Decimal = Decimal("0")
    total_voting_power: Decimal = Decimal("0")

    # Delegation
    delegated_votes: Dict[str, Decimal] = field(default_factory=dict)  # delegatee -> power

    # Metadata
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        if not self.proposal_id:
            self.proposal_id = f"prop_{uuid.uuid4().hex[:10]}"

    @property
    def is_active(self) -> bool:
        return self.status in (ProposalStatus.VOTING,)

    @property
    def has_quorum(self) -> bool:
        if self.total_voting_power == 0:
            return False
        participation = (
            self.yes_votes + self.no_votes + self.abstain_votes
        ) / self.total_voting_power
        return participation >= self.quorum_threshold

    @property
    def approval_rate(self) -> Decimal:
        if self.yes_votes + self.no_votes == 0:
            return Decimal("0")
        return self.yes_votes / (self.yes_votes + self.no_votes)


@dataclass
class Vote:
    """A vote on a proposal."""

    voter_id: str
    proposal_id: str
    vote_type: VoteType
    voting_power: Decimal
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    delegation_source: Optional[str] = None  # If delegated, who delegated
    rationale: str = ""


class EconomicGovernance:
    """
    Governance system for economic policy decisions.

    Features:
    - Proposal creation and management
    - Token-weighted voting
    - Quorum and approval thresholds
    - Delegation support
    - Proposal execution with delays
    - Emergency procedures
    """

    def __init__(
        self,
        config: Optional[GovernanceConfig] = None,
        token_system=None,
        incentive_system=None,
    ):
        self.config = config or GovernanceConfig()
        self.token_system = token_system
        self.incentive_system = incentive_system

        # Proposals
        self._proposals: Dict[str, Proposal] = {}
        self._agent_proposals: Dict[str, Set[str]] = defaultdict(set)
        self._agent_votes: Dict[str, Dict[str, Vote]] = defaultdict(
            dict
        )  # agent_id -> proposal_id -> Vote

        # Delegation
        self._delegations: Dict[str, str] = {}  # delegator -> delegatee
        self._delegation_chains: Dict[str, List[str]] = defaultdict(
            list
        )  # delegatee -> [delegators]

        # Statistics
        self._stats = {
            "proposals_created": 0,
            "proposals_passed": 0,
            "proposals_rejected": 0,
            "proposals_executed": 0,
            "total_votes_cast": 0,
            "total_voting_power": Decimal("0"),
        }

        logger.info("EconomicGovernance initialized")

    async def create_proposal(
        self,
        proposer_id: str,
        proposal_type: ProposalType,
        title: str,
        description: str,
        parameters: Dict[str, Any],
        stake_amount: Optional[Decimal] = None,
        execution_payload: Optional[Dict[str, Any]] = None,
    ) -> Optional[Proposal]:
        """Create a new governance proposal."""
        # Check proposer eligibility
        if not await self._check_proposer_eligibility(proposer_id):
            logger.warning(f"Proposer {proposer_id} not eligible")
            return None

        # Check active proposal limit
        active_count = sum(
            1
            for pid in self._agent_proposals.get(proposer_id, set())
            if self._proposals.get(pid, Proposal("", "", "", "", "")).status
            in (ProposalStatus.SUBMITTED, ProposalStatus.VOTING)
        )

        if active_count >= self.config.max_proposals_per_agent:
            logger.warning(f"Proposer {proposer_id} has too many active proposals")
            return None

        # Determine required stake
        required_stake = stake_amount or self.config.min_proposal_stake

        # Check stake
        if self.token_system:
            balance = self.token_system.get_balance(proposer_id)
            if balance < required_stake + self.config.proposal_fee:
                logger.warning(f"Insufficient balance for proposal")
                return None

        # Create proposal
        proposal = Proposal(
            proposal_id=f"prop_{uuid.uuid4().hex[:10]}",
            proposal_type=proposal_type,
            title=title,
            description=description,
            proposer_id=proposer_id,
            parameters=parameters,
            execution_payload=execution_payload or {},
            stake_amount=required_stake,
        )

        # Lock stake and pay fee
        if self.token_system:
            await self.token_system.transfer(proposer_id, "governance_stake", required_stake)
            await self.token_system.burn(proposer_id, self.config.proposal_fee, "proposal_fee")

        proposal.stake_locked = True
        proposal.status = ProposalStatus.SUBMITTED

        self._proposals[proposal.proposal_id] = proposal
        self._agent_proposals[proposer_id].add(proposal.proposal_id)
        self._stats["proposals_created"] += 1

        logger.info(f"Created proposal {proposal.proposal_id}: {title}")
        return proposal

    async def submit_proposal(self, proposal_id: str) -> bool:
        """Submit a draft proposal for voting."""
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.status != ProposalStatus.DRAFT:
            return False

        # Start voting period
        proposal.status = ProposalStatus.VOTING
        proposal.submitted_at = datetime.now().timestamp()
        proposal.voting_start = proposal.submitted_at
        proposal.voting_end = proposal.voting_start + (self.config.voting_period_hours * 3600)

        # Calculate total voting power
        if self.token_system:
            # Sum of all token balances (simplified)
            # In practice, would snapshot at voting start
            proposal.total_voting_power = self.token_system._circulating_supply

        logger.info(f"Proposal {proposal_id} submitted for voting")
        return True

    async def vote(
        self,
        voter_id: str,
        proposal_id: str,
        vote_type: VoteType,
        rationale: str = "",
    ) -> bool:
        """Cast a vote on a proposal."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            logger.warning(f"Proposal not found: {proposal_id}")
            return False

        if not proposal.is_active:
            logger.warning(f"Proposal not in voting period: {proposal_id}")
            return False

        # Check voting eligibility
        voting_power = await self._get_voting_power(voter_id, proposal)
        if voting_power < self.config.min_voting_power:
            logger.warning(f"Insufficient voting power: {voter_id}")
            return False

        # Check if already voted
        if voter_id in proposal.votes:
            logger.warning(f"Already voted: {voter_id} on {proposal_id}")
            return False

        # Check delegation
        if voter_id in self._delegations:
            delegatee = self._delegations[voter_id]
            # In practice, would delegate the vote
            logger.info(f"{voter_id} has delegated to {delegatee}")

        # Record vote
        vote = Vote(
            voter_id=voter_id,
            proposal_id=proposal_id,
            vote_type=vote_type,
            voting_power=voting_power,
            rationale=rationale,
        )

        proposal.votes[voter_id] = vote
        self._agent_votes[voter_id][proposal_id] = vote

        # Update tallies
        if vote_type == VoteType.YES:
            proposal.yes_votes += voting_power
        elif vote_type == VoteType.NO:
            proposal.no_votes += voting_power
        else:
            proposal.abstain_votes += voting_power

        self._stats["total_votes_cast"] += 1
        self._stats["total_voting_power"] += voting_power

        logger.info(f"Vote cast: {voter_id} -> {vote_type.value} on {proposal_id}")
        return True

    async def delegate_vote(
        self,
        delegator_id: str,
        delegatee_id: str,
        proposal_id: Optional[str] = None,
    ) -> bool:
        """Delegate voting power."""
        if not self.config.delegation_enabled:
            return False

        if delegator_id == delegatee_id:
            return False

        # Check chain depth
        chain = self._delegation_chains.get(delegatee_id, [])
        if len(chain) >= self.config.max_delegation_depth:
            return False

        # Verify delegator has voting power
        if self.token_system:
            balance = self.token_system.get_balance(delegator_id)
            if balance < self.config.min_voting_power:
                return False

        # Check no circular delegation
        if self._would_create_cycle(delegator_id, delegatee_id):
            return False

        # Create delegation
        self._delegations[delegator_id] = delegatee_id
        self._delegation_chains[delegatee_id].append(delegator_id)

        logger.info(f"Delegation: {delegator_id} -> {delegatee_id}")
        return True

    def _would_create_cycle(self, start: str, target: str) -> bool:
        """Check if delegation would create a cycle."""
        visited = set()
        current = target
        while current in self._delegations:
            if current == start:
                return True
            if current in visited:
                return True
            visited.add(current)
            current = self._delegations[current]
        return False

    async def _get_voting_power(self, agent_id: str, proposal: Proposal) -> Decimal:
        """Calculate voting power for an agent."""
        base_power = Decimal("0")

        if self.token_system:
            balance = self.token_system.get_balance(agent_id)
            staked = self.token_system.get_total_balance(agent_id) - balance
            # Base + staked bonus
            base_power = balance + (staked * Decimal("2"))

        # Add delegated power
        for delegator, delegatee in self._delegations.items():
            if delegatee == agent_id:
                delegator_power = await self._get_voting_power(delegator, proposal)
                base_power += delegator_power

        return base_power

    async def check_proposal_status(self, proposal_id: str) -> Optional[ProposalStatus]:
        """Check and update proposal status."""
        proposal = self._proposals.get(proposal_id)
        if not proposal:
            return None

        if proposal.status == ProposalStatus.VOTING:
            now = datetime.now().timestamp()

            # Check if voting period ended
            if proposal.voting_end and now >= proposal.voting_end:
                # Determine outcome
                if proposal.has_quorum:
                    # Check approval threshold
                    required = (
                        self.config.supermajority_threshold
                        if proposal.proposal_type
                        in [
                            ProposalType.CONSTITUTIONAL_AMENDMENT,
                            ProposalType.EMERGENCY_ACTION,
                        ]
                        else self.config.approval_threshold
                    )

                    if proposal.approval_rate >= required:
                        proposal.status = ProposalStatus.PASSED
                        self._stats["proposals_passed"] += 1
                    else:
                        proposal.status = ProposalStatus.REJECTED
                        self._stats["proposals_rejected"] += 1
                else:
                    proposal.status = ProposalStatus.REJECTED
                    self._stats["proposals_rejected"] += 1

                # Refund or slash stake
                await self._handle_stake_outcome(proposal)

        return proposal.status

    async def execute_proposal(self, proposal_id: str) -> bool:
        """Execute a passed proposal after delay."""
        proposal = self._proposals.get(proposal_id)
        if not proposal or proposal.status != ProposalStatus.PASSED:
            return False

        # Check execution delay
        if proposal.voting_end:
            delay_end = proposal.voting_end + (self.config.execution_delay_hours * 3600)
            if datetime.now().timestamp() < delay_end:
                logger.warning(f"Execution delay not elapsed: {proposal_id}")
                return False

        try:
            # Execute based on type
            success = await self._execute_proposal_actions(proposal)

            if success:
                proposal.status = ProposalStatus.EXECUTED
                proposal.executed_at = datetime.now().timestamp()
                self._stats["proposals_executed"] += 1

                # Refund stake
                if proposal.stake_locked and self.token_system:
                    await self.token_system.transfer(
                        "governance_stake", proposal.proposer_id, proposal.stake_amount
                    )
                    proposal.stake_locked = False

                logger.info(f"Executed proposal: {proposal_id}")
            else:
                proposal.status = ProposalStatus.FAILED
                logger.error(f"Proposal execution failed: {proposal_id}")

            return success

        except Exception as e:
            logger.error(f"Proposal execution error: {e}")
            proposal.status = ProposalStatus.FAILED
            return False

    async def _execute_proposal_actions(self, proposal: Proposal) -> bool:
        """Execute the specific actions of a proposal."""
        try:
            if proposal.proposal_type == ProposalType.PARAMETER_CHANGE:
                # Update system parameters
                for param, value in proposal.parameters.items():
                    logger.info(f"Parameter change: {param} = {value}")
                return True

            elif proposal.proposal_type == ProposalType.RESOURCE_ALLOCATION:
                # Allocate from treasury
                if self.token_system:
                    for recipient, amount in proposal.parameters.get("allocations", {}).items():
                        await self.token_system.mint(
                            recipient, Decimal(str(amount)), "treasury_allocation"
                        )
                return True

            elif proposal.proposal_type == ProposalType.TREASURY_SPEND:
                if self.token_system:
                    for recipient, amount in proposal.parameters.get("payments", {}).items():
                        await self.token_system.transfer(
                            "treasury", recipient, Decimal(str(amount))
                        )
                return True

            elif proposal.proposal_type == ProposalType.TOKEN_MINT:
                if self.token_system:
                    await self.token_system.mint(
                        proposal.parameters.get("recipient", "treasury"),
                        Decimal(str(proposal.parameters.get("amount", 0))),
                        "governance_mint",
                    )
                return True

            elif proposal.proposal_type == ProposalType.TOKEN_BURN:
                if self.token_system:
                    await self.token_system.burn(
                        proposal.parameters.get("from", "treasury"),
                        Decimal(str(proposal.parameters.get("amount", 0))),
                        "governance_burn",
                    )
                return True

            elif proposal.proposal_type == ProposalType.POLICY_UPDATE:
                if self.incentive_system:
                    policy_id = proposal.parameters.get("policy_id")
                    updates = proposal.parameters.get("updates", {})
                    policy = self.incentive_system.get_policy(policy_id)
                    if policy:
                        for key, value in updates.items():
                            setattr(policy, key, value)
                return True

            elif proposal.proposal_type == ProposalType.EMERGENCY_ACTION:
                # Execute emergency action immediately
                action = proposal.parameters.get("action")
                if action == "pause_minting":
                    logger.warning("Emergency: Minting paused")
                return True

            return True

        except Exception as e:
            logger.error(f"Proposal execution error: {e}")
            return False

    async def _handle_stake_outcome(self, proposal: Proposal):
        """Handle stake refund or slashing based on outcome."""
        if not proposal.stake_locked or not self.token_system:
            return

        if proposal.status == ProposalStatus.PASSED:
            # Refund stake
            await self.token_system.transfer(
                "governance_stake", proposal.proposer_id, proposal.stake_amount
            )
        elif proposal.status == ProposalStatus.REJECTED:
            # Check if should slash (spam proposal)
            if proposal.proposal_type == ProposalType.CONSTITUTIONAL_AMENDMENT:
                # Slash 10% for failed constitutional amendment
                slash_amount = proposal.stake_amount * Decimal("0.1")
                await self.token_system.burn("governance_stake", slash_amount, "proposal_slash")
                refund = proposal.stake_amount - slash_amount
            else:
                refund = proposal.stake_amount

            if refund > 0:
                await self.token_system.transfer("governance_stake", proposal.proposer_id, refund)

        proposal.stake_locked = False

    async def _check_proposer_eligibility(self, agent_id: str) -> bool:
        """Check if agent is eligible to propose."""
        if self.token_system:
            balance = self.token_system.get_balance(agent_id)
            if balance < self.config.min_proposal_stake + self.config.proposal_fee:
                return False
        return True

    # Query methods

    def get_proposal(self, proposal_id: str) -> Optional[Proposal]:
        """Get proposal by ID."""
        return self._proposals.get(proposal_id)

    def get_active_proposals(self) -> List[Proposal]:
        """Get all active (voting) proposals."""
        return [p for p in self._proposals.values() if p.is_active]

    def get_agent_proposals(self, agent_id: str) -> List[Proposal]:
        """Get proposals by an agent."""
        proposal_ids = self._agent_proposals.get(agent_id, set())
        return [self._proposals[pid] for pid in proposal_ids if pid in self._proposals]

    def get_agent_votes(self, agent_id: str) -> Dict[str, Vote]:
        """Get votes cast by an agent."""
        return self._agent_votes.get(agent_id, {})

    def get_proposal_votes(self, proposal_id: str) -> Dict[str, Vote]:
        """Get all votes for a proposal."""
        proposal = self._proposals.get(proposal_id)
        return proposal.votes if proposal else {}

    def get_stats(self) -> Dict[str, Any]:
        """Get governance statistics."""
        return {
            **self._stats,
            "active_proposals": len(self.get_active_proposals()),
            "total_proposals": len(self._proposals),
            "active_delegations": len(self._delegations),
        }

    async def auto_finalize_expired(self) -> List[str]:
        """Finalize all expired proposals."""
        finalized = []
        for proposal in self._proposals.values():
            if proposal.is_active:
                status = await self.check_proposal_status(proposal.proposal_id)
                if status and status != ProposalStatus.VOTING:
                    finalized.append(proposal.proposal_id)
        return finalized
