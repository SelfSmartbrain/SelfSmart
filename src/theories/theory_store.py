"""theory_store.py

Persistent storage and retrieval for theories.
Manages theory lifecycle, versioning, and access.
"""

from __future__ import annotations

import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
from pathlib import Path

from pydantic import BaseModel, Field

from src.config.logging import get_logger
from .theory_generator import Theory, TheoryType, TheoryStrength

logger = get_logger(__name__)


class TheoryEntry(BaseModel):
    """Serializable entry for theory storage."""
    id: str
    name: str
    description: str
    theory_type: str
    strength: str
    confidence: float
    conditions: List[str]
    predictions: List[str]
    evidence: List[str]
    counterexamples: List[str]
    source_concepts: List[str]
    domain: str
    created_at: str
    updated_at: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TheoryStore:
    """Persistent storage for theories."""
    
    def __init__(self, storage_path: Optional[str] = None):
        self.theories: Dict[str, Theory] = {}
        self.storage_path = Path(storage_path) if storage_path else Path(".data/theories")
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.index_path = self.storage_path / "index.json"
        self._load_index()
        logger.info(f"TheoryStore initialized with storage at {self.storage_path}")
    
    def _load_index(self):
        """Load theory index from storage."""
        if self.index_path.exists():
            try:
                with open(self.index_path, "r") as f:
                    index = json.load(f)
                    for entry_data in index.get("theories", []):
                        entry = TheoryEntry(**entry_data)
                        theory = Theory(
                            id=entry.id,
                            name=entry.name,
                            description=entry.description,
                            theory_type=TheoryType(entry.theory_type),
                            strength=TheoryStrength(entry.strength),
                            confidence=entry.confidence,
                            conditions=entry.conditions,
                            predictions=entry.predictions,
                            evidence=entry.evidence,
                            counterexamples=entry.counterexamples,
                            source_concepts=entry.source_concepts,
                            domain=entry.domain,
                            created_at=datetime.fromisoformat(entry.created_at),
                            updated_at=datetime.fromisoformat(entry.updated_at),
                            metadata=entry.metadata,
                        )
                        self.theories[theory.id] = theory
                logger.info(f"Loaded {len(self.theories)} theories from index")
            except Exception as e:
                logger.error(f"Failed to load theory index: {e}")
    
    def _save_index(self):
        """Save theory index to storage."""
        try:
            entries = [
                TheoryEntry(
                    id=t.id,
                    name=t.name,
                    description=t.description,
                    theory_type=t.theory_type.value,
                    strength=t.strength.value,
                    confidence=t.confidence,
                    conditions=t.conditions,
                    predictions=t.predictions,
                    evidence=t.evidence,
                    counterexamples=t.counterexamples,
                    source_concepts=t.source_concepts,
                    domain=t.domain,
                    created_at=t.created_at.isoformat(),
                    updated_at=t.updated_at.isoformat(),
                    metadata=t.metadata,
                )
                for t in self.theories.values()
            ]
            index = {
                "theories": [e.model_dump() for e in entries],
                "updated_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(self.index_path, "w") as f:
                json.dump(index, f, indent=2)
            logger.info("Saved theory index")
        except Exception as e:
            logger.error(f"Failed to save theory index: {e}")
    
    def store_theory(self, theory: Theory) -> Theory:
        """Store a theory in the repository."""
        self.theories[theory.id] = theory
        self._save_index()
        logger.info(f"Stored theory: {theory.name}")
        return theory
    
    def get_theory(self, theory_id: str) -> Optional[Theory]:
        """Retrieve a theory by ID."""
        return self.theories.get(theory_id)
    
    def find_theories_by_name(self, name: str) -> List[Theory]:
        """Find theories by name."""
        name_lower = name.lower()
        return [t for t in self.theories.values() if name_lower in t.name.lower()]
    
    def find_theories_by_concept(self, concept: str) -> List[Theory]:
        """Find theories involving a specific concept."""
        return [t for t in self.theories.values() if concept in t.source_concepts]
    
    def find_theories_by_domain(self, domain: str) -> List[Theory]:
        """Find theories in a specific domain."""
        return [t for t in self.theories.values() if t.domain == domain]
    
    def list_theories(
        self,
        theory_type: Optional[TheoryType] = None,
        min_confidence: float = 0.0,
        domain: Optional[str] = None,
    ) -> List[Theory]:
        """List theories with optional filters."""
        theories = list(self.theories.values())
        
        if theory_type:
            theories = [t for t in theories if t.theory_type == theory_type]
        
        if min_confidence > 0:
            theories = [t for t in theories if t.confidence >= min_confidence]
        
        if domain:
            theories = [t for t in theories if t.domain == domain]
        
        return sorted(theories, key=lambda t: t.updated_at, reverse=True)
    
    def update_theory(
        self,
        theory_id: str,
        name: Optional[str] = None,
        description: Optional[str] = None,
        confidence: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Optional[Theory]:
        """Update an existing theory."""
        theory = self.theories.get(theory_id)
        if not theory:
            return None
        
        if name is not None:
            theory.name = name
        if description is not None:
            theory.description = description
        if confidence is not None:
            theory.confidence = max(0.0, min(1.0, confidence))
        if metadata is not None:
            theory.metadata.update(metadata)
        
        theory.updated_at = datetime.now(timezone.utc)
        self._save_index()
        return theory
    
    def add_evidence(self, theory_id: str, evidence: str) -> bool:
        """Add supporting evidence to a theory."""
        theory = self.theories.get(theory_id)
        if not theory:
            return False
        
        if evidence not in theory.evidence:
            theory.evidence.append(evidence)
            theory.updated_at = datetime.now(timezone.utc)
            self._save_index()
        return True
    
    def add_counterexample(self, theory_id: str, counterexample: str) -> bool:
        """Add a counterexample to a theory."""
        theory = self.theories.get(theory_id)
        if not theory:
            return False
        
        if counterexample not in theory.counterexamples:
            theory.counterexamples.append(counterexample)
            theory.updated_at = datetime.now(timezone.utc)
            self._save_index()
        return True
    
    def delete_theory(self, theory_id: str) -> bool:
        """Delete a theory from the store."""
        if theory_id not in self.theories:
            return False
        
        del self.theories[theory_id]
        self._save_index()
        logger.info(f"Deleted theory {theory_id}")
        return True
    
    def get_top_theories(self, n: int = 10) -> List[Theory]:
        """Get top N theories by confidence."""
        return sorted(self.theories.values(), key=lambda t: t.confidence, reverse=True)[:n]
    
    def get_theories_by_strength(self, strength: TheoryStrength) -> List[Theory]:
        """Get all theories with a specific strength level."""
        return [t for t in self.theories.values() if t.strength == strength]
    
    def export_theories(self, filepath: str) -> bool:
        """Export all theories to a JSON file."""
        try:
            data = {
                "theories": [t.to_dict() for t in self.theories.values()],
                "exported_at": datetime.now(timezone.utc).isoformat(),
            }
            with open(filepath, "w") as f:
                json.dump(data, f, indent=2)
            logger.info(f"Exported theories to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Failed to export theories: {e}")
            return False
    
    def import_theories(self, filepath: str) -> int:
        """Import theories from a JSON file."""
        try:
            with open(filepath, "r") as f:
                data = json.load(f)
            
            imported = 0
            for theory_data in data.get("theories", []):
                theory = Theory(
                    id=theory_data["id"],
                    name=theory_data["name"],
                    description=theory_data["description"],
                    theory_type=TheoryType(theory_data["theory_type"]),
                    strength=TheoryStrength(theory_data["strength"]),
                    confidence=theory_data["confidence"],
                    conditions=theory_data.get("conditions", []),
                    predictions=theory_data.get("predictions", []),
                    evidence=theory_data.get("evidence", []),
                    counterexamples=theory_data.get("counterexamples", []),
                    source_concepts=theory_data.get("source_concepts", []),
                    domain=theory_data.get("domain", ""),
                    created_at=datetime.fromisoformat(theory_data["created_at"]),
                    updated_at=datetime.fromisoformat(theory_data["updated_at"]),
                    metadata=theory_data.get("metadata", {}),
                )
                self.theories[theory.id] = theory
                imported += 1
            
            self._save_index()
            logger.info(f"Imported {imported} theories from {filepath}")
            return imported
        except Exception as e:
            logger.error(f"Failed to import theories: {e}")
            return 0
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get store statistics."""
        type_counts = {}
        for theory in self.theories.values():
            type_counts[theory.theory_type.value] = type_counts.get(theory.theory_type.value, 0) + 1
        
        strength_counts = {}
        for theory in self.theories.values():
            strength_counts[theory.strength.value] = strength_counts.get(theory.strength.value, 0) + 1
        
        domain_counts = {}
        for theory in self.theories.values():
            if theory.domain:
                domain_counts[theory.domain] = domain_counts.get(theory.domain, 0) + 1
        
        return {
            "total_theories": len(self.theories),
            "by_type": type_counts,
            "by_strength": strength_counts,
            "by_domain": domain_counts,
            "average_confidence": sum(t.confidence for t in self.theories.values()) / len(self.theories) if self.theories else 0.0,
        }
