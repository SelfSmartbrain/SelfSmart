"""
Knowledge Fitness Engine - Evaluates and scores memory beliefs.

The engine computes fitness scores for beliefs stored in Neo4j and Qdrant
based on age, access frequency, confidence, validations, contradictions,
semantic coherence, and utility.
"""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Set
from enum import Enum

from src.config.logging import get_logger
from src.config.settings import get_settings
from .config import (
    FitnessConfig,
    FitnessMetric,
    DEFAULT_FITNESS_CONFIG,
)

logger = get_logger(__name__)


class BeliefType(Enum):
    """Types of beliefs that can be evaluated."""
    FACT = "fact"
    CONCEPT = "concept"
    RULE = "rule"
    PATTERN = "pattern"
    MEMORY = "memory"
    STRATEGY = "strategy"
    SKILL = "skill"


@dataclass
class BeliefRecord:
    """A belief record from memory stores."""
    id: str
    content: str
    belief_type: BeliefType
    confidence: float
    created_at: datetime
    last_accessed: Optional[datetime] = None
    access_count: int = 0
    validation_count: int = 0
    contradiction_count: int = 0
    source: str = "unknown"
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    # Qdrant specific
    collection: Optional[str] = None
    vector: Optional[List[float]] = None
    
    # Neo4j specific
    node_labels: List[str] = field(default_factory=list)
    relationships: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class FitnessScore:
    """Fitness evaluation result for a belief."""
    belief_id: str
    overall_fitness: float
    metric_scores: Dict[FitnessMetric, float]
    metric_details: Dict[str, Any]
    recommendation: str  # "keep", "review", "prune", "critical"
    evaluated_at: datetime = field(default_factory=datetime.utcnow)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "belief_id": self.belief_id,
            "overall_fitness": self.overall_fitness,
            "metric_scores": {k.value: v for k, v in self.metric_scores.items()},
            "metric_details": self.metric_details,
            "recommendation": self.recommendation,
            "evaluated_at": self.evaluated_at.isoformat(),
        }


class KnowledgeFitnessEngine:
    """
    Evaluates the fitness of knowledge beliefs across memory stores.
    
    Computes scores based on:
    - Age decay (older beliefs lose relevance)
    - Access frequency (frequently used beliefs are more valuable)
    - Original confidence (LLM/confidence at creation)
    - Validation count (times verified against reality)
    - Contradiction count (times contradicted by new evidence)
    - Semantic coherence (internal consistency)
    - Utility score (practical usefulness)
    """
    
    def __init__(
        self,
        config: FitnessConfig = DEFAULT_FITNESS_CONFIG,
        qdrant_client=None,
        neo4j_client=None,
        embedding_service=None,
    ):
        self.config = config
        self.qdrant_client = qdrant_client
        self.neo4j_client = neo4j_client
        self.embedding_service = embedding_service
        self._initialized = False
        
        # Statistics
        self._evaluations_performed = 0
        self._beliefs_evaluated = 0
        self._pruning_recommendations = 0
        
    async def initialize(self) -> None:
        """Initialize connections to memory stores."""
        if self._initialized:
            return
            
        settings = get_settings()
        
        # Initialize Qdrant if not provided
        if self.qdrant_client is None:
            from src.rag.vector_store import VectorStoreManager
            self.qdrant_client = VectorStoreManager()
            await self.qdrant_client.initialize()
        
        # Initialize Neo4j if not provided
        if self.neo4j_client is None:
            try:
                from neo4j import AsyncGraphDatabase
                self.neo4j_client = AsyncGraphDatabase.driver(
                    settings.neo4j_uri,
                    auth=(settings.neo4j_user, settings.neo4j_password),
                )
                await self.neo4j_client.verify_connectivity()
            except Exception as e:
                logger.warning(f"Neo4j connection failed: {e}")
                self.neo4j_client = None
        
        # Initialize embedding service if not provided
        if self.embedding_service is None:
            try:
                from src.rag.embeddings import EmbeddingService
                self.embedding_service = EmbeddingService()
            except Exception as e:
                logger.warning(f"Embedding service not available: {e}")
        
        self._initialized = True
        logger.info("KnowledgeFitnessEngine initialized")
    
    async def close(self) -> None:
        """Close connections."""
        if self.qdrant_client and hasattr(self.qdrant_client, 'close'):
            await self.qdrant_client.close()
        if self.neo4j_client:
            await self.neo4j_client.close()
    
    async def evaluate_all_beliefs(
        self,
        collections: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
    ) -> List[FitnessScore]:
        """
        Evaluate fitness of all beliefs across specified collections/labels.
        
        Args:
            collections: Qdrant collections to evaluate (default: config)
            labels: Neo4j node labels to evaluate (default: config)
            
        Returns:
            List of FitnessScore objects
        """
        await self.initialize()
        
        collections = collections or self.config.qdrant_collections
        labels = labels or self.config.neo4j_labels
        
        all_beliefs = []
        
        # Fetch from Qdrant
        qdrant_beliefs = await self._fetch_qdrant_beliefs(collections)
        all_beliefs.extend(qdrant_beliefs)
        logger.info(f"Fetched {len(qdrant_beliefs)} beliefs from Qdrant")
        
        # Fetch from Neo4j
        neo4j_beliefs = await self._fetch_neo4j_beliefs(labels)
        all_beliefs.extend(neo4j_beliefs)
        logger.info(f"Fetched {len(neo4j_beliefs)} beliefs from Neo4j")
        
        # Evaluate each belief
        scores = []
        for belief in all_beliefs:
            score = await self._evaluate_belief(belief)
            scores.append(score)
            self._beliefs_evaluated += 1
            
            if score.recommendation in ("prune", "critical"):
                self._pruning_recommendations += 1
        
        self._evaluations_performed += 1
        logger.info(
            f"Fitness evaluation complete: {len(scores)} beliefs evaluated, "
            f"{self._pruning_recommendations} flagged for pruning"
        )
        
        return scores
    
    async def _fetch_qdrant_beliefs(self, collections: List[str]) -> List[BeliefRecord]:
        """Fetch beliefs from Qdrant collections."""
        beliefs = []
        
        for collection in collections:
            try:
                # Get collection info
                count = await self.qdrant_client.count(collection)
                if count == 0:
                    continue
                
                # Scroll through points in batches
                from qdrant_client import models
                limit = 100
                offset = None
                
                while True:
                    results = await self.qdrant_client._client.scroll(
                        collection_name=collection,
                        limit=limit,
                        offset=offset,
                        with_payload=True,
                        with_vectors=True,
                    )
                    
                    points = results[0]
                    if not points:
                        break
                    
                    for point in points:
                        payload = point.payload or {}
                        belief = BeliefRecord(
                            id=str(point.id),
                            content=payload.get("content", ""),
                            belief_type=self._infer_belief_type(payload),
                            confidence=payload.get("confidence", 0.5),
                            created_at=datetime.fromtimestamp(
                                payload.get("timestamp", datetime.utcnow().timestamp())
                            ),
                            last_accessed=datetime.fromtimestamp(
                                payload.get("last_accessed", 0)
                            ) if payload.get("last_accessed") else None,
                            access_count=payload.get("access_count", 0),
                            validation_count=payload.get("validation_count", 0),
                            contradiction_count=payload.get("contradiction_count", 0),
                            source=payload.get("source", "unknown"),
                            metadata=payload,
                            collection=collection,
                            vector=point.vector if isinstance(point.vector, list) else None,
                        )
                        beliefs.append(belief)
                    
                    offset = results[1]
                    if offset is None:
                        break
                        
            except Exception as e:
                logger.error(f"Error fetching from Qdrant collection {collection}: {e}")
        
        return beliefs
    
    async def _fetch_neo4j_beliefs(self, labels: List[str]) -> List[BeliefRecord]:
        """Fetch beliefs from Neo4j."""
        beliefs = []
        
        if not self.neo4j_client:
            return beliefs
        
        try:
            async with self.neo4j_client.session() as session:
                for label in labels:
                    query = f"""
                    MATCH (n:{label})
                    OPTIONAL MATCH (n)-[r]-(m)
                    RETURN n, collect(r) as relationships, collect(m) as connected
                    LIMIT 1000
                    """
                    
                    result = await session.run(query)
                    async for record in result:
                        node = record["n"]
                        props = dict(node)
                        
                        belief = BeliefRecord(
                            id=str(node.id),
                            content=props.get("content", props.get("text", "")),
                            belief_type=self._infer_belief_type_from_label(label),
                            confidence=props.get("confidence", 0.5),
                            created_at=datetime.fromtimestamp(
                                props.get("timestamp", datetime.utcnow().timestamp())
                            ),
                            last_accessed=datetime.fromtimestamp(
                                props.get("last_accessed", 0)
                            ) if props.get("last_accessed") else None,
                            access_count=props.get("access_count", 0),
                            validation_count=props.get("validation_count", 0),
                            contradiction_count=props.get("contradiction_count", 0),
                            source=props.get("source", "neo4j"),
                            metadata=props,
                            node_labels=list(node.labels),
                            relationships=[
                                {
                                    "type": r.type,
                                    "target": dict(record["connected"][i]) if i < len(record["connected"]) else {}
                                }
                                for i, r in enumerate(record["relationships"])
                            ],
                        )
                        beliefs.append(belief)
                        
        except Exception as e:
            logger.error(f"Error fetching from Neo4j: {e}")
        
        return beliefs
    
    def _infer_belief_type(self, payload: Dict[str, Any]) -> BeliefType:
        """Infer belief type from payload metadata."""
        btype = payload.get("belief_type", payload.get("type", "")).lower()
        
        type_mapping = {
            "fact": BeliefType.FACT,
            "concept": BeliefType.CONCEPT,
            "rule": BeliefType.RULE,
            "pattern": BeliefType.PATTERN,
            "memory": BeliefType.MEMORY,
            "strategy": BeliefType.STRATEGY,
            "skill": BeliefType.SKILL,
        }
        
        return type_mapping.get(btype, BeliefType.FACT)
    
    def _infer_belief_type_from_label(self, label: str) -> BeliefType:
        """Infer belief type from Neo4j label."""
        label_lower = label.lower()
        
        if "fact" in label_lower:
            return BeliefType.FACT
        elif "concept" in label_lower:
            return BeliefType.CONCEPT
        elif "rule" in label_lower:
            return BeliefType.RULE
        elif "pattern" in label_lower:
            return BeliefType.PATTERN
        elif "memory" in label_lower:
            return BeliefType.MEMORY
        elif "strategy" in label_lower:
            return BeliefType.STRATEGY
        elif "skill" in label_lower:
            return BeliefType.SKILL
        
        return BeliefType.FACT
    
    async def _evaluate_belief(self, belief: BeliefRecord) -> FitnessScore:
        """Evaluate fitness of a single belief."""
        metric_scores = {}
        metric_details = {}
        
        now = datetime.utcnow()
        
        # 1. Age score (older = lower score, with half-life decay)
        age_days = (now - belief.created_at).days
        age_score = max(0.0, 1.0 - (age_days / self.config.max_age_days))
        metric_scores[FitnessMetric.AGE] = age_score
        metric_details["age_days"] = age_days
        
        # 2. Access frequency score (with exponential decay)
        if belief.last_accessed:
            days_since_access = (now - belief.last_accessed).days
            access_score = max(0.0, 1.0 - (days_since_access / self.config.half_life_days))
        else:
            access_score = 0.1 if belief.access_count == 0 else 0.3
        metric_scores[FitnessMetric.ACCESS_FREQUENCY] = access_score
        metric_details["access_count"] = belief.access_count
        metric_details["days_since_access"] = (
            (now - belief.last_accessed).days if belief.last_accessed else None
        )
        
        # 3. Confidence score (direct from belief)
        confidence_score = belief.confidence
        metric_scores[FitnessMetric.CONFIDENCE] = confidence_score
        metric_details["original_confidence"] = belief.confidence
        
        # 4. Validation score (more validations = higher score)
        validation_score = min(1.0, belief.validation_count / 5.0)
        metric_scores[FitnessMetric.VALIDATION_COUNT] = validation_score
        metric_details["validation_count"] = belief.validation_count
        
        # 5. Contradiction penalty (more contradictions = lower score)
        contradiction_penalty = belief.contradiction_count * self.config.contradiction_penalty
        contradiction_score = max(0.0, 1.0 - contradiction_penalty)
        metric_scores[FitnessMetric.CONTRADICTION_COUNT] = contradiction_score
        metric_details["contradiction_count"] = belief.contradiction_count
        metric_details["contradiction_penalty"] = contradiction_penalty
        
        # 6. Semantic coherence (placeholder - would use embeddings)
        coherence_score = await self._compute_semantic_coherence(belief)
        metric_scores[FitnessMetric.SEMANTIC_COHERENCE] = coherence_score
        metric_details["semantic_coherence"] = coherence_score
        
        # 7. Utility score (placeholder - based on access patterns)
        utility_score = min(1.0, belief.access_count / 10.0)
        metric_scores[FitnessMetric.UTILITY_SCORE] = utility_score
        metric_details["utility_score"] = utility_score
        
        # Compute weighted overall fitness
        overall_fitness = sum(
            metric_scores[metric] * self.config.metric_weights.get(metric, 0)
            for metric in FitnessMetric
        )
        
        # Determine recommendation
        if overall_fitness >= self.config.high_value_threshold:
            recommendation = "keep"
        elif overall_fitness >= self.config.min_fitness_threshold:
            recommendation = "review"
        elif overall_fitness >= self.config.critical_fitness_threshold:
            recommendation = "prune"
        else:
            recommendation = "critical"
        
        return FitnessScore(
            belief_id=belief.id,
            overall_fitness=overall_fitness,
            metric_scores=metric_scores,
            metric_details=metric_details,
            recommendation=recommendation,
        )
    
    async def _compute_semantic_coherence(self, belief: BeliefRecord) -> float:
        """
        Compute semantic coherence of a belief.
        
        In a full implementation, this would:
        - Check if belief contradicts other high-confidence beliefs
        - Verify internal logical consistency
        - Check alignment with core knowledge graph
        """
        # Placeholder: base score on contradiction count and validation
        base_coherence = 1.0 - (belief.contradiction_count * 0.1)
        validation_bonus = min(0.2, belief.validation_count * 0.05)
        return max(0.0, min(1.0, base_coherence + validation_bonus))
    
    async def get_pruning_candidates(
        self,
        threshold: Optional[float] = None,
        limit: Optional[int] = None,
    ) -> List[FitnessScore]:
        """Get beliefs that are candidates for pruning."""
        scores = await self.evaluate_all_beliefs()
        
        threshold = threshold or self.config.min_fitness_threshold
        limit = limit or self.config.max_prune_per_run
        
        candidates = [
            s for s in scores 
            if s.overall_fitness < threshold and s.recommendation in ("prune", "critical")
        ]
        
        # Sort by fitness (worst first)
        candidates.sort(key=lambda x: x.overall_fitness)
        
        return candidates[:limit]
    
    def get_stats(self) -> Dict[str, Any]:
        """Get engine statistics."""
        return {
            "evaluations_performed": self._evaluations_performed,
            "beliefs_evaluated": self._beliefs_evaluated,
            "pruning_recommendations": self._pruning_recommendations,
            "config": {
                "min_fitness_threshold": self.config.min_fitness_threshold,
                "critical_fitness_threshold": self.config.critical_fitness_threshold,
                "high_value_threshold": self.config.high_value_threshold,
            }
        }