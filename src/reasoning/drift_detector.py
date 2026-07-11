"""
Environmental Drift Detector - Dynamic Re-Planning

Detects when the execution environment has diverged from the plan's
expected state, triggering re-planning.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import numpy as np

logger = logging.getLogger(__name__)


class DriftType(Enum):
    """Types of environmental drift"""
    STATE_DIVERGENCE = "state_divergence"
    RESOURCE_CHANGE = "resource_change"
    CONSTRAINT_VIOLATION = "constraint_violation"
    GOAL_OBSOLESCENCE = "goal_obsolescence"
    EXTERNAL_EVENT = "external_event"


@dataclass
class DriftSignal:
    """A detected drift signal"""
    drift_type: DriftType
    severity: float  # 0.0 to 1.0
    description: str
    affected_actions: List[str]
    detected_at: float = field(default_factory=lambda: datetime.now().timestamp())
    evidence: Dict[str, Any] = field(default_factory=dict)
    suggested_response: str = ""


@dataclass
class PlanSnapshot:
    """Snapshot of plan state at a point in time"""
    plan_id: str
    step_index: int
    expected_state: Dict[str, Any]
    actual_state: Dict[str, Any]
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


class EnvironmentalDriftDetector:
    """
    Detects drift between expected and actual execution state.
    
    Uses multiple detection strategies:
    - State comparison (embedding-based)
    - Resource monitoring
    - Constraint checking
    - Goal relevance validation
    """

    def __init__(
        self,
        memory_fabric: Any = None,
        llm_client: Any = None,
        embedding_model: Any = None,
        drift_threshold: float = 0.3,
        check_interval: int = 30,
    ):
        self.memory = memory_fabric
        self.llm = llm_client
        self.embedding_model = embedding_model
        self.drift_threshold = drift_threshold
        self.check_interval = check_interval

        self._plan_snapshots: Dict[str, List[PlanSnapshot]] = {}
        self._baseline_states: Dict[str, Dict[str, Any]] = {}
        self._drift_history: List[DriftSignal] = []
        self._monitors: Dict[str, asyncio.Task] = {}

    async def initialize(self) -> None:
        """Initialize drift detector"""
        logger.info("EnvironmentalDriftDetector initialized")

    async def register_plan(
        self,
        plan_id: str,
        expected_states: List[Dict[str, Any]],
        baseline_state: Dict[str, Any],
    ) -> None:
        """
        Register a plan for drift monitoring.
        
        Args:
            plan_id: Plan identifier
            expected_states: Expected state at each step
            baseline_state: Initial state before execution
        """
        self._baseline_states[plan_id] = baseline_state
        self._plan_snapshots[plan_id] = []
        
        # Store expected states for comparison
        for i, state in enumerate(expected_states):
            snapshot = PlanSnapshot(
                plan_id=plan_id,
                step_index=i,
                expected_state=state,
                actual_state={},
            )
            self._plan_snapshots[plan_id].append(snapshot)
        
        logger.info(f"Registered plan {plan_id} for drift monitoring ({len(expected_states)} steps)")

    async def record_actual_state(
        self,
        plan_id: str,
        step_index: int,
        actual_state: Dict[str, Any],
    ) -> None:
        """Record actual observed state at a plan step"""
        if plan_id not in self._plan_snapshots:
            return
        
        snapshots = self._plan_snapshots[plan_id]
        if step_index < len(snapshots):
            snapshots[step_index].actual_state = actual_state
            snapshots[step_index].timestamp = datetime.now().timestamp()

    async def check_drift(
        self,
        plan_id: str,
        current_step: int,
        current_state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[DriftSignal]:
        """
        Check for drift at current execution point.
        
        Args:
            plan_id: Plan identifier
            current_step: Current step index
            current_state: Currently observed state
            context: Additional context (resources, constraints, goals)
            
        Returns:
            List of detected drift signals
        """
        signals = []
        
        # 1. State divergence check
        state_signals = await self._check_state_divergence(plan_id, current_step, current_state)
        signals.extend(state_signals)
        
        # 2. Resource change check
        resource_signals = await self._check_resource_changes(plan_id, current_state, context)
        signals.extend(resource_signals)
        
        # 3. Constraint violation check
        constraint_signals = await self._check_constraint_violations(plan_id, current_state, context)
        signals.extend(constraint_signals)
        
        # 4. Goal obsolescence check
        goal_signals = await self._check_goal_obsolescence(plan_id, current_state, context)
        signals.extend(goal_signals)
        
        # Record and return significant signals
        significant = [s for s in signals if s.severity >= self.drift_threshold]
        self._drift_history.extend(significant)
        
        if significant:
            logger.warning(f"Drift detected for plan {plan_id}: {len(significant)} signals")
            for s in significant:
                logger.warning(f"  - {s.drift_type.value}: {s.description} (severity: {s.severity:.2f})")
        
        return significant

    async def _check_state_divergence(
        self,
        plan_id: str,
        current_step: int,
        current_state: Dict[str, Any],
    ) -> List[DriftSignal]:
        """Check if actual state diverges from expected"""
        signals = []
        
        if plan_id not in self._plan_snapshots:
            return signals
        
        snapshots = self._plan_snapshots[plan_id]
        if current_step >= len(snapshots):
            return signals
        
        expected = snapshots[current_step].expected_state
        
        # Compare states using embeddings
        expected_emb = await self._get_state_embedding(expected)
        actual_emb = await self._get_state_embedding(current_state)
        
        if expected_emb is not None and actual_emb is not None:
            similarity = self._cosine_similarity(expected_emb, actual_emb)
            divergence = 1.0 - similarity
            
            if divergence > self.drift_threshold:
                # Identify which aspects diverged
                affected = self._identify_diverged_keys(expected, current_state)
                
                signals.append(DriftSignal(
                    drift_type=DriftType.STATE_DIVERGENCE,
                    severity=divergence,
                    description=f"State divergence at step {current_step}: expected vs actual similarity {similarity:.2f}",
                    affected_actions=affected,
                    evidence={
                        "expected_keys": list(expected.keys()),
                        "actual_keys": list(current_state.keys()),
                        "similarity": similarity,
                    },
                    suggested_response="Re-plan from current step with updated state",
                ))
        
        return signals

    async def _check_resource_changes(
        self,
        plan_id: str,
        current_state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[DriftSignal]:
        """Check for resource availability changes"""
        signals = []
        
        baseline = self._baseline_states.get(plan_id, {})
        expected_resources = baseline.get("resources", {})
        current_resources = context.get("resources", {})
        
        for resource, expected_amount in expected_resources.items():
            current_amount = current_resources.get(resource, 0)
            if current_amount < expected_amount * 0.5:  # Less than 50% expected
                severity = 1.0 - (current_amount / expected_amount) if expected_amount > 0 else 1.0
                
                signals.append(DriftSignal(
                    drift_type=DriftType.RESOURCE_CHANGE,
                    severity=min(severity, 1.0),
                    description=f"Resource {resource} depleted: {current_amount}/{expected_amount}",
                    affected_actions=context.get("resource_dependent_actions", []),
                    evidence={
                        "resource": resource,
                        "expected": expected_amount,
                        "actual": current_amount,
                    },
                    suggested_response="Adjust plan for resource constraints or acquire resources",
                ))
        
        return signals

    async def _check_constraint_violations(
        self,
        plan_id: str,
        current_state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[DriftSignal]:
        """Check for constraint violations"""
        signals = []
        
        constraints = context.get("constraints", [])
        for constraint in constraints:
            # Constraint format: {"type": "max_time", "limit": 3600, "current": 4000}
            c_type = constraint.get("type")
            limit = constraint.get("limit")
            current = constraint.get("current")
            
            if c_type == "max_time" and current and current > limit:
                severity = min((current - limit) / limit, 1.0)
                signals.append(DriftSignal(
                    drift_type=DriftType.CONSTRAINT_VIOLATION,
                    severity=severity,
                    description=f"Time constraint violated: {current}s > {limit}s limit",
                    affected_actions=context.get("time_sensitive_actions", []),
                    evidence=constraint,
                    suggested_response="Re-prioritize or parallelize remaining actions",
                ))
            elif c_type == "budget" and current and current > limit:
                severity = min((current - limit) / limit, 1.0)
                signals.append(DriftSignal(
                    drift_type=DriftType.CONSTRAINT_VIOLATION,
                    severity=severity,
                    description=f"Budget constraint violated: {current} > {limit}",
                    affected_actions=context.get("costly_actions", []),
                    evidence=constraint,
                    suggested_response="Reduce scope or find cost-effective alternatives",
                ))
        
        return signals

    async def _check_goal_obsolescence(
        self,
        plan_id: str,
        current_state: Dict[str, Any],
        context: Dict[str, Any],
    ) -> List[DriftSignal]:
        """Check if original goal is still relevant"""
        signals = []
        
        goal = context.get("goal", "")
        if not goal or not self.llm:
            return signals
        
        # Ask LLM if goal is still relevant given current state
        prompt = f"""Given the original goal and current state, is the goal still relevant and achievable?

Original Goal: {goal}
Current State: {current_state}
Context: {context}

Respond with: RELEVANT | PARTIALLY_RELEVANT | OBSOLETE
And brief reasoning:"""
        
        try:
            response = await self.llm.ainvoke(prompt)
            content = response.content if hasattr(response, 'content') else str(response)
            
            if "OBSOLETE" in content.upper():
                signals.append(DriftSignal(
                    drift_type=DriftType.GOAL_OBSOLESCENCE,
                    severity=0.9,
                    description="Original goal appears obsolete given current state",
                    affected_actions=list(context.get("remaining_actions", [])),
                    evidence={"llm_assessment": content},
                    suggested_response="Re-define goal and create new plan",
                ))
            elif "PARTIALLY_RELEVANT" in content.upper():
                signals.append(DriftSignal(
                    drift_type=DriftType.GOAL_OBSOLESCENCE,
                    severity=0.5,
                    description="Goal partially relevant - scope may need adjustment",
                    affected_actions=list(context.get("remaining_actions", [])),
                    evidence={"llm_assessment": content},
                    suggested_response="Adjust goal scope and re-plan",
                ))
        except Exception as e:
            logger.error(f"Goal relevance check failed: {e}")
        
        return signals

    async def _get_state_embedding(self, state: Dict[str, Any]) -> Optional[List[float]]:
        """Generate embedding for state dictionary"""
        if not state:
            return None
        
        # Serialize state to text
        state_text = self._serialize_state(state)
        
        if self.embedding_model:
            return await self.embedding_model.embed(state_text)
        
        # Fallback: hash-based embedding
        return self._hash_embedding(state_text)

    def _serialize_state(self, state: Dict[str, Any]) -> str:
        """Serialize state dict to text for embedding"""
        parts = []
        for key, value in sorted(state.items()):
            if isinstance(value, (str, int, float, bool)):
                parts.append(f"{key}: {value}")
            elif isinstance(value, (list, dict)):
                parts.append(f"{key}: {str(value)[:200]}")
        return " | ".join(parts)

    def _hash_embedding(self, text: str, dim: int = 1536) -> List[float]:
        """Generate deterministic pseudo-embedding"""
        import hashlib
        hash_bytes = hashlib.sha256(text.encode()).digest()
        return [(hash_bytes[i % len(hash_bytes)] - 128) / 128.0 for i in range(dim)]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity"""
        a_np = np.array(a)
        b_np = np.array(b)
        norm_a = np.linalg.norm(a_np)
        norm_b = np.linalg.norm(b_np)
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return float(np.dot(a_np, b_np) / (norm_a * norm_b))

    def _identify_diverged_keys(
        self,
        expected: Dict[str, Any],
        actual: Dict[str, Any],
    ) -> List[str]:
        """Identify which state keys have significant divergence"""
        diverged = []
        all_keys = set(expected.keys()) | set(actual.keys())
        
        for key in all_keys:
            exp_val = expected.get(key)
            act_val = actual.get(key)
            
            if exp_val is None or act_val is None:
                diverged.append(key)
            elif isinstance(exp_val, (int, float)) and isinstance(act_val, (int, float)):
                if exp_val != 0:
                    diff = abs(exp_val - act_val) / abs(exp_val)
                    if diff > 0.3:
                        diverged.append(key)
                elif act_val != 0:
                    diverged.append(key)
            elif exp_val != act_val:
                diverged.append(key)
        
        return diverged

    async def start_monitoring(
        self,
        plan_id: str,
        get_state_func: callable,
        get_context_func: callable,
    ) -> None:
        """Start continuous drift monitoring for a plan"""
        if plan_id in self._monitors:
            return
        
        async def monitor_loop():
            step = 0
            while plan_id in self._monitors:
                try:
                    current_state = await get_state_func()
                    context = await get_context_func()
                    
                    await self.check_drift(plan_id, step, current_state, context)
                    step += 1
                    
                except Exception as e:
                    logger.error(f"Drift monitoring error for {plan_id}: {e}")
                
                await asyncio.sleep(self.check_interval)
        
        self._monitors[plan_id] = asyncio.create_task(monitor_loop())
        logger.info(f"Started drift monitoring for plan {plan_id}")

    async def stop_monitoring(self, plan_id: str) -> None:
        """Stop drift monitoring for a plan"""
        if plan_id in self._monitors:
            self._monitors[plan_id].cancel()
            try:
                await self._monitors[plan_id]
            except asyncio.CancelledError:
                pass
            del self._monitors[plan_id]
            logger.info(f"Stopped drift monitoring for plan {plan_id}")

    def get_drift_history(self, plan_id: Optional[str] = None) -> List[DriftSignal]:
        """Get drift detection history"""
        if plan_id:
            return [d for d in self._drift_history if d.evidence.get("plan_id") == plan_id]
        return self._drift_history