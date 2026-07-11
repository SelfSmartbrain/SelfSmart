"""Knowledge Graph Manager."""

from __future__ import annotations

import logging
import re
from typing import Any

from .client import Neo4jClient

logger = logging.getLogger(__name__)

def _sanitize_identifier(identifier: str) -> str:
    """Ensure identifier only contains alphanumeric characters and underscores."""
    if not re.match(r"^[A-Za-z0-9_]+$", identifier):
        raise ValueError(f"Invalid Cypher identifier: {identifier}")
    return identifier

class KnowledgeGraphManager:
    """Provides high-level operations for storing and querying the Knowledge Graph."""

    def __init__(self, client: Neo4jClient) -> None:
        self.client = client

    async def add_concept(self, name: str, domain: str, properties: dict[str, Any] | None = None) -> None:
        """Add a high-level concept node to the knowledge graph."""
        props = properties or {}
        query = """
        MERGE (c:Concept {name: $name})
        SET c.domain = $domain, c += $props
        RETURN c
        """
        await self.client.execute_query(query, {"name": name, "domain": domain, "props": props})
        logger.debug(f"Added concept to KG: {name} ({domain})")

    async def add_entity(self, entity_id: str, label: str, properties: dict[str, Any] | None = None) -> None:
        """Add a specific entity instance to the knowledge graph."""
        props = properties or {}
        # Cypher doesn't allow dynamic labels in MERGE easily via parameters,
        # so we merge on a generic Entity label and set the specific label.
        # But for this implementation, we can just use the properties.
        safe_label = _sanitize_identifier(label)
        query = f"""
        MERGE (e:{safe_label} {{id: $entity_id}})
        SET e += $props
        RETURN e
        """
        await self.client.execute_query(query, {"entity_id": entity_id, "props": props})

    async def add_relationship(
        self,
        source_id: str,
        source_label: str,
        target_id: str,
        target_label: str,
        rel_type: str,
        properties: dict[str, Any] | None = None,
    ) -> None:
        """Create a directed relationship between two nodes."""
        props = properties or {}
        safe_source = _sanitize_identifier(source_label)
        safe_target = _sanitize_identifier(target_label)
        safe_rel = _sanitize_identifier(rel_type)
        query = f"""
        MATCH (a:{safe_source} {{id: $source_id}})
        MATCH (b:{safe_target} {{id: $target_id}})
        MERGE (a)-[r:{safe_rel}]->(b)
        SET r += $props
        RETURN r
        """
        await self.client.execute_query(
            query,
            {
                "source_id": source_id,
                "target_id": target_id,
                "props": props,
            },
        )
        logger.debug(f"Added relationship: {source_id} -[{rel_type}]-> {target_id}")

    async def add_concept_relationship(
        self, source_name: str, target_name: str, rel_type: str, properties: dict[str, Any] | None = None
    ) -> None:
        """Create a directed relationship between two Concepts."""
        props = properties or {}
        safe_rel = _sanitize_identifier(rel_type)
        query = f"""
        MATCH (a:Concept {{name: $source_name}})
        MATCH (b:Concept {{name: $target_name}})
        MERGE (a)-[r:{safe_rel}]->(b)
        SET r += $props
        RETURN r
        """
        await self.client.execute_query(
            query,
            {
                "source_name": source_name,
                "target_name": target_name,
                "props": props,
            },
        )

    async def get_concept_subgraph(self, concept_name: str, depth: int = 2) -> list[dict[str, Any]]:
        """Retrieve a subgraph centered around a specific concept."""
        query = """
        MATCH path = (c:Concept {name: $concept_name})-[*1..$depth]-(related)
        RETURN path
        """
        # Note: Cypher parameters can't bind to variable path lengths (1..$depth), 
        # so we inject depth into the string directly. Safe since it's an int.
        safe_query = query.replace("$depth", str(depth))
        return await self.client.execute_query(safe_query, {"concept_name": concept_name})
