"""
ArXiv search tool for the Autonomous Agent Platform.

Searches the arXiv preprint repository for academic papers matching
a query string.  Returns structured results including title, authors,
abstract, publication date, PDF URL, and a relevance score.
"""

from __future__ import annotations

import asyncio
from typing import Any

import arxiv
from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.tools.base import AgentTool

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------


class ArxivSearchInput(BaseModel):
    """Input schema for ArxivSearchTool."""

    query: str = Field(
        ...,
        min_length=1,
        max_length=500,
        description="Search query for arXiv papers",
    )
    max_results: int = Field(
        default=5,
        ge=1,
        le=50,
        description="Maximum number of results to return",
    )


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------


class ArxivSearchTool(AgentTool):
    """Search the arXiv preprint repository for academic papers.

    Uses the ``arxiv`` Python package to query the arXiv API.  Results
    are sorted by relevance and include a simple relevance score based
    on term-frequency overlap between the query and the paper's
    title + abstract.

    Example usage::

        tool = ArxivSearchTool()
        result = await tool._arun(query="transformer attention mechanism")
    """

    name: str = "arxiv_search"
    description: str = (
        "Search arXiv for academic papers. Returns titles, authors, "
        "abstracts, publication dates, PDF URLs, and relevance scores."
    )
    args_schema: type[BaseModel] = ArxivSearchInput
    timeout_seconds: float = 45.0

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    async def _execute(self, **kwargs: Any) -> list[dict[str, Any]]:
        """Execute an arXiv search and return formatted results.

        Args:
            **kwargs: Validated fields from :class:`ArxivSearchInput`.

        Returns:
            A list of dicts, each representing one paper with keys:
            ``title``, ``authors``, ``abstract``, ``published``,
            ``pdf_url``, ``entry_id``, ``primary_category``,
            ``relevance_score``.
        """
        query: str = kwargs["query"]
        max_results: int = kwargs.get("max_results", 5)

        log = logger.bind(tool=self.name, query=query, max_results=max_results)
        log.debug("arxiv.search.start")

        # Build the search object — sorted by relevance
        search = arxiv.Search(
            query=query,
            max_results=max_results,
            sort_by=arxiv.SortCriterion.Relevance,
            sort_order=arxiv.SortOrder.Descending,
        )

        client = arxiv.Client(
            page_size=max_results,
            delay_seconds=1.0,
            num_retries=2,
        )

        # Run the synchronous arxiv search in a thread pool to avoid blocking
        def _sync_search():
            results: list[dict[str, Any]] = []
            query_terms = set(query.lower().split())
            for paper in client.results(search):
                relevance = self._compute_relevance(query_terms, paper.title, paper.summary)
                results.append(
                    {
                        "title": paper.title,
                        "authors": [author.name for author in paper.authors],
                        "abstract": paper.summary.strip(),
                        "published": paper.published.isoformat() if paper.published else None,
                        "pdf_url": paper.pdf_url,
                        "entry_id": paper.entry_id,
                        "primary_category": paper.primary_category,
                        "relevance_score": relevance,
                    }
                )
            # Sort by relevance descending
            results.sort(key=lambda r: r["relevance_score"], reverse=True)
            return results

        results = await asyncio.to_thread(_sync_search)

        log.info("arxiv.search.complete", result_count=len(results))
        return results

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_relevance(
        query_terms: set[str],
        title: str,
        abstract: str,
    ) -> float:
        """Compute a simple relevance score (0.0 – 1.0).

        The score is the fraction of distinct query terms found in the
        combined text of the title and abstract.  Title matches are
        weighted 2× more than abstract-only matches.

        Args:
            query_terms: Lower-cased set of query tokens.
            title: Paper title.
            abstract: Paper abstract/summary.

        Returns:
            A float between 0.0 and 1.0.
        """
        if not query_terms:
            return 0.0

        title_lower = title.lower()
        abstract_lower = abstract.lower()

        score = 0.0
        max_possible = len(query_terms) * 3  # max 3 pts per term

        for term in query_terms:
            if term in title_lower:
                score += 2.0  # title match weighted higher
            if term in abstract_lower:
                score += 1.0

        return round(min(score / max_possible, 1.0), 4) if max_possible > 0 else 0.0
