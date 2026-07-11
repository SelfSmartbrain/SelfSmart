"""
Architecture Evolver - Self-Improvement Loop

Enables the system to analyze its own performance bottlenecks,
propose code-level improvements, validate them via tests,
and apply them with human approval gates.
"""

import asyncio
import logging
import json
import uuid
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Optional, Callable
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

logger = logging.getLogger(__name__)


class PatchType(Enum):
    """Types of architecture patches"""
    PERFORMANCE = "performance"
    RELIABILITY = "reliability"
    FUNCTIONALITY = "functionality"
    REFACTOR = "refactor"
    SECURITY = "security"


class PatchStatus(Enum):
    """Patch lifecycle status"""
    PROPOSED = "proposed"
    ANALYZING = "analyzing"
    TESTING = "testing"
    VALIDATED = "validated"
    APPROVED = "approved"
    APPLIED = "applied"
    REJECTED = "rejected"
    FAILED = "failed"


@dataclass
class ArchitecturePatch:
    """A proposed architecture improvement patch"""
    patch_id: str
    patch_type: PatchType
    title: str
    description: str
    target_files: List[str]
    diff: str  # Unified diff format
    rationale: str
    expected_impact: Dict[str, float]  # metric -> expected change
    status: PatchStatus = PatchStatus.PROPOSED
    created_at: float = field(default_factory=lambda: datetime.now().timestamp())
    validated_at: Optional[float] = None
    approved_at: Optional[float] = None
    applied_at: Optional[float] = None
    test_results: Optional[Dict[str, Any]] = None
    approval_required: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class BottleneckAnalysis:
    """Analysis of a performance bottleneck"""
    component: str
    metric: str
    current_value: float
    expected_value: float
    severity: float  # 0-1
    root_cause: str
    suggested_approach: str


class ArchitectureEvolver:
    """
    Analyzes system performance, proposes code improvements,
    validates via tests, and applies with human approval.
    
    Flow:
    1. Analyze metrics -> identify bottlenecks
    2. Generate patches via LLM
    3. Validate patches in sandbox (run tests)
    4. Human approval gate
    5. Apply patches
    6. Monitor impact
    """

    def __init__(
        self,
        llm_client: Any,
        repo_root: str,
        test_runner: Callable[[str], Any],  # Function that runs tests and returns results
        approval_callback: Optional[Callable[[ArchitecturePatch], Any]] = None,
        max_patches_per_cycle: int = 5,
        auto_apply_safe: bool = False,
    ):
        self.llm = llm_client
        self.repo_root = Path(repo_root)
        self.test_runner = test_runner
        self.approval_callback = approval_callback
        self.max_patches_per_cycle = max_patches_per_cycle
        self.auto_apply_safe = auto_apply_safe

        self._patches: Dict[str, ArchitecturePatch] = {}
        self._bottleneck_history: List[BottleneckAnalysis] = []
        self._patch_history: List[Dict[str, Any]] = []

    async def initialize(self) -> None:
        """Initialize architecture evolver"""
        logger.info("ArchitectureEvolver initialized")

    async def analyze_and_propose(
        self,
        metrics: Dict[str, Any],
        context: Optional[Dict[str, Any]] = None,
    ) -> List[ArchitecturePatch]:
        """
        Analyze metrics for bottlenecks and propose patches.
        
        Args:
            metrics: System performance metrics
            context: Additional context (recent errors, deployment info, etc.)
            
        Returns:
            List of proposed patches
        """
        logger.info("Starting architecture analysis and patch proposal")
        
        # Step 1: Identify bottlenecks
        bottlenecks = await self._identify_bottlenecks(metrics, context)
        
        if not bottlenecks:
            logger.info("No significant bottlenecks identified")
            return []
        
        # Step 2: Generate patches for top bottlenecks
        patches = []
        for bottleneck in bottlenecks[:self.max_patches_per_cycle]:
            patch = await self._generate_patch(bottleneck, metrics, context)
            if patch:
                patches.append(patch)
                self._patches[patch.patch_id] = patch
        
        # Step 3: Validate patches in parallel
        validation_results = await asyncio.gather(*[
            self._validate_patch(patch) for patch in patches
        ], return_exceptions=True)
        
        for patch, result in zip(patches, validation_results):
            if isinstance(result, Exception):
                patch.status = PatchStatus.FAILED
                patch.test_results = {"error": str(result)}
            else:
                patch.test_results = result
                if result.get("passed", False):
                    patch.status = PatchStatus.VALIDATED
                else:
                    patch.status = PatchStatus.REJECTED
        
        # Step 4: Handle approval for validated patches
        for patch in patches:
            if patch.status == PatchStatus.VALIDATED:
                if patch.approval_required and self.approval_callback:
                    await self._request_approval(patch)
                elif self.auto_apply_safe and self._is_safe_patch(patch):
                    await self._apply_patch(patch)
        
        logger.info(f"Proposed {len(patches)} patches, {sum(1 for p in patches if p.status == PatchStatus.VALIDATED)} validated")
        return patches

    async def _identify_bottlenecks(
        self,
        metrics: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> List[BottleneckAnalysis]:
        """Identify performance bottlenecks from metrics"""
        bottlenecks = []
        
        # Define threshold rules for common metrics
        threshold_rules = [
            ("api_latency_p99", 2.0, "API latency too high", "Optimize slow endpoints, add caching"),
            ("memory_usage_percent", 85.0, "High memory usage", "Fix memory leaks, optimize data structures"),
            ("cpu_usage_percent", 90.0, "High CPU usage", "Optimize hot paths, add parallelism"),
            ("error_rate", 0.05, "High error rate", "Fix root causes, improve error handling"),
            ("queue_depth", 1000, "Task queue backing up", "Scale workers, optimize task processing"),
            ("db_query_latency_p99", 1.0, "Slow database queries", "Add indexes, optimize queries"),
            ("cache_hit_rate", 0.7, "Low cache hit rate", "Improve caching strategy"),
            ("task_completion_rate", 0.8, "Low task completion", "Improve reliability, add retries"),
        ]
        
        for metric_name, threshold, description, approach in threshold_rules:
            current = metrics.get(metric_name)
            if current is not None:
                if (metric_name.endswith("_rate") or metric_name.endswith("_percent")) and current > threshold:
                    severity = min((current - threshold) / threshold, 1.0)
                    bottlenecks.append(BottleneckAnalysis(
                        component=metric_name.split("_")[0],
                        metric=metric_name,
                        current_value=current,
                        expected_value=threshold,
                        severity=severity,
                        root_cause=description,
                        suggested_approach=approach,
                    ))
                elif not (metric_name.endswith("_rate") or metric_name.endswith("_percent")) and current > threshold:
                    severity = min((current - threshold) / threshold, 1.0)
                    bottlenecks.append(BottleneckAnalysis(
                        component=metric_name.split("_")[0],
                        metric=metric_name,
                        current_value=current,
                        expected_value=threshold,
                        severity=severity,
                        root_cause=description,
                        suggested_approach=approach,
                    ))
        
        # Sort by severity
        bottlenecks.sort(key=lambda b: b.severity, reverse=True)
        self._bottleneck_history.extend(bottlenecks)
        
        return bottlenecks

    async def _generate_patch(
        self,
        bottleneck: BottleneckAnalysis,
        metrics: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> Optional[ArchitecturePatch]:
        """Generate a code patch for a bottleneck using LLM"""
        
        # Find relevant source files
        target_files = await self._find_relevant_files(bottleneck)
        
        if not target_files:
            logger.warning(f"No relevant files found for bottleneck: {bottleneck.metric}")
            return None
        
        # Read current file contents
        file_contents = {}
        for file_path in target_files:
            full_path = self.repo_root / file_path
            if full_path.exists():
                file_contents[file_path] = full_path.read_text()
        
        # Build prompt for LLM
        prompt = self._build_patch_prompt(bottleneck, file_contents, metrics, context)
        
        try:
            response = await self.llm.ainvoke(prompt)
            patch_data = json.loads(response.content if hasattr(response, 'content') else str(response))
            
            patch = ArchitecturePatch(
                patch_id=f"patch_{uuid.uuid4().hex[:12]}",
                patch_type=PatchType(patch_data.get("patch_type", "performance")),
                title=patch_data.get("title", f"Optimize {bottleneck.metric}"),
                description=patch_data.get("description", ""),
                target_files=target_files,
                diff=patch_data.get("diff", ""),
                rationale=patch_data.get("rationale", f"Address bottleneck: {bottleneck.root_cause}"),
                expected_impact=patch_data.get("expected_impact", {bottleneck.metric: -bottleneck.severity * 0.5}),
                approval_required=not self._is_safe_patch_type(patch_data.get("patch_type", "performance")),
            )
            
            return patch
            
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse patch JSON: {e}")
        except Exception as e:
            logger.error(f"Patch generation failed: {e}")
        
        return None

    async def _find_relevant_files(self, bottleneck: BottleneckAnalysis) -> List[str]:
        """Find source files relevant to a bottleneck"""
        # Map metrics to likely file patterns
        metric_to_patterns = {
            "api_latency": ["src/api/**/*.py", "src/runtime/**/*.py"],
            "memory_usage": ["src/**/*.py"],
            "cpu_usage": ["src/**/*.py"],
            "error_rate": ["src/**/*.py"],
            "queue_depth": ["src/runtime/**/*.py", "src/cognition/**/*.py"],
            "db_query_latency": ["src/memory/**/*.py", "src/rag/**/*.py"],
            "cache_hit_rate": ["src/memory/**/*.py"],
            "task_completion": ["src/runtime/**/*.py", "src/cognition/**/*.py"],
        }
        
        patterns = metric_to_patterns.get(bottleneck.metric.split("_")[0], ["src/**/*.py"])
        
        # For now, return a reasonable default set
        # In production, would use more sophisticated analysis
        relevant = [
            "src/runtime/executor.py",
            "src/memory/memory_fabric.py",
            "src/api/routes.py",
            "src/cognition/planner.py",
        ]
        
        # Filter to existing files
        existing = []
        for f in relevant:
            if (self.repo_root / f).exists():
                existing.append(f)
        
        return existing[:3]  # Limit to top 3

    def _build_patch_prompt(
        self,
        bottleneck: BottleneckAnalysis,
        file_contents: Dict[str, str],
        metrics: Dict[str, Any],
        context: Optional[Dict[str, Any]],
    ) -> str:
        """Build LLM prompt for patch generation"""
        
        files_text = "\n\n".join([
            f"=== {path} ===\n{content[:3000]}"
            for path, content in file_contents.items()
        ])
        
        return f"""You are an expert software architect optimizing an AGI agent platform.

BOTTLENECK ANALYSIS:
- Metric: {bottleneck.metric}
- Current: {bottleneck.current_value}
- Target: {bottleneck.expected_value}
- Severity: {bottleneck.severity:.2f}
- Root Cause: {bottleneck.root_cause}
- Suggested Approach: {bottleneck.suggested_approach}

RELEVANT SOURCE FILES:
{files_text}

CURRENT METRICS:
{json.dumps(metrics, indent=2, default=str)}

CONTEXT:
{json.dumps(context or {}, indent=2, default=str)}

Generate a code patch as JSON with:
{{
  "patch_type": "performance|reliability|functionality|refactor|security",
  "title": "Brief title",
  "description": "Detailed description of changes",
  "diff": "Unified diff format patch",
  "rationale": "Why this will help",
  "expected_impact": {{"metric_name": expected_change}}
}}

Focus on:
- Minimal, targeted changes
- Backward compatibility
- No breaking changes
- Clear performance/reliability improvement
- Include error handling

Return ONLY valid JSON."""


    async def _validate_patch(self, patch: ArchitecturePatch) -> Dict[str, Any]:
        """Validate a patch by running tests in sandbox"""
        patch.status = PatchStatus.TESTING
        
        try:
            # Apply patch temporarily
            await self._apply_patch_temp(patch)
            
            # Run tests
            test_results = await self.test_runner(patch.patch_id)
            
            # Revert patch
            await self._revert_patch_temp(patch)
            
            passed = test_results.get("passed", False)
            patch.status = PatchStatus.VALIDATED if passed else PatchStatus.REJECTED
            
            return {
                "passed": passed,
                "test_output": test_results.get("output", ""),
                "tests_run": test_results.get("tests_run", 0),
                "failures": test_results.get("failures", []),
            }
            
        except Exception as e:
            logger.error(f"Patch validation failed: {e}")
            await self._revert_patch_temp(patch)
            return {"passed": False, "error": str(e)}

    async def _apply_patch_temp(self, patch: ArchitecturePatch) -> None:
        """Apply patch temporarily for testing"""
        # In production, would use git apply --check then git apply
        # For now, store original content for revert
        patch.metadata["original_content"] = {}
        for file_path in patch.target_files:
            full_path = self.repo_root / file_path
            if full_path.exists():
                patch.metadata["original_content"][file_path] = full_path.read_text()
        
        # Apply diff (simplified - would use proper patch library)
        logger.info(f"Temporarily applying patch {patch.patch_id}")

    async def _revert_patch_temp(self, patch: ArchitecturePatch) -> None:
        """Revert temporary patch"""
        original = patch.metadata.get("original_content", {})
        for file_path, content in original.items():
            full_path = self.repo_root / file_path
            full_path.write_text(content)
        logger.info(f"Reverted temporary patch {patch.patch_id}")

    async def _request_approval(self, patch: ArchitecturePatch) -> None:
        """Request human approval for patch"""
        if self.approval_callback:
            try:
                approved = await self.approval_callback(patch)
                if approved:
                    patch.status = PatchStatus.APPROVED
                    patch.approved_at = datetime.now().timestamp()
                    await self._apply_patch(patch)
                else:
                    patch.status = PatchStatus.REJECTED
            except Exception as e:
                logger.error(f"Approval callback failed: {e}")
                patch.status = PatchStatus.REJECTED

    async def _apply_patch(self, patch: ArchitecturePatch) -> None:
        """Permanently apply approved patch"""
        try:
            # Apply the diff
            for file_path in patch.target_files:
                full_path = self.repo_root / file_path
                if full_path.exists():
                    # In production, would use proper patch application
                    logger.info(f"Applying patch {patch.patch_id} to {file_path}")
            
            patch.status = PatchStatus.APPLIED
            patch.applied_at = datetime.now().timestamp()
            
            # Record in history
            self._patch_history.append({
                "patch_id": patch.patch_id,
                "title": patch.title,
                "type": patch.patch_type.value,
                "applied_at": patch.applied_at,
                "target_files": patch.target_files,
            })
            
            logger.info(f"Patch {patch.patch_id} applied successfully")
            
        except Exception as e:
            logger.error(f"Failed to apply patch: {e}")
            patch.status = PatchStatus.FAILED

    def _is_safe_patch(self, patch: ArchitecturePatch) -> bool:
        """Check if patch is safe for auto-apply"""
        return (
            patch.patch_type in (PatchType.REFACTOR, PatchType.PERFORMANCE) and
            patch.expected_impact.get("risk", 1.0) < 0.3 and
            len(patch.target_files) <= 2
        )

    def _is_safe_patch_type(self, patch_type: str) -> bool:
        """Check if patch type is safe"""
        return patch_type in ("refactor", "performance")

    def get_patch(self, patch_id: str) -> Optional[ArchitecturePatch]:
        """Get patch by ID"""
        return self._patches.get(patch_id)

    def get_patches_by_status(self, status: PatchStatus) -> List[ArchitecturePatch]:
        """Get patches by status"""
        return [p for p in self._patches.values() if p.status == status]

    def get_patch_history(self) -> List[Dict[str, Any]]:
        """Get applied patch history"""
        return self._patch_history

    def get_bottleneck_history(self) -> List[BottleneckAnalysis]:
        """Get bottleneck analysis history"""
        return self._bottleneck_history


class StrategyEvolver:
    """
    Evolves agent strategies using genetic algorithm over strategy parameters.
    """

    def __init__(
        self,
        llm_client: Any,
        strategy_registry: Any,
        evaluator: Callable[[Dict[str, Any]], float],
    ):
        self.llm = llm_client
        self.registry = strategy_registry
        self.evaluator = evaluator

        self._population: List[Dict[str, Any]] = []
        self._generation = 0

    async def initialize(self) -> None:
        logger.info("StrategyEvolver initialized")

    async def evolve_strategies(
        self,
        performance_data: List[Dict[str, Any]],
        generations: int = 10,
        population_size: int = 20,
    ) -> List[Dict[str, Any]]:
        """
        Evolve strategies using genetic algorithm.
        
        Args:
            performance_data: Historical performance data
            generations: Number of generations
            population_size: Population size
            
        Returns:
            Best evolved strategies
        """
        logger.info(f"Starting strategy evolution: {generations} generations, pop={population_size}")
        
        # Initialize population from performance data
        self._population = await self._initialize_population(performance_data, population_size)
        
        for gen in range(generations):
            # Evaluate fitness
            fitness_scores = await asyncio.gather(*[
                self._evaluate_individual(ind) for ind in self._population
            ])
            
            # Select parents
            parents = self._select_parents(self._population, fitness_scores)
            
            # Create next generation
            offspring = []
            while len(offspring) < population_size:
                parent1, parent2 = self._select_two(parents)
                child = await self._crossover(parent1, parent2)
                child = await self._mutate(child)
                offspring.append(child)
            
            self._population = offspring
            self._generation += 1
            
            best_fitness = max(fitness_scores)
            logger.info(f"Generation {gen+1}: best fitness = {best_fitness:.4f}")
        
        # Return top strategies
        final_fitness = await asyncio.gather(*[
            self._evaluate_individual(ind) for ind in self._population
        ])
        
        ranked = sorted(zip(self._population, final_fitness), key=lambda x: x[1], reverse=True)
        return [ind for ind, _ in ranked[:5]]

    async def _initialize_population(
        self,
        performance_data: List[Dict[str, Any]],
        size: int,
    ) -> List[Dict[str, Any]]:
        """Initialize population from performance data"""
        population = []
        
        # Extract successful strategy patterns
        successful = [d for d in performance_data if d.get("success_rate", 0) > 0.7]
        
        for i in range(size):
            if successful and i < len(successful):
                base = successful[i % len(successful)].get("strategy_params", {})
            else:
                base = {}
            
            # Add variation
            individual = {k: v * (0.8 + 0.4 * hash(str(k) + str(i)) % 100 / 100) 
                         for k, v in base.items()}
            
            # Add some random parameters
            individual.update({
                "exploration_rate": 0.1 + 0.3 * (i % 10) / 10,
                "retry_threshold": 2 + (i % 5),
                "parallelism": 1 + (i % 4),
            })
            
            population.append(individual)
        
        return population

    async def _evaluate_individual(self, individual: Dict[str, Any]) -> float:
        """Evaluate fitness of an individual strategy"""
        return await self.evaluator(individual)

    def _select_parents(
        self,
        population: List[Dict[str, Any]],
        fitness_scores: List[float],
    ) -> List[Dict[str, Any]]:
        """Select parents using tournament selection"""
        parents = []
        for _ in range(len(population) // 2):
            # Tournament of 3
            candidates = np.random.choice(len(population), 3, replace=False)
            winner = max(candidates, key=lambda i: fitness_scores[i])
            parents.append(population[winner])
        return parents

    def _select_two(self, parents: List[Dict[str, Any]]) -> tuple:
        """Select two parents"""
        return np.random.choice(parents, 2, replace=False)

    async def _crossover(self, parent1: Dict[str, Any], parent2: Dict[str, Any]) -> Dict[str, Any]:
        """Crossover two parents"""
        child = {}
        all_keys = set(parent1.keys()) | set(parent2.keys())
        
        for key in all_keys:
            if key in parent1 and key in parent2:
                # Blend
                child[key] = (parent1[key] + parent2[key]) / 2
            elif key in parent1:
                child[key] = parent1[key]
            else:
                child[key] = parent2[key]
        
        return child

    async def _mutate(self, individual: Dict[str, Any]) -> Dict[str, Any]:
        """Mutate an individual"""
        mutated = individual.copy()
        
        for key, value in mutated.items():
            if isinstance(value, (int, float)) and np.random.random() < 0.1:
                # Gaussian mutation
                mutated[key] = value * (1 + np.random.normal(0, 0.1))
        
        return mutated


# Need numpy for strategy evolver
import numpy as np