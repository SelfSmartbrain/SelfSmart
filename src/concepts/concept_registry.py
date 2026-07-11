"""concept_registry.py

Central registry for managing concept lifecycle, persistence,
and retrieval across the knowledge evolution system.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from src.config.logging import get_logger
from .concept_graph import ConceptGraph, ConceptNode, ConceptState

logger = get_logger(__name__)


class ConceptEntry(BaseModel):
    """Serializable entry for concept storage."""
    id: str
    name: str
    description: str
    state: str
    confidence: float
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    source_memories: List[str] = Field(default_factory=list)


class ConceptRegistry:
    """Registry for managing concept persistence and lifecycle."""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.graph = ConceptGraph()
        self.storage_path = Path(storage_path) if storage_path else Path(".data/concepts")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.index_path = self.storage_path / "index.json"
        self._load_index()
        logger.info(f"ConceptRegistry initialized with storage at {self.storage_path}")
    
    def _load_index(self):
        """Load concept index from storage."""
        if self.index_path.exists():
            try:
                with open(self.index_path, "r") as f:
                    index = json.load(f)
                    for entry_data in index.get("concepts", []):
                        entry = ConceptEntry(**entry_data)
                        concept = ConceptNode(
                            id=entry.id,
                            name=entry.name,
                            description=entry.description,
                            state=ConceptState(entry.state),
                            confidence=entry.confidence,
                            created_at=datetime.fromisoformat(entry.created_at),
                            updated_at=datetime.fromisoformat(entry.updated_at),
                            metadata=entry.metadata,
                            source_memories=entry.source_memories,
                        )
                        self.graph.nodes[concept.id] = concept
                        self.graph.adjacency[concept.id] = set()
                logger.info(f"Loaded {len(self.graph.nodes)} concepts from index")
            except Exception as e:
                logger.error(f"Failed to load concept index: {e}")
    
    def _save_index(self):
        """Save concept index to storage."""
        try:
            entries = [
                ConceptEntry(
                    id=c.id,
                    name=c.name,
                    description=c.description,
                    state=c.state.value,
                    confidence=c.confidence,
                    created_at=c.created_at.isoformat(),
                    updated_at=c.updated_at.isoformat(),
                    metadata=c.metadata,
                    source_memories=c.source_memories,
                )
                for c in self.graph.nodes.values()
            ]
            index = {
                "concepts": [e.model_dump() for e in entries],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(self.index_path, "w") as f:
                json.dump(index, f, indent=2)
            logger.info("Saved concept index")
        except Exception as e:
            logger.error(f"Failed to save concept index: {e}")
    
    def register_concept(
        self,
        name: str,
        description: str = "",
        confidence: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
        source_memories: Optional[List[str]] = None,
    ) -> ConceptNode:
        """Register a new concept."""
        concept = self.graph.add_concept(
            name=name,
            description=description,
            confidence=confidence,
            metadata=metadata,
            source_memories=source_memories,
        )
        self._save_index()
        return concept
    
    def get_concept(self, concept_id: str) -> Optional[ConceptNode]:
        """Retrieve a concept by ID."""
        return self.graph.get_concept(concept_id)
    
    def find_concept(self, name: str) -> Optional[ConceptNode]:
        """Find a concept by name."""
        return self.graph.find_concept_by_name(name)
    
    def search_concepts(self, query: str, limit: int = 10) -> List[ConceptNode]:
        """Search concepts by name or description."""
        query_lower = query.lower()
        results = []
        for concept in self.graph.nodes.values():
            if query_lower in concept.name.lower() or query_lower in concept.description.lower():
                results.append(concept)
                if len(results) >= limit:
                    break
        return results
    
    def list_concepts(
        self,
        state: Optional[ConceptState] = None,
        min_confidence: float = 0.0,
    ) -> List[ConceptNode]:
        """List concepts with optional filters."""
        concepts = list(self.graph.nodes.values())
        
        if state:
            concepts = [c for c in concepts if c.state == state]
        
        if min_confidence > 0:
            concepts = [c for c in concepts if c.confidence >= min_confidence]
        
        return sorted(concepts, key=lambda c:c.updated_at, reverse=True)
    
    def update_concept(
        self,
        concept_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        confidence: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[ConceptNode]:
        """Update an existing concept."""
        concept = self.graph.get_concept(concept_id)
        if not concept:
            return None
        
        if name is not None:
            concept.name = name
        if description is not None:
            concept.description = description
        if confidence is not None:
            concept.confidence = max(0.0, min(1.0, confidence))
        if metadata is not None:
            concept.metadata.update(metadata)
        
        concept.updated_at = datetime.now(timezone.utc)
        self._save_index()
        return concept
    
    def set_concept_state(self, concept_id: str, state: ConceptState) -> bool:
        """Set the lifecycle state of a concept."""
        success = self.graph.update_concept_state(concept_id, state)
        if success:
            self._save_index()
        return success
    
    def add_source_memory(self, concept_id: str, memory_id: str) -> bool:
        """Add a source memory to a concept."""
        concept = self.graph.get_concept(concept_id)
        if not concept:
            return False
        
        if memory_id not in concept.source_memories:
            concept.source_memories.append(memory_id)
            concept.updated_at = datetime.now(timezone.utc)
            self._save_index()
        return True
    
    def get_concepts_by_memory(self, memory_id: str) -> List[ConceptNode]:
        """Get all concepts derived from a specific memory."""
        return [
            c for c in self.graph.nodes.values()
            if memory_id in c.source_memories
        ]
    
    def delete_concept(self, concept_id: str) -> bool:
        """Delete a concept from the registry."""
        if concept_id not in self.graph.nodes:
            return False
        
        del self.graph.nodes[concept_id]
        if concept_id in self.graph.adjacency:
            del self.graph.adjacency[concept_id]
        
        # Remove from other adjacencies
        for adj_set in self.graph.adjacency.values():
            adj_set.discard(concept_id)
        
        # Remove edges
        edges_to_remove = [k for k in self.graph.edge_weights if concept_id in k]
        for edge in edges_to_remove:
            del self.graph.edge_weights[edge]
            del self.graph.edge_types[edge]
        
        self._save_index()
        logger.info(f"Deleted concept {concept_id}")
        return True
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get registry statistics."""
        return self.graph.get_statistics()
    
    def export_concepts(self, filepath: str) -> bool:
        """Export all concepts to a JSON file."""
        try:
            data = {
                "concepts": [
                    c.to_dict() for c in self.graph.nodes.values()
                ],
                "relationships": [
                    {
                        "from_id": k[0],
                        "to_id": k[1],
                        "type": v,
                        "weight": self.graph.edge_weights.get(k, 1.0),
                    }
                    for k, v in self.graph.edge_types.items()
                    if k[0] < k[1]  # Avoid duplicates
                ],
                "exported_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Exported concepts to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to export concepts: {e}")
            return False
