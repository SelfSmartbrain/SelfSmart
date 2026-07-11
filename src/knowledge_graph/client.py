"""Neo4j async client wrapper."""

from __future__ import annotations

import logging
from typing import Any, AsyncGenerator

from neo4j import AsyncGraphDatabase, AsyncDriver, AsyncSession

from src.config.settings import get_settings

logger = logging.getLogger(__name__)


class Neo4jClient:
    """Async client for Neo4j Knowledge Graph operations."""

    def __init__(self) -> None:
        self.settings = get_settings()
        self._driver: AsyncDriver | None = None

    async def initialize(self) -> None:
        """Initialize the Neo4j driver."""
        if self._driver is None:
            try:
                self._driver = AsyncGraphDatabase.driver(
                    self.settings.neo4j_uri,
                    auth=(self.settings.neo4j_user, self.settings.neo4j_password.get_secret_value()),
                )
                # Verify connectivity
                await self._driver.verify_connectivity()
                logger.info("Connected to Neo4j knowledge graph.")
            except Exception as e:
                logger.error(f"Failed to connect to Neo4j: {e}")
                raise

    async def close(self) -> None:
        """Close the Neo4j driver."""
        if self._driver is not None:
            await self._driver.close()
            self._driver = None
            logger.info("Neo4j connection closed.")

    def session(self) -> AsyncSession:
        """Get an async Neo4j session.
        
        Usage:
            async with client.session() as session:
                result = await session.run("MATCH (n) RETURN n LIMIT 1")
        """
        if self._driver is None:
            raise RuntimeError("Neo4j client not initialized. Call initialize() first.")
        return self._driver.session()

    async def execute_query(self, query: str, parameters: dict[str, Any] | None = None) -> list[dict[str, Any]]:
        """Utility method to execute a query and fetch all results as a list of dicts."""
        if parameters is None:
            parameters = {}
            
        async with self.session() as session:
            try:
                result = await session.run(query, parameters)
                records = await result.data()
                return records
            except Exception as e:
                logger.error(f"Error executing Cypher query: {e}\nQuery: {query}")
                raise
