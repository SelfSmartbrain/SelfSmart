"""concept_graph.py

Core graph structure for representing concepts and their relationships.
Enables traversal, clustering, and evolution of knowledge structures.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Set, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)


class ConceptState(str, Enum):
    """Lifecycle states of a concept."""
    EMERGING = "emerging"
    STABLE = "stable"
    REFINING = "refining"
    DEPRECATED = "deprecated"
    MERGED = "merged"


@dataclass
class ConceptNode:
    """A single concept in the knowledge graph."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""
    description: str = ""
    state: ConceptState = ConceptState.EMERGING
    confidence: float = 0.5
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    metadata: Dict[str, Any] = field(default_factory=dict)
    source_memories: List[str] = field(default_factory=list)
    embedding: Optional[List[float]] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "state": self.state.value,
            "confidence": self.confidence,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
            "source_memories": self.source_memories,
        }


class ConceptGraph:
    """Graph structure for managing concepts and their relationships."""
    
    def __init__(self):
        self.nodes: Dict[str, ConceptNode] = {}
        self.adjacency: Dict[str, Set[str]] = {}  # concept_id -> set of related concept_ids
        self.edge_weights: Dict[tuple, float] = {}  # (from_id, to_id) -> weight
        self.edge_types: Dict[tuple, str] = {}  # (from_id, to_id) -> relationship_type
        logger.info("ConceptGraph initialized")
    
    def add_concept(
        self,
        name: str,
        description: str = "",
        confidence: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
        source_memories: Optional[List[str]] = None,
    ) -> ConceptNode:
        """Add a new concept to the graph."""
        concept = ConceptNode(
            name=name,
            description=description,
            confidence=confidence,
            metadata=metadata or {},
            source_memories=source_memories or [],
        )
        self.nodes[concept.id] = concept
        self.adjacency[concept.id] = set()
        logger.info(f"Added concept: {name} (id={concept.id})")
        return concept
    
    def get_concept(self, concept_id: str) -> Optional[ConceptNode]:
        """Retrieve a concept by ID."""
        return self.nodes.get(concept_id)
    
    def find_concept_by_name(self, name: str) -> Optional[ConceptNode]:
        """Find a concept by name."""
        for concept in self.nodes.values():
            if concept.name.lower() == name.lower():
                return concept
        return None
    
    def add_relationship(
        self,
        from_id: str,
        to_id: str,
        relationship_type: str = "related",
        weight: float = 1.0,
    ) -> bool:
        """Add a relationship between two concepts."""
        if from_id not in self.nodes or to_id not in self.nodes:
            logger.warning(f"Cannot add relationship: missing concept IDs")
            return False
        
        self.adjacency[from_id].add(to_id)
        self.adjacency[to_id].add(from_id)
        self.edge_weights[(from_id, to_id)] = weight
        self.edge_weights[(to_id, from_id)] = weight
        self.edge_types[(from_id, to_id)] = relationship_type
        self.edge_types[(to_id, from_id)] = relationship_type
        
        logger.info(f"Added relationship: {from_id} --[{relationship_type}]--> {to_id}")
        return True
    
    def get_neighbors(self, concept_id: str) -> List[ConceptNode]:
        """Get all concepts related to the given concept."""
        if concept_id not in self.adjacency:
            return []
        return [self.nodes[nid] for nid in self.adjacency[concept_id]]
    
    def get_relationship_type(self, from_id: str, to_id: str) -> Optional[str]:
        """Get the relationship type between two concepts."""
        return self.edge_types.get((from_id, to_id))
    
    def find_path(self, from_id: str, to_id: str) -> Optional[List[str]]:
        """Find shortest path between two concepts using BFS."""
        if from_id not in self.nodes or to_id not in self.nodes:
            return None
        
        if from_id == to_id:
            return [from_id]
        
        queue = [(from_id, [from_id])]
        visited = {from_id}
        
        while queue:
            current, path = queue.pop(0)
            
            for neighbor in self.adjacency[current]:
                if neighbor == to_id:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return None
    
    def find_cluster(self, concept_id: str, max_depth: int = 2) -> Set[str]:
        """Find all concepts within a certain distance of the given concept."""
        if concept_id not in self.nodes:
            return set()
        
        cluster = {concept_id}
        current_level = {concept_id}
        
        for _ in range(max_depth):
            next_level = set()
            for cid in current_level:
                next_level.update(self.adjacency[cid])
            cluster.update(next_level)
            current_level = next_level - cluster
        
        return cluster
    
    def get_concepts_by_state(self, state: ConceptState) -> List[ConceptNode]:
        """Get all concepts in a specific state."""
        return [c for c in self.nodes.values() if c.state == state]
    
    def update_concept_state(self, concept_id: str, new_state: ConceptState) -> bool:
        """Update the lifecycle state of a concept."""
        if concept_id not in self.nodes:
            return False
        
        old_state = self.nodes[concept_id].state
        self.nodes[concept_id].state = new_state
        self.nodes[concept_id].updated_at = datetime.now(timezone.utc)
        
        logger.info(f"Concept {concept_id} state: {old_state} -> {new_state}")
        return True
    
    def merge_concepts(
        self,
        primary_id: str,
        secondary_id: str,
        new_name: Optional[str] = None,
    ) -> Optional[ConceptNode]:
        """Merge two concepts into one."""
        if primary_id not in self.nodes or secondary_id not in self.nodes:
            return None
        
        primary = self.nodes[primary_id]
        secondary = self.nodes[secondary_id]
        
        # Merge source memories
        primary.source_memories.extend(secondary.source_memories)
        primary.source_memories = list(set(primary.source_memories))
        
        # Merge metadata
        primary.metadata.update(secondary.metadata)
        
        # Update name if provided
        if new_name:
            primary.name = new_name
        
        # Reassign relationships
        for neighbor_id in self.adjacency[secondary_id]:
            if neighbor_id != primary_id:
                self.add_relationship(
                    primary_id,
                    neighbor_id,
                    self.get_relationship_type(secondary_id, neighbor_id) or "related",
                    self.edge_weights.get((secondary_id, neighbor_id), 1.0),
                )
        
        # Mark secondary as merged
        secondary.state = ConceptState.MERGED
        primary.updated_at = datetime.now(timezone.utc)
        
        logger.info(f"Merged concepts: {secondary_id} -> {primary_id}")
        return primary
    
    def split_concept(
        self,
        concept_id: str,
        new_name: str,
        new_description: str,
        memories_to_transfer: List[str],
    ) -> Optional[ConceptNode]:
        """Split a concept into two."""
        if concept_id not in self.nodes:
            return None
        
        original = self.nodes[concept_id]
        
        # Create new concept
        new_concept = self.add_concept(
            name=new_name,
            description=new_description,
            confidence=original.confidence * 0.8,
            metadata=original.metadata.copy(),
            source_memories=memories_to_transfer,
        )
        
        # Remove transferred memories from original
        original.source_memories = [m for m in original.source_memories if m not in memories_to_transfer]
        
        # Mark original as refining
        original.state = ConceptState.REFINING
        original.updated_at = datetime.now(timezone.utc)
        
        logger.info(f"Split concept: {concept_id} -> {new_concept.id}")
        return new_concept
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get graph statistics."""
        return {
            "total_concepts": len(self.nodes),
            "total_relationships": len(self.edge_types) // 2,
            "emerging": len(self.get_concepts_by_state(ConceptState.EMERGING)),
            "stable": len(self.get_concepts_by_state(ConceptState.STABLE)),
            "refining": len(self.get_concepts_by_state(ConceptState.REFINING)),
            "deprecated": len(self.get_concepts_by_state(ConceptState.DEPRECATED)),
            "merged": len(self.get_concepts_by_state(ConceptState.MERGED)),
        }
