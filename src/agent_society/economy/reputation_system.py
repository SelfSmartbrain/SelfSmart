"""
Reputation System - Multi-dimensional reputation scoring for agents.

Provides comprehensive reputation tracking across multiple dimensions
with decay, validation, and social proof mechanisms.
"""

import logging
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from enum import Enum
from typing import Any, Dict, List, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class ReputationDimension(Enum):
    """Dimensions of agent reputation."""

    TECHNICAL_COMPETENCE = "technical_competence"  # Code quality, problem solving
    RELIABILITY = "reliability"  # Task completion, uptime
    COLLABORATION = "collaboration"  # Teamwork, communication
    INNOVATION = "innovation"  # Novel solutions, creativity
    SECURITY = "security"  # Secure practices, vulnerability handling
    MENTORSHIP = "mentorship"  # Teaching, helping others
    GOVERNANCE = "governance"  # Participation in decisions
    ECONOMIC_CONTRIBUTION = "economic_contribution"  # Value created, resources managed


@dataclass
class ReputationEvent:
    """Event that affects reputation."""

    event_id: str
    agent_id: str
    dimension: ReputationDimension
    delta: Decimal  # Positive or negative change
    weight: Decimal = Decimal("1.0")  # Event weight/importance
    source: str = "system"  # system, peer, oracle, self
    description: str = ""
    evidence: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    verified: bool = False
    verifier_id: Optional[str] = None

    def __post_init__(self):
        if not self.event_id:
            self.event_id = f"rep_{uuid.uuid4().hex[:12]}"


@dataclass
class ReputationProfile:
    """Complete reputation profile for an agent."""

    agent_id: str
    scores: Dict[ReputationDimension, Decimal] = field(default_factory=dict)
    events: List[ReputationEvent] = field(default_factory=list)
    peer_endorsements: Dict[str, Dict[ReputationDimension, Decimal]] = field(
        default_factory=dict
    )  # endorser -> dimension -> score
    last_updated: float = field(default_factory=lambda: datetime.now().timestamp())
    total_events: int = 0
    positive_events: int = 0
    negative_events: int = 0

    def __post_init__(self):
        # Initialize all dimensions to neutral if not set
        for dim in ReputationDimension:
            if dim not in self.scores:
                self.scores[dim] = Decimal("0.5")

    @property
    def overall_score(self) -> Decimal:
        """Calculate weighted overall reputation score."""
        if not self.scores:
            return Decimal("0.5")
        return sum(self.scores.values()) / Decimal(len(self.scores))

    @property
    def percentile(self) -> Decimal:
        """Approximate percentile (would need global comparison)."""
        # Simplified: map 0-1 to 0-100
        return min(Decimal("100"), max(Decimal("0"), self.overall_score * Decimal("100")))

    def get_dimension_score(self, dimension: ReputationDimension) -> Decimal:
        """Get score for specific dimension."""
        return self.scores.get(dimension, Decimal("0.5"))

    def get_dimension_percentile(self, dimension: ReputationDimension) -> Decimal:
        """Get percentile for specific dimension."""
        return min(
            Decimal("100"), max(Decimal("0"), self.get_dimension_score(dimension) * Decimal("100"))
        )


class ReputationSystem:
    """
    Multi-dimensional reputation system for agent society.

    Features:
    - Multiple reputation dimensions
    - Event-based scoring with weights
    - Peer endorsements and social proof
    - Time decay for old events
    - Verification and dispute resolution
    - Percentile rankings
    """

    def __init__(
        self,
        decay_rate: Decimal = Decimal("0.01"),  # 1% per period
        decay_period_days: int = 30,
        max_event_age_days: int = 365,
        min_weight: Decimal = Decimal("0.1"),
        endorsement_weight: Decimal = Decimal("0.3"),
        verification_bonus: Decimal = Decimal("0.2"),
    ):
        self.decay_rate = decay_rate
        self.decay_period = timedelta(days=decay_period_days)
        self.max_event_age = timedelta(days=max_event_age_days)
        self.min_weight = min_weight
        self.endorsement_weight = endorsement_weight
        self.verification_bonus = verification_bonus

        # Profiles
        self._profiles: Dict[str, ReputationProfile] = {}

        # Pending verifications
        self._pending_verifications: Dict[str, List[str]] = defaultdict(
            list
        )  # event_id -> verifier_ids

        # Statistics
        self._stats = {
            "total_events": 0,
            "verified_events": 0,
            "endorsements_given": 0,
            "profiles_created": 0,
        }

        logger.info("ReputationSystem initialized")

    def get_profile(self, agent_id: str) -> ReputationProfile:
        """Get or create reputation profile."""
        if agent_id not in self._profiles:
            self._profiles[agent_id] = ReputationProfile(agent_id=agent_id)
            self._stats["profiles_created"] += 1
        return self._profiles[agent_id]

    def record_event(
        self,
        agent_id: str,
        dimension: ReputationDimension,
        delta: Decimal,
        weight: Decimal = Decimal("1.0"),
        source: str = "system",
        description: str = "",
        evidence: Optional[Dict[str, Any]] = None,
    ) -> ReputationEvent:
        """Record a reputation event."""
        profile = self.get_profile(agent_id)

        event = ReputationEvent(
            event_id=f"rep_{uuid.uuid4().hex[:12]}",
            agent_id=agent_id,
            dimension=dimension,
            delta=delta,
            weight=max(weight, self.min_weight),
            source=source,
            description=description,
            evidence=evidence or {},
        )

        profile.events.append(event)
        profile.total_events += 1
        if delta > 0:
            profile.positive_events += 1
        else:
            profile.negative_events += 1

        # Apply immediately (will be decayed later)
        self._apply_event(profile, event)
        profile.last_updated = datetime.now().timestamp()

        self._stats["total_events"] += 1

        logger.debug(
            f"Reputation event: {agent_id} {dimension.value} {delta:+.3f} (weight: {weight})"
        )
        return event

    def _apply_event(self, profile: ReputationProfile, event: ReputationEvent):
        """Apply event to profile scores."""
        current = profile.scores.get(event.dimension, Decimal("0.5"))

        # Weighted update with bounds
        change = event.delta * event.weight
        new_score = max(Decimal("0"), min(Decimal("1"), current + change))
        profile.scores[event.dimension] = new_score

    def endorse(
        self,
        endorser_id: str,
        endorsee_id: str,
        dimension: ReputationDimension,
        score: Decimal,
        evidence: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Endorse another agent's reputation in a dimension."""
        if endorser_id == endorsee_id:
            logger.warning("Cannot endorse self")
            return False

        endorser_profile = self.get_profile(endorser_id)
        endorsee_profile = self.get_profile(endorsee_id)

        # Endorser must have decent reputation to endorse
        if endorser_profile.get_dimension_score(dimension) < Decimal("0.5"):
            logger.warning(
                f"Endorser {endorser_id} has insufficient reputation in {dimension.value}"
            )
            return False

        # Record endorsement
        if endorser_id not in endorsee_profile.peer_endorsements:
            endorsee_profile.peer_endorsements[endorser_id] = {}

        endorsee_profile.peer_endorsements[endorser_id][dimension] = score

        # Apply endorsement effect
        endorser_weight = endorser_profile.get_dimension_score(dimension) * self.endorsement_weight
        adjustment = (score - Decimal("0.5")) * endorser_weight

        current = endorsee_profile.scores.get(dimension, Decimal("0.5"))
        endorsee_profile.scores[dimension] = max(
            Decimal("0"), min(Decimal("1"), current + adjustment)
        )

        self._stats["endorsements_given"] += 1
        logger.debug(f"Endorsement: {endorser_id} -> {endorsee_id} {dimension.value}: {score}")
        return True

    def verify_event(self, event_id: str, verifier_id: str) -> bool:
        """Verify a reputation event."""
        # Find event
        event = None
        for profile in self._profiles.values():
            for e in profile.events:
                if e.event_id == event_id:
                    event = e
                    break
            if event:
                break

        if not event:
            logger.warning(f"Event not found: {event_id}")
            return False

        if event.verified:
            logger.warning(f"Event already verified: {event_id}")
            return False

        # Verifier must have good governance reputation
        verifier_profile = self.get_profile(verifier_id)
        if verifier_profile.get_dimension_score(ReputationDimension.GOVERNANCE) < Decimal("0.6"):
            logger.warning(f"Verifier {verifier_id} lacks governance reputation")
            return False

        event.verified = True
        event.verifier_id = verifier_id

        # Apply verification bonus
        profile = self.get_profile(event.agent_id)
        bonus = event.delta * self.verification_bonus
        profile.scores[event.dimension] = max(
            Decimal("0"),
            min(Decimal("1"), profile.scores.get(event.dimension, Decimal("0.5")) + bonus),
        )

        self._stats["verified_events"] += 1
        logger.info(f"Event verified: {event_id} by {verifier_id}")
        return True

    def apply_decay(self, agent_id: Optional[str] = None):
        """Apply time decay to reputation scores."""
        now = datetime.now()

        agents = [agent_id] if agent_id else list(self._profiles.keys())

        for aid in agents:
            profile = self.get_profile(aid)
            if not profile.events:
                continue

            # Remove old events
            cutoff = now - self.max_event_age
            profile.events = [
                e for e in profile.events if datetime.fromtimestamp(e.timestamp) > cutoff
            ]

            # Recalculate scores from remaining events
            self._recalculate_scores(profile)
            profile.last_updated = now.timestamp()

    def _recalculate_scores(self, profile: ReputationProfile):
        """Recalculate scores from events."""
        # Reset to neutral
        for dim in ReputationDimension:
            profile.scores[dim] = Decimal("0.5")

        # Reapply all events with decay
        now = datetime.now()
        for event in profile.events:
            age = now - datetime.fromtimestamp(event.timestamp)
            if age > self.decay_period:
                decay_factor = Decimal("1") - self.decay_rate * Decimal(
                    age.days / self.decay_period.days
                )
                decay_factor = max(Decimal("0"), decay_factor)
                adjusted_delta = event.delta * event.weight * decay_factor
            else:
                adjusted_delta = event.delta * event.weight

            current = profile.scores.get(event.dimension, Decimal("0.5"))
            profile.scores[event.dimension] = max(
                Decimal("0"), min(Decimal("1"), current + adjusted_delta)
            )

        # Reapply endorsements
        for endorser_id, endorsements in profile.peer_endorsements.items():
            endorser_profile = self.get_profile(endorser_id)
            for dimension, score in endorsements.items():
                endorser_weight = (
                    endorser_profile.get_dimension_score(dimension) * self.endorsement_weight
                )
                adjustment = (score - Decimal("0.5")) * endorser_weight
                current = profile.scores.get(dimension, Decimal("0.5"))
                profile.scores[dimension] = max(
                    Decimal("0"), min(Decimal("1"), current + adjustment)
                )

    def get_ranking(
        self,
        dimension: Optional[ReputationDimension] = None,
        limit: int = 100,
        min_events: int = 5,
    ) -> List[Tuple[str, Decimal]]:
        """Get reputation ranking."""
        ranked = []

        for agent_id, profile in self._profiles.items():
            if profile.total_events < min_events:
                continue

            if dimension:
                score = profile.get_dimension_score(dimension)
            else:
                score = profile.overall_score

            ranked.append((agent_id, score))

        ranked.sort(key=lambda x: x[1], reverse=True)
        return ranked[:limit]

    def get_percentile(
        self, agent_id: str, dimension: Optional[ReputationDimension] = None
    ) -> Decimal:
        """Get agent's percentile ranking."""
        rankings = self.get_ranking(dimension, limit=len(self._profiles), min_events=0)

        if not rankings:
            return Decimal("50")

        agent_rank = next((i for i, (aid, _) in enumerate(rankings) if aid == agent_id), -1)

        if agent_rank == -1:
            return Decimal("50")

        percentile = Decimal("100") * (Decimal(len(rankings) - agent_rank) / Decimal(len(rankings)))
        return percentile

    def get_leaderboard(
        self, dimension: Optional[ReputationDimension] = None, top_n: int = 10
    ) -> List[Dict[str, Any]]:
        """Get formatted leaderboard."""
        rankings = self.get_ranking(dimension, limit=top_n)

        leaderboard = []
        for rank, (agent_id, score) in enumerate(rankings, 1):
            profile = self._profiles[agent_id]
            leaderboard.append(
                {
                    "rank": rank,
                    "agent_id": agent_id,
                    "score": float(score),
                    "percentile": float(self.get_percentile(agent_id, dimension)),
                    "total_events": profile.total_events,
                    "verified": profile.positive_events > profile.negative_events,
                }
            )

        return leaderboard

    def get_stats(self) -> Dict[str, Any]:
        """Get system statistics."""
        return {
            **self._stats,
            "active_profiles": len([p for p in self._profiles.values() if p.total_events > 0]),
            "total_profiles": len(self._profiles),
        }

    def export_profile(self, agent_id: str) -> Optional[Dict[str, Any]]:
        """Export profile as dictionary."""
        profile = self._profiles.get(agent_id)
        if not profile:
            return None

        return {
            "agent_id": profile.agent_id,
            "overall_score": float(profile.overall_score),
            "dimension_scores": {dim.value: float(score) for dim, score in profile.scores.items()},
            "dimension_percentiles": {
                dim.value: float(profile.get_dimension_percentile(dim))
                for dim in ReputationDimension
            },
            "total_events": profile.total_events,
            "positive_events": profile.positive_events,
            "negative_events": profile.negative_events,
            "endorsement_count": sum(len(e) for e in profile.peer_endorsements.values()),
            "last_updated": profile.last_updated,
        }
