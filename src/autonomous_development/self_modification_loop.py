"""
Self-Modification Loop - Orchestrates self-improvement cycle.

Coordinates SelfDevelopment analysis, PatchGenerator code generation,
safety validation, sandbox testing, and controlled deployment.
"""

import asyncio
import logging
import shutil
import tempfile
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
from contextlib import asynccontextmanager

from src.autonomous_development.self_development import (
    SelfDevelopment,
    SafetyLevel,
    AnalysisResult,
    ImprovementPlan,
)
from src.coding.patch_generator import PatchGenerator, GeneratedPatch, FileChange
from src.autonomous_development.patch_applier import PatchApplier, PatchResult
from src.autonomous_development.test_runner import TestRunner, TestResult
from src.autonomous_development.rollback_manager import RollbackManager
from src.safety.self_patch_safety_gate import SelfPatchSafetyGate, SafetyAssessment

logger = logging.getLogger(__name__)


class ModificationPhase(Enum):
    """Phases of the self-modification cycle."""
    IDLE = "idle"
    ANALYZING = "analyzing"
    PLANNING = "planning"
    GENERATING_PATCHES = "generating_patches"
    SAFETY_CHECK = "safety_check"
    SANDBOX_TESTING = "sandbox_testing"
    DEPLOYING = "deploying"
    VALIDATING = "validating"
    ROLLING_BACK = "rolling_back"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ModificationConfig:
    """Configuration for self-modification loop."""
    
    # Repository
    repo_path: str = "/Users/subh/Documents/selfsmart"
    target_branch: str = "main"
    
    # Safety
    max_safety_level: SafetyLevel = SafetyLevel.MODERATE
    require_approval: bool = True
    require_tests_pass: bool = True
    require_sandbox_pass: bool = True
    
    # Testing
    test_command: str = "pytest -x -q"
    test_timeout: int = 300
    sandbox_test_command: Optional[str] = None
    
    # Limits
    max_changes_per_cycle: int = 5
    max_patch_size_lines: int = 500
    max_concurrent_tests: int = 2
    
    # Scheduling
    cycle_interval_hours: int = 24
    min_cycle_interval_hours: int = 6
    
    # Rollback
    auto_rollback_on_failure: bool = True
    keep_backups: int = 10
    
    # Notifications
    notify_on_success: bool = True
    notify_on_failure: bool = True
    notification_webhook: Optional[str] = None


@dataclass
class ModificationCycle:
    """Represents a single self-modification cycle."""
    cycle_id: str
    started_at: datetime
    phase: ModificationPhase = ModificationPhase.IDLE
    analysis_results: List[AnalysisResult] = field(default_factory=list)
    improvement_plan: Optional[ImprovementPlan] = None
    generated_patches: List[GeneratedPatch] = field(default_factory=list)
    safety_assessments: List[SafetyAssessment] = field(default_factory=list)
    test_results: List[TestResult] = field(default_factory=list)
    applied_patches: List[PatchResult] = field(default_factory=list)
    rolled_back: bool = False
    error: Optional[str] = None
    completed_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "cycle_id": self.cycle_id,
            "started_at": self.started_at.isoformat(),
            "phase": self.phase.value,
            "analysis_count": len(self.analysis_results),
            "plan_id": self.improvement_plan.plan_id if self.improvement_plan else None,
            "patches_generated": len(self.generated_patches),
            "patches_applied": len([p for p in self.applied_patches if p.success]),
            "rolled_back": self.rolled_back,
            "error": self.error,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
        }


class SelfModificationLoop:
    """
    Orchestrates the complete self-modification cycle.
    
    Flow:
    1. ANALYZING - SelfDevelopment analyzes codebase components
    2. PLANNING - Generate improvement plan from analysis
    3. GENERATING_PATCHES - PatchGenerator creates code patches
    4. SAFETY_CHECK - SelfPatchSafetyGate validates patches
    5. SANDBOX_TESTING - Apply patches in isolated sandbox, run tests
    6. DEPLOYING - Apply patches to main repo (if approved)
    7. VALIDATING - Run full test suite on modified code
    8. COMPLETED/FAILED - Record results, rollback if needed
    """
    
    def __init__(self, config: ModificationConfig):
        self.config = config
        self.repo_path = Path(config.repo_path)
        
        # Components
        self.self_dev = SelfDevelopment(
            repo_path=str(self.repo_path),
            max_safety_level=config.max_safety_level,
        )
        self.patch_generator = PatchGenerator(str(self.repo_path))
        self.patch_applier = PatchApplier(str(self.repo_path))
        self.test_runner = TestRunner(
            repo_path=str(self.repo_path),
            test_command=config.test_command,
            timeout=config.test_timeout,
        )
        self.rollback_manager = RollbackManager(
            repo_path=str(self.repo_path),
            max_backups=config.keep_backups,
        )
        self.safety_gate = SelfPatchSafetyGate()
        
        # State
        self._current_cycle: Optional[ModificationCycle] = None
        self._cycle_history: List[ModificationCycle] = []
        self._running = False
        self._task: Optional[asyncio.Task] = None
        
        # Statistics
        self._cycles_completed = 0
        self._cycles_failed = 0
        self._patches_applied = 0
        self._rollbacks_performed = 0
    
    async def initialize(self) -> None:
        """Initialize all components."""
        await self.self_dev.initialize()
        await self.patch_applier.initialize()
        await self.test_runner.initialize()
        await self.rollback_manager.initialize()
        await self.safety_gate.initialize()
        logger.info("SelfModificationLoop initialized")
    
    async def run_cycle(self, components: Optional[List[str]] = None) -> ModificationCycle:
        """
        Run a single self-modification cycle.
        
        Args:
            components: Specific components to analyze (None = all)
            
        Returns:
            Completed modification cycle
        """
        cycle_id = f"cycle_{datetime.utcnow().timestamp()}"
        cycle = ModificationCycle(
            cycle_id=cycle_id,
            started_at=datetime.utcnow(),
        )
        self._current_cycle = cycle
        
        try:
            logger.info(f"Starting self-modification cycle {cycle_id}")
            
            # Phase 1: ANALYZING
            cycle.phase = ModificationPhase.ANALYZING
            logger.info("Phase 1: Analyzing codebase")
            cycle.analysis_results = await self._analyze_codebase(components)
            
            # Phase 2: PLANNING
            cycle.phase = ModificationPhase.PLANNING
            logger.info("Phase 2: Generating improvement plan")
            cycle.improvement_plan = await self._generate_plan(cycle.analysis_results)
            
            if not cycle.improvement_plan.changes:
                logger.info("No improvements needed")
                cycle.phase = ModificationPhase.COMPLETED
                cycle.completed_at = datetime.utcnow()
                self._cycle_history.append(cycle)
                self._cycles_completed += 1
                return cycle
            
            # Phase 3: GENERATING_PATCHES
            cycle.phase = ModificationPhase.GENERATING_PATCHES
            logger.info("Phase 3: Generating code patches")
            cycle.generated_patches = await self._generate_patches(cycle.improvement_plan)
            
            if not cycle.generated_patches:
                logger.warning("No patches generated")
                cycle.phase = ModificationPhase.COMPLETED
                cycle.completed_at = datetime.utcnow()
                self._cycle_history.append(cycle)
                self._cycles_completed += 1
                return cycle
            
            # Phase 4: SAFETY_CHECK
            cycle.phase = ModificationPhase.SAFETY_CHECK
            logger.info("Phase 4: Safety validation")
            cycle.safety_assessments = await self._safety_check(cycle.generated_patches)
            
            safe_patches = [
                p for p, a in zip(cycle.generated_patches, cycle.safety_assessments)
                if a.is_safe
            ]
            
            if not safe_patches:
                logger.warning("No patches passed safety check")
                cycle.phase = ModificationPhase.COMPLETED
                cycle.completed_at = datetime.utcnow()
                self._cycle_history.append(cycle)
                self._cycles_completed += 1
                return cycle
            
            # Phase 5: SANDBOX_TESTING
            if self.config.require_sandbox_pass:
                cycle.phase = ModificationPhase.SANDBOX_TESTING
                logger.info("Phase 5: Sandbox testing")
                cycle.test_results = await self._sandbox_test(safe_patches)
                
                passed_patches = [
                    p for p, r in zip(safe_patches, cycle.test_results)
                    if r.passed
                ]
                
                if not passed_patches:
                    logger.warning("No patches passed sandbox tests")
                    cycle.phase = ModificationPhase.COMPLETED
                    cycle.completed_at = datetime.utcnow()
                    self._cycle_history.append(cycle)
                    self._cycles_completed += 1
                    return cycle
            else:
                passed_patches = safe_patches
            
            # Phase 6: DEPLOYING (requires approval)
            if self.config.require_approval:
                logger.info("Phase 6: Awaiting approval for deployment")
                # In production, this would wait for human approval
                # For now, we skip deployment if approval required
                cycle.phase = ModificationPhase.COMPLETED
                cycle.completed_at = datetime.utcnow()
                self._cycle_history.append(cycle)
                self._cycles_completed += 1
                return cycle
            
            cycle.phase = ModificationPhase.DEPLOYING
            logger.info("Phase 6: Deploying patches")
            cycle.applied_patches = await self._deploy_patches(passed_patches)
            
            # Phase 7: VALIDATING
            if self.config.require_tests_pass:
                cycle.phase = ModificationPhase.VALIDATING
                logger.info("Phase 7: Validating deployment")
                validation_results = await self.test_runner.run_all()
                
                all_passed = all(r.passed for r in validation_results)
                
                if not all_passed and self.config.auto_rollback_on_failure:
                    logger.warning("Validation failed, rolling back")
                    cycle.phase = ModificationPhase.ROLLING_BACK
                    await self._rollback(cycle)
                    cycle.rolled_back = True
                    cycle.phase = ModificationPhase.FAILED
                    cycle.error = "Validation failed after deployment"
                elif not all_passed:
                    cycle.phase = ModificationPhase.FAILED
                    cycle.error = "Validation failed after deployment"
                else:
                    cycle.phase = ModificationPhase.COMPLETED
            else:
                cycle.phase = ModificationPhase.COMPLETED
            
            cycle.completed_at = datetime.utcnow()
            self._cycles_completed += 1
            self._patches_applied += len([p for p in cycle.applied_patches if p.success])
            
        except Exception as e:
            logger.error(f"Cycle {cycle_id} failed: {e}")
            cycle.phase = ModificationPhase.FAILED
            cycle.error = str(e)
            cycle.completed_at = datetime.utcnow()
            self._cycles_failed += 1
            
            # Attempt rollback on failure
            if self.config.auto_rollback_on_failure and self._current_cycle:
                try:
                    await self._rollback(self._current_cycle)
                    self._current_cycle.rolled_back = True
                    self._rollbacks_performed += 1
                except Exception as rb_e:
                    logger.error(f"Rollback failed: {rb_e}")
        
        finally:
            self._cycle_history.append(cycle)
            self._current_cycle = None
        
        return cycle
    
    async def _analyze_codebase(self, components: Optional[List[str]]) -> List[AnalysisResult]:
        """Analyze codebase components."""
        if components:
            results = []
            for comp in components[:self.config.max_changes_per_cycle]:
                result = await self.self_dev.analyze_component(comp)
                results.append(result)
            return results
        else:
            return await self.self_dev.analyze_entire_codebase()
    
    async def _generate_plan(self, analyses: List[AnalysisResult]) -> ImprovementPlan:
        """Generate improvement plan from analyses."""
        return await self.self_dev.generate_improvement_plan(
            analyses,
            safety_level=self.config.max_safety_level,
        )
    
    async def _generate_patches(self, plan: ImprovementPlan) -> List[GeneratedPatch]:
        """Generate code patches from improvement plan."""
        patches = []
        
        for change in plan.changes[:self.config.max_changes_per_cycle]:
            try:
                # Create a mock execution plan step for the patch generator
                from src.coding.planner import ExecutionPlan, ExecutionStep, StepType
                
                step = ExecutionStep(
                    step_id=change["change_id"],
                    step_type=StepType.GENERATE,
                    description=change["description"],
                    file_path=change.get("file_path"),
                    parameters={"focus": "improvement"},
                )
                
                mock_plan = ExecutionPlan(
                    task_id=plan.plan_id,
                    task_type="self_improvement",
                    goal=plan.title,
                    steps=[step],
                    context={"repository_structure": await self._get_repo_structure()},
                )
                
                patch = await self.patch_generator.generate_patch(mock_plan)
                if patch.file_changes:
                    patches.append(patch)
                    
            except Exception as e:
                logger.error(f"Failed to generate patch for {change['change_id']}: {e}")
        
        return patches
    
    async def _get_repo_structure(self) -> str:
        """Get repository structure for context."""
        try:
            result = subprocess.run(
                ["find", ".", "-type", "f", "-name", "*.py", "|", "head", "-50"],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                shell=True,
            )
            return result.stdout[:2000] if result.stdout else "Unknown"
        except Exception:
            return "Unknown"
    
    async def _safety_check(self, patches: List[GeneratedPatch]) -> List[SafetyAssessment]:
        """Run safety gate on patches."""
        assessments = []
        
        for patch in patches:
            try:
                assessment = await self.safety_gate.assess_patch(patch)
                assessments.append(assessment)
            except Exception as e:
                logger.error(f"Safety check failed for patch: {e}")
                # Create failed assessment
                from src.safety.self_patch_safety_gate import SafetyAssessment
                assessments.append(SafetyAssessment(
                    patch_id=patch.metadata.get("task_type", "unknown"),
                    is_safe=False,
                    risk_level="critical",
                    findings=[f"Safety check error: {e}"],
                    blockers=[str(e)],
                ))
        
        return assessments
    
    async def _sandbox_test(self, patches: List[GeneratedPatch]) -> List[TestResult]:
        """Test patches in sandbox environment."""
        results = []
        
        for patch in patches:
            try:
                # Create sandbox copy
                sandbox_path = await self.patch_applier.create_sandbox()
                
                # Apply patch to sandbox
                apply_result = await self.patch_applier.apply_patch(
                    sandbox_path,
                    patch,
                )
                
                if not apply_result.success:
                    results.append(TestResult(
                        test_name=f"sandbox_apply_{patch.metadata.get('task_type', 'patch')}",
                        passed=False,
                        error=f"Failed to apply patch: {apply_result.error}",
                    ))
                    continue
                
                # Run tests in sandbox
                test_result = await self.test_runner.run_in_sandbox(
                    sandbox_path,
                    self.config.sandbox_test_command or self.config.test_command,
                )
                results.append(test_result)
                
                # Cleanup sandbox
                await self.patch_applier.cleanup_sandbox(sandbox_path)
                
            except Exception as e:
                logger.error(f"Sandbox test failed: {e}")
                results.append(TestResult(
                    test_name="sandbox_test",
                    passed=False,
                    error=str(e),
                ))
        
        return results
    
    async def _deploy_patches(self, patches: List[GeneratedPatch]) -> List[PatchResult]:
        """Deploy patches to main repository."""
        results = []
        
        # Create backup before deployment
        backup_id = await self.rollback_manager.create_backup("pre_deployment")
        logger.info(f"Created backup {backup_id}")
        
        for patch in patches:
            try:
                result = await self.patch_applier.apply_patch(
                    self.repo_path,
                    patch,
                )
                results.append(result)
                
                if result.success:
                    logger.info(f"Applied patch {patch.metadata.get('task_type', 'unknown')}")
                else:
                    logger.error(f"Failed to apply patch: {result.error}")
                    
            except Exception as e:
                logger.error(f"Deployment error: {e}")
                results.append(PatchResult(
                    patch_id=patch.metadata.get("task_type", "unknown"),
                    success=False,
                    error=str(e),
                ))
        
        return results
    
    async def _rollback(self, cycle: ModificationCycle) -> None:
        """Rollback changes from a cycle."""
        if cycle.applied_patches:
            await self.rollback_manager.rollback_to_backup("pre_deployment")
        logger.info(f"Rolled back cycle {cycle.cycle_id}")
    
    async def start_continuous(self) -> None:
        """Start continuous self-modification loop."""
        self._running = True
        self._task = asyncio.create_task(self._continuous_loop())
        logger.info("Self-modification loop started")
    
    async def stop(self) -> None:
        """Stop the continuous loop."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Self-modification loop stopped")
    
    async def _continuous_loop(self) -> None:
        """Continuous loop for self-modification."""
        while self._running:
            try:
                await self.run_cycle()
            except Exception as e:
                logger.error(f"Cycle error: {e}")
            
            # Wait for next cycle
            await asyncio.sleep(self.config.cycle_interval_hours * 3600)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current loop status."""
        return {
            "running": self._running,
            "current_cycle": self._current_cycle.to_dict() if self._current_cycle else None,
            "cycles_completed": self._cycles_completed,
            "cycles_failed": self._cycles_failed,
            "patches_applied": self._patches_applied,
            "rollbacks_performed": self._rollbacks_performed,
            "history_size": len(self._cycle_history),
        }
    
    def get_cycle_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent cycle history."""
        return [c.to_dict() for c in self._cycle_history[-limit:]]