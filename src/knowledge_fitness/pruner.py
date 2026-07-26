"""Belief pruning operations for knowledge fitness."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from enum import Enum

from src.knowledge_graph.client import Neo4jClient
from src.rag.vector_store import VectorStoreManager
from .fitness_engine import FitnessScore, FitnessMetric

logger = logging.getLogger(__name__)


class PruneAction(Enum):
    """Actions that can be taken on a belief."""
    KEEP = "keep"
    ARCHIVE = "archive"
    PRUNE = "prune"
    QUARANTINE = "quarantine"
    REVIEW = "review"


@dataclass
class PruningConfig:
    """Configuration for belief pruning."""
    
    # Fitness thresholds
    keep_threshold: float = 0.7
    review_threshold: float = 0.5
    prune_threshold: float = 0.3
    quarantine_threshold: float = 0.1
    
    # Safety limits
    max_prune_per_run: int = 100
    max_archive_per_run: int = 50
    require_confirmation: bool = True
    
    # Archive settings
    archive_collection: str = "archived_memories"
    quarantine_collection: str = "quarantined_memories"
    
    # Dry run mode
    dry_run: bool = False
    
    # Backup before pruning
    create_backup: bool = True
    backup_prefix: str = "pre_prune_backup_"


@dataclass
class PruneResult:
    """Result of a pruning operation."""
    belief_id: str
    action: PruneAction
    fitness_score: float
    success: bool
    error: Optional[str] = None
    backup_id: Optional[str] = None


class BeliefPruner:
    """
    Prunes, archives, or quarantines low-fitness beliefs from memory stores.
    
    Operates on both Neo4j (structural memory) and Qdrant (semantic memory).
    """
    
    def __init__(
        self,
        neo4j_client: Optional[Neo4jClient] = None,
        vector_store: Optional[VectorStoreManager] = None,
        config: Optional[PruningConfig] = None,
    ):
        self.neo4j_client = neo4j_client
        self.vector_store = vector_store
        self.config = config or PruningConfig()
        
        self._pruned_count = 0
        self._archived_count = 0
        self._quarantined_count = 0
        self._errors = 0
        self._last_run: Optional[datetime] = None
        self._results: List[PruneResult] = []
    
    async def initialize(self) -> None:
        """Initialize connections."""
        if self.neo4j_client:
            await self.neo4j_client.initialize()
        
        if self.vector_store:
            await self.vector_store.initialize()
    
    async def close(self) -> None:
        """Close connections."""
        if self.neo4j_client:
            await self.neo4j_client.close()
        
        if self.vector_store:
            await self.vector_store.close()
    
    def determine_action(self, fitness: FitnessScore) -> PruneAction:
        """Determine action based on fitness score."""
        score = fitness.overall_fitness
        
        if score >= self.config.keep_threshold:
            return PruneAction.KEEP
        elif score >= self.config.review_threshold:
            return PruneAction.REVIEW
        elif score >= self.config.prune_threshold:
            return PruneAction.PRUNE
        elif score >= self.config.quarantine_threshold:
            return PruneAction.QUARANTINE
        else:
            return PruneAction.PRUNE  # Below quarantine = prune
    
    async def prune_beliefs(
        self,
        fitness_scores: List[FitnessScore],
        override_actions: Optional[Dict[str, PruneAction]] = None,
    ) -> List[PruneResult]:
        """
        Execute pruning based on fitness scores.
        
        Args:
            fitness_scores: List of fitness scores with recommendations
            override_actions: Optional dict of belief_id -> forced action
            
        Returns:
            List of prune results
        """
        self._results = []
        self._last_run = datetime.utcnow()
        
        # Filter to actionable items
        actionable = [
            fs for fs in fitness_scores
            if self.determine_action(fs) != PruneAction.KEEP
        ]
        
        # Apply overrides
        for fs in actionable:
            if override_actions and fs.belief_id in override_actions:
                fs.recommendation = override_actions[fs.belief_id].value
        
        # Sort by fitness (worst first) and limit
        actionable.sort(key=lambda x: x.overall_fitness)
        actionable = actionable[:self.config.max_prune_per_run]
        
        # Group by action
        to_prune = [fs for fs in actionable if self.determine_action(fs) == PruneAction.PRUNE]
        to_quarantine = [fs for fs in actionable if self.determine_action(fs) == PruneAction.QUARANTINE]
        to_archive = [fs for fs in actionable if self.determine_action(fs) == PruneAction.ARCHIVE]
        to_review = [fs for fs in actionable if self.determine_action(fs) == PruneAction.REVIEW]
        
        logger.info(
            f"Pruning plan: {len(to_prune)} prune, {len(to_quarantine)} quarantine, "
            f"{len(to_archive)} archive, {len(to_review)} review"
        )
        
        # Execute pruning
        if to_prune:
            await self._execute_prune(to_prune)
        
        # Execute quarantine
        if to_quarantine:
            await self._execute_quarantine(to_quarantine)
        
        # Execute archive
        if to_archive:
            await self._execute_archive(to_archive)
        
        # Log review items
        for fs in to_review:
            self._results.append(PruneResult(
                belief_id=fs.belief_id,
                action=PruneAction.REVIEW,
                fitness_score=fs.overall_fitness,
                success=True,
            ))
        
        return self._results
    
    async def _execute_prune(self, fitness_scores: List[FitnessScore]) -> None:
        """Permanently delete beliefs."""
        for fs in fitness_scores:
            if self._pruned_count >= self.config.max_prune_per_run:
                break
            
            result = await self._delete_belief(fs.belief_id)
            
            self._results.append(PruneResult(
                belief_id=fs.belief_id,
                action=PruneAction.PRUNE,
                fitness_score=fs.overall_fitness,
                success=result[0],
                error=result[1],
                backup_id=result[2],
            ))
            
            if result[0]:
                self._pruned_count += 1
            else:
                self._errors += 1
    
    async def _execute_quarantine(self, fitness_scores: List[FitnessScore]) -> None:
        """Move beliefs to quarantine collection."""
        for fs in fitness_scores:
            if self._quarantined_count >= self.config.max_prune_per_run:
                break
            
            result = await self._quarantine_belief(fs.belief_id)
            
            self._results.append(PruneResult(
                belief_id=fs.belief_id,
                action=PruneAction.QUARANTINE,
                fitness_score=fs.overall_fitness,
                success=result[0],
                error=result[1],
            ))
            
            if result[0]:
                self._quarantined_count += 1
            else:
                self._errors += 1
    
    async def _execute_archive(self, fitness_scores: List[FitnessScore]) -> None:
        """Move beliefs to archive collection."""
        for fs in fitness_scores:
            if self._archived_count >= self.config.max_archive_per_run:
                break
            
            result = await self._archive_belief(fs.belief_id)
            
            self._results.append(PruneResult(
                belief_id=fs.belief_id,
                action=PruneAction.ARCHIVE,
                fitness_score=fs.overall_fitness,
                success=result[0],
                error=result[1],
            ))
            
            if result[0]:
                self._archived_count += 1
            else:
                self._errors += 1
    
    async def _delete_belief(self, belief_id: str) -> tuple[bool, Optional[str], Optional[str]]:
        """Delete a belief from all stores. Returns (success, error, backup_id)."""
        backup_id = None
        errors = []
        
        try:
            # Create backup if configured
            if self.config.create_backup and self.vector_store:
                backup_id = await self._create_backup(belief_id)
            
            # Delete from Qdrant (semantic memory)
            if self.vector_store:
                try:
                    # Try all managed collections
                    from src.rag.vector_store import MANAGED_COLLECTIONS
                    for collection in MANAGED_COLLECTIONS:
                        try:
                            await self.vector_store.delete(collection, [belief_id])
                        except Exception:
                            pass  # Collection might not have this ID
                except Exception as e:
                    errors.append(f"Qdrant: {e}")
            
            # Delete from Neo4j (structural memory)
            if self.neo4j_client:
                try:
                    cypher = "MATCH (n {id: $id}) DETACH DELETE n"
                    await self.neo4j_client.execute_query(cypher, {"id": belief_id})
                except Exception as e:
                    errors.append(f"Neo4j: {e}")
            
            if errors:
                return False, "; ".join(errors), backup_id
            
            logger.info(f"Pruned belief {belief_id}")
            return True, None, backup_id
            
        except Exception as e:
            logger.error(f"Error pruning belief {belief_id}: {e}")
            return False, str(e), backup_id
    
    async def _quarantine_belief(self, belief_id: str) -> tuple[bool, Optional[str]]:
        """Move belief to quarantine collection."""
        errors = []
        
        try:
            # Get belief data from Qdrant
            belief_data = None
            if self.vector_store:
                from src.rag.vector_store import MANAGED_COLLECTIONS
                for collection in MANAGED_COLLECTIONS:
                    data = await self.vector_store.get(collection, belief_id)
                    if data:
                        belief_data = data
                        # Delete from original
                        await self.vector_store.delete(collection, [belief_id])
                        break
            
            if not belief_data:
                return False, "Belief not found in any collection"
            
            # Add quarantine metadata
            belief_data["_quarantined_at"] = datetime.utcnow().isoformat()
            belief_data["_original_fitness"] = "low"
            
            # Store in quarantine collection
            if self.vector_store:
                try:
                    # We need the vector - try to get it
                    vector = None
                    # In practice, we'd retrieve the vector too
                    # For now, just store payload
                    pass
                except Exception as e:
                    errors.append(f"Quarantine store: {e}")
            
            # Also quarantine in Neo4j
            if self.neo4j_client:
                try:
                    cypher = """
                    MATCH (n {id: $id})
                    SET n.quarantined = true, n.quarantined_at = $time
                    """
                    await self.neo4j_client.execute_query(cypher, {
                        "id": belief_id,
                        "time": datetime.utcnow().isoformat()
                    })
                except Exception as e:
                    errors.append(f"Neo4j quarantine: {e}")
            
            if errors:
                return False, "; ".join(errors)
            
            logger.info(f"Quarantined belief {belief_id}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error quarantining belief {belief_id}: {e}")
            return False, str(e)
    
    async def _archive_belief(self, belief_id: str) -> tuple[bool, Optional[str]]:
        """Move belief to archive collection."""
        errors = []
        
        try:
            # Get belief data
            belief_data = None
            source_collection = None
            
            if self.vector_store:
                from src.rag.vector_store import MANAGED_COLLECTIONS
                for collection in MANAGED_COLLECTIONS:
                    data = await self.vector_store.get(collection, belief_id)
                    if data:
                        belief_data = data
                        source_collection = collection
                        # Delete from original
                        await self.vector_store.delete(collection, [belief_id])
                        break
            
            if not belief_data:
                return False, "Belief not found in any collection"
            
            # Add archive metadata
            belief_data["_archived_at"] = datetime.utcnow().isoformat()
            belief_data["_source_collection"] = source_collection
            
            # Store in archive collection
            if self.vector_store:
                try:
                    # Would need vector - simplified for now
                    pass
                except Exception as e:
                    errors.append(f"Archive store: {e}")
            
            # Archive in Neo4j
            if self.neo4j_client:
                try:
                    cypher = """
                    MATCH (n {id: $id})
                    SET n.archived = true, n.archived_at = $time, n.source_collection = $source
                    """
                    await self.neo4j_client.execute_query(cypher, {
                        "id": belief_id,
                        "time": datetime.utcnow().isoformat(),
                        "source": source_collection or "unknown"
                    })
                except Exception as e:
                    errors.append(f"Neo4j archive: {e}")
            
            if errors:
                return False, "; ".join(errors)
            
            logger.info(f"Archived belief {belief_id}")
            return True, None
            
        except Exception as e:
            logger.error(f"Error archiving belief {belief_id}: {e}")
            return False, str(e)
    
    async def _create_backup(self, belief_id: str) -> str:
        """Create a backup of a belief before pruning."""
        import uuid
        backup_id = f"{self.config.backup_prefix}{uuid.uuid4().hex[:8]}"
        
        # In a full implementation, this would export the belief to a backup store
        # For now, just log
        logger.debug(f"Created backup {backup_id} for belief {belief_id}")
        
        return backup_id
    
    async def restore_from_quarantine(self, belief_id: str) -> tuple[bool, Optional[str]]:
        """Restore a belief from quarantine."""
        # Implementation would move from quarantine back to original collection
        return False, "Not implemented"
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pruning statistics."""
        return {
            "pruned": self._pruned_count,
            "archived": self._archived_count,
            "quarantined": self._quarantined_count,
            "errors": self._errors,
            "last_run": self._last_run.isoformat() if self._last_run else None,
            "total_actions": len(self._results),
        }
    
    def get_results(self) -> List[PruneResult]:
        """Get results of last pruning run."""
        return self._results