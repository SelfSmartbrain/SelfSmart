"""decision_archive.py

Phase 16I: Decision Archive

Archives historic decisions for long-term analysis.
Stores:
- Historic decisions
- Historic mistakes
- Historic successes
- Lessons learned
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from enum import Enum
from dataclasses import dataclass, field

from src.config.logging import get_logger

logger = get_logger(__name__)


class ArchiveCategory(str, Enum):
    """Categories of archived decisions."""
    SUCCESS = "success"
    FAILURE = "failure"
    MISTAKE = "mistake"
    LEARNED = "learned"
    REFERENCE = "reference"


@dataclass
class ArchivedDecision:
    """An archived decision."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    original_decision_id: str = ""
    category: ArchiveCategory = ArchiveCategory.REFERENCE
    decision_data: Dict[str, Any] = field(default_factory=dict)
    outcome: Dict[str, Any] = field(default_factory=dict)
    lessons_learned: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)
    archived_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    archived_by: str = ""
    reason: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.archived_id,
            "original_decision_id": self.original_decision_id,
            "category": self.category.value,
            "decision_data": self.decision_data,
            "outcome": self.outcome,
            "lessons_learned": self.lessons_learned,
            "tags": self.tags,
            "archived_at": self.archived_at.isoformat(),
            "archived_by": self.archived_by,
            "reason": self.reason,
            "metadata": self.metadata,
        }


class DecisionArchive:
    """Archive for historic decisions."""
    
    def __init__(self):
        self.archive: Dict[str, ArchivedDecision] = {}
        self.archive_by_category: Dict[str, List[str]] = {}  # category -> archive_ids
        self.archive_by_tag: Dict[str, List[str]] = {}  # tag -> archive_ids
        logger.info("DecisionArchive initialized")
    
    def archive_decision(
        self,
        original_decision_id: str,
        decision_data: Dict[str, Any],
        outcome: Dict[str, Any],
        category: ArchiveCategory,
        lessons_learned: Optional[List[str]] = None,
        tags: Optional[List[str]] = None,
        archived_by: str = "",
        reason: str = "",
    ) -> ArchivedDecision:
        """Archive a decision."""
        archived = ArchivedDecision(
            original_decision_id=original_decision_id,
            decision_data=decision_data,
            outcome=outcome,
            category=category,
            lessons_learned=lessons_learned or [],
            tags=tags or [],
            archived_by=archived_by,
            reason=reason,
        )
        
        self.archive[archived.id] = archived
        
        # Index by category
        if category.value not in self.archive_by_category:
            self.archive_by_category[category.value] = []
        self.archive_by_category[category.value].append(archived.id)
        
        # Index by tags
        for tag in archived.tags:
            if tag not in self.archive_by_tag:
                self.archive_by_tag[tag] = []
            self.archive_by_tag[tag].append(archived.id)
        
        logger.info(f"Archived decision {original_decision_id} as {category.value}")
        
        return archived
    
    def get_archived(self, archive_id: str) -> Optional[ArchivedDecision]:
        """Get an archived decision by ID."""
        return self.archive.get(archive_id)
    
    def get_by_original_id(self, original_decision_id: str) -> Optional[ArchivedDecision]:
        """Get archived decision by original decision ID."""
        for archived in self.archive.values():
            if archived.original_decision_id == original_decision_id:
                return archived
        return None
    
    def get_by_category(self, category: ArchiveCategory) -> List[ArchivedDecision]:
        """Get all archived decisions of a category."""
        archive_ids = self.archive_by_category.get(category.value, [])
        return [self.archive[aid] for aid in archive_ids if aid in self.archive]
    
    def get_by_tag(self, tag: str) -> List[ArchivedDecision]:
        """Get all archived decisions with a tag."""
        archive_ids = self.archive_by_tag.get(tag, [])
        return [self.archive[aid] for aid in archive_ids if aid in self.archive]
    
    def search_archive(self, query: str) -> List[ArchivedDecision]:
        """Search the archive."""
        query_lower = query.lower()
        results = []
        
        for archived in self.archive.values():
            # Search in decision data
            if query_lower in str(archived.decision_data).lower():
                results.append(archived)
                continue
            
            # Search in lessons learned
            if any(query_lower in lesson.lower() for lesson in archived.lessons_learned):
                results.append(archived)
                continue
            
            # Search in tags
            if any(query_lower in tag.lower() for tag in archived.tags):
                results.append(archived)
                continue
        
        return results
    
    def get_similar_decisions(
        self,
        decision_data: Dict[str, Any],
        limit: int = 5,
    ) -> List[ArchivedDecision]:
        """Find similar archived decisions."""
        # Simple similarity based on query matching
        query = decision_data.get("query", "").lower()
        
        similar = []
        for archived in self.archive.values():
            archived_query = archived.decision_data.get("query", "").lower()
            
            # Check for word overlap
            query_words = set(query.split())
            archived_words = set(archived_query.split())
            
            overlap = query_words & archived_words
            
            if overlap:
                similarity_score = len(overlap) / max(len(query_words), len(archived_words))
                if similarity_score > 0.3:
                    similar.append((archived, similarity_score))
        
        # Sort by similarity and return top N
        similar.sort(key=lambda x: x[1], reverse=True)
        return [a for a, s in similar[:limit]]
    
    def add_lesson(self, archive_id: str, lesson: str) -> bool:
        """Add a lesson learned to an archived decision."""
        archived = self.archive.get(archive_id)
        if archived:
            if lesson not in archived.lessons_learned:
                archived.lessons_learned.append(lesson)
                logger.info(f"Added lesson to archive {archive_id}")
            return True
        return False
    
    def get_lessons_by_category(self, category: ArchiveCategory) -> List[str]:
        """Get all lessons learned from a category."""
        archived_decisions = self.get_by_category(category)
        lessons = []
        
        for archived in archived_decisions:
            lessons.extend(archived.lessons_learned)
        
        return lessons
    
    def get_archive_statistics(self) -> Dict[str, Any]:
        """Get statistics about the archive."""
        total_archived = len(self.archive)
        
        by_category = {
            category.value: len(self.get_by_category(category))
            for category in ArchiveCategory
        }
        
        total_lessons = sum(len(a.lessons_learned) for a in self.archive.values())
        
        return {
            "total_archived": total_archived,
            "by_category": by_category,
            "total_lessons_learned": total_lessons,
            "unique_tags": len(self.archive_by_tag),
        }
