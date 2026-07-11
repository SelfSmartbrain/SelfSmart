"""concept_relationships.py

Defines and manages semantic relationships between concepts.
Enables rich knowledge structure through typed relationships.
"""

from __future__ import annotations

from enum import Enum
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass

from pydantic import BaseModel, Field

from src.config.logging import get_logger
from .concept_graph import ConceptGraph

logger = get_logger(__name__)


class RelationshipType(str, Enum):
    """Types of semantic relationships between concepts."""
    # Hierarchical
    IS_A = "is_a"  # "Dog IS_A Animal"
    PART_OF = "part_of"  # "Wheel PART_OF Car"
    INSTANCE_OF = "instance_of"  # "Fido INSTANCE_OF Dog"
    
    # Associative
    RELATED_TO = "related_to"  # General association
    SIMILAR_TO = "similar_to"  # "Car SIMILAR_TO Truck"
    OPPOSITE_OF = "opposite_of"  # "Hot OPPOSITE_OF Cold"
    
    # Causal
    CAUSES = "causes"  # "Fire CAUSES Smoke"
    CAUSED_BY = "caused_by"  # "Smoke CAUSED_BY Fire"
    ENABLES = "enables"  # "Key ENABLES Lock"
    REQUIRES = "requires"  "Lock REQUIRES Key"
    
    # Temporal
    PRECEDES = "precedes"  # "Breakfast PRECEDES Lunch"
    FOLLOWS = "follows"  # "Lunch FOLLOWS Breakfast"
    SIMULTANEOUS_WITH = "simultaneous_with"
    
    # Spatial
    LOCATED_AT = "located_at"  # "Paris LOCATED_AT France"
    CONTAINS = "contains"  # "France CONTAINS Paris"
    NEAR = "near"  # "Paris NEAR London"
    
    # Functional
    USED_FOR = "used_for"  # "Hammer USED_FOR Nailing"
    HAS_PROPERTY = "has_property"  # "Fire HAS_PROPERTY Hot"
    MEASURED_BY = "measured_by"  # "Temperature MEASURED_BY Thermometer"
    
    # Knowledge
    DERIVED_FROM = "derived_from"  # Concept derived from another
    GENERALIZES = "generalizes"  # "Infrastructure Reliability GENERALIZES API Timeout"
    SPECIALIZES = "specializes"  # "API Timeout SPECIALIZES Infrastructure Reliability"


@dataclass
class Relationship:
    """A relationship between two concepts."""
    from_id: str
    to_id: str
    type: RelationshipType
    weight: float = 1.0
    metadata: Dict = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}


class ConceptRelationships:
    """Manages semantic relationships in the concept graph."""
    
    def __init__(self, graph: ConceptGraph):
        self.graph = graph
        self.relationship_index: Dict[RelationshipType, Set[Tuple[str, str]]] = {}
        for rel_type in RelationshipType:
            self.relationship_index[rel_type] = set()
        logger.info("ConceptRelationships initialized")
    
    def add_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: RelationshipType,
        weight: float = 1.0,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """Add a typed relationship between concepts."""
        if not self.graph.get_concept(from_id) or not self.graph.get_concept(to_id):
            logger.warning(f"Cannot add relationship: missing concept IDs")
            return False
        
        success = self.graph.add_relationship(
            from_id, to_id, rel_type.value, weight
        )
        
        if success:
            self.relationship_index[rel_type].add((from_id, to_id))
            logger.info(f"Added {rel_type.value}: {from_id} -> {to_id}")
        
        return success
    
    def get_relationships(
        self,
        concept_id: str,
        rel_type: Optional[RelationshipType] = None,
    ) -> List[Tuple[str, str, float]]:
        """Get relationships for a concept, optionally filtered by type."""
        relationships = []
        
        for neighbor_id in self.graph.adjacency.get(concept_id, set()):
            edge_type = self.graph.get_relationship_type(concept_id, neighbor_id)
            if rel_type is None or edge_type == rel_type.value:
                weight = self.graph.edge_weights.get((concept_id, neighbor_id), 1.0)
                relationships.append((neighbor_id, edge_type, weight))
        
        return relationships
    
    def get_by_type(self, rel_type: RelationshipType) -> List[Tuple[str, str]]:
        """Get all relationships of a specific type."""
        return list(self.relationship_index[rel_type])
    
    def find_transitive_relationship(
        self,
        from_id: str,
        to_id: str,
        rel_type: RelationshipType,
        max_depth: int = 3,
    ) -> Optional[List[str]]:
        """Find transitive relationship path of a specific type."""
        if from_id not in self.graph.nodes or to_id not in self.graph.nodes:
            return None
        
        if from_id == to_id:
            return [from_id]
        
        queue = [(from_id, [from_id])]
        visited = {from_id}
        
        while queue:
            current, path = queue.pop(0)
            
            if len(path) > max_depth:
                continue
            
            for neighbor_id in self.graph.adjacency[current]:
                edge_type = self.graph.get_relationship_type(current, neighbor_id)
                
                if edge_type == rel_type.value:
                    if neighbor_id == to_id:
                        return path + [neighbor_id]
                    
                    if neighbor_id not in visited:
                        visited.add(neighbor_id)
                        queue.append((neighbor_id, path + [neighbor_id]))
        
        return None
    
    def get_hierarchy(self, concept_id: str) -> Dict[str, List[str]]:
        """Get hierarchical relationships (parents and children)."""
        parents = []
        children = []
        
        for neighbor_id, rel_type, _ in self.get_relationships(concept_id):
            if rel_type == RelationshipType.IS_A.value:
                parents.append(neighbor_id)
            elif rel_type == RelationshipType.PART_OF.value:
                parents.append(neighbor_id)
        
        # Check reverse relationships for children
        for other_id in self.graph.nodes:
            if other_id == concept_id:
                continue
            for neighbor_id, rel_type, _ in self.get_relationships(other_id):
                if neighbor_id == concept_id:
                    if rel_type == RelationshipType.IS_A.value:
                        children.append(other_id)
                    elif rel_type == RelationshipType.PART_OF.value:
                        children.append(other_id)
        
        return {"parents": parents, "children": children}
    
    def get_causal_chain(self, concept_id: str) -> List[str]:
        """Get causal chain starting from a concept."""
        chain = [concept_id]
        current = concept_id
        
        while True:
            causes = []
            for neighbor_id, rel_type, _ in self.get_relationships(current):
                if rel_type == RelationshipType.CAUSES.value:
                    causes.append(neighbor_id)
            
            if not causes:
                break
            
            # Pick the strongest cause
            current = max(
                causes,
                key=lambda cid: self.graph.edge_weights.get((current, cid), 0.0),
            )
            chain.append(current)
            
            if len(chain) > 10:  # Prevent infinite loops
                break
        
        return chain
    
    def infer_relationship(
        self,
        from_id: str,
        to_id: str,
    ) -> Optional[RelationshipType]:
        """Infer potential relationship type based on existing patterns."""
        # Check if there's already a direct relationship
        existing = self.graph.get_relationship_type(from_id, to_id)
        if existing:
            return RelationshipType(existing)
        
        # Check for transitive IS_A relationships
        if self.find_transitive_relationship(
            from_id, to_id, RelationshipType.IS_A, max_depth=2
        ):
            return RelationshipType.RELATED_TO
        
        # Check if they share common neighbors
        from_neighbors = self.graph.adjacency.get(from_id, set())
        to_neighbors = self.graph.adjacency.get(to_id, set())
        common = from_neighbors & to_neighbors
        
        if common:
            return RelationshipType.RELATED_TO
        
        return None
    
    def suggest_relationships(
        self,
        concept_id: str,
        limit: int = 5,
    ) -> List[Tuple[str, RelationshipType, float]]:
        """Suggest potential relationships based on graph structure."""
        suggestions = []
        concept = self.graph.get_concept(concept_id)
        
        if not concept:
            return suggestions
        
        # Find concepts that share source memories
        for other_id, other_concept in self.graph.nodes.items():
            if other_id == concept_id:
                continue
            
            # Check for shared memories
            shared_memories = set(concept.source_memories) & set(other_concept.source_memories)
            if shared_memories:
                confidence = len(shared_memories) / max(len(concept.source_memories), 1)
                suggestions.append((other_id, RelationshipType.RELATED_TO, confidence))
        
        # Sort by confidence
        suggestions.sort(key=lambda x: x[2], reverse=True)
        return suggestions[:limit]
    
    def get_statistics(self) -> Dict[str, int]:
        """Get relationship statistics."""
        stats = {rel_type.value: 0 for rel_type in RelationshipType}
        
        for (from_id, to_id), rel_type in self.graph.edge_types.items():
            if from_id < to_id:  # Count each relationship once
                stats[rel_type] = stats.get(rel_type, 0) + 1
        
        return stats
