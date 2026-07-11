"""
Short-Term Memory (Redis).

Provides fast, ephemeral storage for session context, intermediate task results,
and caching. Uses Redis for key-value storage with TTLs.
"""

from __future__ import annotations

import json
from typing import Any

from redis.asyncio import Redis

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)


class ShortTermMemory:
    """
    Redis-backed short-term memory system.
    
    Used for session context, intermediate agent states, and fast caching.
    All data is stored with an expiration (TTL).
    """

    def __init__(self) -> None:
        """Initialize the Redis client."""
        settings = get_settings()
        self.redis = Redis.from_url(
            str(settings.redis_url),
            decode_responses=True,
        )

    async def store(
        self,
        session_id: str,
        key: str,
        value: Any,
        ttl: int = 3600,
    ) -> None:
        """
        Store a value in short-term memory.

        Args:
            session_id: The session identifier.
            key: The specific memory key.
            value: The data to store (will be JSON serialized).
            ttl: Time-to-live in seconds (default: 1 hour).
        """
        full_key = f"session:{session_id}:{key}"
        try:
            serialized = json.dumps(value)
            await self.redis.setex(full_key, ttl, serialized)
            logger.debug("Stored short-term memory", session=session_id, key=key)
        except Exception as e:
            logger.error("Failed to store short-term memory", error=str(e), key=full_key)

    async def get(
        self,
        session_id: str,
        key: str,
    ) -> Any | None:
        """
        Retrieve a value from short-term memory.

        Args:
            session_id: The session identifier.
            key: The specific memory key.

        Returns:
            The parsed value or None if not found.
        """
        full_key = f"session:{session_id}:{key}"
        try:
            data = await self.redis.get(full_key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.error("Failed to retrieve short-term memory", error=str(e), key=full_key)
            return None

    async def get_all(
        self,
        session_id: str,
    ) -> dict[str, Any]:
        """
        Retrieve all short-term memory for a session.

        Args:
            session_id: The session identifier.

        Returns:
            Dictionary of all keys and values for the session.
        """
        pattern = f"session:{session_id}:*"
        result: dict[str, Any] = {}
        
        try:
            cursor = 0
            while True:
                cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
                if keys:
                    values = await self.redis.mget(keys)
                    for k, v in zip(keys, values):
                        if v:
                            # Extract the original key name
                            short_key = k.split(":")[-1]
                            result[short_key] = json.loads(v)
                
                if cursor == 0:
                    break
                    
            return result
        except Exception as e:
            logger.error("Failed to retrieve all short-term memory", error=str(e), session=session_id)
            return {}

    async def delete(
        self,
        session_id: str,
        key: str,
    ) -> None:
        """Delete a specific memory key."""
        full_key = f"session:{session_id}:{key}"
        await self.redis.delete(full_key)

    async def clear_session(
        self,
        session_id: str,
    ) -> None:
        """Clear all short-term memory for a session."""
        pattern = f"session:{session_id}:*"
        cursor = 0
        while True:
            cursor, keys = await self.redis.scan(cursor, match=pattern, count=100)
            if keys:
                await self.redis.delete(*keys)
            if cursor == 0:
                break
        logger.info("Cleared session memory", session=session_id)

    async def close(self) -> None:
        """Close the Redis connection."""
        await self.redis.close()
