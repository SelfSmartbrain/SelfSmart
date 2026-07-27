"""
Background Thinker - Autonomous cognitive processing during idle periods.

When the agent has no active objectives, the background thinker explores
the knowledge graph, reflects on memories, generates insights, and
prepares for future tasks.
"""

import asyncio
import logging
import random
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from enum import Enum

from src.cognitive_kernel.kernel import CognitiveKernel
from src.memory.memory_fabric import MemoryFabric, MemoryType

logger = logging.getLogger(__name__)


class ThinkingMode(Enum):
    """Modes of background thinking."""

    EXPLORATION = "exploration"  # Explore knowledge graph
    REFLECTION = "reflection"  # Reflect on past experiences
    SYNTHESIS = "synthesis"  # Synthesize new connections
    PLANNING = "planning"  # Plan for future goals
    CURIOSITY = "curiosity"  # Follow curiosity threads
    CONSOLIDATION = "consolidation"  # Consolidate learning


@dataclass
class ThinkingConfig:
    """Configuration for background thinking."""

    interval: float = 60.0  # Seconds between thinking sessions
    idle_threshold: float = 30.0  # Seconds of idle before thinking
    max_thought_duration: float = 30.0  # Max seconds per thought session

    # Mode weights (probability of each mode)
    mode_weights: Dict[ThinkingMode, float] = field(
        default_factory=lambda: {
            ThinkingMode.EXPLORATION: 0.25,
            ThinkingMode.REFLECTION: 0.20,
            ThinkingMode.SYNTHESIS: 0.20,
            ThinkingMode.PLANNING: 0.15,
            ThinkingMode.CURIOSITY: 0.10,
            ThinkingMode.CONSOLIDATION: 0.10,
        }
    )

    # Exploration params
    exploration_depth: int = 3
    max_concepts_per_session: int = 10

    # Reflection params
    reflection_lookback_hours: int = 24
    min_reflection_confidence: float = 0.6

    # Curiosity
    curiosity_topics: List[str] = field(
        default_factory=lambda: ["causality", "patterns", "anomalies", "optimization", "emergence"]
    )

    # Output
    store_insights: bool = True
    insight_importance_threshold: float = 0.5


@dataclass
class ThoughtResult:
    """Result of a background thinking session."""

    mode: ThinkingMode
    started_at: datetime
    completed_at: datetime
    insights: List[Dict[str, Any]] = field(default_factory=list)
    concepts_explored: List[str] = field(default_factory=list)
    connections_made: int = 0
    memories_reviewed: int = 0
    new_questions: List[str] = field(default_factory=list)
    success: bool = True
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "mode": self.mode.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "insights": self.insights,
            "concepts_explored": self.concepts_explored,
            "connections_made": self.connections_made,
            "memories_reviewed": self.memories_reviewed,
            "new_questions": self.new_questions,
            "success": self.success,
            "error": self.error,
        }


class BackgroundThinker:
    """
    Performs autonomous background thinking when the agent is idle.

    Modes:
    - EXPLORATION: Traverse knowledge graph, find new connections
    - REFLECTION: Review recent experiences, extract lessons
    - SYNTHESIS: Combine disparate concepts into new understanding
    - PLANNING: Anticipate future needs, prepare strategies
    - CURIOSITY: Follow interesting threads, ask questions
    - CONSOLIDATION: Strengthen important memories, prune noise
    """

    def __init__(
        self,
        kernel: CognitiveKernel,
        memory_fabric: Optional[MemoryFabric] = None,
        config: Optional[ThinkingConfig] = None,
    ):
        self.kernel = kernel
        self.memory_fabric = memory_fabric
        self.config = config or ThinkingConfig()

        self._running = False
        self._thought_history: List[ThoughtResult] = []
        self._explored_concepts: Set[str] = set()
        self._curiosity_queue: List[str] = []

        # Statistics
        self._total_sessions = 0
        self._total_insights = 0
        self._total_connections = 0

    async def think(self, mode: Optional[ThinkingMode] = None) -> ThoughtResult:
        """
        Perform a background thinking session.

        Args:
            mode: Specific thinking mode (random if None)

        Returns:
            ThoughtResult with insights and metadata
        """
        if self._running:
            # Already thinking, skip
            return ThoughtResult(
                mode=mode or ThinkingMode.EXPLORATION,
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                success=False,
                error="Already thinking",
            )

        self._running = True
        start_time = datetime.utcnow()
        mode = mode or self._select_mode()

        logger.info(f"Starting background thinking: {mode.value}")

        result = ThoughtResult(
            mode=mode,
            started_at=start_time,
        )

        try:
            # Dispatch to appropriate thinking method
            if mode == ThinkingMode.EXPLORATION:
                await self._explore(result)
            elif mode == ThinkingMode.REFLECTION:
                await self._reflect(result)
            elif mode == ThinkingMode.SYNTHESIS:
                await self._synthesize(result)
            elif mode == ThinkingMode.PLANNING:
                await self._plan(result)
            elif mode == ThinkingMode.CURIOSITY:
                await self._follow_curiosity(result)
            elif mode == ThinkingMode.CONSOLIDATION:
                await self._consolidate(result)

            result.success = True

        except Exception as e:
            logger.error(f"Background thinking failed: {e}")
            result.success = False
            result.error = str(e)

        finally:
            result.completed_at = datetime.utcnow()
            self._running = False
            self._total_sessions += 1
            self._total_insights += len(result.insights)
            self._total_connections += result.connections_made

            # Store insights in memory
            if self.config.store_insights and result.insights and self.memory_fabric:
                await self._store_insights(result.insights)

            # Keep history manageable
            self._thought_history.append(result)
            if len(self._thought_history) > 100:
                self._thought_history = self._thought_history[-100:]

        logger.info(
            f"Background thinking complete: {mode.value}, "
            f"{len(result.insights)} insights, {result.connections_made} connections"
        )

        return result

    def _select_mode(self) -> ThinkingMode:
        """Select thinking mode based on weights."""
        modes = list(self.config.mode_weights.keys())
        weights = list(self.config.mode_weights.values())
        return random.choices(modes, weights=weights)[0]

    async def _explore(self, result: ThoughtResult) -> None:
        """Explore the knowledge graph for new connections."""
        if not self.memory_fabric:
            return

        # Get random seed concepts from semantic memory
        seeds = await self._get_random_concepts(self.config.max_concepts_per_session)

        for seed in seeds:
            result.concepts_explored.append(seed)
            self._explored_concepts.add(seed)

            # Query related concepts
            related = await self.memory_fabric.query(
                query=seed,
                memory_types=[MemoryType.SEMANTIC, MemoryType.STRUCTURAL],
                limit=5,
            )

            for rel in related:
                concept = rel.get("content", "")
                if concept and concept not in self._explored_concepts:
                    # Check if this is a novel connection
                    connection = await self._evaluate_connection(seed, concept)
                    if connection:
                        result.insights.append(connection)
                        result.connections_made += 1

            # Limit exploration depth
            if len(result.insights) >= self.config.exploration_depth:
                break

    async def _reflect(self, result: ThoughtResult) -> None:
        """Reflect on recent experiences and extract lessons."""
        if not self.memory_fabric:
            return

        # Query recent episodic memories
        cutoff = datetime.utcnow() - timedelta(hours=self.config.reflection_lookback_hours)

        memories = await self.memory_fabric.query(
            query="experience outcome result",
            memory_types=[MemoryType.EPISODIC],
            limit=20,
        )

        result.memories_reviewed = len(memories)

        # Analyze each memory for lessons
        for memory in memories:
            content = memory.get("content", "")
            metadata = memory.get("metadata", {})

            # Extract key elements
            outcome = metadata.get("outcome")
            action = metadata.get("action")
            confidence = memory.get("importance", 0.5)

            if confidence >= self.config.min_reflection_confidence:
                insight = await self._extract_lesson(content, outcome, action, confidence)
                if insight:
                    result.insights.append(insight)
                    result.connections_made += 1

    async def _synthesize(self, result: ThoughtResult) -> None:
        """Synthesize new understanding from disparate concepts."""
        if not self.memory_fabric:
            return

        # Get diverse concepts from different memory types
        concepts = []

        for mem_type in [MemoryType.SEMANTIC, MemoryType.STRUCTURAL, MemoryType.EPISODIC]:
            mems = await self.memory_fabric.query(
                query="concept principle pattern",
                memory_types=[mem_type],
                limit=5,
            )
            concepts.extend([m.get("content", "") for m in mems if m.get("content")])

        # Try to find synthesis opportunities
        # In a full implementation, this would use the kernel to reason about combinations
        for i, c1 in enumerate(concepts[:5]):
            for c2 in concepts[i + 1 : 6]:
                synthesis = await self._attempt_synthesis(c1, c2)
                if synthesis:
                    result.insights.append(synthesis)
                    result.connections_made += 1

    async def _plan(self, result: ThoughtResult) -> None:
        """Plan for anticipated future needs."""
        # This would integrate with the objective manager to anticipate goals
        # For now, generate planning questions

        if self.memory_fabric:
            # Look for patterns in past objectives
            objectives = await self.memory_fabric.query(
                query="objective goal task",
                memory_types=[MemoryType.EPISODIC, MemoryType.PROCEDURAL],
                limit=10,
            )

            for obj in objectives:
                # Generate anticipatory questions
                question = f"How to better achieve: {obj.get('content', '')[:100]}"
                result.new_questions.append(question)
                result.insights.append(
                    {
                        "type": "planning_question",
                        "question": question,
                        "source": obj.get("content", ""),
                        "importance": 0.6,
                    }
                )

    async def _follow_curiosity(self, result: ThoughtResult) -> None:
        """Follow curiosity threads and generate questions."""
        # Pick a curiosity topic
        topic = random.choice(self.config.curiosity_topics)

        if self.memory_fabric:
            # Search for related knowledge
            related = await self.memory_fabric.query(
                query=topic,
                memory_types=[MemoryType.SEMANTIC, MemoryType.STRUCTURAL],
                limit=5,
            )

            for rel in related:
                content = rel.get("content", "")
                # Generate curiosity-driven questions
                questions = [
                    f"What causes {topic} in {content[:50]}?",
                    f"How does {topic} relate to {content[:50]}?",
                    f"Can {topic} be optimized in {content[:50]}?",
                ]
                result.new_questions.extend(questions)

                # Store as insights
                for q in questions:
                    result.insights.append(
                        {
                            "type": "curiosity_question",
                            "question": q,
                            "topic": topic,
                            "related_to": content[:100],
                            "importance": 0.5,
                        }
                    )

        result.concepts_explored.append(topic)

    async def _consolidate(self, result: ThoughtResult) -> None:
        """Consolidate important memories, identify patterns."""
        if not self.memory_fabric:
            return

        # Find frequently accessed but not yet consolidated memories
        memories = await self.memory_fabric.query(
            query="important recurring pattern",
            memory_types=[MemoryType.WORKING, MemoryType.EPISODIC],
            limit=10,
        )

        result.memories_reviewed = len(memories)

        for mem in memories:
            importance = mem.get("importance", 0)
            access_count = mem.get("metadata", {}).get("access_count", 0)

            if importance > self.config.insight_importance_threshold or access_count > 3:
                # This memory should be consolidated
                result.insights.append(
                    {
                        "type": "consolidation_candidate",
                        "memory_id": mem.get("id"),
                        "content": mem.get("content", "")[:200],
                        "importance": importance,
                        "access_count": access_count,
                        "recommendation": "promote_to_long_term",
                    }
                )
                result.connections_made += 1

    async def _get_random_concepts(self, count: int) -> List[str]:
        """Get random concepts from memory for exploration."""
        if not self.memory_fabric:
            return []

        # Query for diverse concepts
        results = await self.memory_fabric.query(
            query="concept idea principle method",
            memory_types=[MemoryType.SEMANTIC],
            limit=count * 2,
        )

        concepts = [r.get("content", "") for r in results if r.get("content")]

        # Filter out recently explored
        new_concepts = [c for c in concepts if c not in self._explored_concepts]

        return new_concepts[:count]

    async def _evaluate_connection(self, concept1: str, concept2: str) -> Optional[Dict[str, Any]]:
        """Evaluate if two concepts have a meaningful connection."""
        # Use kernel to reason about connection
        try:
            result = await self.kernel.process(
                {
                    "type": "connection_evaluation",
                    "concept_a": concept1,
                    "concept_b": concept2,
                    "task": "Identify meaningful relationships, causal links, or analogies",
                },
                priority=0.3,
            )

            decision = result.get("decision", {})
            if decision.get("confidence", 0) > 0.5:
                return {
                    "type": "concept_connection",
                    "concept_a": concept1,
                    "concept_b": concept2,
                    "relationship": decision.get("reasoning", ""),
                    "confidence": decision.get("confidence", 0.5),
                    "importance": decision.get("confidence", 0.5) * 0.8,
                }
        except Exception as e:
            logger.debug(f"Connection evaluation failed: {e}")

        return None

    async def _extract_lesson(
        self,
        content: str,
        outcome: Optional[str],
        action: Optional[str],
        confidence: float,
    ) -> Optional[Dict[str, Any]]:
        """Extract a lesson from an experience."""
        if not outcome and not action:
            return None

        return {
            "type": "reflection_lesson",
            "experience": content[:200],
            "action": action,
            "outcome": outcome,
            "lesson": f"When {action}, {outcome}" if action and outcome else content[:100],
            "confidence": confidence,
            "importance": confidence * 0.8,
        }

    async def _attempt_synthesis(self, concept1: str, concept2: str) -> Optional[Dict[str, Any]]:
        """Attempt to synthesize understanding from two concepts."""
        try:
            result = await self.kernel.process(
                {
                    "type": "synthesis",
                    "concept_a": concept1,
                    "concept_b": concept2,
                    "task": "Find unifying principles, analogies, or combined applications",
                },
                priority=0.2,
            )

            decision = result.get("decision", {})
            if decision.get("confidence", 0) > 0.6:
                return {
                    "type": "synthesis",
                    "concept_a": concept1,
                    "concept_b": concept2,
                    "unified_understanding": decision.get("reasoning", ""),
                    "confidence": decision.get("confidence", 0),
                    "importance": decision.get("confidence", 0) * 0.7,
                }
        except Exception:
            pass

        return None

    async def _store_insights(self, insights: List[Dict[str, Any]]) -> None:
        """Store insights in memory fabric."""
        for insight in insights:
            if insight.get("importance", 0) >= self.config.insight_importance_threshold:
                try:
                    await self.memory_fabric.store(
                        {
                            "content": str(insight),
                            "memory_type": MemoryType.SEMANTIC,
                            "importance": insight.get("importance", 0.5),
                            "source": "background_thinking",
                            "metadata": insight,
                        }
                    )
                except Exception as e:
                    logger.warning(f"Failed to store insight: {e}")

    def get_stats(self) -> Dict[str, Any]:
        """Get thinker statistics."""
        return {
            "total_sessions": self._total_sessions,
            "total_insights": self._total_insights,
            "total_connections": self._total_connections,
            "explored_concepts": len(self._explored_concepts),
            "curiosity_queue_size": len(self._curiosity_queue),
            "history_size": len(self._thought_history),
            "last_thought": (
                self._thought_history[-1].completed_at.isoformat()
                if self._thought_history
                else None
            ),
        }

    def get_recent_thoughts(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent thought results."""
        return [t.to_dict() for t in self._thought_history[-limit:]]
