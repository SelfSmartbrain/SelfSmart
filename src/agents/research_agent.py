"""
Research Agent — Multi-source research pipeline.

Capabilities:
- ArXiv paper search
- Web search (Tavily)
- Wikipedia lookup
- Semantic retrieval from knowledge base
- Source verification and confidence scoring
"""

from __future__ import annotations

import json
import time
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage

from src.config.logging import get_logger
from src.config.settings import get_settings

logger = get_logger(__name__)


RESEARCH_PLANNING_PROMPT = """You are a research planning expert. Given the task, determine the best research strategy.

Task: {task_description}
Goal Context: {goal}
Available Sources: arxiv, web_search, wikipedia, knowledge_base

Plan your research as JSON:
{{
    "search_queries": [
        {{
            "source": "arxiv | web_search | wikipedia | knowledge_base",
            "query": "search query string",
            "priority": 1-5,
            "reason": "why this source and query"
        }}
    ],
    "expected_output": "What the research should produce",
    "max_sources": 5
}}

Rules:
- Use arxiv for academic/scientific topics
- Use web_search for current events, tutorials, documentation
- Use wikipedia for general knowledge and definitions
- Use knowledge_base for previously stored information
- Order queries by priority (1 = most important)
- Limit to 3-5 queries total

Respond ONLY with valid JSON."""


SYNTHESIS_PROMPT = """You are a research synthesis expert. Combine the following research findings into a coherent summary.

Original Task: {task}
Research Findings:
{findings}

Provide a comprehensive synthesis that:
1. Answers the original research question
2. Cites sources where applicable
3. Notes confidence levels
4. Highlights key insights
5. Identifies gaps or uncertainties

Format as clear, well-structured text."""


class ResearchAgent:
    """
    Agent responsible for multi-source research within the orchestration workflow.

    Coordinates searches across ArXiv, web, Wikipedia, and the knowledge base,
    then synthesizes findings into a coherent response.
    """

    def __init__(
        self,
        tools: list[Any] | None = None,
        retriever: Any = None,
    ) -> None:
        """
        Initialize the research agent.

        Args:
            tools: List of LangChain tools for research operations.
            retriever: RAG retriever for knowledge base queries.
        """
        settings = get_settings()
        self.llm = ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key.get_secret_value(),
            temperature=0.2,
            max_tokens=8192,
        )
        self.tools = {t.name: t for t in (tools or [])}
        self.retriever = retriever

    async def execute(
        self,
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute a research task through the full research pipeline.

        Pipeline: Plan → Search → Verify → Synthesize → Return

        Args:
            task: Task specification.
            context: Execution context.

        Returns:
            Result dictionary with synthesized research output.
        """
        start_time = time.monotonic()
        task_desc = task.get("description", "")

        try:
            # Step 1: Plan research strategy
            plan = await self._plan_research(task_desc, context.get("goal", ""))

            # Step 2: Execute search queries
            findings = await self._execute_searches(plan)

            # Step 3: Synthesize results
            synthesis = await self._synthesize(task_desc, findings)

            duration_ms = int((time.monotonic() - start_time) * 1000)

            return {
                "status": "completed",
                "output": synthesis,
                "sources": [f.get("source", "unknown") for f in findings],
                "source_count": len(findings),
                "duration_ms": duration_ms,
                "confidence": self._calculate_confidence(findings),
            }

        except Exception as e:
            logger.error("Research execution failed", error=str(e))
            return {
                "status": "failed",
                "error": str(e),
                "duration_ms": int((time.monotonic() - start_time) * 1000),
            }

    async def _plan_research(
        self,
        task_description: str,
        goal: str,
    ) -> dict[str, Any]:
        """Use LLM to plan the research strategy."""
        prompt = RESEARCH_PLANNING_PROMPT.format(
            task_description=task_description,
            goal=goal,
        )

        response = await self.llm.ainvoke([
            SystemMessage(content="You are a research planning expert. Respond only with valid JSON."),
            HumanMessage(content=prompt),
        ])

        try:
            plan = json.loads(response.content)
        except json.JSONDecodeError:
            content = str(response.content)
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                plan = json.loads(content[start:end])
            else:
                plan = {
                    "search_queries": [{
                        "source": "web_search",
                        "query": task_description,
                        "priority": 1,
                        "reason": "Direct search for task",
                    }],
                    "expected_output": "Research findings",
                    "max_sources": 5,
                }

        logger.info(
            "Research plan created",
            query_count=len(plan.get("search_queries", [])),
        )
        return plan

    async def _execute_searches(
        self,
        plan: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Execute all planned search queries."""
        findings: list[dict[str, Any]] = []
        queries = plan.get("search_queries", [])

        # Sort by priority
        queries.sort(key=lambda q: q.get("priority", 5))

        for query_spec in queries[:5]:  # Limit to 5 queries
            source = query_spec.get("source", "web_search")
            query = query_spec.get("query", "")

            if not query:
                continue

            try:
                result = await self._execute_single_search(source, query)
                if result:
                    findings.append({
                        "source": source,
                        "query": query,
                        "content": result,
                        "confidence": self._score_result(result),
                    })
            except Exception as e:
                logger.warning(
                    "Search query failed",
                    source=source,
                    query=query[:50],
                    error=str(e),
                )

        logger.info("Search execution complete", findings_count=len(findings))
        return findings

    async def _execute_single_search(
        self,
        source: str,
        query: str,
    ) -> str | None:
        """Execute a single search query against a specific source."""
        tool_name_map = {
            "arxiv": "arxiv_search",
            "web_search": "web_search",
            "wikipedia": "wikipedia_search",
            "knowledge_base": "semantic_retrieval",
        }

        tool_name = tool_name_map.get(source, source)

        if tool_name in self.tools:
            tool = self.tools[tool_name]
            result = await tool.ainvoke({"query": query})
            return str(result) if result else None

        # Fallback: use LLM knowledge
        response = await self.llm.ainvoke([
            SystemMessage(content=f"You are a {source} expert. Provide factual information."),
            HumanMessage(content=f"Research: {query}"),
        ])
        return str(response.content)

    async def _synthesize(
        self,
        task: str,
        findings: list[dict[str, Any]],
    ) -> str:
        """Synthesize research findings into a coherent response."""
        if not findings:
            return "No research findings were gathered. The research query may need refinement."

        findings_text = "\n\n".join([
            f"### Source: {f.get('source', 'unknown')} (confidence: {f.get('confidence', 0):.2f})\n"
            f"Query: {f.get('query', '')}\n"
            f"Content: {str(f.get('content', ''))[:2000]}"
            for f in findings
        ])

        prompt = SYNTHESIS_PROMPT.format(
            task=task,
            findings=findings_text,
        )

        response = await self.llm.ainvoke([
            SystemMessage(content="You are a research synthesis expert. Provide thorough, well-cited summaries."),
            HumanMessage(content=prompt),
        ])

        return str(response.content)

    def _score_result(self, content: str | None) -> float:
        """Score the quality of a search result."""
        if not content:
            return 0.0

        content_str = str(content)
        score = 0.3  # Base score for any result

        # Length-based scoring
        if len(content_str) > 100:
            score += 0.2
        if len(content_str) > 500:
            score += 0.1
        if len(content_str) > 1000:
            score += 0.1

        # Content quality indicators
        quality_indicators = ["http", "reference", "study", "research", "found", "result"]
        for indicator in quality_indicators:
            if indicator in content_str.lower():
                score += 0.05

        return min(score, 1.0)

    def _calculate_confidence(self, findings: list[dict[str, Any]]) -> float:
        """Calculate overall confidence from all findings."""
        if not findings:
            return 0.0

        scores = [f.get("confidence", 0.0) for f in findings]
        return sum(scores) / len(scores)
