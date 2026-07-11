"""
Reflection Agent — Post-execution analysis and self-improvement.

After every session, this agent:
1. Evaluates what succeeded and what failed
2. Performs root cause analysis on failures
3. Generates improvement strategies
4. Stores learnings as procedural memories
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


REFLECTION_PROMPT = """You are a reflection and self-improvement expert. Analyze the execution of the following goal and provide a thorough reflection.

## Goal
{goal}

## Task Plan
{task_plan}

## Task Results
{task_results}

## Errors Encountered
{errors}

Provide your reflection as JSON:
{{
    "successes": [
        "Description of each successful outcome"
    ],
    "failures": [
        "Description of each failure"
    ],
    "root_causes": [
        {{
            "failure": "Which failure this relates to",
            "cause": "Root cause analysis",
            "category": "planning | execution | knowledge | resource | external"
        }}
    ],
    "improvements": [
        {{
            "category": "planning | research | execution | memory | strategy",
            "description": "Specific actionable improvement",
            "priority": "high | medium | low",
            "applicable_scenarios": ["When this improvement applies"],
            "expected_impact": "What improvement this would bring"
        }}
    ],
    "metrics": {{
        "tasks_total": 0,
        "tasks_completed": 0,
        "tasks_failed": 0,
        "success_rate": 0.0,
        "overall_quality": "excellent | good | fair | poor"
    }},
    "confidence_score": 0.0,
    "should_retry": false,
    "retry_strategy": null,
    "key_learnings": [
        "Important lessons learned from this execution"
    ]
}}

Be thorough and specific in your analysis. Focus on actionable improvements.
Respond ONLY with valid JSON."""


STRATEGY_UPDATE_PROMPT = """Based on the following reflections from past executions, generate updated strategies for future goal execution.

Past Reflections:
{past_reflections}

Current Improvements:
{current_improvements}

Generate updated strategic guidance as JSON:
{{
    "updated_strategies": [
        {{
            "area": "planning | research | execution | memory",
            "strategy": "Detailed strategy description",
            "when_to_apply": "Conditions under which to use this strategy",
            "confidence": 0.0-1.0
        }}
    ]
}}

Respond ONLY with valid JSON."""


class ReflectionAgent:
    """
    Agent responsible for post-execution reflection and self-improvement.

    Analyzes completed sessions to identify successes, failures, root causes,
    and improvement opportunities. Stores learnings as procedural memories
    for future reference.
    """

    def __init__(
        self,
        memory_agent: Any = None,
    ) -> None:
        """
        Initialize the reflection agent.

        Args:
            memory_agent: Memory agent for storing learnings.
        """
        settings = get_settings()
        self.llm = ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key.get_secret_value(),
            temperature=0.3,
            max_tokens=8192,
        )
        self.memory_agent = memory_agent

    async def execute(
        self,
        goal: str,
        task_plan: list[dict[str, Any]],
        task_results: dict[str, dict[str, Any]],
        errors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """
        Perform reflection on a completed session.

        Args:
            goal: The original goal.
            task_plan: The decomposed task plan.
            task_results: Results of each task.
            errors: Errors encountered during execution.

        Returns:
            Reflection output with successes, failures, root causes, and improvements.
        """
        start_time = time.monotonic()

        try:
            # Step 1: Analyze execution
            reflection = await self._analyze_execution(goal, task_plan, task_results, errors)

            # Step 2: Store learnings as memories
            await self._store_learnings(reflection, goal)

            # Step 3: Generate strategy updates
            strategy_updates = await self._update_strategies(reflection)

            duration_ms = int((time.monotonic() - start_time) * 1000)

            logger.info(
                "Reflection complete",
                successes=len(reflection.get("successes", [])),
                failures=len(reflection.get("failures", [])),
                improvements=len(reflection.get("improvements", [])),
                duration_ms=duration_ms,
            )

            return {
                **reflection,
                "strategy_updates": strategy_updates,
                "duration_ms": duration_ms,
            }

        except Exception as e:
            logger.error("Reflection failed", error=str(e))
            return {
                "successes": [],
                "failures": [f"Reflection process itself failed: {str(e)}"],
                "root_causes": [{"failure": "Reflection failure", "cause": str(e), "category": "execution"}],
                "improvements": [],
                "confidence_score": 0.0,
                "duration_ms": int((time.monotonic() - start_time) * 1000),
            }

    async def _analyze_execution(
        self,
        goal: str,
        task_plan: list[dict[str, Any]],
        task_results: dict[str, dict[str, Any]],
        errors: list[dict[str, Any]],
    ) -> dict[str, Any]:
        """Use LLM to perform deep analysis of the execution."""
        # Prepare concise summaries for the LLM
        plan_summary = json.dumps([
            {"id": t.get("id"), "title": t.get("title"), "agent_type": t.get("agent_type")}
            for t in task_plan
        ])[:2000]

        results_summary = json.dumps({
            tid: {
                "status": r.get("status"),
                "output_preview": str(r.get("output", ""))[:300],
                "error": r.get("error"),
                "duration_ms": r.get("duration_ms"),
            }
            for tid, r in task_results.items()
        }, default=str)[:3000]

        errors_summary = json.dumps(errors[:10])[:1000]

        prompt = REFLECTION_PROMPT.format(
            goal=goal,
            task_plan=plan_summary,
            task_results=results_summary,
            errors=errors_summary,
        )

        response = await self.llm.ainvoke([
            SystemMessage(content="You are a reflection and self-improvement expert. Respond only with valid JSON."),
            HumanMessage(content=prompt),
        ])

        try:
            reflection = json.loads(response.content)
        except json.JSONDecodeError:
            content = str(response.content)
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                reflection = json.loads(content[start:end])
            else:
                # Compute basic metrics as fallback
                completed = sum(1 for r in task_results.values() if r.get("status") == "completed")
                failed = sum(1 for r in task_results.values() if r.get("status") == "failed")
                total = len(task_results) or 1

                reflection = {
                    "successes": [f"Completed {completed} tasks"] if completed else [],
                    "failures": [f"Failed {failed} tasks"] if failed else [],
                    "root_causes": [],
                    "improvements": [],
                    "metrics": {
                        "tasks_total": total,
                        "tasks_completed": completed,
                        "tasks_failed": failed,
                        "success_rate": completed / total,
                        "overall_quality": "good" if completed / total > 0.7 else "fair",
                    },
                    "confidence_score": completed / total,
                    "should_retry": failed > 0 and completed / total < 0.5,
                    "key_learnings": [],
                }

        return reflection

    async def _store_learnings(
        self,
        reflection: dict[str, Any],
        goal: str,
    ) -> None:
        """Store key learnings as procedural memories."""
        if not self.memory_agent:
            return

        learnings = reflection.get("key_learnings", [])
        improvements = reflection.get("improvements", [])

        # Store key learnings
        for learning in learnings[:5]:
            try:
                await self.memory_agent.store(
                    content=f"Learning from goal '{goal[:100]}': {learning}",
                    user_id="system",
                    memory_type="procedural",
                    importance=0.7,
                    metadata={
                        "source": "reflection",
                        "goal": goal[:200],
                        "confidence": reflection.get("confidence_score", 0.5),
                    },
                )
            except Exception as e:
                logger.warning("Failed to store learning", error=str(e))

        # Store high-priority improvements
        for improvement in improvements[:3]:
            if isinstance(improvement, dict) and improvement.get("priority") == "high":
                try:
                    await self.memory_agent.store(
                        content=(
                            f"Improvement strategy ({improvement.get('category', 'general')}): "
                            f"{improvement.get('description', '')}"
                        ),
                        user_id="system",
                        memory_type="procedural",
                        importance=0.8,
                        metadata={
                            "source": "reflection",
                            "category": improvement.get("category", "general"),
                            "applicable_scenarios": improvement.get("applicable_scenarios", []),
                        },
                    )
                except Exception as e:
                    logger.warning("Failed to store improvement", error=str(e))

    async def _update_strategies(
        self,
        reflection: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Generate updated strategies based on current and past reflections."""
        improvements = reflection.get("improvements", [])
        if not improvements:
            return []

        # Get past reflections from memory
        past_reflections_text = "No past reflections available."
        if self.memory_agent:
            try:
                past = await self.memory_agent.recall(
                    query="improvement strategies and learnings",
                    user_id="system",
                    memory_type="procedural",
                    limit=5,
                )
                if past:
                    past_reflections_text = json.dumps([
                        {"content": p.get("content", ""), "importance": p.get("importance_score", 0)}
                        for p in past
                    ])[:2000]
            except Exception:
                pass

        prompt = STRATEGY_UPDATE_PROMPT.format(
            past_reflections=past_reflections_text,
            current_improvements=json.dumps(improvements)[:2000],
        )

        response = await self.llm.ainvoke([
            SystemMessage(content="You are a strategy expert. Respond only with valid JSON."),
            HumanMessage(content=prompt),
        ])

        try:
            result = json.loads(response.content)
            return result.get("updated_strategies", [])
        except json.JSONDecodeError:
            return []
