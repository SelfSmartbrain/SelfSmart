"""compression_engine.py

Compresses large sets of observations into smaller, more manageable knowledge.
Reduces redundancy while preserving essential information.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timezone
from dataclasses import dataclass, field
from enum import Enum

from pydantic import BaseModel, Field

from src.config.logging import get_logger

logger = get_logger(__name__)


class CompressionStrategy(str, Enum):
    """Strategies for knowledge compression."""
    DEDUPLICATION = "deduplication"  # Remove exact duplicates
    CLUSTERING = "clustering"  # Group similar items
    SAMPLING = "sampling"  # Representative sampling
    SUMMARIZATION = "summarization"  # Generate summaries
    PATTERN_EXTRACTION = "pattern_extraction"  # Extract patterns


@dataclass
class CompressionResult:
    """Result of a compression operation."""
    original_count: int
    compressed_count: int
    compression_ratio: float
    strategy: CompressionStrategy
    compressed_items: List[Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class CompressionEngine:
    """Compresses knowledge to reduce redundancy while preserving value."""
    
    def __init__(self):
        self.compression_history: List[CompressionResult] = []
        logger.info("CompressionEngine initialized")
    
    def compress_observations(
        self,
        observations: List[str],
        strategy: CompressionStrategy = CompressionStrategy.CLUSTERING,
        target_ratio: float = 0.1,  # Target 10% of original
    ) -> CompressionResult:
        """Compress a list of observations."""
        original_count = len(observations)
        
        if strategy == CompressionStrategy.DEDUPLICATION:
            compressed = self._deduplicate(observations)
        elif strategy == CompressionStrategy.CLUSTERING:
            compressed = self._cluster_observations(observations, target_ratio)
        elif strategy == CompressionStrategy.SAMPLING:
            compressed = self._sample_observations(observations, target_ratio)
        elif strategy == CompressionStrategy.SUMMARIZATION:
            compressed = self._summarize_observations(observations, target_ratio)
        elif strategy == CompressionStrategy.PATTERN_EXTRACTION:
            compressed = self._extract_patterns(observations, target_ratio)
        else:
            compressed = observations
        
        compressed_count = len(compressed)
        compression_ratio = compressed_count / original_count if original_count > 0 else 1.0
        
        result = CompressionResult(
            original_count=original_count,
            compressed_count=compressed_count,
            compression_ratio=compression_ratio,
            strategy=strategy,
            compressed_items=compressed,
            metadata={"target_ratio": target_ratio},
        )
        
        self.compression_history.append(result)
        logger.info(f"Compressed {original_count} -> {compressed_count} items ({compression_ratio:.1%})")
        return result
    
    def _deduplicate(self, items: List[str]) -> List[str]:
        """Remove exact duplicates."""
        seen = set()
        unique = []
        for item in items:
            if item not in seen:
                seen.add(item)
                unique.append(item)
        return unique
    
    def _cluster_observations(
        self,
        observations: List[str],
        target_ratio: float,
    ) -> List[str]:
        """Cluster similar observations and pick representatives."""
        if not observations:
            return []
        
        # Simple clustering based on word overlap
        clusters = []
        used = set()
        
        for obs in observations:
            if obs in used:
                continue
            
            # Find similar observations
            cluster = [obs]
            obs_words = set(obs.lower().split())
            
            for other in observations:
                if other in used:
                    continue
                
                other_words = set(other.lower().split())
                overlap = len(obs_words & other_words) / max(len(obs_words), len(other_words), 1)
                
                if overlap > 0.5:  # 50% word overlap threshold
                    cluster.append(other)
                    used.add(other)
            
            # Pick representative (longest in cluster)
            representative = max(cluster, key=len)
            clusters.append(representative)
            used.add(obs)
        
        # If still too many, sample
        if len(clusters) > len(observations) * target_ratio:
            target_count = int(len(observations) * target_ratio)
            step = len(clusters) // target_count if target_count > 0 else 1
            clusters = clusters[::step]
        
        return clusters
    
    def _sample_observations(
        self,
        observations: List[str],
        target_ratio: float,
    ) -> List[str]:
        """Sample representative observations."""
        if not observations:
            return []
        
        target_count = max(1, int(len(observations) * target_ratio))
        step = len(observations) // target_count if target_count > 0 else 1
        
        # Stratified sampling: take evenly distributed samples
        sampled = observations[::step]
        
        # Ensure we have at least target_count
        while len(sampled) < target_count and len(sampled) < len(observations):
            sampled.append(observations[len(sampled)])
        
        return sampled[:target_count]
    
    def _summarize_observations(
        self,
        observations: List[str],
        target_ratio: float,
    ) -> List[str]:
        """Generate summaries of observation groups."""
        if not observations:
            return []
        
        target_count = max(1, int(len(observations) * target_ratio))
        group_size = len(observations) // target_count if target_count > 0 else len(observations)
        
        summaries = []
        for i in range(0, len(observations), group_size):
            group = observations[i:i+group_size]
            summary = self._generate_summary(group)
            summaries.append(summary)
        
        return summaries
    
    def _generate_summary(self, items: List[str]) -> str:
        """Generate a summary from a group of items."""
        if not items:
            return ""
        
        # Simple summary: extract common words
        all_words = []
        for item in items:
            all_words.extend(item.lower().split())
        
        # Count word frequencies
        word_counts = {}
        for word in all_words:
            word_counts[word] = word_counts.get(word, 0) + 1
        
        # Get top words
        top_words = sorted(word_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        summary_words = [word for word, count in top_words]
        
        return f"Summary of {len(items)} items: {' '.join(summary_words)}"
    
    def _extract_patterns(
        self,
        observations: List[str],
        target_ratio: float,
    ) -> List[str]:
        """Extract patterns from observations."""
        if not observations:
            return []
        
        # Find common prefixes/suffixes
        patterns = []
        
        # Extract n-grams
        n = 3
        ngram_counts = {}
        
        for obs in observations:
            words = obs.lower().split()
            for i in range(len(words) - n + 1):
                ngram = " ".join(words[i:i+n])
                ngram_counts[ngram] = ngram_counts.get(ngram, 0) + 1
        
        # Get most common n-grams
        common_ngrams = sorted(ngram_counts.items(), key=lambda x: x[1], reverse=True)
        
        target_count = max(1, int(len(observations) * target_ratio))
        for ngram, count in common_ngrams[:target_count]:
            patterns.append(f"Pattern: '{ngram}' (occurs {count} times)")
        
        return patterns if patterns else observations[:target_count]
    
    def compress_dict_values(
        self,
        data: Dict[str, List[Any]],
        strategy: CompressionStrategy = CompressionStrategy.DEDUPLICATION,
    ) -> Dict[str, CompressionResult]:
        """Compress values in a dictionary."""
        results = {}
        
        for key, values in data.items():
            if isinstance(values, list):
                str_values = [str(v) for v in values]
                result = self.compress_observations(str_values, strategy)
                results[key] = result
        
        return results
    
    def get_compression_statistics(self) -> Dict[str, Any]:
        """Get statistics on compression operations."""
        if not self.compression_history:
            return {
                "total_compressions": 0,
                "average_compression_ratio": 0.0,
            }
        
        total_compressions = len(self.compression_history)
        avg_ratio = sum(r.compression_ratio for r in self.compression_history) / total_compressions
        
        strategy_counts = {}
        for result in self.compression_history:
            strategy_counts[result.strategy.value] = strategy_counts.get(result.strategy.value, 0) + 1
        
        return {
            "total_compressions": total_compressions,
            "average_compression_ratio": avg_ratio,
            "by_strategy": strategy_counts,
            "total_items_compressed": sum(r.original_count for r in self.compression_history),
            "total_items_after_compression": sum(r.compressed_count for r in self.compression_history),
        }
