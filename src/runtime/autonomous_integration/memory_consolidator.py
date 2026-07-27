"""
Memory Consolidator - Automated memory consolidation and promotion.

Moves important memories from working/episodic storage to long-term semantic
and structural storage, strengthening connections and pruning noise.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set

from src.memory.memory_fabric import MemoryFabric, MemoryType, MemoryEntry
from src.cognitive_kernel.kernel import CognitiveKernel

logger = logging.getLogger(__name__)


@dataclass
class ConsolidationConfig:
    """Configuration for memory consolidation."""

    # Timing
    interval: float = 300.0  # 5 minutes
    min_age_hours: float = 1.0  # Minimum age before consolidation

    # Thresholds
    importance_threshold: float = 0.6
    access_count_threshold: int = 3
    confidence_threshold: float = 0.7

    # Batch processing
    batch_size: int = 50
    max_batches_per_run: int = 5

    # Promotion rules
    promote_working_to_episodic: bool = True
    promote_episodic_to_semantic: bool = True
    promote_semantic_to_structural: bool = True

    # Pruning
    prune_low_importance: bool = True
    prune_threshold: float = 0.2
    max_age_days: int = 30

    # Strengthening
    strengthen_connections: bool = True
    min_connection_strength: float = 0.5


@dataclass
class ConsolidationResult:
    """Result of a consolidation run."""

    started_at: datetime
    completed_at: datetime
    memories_processed: int = 0
    promoted_to_episodic: int = 0
    promoted_to_semantic: int = 0
    promoted_to_structural: int = 0
    connections_strengthened: int = 0
    pruned: int = 0
    errors: int = 0
    error_details: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat(),
            "memories_processed": self.memories_processed,
            "promoted_to_episodic": self.promoted_to_episodic,
            "promoted_to_semantic": self.promoted_to_semantic,
            "promoted_to_structural": self.promoted_to_structural,
            "connections_strengthened": self.connections_strengthened,
            "pruned": self.pruned,
            "errors": self.errors,
        }


class MemoryConsolidator:
    """
    Automates memory consolidation across the memory fabric.

    Performs:
    - Working memory -> Episodic memory promotion
    - Episodic memory -> Semantic memory promotion
    - Semantic memory -> Structural (Neo4j) promotion
    - Connection strengthening between related memories
    - Pruning of low-value, old memories
    """

    def __init__(
        self,
        memory_fabric: MemoryFabric,
        kernel: Optional[CognitiveKernel] = None,
        config: Optional[ConsolidationConfig] = None,
    ):
        self.memory_fabric = memory_fabric
        self.kernel = kernel
        self.config = config or ConsolidationConfig()

        self._last_consolidation: Optional[datetime] = None
        self._consolidation_history: List[ConsolidationResult] = []
        self._running = False

        # Statistics
        self._total_consolidations = 0
        self._total_promoted = 0
        self._total_pruned = 0

    async def consolidate(self) -> ConsolidationResult:
        """
        Run a full consolidation cycle.

        Returns:
            ConsolidationResult with statistics
        """
        if self._running:
            logger.warning("Consolidation already running")
            return ConsolidationResult(
                started_at=datetime.utcnow(),
                completed_at=datetime.utcnow(),
                errors=1,
                error_details=["Already running"],
            )

        self._running = True
        result = ConsolidationResult(started_at=datetime.utcnow())

        try:
            logger.info("Starting memory consolidation")

            # Phase 1: Promote working -> episodic
            if self.config.promote_working_to_episodic:
                count = await self._promote_working_to_episodic()
                result.promoted_to_episodic = count
                result.memories_processed += count

            # Phase 2: Promote episodic -> semantic
            if self.config.promote_episodic_to_semantic:
                count = await self._promote_episodic_to_semantic()
                result.promoted_to_semantic = count
                result.memories_processed += count

            # Phase 3: Promote semantic -> structural
            if self.config.promote_semantic_to_structural:
                count = await self._promote_semantic_to_structural()
                result.promoted_to_structural = count
                result.memories_processed += count

            # Phase 4: Strengthen connections
            if self.config.strengthen_connections:
                count = await self._strengthen_connections()
                result.connections_strengthened = count

            # Phase 5: Prune low-value memories
            if self.config.prune_low_importance:
                count = await self._prune_low_value()
                result.pruned = count

            self._last_consolidation = datetime.utcnow()
            result.completed_at = datetime.utcnow()

            # Update statistics
            self._total_consolidations += 1
            self._total_promoted += (
                result.promoted_to_episodic
                + result.promoted_to_semantic
                + result.promoted_to_structural
            )
            self._total_pruned += result.pruned

            # Record history
            self._consolidation_history.append(result)
            if len(self._consolidation_history) > 100:
                self._consolidation_history = self._consolidation_history[-100:]

            logger.info(
                f"Memory consolidation complete: "
                f"{result.memories_processed} processed, "
                f"{result.promoted_to_episodic}->episodic, "
                f"{result.promoted_to_semantic}->semantic, "
                f"{result.promoted_to_structural}->structural, "
                f"{result.connections_strengthened} connections, "
                f"{result.pruned} pruned"
            )

        except Exception as e:
            logger.error(f"Consolidation failed: {e}")
            result.errors += 1
            result.error_details.append(str(e))
            result.completed_at = datetime.utcnow()

        finally:
            self._running = False

        return result

    async def _promote_working_to_episodic(self) -> int:
        """Promote important working memories to episodic storage."""
        if not self.memory_fabric or not self.memory_fabric._backends.get(MemoryType.WORKING):
            return 0

        promoted = 0

        # Scan working memory for candidates
        backend = self.memory_fabric._backends[MemoryType.WORKING]

        if hasattr(backend, "scan"):
            cursor = 0
            batch = []

            while True:
                cursor, keys = await backend.scan(cursor, match="memory:*", count=100)

                for key in keys:
                    value = await backend.get(key)
                    if not value:
                        continue

                    import json

                    try:
                        data = json.loads(value)

                        importance = data.get("importance", 0.5)
                        access_count = data.get("access_count", 0)
                        age_hours = (
                            datetime.utcnow().timestamp() - data.get("timestamp", 0)
                        ) / 3600

                        # Check promotion criteria
                        if (
                            importance >= self.config.importance_threshold
                            or access_count >= self.config.access_count_threshold
                        ) and age_hours >= self.config.min_age_hours:

                            batch.append((key, data))

                            if len(batch) >= self.config.batch_size:
                                promoted += await self._process_promotion_batch(
                                    batch, MemoryType.WORKING, MemoryType.EPISODIC
                                )
                                batch = []

                    except Exception as e:
                        logger.debug(f"Failed to process working memory {key}: {e}")

                if cursor == 0:
                    break

            # Process remaining batch
            if batch:
                promoted += await self._process_promotion_batch(
                    batch, MemoryType.WORKING, MemoryType.EPISODIC
                )

        return promoted

    async def _promote_episodic_to_semantic(self) -> int:
        """Promote important episodic memories to semantic (vector) storage."""
        if not self.memory_fabric or not self.memory_fabric._backends.get(MemoryType.EPISODIC):
            return 0

        promoted = 0

        # Use the episodic memory's search/query capabilities
        backend = self.memory_fabric._backends[MemoryType.EPISODIC]

        if hasattr(backend, "get_consolidation_candidates"):
            try:
                candidates = await backend.get_consolidation_candidates(
                    min_importance=self.config.importance_threshold,
                    min_access_count=self.config.access_count_threshold,
                    min_age_hours=self.config.min_age_hours,
                    limit=self.config.batch_size * self.config.max_batches_per_run,
                )

                for candidate in candidates:
                    # Store in semantic memory with embedding
                    await self.memory_fabric.store(
                        {
                            "content": candidate.content,
                            "memory_type": MemoryType.SEMANTIC,
                            "importance": candidate.importance_score,
                            "source": "consolidation",
                            "metadata": {
                                **candidate.metadata_,
                                "original_type": "episodic",
                                "original_id": str(candidate.id),
                                "consolidated_at": datetime.utcnow().isoformat(),
                            },
                        }
                    )
                    promoted += 1

            except Exception as e:
                logger.error(f"Episodic to semantic promotion failed: {e}")

        return promoted

    async def _promote_semantic_to_structural(self) -> int:
        """Promote high-confidence semantic memories to structural (Neo4j) graph."""
        if not self.memory_fabric or not self.memory_fabric._backends.get(MemoryType.STRUCTURAL):
            return 0

        promoted = 0

        # Query semantic memory for high-confidence concepts
        if self.memory_fabric._backends.get(MemoryType.SEMANTIC):
            try:
                # Get high-importance semantic memories
                results = await self.memory_fabric.query(
                    query="concept principle rule pattern fact",
                    memory_types=[MemoryType.SEMANTIC],
                    limit=self.config.batch_size * self.config.max_batches_per_run,
                    min_importance=self.config.confidence_threshold,
                )

                for result in results:
                    metadata = result.get("metadata", {})
                    confidence = metadata.get("confidence", result.get("importance", 0.5))

                    if confidence >= self.config.confidence_threshold:
                        # Extract entities and relationships using kernel
                        if self.kernel:
                            try:
                                extraction = await self.kernel.process(
                                    {
                                        "type": "knowledge_extraction",
                                        "content": result.get("content", ""),
                                        "task": "Extract entities, relationships, and formalize as structured knowledge",
                                    }
                                )

                                decision = extraction.get("decision", {})
                                if (
                                    decision.get("confidence", 0)
                                    > self.config.min_connection_strength
                                ):
                                    # Store in Neo4j
                                    await self._store_in_structural(
                                        result.get("content", ""),
                                        decision.get("reasoning", ""),
                                        confidence,
                                    )
                                    promoted += 1
                            except Exception as e:
                                logger.debug(f"Structural promotion failed: {e}")

            except Exception as e:
                logger.error(f"Semantic to structural promotion failed: {e}")

        return promoted

    async def _store_in_structural(
        self,
        content: str,
        structured_knowledge: str,
        confidence: float,
    ) -> None:
        """Store extracted knowledge in Neo4j."""
        backend = self.memory_fabric._backends.get(MemoryType.STRUCTURAL)

        if not backend or not hasattr(backend, "execute_query"):
            return

        import uuid

        node_id = str(uuid.uuid4())

        # Parse structured knowledge for entities/relationships
        # This is simplified - in practice would parse the kernel's output
        cypher = """
        CREATE (k:Knowledge {
            id: $id,
            content: $content,
            structured: $structured,
            confidence: $confidence,
            created_at: $created_at
        })
        """

        await backend.execute_query(
            cypher,
            {
                "id": node_id,
                "content": content[:1000],
                "structured": structured_knowledge[:2000],
                "confidence": confidence,
                "created_at": datetime.utcnow().isoformat(),
            },
        )

    async def _process_promotion_batch(
        self,
        batch: List[tuple],
        from_type: MemoryType,
        to_type: MemoryType,
    ) -> int:
        """Process a batch of memories for promotion."""
        promoted = 0

        for key, data in batch:
            try:
                # Store in target memory type
                await self.memory_fabric.store(
                    {
                        "content": data.get("content", ""),
                        "memory_type": to_type,
                        "importance": data.get("importance", 0.5),
                        "source": "promotion",
                        "metadata": {
                            **data.get("metadata", {}),
                            "original_type": from_type.value,
                            "original_key": key,
                            "promoted_at": datetime.utcnow().isoformat(),
                        },
                    }
                )

                # Delete from source
                backend = self.memory_fabric._backends.get(from_type)
                if backend and hasattr(backend, "delete"):
                    await backend.delete(key)

                promoted += 1

            except Exception as e:
                logger.debug(f"Failed to promote {key}: {e}")

        return promoted

    async def _strengthen_connections(self) -> int:
        """Strengthen connections between related memories."""
        strengthened = 0

        if not self.memory_fabric or not self.memory_fabric._backends.get(MemoryType.STRUCTURAL):
            return 0

        # This would query Neo4j for weakly connected nodes and strengthen
        # them based on co-occurrence, semantic similarity, etc.
        # Simplified implementation

        return strengthened

    async def _prune_low_value(self) -> int:
        """Prune low-importance, old memories."""
        pruned = 0

        if not self.memory_fabric:
            return 0

        cutoff = datetime.utcnow() - timedelta(days=self.config.max_age_days)

        for mem_type in [MemoryType.WORKING, MemoryType.EPISODIC]:
            backend = self.memory_fabric._backends.get(mem_type)
            if not backend:
                continue

            if hasattr(backend, "prune_old_low_importance"):
                try:
                    count = await backend.prune_old_low_importance(
                        min_importance=self.config.prune_threshold,
                        max_age=cutoff,
                    )
                    pruned += count
                except Exception as e:
                    logger.debug(f"Pruning {mem_type.value} failed: {e}")

        return pruned

    def get_stats(self) -> Dict[str, Any]:
        """Get consolidator statistics."""
        return {
            "total_consolidations": self._total_consolidations,
            "total_promoted": self._total_promoted,
            "total_pruned": self._total_pruned,
            "last_consolidation": (
                self._last_consolidation.isoformat() if self._last_consolidation else None
            ),
            "history_size": len(self._consolidation_history),
        }

    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get consolidation history."""
        return [c.to_dict() for c in self._consolidation_history[-limit:]]
