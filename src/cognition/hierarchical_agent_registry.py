"""
Hierarchical Agent Registry - Enhanced Agent Registry with Capability Vectors

Extends the existing AgentRegistry with vector-based capability discovery
and hierarchical agent relationships for delegation.
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set, Tuple
from dataclasses import dataclass, field
from enum import Enum
from collections import defaultdict
import numpy as np

logger = logging.getLogger(__name__)


class AgentRelationship(Enum):
    """Types of agent relationships"""
    PARENT = "parent"
    CHILD = "child"
    PEER = "peer"
    SUPERVISOR = "supervisor"
    WORKER = "worker"


@dataclass
class CapabilityVector:
    """Vector representation of agent capabilities"""
    capability_name: str
    embedding: List[float]
    proficiency: float
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentRelationshipInfo:
    """Relationship between agents"""
    agent_id: str
    related_agent_id: str
    relationship: AgentRelationship
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    metadata: Dict[str, Any] = field(default_factory=dict)


class HierarchicalAgentRegistry:
    """
    Enhanced agent registry with:
    - Vector-based capability discovery (semantic search)
    - Hierarchical agent relationships (parent/child, supervisor/worker)
    - Capability inheritance
    - Delegation tracking
    """

    def __init__(self, neo4j_client: Any = None, embedding_model: Any = None):
        self.neo4j = neo4j_client
        self.embedding_model = embedding_model
        
        # In-memory storage (backed by Neo4j if available)
        self._agents: Dict[str, Dict[str, Any]] = {}
        self._capability_vectors: Dict[str, List[CapabilityVector]] = defaultdict(list)
        self._relationships: Dict[str, List[AgentRelationshipInfo]] = defaultdict(list)
        self._delegation_history: List[Dict[str, Any]] = []

    async def initialize(self) -> None:
        """Initialize registry and Neo4j indexes"""
        logger.info("HierarchicalAgentRegistry initialized")
        
        if self.neo4j:
            await self._create_indexes()

    async def _create_indexes(self) -> None:
        """Create Neo4j indexes for efficient querying"""
        indexes = [
            "CREATE INDEX agent_id IF NOT EXISTS FOR (a:Agent) ON (a.id)",
            "CREATE INDEX agent_type IF NOT EXISTS FOR (a:Agent) ON (a.type)",
            "CREATE INDEX capability_name IF NOT EXISTS FOR (c:Capability) ON (c.name)",
            "CREATE VECTOR INDEX capability_embedding IF NOT EXISTS FOR (c:Capability) ON (c.embedding) OPTIONS {indexConfig: {`vector.dimensions`: 1536, `vector.similarity_function`: 'cosine'}}",
        ]
        
        for index in indexes:
            try:
                await self.neo4j.run(index)
            except Exception as e:
                logger.warning(f"Index creation failed (may exist): {e}")

    async def register_agent(
        self,
        agent_id: str,
        name: str,
        agent_type: str,
        capabilities: Optional[List[Dict[str, Any]]] = None,
        parent_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Register a new agent with hierarchical support.
        
        Args:
            agent_id: Unique agent identifier
            name: Human-readable name
            agent_type: Type/category of agent
            capabilities: List of {name, proficiency, description} dicts
            parent_id: Optional parent agent ID for hierarchy
            metadata: Additional metadata
            
        Returns:
            Agent information dict
        """
        # Generate capability embeddings
        capability_vectors = []
        if capabilities:
            for cap in capabilities:
                embedding = await self._generate_capability_embedding(cap["name"], cap.get("description", ""))
                capability_vectors.append(CapabilityVector(
                    capability_name=cap["name"],
                    embedding=embedding,
                    proficiency=cap.get("proficiency", 0.5),
                    metadata=cap.get("metadata", {}),
                ))

        agent = {
            "agent_id": agent_id,
            "name": name,
            "agent_type": agent_type,
            "status": "idle",
            "capabilities": capabilities or [],
            "capability_vectors": capability_vectors,
            "reputation": 0.5,
            "created_at": datetime.now().timestamp(),
            "last_active": datetime.now().timestamp(),
            "metadata": metadata or {},
            "parent_id": parent_id,
            "children": [],
        }

        self._agents[agent_id] = agent
        self._capability_vectors[agent_id] = capability_vectors

        # Establish parent-child relationship
        if parent_id and parent_id in self._agents:
            await self._add_relationship(agent_id, parent_id, AgentRelationship.CHILD)
            await self._add_relationship(parent_id, agent_id, AgentRelationship.PARENT)
            self._agents[parent_id]["children"].append(agent_id)

        # Persist to Neo4j
        if self.neo4j:
            await self._persist_agent(agent)

        logger.info(f"Registered agent {agent_id} ({name}) with {len(capability_vectors)} capabilities")
        return agent

    async def _generate_capability_embedding(self, name: str, description: str) -> List[float]:
        """Generate embedding for capability"""
        if self.embedding_model:
            text = f"{name}: {description}"
            return await self.embedding_model.embed(text)
        # Fallback: deterministic hash-based embedding
        return self._hash_embedding(name + description)

    def _hash_embedding(self, text: str, dim: int = 1536) -> List[float]:
        """Generate deterministic pseudo-embedding from text hash"""
        import hashlib
        hash_bytes = hashlib.sha256(text.encode()).digest()
        # Expand to desired dimension
        result = []
        for i in range(dim):
            result.append((hash_bytes[i % len(hash_bytes)] - 128) / 128.0)
        return result

    async def _add_relationship(
        self,
        agent_id: str,
        related_agent_id: str,
        relationship: AgentRelationship,
    ) -> None:
        """Add agent relationship"""
        rel = AgentRelationshipInfo(
            agent_id=agent_id,
            related_agent_id=related_agent_id,
            relationship=relationship,
        )
        self._relationships[agent_id].append(rel)

    async def _persist_agent(self, agent: Dict[str, Any]) -> None:
        """Persist agent to Neo4j"""
        # Implementation would store agent node and capability relationships
        pass

    async def find_capable_agents(
        self,
        required_capabilities: List[str],
        min_proficiency: float = 0.5,
        strategy: str = "vector",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Find agents matching required capabilities.
        
        Args:
            required_capabilities: List of capability names or descriptions
            min_proficiency: Minimum proficiency threshold
            strategy: "vector" (semantic), "exact" (name match), or "hybrid"
            limit: Maximum results
            
        Returns:
            List of matching agents with match scores
        """
        if strategy == "vector" and self.embedding_model:
            return await self._vector_capability_search(required_capabilities, min_proficiency, limit)
        elif strategy == "hybrid":
            exact = await self._exact_capability_search(required_capabilities, min_proficiency, limit)
            vector = await self._vector_capability_search(required_capabilities, min_proficiency, limit)
            return self._merge_results(exact, vector, limit)
        else:
            return await self._exact_capability_search(required_capabilities, min_proficiency, limit)

    async def _exact_capability_search(
        self,
        required: List[str],
        min_proficiency: float,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Exact capability name matching"""
        results = []
        
        for agent_id, agent in self._agents.items():
            if agent["status"] == "decommissioned":
                continue
                
            match_score = 0
            matched_caps = []
            
            for cap in agent["capabilities"]:
                if cap["name"] in required and cap.get("proficiency", 0) >= min_proficiency:
                    match_score += cap.get("proficiency", 0)
                    matched_caps.append(cap["name"])
            
            if matched_caps:
                results.append({
                    "agent": agent,
                    "match_score": match_score / len(required),
                    "matched_capabilities": matched_caps,
                    "search_type": "exact",
                })
        
        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results[:limit]

    async def _vector_capability_search(
        self,
        required: List[str],
        min_proficiency: float,
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Semantic capability search using embeddings"""
        # Generate embeddings for required capabilities
        required_embeddings = []
        for cap in required:
            emb = await self._generate_capability_embedding(cap, "")
            required_embeddings.append(emb)
        
        results = []
        
        for agent_id, agent in self._agents.items():
            if agent["status"] == "decommissioned":
                continue
            
            agent_vectors = self._capability_vectors.get(agent_id, [])
            if not agent_vectors:
                continue
            
            # Calculate max similarity for each required capability
            total_similarity = 0
            matched_caps = []
            
            for req_emb, req_name in zip(required_embeddings, required):
                best_sim = 0
                best_cap = None
                
                for cap_vec in agent_vectors:
                    if cap_vec.proficiency < min_proficiency:
                        continue
                    sim = self._cosine_similarity(req_emb, cap_vec.embedding)
                    if sim > best_sim:
                        best_sim = sim
                        best_cap = cap_vec.capability_name
                
                if best_sim > 0.7:  # Threshold for semantic match
                    total_similarity += best_sim
                    matched_caps.append(f"{best_cap} (~{req_name})")
            
            if matched_caps:
                results.append({
                    "agent": agent,
                    "match_score": total_similarity / len(required),
                    "matched_capabilities": matched_caps,
                    "search_type": "vector",
                })
        
        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results[:limit]

    def _cosine_similarity(self, a: List[float], b: List[float]) -> float:
        """Calculate cosine similarity between vectors"""
        a_np = np.array(a)
        b_np = np.array(b)
        return float(np.dot(a_np, b_np) / (np.linalg.norm(a_np) * np.linalg.norm(b_np)))

    def _merge_results(
        self,
        exact: List[Dict],
        vector: List[Dict],
        limit: int,
    ) -> List[Dict[str, Any]]:
        """Merge and deduplicate exact and vector search results"""
        merged = {}
        
        for r in exact + vector:
            agent_id = r["agent"]["agent_id"]
            if agent_id not in merged or r["match_score"] > merged[agent_id]["match_score"]:
                merged[agent_id] = r
        
        results = list(merged.values())
        results.sort(key=lambda x: x["match_score"], reverse=True)
        return results[:limit]

    async def get_hierarchy(self, agent_id: str) -> Dict[str, Any]:
        """Get agent's position in hierarchy"""
        agent = self._agents.get(agent_id)
        if not agent:
            return {}
        
        return {
            "agent_id": agent_id,
            "parent_id": agent.get("parent_id"),
            "children": agent.get("children", []),
            "ancestors": await self._get_ancestors(agent_id),
            "descendants": await self._get_descendants(agent_id),
        }

    async def _get_ancestors(self, agent_id: str) -> List[str]:
        """Get all ancestor agent IDs"""
        ancestors = []
        current = self._agents.get(agent_id)
        while current and current.get("parent_id"):
            ancestors.append(current["parent_id"])
            current = self._agents.get(current["parent_id"])
        return ancestors

    async def _get_descendants(self, agent_id: str) -> List[str]:
        """Get all descendant agent IDs"""
        descendants = []
        queue = [agent_id]
        
        while queue:
            current_id = queue.pop(0)
            agent = self._agents.get(current_id)
            if agent:
                for child_id in agent.get("children", []):
                    descendants.append(child_id)
                    queue.append(child_id)
        
        return descendants

    async def get_subordinates(self, agent_id: str, direct_only: bool = False) -> List[Dict[str, Any]]:
        """Get subordinate agents (children, grandchildren, etc.)"""
        if direct_only:
            child_ids = self._agents.get(agent_id, {}).get("children", [])
        else:
            child_ids = await self._get_descendants(agent_id)
        
        return [self._agents[cid] for cid in child_ids if cid in self._agents]

    async def delegate_task(
        self,
        task: Dict[str, Any],
        delegator_id: str,
        required_capabilities: List[str],
        strategy: str = "best_match",
    ) -> Optional[str]:
        """
        Delegate task to capable subordinate or peer.
        
        Args:
            task: Task description
            delegator_id: Agent delegating the task
            required_capabilities: Required capabilities
            strategy: "best_match", "least_busy", "highest_reputation"
            
        Returns:
            Delegatee agent ID or None
        """
        # First try subordinates
        subordinates = await self.get_subordinates(delegator_id)
        subordinate_ids = [a["agent_id"] for a in subordinates]
        
        candidates = await self.find_capable_agents(
            required_capabilities,
            min_proficiency=0.6,
            strategy="hybrid",
            limit=20,
        )
        
        # Filter to subordinates first, then peers
        filtered = [c for c in candidates if c["agent"]["agent_id"] in subordinate_ids]
        if not filtered:
            filtered = candidates  # Fall back to any capable agent
        
        if not filtered:
            return None
        
        # Select based on strategy
        if strategy == "least_busy":
            filtered.sort(key=lambda x: x["agent"]["status"] != "idle")
        elif strategy == "highest_reputation":
            filtered.sort(key=lambda x: x["agent"].get("reputation", 0), reverse=True)
        # "best_match" already sorted by match_score
        
        delegatee = filtered[0]["agent"]["agent_id"]
        
        # Record delegation
        self._delegation_history.append({
            "task": task,
            "delegator": delegator_id,
            "delegatee": delegatee,
            "timestamp": datetime.now().timestamp(),
            "required_capabilities": required_capabilities,
            "match_score": filtered[0]["match_score"],
        })
        
        logger.info(f"Delegated task from {delegator_id} to {delegatee}")
        return delegatee

    def get_delegation_history(self, agent_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get delegation history"""
        if agent_id:
            return [d for d in self._delegation_history 
                   if d["delegator"] == agent_id or d["delegatee"] == agent_id]
        return self._delegation_history