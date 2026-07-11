"""
Wikipedia search tool for the Autonomous Agent Platform.

Uses the ``wikipedia-api`` (``wikipediaapi``) package to look up
Wikipedia articles.  Returns the page title, summary, full URL, and
categories.
"""

from __future__ import annotations

from typing import Any

import wikipediaapi
from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.tools.base import AgentTool

logger = get_logger(__name__)

_USER_AGENT = "AutonomousAgentPlatform/0.1.0 (https://github.com/agent-platform)"


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------

class WikipediaSearchInput(BaseModel):
    """Input schema for WikipediaSearchTool."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=300,
        description="Wikipedia article title or search query",
    )
    language: str = Field(
        default="en",
        min_length=2,
        max_length=10,
        description="Wikipedia language edition code (e.g. 'en', 'de', 'fr')",
    )


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------

class WikipediaSearchTool(AgentTool):
    """Look up Wikipedia articles.

    Given a query, the tool first attempts a direct page lookup.  If the
    exact title is not found it falls back to searching Wikipedia's
    suggestion API to find the closest match.

    Returns the page title, a summary (first section), the full URL, and
    the article's categories.

    Example usage::

        tool = WikipediaSearchTool()
        result = await tool._arun(query="Transformer (deep learning)")
    """

    name: str = "wikipedia_search"
    description: str = (
        "Search Wikipedia for articles. Returns page title, summary, "
        "full URL, and categories."
    )
    args_schema: type[BaseModel] = WikipediaSearchInput
    timeout_seconds: float = 30.0

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        """Fetch a Wikipedia article matching the query.

        Args:
            **kwargs: Validated fields from :class:`WikipediaSearchInput`.

        Returns:
            A dict with ``title``, ``summary``, ``url``, ``categories``,
            ``sections``, and ``found`` (bool).
        """
        query: str = kwargs["query"]
        language: str = kwargs.get("language", "en")

        log = logger.bind(tool=self.name, query=query, language=language)
        log.debug("wikipedia.search.start")

        wiki = wikipediaapi.Wikipedia(
            user_agent=_USER_AGENT,
            language=language,
            extract_format=wikipediaapi.ExtractFormat.WIKI,
        )

        # Try direct page lookup first
        page = wiki.page(query)

        if not page.exists():
            # Attempt to search for a close match using a title variant
            # wikipediaapi doesn't expose a search endpoint so we try
            # a few common normalisations.
            variants = self._title_variants(query)
            for variant in variants:
                page = wiki.page(variant)
                if page.exists():
                    break

        if not page.exists():
            log.info("wikipedia.search.not_found", query=query)
            return {
                "found": False,
                "query": query,
                "title": None,
                "summary": None,
                "url": None,
                "categories": [],
                "sections": [],
                "message": f"No Wikipedia article found for '{query}'.",
            }

        # Extract section titles (top-level only)
        section_titles = [s.title for s in page.sections]

        # Extract categories, stripping the "Category:" prefix
        categories = sorted(
            cat.replace("Category:", "")
            for cat in page.categories.keys()
        )

        # Truncate summary to a reasonable length to keep context lean
        summary = page.summary[:3000] if page.summary else ""

        result: dict[str, Any] = {
            "found": True,
            "query": query,
            "title": page.title,
            "summary": summary,
            "url": page.fullurl,
            "categories": categories[:30],  # cap for context window
            "sections": section_titles[:25],
        }

        log.info(
            "wikipedia.search.complete",
            title=page.title,
            summary_len=len(summary),
            category_count=len(categories),
        )

        return result

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _title_variants(query: str) -> list[str]:
        """Generate plausible Wikipedia article title variants.

        Wikipedia article titles follow specific capitalisation and
        formatting conventions.  This helper generates a handful of
        likely variants to improve lookup success.

        Args:
            query: The original search query.

        Returns:
            A list of up to 5 title variants to try.
        """
        variants: list[str] = []

        # Title case
        title_cased = query.title()
        if title_cased != query:
            variants.append(title_cased)

        # Capitalise first letter only
        first_upper = query[0].upper() + query[1:] if len(query) > 1 else query.upper()
        if first_upper != query and first_upper not in variants:
            variants.append(first_upper)

        # Replace hyphens with spaces
        no_hyphens = query.replace("-", " ")
        if no_hyphens != query and no_hyphens not in variants:
            variants.append(no_hyphens)

        # Replace underscores with spaces
        no_underscores = query.replace("_", " ")
        if no_underscores != query and no_underscores not in variants:
            variants.append(no_underscores)

        return variants[:5]
