"""
Context Manager - Manages global cognitive context

The ContextManager is responsible for:
- Maintaining global context across all agents
- Tracking current state and goals
- Providing relevant context for cognitive operations
- Managing context lifecycle
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum
import json


logger = logging.getLogger(__name__)


class ContextScope(Enum):
    """Scopes of context"""
    GLOBAL = "global"
    SESSION = "session"
    TASK = "task"
    AGENT = "agent"


@dataclass
class ContextEntry:
    """A context entry"""
    key: str
    value: Any
    scope: ContextScope
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    ttl: Optional[float] = None  # Time to live in seconds
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def is_expired(self) -> bool:
        """Check if this context entry has expired"""
        if self.ttl is None:
            return False
        return (datetime.now().timestamp() - self.timestamp) > self.ttl


class ContextManager:
    """
    Manages global cognitive context.
    
    Provides a unified context store that all agents can access
    to maintain shared understanding and state.
    """
    
    def __init__(self, kernel: Any):
        self.kernel = kernel
        self._contexts: Dict[ContextScope, Dict[str, ContextEntry]] = {
            scope: {} for scope in ContextScope
        }
        self._lock = asyncio.Lock()
        
        # Context statistics
        self._context_updates = 0
        self._context_queries = 0
    
    async def initialize(self) -> None:
        """Initialize the context manager"""
        logger.info("ContextManager initialized")
    
    async def shutdown(self) -> None:
        """Shutdown the context manager"""
        # Clean up expired contexts
        await self._cleanup_expired()
        logger.info("ContextManager shutdown complete")
    
    async def update(
        self,
        key: str,
        value: Any,
        scope: ContextScope = ContextScope.GLOBAL,
        ttl: Optional[float] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Update a context entry.
        
        Args:
            key: Context key
            value: Context value
            scope: Context scope
            ttl: Time to live in seconds
            metadata: Additional metadata
        """
        async with self._lock:
            entry = ContextEntry(
                key=key,
                value=value,
                scope=scope,
                ttl=ttl,
                metadata=metadata or {},
            )
            
            self._contexts[scope][key] = entry
            self._context_updates += 1
            
            logger.debug(f"Updated context {key} in scope {scope.value}")
    
    async def get(
        self,
        key: str,
        scope: ContextScope = ContextScope.GLOBAL,
        default: Any = None,
    ) -> Any:
        """
        Get a context entry.
        
        Args:
            key: Context key
            scope: Context scope
            default: Default value if not found
            
        Returns:
            Context value or default
        """
        async with self._lock:
            # Clean up expired entries first
            await self._cleanup_expired()
            
            entry = self._contexts[scope].get(key)
            
            if entry is None or entry.is_expired():
                self._context_queries += 1
                return default
            
            self._context_queries += 1
            return entry.value
    
    async def delete(
        self,
        key: str,
        scope: ContextScope = ContextScope.GLOBAL,
    ) -> bool:
        """
        Delete a context entry.
        
        Args:
            key: Context key
            scope: Context scope
            
        Returns:
            True if deleted, False if not found
        """
        async with self._lock:
            if key in self._contexts[scope]:
                del self._contexts[scope][key]
                logger.debug(f"Deleted context {key} from scope {scope.value}")
                return True
            return False
    
    async def get_relevant_context(
        self,
        input_data: Dict[str, Any],
        scope: Optional[ContextScope] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Get context relevant to the input data.
        
        Args:
            input_data: Input data to match against
            scope: Specific scope to search (optional)
            limit: Maximum number of context entries to return
            
        Returns:
            Relevant context dictionary
        """
        async with self._lock:
            await self._cleanup_expired()
            
            relevant_context = {}
            
            # Search in specified scope or all scopes
            scopes_to_search = [scope] if scope else list(ContextScope)
            
            for search_scope in scopes_to_search:
                for key, entry in self._contexts[search_scope].items():
                    if not entry.is_expired():
                        # Simple relevance check: key appears in input
                        if key.lower() in str(input_data).lower():
                            relevant_context[key] = entry.value
                            
                            if len(relevant_context) >= limit:
                                break
                
                if len(relevant_context) >= limit:
                    break
            
            return relevant_context
    
    async def get_scope_context(
        self,
        scope: ContextScope,
        include_expired: bool = False,
    ) -> Dict[str, Any]:
        """
        Get all context in a specific scope.
        
        Args:
            scope: Context scope
            include_expired: Whether to include expired entries
            
        Returns:
            All context in the scope
        """
        async with self._lock:
            if not include_expired:
                await self._cleanup_expired()
            
            return {
                key: entry.value
                for key, entry in self._contexts[scope].items()
                if include_expired or not entry.is_expired()
            }
    
    async def clear_scope(self, scope: ContextScope) -> int:
        """
        Clear all context in a specific scope.
        
        Args:
            scope: Context scope
            
        Returns:
            Number of entries cleared
        """
        async with self._lock:
            count = len(self._contexts[scope])
            self._contexts[scope].clear()
            logger.info(f"Cleared {count} entries from scope {scope.value}")
            return count
    
    async def _cleanup_expired(self) -> int:
        """Clean up expired context entries"""
        total_removed = 0
        
        for scope in ContextScope:
            expired_keys = [
                key for key, entry in self._contexts[scope].items()
                if entry.is_expired()
            ]
            
            for key in expired_keys:
                del self._contexts[scope][key]
                total_removed += 1
        
        if total_removed > 0:
            logger.debug(f"Cleaned up {total_removed} expired context entries")
        
        return total_removed
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get context manager metrics"""
        return {
            "context_updates": self._context_updates,
            "context_queries": self._context_queries,
            "total_entries": sum(
                len(ctx) for ctx in self._contexts.values()
            ),
            "entries_by_scope": {
                scope.value: len(ctx)
                for scope, ctx in self._contexts.items()
            },
        }
