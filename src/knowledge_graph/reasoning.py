"""Knowledge Graph Reasoning."""

from __future__ import annotations

import logging
from typing import Any

from .client import Neo4jClient

logger = logging.getLogger(__name__)


class KnowledgeGraphReasoner:
    """Handles semantic traversal and reasoning over the Knowledge Graph."""

    def __init__(self, client: Neo4jClient) -> None:
        self.client = client

    async def detect_contradictions(self, domain: str | None = None) -> list[dict[str, Any]]:
        """
        Scan the graph for nodes that have CONTRADICTS relationships.
        Optionally filter by a specific domain.
        """
        query = """
        MATCH (a:Concept)-[r:CONTRADICTS]->(b:Concept)
        """
        if domain:
            query += " WHERE a.domain = $domain OR b.domain = $domain"

        query += " RETURN a.name AS concept_a, b.name AS concept_b, r.reason AS reason"

        return await self.client.execute_query(query, {"domain": domain})

    async def find_missing_prerequisites(self) -> list[dict[str, Any]]:
        """
        Find concepts that are REQUIRED_BY another concept, but do not exist in the graph,
        or are marked as incomplete.
        This represents a knowledge gap.
        """
        # A simple heuristic: if a node has very few incoming relationships
        # or properties, it might be a shallow stub.
        query = """
        MATCH (a:Concept)-[:REQUIRES]->(stub:Concept)
        WHERE stub.is_stub = true
        RETURN a.name AS dependent, stub.name AS missing_prerequisite
        """
        return await self.client.execute_query(query)

    async def get_domain_coverage(self, domain: str) -> dict[str, Any]:
        """Evaluate how densely connected a specific domain is."""
        query = """
        MATCH (c:Concept {domain: $domain})
        OPTIONAL MATCH (c)-[r]-()
        WITH count(DISTINCT c) AS concept_count, count(r) AS rel_count
        RETURN concept_count, rel_count, 
               CASE WHEN concept_count = 0 THEN 0.0 ELSE toFloat(rel_count)/concept_count END AS density
        """
        results = await self.client.execute_query(query, {"domain": domain})
        if results:
            return results[0]
        return {"concept_count": 0, "rel_count": 0, "density": 0.0}
