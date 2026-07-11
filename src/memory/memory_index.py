"""
Memory Index - Unified indexing across all memory systems

The MemoryIndex provides:
- Cross-memory system indexing
- Fast lookup across all backends
- Memory linkage and relationships
- Index synchronization
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import hashlib


logger = logging.getLogger(__name__)


class IndexType(Enum):
    """Types of memory indices"""
    TEXT = "text"           # Full-text search index
    TAG = "tag"             # Tag-based index
    TEMPORAL = "temporal"   # Time-based index
    SEMANTIC = "semantic"   # Semantic similarity index
    RELATIONSHIP = "relationship"  # Relationship graph index


@dataclass
class MemoryLink:
    """A link between memory entries"""
    source_id: str
    target_id: str
    link_type: str
    strength: float = 0.5
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class IndexEntry:
    """An entry in the memory index"""
    memory_id: str
    memory_type: str
    index_type: IndexType
    index_value: str
    metadata: Dict[str, Any] = field(default_factory=dict)
    updated_at: float = field(default_factory=lambda: datetime.now().timestamp())


class MemoryIndex:
    """
    Unified index across all memory systems.
    
    Provides fast lookup and relationship tracking across
    all memory backends.
    """
    
    def __init__(self):
        # Indices
        self._text_index: Dict[str, Set[str]] = defaultdict(set)
        self._tag_index: Dict[str, Set[str]] = defaultdict(set)
        self._temporal_index: List[Tuple[float, str]] = []
        self._semantic_index: Dict[str, List[float]] = {}
        
        # Memory links
        self._links: Dict[str, List[MemoryLink]] = defaultdict(list)
        self._reverse_links: Dict[str, List[MemoryLink]] = defaultdict(list)
        
        # Index statistics
        self._index_updates = 0
        self._index_queries = 0
        self._link_count = 0
    
    async def index_memory(
        self,
        memory_id: str,
        memory_type: str,
        content: str,
        tags: List[str],
        timestamp: float,
        embedding: Optional[List[float]] = None,
    ) -> None:
        """
        Index a memory entry.
        
        Args:
            memory_id: Memory ID
            memory_type: Type of memory
            content: Memory content
            tags: Memory tags
            timestamp: Memory timestamp
            embedding: Vector embedding (optional)
        """
        self._index_updates += 1
        
        # Text index
        text_tokens = self._tokenize(content)
        for token in text_tokens:
            self._text_index[token].add(memory_id)
        
        # Tag index
        for tag in tags:
            self._tag_index[tag].add(memory_id)
        
        # Temporal index
        self._temporal_index.append((timestamp, memory_id))
        self._temporal_index.sort(reverse=True)  # Most recent first
        
        # Semantic index
        if embedding:
            self._semantic_index[memory_id] = embedding
        
        logger.debug(f"Indexed memory {memory_id}")
    
    def _tokenize(self, text: str) -> List[str]:
        """Simple tokenization for text indexing"""
        # Convert to lowercase and split on whitespace/punctuation
        text = text.lower()
        tokens = []
        
        for word in text.split():
            # Remove punctuation
            clean_word = "".join(c for c in word if c.isalnum())
            if len(clean_word) > 2:  # Ignore very short tokens
                tokens.append(clean_word)
        
        return tokens
    
    async def search_text(
        self,
        query: str,
        limit: int = 10,
    ) -> List[str]:
        """
        Search by text content.
        
        Args:
            query: Search query
            limit: Maximum results
            
        Returns:
            List of memory IDs
        """
        self._index_queries += 1
        
        tokens = self._tokenize(query)
        
        if not tokens:
            return []
        
        # Find memories containing all tokens
        result_sets = [self._text_index.get(token, set()) for token in tokens]
        
        if not result_sets:
            return []
        
        # Intersection of all token matches
        results = set.intersection(*result_sets)
        
        return list(results)[:limit]
    
    async def search_tags(
        self,
        tags: List[str],
        match_all: bool = False,
        limit: int = 10,
    ) -> List[str]:
        """
        Search by tags.
        
        Args:
            tags: Tags to search for
            match_all: True = all tags must match, False = any tag
            limit: Maximum results
            
        Returns:
            List of memory IDs
        """
        self._index_queries += 1
        
        if match_all:
            # All tags must match
            result_sets = [self._tag_index.get(tag, set()) for tag in tags]
            if result_sets:
                results = set.intersection(*result_sets)
            else:
                results = set()
        else:
            # Any tag can match
            results = set()
            for tag in tags:
                results.update(self._tag_index.get(tag, set()))
        
        return list(results)[:limit]
    
    async def search_temporal(
        self,
        start_time: Optional[float] = None,
        end_time: Optional[float] = None,
        limit: int = 10,
    ) -> List[str]:
        """
        Search by time range.
        
        Args:
            start_time: Start timestamp (optional)
            end_time: End timestamp (optional)
            limit: Maximum results
            
        Returns:
            List of memory IDs
        """
        self._index_queries += 1
        
        results = []
        
        for timestamp, memory_id in self._temporal_index:
            if start_time and timestamp < start_time:
                continue
            if end_time and timestamp > end_time:
                continue
            
            results.append(memory_id)
            
            if len(results) >= limit:
                break
        
        return results
    
    async def search_semantic(
        self,
        query_embedding: List[float],
        limit: int = 10,
        threshold: float = 0.7,
    ) -> List[Tuple[str, float]]:
        """
        Search by semantic similarity.
        
        Args:
            query_embedding: Query vector embedding
            limit: Maximum results
            threshold: Minimum similarity threshold
            
        Returns:
            List of (memory_id, similarity) tuples
        """
        self._index_queries += 1
        
        results = []
        
        for memory_id, embedding in self._semantic_index.items():
            similarity = self._cosine_similarity(query_embedding, embedding)
            
            if similarity >= threshold:
                results.append((memory_id, similarity))
        
        # Sort by similarity
        results.sort(key=lambda x: x[1], reverse=True)
        
        return results[:limit]
    
    def _cosine_similarity(
        self,
        vec1: List[float],
        vec2: List[float],
    ) -> float:
        """Calculate cosine similarity between vectors"""
        if len(vec1) != len(vec2):
            return 0.0
        
        dot_product = sum(a * b for a, b in zip(vec1, vec2))
        magnitude1 = sum(a * a for a in vec1) ** 0.5
        magnitude2 = sum(b * b for b in vec2) ** 0.5
        
        if magnitude1 == 0 or magnitude2 == 0:
            return 0.0
        
        return dot_product / (magnitude1 * magnitude2)
    
    async def add_link(
        self,
        source_id: str,
        target_id: str,
        link_type: str,
        strength: float = 0.5,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Add a link between memory entries.
        
        Args:
            source_id: Source memory ID
            target_id: Target memory ID
            link_type: Type of link
            strength: Link strength (0.0 to 1.0)
            metadata: Additional metadata
        """
        link = MemoryLink(
            source_id=source_id,
            target_id=target_id,
            link_type=link_type,
            strength=strength,
            metadata=metadata or {},
        )
        
        self._links[source_id].append(link)
        self._reverse_links[target_id].append(link)
        self._link_count += 1
        
        logger.debug(f"Added link {source_id} -> {target_id} ({link_type})")
    
    async def get_links(
        self,
        memory_id: str,
        link_type: Optional[str] = None,
        direction: str = "outgoing",
        min_strength: float = 0.0,
    ) -> List[MemoryLink]:
        """
        Get links for a memory entry.
        
        Args:
            memory_id: Memory ID
            link_type: Filter by link type (optional)
            direction: "outgoing", "incoming", or "both"
            min_strength: Minimum link strength
            
        Returns:
            List of memory links
        """
        results = []
        
        if direction in ("outgoing", "both"):
            for link in self._links.get(memory_id, []):
                if link_type is None or link.link_type == link_type:
                    if link.strength >= min_strength:
                        results.append(link)
        
        if direction in ("incoming", "both"):
            for link in self._reverse_links.get(memory_id, []):
                if link_type is None or link.link_type == link_type:
                    if link.strength >= min_strength:
                        results.append(link)
        
        return results
    
    async def find_related(
        self,
        memory_id: str,
        max_depth: int = 2,
        min_strength: float = 0.3,
    ) -> Set[str]:
        """
        Find related memories through links.
        
        Args:
            memory_id: Starting memory ID
            max_depth: Maximum link depth to traverse
            min_strength: Minimum link strength
            
        Returns:
            Set of related memory IDs
        """
        visited = set()
        to_visit = [(memory_id, 0)]
        
        while to_visit:
            current_id, depth = to_visit.pop(0)
            
            if current_id in visited or depth >= max_depth:
                continue
            
            visited.add(current_id)
            
            # Get outgoing links
            for link in self._links.get(current_id, []):
                if link.strength >= min_strength:
                    to_visit.append((link.target_id, depth + 1))
            
            # Get incoming links
            for link in self._reverse_links.get(current_id, []):
                if link.strength >= min_strength:
                    to_visit.append((link.source_id, depth + 1))
        
        visited.discard(memory_id)  # Remove the starting ID
        return visited
    
    async def remove_memory(self, memory_id: str) -> None:
        """
        Remove a memory from all indices.
        
        Args:
            memory_id: Memory ID to remove
        """
        # Remove from text index
        for token, memory_ids in self._text_index.items():
            memory_ids.discard(memory_id)
        
        # Remove from tag index
        for tag, memory_ids in self._tag_index.items():
            memory_ids.discard(memory_id)
        
        # Remove from temporal index
        self._temporal_index = [
            (t, mid) for t, mid in self._temporal_index if mid != memory_id
        ]
        
        # Remove from semantic index
        self._semantic_index.pop(memory_id, None)
        
        # Remove links
        self._links.pop(memory_id, None)
        self._reverse_links.pop(memory_id, None)
        
        logger.debug(f"Removed memory {memory_id} from index")
    
    def get_index_stats(self) -> Dict[str, Any]:
        """Get index statistics"""
        return {
            "index_updates": self._index_updates,
            "index_queries": self._index_queries,
            "link_count": self._link_count,
            "text_index_size": len(self._text_index),
            "tag_index_size": len(self._tag_index),
            "temporal_index_size": len(self._temporal_index),
            "semantic_index_size": len(self._semantic_index),
        }
