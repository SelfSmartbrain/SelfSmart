"""
Memory Agent — Manages short-term and long-term memory operations.

Provides a unified interface for:
- Storing episodic, semantic, and procedural memories
- Recalling memories via semantic search
- Memory consolidation and importance ranking
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


MEMORY_ANALYSIS_PROMPT = """Analyze the following content and determine what memories should be stored.

Task: {task_description}
Content: {content}
Existing Memories: {existing_memories}

For each memory to store, provide:
{{
    "memories": [
        {{
            "content": "The memory content (concise but complete)",
            "memory_type": "episodic | semantic | procedural",
            "importance_score": 0.0-1.0,
            "tags": ["relevant", "tags"]
        }}
    ]
}}

Rules:
- episodic: specific events or interactions
- semantic: facts, knowledge, or concepts
- procedural: how-to knowledge or strategies
- Avoid duplicating existing memories
- Rate importance based on likely future usefulness

Respond ONLY with valid JSON."""


class MemoryAgent:
    """
    Agent responsible for memory operations within the orchestration workflow.

    Wraps the short-term and long-term memory systems and provides
    task-level memory operations for the orchestrator.
    """

    def __init__(
        self,
        short_term_memory: Any = None,
        long_term_memory: Any = None,
    ) -> None:
        """
        Initialize the memory agent.

        Args:
            short_term_memory: ShortTermMemory instance (Redis-backed).
            long_term_memory: LongTermMemory instance (PostgreSQL + Qdrant).
        """
        settings = get_settings()
        self.llm = ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key.get_secret_value(),
            temperature=0.1,
            max_tokens=4096,
        )
        self.short_term = short_term_memory
        self.long_term = long_term_memory

    async def execute(
        self,
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute a memory operation based on the task specification.

        Args:
            task: Task specification with description and parameters.
            context: Execution context with goal, user_id, and previous results.

        Returns:
            Result dictionary with status and output.
        """
        start_time = time.monotonic()
        description = task.get("description", "").lower()

        try:
            if "store" in description or "save" in description or "remember" in description:
                result = await self._store_operation(task, context)
            elif "recall" in description or "retrieve" in description or "search" in description:
                result = await self._recall_operation(task, context)
            elif "consolidate" in description or "merge" in description:
                result = await self._consolidate_operation(context)
            else:
                # Default: analyze content and store relevant memories
                result = await self._analyze_and_store(task, context)

            duration_ms = int((time.monotonic() - start_time) * 1000)
            return {
                "status": "completed",
                "output": result,
                "duration_ms": duration_ms,
            }

        except Exception as e:
            logger.error("Memory operation failed", error=str(e), task_id=task.get("id"))
            return {
                "status": "failed",
                "error": str(e),
                "duration_ms": int((time.monotonic() - start_time) * 1000),
            }

    async def recall(
        self,
        query: str,
        user_id: str,
        memory_type: str | None = None,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """
        Recall memories relevant to a query.

        Args:
            query: Search query for memory recall.
            user_id: User whose memories to search.
            memory_type: Optional filter by memory type.
            limit: Maximum number of memories to return.

        Returns:
            List of memory records with relevance scores.
        """
        if self.long_term:
            try:
                return await self.long_term.recall(
                    query=query,
                    user_id=user_id,
                    memory_type=memory_type,
                    limit=limit,
                )
            except Exception as e:
                logger.warning("Long-term memory recall failed", error=str(e))
                return []
        return []

    async def store(
        self,
        content: str,
        user_id: str,
        memory_type: str = "semantic",
        importance: float = 0.5,
        metadata: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Store a memory in long-term storage.

        Args:
            content: Memory content.
            user_id: User who owns this memory.
            memory_type: Type of memory (episodic, semantic, procedural).
            importance: Importance score (0.0 to 1.0).
            metadata: Additional metadata.

        Returns:
            Stored memory record.
        """
        if self.long_term:
            return await self.long_term.store(
                content=content,
                user_id=user_id,
                memory_type=memory_type,
                metadata=metadata or {},
                importance=importance,
            )
        return {"status": "skipped", "reason": "No long-term memory configured"}

    async def _store_operation(
        self,
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Store content from task results as memories."""
        user_id = context.get("user_id", "unknown")
        previous_results = context.get("previous_results", {})

        # Gather content to store
        content_to_store = task.get("description", "")
        for result in previous_results.values():
            if result.get("status") == "completed" and result.get("output"):
                output = result["output"]
                if isinstance(output, str):
                    content_to_store += f"\n\n{output[:2000]}"

        stored = []
        if self.long_term and content_to_store:
            memory = await self.long_term.store(
                content=content_to_store[:5000],
                user_id=user_id,
                memory_type="semantic",
                metadata={"source": "task_execution", "goal": context.get("goal", "")},
                importance=0.6,
            )
            stored.append(memory)

        return {"stored_count": len(stored), "memories": stored}

    async def _recall_operation(
        self,
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Recall memories relevant to the task."""
        query = task.get("description", context.get("goal", ""))
        user_id = context.get("user_id", "unknown")

        memories = await self.recall(query=query, user_id=user_id, limit=10)
        return {"recalled_count": len(memories), "memories": memories}

    async def _consolidate_operation(
        self,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Consolidate similar memories."""
        user_id = context.get("user_id", "unknown")

        if self.long_term:
            await self.long_term.consolidate(user_id=user_id)
            return {"status": "consolidated"}
        return {"status": "skipped", "reason": "No long-term memory configured"}

    async def _analyze_and_store(
        self,
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Use LLM to analyze content and determine what to store."""
        previous_results = context.get("previous_results", {})

        # Collect content from previous results
        content_parts = []
        for result in previous_results.values():
            if result.get("output"):
                output = str(result["output"])[:2000]
                content_parts.append(output)

        if not content_parts:
            return {"stored_count": 0, "reason": "No content to analyze"}

        combined_content = "\n\n".join(content_parts)[:4000]

        # Get existing memories to avoid duplicates
        existing = await self.recall(
            query=context.get("goal", ""),
            user_id=context.get("user_id", "unknown"),
            limit=5,
        )
        existing_summaries = [m.get("content", "")[:100] for m in existing]

        prompt = MEMORY_ANALYSIS_PROMPT.format(
            task_description=task.get("description", ""),
            content=combined_content,
            existing_memories=json.dumps(existing_summaries),
        )

        response = await self.llm.ainvoke([
            SystemMessage(content="You are a memory analyst. Respond only with valid JSON."),
            HumanMessage(content=prompt),
        ])

        try:
            analysis = json.loads(response.content)
        except json.JSONDecodeError:
            content = str(response.content)
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                analysis = json.loads(content[start:end])
            else:
                return {"stored_count": 0, "reason": "Could not parse LLM response"}

        # Store extracted memories
        stored = []
        user_id = context.get("user_id", "unknown")
        for mem in analysis.get("memories", []):
            if self.long_term:
                result = await self.long_term.store(
                    content=mem.get("content", ""),
                    user_id=user_id,
                    memory_type=mem.get("memory_type", "semantic"),
                    metadata={"tags": mem.get("tags", []), "source": "auto_analysis"},
                    importance=mem.get("importance_score", 0.5),
                )
                stored.append(result)

        return {"stored_count": len(stored), "memories": stored}
