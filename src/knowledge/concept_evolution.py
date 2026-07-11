"""concept_evolution.py

Tracks the lineage and evolution of concepts over time.
Each concept is stored with a version identifier and a parent reference.
Provides methods to retrieve the history of a concept.
"""

from __future__ import annotations

from typing import List, Dict, Optional, Any
from datetime import datetime, timezone
from enum import Enum
from dataclasses import dataclass, field

from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)


class EvolutionEvent(str, Enum):
    """Types of evolution events."""
    CREATED = "created"
    MERGED = "merged"
    SPLIT = "split"
    REFINED = "refined"
    DEPRECATED = "deprecated"
    STRENGTHENED = "strengthened"
    WEAKENED = "weakened"


@dataclass
class EvolutionRecord:
    """A record of a concept evolution event."""
    concept_id: str
    event_type: EvolutionEvent
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    parent_id: Optional[str] = None
    child_ids: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "concept_id": self.concept_id,
            "event_type": self.event_type.value,
            "timestamp": self.timestamp.isoformat(),
            "parent_id": self.parent_id,
            "child_ids": self.child_ids,
            "metadata": self.metadata,
        }


class ConceptEvolution:
    """Tracks concept lineage and evolution over time."""
    
    def __init__(self):
        self.evolution_history: List[EvolutionRecord] = []
        self.concept_versions: Dict[str, List[str]] = {}  # concept_name -> list of version IDs
        self.concept_parents: Dict[str, str] = {}  # concept_id -> parent_id
        logger.info("ConceptEvolution initialized")
    
    def record_creation(self, concept_id: str, name: str, metadata: Optional[Dict[str, Any]] = None) -> EvolutionRecord:
        """Record the creation of a concept."""
        record = EvolutionRecord(
            concept_id=concept_id,
            event_type=EvolutionEvent.CREATED,
            metadata=metadata or {},
        )
        
        if name not in self.concept_versions:
            self.concept_versions[name] = []
        self.concept_versions[name].append(concept_id)
        
        self.evolution_history.append(record)
        logger.info(f"Recorded creation of concept {concept_id}")
        return record
    
    def record_merge(
        self,
        primary_id: str,
        secondary_id: str,
        new_id: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvolutionRecord:
        """Record a merge operation."""
        record = EvolutionRecord(
            concept_id=new_id,
            event_type=EvolutionEvent.MERGED,
            parent_id=primary_id,
            child_ids=[secondary_id],
            metadata=metadata or {},
        )
        
        self.concept_parents[secondary_id] = primary_id
        self.evolution_history.append(record)
        logger.info(f"Recorded merge: {secondary_id} -> {primary_id} (new: {new_id})")
        return record
    
    def record_split(
        self,
        original_id: str,
        new_ids: List[str],
        metadata: Optional[Dict[str, Any]] = None,
    ) -> EvolutionRecord:
        """Record a split operation."""
        record = EvolutionRecord(
            concept_id=original_id,
            event_type=EvolutionEvent.SPLIT,
            child_ids=new_ids,
            metadata=metadata or {},
        )
        
        for new_id in new_ids:
            self.concept_parents[new_id] = original_id
        
        self.evolution_history.append(record)
        logger.info(f"Recorded split: {original_id} -> {new_ids}")
        return record
    
    def record_refinement(self, concept_id: str, metadata: Optional[Dict[str, Any]] = None) -> EvolutionRecord:
        """Record a refinement operation."""
        record = EvolutionRecord(
            concept_id=concept_id,
            event_type=EvolutionEvent.REFINED,
            metadata=metadata or {},
        )
        
        self.evolution_history.append(record)
        logger.info(f"Recorded refinement of concept {concept_id}")
        return record
    
    def record_deprecation(self, concept_id: str, metadata: Optional[Dict[str, Any]] = None) -> EvolutionRecord:
        """Record a deprecation operation."""
        record = EvolutionRecord(
            concept_id=concept_id,
            event_type=EvolutionEvent.DEPRECATED,
            metadata=metadata or {},
        )
        
        self.evolution_history.append(record)
        logger.info(f"Recorded deprecation of concept {concept_id}")
        return record
    
    def get_lineage(self, concept_id: str) -> List[EvolutionRecord]:
        """Get the full lineage of a concept."""
        lineage = []
        
        # Find all records involving this concept
        for record in self.evolution_history:
            if record.concept_id == concept_id:
                lineage.append(record)
            if concept_id in record.child_ids:
                lineage.append(record)
            if record.parent_id == concept_id:
                lineage.append(record)
        
        return sorted(lineage, key=lambda r: r.timestamp)
    
    def get_ancestors(self, concept_id: str) -> List[str]:
        """Get all ancestor concepts."""
        ancestors = []
        current = concept_id
        
        while current in self.concept_parents:
            parent = self.concept_parents[current]
            ancestors.append(parent)
            current = parent
        
        return ancestors
    
    def get_descendants(self, concept_id: str) -> List[str]:
        """Get all descendant concepts."""
        descendants = []
        
        for record in self.evolution_history:
            if record.parent_id == concept_id:
                descendants.extend(record.child_ids)
                for child in record.child_ids:
                    descendants.extend(self.get_descendants(child))
        
        return descendants
    
    def get_version_history(self, concept_name: str) -> List[str]:
        """Get all version IDs for a concept name."""
        return self.concept_versions.get(concept_name, [])
    
    def get_evolution_timeline(self, concept_id: str) -> List[Dict[str, Any]]:
        """Get a timeline of evolution events for a concept."""
        lineage = self.get_lineage(concept_id)
        return [r.to_dict() for r in lineage]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get evolution statistics."""
        event_counts = {}
        for record in self.evolution_history:
            event_counts[record.event_type.value] = event_counts.get(record.event_type.value, 0) + 1
        
        return {
            "total_events": len(self.evolution_history),
            "by_event_type": event_counts,
            "total_concepts": len(self.concept_versions),
            "total_parent_child_links": len(self.concept_parents),
        }
