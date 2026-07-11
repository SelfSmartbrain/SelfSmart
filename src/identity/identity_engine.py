"""
Identity Engine - Manages long-term identity and self-awareness

The IdentityEngine is responsible for:
- Maintaining persistent identity
- Tracking capabilities and skills
- Managing self-knowledge
- Identity evolution over time
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class IdentityState(Enum):
    """States of identity"""
    FORMING = "forming"
    STABLE = "stable"
    EVOLVING = "evolving"
    DEGRADING = "degrading"


@dataclass
class Identity:
    """The identity of ModelX"""
    identity_id: str
    name: str
    version: str
    state: IdentityState = IdentityState.FORMING
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    last_updated: float = field(default_factory=lambda: datetime.now().timestamp())
    core_values: List[str] = field(default_factory=list)
    principles: List[str] = field(default_factory=list)
    personality_traits: Dict[str, float] = field(default_factory=dict)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Skill:
    """A skill or capability"""
    skill_id: str
    name: str
    category: str
    proficiency: float  # 0.0 to 1.0
    experience: float = 0.0
    last_used: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)


class IdentityEngine:
    """
    Engine for managing long-term identity.
    
    Provides:
    - Persistent identity maintenance
    - Capability tracking
    - Self-knowledge management
    - Identity evolution
    """
    
    def __init__(self):
        self._identity: Optional[Identity] = None
        self._skills: Dict[str, Skill] = {}
        self._knowledge_domains: Set[str] = set()
        
        # Identity history
        self._identity_history: List[Dict[str, Any]] = []
        
        # Statistics
        self._identity_updates = 0
        self._skill_improvements = 0
    
    async def initialize(self) -> None:
        """Initialize the identity engine"""
        logger.info("IdentityEngine initialized")
        
        # Create initial identity if none exists
        if self._identity is None:
            await self._create_initial_identity()
    
    async def _create_initial_identity(self) -> None:
        """Create the initial identity"""
        self._identity = Identity(
            identity_id="modelx_identity",
            name="ModelX",
            version="1.0",
            state=IdentityState.FORMING,
            core_values=[
                "truth-seeking",
                "helpfulness",
                "safety",
                "continuous-improvement",
            ],
            principles=[
                "Always prioritize safety",
                "Seek truth and accuracy",
                "Help users achieve their goals",
                "Learn from experience",
                "Respect user autonomy",
            ],
            personality_traits={
                "curiosity": 0.8,
                "caution": 0.7,
                "helpfulness": 0.9,
                "creativity": 0.6,
            },
        )
        
        logger.info("Created initial identity")
    
    async def get_identity(self) -> Identity:
        """Get current identity"""
        if self._identity is None:
            await self._create_initial_identity()
        return self._identity
    
    async def update_identity(
        self,
        core_values: Optional[List[str]] = None,
        principles: Optional[List[str]] = None,
        personality_traits: Optional[Dict[str, float]] = None,
    ) -> bool:
        """
        Update identity attributes.
        
        Args:
            core_values: New core values
            principles: New principles
            personality_traits: New personality traits
            
        Returns:
            True if updated successfully
        """
        if self._identity is None:
            await self._create_initial_identity()
        
        if core_values:
            self._identity.core_values = core_values
        
        if principles:
            self._identity.principles = principles
        
        if personality_traits:
            self._identity.personality_traits.update(personality_traits)
        
        self._identity.last_updated = datetime.now().timestamp()
        self._identity.state = IdentityState.EVOLVING
        self._identity_updates += 1
        
        # Record history
        self._identity_history.append({
            "timestamp": self._identity.last_updated,
            "state": self._identity.state.value,
        })
        
        logger.info("Updated identity")
        return True
    
    async def add_skill(
        self,
        name: str,
        category: str,
        proficiency: float = 0.5,
    ) -> Skill:
        """
        Add or update a skill.
        
        Args:
            name: Skill name
            category: Skill category
            proficiency: Initial proficiency
            
        Returns:
            Skill object
        """
        skill_id = f"skill_{name.lower().replace(' ', '_')}"
        
        if skill_id in self._skills:
            # Update existing skill
            skill = self._skills[skill_id]
            skill.proficiency = max(skill.proficiency, proficiency)
            skill.last_used = datetime.now().timestamp()
        else:
            # Create new skill
            skill = Skill(
                skill_id=skill_id,
                name=name,
                category=category,
                proficiency=proficiency,
            )
            self._skills[skill_id] = skill
        
        logger.debug(f"Added/updated skill: {name} (proficiency: {skill.proficiency:.2f})")
        return skill
    
    async def improve_skill(
        self,
        skill_id: str,
        delta: float,
    ) -> bool:
        """
        Improve a skill's proficiency.
        
        Args:
            skill_id: Skill identifier
            delta: Proficiency increase
            
        Returns:
            True if improved successfully
        """
        if skill_id not in self._skills:
            logger.warning(f"Skill {skill_id} not found")
            return False
        
        skill = self._skills[skill_id]
        skill.proficiency = min(1.0, skill.proficiency + delta)
        skill.experience += delta
        skill.last_used = datetime.now().timestamp()
        
        self._skill_improvements += 1
        
        logger.debug(f"Improved skill {skill_id} to {skill.proficiency:.2f}")
        return True
    
    async def use_skill(self, skill_id: str) -> bool:
        """
        Record usage of a skill.
        
        Args:
            skill_id: Skill identifier
            
        Returns:
            True if recorded successfully
        """
        if skill_id not in self._skills:
            logger.warning(f"Skill {skill_id} not found")
            return False
        
        skill = self._skills[skill_id]
        skill.last_used = datetime.now().timestamp()
        skill.experience += 0.01  # Small experience gain
        
        return True
    
    def get_skill(self, skill_id: str) -> Optional[Skill]:
        """Get a skill by ID"""
        return self._skills.get(skill_id)
    
    def get_skills_by_category(self, category: str) -> List[Skill]:
        """Get all skills in a category"""
        return [skill for skill in self._skills.values() if skill.category == category]
    
    def get_top_skills(self, limit: int = 10) -> List[Skill]:
        """Get top skills by proficiency"""
        skills = list(self._skills.values())
        skills.sort(key=lambda s: s.proficiency, reverse=True)
        return skills[:limit]
    
    async def add_knowledge_domain(self, domain: str) -> None:
        """Add a knowledge domain"""
        self._knowledge_domains.add(domain)
        logger.debug(f"Added knowledge domain: {domain}")
    
    def has_knowledge_domain(self, domain: str) -> bool:
        """Check if has knowledge in a domain"""
        return domain in self._knowledge_domains
    
    def get_knowledge_domains(self) -> Set[str]:
        """Get all knowledge domains"""
        return self._knowledge_domains.copy()
    
    async def reflect_on_identity(self) -> Dict[str, Any]:
        """
        Reflect on current identity state.
        
        Returns:
            Reflection summary
        """
        if self._identity is None:
            await self._create_initial_identity()
        
        reflection = {
            "identity_state": self._identity.state.value,
            "total_skills": len(self._skills),
            "average_proficiency": (
                sum(s.proficiency for s in self._skills.values()) / len(self._skills)
                if self._skills else 0.0
            ),
            "knowledge_domains": len(self._knowledge_domains),
            "identity_updates": self._identity_updates,
            "skill_improvements": self._skill_improvements,
            "core_values": self._identity.core_values,
            "top_skills": [s.name for s in self.get_top_skills(5)],
        }
        
        return reflection
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get identity engine metrics"""
        return {
            "identity_updates": self._identity_updates,
            "skill_improvements": self._skill_improvements,
            "total_skills": len(self._skills),
            "knowledge_domains": len(self._knowledge_domains),
            "identity_state": self._identity.state.value if self._identity else None,
            "history_size": len(self._identity_history),
        }
