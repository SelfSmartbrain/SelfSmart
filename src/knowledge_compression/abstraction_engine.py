"""abstraction_engine.py

Creates abstractions from concrete observations.
Moves from specific instances to general principles.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Set
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict

from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)


class AbstractionLevel(str, Enum):
    """Levels of abstraction."""
    CONCRETE = "concrete"  # Specific instances
    SPECIFIC = "specific"  # Narrow category
    GENERAL = "general"  # Broad category
    PRINCIPLE = "principle"  # General principle
    UNIVERSAL = "universal"  # Universal law


@dataclass
class Abstraction:
    """An abstraction from concrete observations."""
    id: str
    name: str
    description: str
    level: AbstractionLevel
    concrete_instances: List[str] = field(default_factory=list)
    general_properties: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "level": self.level.value,
            "instance_count": len(self.concrete_instances),
            "properties": self.general_properties,
            "created_at": self.created_at.isoformat(),
        }


class AbstractionEngine:
    """Creates abstractions from concrete knowledge."""
    
    def __init__(self):
        self.abstractions: Dict[str, Abstraction] = {}
        self.abstraction_hierarchy: Dict[str, List[str]] = {}  # parent -> children
        logger.info("AbstractionEngine initialized")
    
    def create_abstraction(
        self,
        instances: List[str],
        abstraction_name: str,
        level: AbstractionLevel = AbstractionLevel.GENERAL,
    ) -> Abstraction:
        """Create an abstraction from concrete instances."""
        import uuid
        
        abstraction = Abstraction(
            id=str(uuid.uuid4()),
            name=abstraction_name,
            description=f"Abstraction of {len(instances)} instances",
            level=level,
            concrete_instances=instances,
            general_properties=self._extract_properties(instances),
        )
        
        self.abstractions[abstraction.id] = abstraction
        logger.info(f"Created abstraction: {abstraction.name} (level={level.value})")
        return abstraction
    
    def _extract_properties(self, instances: List[str]) -> Dict[str, Any]:
        """Extract general properties from instances."""
        if not instances:
            return {}
        
        properties = {}
        
        # Extract common words
        all_words = []
        for instance in instances:
            all_words.extend(instance.lower().split())
        
        word_counts = defaultdict(int)
        for word in all_words:
            word_counts[word] += 1
        
        # Words that appear in >50% of instances are properties
        threshold = len(instances) * 0.5
        common_words = [word for word, count in word_counts.items() if count >= threshold]
        
        properties["common_keywords"] = common_words
        properties["instance_count"] = len(instances)
        
        # Extract numerical patterns if present
        numbers = []
        for instance in instances:
            import re
            nums = re.findall(r'\d+\.?\d*', instance)
            numbers.extend([float(n) for n in nums])
        
        if numbers:
            properties["numerical_range"] = {
                "min": min(numbers),
                "max": max(numbers),
                "avg": sum(numbers) / len(numbers),
            }
        
        return properties
    
    def abstract_to_level(
        self,
        instances: List[str],
        target_level: AbstractionLevel,
    ) -> Abstraction:
        """Abstract instances to a specific level."""
        if target_level == AbstractionLevel.CONCRETE:
            # No abstraction needed
            return self.create_abstraction(
                instances,
                f"Concrete ({len(instances)} items)",
                AbstractionLevel.CONCRETE,
            )
        
        if target_level == AbstractionLevel.SPECIFIC:
            # Group by similarity
            groups = self._group_by_similarity(instances)
            if len(groups) == 1:
                return self.create_abstraction(
                    instances,
                    f"Specific category",
                    AbstractionLevel.SPECIFIC,
                )
            else:
                # Create abstraction for largest group
                largest_group = max(groups, key=len)
                return self.create_abstraction(
                    largest_group,
                    f"Specific category ({len(largest_group)} items)",
                    AbstractionLevel.SPECIFIC,
                )
        
        if target_level == AbstractionLevel.GENERAL:
            # Create broad category
            return self.create_abstraction(
                instances,
                f"General category",
                AbstractionLevel.GENERAL,
            )
        
        if target_level == AbstractionLevel.PRINCIPLE:
            # Extract principle
            principle = self._extract_principle(instances)
            return self.create_abstraction(
                instances,
                principle,
                AbstractionLevel.PRINCIPLE,
            )
        
        if target_level == AbstractionLevel.UNIVERSAL:
            # Extract universal law
            universal = self._extract_universal(instances)
            return self.create_abstraction(
                instances,
                universal,
                AbstractionLevel.UNIVERSAL,
            )
        
        # Default to general
        return self.create_abstraction(
            instances,
            f"Abstraction",
            AbstractionLevel.GENERAL,
        )
    
    def _group_by_similarity(self, instances: List[str]) -> List[List[str]]:
        """Group instances by similarity."""
        groups = []
        used = set()
        
        for instance in instances:
            if instance in used:
                continue
            
            group = [instance]
            instance_words = set(instance.lower().split())
            
            for other in instances:
                if other in used:
                    continue
                
                other_words = set(other.lower().split())
                overlap = len(instance_words & other_words) / max(len(instance_words), len(other_words), 1)
                
                if overlap > 0.3:
                    group.append(other)
                    used.add(other)
            
            groups.append(group)
            used.add(instance)
        
        return groups
    
    def _extract_principle(self, instances: List[str]) -> str:
        """Extract a principle from instances."""
        if not instances:
            return "No principle"
        
        # Find common structure
        all_words = []
        for instance in instances:
            all_words.extend(instance.lower().split())
        
        word_counts = defaultdict(int)
        for word in all_words:
            word_counts[word] += 1
        
        # Most common words form the principle
        top_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:3]
        principle_words = [word for word, count in top_words]
        
        return f"Principle: {' '.join(principle_words).capitalize()}"
    
    def _extract_universal(self, instances: List[str]) -> str:
        """Extract a universal law from instances."""
        if not instances:
            return "No universal law"
        
        # Universal: applies to all instances
        common = self._find_common_elements(instances)
        
        if common:
            return f"Universal: {common} is always present"
        else:
            return "Universal: Patterns vary across instances"
    
    def _find_common_elements(self, instances: List[str]) -> str:
        """Find elements common to all instances."""
        if not instances:
            return ""
        
        # Find words present in all instances
        first_words = set(instances[0].lower().split())
        
        for instance in instances[1:]:
            instance_words = set(instance.lower().split())
            first_words = first_words & instance_words
        
        if first_words:
            return " ".join(list(first_words)[:3])
        
        return ""
    
    def create_hierarchy(
        self,
        concrete_instances: List[str],
    ) -> List[Abstraction]:
        """Create a hierarchy of abstractions."""
        hierarchy = []
        
        # Level 1: Concrete
        concrete = self.abstract_to_level(concrete_instances, AbstractionLevel.CONCRETE)
        hierarchy.append(concrete)
        
        # Level 2: Specific
        specific = self.abstract_to_level(concrete_instances, AbstractionLevel.SPECIFIC)
        hierarchy.append(specific)
        self.abstraction_hierarchy[concrete.id] = [specific.id]
        
        # Level 3: General
        general = self.abstract_to_level(concrete_instances, AbstractionLevel.GENERAL)
        hierarchy.append(general)
        self.abstraction_hierarchy[specific.id] = [general.id]
        
        # Level 4: Principle
        principle = self.abstract_to_level(concrete_instances, AbstractionLevel.PRINCIPLE)
        hierarchy.append(principle)
        self.abstraction_hierarchy[general.id] = [principle.id]
        
        # Level 5: Universal (if applicable)
        if len(concrete_instances) > 5:
            universal = self.abstract_to_level(concrete_instances, AbstractionLevel.UNIVERSAL)
            hierarchy.append(universal)
            self.abstraction_hierarchy[principle.id] = [universal.id]
        
        logger.info(f"Created abstraction hierarchy with {len(hierarchy)} levels")
        return hierarchy
    
    def get_abstraction(self, abstraction_id: str) -> Optional[Abstraction]:
        """Get an abstraction by ID."""
        return self.abstractions.get(abstraction_id)
    
    def get_hierarchy(self, abstraction_id: str) -> List[Abstraction]:
        """Get the hierarchy for an abstraction."""
        hierarchy = [self.abstractions.get(abstraction_id)]
        
        current = abstraction_id
        while current in self.abstraction_hierarchy:
            children = self.abstraction_hierarchy[current]
            if children:
                current = children[0]
                hierarchy.append(self.abstractions.get(current))
            else:
                break
        
        return [a for a in hierarchy if a is not None]
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get abstraction statistics."""
        level_counts = {}
        for abstraction in self.abstractions.values():
            level_counts[abstraction.level.value] = level_counts.get(abstraction.level.value, 0) + 1
        
        return {
            "total_abstractions": len(self.abstractions),
            "by_level": level_counts,
            "hierarchy_count": len(self.abstraction_hierarchy),
        }
