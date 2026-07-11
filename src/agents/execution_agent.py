"""
Execution Agent — Sandboxed code execution and task operations.

Capabilities:
- Python code execution (sandboxed subprocess)
- API calls
- File operations
- Database queries
- Report generation
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


EXECUTION_PLANNING_PROMPT = """You are an expert execution planner. Given the task and context, determine the best execution approach.

Task: {task_description}
Goal Context: {goal}
Previous Results: {previous_results}
Available Tools: python_executor, api_caller, file_operations, database_query, report_generator

Plan your execution as JSON:
{{
    "steps": [
        {{
            "tool": "tool_name",
            "action": "what to do",
            "parameters": {{}},
            "expected_output": "what this should produce"
        }}
    ],
    "approach": "Description of overall approach",
    "safety_notes": ["any safety considerations"]
}}

Rules:
- Use python_executor for calculations, data processing, or custom logic
- Use api_caller for external API interactions
- Use file_operations for reading/writing workspace files
- Use report_generator for creating structured output
- Keep steps minimal and focused
- Consider safety implications of each step

Respond ONLY with valid JSON."""

CODE_GENERATION_PROMPT = """Generate Python code to accomplish the following task.

Task: {task}
Context: {context}

Requirements:
- Code must be self-contained
- Use only standard library + numpy, pandas, requests if needed
- Print results to stdout
- Handle errors gracefully
- No file system operations outside /tmp
- No network operations unless specifically required
- No subprocess or os.system calls

Respond with ONLY the Python code, no explanation or markdown."""


class ExecutionAgent:
    """
    Agent responsible for executing computational tasks.

    Uses available tools or generates Python code for complex operations.
    All execution is sandboxed with resource limits.
    """

    def __init__(
        self,
        tools: list[Any] | None = None,
    ) -> None:
        """
        Initialize the execution agent.

        Args:
            tools: List of LangChain tools for execution operations.
        """
        settings = get_settings()
        self.llm = ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key.get_secret_value(),
            temperature=0.1,
            max_tokens=8192,
        )
        self.tools = {t.name: t for t in (tools or [])}
        self.max_execution_time = settings.max_execution_time_seconds

    async def execute(
        self,
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Execute a computational task.

        Pipeline: Plan → Execute Steps → Collect Results

        Args:
            task: Task specification.
            context: Execution context.

        Returns:
            Result dictionary with execution output.
        """
        start_time = time.monotonic()
        task_desc = task.get("description", "")

        try:
            # Step 1: Plan execution
            plan = await self._plan_execution(task_desc, context)

            # Step 2: Execute steps
            results = await self._execute_steps(plan, context)

            # Step 3: Compile output
            output = self._compile_results(results)

            duration_ms = int((time.monotonic() - start_time) * 1000)

            return {
                "status": "completed",
                "output": output,
                "steps_completed": len(results),
                "duration_ms": duration_ms,
            }

        except Exception as e:
            logger.error("Execution failed", error=str(e), task_id=task.get("id"))
            return {
                "status": "failed",
                "error": str(e),
                "duration_ms": int((time.monotonic() - start_time) * 1000),
            }

    async def _plan_execution(
        self,
        task_description: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Use LLM to plan the execution strategy."""
        previous = context.get("previous_results", {})
        prev_summary = json.dumps(
            {k: {"status": v.get("status"), "output_preview": str(v.get("output", ""))[:200]}
             for k, v in previous.items()},
            default=str,
        )[:2000]

        prompt = EXECUTION_PLANNING_PROMPT.format(
            task_description=task_description,
            goal=context.get("goal", ""),
            previous_results=prev_summary,
        )

        response = await self.llm.ainvoke([
            SystemMessage(content="You are an execution planning expert. Respond only with valid JSON."),
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
                # Fallback: generate code directly
                plan = {
                    "steps": [{
                        "tool": "python_executor",
                        "action": task_description,
                        "parameters": {"code": "# Task will be executed via LLM"},
                        "expected_output": "Task result",
                    }],
                    "approach": "Direct execution via code generation",
                }

        logger.info("Execution plan created", steps=len(plan.get("steps", [])))
        return plan

    async def _execute_steps(
        self,
        plan: dict[str, Any],
        context: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Execute all planned steps."""
        results: list[dict[str, Any]] = []
        steps = plan.get("steps", [])

        for i, step in enumerate(steps[:10]):  # Limit to 10 steps
            tool_name = step.get("tool", "")
            action = step.get("action", "")
            params = step.get("parameters", {})

            logger.info("Executing step", step=i + 1, tool=tool_name, action=action[:50])

            try:
                if tool_name == "python_executor":
                    result = await self._execute_python(action, params, context)
                elif tool_name in self.tools:
                    tool = self.tools[tool_name]
                    result = await tool.ainvoke(params)
                    result = {"status": "completed", "output": str(result)}
                else:
                    # Fallback: use LLM to handle the step
                    result = await self._llm_fallback(action, context)

                results.append({
                    "step": i + 1,
                    "tool": tool_name,
                    "action": action,
                    **result,
                })

            except Exception as e:
                logger.warning("Step execution failed", step=i + 1, error=str(e))
                results.append({
                    "step": i + 1,
                    "tool": tool_name,
                    "action": action,
                    "status": "failed",
                    "error": str(e),
                })

        return results

    async def _execute_python(
        self,
        action: str,
        params: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute Python code, generating it if needed."""
        code = params.get("code", "")

        if not code or code.startswith("# Task"):
            # Generate code from the action description
            code = await self._generate_code(action, context)

        # Execute via the python_executor tool if available
        if "python_executor" in self.tools:
            tool = self.tools["python_executor"]
            result = await tool.ainvoke({"code": code, "timeout": 30})
            return {"status": "completed", "output": str(result), "code": code}

        # Fallback: have the LLM reason about what the code would produce
        response = await self.llm.ainvoke([
            SystemMessage(content="You are a Python expert. Analyze this code and describe what it would output."),
            HumanMessage(content=f"Analyze this code:\n```python\n{code}\n```\n\nDescribe the expected output."),
        ])
        return {
            "status": "completed",
            "output": str(response.content),
            "code": code,
            "note": "Simulated execution (sandbox not available)",
        }

    async def _generate_code(
        self,
        task: str,
        context: dict[str, Any],
    ) -> str:
        """Generate Python code for a task using the LLM."""
        context_str = ""
        previous = context.get("previous_results", {})
        if previous:
            context_str = "Previous results:\n" + json.dumps(
                {k: str(v.get("output", ""))[:300] for k, v in previous.items()},
                default=str,
            )[:1000]

        prompt = CODE_GENERATION_PROMPT.format(
            task=task,
            context=context_str,
        )

        response = await self.llm.ainvoke([
            SystemMessage(content="You are a Python code generator. Respond with ONLY executable Python code."),
            HumanMessage(content=prompt),
        ])

        code = str(response.content)

        # Strip markdown code blocks if present
        if code.startswith("```python"):
            code = code[len("```python"):].strip()
        if code.startswith("```"):
            code = code[3:].strip()
        if code.endswith("```"):
            code = code[:-3].strip()

        return code

    async def _llm_fallback(
        self,
        action: str,
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Use LLM as a fallback when specific tools are not available."""
        response = await self.llm.ainvoke([
            SystemMessage(content="You are a technical execution assistant. Provide actionable, detailed results."),
            HumanMessage(content=f"Execute the following:\n\n{action}"),
        ])

        return {
            "status": "completed",
            "output": str(response.content),
            "source": "llm_fallback",
        }

    def _compile_results(self, results: list[dict[str, Any]]) -> str:
        """Compile step results into a single output string."""
        if not results:
            return "No execution steps were completed."

        parts = []
        for r in results:
            status_emoji = "✅" if r.get("status") == "completed" else "❌"
            parts.append(
                f"{status_emoji} Step {r.get('step', '?')}: {r.get('action', 'Unknown')[:100]}\n"
                f"   Output: {str(r.get('output', r.get('error', 'No output')))[:500]}"
            )

        return "\n\n".join(parts)
