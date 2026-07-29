"""
Incentive System - Reward mechanisms and incentive policies for agents.

Provides configurable incentive structures for motivating desired
behaviors in the agent society.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class RewardType(Enum):
    """Types of rewards."""

    TASK_COMPLETION = "task_completion"
    QUALITY_BONUS = "quality_bonus"
    INNOVATION_BONUS = "innovation_bonus"
    COLLABORATION_BONUS = "collaboration_bonus"
    MENTORSHIP_REWARD = "mentorship_reward"
    GOVERNANCE_PARTICIPATION = "governance_participation"
    BUG_BOUNTY = "bug_bounty"
    SECURITY_AUDIT = "security_audit"
    DOCUMENTATION = "documentation"
    REFERRAL = "referral"
    STREAK_BONUS = "streak_bonus"
    MILESTONE = "milestone"


class IncentiveTrigger(Enum):
    """Triggers for incentive evaluation."""

    ON_TASK_COMPLETE = "on_task_complete"
    ON_MILESTONE = "on_milestone"
    PERIODIC = "periodic"
    ON_DEMAND = "on_demand"
    ON_FEEDBACK = "on_feedback"
    ON_PEER_REVIEW = "on_peer_review"


@dataclass
class IncentiveConfig:
    """Configuration for incentive system."""

    base_task_reward: Decimal = Decimal("10.0")
    quality_multiplier: Decimal = Decimal("1.5")
    innovation_multiplier: Decimal = Decimal("2.0")
    collaboration_multiplier: Decimal = Decimal("1.3")
    mentorship_rate: Decimal = Decimal("5.0")
    governance_rate: Decimal = Decimal("3.0")
    bug_bounty_rate: Decimal = Decimal("50.0")
    security_audit_rate: Decimal = Decimal("100.0")
    documentation_rate: Decimal = Decimal("2.0")
    referral_bonus: Decimal = Decimal("20.0")
    streak_bonus_per_day: Decimal = Decimal("1.0")
    max_streak_bonus: Decimal = Decimal("100.0")
    milestone_rewards: Dict[int, Decimal] = field(
        default_factory=lambda: {
            10: Decimal("50"),
            50: Decimal("200"),
            100: Decimal("500"),
            500: Decimal("2000"),
            1000: Decimal("5000"),
        }
    )


@dataclass
class IncentivePolicy:
    """Policy defining when and how incentives are awarded."""

    policy_id: str
    name: str
    description: str
    reward_type: RewardType
    trigger: IncentiveTrigger
    conditions: Dict[str, Any] = field(default_factory=dict)  # e.g., {"min_quality": 0.8}
    reward_formula: str = "base"  # base, scaled, tiered
    cooldown_hours: int = 24
    max_per_period: int = 10
    enabled: bool = True
    priority: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Reward:
    """An awarded reward."""

    reward_id: str
    agent_id: str
    policy_id: str
    reward_type: RewardType
    amount: Decimal
    trigger_event: str
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)
    status: str = "pending"  # pending, confirmed, paid, revoked

    def __post_init__(self):
        if not self.reward_id:
            self.reward_id = f"rew_{uuid.uuid4().hex[:10]}"


class IncentiveSystem:
    """
    Configurable incentive system for agent motivation.

    Features:
    - Policy-based reward rules
    - Multiple reward types and triggers
    - Quality and innovation bonuses
    - Streak and milestone rewards
    - Cooldown and rate limiting
    - Integration with token system
    """

    def __init__(
        self,
        config: Optional[IncentiveConfig] = None,
        token_system=None,
        reputation_system=None,
    ):
        self.config = config or IncentiveConfig()
        self.token_system = token_system
        self.reputation_system = reputation_system

        # Policies
        self._policies: Dict[str, IncentivePolicy] = {}

        # Reward history
        self._rewards: List[Reward] = []
        self._agent_rewards: Dict[str, List[Reward]] = defaultdict(list)

        # Tracking
        self._task_streaks: Dict[str, int] = defaultdict(int)  # agent_id -> streak
        self._task_counts: Dict[str, int] = defaultdict(int)  # agent_id -> count
        self._last_reward_time: Dict[str, float] = defaultdict(
            float
        )  # agent_id+policy_id -> timestamp

        # Statistics
        self._stats = {
            "total_rewards": 0,
            "total_amount": Decimal("0"),
            "by_type": defaultdict(int),
            "by_policy": defaultdict(int),
        }

        # Initialize default policies
        self._initialize_default_policies()

        logger.info("IncentiveSystem initialized")

    def _initialize_default_policies(self):
        """Create default incentive policies."""
        policies = [
            IncentivePolicy(
                policy_id="task_completion",
                name="Task Completion Reward",
                description="Base reward for completing tasks",
                reward_type=RewardType.TASK_COMPLETION,
                trigger=IncentiveTrigger.ON_TASK_COMPLETE,
                reward_formula="base",
            ),
            IncentivePolicy(
                policy_id="quality_bonus",
                name="Quality Bonus",
                description="Bonus for high-quality task completion",
                reward_type=RewardType.QUALITY_BONUS,
                trigger=IncentiveTrigger.ON_TASK_COMPLETE,
                conditions={"min_quality": Decimal("0.8")},
                reward_formula="multiplied",
            ),
            IncentivePolicy(
                policy_id="innovation_bonus",
                name="Innovation Bonus",
                description="Bonus for novel solutions",
                reward_type=RewardType.INNOVATION_BONUS,
                trigger=IncentiveTrigger.ON_FEEDBACK,
                conditions={"innovation_score": Decimal("0.7")},
                reward_formula="multiplied",
            ),
            IncentivePolicy(
                policy_id="collaboration_bonus",
                name="Collaboration Bonus",
                description="Bonus for multi-agent collaboration",
                reward_type=RewardType.COLLABORATION_BONUS,
                trigger=IncentiveTrigger.ON_TASK_COMPLETE,
                conditions={"min_participants": 2},
                reward_formula="multiplied",
            ),
            IncentivePolicy(
                policy_id="mentorship_reward",
                name="Mentorship Reward",
                description="Reward for mentoring other agents",
                reward_type=RewardType.MENTORSHIP_REWARD,
                trigger=IncentiveTrigger.ON_FEEDBACK,
                conditions={"mentorship_rating": Decimal("0.7")},
                reward_formula="fixed",
            ),
            IncentivePolicy(
                policy_id="governance_participation",
                name="Governance Participation",
                description="Reward for participating in governance",
                reward_type=RewardType.GOVERNANCE_PARTICIPATION,
                trigger=IncentiveTrigger.ON_DEMAND,
                reward_formula="fixed",
            ),
            IncentivePolicy(
                policy_id="streak_bonus",
                name="Streak Bonus",
                description="Daily streak bonus for consistent participation",
                reward_type=RewardType.STREAK_BONUS,
                trigger=IncentiveTrigger.PERIODIC,
                reward_formula="streak",
            ),
            IncentivePolicy(
                policy_id="milestone_rewards",
                name="Milestone Rewards",
                description="Rewards for task completion milestones",
                reward_type=RewardType.MILESTONE,
                trigger=IncentiveTrigger.ON_MILESTONE,
                reward_formula="tiered",
            ),
        ]

        for policy in policies:
            self.add_policy(policy)

    def add_policy(self, policy: IncentivePolicy) -> bool:
        """Add an incentive policy."""
        if policy.policy_id in self._policies:
            logger.warning(f"Policy already exists: {policy.policy_id}")
            return False

        self._policies[policy.policy_id] = policy
        logger.info(f"Added incentive policy: {policy.policy_id} ({policy.name})")
        return True

    def remove_policy(self, policy_id: str) -> bool:
        """Remove an incentive policy."""
        if policy_id not in self._policies:
            return False

        del self._policies[policy_id]
        logger.info(f"Removed incentive policy: {policy_id}")
        return True

    def get_policy(self, policy_id: str) -> Optional[IncentivePolicy]:
        """Get policy by ID."""
        return self._policies.get(policy_id)

    async def evaluate_task_completion(
        self,
        agent_id: str,
        task_data: Dict[str, Any],
        quality_score: Decimal = Decimal("0.5"),
        innovation_score: Decimal = Decimal("0.0"),
        collaboration_data: Optional[Dict[str, Any]] = None,
    ) -> List[Reward]:
        """Evaluate and award rewards for task completion."""
        rewards = []

        # Update task count and streak
        self._task_counts[agent_id] += 1
        self._update_streak(agent_id)

        # Base task completion reward
        reward = await self._evaluate_policy(
            "task_completion",
            agent_id,
            {
                "base_amount": self.config.base_task_reward,
            },
            f"task_{uuid.uuid4().hex[:8]}",
        )
        if reward:
            rewards.append(reward)

        # Quality bonus
        if quality_score >= Decimal("0.8"):
            reward = await self._evaluate_policy(
                "quality_bonus",
                agent_id,
                {
                    "base_amount": self.config.base_task_reward,
                    "multiplier": self.config.quality_multiplier,
                    "quality_score": quality_score,
                },
                f"task_quality",
            )
            if reward:
                rewards.append(reward)

        # Innovation bonus
        if innovation_score >= Decimal("0.7"):
            reward = await self._evaluate_policy(
                "innovation_bonus",
                agent_id,
                {
                    "base_amount": self.config.base_task_reward,
                    "multiplier": self.config.innovation_multiplier,
                    "innovation_score": innovation_score,
                },
                f"task_innovation",
            )
            if reward:
                rewards.append(reward)

        # Collaboration bonus
        if collaboration_data and collaboration_data.get("participant_count", 1) >= 2:
            reward = await self._evaluate_policy(
                "collaboration_bonus",
                agent_id,
                {
                    "base_amount": self.config.base_task_reward,
                    "multiplier": self.config.collaboration_multiplier,
                    "participants": collaboration_data.get("participant_count", 2),
                },
                f"task_collab",
            )
            if reward:
                rewards.append(reward)

        # Milestone check
        milestone_rewards = await self._check_milestones(agent_id)
        rewards.extend(milestone_rewards)

        return rewards

    async def evaluate_periodic(self, agent_id: str) -> List[Reward]:
        """Evaluate periodic rewards (streaks, etc.)."""
        rewards = []

        # Streak bonus
        streak = self._task_streaks.get(agent_id, 0)
        if streak > 0:
            reward = await self._evaluate_policy(
                "streak_bonus",
                agent_id,
                {
                    "streak": streak,
                    "per_day": self.config.streak_bonus_per_day,
                    "max_bonus": self.config.max_streak_bonus,
                },
                f"streak_{streak}",
            )
            if reward:
                rewards.append(reward)

        return rewards

    async def award_manual(
        self,
        agent_id: str,
        policy_id: str,
        amount: Decimal,
        trigger_event: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Reward]:
        """Manually award a reward."""
        policy = self._policies.get(policy_id)
        if not policy or not policy.enabled:
            return None

        return await self._create_reward(
            agent_id=agent_id,
            policy=policy,
            amount=amount,
            trigger_event=trigger_event,
            metadata=metadata,
        )

    async def _evaluate_policy(
        self,
        policy_id: str,
        agent_id: str,
        context: Dict[str, Any],
        trigger_event: str,
    ) -> Optional[Reward]:
        """Evaluate a specific policy for an agent."""
        policy = self._policies.get(policy_id)
        if not policy or not policy.enabled:
            return None

        # Check cooldown
        cooldown_key = f"{agent_id}:{policy_id}"
        last_time = self._last_reward_time.get(cooldown_key, 0)
        if datetime.now().timestamp() - last_time < policy.cooldown_hours * 3600:
            return None

        # Check max per period
        recent_rewards = [
            r
            for r in self._agent_rewards[agent_id]
            if r.policy_id == policy_id
            and datetime.now().timestamp() - r.timestamp < 86400  # last 24h
        ]
        if len(recent_rewards) >= policy.max_per_period:
            return None

        # Check conditions
        if not self._check_conditions(policy.conditions, context, agent_id):
            return None

        # Calculate reward amount
        amount = self._calculate_reward(policy, context)
        if amount <= 0:
            return None

        # Create reward
        reward = await self._create_reward(
            agent_id=agent_id,
            policy=policy,
            amount=amount,
            trigger_event=trigger_event,
            metadata=context,
        )

        if reward:
            self._last_reward_time[cooldown_key] = datetime.now().timestamp()

        return reward

    def _check_conditions(
        self,
        conditions: Dict[str, Any],
        context: Dict[str, Any],
        agent_id: str,
    ) -> bool:
        """Check if policy conditions are met."""
        for key, required_value in conditions.items():
            if key not in context:
                return False
            actual_value = context[key]
            if isinstance(required_value, (int, float, Decimal)):
                if actual_value < required_value:
                    return False
            elif actual_value != required_value:
                return False
        return True

    def _calculate_reward(self, policy: IncentivePolicy, context: Dict[str, Any]) -> Decimal:
        """Calculate reward amount based on policy formula."""
        if policy.reward_formula == "base":
            return context.get("base_amount", Decimal("0"))

        elif policy.reward_formula == "multiplied":
            base = context.get("base_amount", Decimal("0"))
            multiplier = context.get("multiplier", Decimal("1"))
            return base * multiplier

        elif policy.reward_formula == "fixed":
            if policy.reward_type == RewardType.MENTORSHIP_REWARD:
                return self.config.mentorship_rate
            elif policy.reward_type == RewardType.GOVERNANCE_PARTICIPATION:
                return self.config.governance_rate
            return Decimal("0")

        elif policy.reward_formula == "streak":
            streak = context.get("streak", 0)
            per_day = context.get("per_day", self.config.streak_bonus_per_day)
            max_bonus = context.get("max_bonus", self.config.max_streak_bonus)
            return min(Decimal(str(streak)) * per_day, max_bonus)

        elif policy.reward_formula == "tiered":
            # Handled in _check_milestones
            return Decimal("0")

        return Decimal("0")

    def _check_conditions(
        self,
        conditions: Dict[str, Any],
        context: Dict[str, Any],
        agent_id: str,
    ) -> bool:
        """Check if all conditions are satisfied."""
        for key, required in conditions.items():
            if key not in context:
                return False

            actual = context[key]
            if isinstance(required, (int, float, Decimal)):
                if Decimal(str(actual)) < Decimal(str(required)):
                    return False
            elif actual != required:
                return False
        return True

    def _update_streak(self, agent_id: str):
        """Update task completion streak."""
        now = datetime.now()
        today = now.date()

        # Get last task date from rewards
        last_task_date = None
        for reward in self._agent_rewards[agent_id]:
            if reward.reward_type == RewardType.TASK_COMPLETION:
                reward_date = datetime.fromtimestamp(reward.timestamp).date()
                if last_task_date is None or reward_date > last_task_date:
                    last_task_date = reward_date

        if last_task_date:
            if today == last_task_date:
                return  # Already counted today
            elif today == last_task_date + timedelta(days=1):
                self._task_streaks[agent_id] += 1
            else:
                self._task_streaks[agent_id] = 1
        else:
            self._task_streaks[agent_id] = 1

    async def _check_milestones(self, agent_id: str) -> List[Reward]:
        """Check and award milestone rewards."""
        rewards = []
        task_count = self._task_counts[agent_id]

        for milestone, reward_amount in self.config.milestone_rewards.items():
            if task_count == milestone:
                reward = await self._create_reward(
                    agent_id=agent_id,
                    policy=self._policies["milestone_rewards"],
                    amount=reward_amount,
                    trigger_event=f"milestone_{milestone}",
                    metadata={"milestone": milestone, "task_count": task_count},
                )
                if reward:
                    rewards.append(reward)

        return rewards

    async def _create_reward(
        self,
        agent_id: str,
        policy: IncentivePolicy,
        amount: Decimal,
        trigger_event: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Reward:
        """Create and record a reward."""
        reward = Reward(
            reward_id=f"rew_{uuid.uuid4().hex[:10]}",
            agent_id=agent_id,
            policy_id=policy.policy_id,
            reward_type=policy.reward_type,
            amount=amount,
            trigger_event=trigger_event,
            metadata=metadata or {},
        )

        self._rewards.append(reward)
        self._agent_rewards[agent_id].append(reward)

        self._stats["total_rewards"] += 1
        self._stats["total_amount"] += amount
        self._stats["by_type"][policy.reward_type.value] += 1
        self._stats["by_policy"][policy.policy_id] += 1

        # Pay out if token system available
        if self.token_system:
            try:
                await self.token_system.reward(agent_id, amount, trigger_event)
            except Exception as e:
                logger.error(f"Failed to pay reward: {e}")

        # Update reputation if available
        if self.reputation_system and policy.reward_type in [
            RewardType.QUALITY_BONUS,
            RewardType.INNOVATION_BONUS,
            RewardType.COLLABORATION_BONUS,
            RewardType.MENTORSHIP_REWARD,
        ]:
            try:
                self.reputation_system.record_event(
                    agent_id=agent_id,
                    dimension=RewardType.ECONOMIC_CONTRIBUTION,
                    delta=amount / Decimal("100"),  # Scale
                    source="incentive",
                    description=f"Reward: {policy.name}",
                )
            except Exception as e:
                logger.error(f"Failed to update reputation: {e}")

        logger.info(f"Awarded {amount} to {agent_id} for {policy.name}")
        return reward

    def get_agent_rewards(
        self,
        agent_id: str,
        policy_id: Optional[str] = None,
        limit: int = 100,
    ) -> List[Reward]:
        """Get rewards for an agent."""
        rewards = self._agent_rewards.get(agent_id, [])

        if policy_id:
            rewards = [r for r in rewards if r.policy_id == policy_id]

        return rewards[-limit:]

    def get_agent_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get incentive statistics for an agent."""
        rewards = self._agent_rewards.get(agent_id, [])

        by_type = defaultdict(int)
        by_policy = defaultdict(int)
        total = Decimal("0")

        for r in rewards:
            by_type[r.reward_type.value] += 1
            by_policy[r.policy_id] += 1
            total += r.amount

        return {
            "total_rewards": len(rewards),
            "total_amount": total,
            "by_type": dict(by_type),
            "by_policy": dict(by_policy),
            "task_count": self._task_counts.get(agent_id, 0),
            "current_streak": self._task_streaks.get(agent_id, 0),
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        return {
            **self._stats,
            "total_rewards": self._stats["total_rewards"],
            "total_amount": float(self._stats["total_amount"]),
            "active_policies": len([p for p in self._policies.values() if p.enabled]),
            "total_policies": len(self._policies),
        }
