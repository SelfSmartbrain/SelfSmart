"""
Memory Router - Intelligent routing of memory operations

The MemoryRouter determines:
- Which memory backend to use for a given operation
- When to migrate data between backends
- Optimal storage strategies based on access patterns
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict


logger = logging.getLogger(__name__)


class AccessPattern(Enum):
    """Memory access patterns"""
    FREQUENT = "frequent"  # Accessed frequently
    RECENT = "recent"      # Accessed recently
    LARGE = "large"        # Large data
    STRUCTURED = "structured"  # Relational data
    VECTOR = "vector"      # Vector/embedding data
    TEMPORAL = "temporal"  # Time-series data


@dataclass
class RoutingDecision:
    """A routing decision for memory operations"""
    target_backend: str
    reason: str
    confidence: float
    alternative_backends: List[str] = field(default_factory=list)


class MemoryRouter:
    """
    Routes memory operations to optimal backends.
    
    Analyzes access patterns and data characteristics to determine
    the best storage backend for each memory operation.
    """
    
    def __init__(self):
        # Access pattern tracking
        self._access_history: Dict[str, List[Tuple[float, str]]] = defaultdict(list)
        self._access_patterns: Dict[str, AccessPattern] = {}
        
        # Backend capabilities
        self._backend_capabilities: Dict[str, Set[AccessPattern]] = {
            "redis": {AccessPattern.FREQUENT, AccessPattern.RECENT},
            "postgres": {AccessPattern.STRUCTURED, AccessPattern.TEMPORAL},
            "qdrant": {AccessPattern.VECTOR},
            "neo4j": {AccessPattern.STRUCTURED},
        }
        
        # Routing statistics
        self._routing_decisions: Dict[str, int] = defaultdict(int)
        self._migration_count = 0
    
    async def route_store(
        self,
        data: Dict[str, Any],
        access_pattern: Optional[AccessPattern] = None,
    ) -> RoutingDecision:
        """
        Determine the best backend for storing data.
        
        Args:
            data: Data to store
            access_pattern: Known access pattern (optional)
            
        Returns:
            Routing decision
        """
        # Auto-detect access pattern if not provided
        if access_pattern is None:
            access_pattern = self._detect_access_pattern(data)
        
        # Find best backend
        backend = self._find_best_backend(access_pattern)
        
        decision = RoutingDecision(
            target_backend=backend,
            reason=f"Optimal for {access_pattern.value} pattern",
            confidence=0.8,
            alternative_backends=self._get_alternative_backends(access_pattern, backend),
        )
        
        self._routing_decisions[backend] += 1
        
        logger.debug(f"Routed store to {backend} (pattern: {access_pattern.value})")
        return decision
    
    async def route_query(
        self,
        query: str,
        query_type: str = "text",
    ) -> RoutingDecision:
        """
        Determine the best backend for querying.
        
        Args:
            query: Query string
            query_type: Type of query (text, vector, structural)
            
        Returns:
            Routing decision
        """
        # Determine query type
        if query_type == "vector":
            backend = "qdrant"
            reason = "Vector similarity search"
        elif query_type == "structural":
            backend = "neo4j"
            reason = "Graph/relational query"
        elif query_type == "recent":
            backend = "redis"
            reason = "Recent/frequent access"
        else:
            backend = "postgres"
            reason = "General text search"
        
        decision = RoutingDecision(
            target_backend=backend,
            reason=reason,
            confidence=0.9,
        )
        
        self._routing_decisions[backend] += 1
        
        logger.debug(f"Routed query to {backend} (type: {query_type})")
        return decision
    
    def _detect_access_pattern(self, data: Dict[str, Any]) -> AccessPattern:
        """Detect access pattern from data characteristics"""
        # Check for vector data
        if "embedding" in data or "vector" in data:
            return AccessPattern.VECTOR
        
        # Check for structured/relational data
        if "relations" in data or "edges" in data or "nodes" in data:
            return AccessPattern.STRUCTURED
        
        # Check for temporal data
        if "timestamp" in data or "time_series" in data:
            return AccessPattern.TEMPORAL
        
        # Check for large data
        data_size = len(str(data))
        if data_size > 10000:
            return AccessPattern.LARGE
        
        # Default to recent pattern
        return AccessPattern.RECENT
    
    def _find_best_backend(self, pattern: AccessPattern) -> str:
        """Find the best backend for a given pattern"""
        # Score each backend
        scores = {}
        
        for backend, capabilities in self._backend_capabilities.items():
            if pattern in capabilities:
                scores[backend] = 1.0
            else:
                scores[backend] = 0.0
        
        # Return highest-scoring backend
        if scores:
            return max(scores, key=scores.get)
        
        return "postgres"  # Default fallback
    
    def _get_alternative_backends(
        self,
        pattern: AccessPattern,
        primary: str,
    ) -> List[str]:
        """Get alternative backends for a pattern"""
        alternatives = []
        
        for backend, capabilities in self._backend_capabilities.items():
            if backend != primary and pattern in capabilities:
                alternatives.append(backend)
        
        return alternatives
    
    def track_access(self, key: str, backend: str) -> None:
        """
        Track memory access for pattern learning.
        
        Args:
            key: Memory key
            backend: Backend accessed
        """
        now = datetime.now().timestamp()
        self._access_history[key].append((now, backend))
        
        # Keep only recent history
        cutoff = now - 3600  # 1 hour
        self._access_history[key] = [
            (t, b) for t, b in self._access_history[key] if t > cutoff
        ]
        
        # Update access pattern
        self._update_access_pattern(key)
    
    def _update_access_pattern(self, key: str) -> None:
        """Update access pattern based on history"""
        history = self._access_history.get(key, [])
        
        if not history:
            return
        
        # Count accesses in last hour
        now = datetime.now().timestamp()
        recent_count = sum(1 for t, _ in history if now - t < 3600)
        
        if recent_count > 10:
            self._access_patterns[key] = AccessPattern.FREQUENT
        elif recent_count > 0:
            self._access_patterns[key] = AccessPattern.RECENT
    
    async def should_migrate(
        self,
        key: str,
        current_backend: str,
    ) -> Optional[str]:
        """
        Determine if data should be migrated to a different backend.
        
        Args:
            key: Memory key
            current_backend: Current backend
            
        Returns:
            Target backend if migration is recommended, None otherwise
        """
        pattern = self._access_patterns.get(key)
        
        if not pattern:
            return None
        
        # Check if current backend is optimal
        optimal = self._find_best_backend(pattern)
        
        if optimal != current_backend:
            self._migration_count += 1
            logger.info(f"Recommended migration: {current_backend} -> {optimal}")
            return optimal
        
        return None
    
    def get_routing_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        return {
            "routing_decisions": dict(self._routing_decisions),
            "migration_count": self._migration_count,
            "tracked_keys": len(self._access_history),
            "detected_patterns": {
                k: v.value for k, v in self._access_patterns.items()
            },
        }
