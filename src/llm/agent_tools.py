"""
Agent Tools Framework - Autonomous Tool Execution
Provides a secure environment for the LLM to execute external tools.
"""

import logging
import subprocess
import json
import httpx
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

class ToolExecutor:
    """
    Executes tools requested by the Agentic LLM.
    """

    def __init__(self):
        self.tools = {
            "web_search": self._web_search,
            "python_repl": self._python_repl,
            "get_datetime": self._get_datetime
        }
        logger.info("Tool executor initialized")

    async def execute(self, tool_name: str, args: Dict[str, Any]) -> Any:
        """Executes a named tool with provided arguments."""
        if tool_name not in self.tools:
            return {"error": f"Tool '{tool_name}' not found."}

        logger.info(f"Executing tool: {tool_name} with args: {args}")
        try:
            return await self.tools[tool_name](**args)
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {e}")
            return {"error": str(e)}

    async def _web_search(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Real web search using DuckDuckGo Instant Answer API.
        No API key required. Gracefully degrades on failure.
        """
        try:
            async with httpx.AsyncClient(timeout=8.0) as client:
                resp = await client.get(
                    "https://api.duckduckgo.com/",
                    params={
                        "q": query,
                        "format": "json",
                        "no_html": 1,
                        "skip_disambig": 1,
                    },
                    headers={"User-Agent": "SelfSmartAI/1.0"},
                )
                resp.raise_for_status()
                data = resp.json()

            results = []

            if data.get("AbstractText"):
                results.append({
                    "title": data.get("Heading", query),
                    "snippet": data["AbstractText"][:400],
                    "url": data.get("AbstractURL", ""),
                    "source": "DuckDuckGo",
                })

            for topic in data.get("RelatedTopics", []):
                if len(results) >= max_results:
                    break
                if isinstance(topic, dict) and topic.get("Text"):
                    results.append({
                        "title": topic["Text"][:80],
                        "snippet": topic["Text"][:400],
                        "url": topic.get("FirstURL", ""),
                        "source": "DuckDuckGo Related",
                    })

            if not results:
                return {
                    "query": query,
                    "results": [],
                    "note": "No results found — try rephrasing.",
                }

            return {"query": query, "result_count": len(results), "results": results}

        except httpx.TimeoutException:
            logger.warning(f"Web search timed out for query: {query}")
            return {"query": query, "error": "Search timed out after 8 seconds"}
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return {"query": query, "error": f"Search unavailable: {str(e)[:100]}"}

    async def _python_repl(self, code: str) -> Dict[str, Any]:
        """Safely executes Python code in a subprocess."""
        try:
            result = subprocess.run(
                ['python3', '-c', code],
                capture_output=True,
                text=True,
                timeout=5
            )
            return {"stdout": result.stdout, "stderr": result.stderr}
        except Exception as e:
            return {"error": str(e)}

    async def _get_datetime(self) -> Dict[str, str]:
        """Returns current system datetime."""
        from datetime import datetime
        return {"datetime": datetime.now().isoformat()}
