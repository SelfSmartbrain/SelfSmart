"""
Orchestrator Agent — The central coordinator for the multi-agent workflow.

Implements a LangGraph StateGraph that:
1. Analyzes high-level goals
2. Decomposes goals into executable tasks
3. Routes tasks to specialist agents
4. Tracks progress and handles failures
5. Triggers reflection after completion
6. Generates summary reports
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.graph import END, START, StateGraph

from src.agents.state import AgentStateDict, TaskSpec
from src.config.logging import get_logger
from src.config.settings import get_settings

from src.agents.cognition_nodes import (
    cognition_reflection_node,
    failure_analysis_node,
    meta_learning_node,
    strategy_optimization_node,
    skill_discovery_node,
    metrics_node,
    self_improvement_node,
)

from src.agents.capability_nodes import (
    capability_gap_detection_node,
    tool_specification_node,
    tool_generation_node,
    tool_validation_node,
    tool_registration_node,
    tool_evolution_node,
    capability_evaluation_node,
    benchmark_execution_node,
    transfer_analysis_node,
    discovery_analysis_node,
    peer_review_node,
    regression_detection_node,
    program_evaluation_node,
    capability_reporting_node,
)

from src.agents.world_model_nodes import (
    pattern_discovery_node,
    causal_reasoning_node,
    hypothesis_generation_node,
    experiment_design_node,
    experiment_execution_node,
    belief_update_node,
    prediction_generation_node,
    world_model_update_node,
)

from src.agents.architecture_nodes import (
    architecture_analysis_node,
    dependency_analysis_node,
    component_analysis_node,
    bottleneck_detection_node,
    hypothesis_generation_node as arch_hypothesis_generation_node,
    candidate_generation_node,
    sandbox_benchmarking_node,
    benchmark_reporting_node,
)

from src.agents.evolution_nodes import (
    genome_generation_node,
    mutation_generation_node,
    candidate_selection_node,
    evolution_cycle_node,
    promotion_decision_node,
    rollback_check_node,
    fitness_tracking_node,
    generation_tracking_node,
)


from src.agents.project_nodes import (
    environment_analysis_node,
    opportunity_detection_node,
    project_creation_node,
    task_decomposition_node,
    resource_allocation_node,
    execution_node,
    checkpointing_node,
    failure_recovery_node,
    impact_analysis_node,
    project_completion_node,
)

logger = get_logger(__name__)


# ---------------------------------------------------------------------------
# System prompts for the orchestrator's different roles
# ---------------------------------------------------------------------------

GOAL_ANALYSIS_PROMPT = """You are an expert goal analyst. Analyze the following goal and provide a structured analysis.

Goal: {goal}
{context}

Provide your analysis as JSON with the following structure:
{{
    "intent": "What the user wants to achieve",
    "scope": "small | medium | large",
    "domain": "The primary domain (e.g., 'research', 'coding', 'analysis')",
    "constraints": ["Any constraints or limitations"],
    "success_criteria": ["How to measure success"],
    "required_capabilities": ["research", "execution", "memory"],
    "estimated_complexity": 1-10,
    "risks": ["Potential risks or challenges"]
}}

Respond ONLY with valid JSON, no additional text."""

TASK_DECOMPOSITION_PROMPT = """You are an expert task planner. Decompose the following goal into executable tasks.

Goal: {goal}
Analysis: {analysis}
Available Memories: {memories}

Create a list of tasks as JSON array. Each task should have:
{{
    "id": "unique_id (use task_1, task_2, etc.)",
    "title": "Short task title",
    "description": "Detailed description of what needs to be done",
    "agent_type": "research | execution | memory",
    "priority": 1-5 (1 = highest),
    "dependencies": ["ids of tasks this depends on"]
}}

Rules:
- Order tasks logically (research before execution)
- Mark dependencies correctly
- Use "research" for information gathering
- Use "execution" for code/file/API operations
- Use "memory" for storing/recalling information
- Keep tasks atomic and focused
- Aim for 3-10 tasks total

Respond ONLY with a valid JSON array, no additional text."""

INTEGRATION_PROMPT = """You are a results integrator. Review the task results and determine next steps.

Goal: {goal}
Completed Tasks: {completed}
Current Task Result: {current_result}
Remaining Tasks: {remaining}
Errors: {errors}

Determine:
1. Was the current task successful?
2. Should we continue with the next task, retry, or stop?
3. Do any remaining tasks need modification based on results?

Respond as JSON:
{{
    "current_task_assessment": "success | partial | failure",
    "action": "continue | retry | stop | reflect",
    "modifications": ["Any task modifications needed"],
    "reasoning": "Why this action"
}}

Respond ONLY with valid JSON."""

REPORT_GENERATION_PROMPT = """You are a report generator. Create a comprehensive summary report.

Goal: {goal}
Task Results: {results}
Reflection: {reflection}

Generate a clear, structured report in Markdown format covering:
1. **Goal**: What was requested
2. **Approach**: How it was tackled
3. **Results**: What was accomplished
4. **Key Findings**: Important discoveries or outputs
5. **Challenges**: Any issues encountered
6. **Recommendations**: Next steps or improvements

Be concise but thorough."""


class OrchestratorAgent:
    """
    Central orchestrator that coordinates the multi-agent workflow using LangGraph.

    The orchestrator manages the lifecycle of goal execution:
    goal → analysis → decomposition → routing → execution → reflection → report
    """

    def __init__(
        self,
        memory_agent: Any = None,
        research_agent: Any = None,
        execution_agent: Any = None,
        reflection_agent: Any = None,
        strategy_engine: Any = None,
        task_classifier: Any = None,
        learning_engine: Any = None,
        experience_replay: Any = None,
    ) -> None:
        """
        Initialize the orchestrator with specialist agents.

        Args:
            memory_agent: Agent for memory operations.
            research_agent: Agent for research tasks.
            execution_agent: Agent for code execution tasks.
            reflection_agent: Agent for post-execution reflection.
        """
        settings = get_settings()
        self.llm = ChatAnthropic(
            model=settings.anthropic_model,
            api_key=settings.anthropic_api_key.get_secret_value(),
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )
        self.memory_agent = memory_agent
        self.research_agent = research_agent
        self.execution_agent = execution_agent
        self.reflection_agent = reflection_agent
        self.strategy_engine = strategy_engine
        self.task_classifier = task_classifier
        self.learning_engine = learning_engine
        self.experience_replay = experience_replay
        self._graph = self._build_graph()

    # -----------------------------------------------------------------------
    # Graph construction
    # -----------------------------------------------------------------------

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph StateGraph for the orchestration workflow."""
        graph = StateGraph(AgentStateDict)

        # Register nodes
        graph.add_node("analyze_goal", self._analyze_goal)
        graph.add_node("recall_memories", self._recall_memories)
        graph.add_node("replay_experiences", self._replay_experiences)
        graph.add_node("decompose_tasks", self._decompose_tasks)
        graph.add_node("classify_task", self._classify_task)
        graph.add_node("select_strategy", self._select_strategy)
        graph.add_node("route_task", self._route_task)
        graph.add_node("execute_research", self._execute_research)
        graph.add_node("execute_task", self._execute_task)
        graph.add_node("execute_memory_op", self._execute_memory_op)
        graph.add_node("integrate_results", self._integrate_results)
        graph.add_node("dynamic_replan", self._dynamic_replan)
        graph.add_node("reflect", self._reflect)
        graph.add_node("extract_learnings", self._extract_learnings)
        graph.add_node("update_strategies", self._update_strategies)
        
        # Phase 6 Autonomous Research Nodes
        graph.add_node("knowledge_gap_detection", self._knowledge_gap_detection)
        graph.add_node("goal_generation", self._goal_generation)
        graph.add_node("curiosity_evaluation", self._curiosity_evaluation)
        graph.add_node("research_director", self._research_director)
        graph.add_node("research_portfolio", self._research_portfolio)
        graph.add_node("knowledge_graph_update", self._knowledge_graph_update)
        
        # Phase 7 Self-Improving Intelligence Nodes
        graph.add_node("cognition_reflection", cognition_reflection_node)
        graph.add_node("failure_analysis", failure_analysis_node)
        graph.add_node("meta_learning", meta_learning_node)
        graph.add_node("strategy_optimization", strategy_optimization_node)
        graph.add_node("skill_discovery", skill_discovery_node)
        graph.add_node("record_metrics", metrics_node)
        graph.add_node("self_improvement", self_improvement_node)
        
        # Phase 8 Autonomous Tool Creation Nodes
        graph.add_node("capability_gap_detection", capability_gap_detection_node)
        graph.add_node("tool_specification", tool_specification_node)
        graph.add_node("tool_generation", tool_generation_node)
        graph.add_node("tool_validation", tool_validation_node)
        graph.add_node("tool_registration", tool_registration_node)
        graph.add_node("tool_evolution", tool_evolution_node)
        
        # Phase 9 World Model Nodes
        graph.add_node("pattern_discovery", pattern_discovery_node)
        graph.add_node("causal_reasoning", causal_reasoning_node)
        graph.add_node("hypothesis_generation", hypothesis_generation_node)
        graph.add_node("experiment_design", experiment_design_node)
        graph.add_node("experiment_execution", experiment_execution_node)
        graph.add_node("belief_update", belief_update_node)
        graph.add_node("prediction_generation", prediction_generation_node)
        graph.add_node("world_model_update", world_model_update_node)
        
        # Phase 10 Architecture Intelligence Nodes
        graph.add_node("architecture_analysis", architecture_analysis_node)
        graph.add_node("dependency_analysis", dependency_analysis_node)
        graph.add_node("component_analysis", component_analysis_node)
        graph.add_node("bottleneck_detection", bottleneck_detection_node)
        graph.add_node("arch_hypothesis_generation", arch_hypothesis_generation_node)
        graph.add_node("candidate_generation", candidate_generation_node)
        graph.add_node("sandbox_benchmarking", sandbox_benchmarking_node)
        graph.add_node("benchmark_reporting", benchmark_reporting_node)
        
        # Phase 10G Evolution Nodes
        graph.add_node("genome_generation", genome_generation_node)
        graph.add_node("mutation_generation", mutation_generation_node)
        graph.add_node("candidate_selection", candidate_selection_node)
        graph.add_node("evolution_cycle", evolution_cycle_node)
        graph.add_node("promotion_decision", promotion_decision_node)
        graph.add_node("rollback_check", rollback_check_node)
        graph.add_node("fitness_tracking", fitness_tracking_node)
        graph.add_node("generation_tracking", generation_tracking_node)
        
        # Phase 11 Capability Nodes
        graph.add_node("capability_evaluation", capability_evaluation_node)
        graph.add_node("benchmark_execution", benchmark_execution_node)
        graph.add_node("transfer_analysis", transfer_analysis_node)
        graph.add_node("discovery_analysis", discovery_analysis_node)
        graph.add_node("peer_review", peer_review_node)
        graph.add_node("regression_detection", regression_detection_node)
        graph.add_node("program_evaluation", program_evaluation_node)
        graph.add_node("capability_reporting", capability_reporting_node)
        
        # Phase 12 Project Nodes
        graph.add_node("environment_analysis", environment_analysis_node)
        graph.add_node("opportunity_detection", opportunity_detection_node)
        graph.add_node("project_creation", project_creation_node)
        graph.add_node("task_decomposition", task_decomposition_node)
        graph.add_node("resource_allocation", resource_allocation_node)
        graph.add_node("execution", execution_node)
        graph.add_node("checkpointing", checkpointing_node)
        graph.add_node("failure_recovery", failure_recovery_node)
        graph.add_node("impact_analysis", impact_analysis_node)
        graph.add_node("project_completion", project_completion_node)
        
        graph.add_node("generate_report", self._generate_report)

        # Define edges
        graph.add_edge(START, "analyze_goal")
        graph.add_edge("analyze_goal", "recall_memories")
        graph.add_edge("recall_memories", "replay_experiences")
        graph.add_edge("replay_experiences", "decompose_tasks")
        graph.add_edge("decompose_tasks", "classify_task")
        graph.add_edge("classify_task", "select_strategy")
        graph.add_edge("select_strategy", "route_task")

        # Conditional routing based on task type
        graph.add_conditional_edges(
            "route_task",
            self._routing_decision,
            {
                "research": "execute_research",
                "execution": "execute_task",
                "memory": "execute_memory_op",
                "reflect": "reflect",
                "complete": "generate_report",
            },
        )

        # All execution paths lead to integration
        graph.add_edge("execute_research", "integrate_results")
        graph.add_edge("execute_task", "integrate_results")
        graph.add_edge("execute_memory_op", "integrate_results")

        # Integration decides next step
        graph.add_conditional_edges(
            "integrate_results",
            self._completion_check,
            {
                "continue": "dynamic_replan",
                "reflect": "reflect",
                "failed": "reflect",
            },
        )

        graph.add_edge("dynamic_replan", "classify_task")
        graph.add_edge("reflect", "extract_learnings")
        graph.add_edge("extract_learnings", "update_strategies")
        
        # Phase 6: Autonomous Research Pipeline
        graph.add_edge("update_strategies", "knowledge_gap_detection")
        graph.add_edge("knowledge_gap_detection", "goal_generation")
        graph.add_edge("goal_generation", "curiosity_evaluation")
        graph.add_edge("curiosity_evaluation", "research_director")
        graph.add_edge("research_director", "research_portfolio")
        graph.add_edge("research_portfolio", "knowledge_graph_update")

        # Phase 7: Post-execution cognition pipeline
        graph.add_edge("knowledge_graph_update", "cognition_reflection")
        graph.add_edge("cognition_reflection", "failure_analysis")
        graph.add_edge("failure_analysis", "meta_learning")
        graph.add_edge("meta_learning", "strategy_optimization")
        graph.add_edge("strategy_optimization", "skill_discovery")
        graph.add_edge("skill_discovery", "record_metrics")
        graph.add_edge("record_metrics", "self_improvement")
        
        # Phase 8: Capability Evolution Pipeline
        graph.add_edge("self_improvement", "capability_gap_detection")
        graph.add_edge("capability_gap_detection", "tool_specification")
        graph.add_edge("tool_specification", "tool_generation")
        graph.add_edge("tool_generation", "tool_validation")
        graph.add_edge("tool_validation", "tool_registration")
        graph.add_edge("tool_registration", "tool_evolution")
        
        # Phase 9: World Model Pipeline
        graph.add_edge("tool_evolution", "pattern_discovery")
        graph.add_edge("pattern_discovery", "causal_reasoning")
        graph.add_edge("causal_reasoning", "hypothesis_generation")
        graph.add_edge("hypothesis_generation", "experiment_design")
        graph.add_edge("experiment_design", "experiment_execution")
        graph.add_edge("experiment_execution", "belief_update")
        graph.add_edge("belief_update", "prediction_generation")
        graph.add_edge("prediction_generation", "world_model_update")
        
        # Phase 10: Architecture Intelligence Pipeline
        graph.add_edge("world_model_update", "architecture_analysis")
        graph.add_edge("architecture_analysis", "dependency_analysis")
        graph.add_edge("dependency_analysis", "component_analysis")
        graph.add_edge("component_analysis", "bottleneck_detection")
        graph.add_edge("bottleneck_detection", "arch_hypothesis_generation")
        graph.add_edge("arch_hypothesis_generation", "candidate_generation")
        graph.add_edge("candidate_generation", "sandbox_benchmarking")
        graph.add_edge("sandbox_benchmarking", "benchmark_reporting")
        
        # Phase 10G: Evolution Pipeline
        graph.add_edge("benchmark_reporting", "genome_generation")
        graph.add_edge("genome_generation", "mutation_generation")
        graph.add_edge("mutation_generation", "candidate_selection")
        graph.add_edge("candidate_selection", "evolution_cycle")
        graph.add_edge("evolution_cycle", "promotion_decision")
        graph.add_edge("promotion_decision", "rollback_check")
        graph.add_edge("rollback_check", "fitness_tracking")
        graph.add_edge("fitness_tracking", "generation_tracking")
        
        # Phase 11: Capability Loop
        graph.add_edge("generation_tracking", "capability_evaluation")
        graph.add_edge("capability_evaluation", "benchmark_execution")
        graph.add_edge("benchmark_execution", "transfer_analysis")
        graph.add_edge("transfer_analysis", "discovery_analysis")
        graph.add_edge("discovery_analysis", "peer_review")
        graph.add_edge("peer_review", "regression_detection")
        graph.add_edge("regression_detection", "program_evaluation")
        graph.add_edge("program_evaluation", "capability_reporting")
        graph.add_edge("capability_reporting", "environment_analysis")
        
        # Phase 12: Project Execution Loop
        graph.add_edge("environment_analysis", "opportunity_detection")
        graph.add_edge("opportunity_detection", "project_creation")
        graph.add_edge("project_creation", "task_decomposition")
        graph.add_edge("task_decomposition", "resource_allocation")
        graph.add_edge("resource_allocation", "execution")
        graph.add_edge("execution", "checkpointing")
        graph.add_edge("checkpointing", "failure_recovery")
        graph.add_edge("failure_recovery", "impact_analysis")
        graph.add_edge("impact_analysis", "project_completion")
        graph.add_edge("project_completion", "generate_report")
        
        graph.add_edge("generate_report", END)

        return graph

    def compile(self, checkpointer: Any = None) -> Any:
        """
        Compile the graph with optional checkpointer for persistence.

        Args:
            checkpointer: LangGraph checkpointer for state persistence.

        Returns:
            Compiled LangGraph graph ready for execution.
        """
        kwargs: dict[str, Any] = {}
        if checkpointer:
            kwargs["checkpointer"] = checkpointer
        return self._graph.compile(**kwargs)

    # -----------------------------------------------------------------------
    # Node implementations
    # -----------------------------------------------------------------------

    async def _analyze_goal(self, state: AgentStateDict) -> dict[str, Any]:
        """Analyze the user's goal to understand intent, scope, and requirements."""
        logger.info("Analyzing goal", goal=state["goal"][:100])
        start_time = time.monotonic()

        context_str = ""
        if state.get("goal_analysis") and isinstance(state["goal_analysis"], dict):
            context_str = f"\nAdditional Context: {json.dumps(state['goal_analysis'])}"

        prompt = GOAL_ANALYSIS_PROMPT.format(
            goal=state["goal"],
            context=context_str,
        )

        response = await self.llm.ainvoke([
            SystemMessage(content="You are an expert goal analyst. Respond only with valid JSON."),
            HumanMessage(content=prompt),
        ])

        try:
            analysis = json.loads(response.content)
        except json.JSONDecodeError:
            # Try to extract JSON from the response
            content = str(response.content)
            start = content.find("{")
            end = content.rfind("}") + 1
            if start >= 0 and end > start:
                analysis = json.loads(content[start:end])
            else:
                analysis = {
                    "intent": state["goal"],
                    "scope": "medium",
                    "domain": "general",
                    "constraints": [],
                    "success_criteria": ["Goal completed successfully"],
                    "required_capabilities": ["research", "execution"],
                    "estimated_complexity": 5,
                    "risks": [],
                }

        duration_ms = int((time.monotonic() - start_time) * 1000)
        logger.info("Goal analysis complete", duration_ms=duration_ms, scope=analysis.get("scope"))

        return {
            "goal_analysis": analysis,
            "status": "planning",
        }

    async def _recall_memories(self, state: AgentStateDict) -> dict[str, Any]:
        """Recall relevant memories from previous sessions."""
        logger.info("Recalling relevant memories")

        memories: list[dict[str, Any]] = []

        if self.memory_agent:
            try:
                recalled = await self.memory_agent.recall(
                    query=state["goal"],
                    user_id=state["user_id"],
                    limit=5,
                )
                memories = [
                    {
                        "id": str(m.get("id", "")),
                        "content": m.get("content", ""),
                        "memory_type": m.get("memory_type", ""),
                        "importance_score": m.get("importance_score", 0.0),
                        "relevance_score": m.get("relevance_score", 0.0),
                    }
                    for m in recalled
                ]
                logger.info("Memories recalled", count=len(memories))
            except Exception as e:
                logger.warning("Memory recall failed, continuing without memories", error=str(e))

        return {"retrieved_memories": memories}

    async def _replay_experiences(self, state: AgentStateDict) -> dict[str, Any]:
        """Replay past experiences for context."""
        logger.info("Replaying past experiences")
        
        experiences = []
        if self.experience_replay:
            try:
                # We fetch some generic past successes/failures related to the goal
                experiences = await self.experience_replay.get_similar_experiences(
                    task=state["goal"], limit=3
                )
            except Exception as e:
                logger.warning("Experience replay failed", error=str(e))
                
        context = ""
        if experiences:
            context = "Past relevant experiences:\n" + "\n".join([e.context_summary for e in experiences])
            
        return {"experience_context": context}

    async def _decompose_tasks(self, state: AgentStateDict) -> dict[str, Any]:
        """Decompose the goal into executable tasks."""
        logger.info("Decomposing goal into tasks")
        start_time = time.monotonic()

        memories_str = json.dumps(state.get("retrieved_memories", [])[:3])
        analysis_str = json.dumps(state.get("goal_analysis", {}))

        prompt = TASK_DECOMPOSITION_PROMPT.format(
            goal=state["goal"],
            analysis=analysis_str,
            memories=memories_str,
        )

        response = await self.llm.ainvoke([
            SystemMessage(content="You are an expert task planner. Respond only with a valid JSON array."),
            HumanMessage(content=prompt),
        ])

        try:
            tasks = json.loads(response.content)
        except json.JSONDecodeError:
            content = str(response.content)
            start = content.find("[")
            end = content.rfind("]") + 1
            if start >= 0 and end > start:
                tasks = json.loads(content[start:end])
            else:
                # Fallback: create a single research task
                tasks = [{
                    "id": "task_1",
                    "title": "Research and execute goal",
                    "description": state["goal"],
                    "agent_type": "research",
                    "priority": 1,
                    "dependencies": [],
                }]

        # Validate and normalize tasks
        validated_tasks = []
        for task in tasks:
            validated_tasks.append({
                "id": task.get("id", f"task_{len(validated_tasks) + 1}"),
                "title": task.get("title", "Unnamed Task"),
                "description": task.get("description", ""),
                "agent_type": task.get("agent_type", "research"),
                "priority": task.get("priority", 3),
                "dependencies": task.get("dependencies", []),
                "status": "pending",
            })

        duration_ms = int((time.monotonic() - start_time) * 1000)
        logger.info(
            "Task decomposition complete",
            task_count=len(validated_tasks),
            duration_ms=duration_ms,
        )

        return {
            "task_plan": validated_tasks,
            "current_task_index": 0,
            "status": "executing",
        }

    async def _classify_task(self, state: AgentStateDict) -> dict[str, Any]:
        """Classify the current task type."""
        task_plan = state.get("task_plan", [])
        current_idx = state.get("current_task_index", 0)
        
        if current_idx >= len(task_plan):
            return {"task_classification": None}
            
        current_task = task_plan[current_idx]
        logger.info("Classifying task", task_id=current_task.get("id"))
        
        classification = None
        if self.task_classifier:
            try:
                classification = await self.task_classifier.classify(
                    task_description=current_task.get("description", ""),
                    context=state.get("goal", ""),
                )
            except Exception as e:
                logger.error("Task classification failed", error=str(e))
                
        return {"task_classification": classification}

    async def _select_strategy(self, state: AgentStateDict) -> dict[str, Any]:
        """Select the best execution strategy for the task."""
        classification = state.get("task_classification")
        if not classification or not self.strategy_engine:
            return {"selected_strategy": None}
            
        logger.info("Selecting strategy for task type", task_type=classification.get("task_type"))
        
        strategy = None
        try:
            # We would normally convert Enum to string or pass directly
            task_type = classification.get("task_type")
            task_plan = state.get("task_plan", [])
            current_idx = state.get("current_task_index", 0)
            current_task = task_plan[current_idx] if current_idx < len(task_plan) else {}
            
            # get_best_strategy uses semantic search
            strategy = await self.strategy_engine.get_best_strategy(
                task_type=task_type,
                context=current_task.get("description", ""),
            )
        except Exception as e:
            logger.error("Strategy selection failed", error=str(e))
            
        strategy_dict = None
        if strategy:
            strategy_dict = {
                "id": str(strategy.id),
                "name": strategy.name,
                "steps": strategy.steps,
            }
            logger.info("Strategy selected", strategy_name=strategy.name)
            
        return {"selected_strategy": strategy_dict}

    async def _route_task(self, state: AgentStateDict) -> dict[str, Any]:
        """Route the current task to the appropriate agent."""
        task_plan = state.get("task_plan", [])
        current_idx = state.get("current_task_index", 0)

        if current_idx >= len(task_plan):
            logger.info("All tasks completed, moving to reflection")
            return {"next_agent": "reflect"}

        current_task = task_plan[current_idx]

        # Check if dependencies are satisfied
        completed_ids = set(state.get("task_results", {}).keys())
        deps = current_task.get("dependencies", [])
        unsatisfied = [d for d in deps if d not in completed_ids]

        if unsatisfied:
            logger.warning(
                "Task has unsatisfied dependencies, skipping",
                task_id=current_task["id"],
                unsatisfied=unsatisfied,
            )
            # Skip to next task
            return {
                "current_task_index": current_idx + 1,
                "next_agent": current_task.get("agent_type", "research"),
            }

        agent_type = current_task.get("agent_type", "research")
        logger.info(
            "Routing task",
            task_id=current_task["id"],
            task_title=current_task["title"],
            agent_type=agent_type,
        )

        return {"next_agent": agent_type}

    def _routing_decision(self, state: AgentStateDict) -> str:
        """Determine which agent to route to based on state."""
        next_agent = state.get("next_agent", "reflect")
        task_plan = state.get("task_plan", [])
        current_idx = state.get("current_task_index", 0)
        iteration = state.get("iteration_count", 0)
        max_iter = state.get("max_iterations", 20)

        # Safety: prevent infinite loops
        if iteration >= max_iter:
            logger.warning("Max iterations reached, forcing reflection", iteration=iteration)
            return "reflect"

        if current_idx >= len(task_plan):
            return "reflect"

        if next_agent == "reflect":
            return "reflect"

        # Map agent types to node names
        routing_map = {
            "research": "research",
            "execution": "execution",
            "memory": "memory",
        }
        return routing_map.get(next_agent, "research")

    async def _execute_research(self, state: AgentStateDict) -> dict[str, Any]:
        """Execute a research task using the research agent."""
        task_plan = state.get("task_plan", [])
        current_idx = state.get("current_task_index", 0)
        current_task = task_plan[current_idx] if current_idx < len(task_plan) else {}

        logger.info("Executing research task", task_id=current_task.get("id"))
        start_time = time.monotonic()

        result: dict[str, Any]
        if self.research_agent:
            try:
                result = await self.research_agent.execute(
                    task=current_task,
                    context={
                        "goal": state["goal"],
                        "previous_results": state.get("task_results", {}),
                        "memories": state.get("retrieved_memories", []),
                    },
                )
            except Exception as e:
                logger.error("Research agent failed", error=str(e))
                result = {"status": "failed", "error": str(e)}
        else:
            # Fallback: use the LLM directly for research
            response = await self.llm.ainvoke([
                SystemMessage(content="You are a research assistant. Provide thorough, well-sourced answers."),
                HumanMessage(content=f"Research the following:\n\n{current_task.get('description', state['goal'])}"),
            ])
            result = {
                "status": "completed",
                "output": str(response.content),
                "source": "llm_fallback",
            }

        duration_ms = int((time.monotonic() - start_time) * 1000)
        task_id = current_task.get("id", f"task_{current_idx}")

        task_results = dict(state.get("task_results", {}))
        task_results[task_id] = {
            **result,
            "task_id": task_id,
            "duration_ms": duration_ms,
        }

        return {
            "task_results": task_results,
            "iteration_count": state.get("iteration_count", 0) + 1,
        }

    async def _execute_task(self, state: AgentStateDict) -> dict[str, Any]:
        """Execute a computational task using the execution agent."""
        task_plan = state.get("task_plan", [])
        current_idx = state.get("current_task_index", 0)
        current_task = task_plan[current_idx] if current_idx < len(task_plan) else {}

        logger.info("Executing computational task", task_id=current_task.get("id"))
        start_time = time.monotonic()

        result: dict[str, Any]
        if self.execution_agent:
            try:
                result = await self.execution_agent.execute(
                    task=current_task,
                    context={
                        "goal": state["goal"],
                        "previous_results": state.get("task_results", {}),
                    },
                )
            except Exception as e:
                logger.error("Execution agent failed", error=str(e))
                result = {"status": "failed", "error": str(e)}
        else:
            # Fallback: use the LLM to generate a response
            response = await self.llm.ainvoke([
                SystemMessage(content="You are a technical execution assistant. Provide actionable solutions."),
                HumanMessage(content=f"Execute the following task:\n\n{current_task.get('description', state['goal'])}"),
            ])
            result = {
                "status": "completed",
                "output": str(response.content),
                "source": "llm_fallback",
            }

        duration_ms = int((time.monotonic() - start_time) * 1000)
        task_id = current_task.get("id", f"task_{current_idx}")

        task_results = dict(state.get("task_results", {}))
        task_results[task_id] = {
            **result,
            "task_id": task_id,
            "duration_ms": duration_ms,
        }

        return {
            "task_results": task_results,
            "iteration_count": state.get("iteration_count", 0) + 1,
        }

    async def _execute_memory_op(self, state: AgentStateDict) -> dict[str, Any]:
        """Execute a memory operation (store or recall)."""
        task_plan = state.get("task_plan", [])
        current_idx = state.get("current_task_index", 0)
        current_task = task_plan[current_idx] if current_idx < len(task_plan) else {}

        logger.info("Executing memory operation", task_id=current_task.get("id"))

        result: dict[str, Any]
        if self.memory_agent:
            try:
                result = await self.memory_agent.execute(
                    task=current_task,
                    context={
                        "goal": state["goal"],
                        "previous_results": state.get("task_results", {}),
                        "user_id": state["user_id"],
                    },
                )
            except Exception as e:
                logger.error("Memory agent failed", error=str(e))
                result = {"status": "failed", "error": str(e)}
        else:
            result = {"status": "completed", "output": "Memory operation skipped (no memory agent)"}

        task_id = current_task.get("id", f"task_{current_idx}")
        task_results = dict(state.get("task_results", {}))
        task_results[task_id] = {**result, "task_id": task_id}

        return {
            "task_results": task_results,
            "iteration_count": state.get("iteration_count", 0) + 1,
        }

    async def _integrate_results(self, state: AgentStateDict) -> dict[str, Any]:
        """Integrate task results and determine next steps."""
        task_plan = state.get("task_plan", [])
        current_idx = state.get("current_task_index", 0)
        task_results = state.get("task_results", {})

        current_task = task_plan[current_idx] if current_idx < len(task_plan) else {}
        task_id = current_task.get("id", f"task_{current_idx}")
        current_result = task_results.get(task_id, {})

        logger.info(
            "Integrating results",
            task_id=task_id,
            status=current_result.get("status", "unknown"),
        )

        # Move to next task
        new_index = current_idx + 1

        # Check if current task failed
        errors = list(state.get("errors", []))
        if current_result.get("status") == "failed":
            errors.append({
                "task_id": task_id,
                "agent_type": current_task.get("agent_type", "unknown"),
                "error_type": "task_failure",
                "message": current_result.get("error", "Unknown error"),
                "recoverable": True,
            })

        return {
            "current_task_index": new_index,
            "errors": errors,
        }

    async def _dynamic_replan(self, state: AgentStateDict) -> dict[str, Any]:
        """Dynamically adjust the plan if tasks fail or new discoveries are made."""
        logger.info("Evaluating dynamic replan")
        # In Phase 5, this would use LLM to check if remaining tasks need adjusting
        # For now, it simply tracks the replan count and proceeds.
        return {
            "replan_count": state.get("replan_count", 0) + 1
        }

    def _completion_check(self, state: AgentStateDict) -> str:
        """Check if all tasks are complete or if we should continue."""
        task_plan = state.get("task_plan", [])
        current_idx = state.get("current_task_index", 0)
        iteration = state.get("iteration_count", 0)
        max_iter = state.get("max_iterations", 20)
        errors = state.get("errors", [])

        # Safety check
        if iteration >= max_iter:
            logger.warning("Max iterations reached during completion check")
            return "reflect"

        # All tasks done
        if current_idx >= len(task_plan):
            return "reflect"

        # Too many errors
        if len(errors) > len(task_plan) * 2:
            logger.warning("Too many errors, forcing reflection")
            return "failed"

        return "continue"

    async def _reflect(self, state: AgentStateDict) -> dict[str, Any]:
        """Run the reflection agent to analyze the session."""
        logger.info("Starting reflection phase")

        reflection: dict[str, Any]
        if self.reflection_agent:
            try:
                reflection = await self.reflection_agent.execute(
                    goal=state["goal"],
                    task_plan=state.get("task_plan", []),
                    task_results=state.get("task_results", {}),
                    errors=state.get("errors", []),
                )
            except Exception as e:
                logger.error("Reflection agent failed", error=str(e))
                reflection = {
                    "successes": [],
                    "failures": [str(e)],
                    "root_causes": ["Reflection agent error"],
                    "improvements": [],
                    "confidence_score": 0.0,
                }
        else:
            # Fallback: LLM-based reflection
            task_results = state.get("task_results", {})
            successes = [tid for tid, r in task_results.items() if r.get("status") == "completed"]
            failures = [tid for tid, r in task_results.items() if r.get("status") == "failed"]

            reflection = {
                "successes": [f"Task {tid} completed successfully" for tid in successes],
                "failures": [f"Task {tid} failed: {task_results[tid].get('error', 'unknown')}" for tid in failures],
                "root_causes": [],
                "improvements": [],
                "confidence_score": len(successes) / max(len(task_results), 1),
            }

        return {
            "reflection": reflection,
            "status": "reflecting",
        }

    async def _extract_learnings(self, state: AgentStateDict) -> dict[str, Any]:
        """Extract learnings from reflection."""
        logger.info("Extracting learnings from reflection")
        
        learnings = []
        if self.learning_engine and state.get("reflection"):
            try:
                # We need a session ID, fallback to uuid4 if None
                session_id = uuid.UUID(state.get("session_id")) if state.get("session_id") else uuid.uuid4()
                learnings = await self.learning_engine.extract_learnings(
                    session_id=session_id,
                    reflections=[state.get("reflection")],
                    task_results=state.get("task_results", {}),
                )
                logger.info("Extracted learnings", count=len(learnings))
            except Exception as e:
                logger.error("Learning extraction failed", error=str(e))
                
        return {"learnings": learnings}

    async def _update_strategies(self, state: AgentStateDict) -> dict[str, Any]:
        """Update strategies based on the new learnings."""
        logger.info("Updating strategies")
        # Logic to update strategy confidence happens here or via the LearningEngine
        return {}

    # -----------------------------------------------------------------------
    # Phase 6 Autonomous Research Nodes
    # ---------------------------------------------------------------------------

    async def _knowledge_gap_detection(self, state: AgentStateDict) -> dict[str, Any]:
        """Detect knowledge gaps by analyzing task results and errors."""
        logger.info("Detecting knowledge gaps")

        task_results = state.get("task_results", {})
        errors = state.get("errors", [])
        gaps: list[dict[str, Any]] = []

        for task_id, result in task_results.items():
            if result.get("status") == "failed":
                gaps.append(
                    {
                        "source": task_id,
                        "gap_description": result.get("error") or "Task failed without a recorded error",
                        "severity": "high",
                        "domain": result.get("agent_type", "execution"),
                    }
                )

        for error in errors:
            gaps.append(
                {
                    "source": error.get("task_id", "system"),
                    "gap_description": error.get("message", ""),
                    "severity": "medium" if error.get("recoverable", True) else "high",
                    "domain": error.get("agent_type", "unknown"),
                }
            )

        if not gaps and state.get("reflection"):
            reflection = state.get("reflection") or {}
            for item in reflection.get("improvements", []):
                gaps.append(
                    {
                        "source": "reflection",
                        "gap_description": str(item),
                        "severity": "low",
                        "domain": "learning",
                    }
                )

        try:
            response = await self.llm.ainvoke(
                [
                    SystemMessage(
                        content=(
                            "You detect knowledge gaps in autonomous agent runs. "
                            "Return only a JSON array of gap objects with source, "
                            "gap_description, severity, and domain."
                        )
                    ),
                    HumanMessage(
                        content=(
                            "Analyze this run state for additional knowledge gaps:\n"
                            f"{json.dumps({'goal': state.get('goal'), 'task_results': task_results, 'errors': errors}, default=str)[:4000]}"
                        )
                    ),
                ]
            )
            llm_gaps = json.loads(str(response.content))
            if isinstance(llm_gaps, list):
                gaps.extend(g for g in llm_gaps if isinstance(g, dict))
        except Exception as e:
            logger.warning("Knowledge gap LLM analysis failed", error=str(e))

        return {"knowledge_gaps": gaps}

    async def _goal_generation(self, state: AgentStateDict) -> dict[str, Any]:
        """Generate autonomous research goals from knowledge gaps."""
        logger.info("Generating autonomous goals")
        gaps = state.get("knowledge_gaps", [])
        goals: list[dict[str, Any]] = []

        for index, gap in enumerate(gaps, start=1):
            description = gap.get("gap_description", "Investigate unresolved gap")
            goals.append(
                {
                    "id": f"goal_{index}",
                    "title": f"Resolve {gap.get('domain', 'system')} gap",
                    "description": f"Investigate and address: {description}",
                    "source_gap": gap,
                    "priority": 1 if gap.get("severity") == "high" else 3,
                }
            )

        if gaps:
            try:
                response = await self.llm.ainvoke(
                    [
                        SystemMessage(
                            content=(
                                "You generate concise autonomous research goals. "
                                "Return only a JSON array of goal objects with id, title, "
                                "description, and priority."
                            )
                        ),
                        HumanMessage(
                            content=f"Knowledge gaps:\n{json.dumps(gaps, default=str)[:4000]}"
                        ),
                    ]
                )
                llm_goals = json.loads(str(response.content))
                if isinstance(llm_goals, list) and llm_goals:
                    goals = [g for g in llm_goals if isinstance(g, dict)]
            except Exception as e:
                logger.warning("Goal generation LLM call failed", error=str(e))

        return {"generated_goals": goals}

    async def _curiosity_evaluation(self, state: AgentStateDict) -> dict[str, Any]:
        """Evaluate curiosity scores for goals."""
        logger.info("Evaluating curiosity for goals")
        goals = []
        for goal in state.get("generated_goals", []):
            priority = float(goal.get("priority", 3))
            novelty = 1.0 if goal.get("source_gap", {}).get("domain") not in {"execution", "unknown"} else 0.6
            severity_bonus = 0.3 if goal.get("source_gap", {}).get("severity") == "high" else 0.0
            curiosity_score = min(1.0, max(0.0, (6 - priority) / 5 * 0.6 + novelty * 0.3 + severity_bonus))
            goals.append({**goal, "curiosity_score": round(curiosity_score, 3)})

        goals.sort(key=lambda item: item.get("curiosity_score", 0.0), reverse=True)
        return {"generated_goals": goals}

    async def _research_director(self, state: AgentStateDict) -> dict[str, Any]:
        """Manage research tracks and allocate tasks."""
        logger.info("Director reviewing goals and tracks")
        tracks = []
        for goal in state.get("generated_goals", [])[:5]:
            tracks.append(
                {
                    "track_id": f"track_{goal.get('id', len(tracks) + 1)}",
                    "goal_id": goal.get("id"),
                    "title": goal.get("title", "Autonomous research track"),
                    "status": "planned",
                    "priority": goal.get("priority", 3),
                    "curiosity_score": goal.get("curiosity_score", 0.0),
                    "tasks": [
                        "collect evidence",
                        "evaluate candidate solutions",
                        "record reusable learning",
                    ],
                }
            )
        return {"research_tracks": tracks}

    async def _research_portfolio(self, state: AgentStateDict) -> dict[str, Any]:
        """Update research portfolios."""
        logger.info("Updating research portfolios")
        tracks = state.get("research_tracks", [])
        portfolio_summary = {
            "track_count": len(tracks),
            "planned": sum(1 for track in tracks if track.get("status") == "planned"),
            "average_curiosity": (
                sum(float(track.get("curiosity_score", 0.0)) for track in tracks) / len(tracks)
                if tracks
                else 0.0
            ),
            "high_priority_tracks": [
                track.get("track_id") for track in tracks if int(track.get("priority", 3)) <= 2
            ],
        }
        return {"portfolio_summary": portfolio_summary}

    async def _knowledge_graph_update(self, state: AgentStateDict) -> dict[str, Any]:
        """Update the knowledge graph with new findings."""
        logger.info("Updating knowledge graph")
        # This would integrate with a knowledge graph backend (Neo4j)
        # For now, we just track that the update was triggered
        return {
            "knowledge_graph_updated": True,
            "knowledge_graph_update_summary": {
                "gaps": len(state.get("knowledge_gaps", [])),
                "goals": len(state.get("generated_goals", [])),
                "tracks": len(state.get("research_tracks", [])),
            },
        }

    async def _generate_report(self, state: AgentStateDict) -> dict[str, Any]:
        """Generate a summary report of the goal execution."""
        logger.info("Generating final report")

        prompt = REPORT_GENERATION_PROMPT.format(
            goal=state["goal"],
            results=json.dumps(state.get("task_results", {}), default=str)[:4000],
            reflection=json.dumps(state.get("reflection", {}), default=str)[:2000],
        )

        response = await self.llm.ainvoke([
            SystemMessage(content="You are a concise report generator. Use Markdown formatting."),
            HumanMessage(content=prompt),
        ])

        return {
            "final_report": str(response.content),
            "status": "complete",
        }

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def execute_goal(
        self,
        goal: str,
        user_id: str,
        session_id: str | None = None,
        max_iterations: int = 20,
        context: str | None = None,
        checkpointer: Any = None,
    ) -> dict[str, Any]:
        """
        Execute a goal through the full agent pipeline.

        Args:
            goal: High-level goal description.
            user_id: User identifier.
            session_id: Optional session ID for persistence.
            max_iterations: Maximum agent loop iterations.
            context: Additional context for the goal.
            checkpointer: Optional LangGraph checkpointer.

        Returns:
            Final state dictionary with results and report.
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        initial_state: AgentStateDict = {
            # Phase 1-4: Core
            "goal": goal,
            "goal_analysis": {"context": context} if context else None,
            "task_plan": [],
            "current_task_index": 0,
            "messages": [],
            "task_results": {},
            "errors": [],
            "retrieved_memories": [],
            "retrieved_knowledge": [],
            "reflection": None,
            "session_id": session_id,
            "user_id": user_id,
            "iteration_count": 0,
            "max_iterations": max_iterations,
            "status": "planning",
            "next_agent": None,
            # Phase 5: Meta-Learning
            "task_classification": None,
            "selected_strategy": None,
            "strategy_executions": {},
            "experience_context": None,
            "learnings": [],
            "replan_count": 0,
            # Phase 6: Autonomous Research
            "knowledge_gaps": [],
            "generated_goals": [],
            "research_tracks": [],
            "portfolio_summary": None,
            # Phase 7: Self-Improving Intelligence
            "cognition_reflections": [],
            "failure_patterns": [],
            "research_strategies": [],
            "cognitive_skills": [],
            "cognitive_metrics": [],
            "autonomy_score": 0.0,
            "learning_velocity": 0.0,
            "best_strategy": None,
            "optimization_recommendations": [],
            # Phase 9: World Model
            "hypotheses": [],
            "beliefs": [],
            "experiment_results": [],
            "patterns": [],
            "causal_links": [],
            "experiments": [],
            # Phase 10G: Evolution
            "genome_data": {},
            # Phase 12: Project
            "project": None,
            "opportunities": [],
            "tasks": [],
            # Output
            "final_report": None,
        }

        compiled = self.compile(checkpointer=checkpointer)

        config = {"configurable": {"thread_id": session_id}}

        logger.info(
            "Starting goal execution",
            session_id=session_id,
            goal=goal[:100],
            max_iterations=max_iterations,
        )

        final_state = await compiled.ainvoke(initial_state, config=config)

        logger.info(
            "Goal execution complete",
            session_id=session_id,
            status=final_state.get("status"),
            tasks_completed=len(final_state.get("task_results", {})),
        )

        return dict(final_state)
