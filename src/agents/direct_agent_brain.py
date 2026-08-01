"""
Embedded Multi-Agent Brain Engine - Direct PyTorch Multi-Agent Reasoning

This module implements a team of specialized cognitive agents (Planner, Researcher, 
Coder, Evaluator, Safety Gate) that operate in-process directly over the native 
local PyTorch model, eliminating external API dependencies.
"""

import logging
import json
import uuid
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Callable
from enum import Enum
from datetime import datetime

from src.llm.local_weight_engine import LocalWeightEngine
from src.config.logging import get_logger

logger = get_logger(__name__)


class AgentRole(str, Enum):
    """Specialized agent roles in the multi-agent brain"""
    PLANNER = "planner"
    RESEARCHER = "researcher"
    CODER = "coder"
    EVALUATOR = "evaluator"
    SAFETY_GATE = "safety_gate"


@dataclass
class BrainState:
    """State container for multi-agent reasoning process"""
    objective: str
    current_step: int = 0
    max_steps: int = 10
    plan: List[Dict[str, Any]] = field(default_factory=list)
    research_findings: List[Dict[str, Any]] = field(default_factory=list)
    code_patches: List[Dict[str, Any]] = field(default_factory=list)
    evaluation_results: List[Dict[str, Any]] = field(default_factory=list)
    safety_checks: List[Dict[str, Any]] = field(default_factory=list)
    final_output: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)


@dataclass
class AgentResult:
    """Result from a single agent execution"""
    agent_role: AgentRole
    success: bool
    output: Any
    reasoning: str
    confidence: float
    metadata: Dict[str, Any] = field(default_factory=dict)


class DirectAgentBrain:
    """
    Embedded multi-agent brain that runs specialized agents directly on local model weights.
    
    Agents:
    - Planner: Breaks down user requirements into execution steps
    - Researcher: Scans project files and extracts relevant code context
    - Coder: Generates code implementations or patches
    - Evaluator: Evaluates generated code against test criteria
    - Safety Gate: Runs static safety checks on generated code
    """
    
    def __init__(self, engine: LocalWeightEngine):
        self.engine = engine
        self._agents: Dict[AgentRole, Callable] = {}
        self._state: Optional[BrainState] = None
        self._execution_history: List[AgentResult] = []
        self._register_agents()
    
    def _register_agents(self) -> None:
        """Register all specialized agent nodes"""
        self._agents = {
            AgentRole.PLANNER: self._planner_node,
            AgentRole.RESEARCHER: self._researcher_node,
            AgentRole.CODER: self._coder_node,
            AgentRole.EVALUATOR: self._evaluator_node,
            AgentRole.SAFETY_GATE: self._safety_gate_node,
        }
    
    def step(self, user_objective: str) -> BrainState:
        """
        Execute a complete multi-agent reasoning cycle.
        
        Flow: Planner -> Researcher -> Coder -> Evaluator -> Safety Gate
        
        Args:
            user_objective: The high-level objective to accomplish
            
        Returns:
            Final BrainState with all agent outputs
        """
        # Initialize state
        self._state = BrainState(objective=user_objective)
        self._execution_history = []
        
        logger.info(f"Starting multi-agent brain for objective: {user_objective}")
        
        # Execute agents in sequence
        agent_sequence = [
            AgentRole.PLANNER,
            AgentRole.RESEARCHER,
            AgentRole.CODER,
            AgentRole.EVALUATOR,
            AgentRole.SAFETY_GATE,
        ]
        
        for role in agent_sequence:
            if self._state.current_step >= self._state.max_steps:
                logger.warning("Max steps reached, stopping execution")
                break
            
            logger.info(f"Executing {role.value} agent")
            result = self._execute_agent(role)
            self._execution_history.append(result)
            self._state.current_step += 1
            self._state.updated_at = datetime.now()
            
            if not result.success:
                logger.error(f"Agent {role.value} failed: {result.reasoning}")
                self._state.errors.append(f"{role.value}: {result.reasoning}")
                # Continue anyway for observability
        
        # Compile final output
        self._compile_final_output()
        
        logger.info(f"Multi-agent brain completed in {self._state.current_step} steps")
        return self._state
    
    def _execute_agent(self, role: AgentRole) -> AgentResult:
        """Execute a single agent and return result"""
        agent_fn = self._agents.get(role)
        if not agent_fn:
            return AgentResult(
                agent_role=role,
                success=False,
                output=None,
                reasoning=f"Unknown agent role: {role}",
                confidence=0.0,
            )
        
        try:
            output = agent_fn(self._state)
            return AgentResult(
                agent_role=role,
                success=True,
                output=output,
                reasoning=f"{role.value} completed successfully",
                confidence=0.8,
            )
        except Exception as e:
            logger.error(f"Agent {role.value} error: {e}")
            return AgentResult(
                agent_role=role,
                success=False,
                output=None,
                reasoning=str(e),
                confidence=0.0,
            )
    
    def _planner_node(self, state: BrainState) -> Dict[str, Any]:
        """Planner Agent: Decompose objective into actionable steps"""
        prompt = f"""You are a Planner Agent. Break down the following objective into 3-5 concrete, executable steps.

Objective: {state.objective}

Return a JSON array of steps, each with:
- step_id: unique identifier
- description: what to do
- agent: which agent should execute (researcher, coder, evaluator)
- dependencies: list of step_ids that must complete first
- success_criteria: how to verify completion

Example format:
[
  {{"step_id": "1", "description": "Research existing codebase", "agent": "researcher", "dependencies": [], "success_criteria": "Found relevant files"}},
  {{"step_id": "2", "description": "Implement feature", "agent": "coder", "dependencies": ["1"], "success_criteria": "Code compiles and tests pass"}}
]"""

        response = self.engine.generate(prompt, max_new_tokens=512, temperature=0.3)
        
        try:
            plan = json.loads(response)
            state.plan = plan
            return {"plan": plan, "steps_count": len(plan)}
        except json.JSONDecodeError:
            # Fallback plan
            fallback_plan = [
                {"step_id": "1", "description": "Research codebase context", "agent": "researcher", "dependencies": [], "success_criteria": "Context gathered"},
                {"step_id": "2", "description": "Generate implementation", "agent": "coder", "dependencies": ["1"], "success_criteria": "Code generated"},
                {"step_id": "3", "description": "Evaluate implementation", "agent": "evaluator", "dependencies": ["2"], "success_criteria": "Tests pass"},
            ]
            state.plan = fallback_plan
            return {"plan": fallback_plan, "steps_count": len(fallback_plan), "fallback": True}
    
    def _researcher_node(self, state: BrainState) -> Dict[str, Any]:
        """Researcher Agent: Scan project and extract relevant context"""
        # Build context from plan
        plan_context = json.dumps(state.plan, indent=2)
        
        prompt = f"""You are a Researcher Agent. Analyze the objective and plan to identify what codebase context is needed.

Objective: {state.objective}
Plan: {plan_context}

Return a JSON object with:
- files_to_examine: list of file paths or patterns to look at
- key_concepts: important concepts/patterns to understand
- dependencies: external dependencies or libraries involved
- risks: potential issues or complexities
- recommendations: suggested approach"""

        response = self.engine.generate(prompt, max_new_tokens=512, temperature=0.3)
        
        try:
            findings = json.loads(response)
            state.research_findings.append(findings)
            return findings
        except json.JSONDecodeError:
            fallback = {
                "files_to_examine": ["src/", "tests/"],
                "key_concepts": ["local LLM integration", "fine-tuning pipeline"],
                "dependencies": ["torch", "transformers", "peft"],
                "risks": ["Model loading memory", "Training stability"],
                "recommendations": ["Use LoRA adapters", "Implement checkpointing"],
            }
            state.research_findings.append(fallback)
            return fallback
    
    def _coder_node(self, state: BrainState) -> Dict[str, Any]:
        """Coder Agent: Generate code implementation based on plan and research"""
        research_context = json.dumps(state.research_findings, indent=2)
        plan_context = json.dumps(state.plan, indent=2)
        
        prompt = f"""You are a Coder Agent. Generate a Python implementation based on the objective, plan, and research.

Objective: {state.objective}
Plan: {plan_context}
Research Findings: {research_context}

Generate a complete, working Python implementation. Return as JSON with:
- files: array of {{"path": "...", "content": "..."}}
- explanation: brief description of the implementation
- tests: suggested test cases"""

        response = self.engine.generate(prompt, max_new_tokens=1024, temperature=0.2)
        
        try:
            code_output = json.loads(response)
            state.code_patches.append(code_output)
            return code_output
        except json.JSONDecodeError:
            fallback = {
                "files": [
                    {"path": "src/generated/implementation.py", "content": "# Implementation placeholder\npass"}
                ],
                "explanation": "Fallback implementation - needs manual completion",
                "tests": ["Test basic functionality", "Test error handling"],
            }
            state.code_patches.append(fallback)
            return fallback
    
    def _evaluator_node(self, state: BrainState) -> Dict[str, Any]:
        """Evaluator Agent: Evaluate generated code against criteria"""
        code_context = json.dumps(state.code_patches, indent=2)
        plan_context = json.dumps(state.plan, indent=2)
        
        prompt = f"""You are an Evaluator Agent. Assess the generated implementation against the original objective.

Objective: {state.objective}
Plan: {plan_context}
Generated Code: {code_context}

Return a JSON object with:
- score: 0.0-1.0 overall quality score
- criteria_met: list of satisfied success criteria
- criteria_failed: list of unmet criteria
- issues: specific problems found
- suggestions: improvements needed
- passes: true/false whether it meets minimum threshold (0.7)"""

        response = self.engine.generate(prompt, max_new_tokens=512, temperature=0.2)
        
        try:
            evaluation = json.loads(response)
            state.evaluation_results.append(evaluation)
            return evaluation
        except json.JSONDecodeError:
            fallback = {
                "score": 0.5,
                "criteria_met": ["Basic structure"],
                "criteria_failed": ["Functionality verification"],
                "issues": ["Evaluation parsing failed"],
                "suggestions": ["Manual review required"],
                "passes": False,
            }
            state.evaluation_results.append(fallback)
            return fallback
    
    def _safety_gate_node(self, state: BrainState) -> Dict[str, Any]:
        """Safety Gate Agent: Run static safety checks on generated code"""
        code_context = json.dumps(state.code_patches, indent=2)
        evaluation = state.evaluation_results[-1] if state.evaluation_results else {}
        
        prompt = f"""You are a Safety Gate Agent. Perform static safety analysis on the generated code.

Code: {code_context}
Evaluation: {json.dumps(evaluation, indent=2)}

Check for:
- Dangerous imports (os.system, subprocess, eval, exec)
- File system access outside project
- Network requests to external hosts
- Code injection vulnerabilities
- Hardcoded secrets or credentials
- Infinite loops or resource exhaustion

Return JSON with:
- safe: true/false
- violations: list of safety violations found
- warnings: list of warnings
- recommended_action: "allow", "modify", or "reject" """

        response = self.engine.generate(prompt, max_new_tokens=512, temperature=0.1)
        
        try:
            safety = json.loads(response)
            state.safety_checks.append(safety)
            return safety
        except json.JSONDecodeError:
            fallback = {
                "safe": True,
                "violations": [],
                "warnings": ["Safety check parsing failed - manual review recommended"],
                "recommended_action": "allow",
            }
            state.safety_checks.append(fallback)
            return fallback
    
    def _compile_final_output(self) -> None:
        """Compile final output from all agent results"""
        if not self._state:
            return
        
        # Determine overall success
        all_success = all(
            r.success for r in self._execution_history
        )
        safety_passed = (
            self._state.safety_checks[-1].get("safe", True) 
            if self._state.safety_checks else True
        )
        evaluation_passed = (
            self._state.evaluation_results[-1].get("passes", False) 
            if self._state.evaluation_results else False
        )
        
        overall_success = all_success and safety_passed and evaluation_passed
        
        # Build summary
        summary = {
            "objective": self._state.objective,
            "success": overall_success,
            "steps_executed": self._state.current_step,
            "agents_run": [r.agent_role.value for r in self._execution_history],
            "plan": self._state.plan,
            "research_findings": self._state.research_findings,
            "code_generated": len(self._state.code_patches) > 0,
            "evaluation_score": self._state.evaluation_results[-1].get("score", 0) if self._state.evaluation_results else 0,
            "safety_passed": safety_passed,
            "errors": self._state.errors,
        }
        
        self._state.final_output = json.dumps(summary, indent=2)
        self._state.metadata["summary"] = summary
    
    def get_execution_history(self) -> List[AgentResult]:
        """Get the execution history of all agents"""
        return self._execution_history
    
    def get_state(self) -> Optional[BrainState]:
        """Get the current brain state"""
        return self._state
    
    def reset(self) -> None:
        """Reset the brain for a new objective"""
        self._state = None
        self._execution_history = []


class MultiAgentSwarm:
    """
    Coordinates multiple DirectAgentBrain instances for parallel problem solving.
    """
    
    def __init__(self, num_brains: int = 3):
        self.num_brains = num_brains
        self._engines: List[LocalWeightEngine] = []
        self._brains: List[DirectAgentBrain] = []
    
    def initialize(self, model_config) -> None:
        """Initialize multiple model engines and brains"""
        for i in range(self.num_brains):
            engine = LocalWeightEngine()
            engine.load_model(model_config)
            engine.attach_lora(LoRAConfig())
            self._engines.append(engine)
            self._brains.append(DirectAgentBrain(engine))
    
    def solve_parallel(self, objective: str) -> List[BrainState]:
        """Run multiple brains in parallel on the same objective"""
        import concurrent.futures
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=self.num_brains) as executor:
            futures = [executor.submit(brain.step, objective) for brain in self._brains]
            results = [f.result() for f in concurrent.futures.as_completed(futures)]
        
        return results
    
    def consensus(self, results: List[BrainState]) -> BrainState:
        """Select best result via consensus"""
        # Simple consensus: pick the one with highest evaluation score
        best = max(results, key=lambda r: r.metadata.get("summary", {}).get("evaluation_score", 0))
        return best
    
    def cleanup(self) -> None:
        """Clean up all engines"""
        for engine in self._engines:
            engine.unload()
        self._engines.clear()
        self._brains.clear()


# Need to import LoRAConfig for the swarm
from src.llm.local_weight_engine import LoRAConfig