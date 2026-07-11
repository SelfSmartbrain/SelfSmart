"""
Read-only database query tool for the Autonomous Agent Platform.

Executes SQL ``SELECT`` statements against a PostgreSQL database.
DDL and DML statements are blocked for safety.  Queries are subject
to a configurable timeout.

Uses a connection pool for efficient connection reuse.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Optional

import asyncpg
from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.config.settings import get_settings
from src.tools.base import AgentTool, ToolExecutionError

logger = get_logger(__name__)

# Module-level connection pool (shared across all tool instances)
_connection_pool: Optional[asyncpg.Pool] = None
_pool_lock = asyncio.Lock()

# ---------------------------------------------------------------------------
# SQL security
# ---------------------------------------------------------------------------

# Statements that are categorically blocked.
_BLOCKED_KEYWORDS: frozenset[str] = frozenset(
    {
        "INSERT",
        "UPDATE",
        "DELETE",
        "DROP",
        "CREATE",
        "ALTER",
        "TRUNCATE",
        "GRANT",
        "REVOKE",
        "COPY",
        "EXECUTE",
        "VACUUM",
        "REINDEX",
        "CLUSTER",
        "COMMENT",
        "LOCK",
        "NOTIFY",
        "LISTEN",
        "UNLISTEN",
        "LOAD",
        "SECURITY",
        "REASSIGN",
    }
)

# Pattern to match the leading statement keyword (after optional CTEs).
_LEADING_KEYWORD_RE = re.compile(
    r"^\s*(?:WITH\b.+?\)\s*)?(\w+)",
    re.IGNORECASE | re.DOTALL,
)

# Pattern to detect stacked queries (semicolons followed by another statement)
_STACKED_QUERY_RE = re.compile(
    r";\s*\w",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------

class DatabaseQueryInput(BaseModel):
    """Input schema for DatabaseQueryTool."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=10_000,
        description="SQL SELECT query to execute",
    )
    params: dict[str, Any] | None = Field(
        default=None,
        description="Optional named parameters for parameterised queries",
    )


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------

class DatabaseQueryTool(AgentTool):
    """Execute read-only SQL queries against PostgreSQL.

    Only ``SELECT`` and ``EXPLAIN`` statements are permitted.  Any
    attempt to run DDL (``CREATE``, ``DROP``, etc.) or DML (``INSERT``,
    ``UPDATE``, ``DELETE``) will be rejected before the query reaches
    the database.

    Queries are executed with a statement timeout to protect against
    long-running analytical queries.  Results are returned as a list
    of dicts.

    Example usage::

        tool = DatabaseQueryTool()
        result = await tool._arun(query="SELECT id, name FROM users LIMIT 10")
    """

    name: str = "database_query"
    description: str = (
        "Execute read-only SQL SELECT queries against PostgreSQL. "
        "Returns results as a list of dicts. DDL/DML statements are blocked."
    )
    args_schema: type[BaseModel] = DatabaseQueryInput
    timeout_seconds: float = 60.0
    max_retries: int = 2

    # Maximum rows to return (safety cap)
    _max_rows: int = 1000
    # Statement timeout in milliseconds
    _statement_timeout_ms: int = 30_000

    @classmethod
    async def _get_pool(cls) -> asyncpg.Pool:
        """Get or create the shared connection pool."""
        global _connection_pool
        if _connection_pool is None:
            async with _pool_lock:
                if _connection_pool is None:
                    settings = get_settings()
                    dsn = (
                        f"postgresql://{settings.postgres_user}"
                        f":{settings.postgres_password.get_secret_value()}"
                        f"@{settings.postgres_host}:{settings.postgres_port}"
                        f"/{settings.postgres_db}"
                    )
                    _connection_pool = await asyncpg.create_pool(
                        dsn=dsn,
                        min_size=2,
                        max_size=10,
                        timeout=10,
                        statement_cache_size=0,
                    )
                    logger.info("Database connection pool created")
        return _connection_pool

    @classmethod
    async def close_pool(cls) -> None:
        """Close the connection pool (for shutdown)."""
        global _connection_pool
        if _connection_pool is not None:
            await _connection_pool.close()
            _connection_pool = None
            logger.info("Database connection pool closed")

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        """Validate and execute a read-only SQL query.

        Args:
            **kwargs: Validated fields from :class:`DatabaseQueryInput`.

        Returns:
            A dict with ``columns``, ``rows`` (list of dicts),
            ``row_count``, and ``query``.
        """
        query: str = kwargs["query"]
        params: dict[str, Any] | None = kwargs.get("params")

        log = logger.bind(tool=self.name, query_len=len(query))
        log.debug("database_query.validate.start")

        # --- Security validation ---
        self._validate_query(query)

        log.debug("database_query.execute.start")

        # --- Get connection from pool ---
        pool = await self._get_pool()
        
        async with pool.acquire() as conn:
            try:
                # Set a statement-level timeout
                await conn.execute(
                    f"SET statement_timeout = {self._statement_timeout_ms}"
                )

                # Apply LIMIT safety net if not already present
                effective_query = self._apply_limit(query)

                # Execute with optional positional params
                if params:
                    # asyncpg uses $1, $2, ... for positional params.
                    # We convert named params to positional.
                    effective_query, positional = self._named_to_positional(
                        effective_query, params
                    )
                    rows = await conn.fetch(effective_query, *positional)
                else:
                    rows = await conn.fetch(effective_query)

                # Format results
                if rows:
                    columns = list(rows[0].keys())
                    result_rows = [dict(r) for r in rows]
                else:
                    columns = []
                    result_rows = []

            except asyncpg.PostgresError as exc:
                raise ToolExecutionError(
                    tool_name=self.name,
                    message=f"Database error: {exc}",
                    cause=exc,
                ) from exc

        result: dict[str, Any] = {
            "query": query,
            "columns": columns,
            "rows": result_rows,
            "row_count": len(result_rows),
            "truncated": len(result_rows) >= self._max_rows,
        }

        log.info("database_query.complete", row_count=len(result_rows))
        return result

    # ------------------------------------------------------------------
    # Query validation
    # ------------------------------------------------------------------

    @classmethod
    def _validate_query(cls, query: str) -> None:
        """Ensure the query is a safe read-only statement.

        Args:
            query: Raw SQL string.

        Raises:
            ToolExecutionError: If the query contains blocked keywords
                or patterns.
        """
        stripped = query.strip().rstrip(";").strip()

        if not stripped:
            raise ToolExecutionError(
                tool_name="database_query",
                message="Empty query.",
            )

        # Block stacked queries
        if _STACKED_QUERY_RE.search(stripped):
            raise ToolExecutionError(
                tool_name="database_query",
                message="Multiple statements (stacked queries) are not allowed.",
            )

        # Extract leading keyword
        match = _LEADING_KEYWORD_RE.match(stripped)
        if not match:
            raise ToolExecutionError(
                tool_name="database_query",
                message="Could not determine statement type.",
            )

        leading = match.group(1).upper()
        allowed = {"SELECT", "EXPLAIN", "WITH", "VALUES", "TABLE", "SHOW"}
        if leading not in allowed:
            raise ToolExecutionError(
                tool_name="database_query",
                message=f"Only read-only queries are allowed. Got: {leading}.",
            )

        # Scan for blocked keywords anywhere in the query
        upper = stripped.upper()
        for kw in _BLOCKED_KEYWORDS:
            # Use word-boundary check to avoid false positives
            pattern = rf"\b{kw}\b"
            if re.search(pattern, upper):
                raise ToolExecutionError(
                    tool_name="database_query",
                    message=f"Blocked keyword detected: {kw}.",
                )

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _apply_limit(self, query: str) -> str:
        """Append a LIMIT clause if one is not already present.

        Args:
            query: SQL query string.

        Returns:
            Query with an appended ``LIMIT`` if none was specified.
        """
        upper = query.upper()
        if "LIMIT" not in upper:
            return f"{query.rstrip().rstrip(';')} LIMIT {self._max_rows}"
        return query

    @staticmethod
    def _named_to_positional(
        query: str, params: dict[str, Any]
    ) -> tuple[str, list[Any]]:
        """Convert ``:name``-style named parameters to ``$N`` positional style.

        Args:
            query: SQL query with ``:name`` placeholders.
            params: Dict mapping names to values.

        Returns:
            A tuple of (rewritten_query, positional_values).
        """
        positional: list[Any] = []
        counter = 0
        name_to_idx: dict[str, int] = {}

        def replacer(m: re.Match[str]) -> str:
            nonlocal counter
            name = m.group(1)
            if name not in name_to_idx:
                counter += 1
                name_to_idx[name] = counter
                positional.append(params.get(name))
            return f"${name_to_idx[name]}"

        rewritten = re.sub(r":(\w+)", replacer, query)
        return rewritten, positional