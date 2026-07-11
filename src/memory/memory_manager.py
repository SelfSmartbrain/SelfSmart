"""
Memory Manager - Unified interface for all memory systems

Provides a single entry point for:
- Working Memory (short-term, volatile)
- Episodic Memory (project runs, failures, experiments)
- Semantic Memory (facts, concepts, knowledge)
- Procedural Memory (skills, patterns, procedures)
"""

import logging
from typing import Any, Dict, List, Optional
from datetime import datetime

from .working_memory import WorkingMemory
from .episodic_memory import EpisodicMemory, store_episode
from .memory_router import MemoryRouter, AccessPattern

logger = logging.getLogger(__name__)


class InMemorySemanticMemory:
    """In-memory implementation of semantic memory for testing."""
    
    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._embeddings: Dict[str, List[float]] = {}
    
    def store(self, key: str, value: Any, confidence: float = 1.0, source: Optional[str] = None):
        self._store[key] = {"value": value, "confidence": confidence, "source": source}
    
    def retrieve(self, key: str) -> Optional[Any]:
        entry = self._store.get(key)
        return entry["value"] if entry else None
    
    def search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        # Simple keyword matching for in-memory version
        results = []
        for key, entry in self._store.items():
            if query.lower() in str(entry["value"]).lower():
                results.append({"key": key, "value": entry["value"], "confidence": entry["confidence"]})
        return results[:top_k]
    
    def get_statistics(self) -> Dict[str, Any]:
        return {"total_facts": len(self._store)}
    
    def clear(self):
        self._store.clear()


class InMemoryProceduralMemory:
    """In-memory implementation of procedural memory for testing."""
    
    def __init__(self):
        self._store: Dict[str, Dict[str, Any]] = {}
    
    def store(self, skill_name: str, procedure: Dict[str, Any], success_rate: float = 0.0):
        self._store[skill_name] = {
            "procedure": procedure,
            "success_rate": success_rate,
            "attempts": 1 if success_rate > 0 else 0,
        }
    
    def retrieve(self, skill_name: str) -> Optional[Dict[str, Any]]:
        entry = self._store.get(skill_name)
        return entry["procedure"] if entry else None
    
    def update_success_rate(self, skill_name: str, success: bool):
        if skill_name in self._store:
            entry = self._store[skill_name]
            entry["attempts"] += 1
            if success:
                successes = entry["success_rate"] * (entry["attempts"] - 1) + 1
            else:
                successes = entry["success_rate"] * (entry["attempts"] - 1)
            entry["success_rate"] = successes / entry["attempts"]
    
    def get_statistics(self) -> Dict[str, Any]:
        return {"total_skills": len(self._store)}
    
    def clear(self):
        self._store.clear()


class MemoryManager:
    """
    Unified manager for all memory systems.
    
    Routes memory operations to appropriate backends and provides
    a consistent interface for memory operations.
    """
    
    def __init__(
        self,
        working_ttl: int = 300,
        enable_routing: bool = True,
        use_in_memory_backends: bool = True,
    ):
        self.working_memory = WorkingMemory(ttl=working_ttl)
        
        # Use in-memory implementations for testing
        if use_in_memory_backends:
            self.semantic_memory = InMemorySemanticMemory()
            self.procedural_memory = InMemoryProceduralMemory()
        else:
            # Would use real database-backed implementations
            from .semantic_memory import SemanticMemory
            from .procedural_memory import ProceduralMemory
            self.semantic_memory = SemanticMemory()
            self.procedural_memory = ProceduralMemory()
        
        self.router = MemoryRouter() if enable_routing else None
        
        # Episodic memory requires a database session
        # Initialized separately when database is available
        self._episodic_session = None
        
        logger.info("MemoryManager initialized")
    
    def set_episodic_session(self, session) -> None:
        """Set the database session for episodic memory."""
        self._episodic_session = session
        logger.info("Episodic memory session configured")
    
    # Working Memory Operations
    def working_set(self, key: str, value: Any) -> None:
        """Store value in working memory."""
        self.working_memory.set(key, value)
    
    def working_get(self, key: str, default: Any = None) -> Any:
        """Retrieve value from working memory."""
        return self.working_memory.get(key, default)
    
    def working_clear(self) -> None:
        """Clear working memory."""
        self.working_memory.clear()
    
    # Episodic Memory Operations
    def store_episode(
        self,
        project_id: str,
        data: Dict[str, Any],
        outcome: Optional[str] = None,
    ) -> Optional[EpisodicMemory]:
        """Store an episode in episodic memory."""
        if not self._episodic_session:
            logger.warning("Episodic session not configured, skipping episode storage")
            return None
        
        return store_episode(self._episodic_session, project_id, data, outcome)
    
    # Semantic Memory Operations
    def semantic_store(
        self,
        key: str,
        value: Any,
        confidence: float = 1.0,
        source: Optional[str] = None,
    ) -> None:
        """Store a fact in semantic memory."""
        self.semantic_memory.store(key, value, confidence, source)
    
    def semantic_get(self, key: str) -> Optional[Any]:
        """Retrieve a fact from semantic memory."""
        return self.semantic_memory.retrieve(key)
    
    def semantic_search(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Search semantic memory for related facts."""
        return self.semantic_memory.search(query, top_k)
    
    # Procedural Memory Operations
    def procedural_store(
        self,
        skill_name: str,
        procedure: Dict[str, Any],
        success_rate: float = 0.0,
    ) -> None:
        """Store a procedure in procedural memory."""
        self.procedural_memory.store(skill_name, procedure, success_rate)
    
    def procedural_get(self, skill_name: str) -> Optional[Dict[str, Any]]:
        """Retrieve a procedure from procedural memory."""
        return self.procedural_memory.retrieve(skill_name)
    
    def procedural_update_success(self, skill_name: str, success: bool) -> None:
        """Update the success rate for a procedure."""
        self.procedural_memory.update_success_rate(skill_name, success)
    
    # Unified Memory Operations
    async def store(
        self,
        key: str,
        value: Any,
        memory_type: str = "working",
        **kwargs,
    ) -> None:
        """
        Store data in the specified memory type.
        
        Args:
            key: Storage key
            value: Value to store
            memory_type: Type of memory (working, semantic, procedural, episodic)
            **kwargs: Additional parameters for specific memory types
        """
        if memory_type == "working":
            self.working_set(key, value)
        elif memory_type == "semantic":
            self.semantic_store(key, value, **kwargs)
        elif memory_type == "procedural":
            self.procedural_store(key, value, **kwargs)
        elif memory_type == "episodic":
            if "project_id" not in kwargs:
                raise ValueError("project_id required for episodic memory")
            self.store_episode(kwargs["project_id"], {"key": key, "value": value})
        else:
            raise ValueError(f"Unknown memory type: {memory_type}")
    
    async def retrieve(
        self,
        key: str,
        memory_type: str = "working",
    ) -> Optional[Any]:
        """
        Retrieve data from the specified memory type.
        
        Args:
            key: Storage key
            memory_type: Type of memory (working, semantic, procedural)
            
        Returns:
            Retrieved value or None if not found
        """
        if memory_type == "working":
            return self.working_get(key)
        elif memory_type == "semantic":
            return self.semantic_get(key)
        elif memory_type == "procedural":
            return self.procedural_get(key)
        else:
            raise ValueError(f"Unknown memory type: {memory_type}")
    
    async def route_store(
        self,
        key: str,
        value: Any,
        access_pattern: Optional[AccessPattern] = None,
    ) -> str:
        """
        Route a store operation to the optimal backend.
        
        Args:
            key: Storage key
            value: Value to store
            access_pattern: Known access pattern (optional)
            
        Returns:
            Target backend name
        """
        if not self.router:
            logger.warning("Memory routing not enabled, using working memory")
            self.working_set(key, value)
            return "working"
        
        data = {"key": key, "value": value}
        decision = await self.router.route_store(data, access_pattern)
        
        # Route to appropriate memory based on decision
        if decision.target_backend == "redis":
            self.working_set(key, value)
        elif decision.target_backend == "postgres":
            self.semantic_store(key, value)
        elif decision.target_backend == "qdrant":
            self.semantic_store(key, value)  # Vector search
        else:
            self.working_set(key, value)
        
        return decision.target_backend
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get statistics from all memory systems."""
        stats = {
            "working_memory": {
                "entries": len(self.working_memory._store),
                "ttl": self.working_memory.ttl,
            },
            "semantic_memory": self.semantic_memory.get_statistics(),
            "procedural_memory": self.procedural_memory.get_statistics(),
        }
        
        if self.router:
            stats["routing"] = self.router.get_routing_stats()
        
        return stats
    
    def clear_all(self) -> None:
        """Clear all memory systems."""
        self.working_clear()
        self.semantic_memory.clear()
        self.procedural_memory.clear()
        logger.info("All memory systems cleared")
