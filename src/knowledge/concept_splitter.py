"""concept_splitter.py

Splits concepts into more granular sub-concepts when they become too broad.
Enables refinement of knowledge structures over time.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)


class SplitStrategy(str, Enum):
    """Strategies for splitting concepts."""
    SEMANTIC = "semantic"  # Split by semantic meaning
    TEMPORAL = "temporal"  # Split by time periods
    DOMAIN = "domain"  # Split by domain/application
    ATTRIBUTE = "attribute"  # Split by attributes
    CLUSTERING = "clustering"  # Cluster-based splitting


@dataclass
class SplitResult:
    """Result of a concept split operation."""
    original_concept_id: str
    new_concept_ids: List[str]
    split_strategy: SplitStrategy
    rationale: str
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)


class ConceptSplitter:
    """Splits concepts into more granular sub-concepts."""
    
    def __init__(self, concept_graph):
        self.graph = concept_graph
        self.split_history: List[SplitResult] = []
        logger.info("ConceptSplitter initialized")
    
    def should_split(
        self,
        concept_id: str,
        max_source_memories: int = 50,
        max_relationships: int = 20,
    ) -> bool:
        """Determine if a concept should be split."""
        concept = self.graph.get_concept(concept_id)
        if not concept:
            return False
        
        # Split if too many source memories
        if len(concept.source_memories) > max_source_memories:
            return True
        
        # Split if too many relationships
        if len(self.graph.adjacency.get(concept_id, set())) > max_relationships:
            return True
        
        # Split if description is too long
        if len(concept.description) > 500:
            return True
        
        return False
    
    def split_concept(
        self,
        concept_id: str,
        strategy: SplitStrategy = SplitStrategy.SEMANTIC,
        num_splits: int = 2,
    ) -> Optional[SplitResult]:
        """Split a concept into sub-concepts."""
        concept = self.graph.get_concept(concept_id)
        if not concept:
            return None
        
        if strategy == SplitStrategy.SEMANTIC:
            new_concepts = self._split_semantic(concept, num_splits)
        elif strategy == SplitStrategy.TEMPORAL:
            new_concepts = self._split_temporal(concept, num_splits)
        elif strategy == SplitStrategy.DOMAIN:
            new_concepts = self._split_domain(concept, num_splits)
        elif strategy == SplitStrategy.ATTRIBUTE:
            new_concepts = self._split_attribute(concept, num_splits)
        elif strategy == SplitStrategy.CLUSTERING:
            new_concepts = self._split_clustering(concept, num_splits)
        else:
            return None
        
        if not new_concepts:
            return None
        
        # Create new concepts
        new_concept_ids = []
        for new_concept_data in new_concepts:
            new_concept = self.graph.add_concept(
                name=new_concept_data["name"],
                description=new_concept_data["description"],
                confidence=concept.confidence * 0.9,
                metadata=concept.metadata.copy(),
                source_memories=new_concept_data["source_memories"],
            )
            new_concept_ids.append(new_concept.id)
            
            # Add relationship to original
            self.graph.add_relationship(
                concept_id,
                new_concept.id,
                "specializes",
                weight=0.8,
            )
        
        # Mark original as refining
        self.graph.update_concept_state(concept_id, "refining")
        
        result = SplitResult(
            original_concept_id=concept_id,
            new_concept_ids=new_concept_ids,
            split_strategy=strategy,
            rationale=f"Split {concept.name} into {len(new_concept_ids)} sub-concepts using {strategy.value}",
        )
        
        self.split_history.append(result)
        logger.info(f"Split concept {concept_id} into {len(new_concept_ids)} sub-concepts")
        return result
    
    def _split_semantic(self, concept, num_splits: int) -> List[Dict[str, Any]]:
        """Split concept by semantic meaning."""
        # Group source memories by semantic similarity
        memory_groups = self._group_memories_semantic(concept.source_memories, num_splits)
        
        splits = []
        for i, group in enumerate(memory_groups):
            if group:
                splits.append({
                    "name": f"{concept.name} - Part {i+1}",
                    "description": f"Sub-concept of {concept.name} focusing on specific aspects",
                    "source_memories": group,
                })
        
        return splits
    
    def _split_temporal(self, concept, num_splits: int) -> List[Dict[str, Any]]:
        """Split concept by time periods."""
        if not concept.source_memories:
            return []
        
        # Simple split: divide memories into chunks
        chunk_size = max(1, len(concept.source_memories) // num_splits)
        splits = []
        
        for i in range(num_splits):
            start = i * chunk_size
            end = start + chunk_size if i < num_splits - 1 else len(concept.source_memories)
            memories = concept.source_memories[start:end]
            
            if memories:
                splits.append({
                    "name": f"{concept.name} - Period {i+1}",
                    "description": f"Sub-concept of {concept.name} from time period {i+1}",
                    "source_memories": memories,
                })
        
        return splits
    
    def _split_domain(self, concept, num_splits: int) -> List[Dict[str, Any]]:
        """Split concept by domain/application."""
        # Extract domain keywords from metadata or description
        domain_keywords = concept.metadata.get("domains", [])
        
        if not domain_keywords:
            # Fallback to semantic split
            return self._split_semantic(concept, num_splits)
        
        splits = []
        for i, keyword in enumerate(domain_keywords[:num_splits]):
            # Find memories containing this keyword
            relevant_memories = [
                m for m in concept.source_memories
                if keyword.lower() in str(m).lower()
            ]
            
            if relevant_memories:
                splits.append({
                    "name": f"{concept.name} - {keyword.capitalize()}",
                    "description": f"Sub-concept of {concept.name} in {keyword} domain",
                    "source_memories": relevant_memories,
                })
        
        return splits
    
    def _split_attribute(self, concept, num_splits: int) -> List[Dict[str, Any]]:
        """Split concept by attributes."""
        # Extract attributes from metadata
        attributes = concept.metadata.get("attributes", {})
        
        if not attributes:
            return self._split_semantic(concept, num_splits)
        
        splits = []
        for i, (attr_name, attr_value) in enumerate(list(attributes.items())[:num_splits]):
            splits.append({
                "name": f"{concept.name} - {attr_name}",
                "description": f"Sub-concept of {concept.name} with {attr_name} = {attr_value}",
                "source_memories": concept.source_memories[:len(concept.source_memories)//num_splits],
            })
        
        return splits
    
    def _split_clustering(self, concept, num_splits: int) -> List[Dict[str, Any]]:
        """Split concept using clustering."""
        # Group memories by similarity
        memory_groups = self._group_memories_clustering(concept.source_memories, num_splits)
        
        splits = []
        for i, group in enumerate(memory_groups):
            if group:
                splits.append({
                    "name": f"{concept.name} - Cluster {i+1}",
                    "description": f"Sub-concept of {concept.name} from cluster {i+1}",
                    "source_memories": group,
                })
        
        return splits
    
    def _group_memories_semantic(self, memories: List[str], num_groups: int) -> List[List[str]]:
        """Group memories by semantic similarity."""
        if not memories:
            return []
        
        # Simple grouping by keyword overlap
        groups = [[] for _ in range(num_groups)]
        used = set()
        
        for i, memory in enumerate(memories):
            if memory in used:
                continue
            
            group_idx = i % num_groups
            memory_words = set(str(memory).lower().split())
            
            groups[group_idx].append(memory)
            used.add(memory)
            
            # Find similar memories
            for other in memories[i+1:]:
                if other in used:
                    continue
                
                other_words = set(str(other).lower().split())
                overlap = len(memory_words & other_words) / max(len(memory_words), len(other_words), 1)
                
                if overlap > 0.3:
                    groups[group_idx].append(other)
                    used.add(other)
        
        return groups
    
    def _group_memories_clustering(self, memories: List[str], num_groups: int) -> List[List[str]]:
        """Group memories using clustering."""
        # Similar to semantic grouping but with different threshold
        return self._group_memories_semantic(memories, num_groups)
    
    def get_split_history(self, concept_id: Optional[str] = None) -> List[SplitResult]:
        """Get split history, optionally filtered by concept."""
        if concept_id:
            return [s for s in self.split_history if s.original_concept_id == concept_id]
        return self.split_history
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get split statistics."""
        strategy_counts = {}
        for result in self.split_history:
            strategy_counts[result.split_strategy.value] = strategy_counts.get(result.split_strategy.value, 0) + 1
        
        return {
            "total_splits": len(self.split_history),
            "by_strategy": strategy_counts,
            "average_new_concepts": sum(len(r.new_concept_ids) for r in self.split_history) / len(self.split_history) if self.split_history else 0.0,
        }
