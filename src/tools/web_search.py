"""
Web search tool for the Autonomous Agent Platform.

Uses the Tavily Search API via raw ``httpx`` calls (no LangChain wrapper)
to perform web searches.  Supports both *basic* and *advanced* search
depths and gracefully degrades when no API key is configured.
"""

from __future__ import annotations

from typing import Any, Literal

import httpx
from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.config.settings import get_settings
from src.tools.base import AgentTool, ToolExecutionError

logger = get_logger(__name__)

TAVILY_API_URL = "https://api.tavily.com/search"


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------

class WebSearchInput(BaseModel):
    """Input schema for WebSearchTool."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=1000,
        description="Search query string",
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=20,
        description="Maximum number of results to return",
    )
    search_depth: Literal["basic", "advanced"] = Field(
        default="basic",
        description="Search depth — 'basic' is faster, 'advanced' is more thorough",
    )


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------

class WebSearchTool(AgentTool):
    """Search the web using the Tavily Search API.

    Performs internet searches and returns structured results including
    title, URL, content snippet, and relevance score.

    If the ``TAVILY_API_KEY`` setting is not configured the tool returns
    a clear error message rather than raising an exception, enabling the
    agent to fall back to alternative information sources.

    Example usage::

        tool = WebSearchTool()
        result = await tool._arun(query="latest AI research 2026")
    """

    name: str = "web_search"
    description: str = (
        "Search the web using Tavily API. Returns titles, URLs, "
        "content snippets, and relevance scores."
    )
    args_schema: type[BaseModel] = WebSearchInput
    timeout_seconds: float = 30.0

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        """Execute a web search via the Tavily API.

        Args:
            **kwargs: Validated fields from :class:`WebSearchInput`.

        Returns:
            A dict with ``query``, ``results`` (list of result dicts),
            and ``result_count``.
        """
        query: str = kwargs["query"]
        max_results: int = kwargs.get("max_results", 5)
        search_depth: str = kwargs.get("search_depth", "basic")

        settings = get_settings()
        api_key = settings.tavily_api_key

        if not api_key:
            return {
                "query": query,
                "results": [],
                "result_count": 0,
                "error": (
                    "Tavily API key not configured. Set the TAVILY_API_KEY "
                    "environment variable to enable web search."
                ),
            }

        log = logger.bind(tool=self.name, query=query, depth=search_depth)
        log.debug("web_search.start")

        payload = {
            "api_key": api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": True,
            "include_raw_content": False,
        }

        async with httpx.AsyncClient(timeout=self.timeout_seconds) as client:
            response = await client.post(TAVILY_API_URL, json=payload)

            if response.status_code != 200:
                raise ToolExecutionError(
                    tool_name=self.name,
                    message=(
                        f"Tavily API returned status {response.status_code}: "
                        f"{response.text[:500]}"
                    ),
                )

            data = response.json()

        results = self._format_results(data)

        log.info("web_search.complete", result_count=len(results))

        return {
            "query": query,
            "answer": data.get("answer"),
            "results": results,
            "result_count": len(results),
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_results(data: dict[str, Any]) -> list[dict[str, Any]]:
        """Extract and normalise individual results from the API response.

        Args:
            data: Raw JSON response from the Tavily API.

        Returns:
            A list of dicts with ``title``, ``url``, ``content``, and
            ``relevance_score`` keys.
        """
        formatted: list[dict[str, Any]] = []

        for item in data.get("results", []):
            formatted.append(
                {
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "content": item.get("content", ""),
                    "relevance_score": item.get("score", 0.0),
                }
            )

        return formatted
