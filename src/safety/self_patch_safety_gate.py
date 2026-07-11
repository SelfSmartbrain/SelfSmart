"""Self-patch safety gate with sandbox testing and CI integration.

Phase 16D: Self-Patch Safety Gate

Implements safety checks before applying self-generated patches:
- Sandbox isolation for patch testing
- Test suite execution before application
- CI integration checks
- Automatic rollback on failure
- Blast-radius limits
- Human approval for critical paths
"""

from __future__ import annotations

import asyncio
import subprocess
import shutil
from pathlib import Path
from typing import Any, Optional, Dict, List, Set
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from src.config.logging import get_logger
from src.sandbox.sandbox_manager import SandboxManager
from src.coding.code_editor import CodeEditor, FileChange, EditResult

logger = get_logger(__name__)


class PatchSafetyLevel(str, Enum):
    """Safety levels for patches based on what they modify."""
    
    SAFE = "safe"  # Non-critical files, small changes
    MODERATE = "moderate"  # Some critical files, medium changes
    CRITICAL = "critical"  # Core system files, orchestrator, auth, safety code
    FORBIDDEN = "forbidden"  # Modifying the safety gate itself


class TestResult(str, Enum):
    """Results of test execution."""
    
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    ERROR = "error"


@dataclass
class PatchSafetyCheck:
    """Result of a safety check on a patch."""
    
    safety_level: PatchSafetyLevel
    requires_human_approval: bool
    blast_radius_score: float  # 0.0 (minimal) to 1.0 (maximal)
    critical_files_touched: List[str]
    forbidden_files_touched: List[str]
    diff_size: int
    estimated_risk: str  # "low", "medium", "high", "critical"
    can_apply: bool
    rejection_reason: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "safety_level": self.safety_level.value,
            "requires_human_approval": self.requires_human_approval,
            "blast_radius_score": self.blast_radius_score,
            "critical_files_touched": self.critical_files_touched,
            "forbidden_files_touched": self.forbidden_files_touched,
            "diff_size": self.diff_size,
            "estimated_risk": self.estimated_risk,
            "can_apply": self.can_apply,
            "rejection_reason": self.rejection_reason,
        }


@dataclass
class PatchTestResult:
    """Result of testing a patch in sandbox."""
    
    test_result: TestResult
    tests_run: int
    tests_passed: int
    tests_failed: int
    test_output: str
    execution_time_seconds: float
    sandbox_path: str
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "test_result": self.test_result.value,
            "tests_run": self.tests_run,
            "tests_passed": self.tests_passed,
            "tests_failed": self.tests_failed,
            "test_output": self.test_output,
            "execution_time_seconds": self.execution_time_seconds,
            "sandbox_path": self.sandbox_path,
        }


@dataclass
class PatchApplicationResult:
    """Result of applying a patch with safety checks."""
    
    success: bool
    safety_check: PatchSafetyCheck
    test_result: Optional[PatchTestResult]
    edit_results: List[EditResult]
    rollback_performed: bool
    human_approval_obtained: bool
    rejection_reason: Optional[str] = None
    applied_at: Optional[datetime] = None
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "success": self.success,
            "safety_check": self.safety_check.to_dict(),
            "test_result": self.test_result.to_dict() if self.test_result else None,
            "edit_results": [er.to_dict() for er in self.edit_results],
            "rollback_performed": self.rollback_performed,
            "human_approval_obtained": self.human_approval_obtained,
            "rejection_reason": self.rejection_reason,
            "applied_at": self.applied_at.isoformat() if self.applied_at else None,
        }


class SelfPatchSafetyGate:
    """Safety gate for self-patching with sandbox testing and CI integration."""
    
    # Files that are considered critical and require human approval
    CRITICAL_PATHS = [
        "src/runtime/",
        "src/autonomy/",
        "src/agents/",
        "src/agents/orchestrator.py",
        "src/api/auth.py",
        "src/api/dependencies.py",
        "src/api/middleware.py",
        "src/safety/",
        "src/governance/",
    ]
    
    # Files that are forbidden to modify (the safety gate itself)
    FORBIDDEN_PATHS = [
        "src/safety/self_patch_safety_gate.py",
        "src/safety/safety_hypervisor.py",  # if it exists
    ]
    
    # Maximum diff size (in characters) for auto-approval
    MAX_AUTO_APPROVE_DIFF_SIZE = 5000
    
    def __init__(
        self,
        repository_path: str,
        require_human_for_critical: bool = True,
        require_ci_pass: bool = True,
        max_blast_radius: float = 0.3,
    ):
        self.repository_path = Path(repository_path)
        self.require_human_for_critical = require_human_for_critical
        self.require_ci_pass = require_ci_pass
        self.max_blast_radius = max_blast_radius
        
        self.sandbox_manager = SandboxManager()
        self.code_editor = CodeEditor(repository_path)
        
        self.patch_history: List[Dict[str, Any]] = []
        self.rejected_patches: List[Dict[str, Any]] = []
        
        logger.info("SelfPatchSafetyGate initialized")
    
    def _is_critical_path(self, file_path: str) -> bool:
        """Check if a file path is in a critical directory."""
        file_path = file_path.replace("\\", "/")
        for critical_path in self.CRITICAL_PATHS:
            if file_path.startswith(critical_path):
                return True
        return False
    
    def _is_forbidden_path(self, file_path: str) -> bool:
        """Check if a file path is forbidden to modify."""
        file_path = file_path.replace("\\", "/")
        for forbidden_path in self.FORBIDDEN_PATHS:
            if file_path == forbidden_path or file_path.endswith(forbidden_path):
                return True
        return False
    
    def _calculate_blast_radius(self, file_changes: List[FileChange]) -> float:
        """Calculate blast radius score based on number and type of files changed."""
        if not file_changes:
            return 0.0
        
        score = 0.0
        for change in file_changes:
            file_path = change.file_path
            
            # Base score per file
            score += 0.1
            
            # Critical files add more
            if self._is_critical_path(file_path):
                score += 0.3
            
            # Forbidden files add maximum
            if self._is_forbidden_path(file_path):
                score += 1.0
        
        # Normalize to 0-1 range
        return min(score / len(file_changes) if file_changes else 0.0, 1.0)
    
    def _calculate_diff_size(self, file_changes: List[FileChange]) -> int:
        """Calculate total diff size in characters."""
        total_size = 0
        for change in file_changes:
            if change.new_content:
                total_size += len(change.new_content)
            if change.old_content:
                total_size += len(change.old_content)
        return total_size
    
    def perform_safety_check(self, file_changes: List[FileChange]) -> PatchSafetyCheck:
        """Perform safety check on a patch before testing."""
        
        critical_files = []
        forbidden_files = []
        
        for change in file_changes:
            if self._is_forbidden_path(change.file_path):
                forbidden_files.append(change.file_path)
            elif self._is_critical_path(change.file_path):
                critical_files.append(change.file_path)
        
        # Determine safety level
        if forbidden_files:
            safety_level = PatchSafetyLevel.FORBIDDEN
            can_apply = False
            rejection_reason = "Patch attempts to modify forbidden files"
        elif critical_files:
            safety_level = PatchSafetyLevel.CRITICAL
            can_apply = not self.require_human_for_critical
            rejection_reason = None if can_apply else "Critical files require human approval"
        else:
            diff_size = self._calculate_diff_size(file_changes)
            if diff_size > self.MAX_AUTO_APPROVE_DIFF_SIZE:
                safety_level = PatchSafetyLevel.MODERATE
                can_apply = not self.require_human_for_critical
                rejection_reason = None if can_apply else "Large diff requires human approval"
            else:
                safety_level = PatchSafetyLevel.SAFE
                can_apply = True
                rejection_reason = None
        
        # Calculate blast radius
        blast_radius = self._calculate_blast_radius(file_changes)
        
        # Determine estimated risk
        if blast_radius > 0.7 or forbidden_files:
            estimated_risk = "critical"
        elif blast_radius > 0.5 or critical_files:
            estimated_risk = "high"
        elif blast_radius > 0.3:
            estimated_risk = "medium"
        else:
            estimated_risk = "low"
        
        # Check against max blast radius
        if blast_radius > self.max_blast_radius:
            can_apply = False
            if not rejection_reason:
                rejection_reason = f"Blast radius {blast_radius:.2f} exceeds maximum {self.max_blast_radius}"
        
        return PatchSafetyCheck(
            safety_level=safety_level,
            requires_human_approval=safety_level in [PatchSafetyLevel.CRITICAL, PatchSafetyLevel.MODERATE],
            blast_radius_score=blast_radius,
            critical_files_touched=critical_files,
            forbidden_files_touched=forbidden_files,
            diff_size=self._calculate_diff_size(file_changes),
            estimated_risk=estimated_risk,
            can_apply=can_apply,
            rejection_reason=rejection_reason,
        )
    
    async def test_patch_in_sandbox(
        self,
        file_changes: List[FileChange],
        test_command: Optional[List[str]] = None,
    ) -> PatchTestResult:
        """Test a patch in an isolated sandbox environment."""
        
        logger.info("Creating sandbox for patch testing")
        sandbox_path = await self.sandbox_manager.create_sandbox()
        
        start_time = datetime.utcnow()
        
        try:
            # Copy repository to sandbox
            sandbox_repo = Path(sandbox_path) / "repo"
            shutil.copytree(self.repository_path, sandbox_repo)
            
            # Apply patch in sandbox
            sandbox_editor = CodeEditor(str(sandbox_repo))
            
            for change in file_changes:
                result = sandbox_editor.apply_patch(change)
                if not result.success:
                    return PatchTestResult(
                        test_result=TestResult.FAILED,
                        tests_run=0,
                        tests_passed=0,
                        tests_failed=0,
                        test_output=f"Failed to apply patch: {result.error}",
                        execution_time_seconds=0.0,
                        sandbox_path=sandbox_path,
                    )
            
            # Run tests if command provided
            if test_command:
                logger.info(f"Running tests in sandbox: {' '.join(test_command)}")
                
                try:
                    process = await asyncio.create_subprocess_exec(
                        *test_command,
                        cwd=str(sandbox_repo),
                        stdout=asyncio.subprocess.PIPE,
                        stderr=asyncio.subprocess.PIPE,
                    )
                    
                    stdout, stderr = await asyncio.wait_for(
                        process.communicate(),
                        timeout=300.0,  # 5 minute timeout
                    )
                    
                    test_output = stdout.decode() + "\n" + stderr.decode()
                    
                    # Parse test results (simplified - assumes pytest output)
                    tests_run = test_output.count("PASSED") + test_output.count("FAILED")
                    tests_passed = test_output.count("PASSED")
                    tests_failed = test_output.count("FAILED")
                    
                    if process.returncode == 0:
                        test_result = TestResult.PASSED
                    else:
                        test_result = TestResult.FAILED
                
                except asyncio.TimeoutError:
                    test_result = TestResult.ERROR
                    test_output = "Test execution timed out"
                    tests_run = 0
                    tests_passed = 0
                    tests_failed = 0
                
                except Exception as exc:
                    test_result = TestResult.ERROR
                    test_output = f"Test execution error: {exc}"
                    tests_run = 0
                    tests_passed = 0
                    tests_failed = 0
            else:
                # No tests configured, skip
                test_result = TestResult.SKIPPED
                test_output = "No test command provided, skipping tests"
                tests_run = 0
                tests_passed = 0
                tests_failed = 0
        
        except Exception as exc:
            logger.error(f"Sandbox testing failed: {exc}")
            return PatchTestResult(
                test_result=TestResult.ERROR,
                tests_run=0,
                tests_passed=0,
                tests_failed=0,
                test_output=f"Sandbox error: {exc}",
                execution_time_seconds=0.0,
                sandbox_path=sandbox_path,
            )
        
        finally:
            # Cleanup sandbox
            await self.sandbox_manager.teardown_sandbox()
        
        execution_time = (datetime.utcnow() - start_time).total_seconds()
        
        return PatchTestResult(
            test_result=test_result,
            tests_run=tests_run,
            tests_passed=tests_passed,
            tests_failed=tests_failed,
            test_output=test_output,
            execution_time_seconds=execution_time,
            sandbox_path=sandbox_path,
        )
    
    async def apply_patch_with_safety(
        self,
        file_changes: List[FileChange],
        human_approval: bool = False,
        test_command: Optional[List[str]] = None,
        skip_tests: bool = False,
    ) -> PatchApplicationResult:
        """Apply a patch with full safety checks."""
        
        logger.info(f"Applying patch with safety checks: {len(file_changes)} file changes")
        
        # Step 1: Safety check
        safety_check = self.perform_safety_check(file_changes)
        
        if not safety_check.can_apply:
            logger.warning(f"Patch rejected by safety check: {safety_check.rejection_reason}")
            self.rejected_patches.append({
                "timestamp": datetime.utcnow().isoformat(),
                "safety_check": safety_check.to_dict(),
                "file_changes": [fc.__dict__ for fc in file_changes],
            })
            
            return PatchApplicationResult(
                success=False,
                safety_check=safety_check,
                test_result=None,
                edit_results=[],
                rollback_performed=False,
                human_approval_obtained=False,
                rejection_reason=safety_check.rejection_reason,
            )
        
        # Step 2: Check human approval requirement
        if safety_check.requires_human_approval and not human_approval:
            logger.warning("Patch requires human approval but not provided")
            return PatchApplicationResult(
                success=False,
                safety_check=safety_check,
                test_result=None,
                edit_results=[],
                rollback_performed=False,
                human_approval_obtained=False,
                rejection_reason="Human approval required but not provided",
            )
        
        # Step 3: Test in sandbox (unless skipped)
        test_result = None
        if not skip_tests and self.require_ci_pass:
            test_result = await self.test_patch_in_sandbox(file_changes, test_command)
            
            if test_result.test_result == TestResult.FAILED:
                logger.error("Patch failed sandbox tests, rejecting")
                return PatchApplicationResult(
                    success=False,
                    safety_check=safety_check,
                    test_result=test_result,
                    edit_results=[],
                    rollback_performed=False,
                    human_approval_obtained=human_approval,
                    rejection_reason="Patch failed sandbox tests",
                )
            
            if test_result.test_result == TestResult.ERROR:
                logger.error("Patch testing encountered error, rejecting")
                return PatchApplicationResult(
                    success=False,
                    safety_check=safety_check,
                    test_result=test_result,
                    edit_results=[],
                    rollback_performed=False,
                    human_approval_obtained=human_approval,
                    rejection_reason="Patch testing encountered error",
                )
        
        # Step 4: Apply patch with rollback capability
        edit_results = []
        rollback_data = []
        
        try:
            # Store original content for rollback
            for change in file_changes:
                original = self.code_editor.read_file(change.file_path)
                if original.success:
                    rollback_data.append({
                        "file_path": change.file_path,
                        "original_content": original.before,
                    })
            
            # Apply changes
            for change in file_changes:
                result = self.code_editor.apply_patch(change)
                edit_results.append(result)
                
                if not result.success:
                    logger.error(f"Failed to apply patch to {change.file_path}: {result.error}")
                    
                    # Rollback
                    for rollback_item in rollback_data:
                        self.code_editor.write_file(
                            rollback_item["file_path"],
                            rollback_item["original_content"],
                        )
                    
                    return PatchApplicationResult(
                        success=False,
                        safety_check=safety_check,
                        test_result=test_result,
                        edit_results=edit_results,
                        rollback_performed=True,
                        human_approval_obtained=human_approval,
                        rejection_reason=f"Failed to apply patch: {result.error}",
                    )
            
            # Success
            logger.info("Patch applied successfully")
            
            result = PatchApplicationResult(
                success=True,
                safety_check=safety_check,
                test_result=test_result,
                edit_results=edit_results,
                rollback_performed=False,
                human_approval_obtained=human_approval,
                applied_at=datetime.utcnow(),
            )
            
            self.patch_history.append(result.to_dict())
            
            return result
        
        except Exception as exc:
            logger.error(f"Patch application failed with exception: {exc}")
            
            # Attempt rollback
            for rollback_item in rollback_data:
                try:
                    self.code_editor.write_file(
                        rollback_item["file_path"],
                        rollback_item["original_content"],
                    )
                except Exception as rollback_exc:
                    logger.error(f"Rollback failed for {rollback_item['file_path']}: {rollback_exc}")
            
            return PatchApplicationResult(
                success=False,
                safety_check=safety_check,
                test_result=test_result,
                edit_results=edit_results,
                rollback_performed=True,
                human_approval_obtained=human_approval,
                rejection_reason=f"Exception during patch application: {exc}",
            )
    
    def get_patch_statistics(self) -> Dict[str, Any]:
        """Get statistics about patches applied and rejected."""
        return {
            "total_patches_applied": len(self.patch_history),
            "total_patches_rejected": len(self.rejected_patches),
            "rejection_rate": len(self.rejected_patches) / (len(self.patch_history) + len(self.rejected_patches))
            if (len(self.patch_history) + len(self.rejected_patches)) > 0 else 0.0,
            "recent_rejections": self.rejected_patches[-10:] if self.rejected_patches else [],
        }
