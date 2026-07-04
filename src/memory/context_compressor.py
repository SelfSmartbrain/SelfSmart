"""
Context Compressor - Long-Horizon Task Persistence

Compresses working memory using clustering + LLM summarization
to enable tasks spanning days/weeks without context bloat.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field
from enum import Enum
import json
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics.pairwise import cosine_similarity

logger = logging.getLogger(__name__)


class CompressionStrategy(Enum):
    """Compression strategies"""
    CLUSTER_SUMMARIZE = "cluster_summarize"
    IMPORTANCE_FILTER = "importance_filter"
    TEMPORAL_DECAY = "temporal_decay"
    HYBRID = "hybrid"


@dataclass
class MemoryCluster:
    """A cluster of related memories"""
    cluster_id: int
    memories: List[Dict[str, Any]]
    centroid: List[float]
    summary: str = ""
    importance: float = 0.0
    tags: List[str] = field(default_factory=list)
    timestamp_range: tuple = (0.0, 0.0)


@dataclass
class CompressionResult:
    """Result of compression operation"""
    original_count: int
    compressed_count: int
    clusters: List[MemoryCluster]
    token_savings: int
    compression_ratio: float


class ContextCompressor:
    """
    Compresses working memory by clustering related memories
    and generating LLM summaries for each cluster.
    """

    def __init__(
        self,
        llm_client: Any,
        vector_store: Any,
        memory_fabric: Any,
        strategy: CompressionStrategy = CompressionStrategy.HYBRID,
        max_clusters: int = 10,
        min_cluster_size: int = 3,
        importance_threshold: float = 0.3,
    ):
        self.llm = llm_client
        self.vectors = vector_store
        self.memory = memory_fabric
        self.strategy = strategy
        self.max_clusters = max_clusters
        self.min_cluster_size = min_cluster_size
        self.importance_threshold = importance_threshold

    async def compress(
        self,
        agent_id: str,
        working_memories: List[Dict[str, Any]],
        max_tokens: int = 8000,
    ) -> CompressionResult:
        """
        Compress working memories into summarized clusters.
        
        Args:
            agent_id: Agent identifier
            working_memories: List of memory entries from working memory
            max_tokens: Target token budget after compression
            
        Returns:
            CompressionResult with clusters and metrics
        """
        if not working_memories:
            return CompressionResult(
                original_count=0,
                compressed_count=0,
                clusters=[],
                token_savings=0,
                compression_ratio=0.0,
            )

        logger.info(f"Compressing {len(working_memories)} memories for agent {agent_id}")

        # Filter by importance
        important_memories = [
            m for m in working_memories
            if m.get("importance", 0.5) >= self.importance_threshold
        ]

        # Get embeddings for clustering
        embeddings = await self._get_embeddings(important_memories)

        # Cluster memories
        clusters = await self._cluster_memories(important_memories, embeddings)

        # Summarize each cluster
        summarized_clusters = await asyncio.gather(*[
            self._summarize_cluster(cluster) for cluster in clusters
        ])

        # Store summaries as long-term memories
        stored_ids = []
        for cluster in summarized_clusters:
            memory_id = await self._store_summary(agent_id, cluster)
            stored_ids.append(memory_id)

        # Calculate metrics
        original_tokens = sum(self._estimate_tokens(m.get("content", "")) for m in working_memories)
        compressed_tokens = sum(self._estimate_tokens(c.summary) for c in summarized_clusters)
        token_savings = original_tokens - compressed_tokens

        result = CompressionResult(
            original_count=len(working_memories),
            compressed_count=len(summarized_clusters),
            clusters=summarized_clusters,
            token_savings=token_savings,
            compression_ratio=compressed_tokens / original_tokens if original_tokens > 0 else 0.0,
        )

        logger.info(
            f"Compression complete: {len(working_memories)} -> {len(summarized_clusters)} "
            f"({token_savings} tokens saved, ratio: {result.compression_ratio:.2f})"
        )

        return result

    async def _get_embeddings(self, memories: List[Dict[str, Any]]) -> np.ndarray:
        """Get embeddings for memories, generating if missing"""
        embeddings = []
        for mem in memories:
            if mem.get("embedding"):
                embeddings.append(mem["embedding"])
            else:
                # Generate embedding via LLM or vector store
                embedding = await self._generate_embedding(mem.get("content", ""))
                embeddings.append(embedding)
        return np.array(embeddings)

    async def _generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text using the embedding service"""
        try:
            # Try to use the vector store's embedding service
            if hasattr(self.vectors, 'embed_text'):
                return await self.vectors.embed_text(text)
            # Try to use the memory fabric's embedding service
            if hasattr(self.memory, 'embed_text'):
                return await self.memory.embed_text(text)
            # Try to use the LLM's embedding capability
            if hasattr(self.llm, 'embed_text'):
                return await self.llm.embed_text(text)
            # Fallback: deterministic multi-hash embedding with broad dimensional coverage.
            # This is a last resort; production should use a real embedding model.
            import hashlib
            embedding = []
            for i in range(48):
                hash_input = f"{text}__dim_{i}".encode()
                hash_bytes = hashlib.sha256(hash_input).digest()
                embedding.extend([(b / 255.0 - 0.5) * 2 for b in hash_bytes])
            return embedding[:1536]
        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            # Return zero vector as last resort
            return [0.0] * 1536

    async def _cluster_memories(
        self,
        memories: List[Dict[str, Any]],
        embeddings: np.ndarray,
    ) -> List[MemoryCluster]:
        """Cluster memories using K-Means on embeddings"""
        n_clusters = min(self.max_clusters, max(1, len(memories) // self.min_cluster_size))
        
        if n_clusters == 1:
            # Single cluster
            centroid = np.mean(embeddings, axis=0).tolist()
            return [MemoryCluster(
                cluster_id=0,
                memories=memories,
                centroid=centroid,
                timestamp_range=(
                    min(m.get("timestamp", 0) for m in memories),
                    max(m.get("timestamp", 0) for m in memories),
                ),
            )]

        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init=10)
        labels = kmeans.fit_predict(embeddings)

        clusters = []
        for cluster_id in range(n_clusters):
            cluster_memories = [memories[i] for i in range(len(memories)) if labels[i] == cluster_id]
            if len(cluster_memories) >= self.min_cluster_size:
                centroid = kmeans.cluster_centers_[cluster_id].tolist()
                clusters.append(MemoryCluster(
                    cluster_id=cluster_id,
                    memories=cluster_memories,
                    centroid=centroid,
                    timestamp_range=(
                        min(m.get("timestamp", 0) for m in cluster_memories),
                        max(m.get("timestamp", 0) for m in cluster_memories),
                    ),
                ))

        # Handle outliers (memories in small clusters)
        outlier_memories = [memories[i] for i in range(len(memories)) 
                           if labels[i] not in [c.cluster_id for c in clusters]]
        if outlier_memories:
            centroid = np.mean([embeddings[i] for i in range(len(memories)) 
                               if labels[i] not in [c.cluster_id for c in clusters]], axis=0).tolist()
            clusters.append(MemoryCluster(
                cluster_id=n_clusters,
                memories=outlier_memories,
                centroid=centroid,
                timestamp_range=(
                    min(m.get("timestamp", 0) for m in outlier_memories),
                    max(m.get("timestamp", 0) for m in outlier_memories),
                ),
            ))

        return clusters

    async def _summarize_cluster(self, cluster: MemoryCluster) -> MemoryCluster:
        """Generate LLM summary for a memory cluster"""
        # Prepare memory texts
        memory_texts = "\n---\n".join([
            f"[{m.get('timestamp', 0)}] {m.get('content', '')}"
            for m in cluster.memories
        ])

        prompt = f"""Summarize the following related memories into key insights.
Preserve important facts, decisions, and outcomes.
Focus on information that would be useful for future task continuation.

Memories:
{memory_texts}

Provide a concise summary (max 500 words) and extract key tags:"""

        try:
            response = await self.llm.ainvoke(prompt)
            summary = response.content if hasattr(response, 'content') else str(response)
        except Exception as e:
            logger.error(f"LLM summarization failed: {e}")
            summary = f"Cluster {cluster.cluster_id}: {len(cluster.memories)} memories (auto-summarization failed)"

        # Extract tags from summary (simple keyword extraction)
        tags = self._extract_tags(summary)

        # Calculate cluster importance
        importance = np.mean([m.get("importance", 0.5) for m in cluster.memories])

        cluster.summary = summary
        cluster.importance = float(importance)
        cluster.tags = tags

        return cluster

    def _extract_tags(self, text: str) -> List[str]:
        """Extract key tags from summary text"""
        # Simple implementation - could use NLP
        keywords = ["decision", "error", "success", "config", "api", "database", 
                   "auth", "deploy", "test", "bug", "feature", "refactor"]
        found = [k for k in keywords if k.lower() in text.lower()]
        return found[:5]

    async def _store_summary(self, agent_id: str, cluster: MemoryCluster) -> str:
        """Store cluster summary as long-term semantic memory"""
        from src.memory.memory_fabric import MemoryEntry, MemoryType
        
        entry = MemoryEntry(
            content=cluster.summary,
            memory_type=MemoryType.SEMANTIC,
            metadata={
                "cluster_id": cluster.cluster_id,
                "original_count": len(cluster.memories),
                "timestamp_range": cluster.timestamp_range,
                "tags": cluster.tags,
                "compressed": True,
                "agent_id": agent_id,
            },
            importance=cluster.importance,
            tags=cluster.tags,
            source="context_compressor",
        )

        return await self.memory.store(entry, MemoryType.SEMANTIC)

    def _estimate_tokens(self, text: str) -> int:
        """Rough token estimation"""
        return len(text) // 4


class CompressionScheduler:
    """
    Automatically triggers context compression when working memory
    approaches token limits.
    """

    def __init__(
        self,
        memory_fabric: Any,
        compressor: ContextCompressor,
        trigger_threshold: float = 0.8,
        check_interval: int = 300,  # 5 minutes
    ):
        self.memory = memory_fabric
        self.compressor = compressor
        self.trigger_threshold = trigger_threshold
        self.check_interval = check_interval
        self._running = False
        self._task: Optional[asyncio.Task] = None

    async def start(self, agent_ids: List[str]) -> None:
        """Start the compression scheduler for given agents"""
        self._running = True
        self._task = asyncio.create_task(self._monitor_loop(agent_ids))
        logger.info(f"CompressionScheduler started for agents: {agent_ids}")

    async def stop(self) -> None:
        """Stop the compression scheduler"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("CompressionScheduler stopped")

    async def _monitor_loop(self, agent_ids: List[str]) -> None:
        """Monitor working memory and trigger compression"""
        while self._running:
            for agent_id in agent_ids:
                try:
                    await self.check_and_compress(agent_id)
                except Exception as e:
                    logger.error(f"Compression check failed for {agent_id}: {e}")
            await asyncio.sleep(self.check_interval)

    async def check_and_compress(self, agent_id: str) -> bool:
        """Check if compression needed and execute"""
        # Get working memory stats
        wm_stats = await self._get_working_memory_stats(agent_id)
        
        if wm_stats["token_usage"] / wm_stats["max_tokens"] > self.trigger_threshold:
            logger.info(f"Triggering compression for agent {agent_id} "
                       f"({wm_stats['token_usage']}/{wm_stats['max_tokens']} tokens)")
            
            # Get working memories
            memories = await self._get_working_memories(agent_id)
            
            # Compress
            await self.compressor.compress(agent_id, memories)
            return True
        
        return False

    async def _get_working_memory_stats(self, agent_id: str) -> Dict[str, Any]:
        """Get working memory statistics"""
        # Placeholder - would query actual working memory backend
        return {
            "token_usage": 0,
            "max_tokens": 8000,
            "entry_count": 0,
        }

    async def _get_working_memories(self, agent_id: str) -> List[Dict[str, Any]]:
        """Retrieve working memories for compression"""
        # Placeholder - would query actual working memory backend
        return []
