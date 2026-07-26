"""
Rollback Manager - Manages automated rollback of failed patches.

Provides intelligent rollback capabilities including:
- Automatic rollback on test failure
- Selective rollback of specific changes
- Rollback verification
- Rollback history and audit trail
"""

import asyncio
import logging
import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


@dataclass
class RollbackRecord:
    """Record of a rollback operation."""
    rollback_id: str
    triggered_at: datetime
    reason: str
    patches_rolled_back: List[str]
    success: bool
    error: Optional[str] = None
    restored_from_backup: Optional[str] = None


@dataclass
class DeploymentRecord:
    """Record of a deployment for rollback reference."""
    deployment_id: str
    deployed_at: datetime
    patches: List[Dict[str, Any]]
    backup_id: str
    test_results: Dict[str, Any]
    status: str  # "success", "failed", "rolled_back"


class RollbackManager:
    """
    Manages rollback operations for self-modification deployments.
    
    Features:
    - Creates deployment records for rollback reference
    - Automatic rollback on validation failure
    - Selective rollback of individual patches
    - Rollback verification
    - Audit trail
    """
    
    def __init__(
        self,
        repo_path: str,
        backup_dir: Optional[str] = None,
        max_backups: int = 10,
    ):
        self.repo_path = Path(repo_path).resolve()
        self.backup_dir = Path(backup_dir) if backup_dir else self.repo_path / ".patch_backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_backups = max_backups
        
        # Records
        self._deployment_history: List[DeploymentRecord] = []
        self._rollback_history: List[RollbackRecord] = []
        
        # State
        self._last_deployment: Optional[DeploymentRecord] = None
    
    async def initialize(self) -> None:
        """Initialize rollback manager."""
        # Load history from disk if exists
        await self._load_history()
        logger.info("RollbackManager initialized")
    
    async def _load_history(self) -> None:
        """Load deployment and rollback history from disk."""
        history_file = self.backup_dir / "rollback_history.json"
        if history_file.exists():
            try:
                content = history_file.read_text()
                data = json.loads(content)
                
                for dep in data.get("deployments", []):
                    dep["deployed_at"] = datetime.fromisoformat(dep["deployed_at"])
                    self._deployment_history.append(DeploymentRecord(**dep))
                
                for rb in data.get("rollbacks", []):
                    rb["triggered_at"] = datetime.fromisoformat(rb["triggered_at"])
                    self._rollback_history.append(RollbackRecord(**rb))
                    
                logger.info(f"Loaded {len(self._deployment_history)} deployments, "
                           f"{len(self._rollback_history)} rollbacks from history")
            except Exception as e:
                logger.warning(f"Failed to load rollback history: {e}")
    
    async def _save_history(self) -> None:
        """Save deployment and rollback history to disk."""
        history_file = self.backup_dir / "rollback_history.json"
        
        data = {
            "deployments": [
                {
                    **dep.__dict__,
                    "deployed_at": dep.deployed_at.isoformat(),
                }
                for dep in self._deployment_history
            ],
            "rollbacks": [
                {
                    **rb.__dict__,
                    "triggered_at": rb.triggered_at.isoformat(),
                }
                for rb in self._rollback_history
            ],
        }
        
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                history_file.write_text,
                json.dumps(data, indent=2),
            )
        except Exception as e:
            logger.error(f"Failed to save rollback history: {e}")
    
    async def record_deployment(
        self,
        patches: List[Dict[str, Any]],
        backup_id: str,
        test_results: Dict[str, Any],
        status: str = "success",
    ) -> str:
        """
        Record a successful deployment for potential rollback.
        
        Args:
            patches: List of applied patches with metadata
            backup_id: Backup ID created before deployment
            test_results: Test results after deployment
            status: Deployment status
            
        Returns:
            Deployment ID
        """
        deployment_id = f"deploy_{datetime.utcnow().timestamp()}"
        
        record = DeploymentRecord(
            deployment_id=deployment_id,
            deployed_at=datetime.utcnow(),
            patches=patches,
            backup_id=backup_id,
            test_results=test_results,
            status=status,
        )
        
        self._deployment_history.append(record)
        self._last_deployment = record
        
        # Cleanup old backups
        await self._cleanup_old_backups()
        
        await self._save_history()
        
        logger.info(f"Recorded deployment: {deployment_id}")
        return deployment_id
    
    async def _cleanup_old_backups(self) -> None:
        """Remove backups beyond max_backups limit."""
        backups = sorted(
            self.backup_dir.iterdir(),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )
        
        for backup in backups[self.max_backups:]:
            if backup.is_dir() and backup.name != "rollback_history.json":
                try:
                    import shutil
                    await asyncio.get_event_loop().run_in_executor(
                        None,
                        shutil.rmtree,
                        backup,
                    )
                except Exception as e:
                    logger.error(f"Failed to remove old backup {backup}: {e}")
    
    async def rollback_last_deployment(
        self,
        reason: str = "Automatic rollback",
    ) -> RollbackRecord:
        """
        Rollback the last successful deployment.
        
        Args:
            reason: Reason for rollback
            
        Returns:
            RollbackRecord with operation details
        """
        if not self._last_deployment:
            return RollbackRecord(
                rollback_id=f"rollback_{datetime.utcnow().timestamp()}",
                triggered_at=datetime.utcnow(),
                reason=reason,
                patches_rolled_back=[],
                success=False,
                error="No deployment to rollback",
            )
        
        return await self.rollback_deployment(
            self._last_deployment.deployment_id,
            reason,
        )
    
    async def rollback_deployment(
        self,
        deployment_id: str,
        reason: str = "Manual rollback",
    ) -> RollbackRecord:
        """
        Rollback a specific deployment.
        
        Args:
            deployment_id: ID of deployment to rollback
            reason: Reason for rollback
            
        Returns:
            RollbackRecord with operation details
        """
        rollback_id = f"rollback_{datetime.utcnow().timestamp()}"
        
        # Find deployment
        deployment = next(
            (d for d in self._deployment_history if d.deployment_id == deployment_id),
            None,
        )
        
        if not deployment:
            return RollbackRecord(
                rollback_id=rollback_id,
                triggered_at=datetime.utcnow(),
                reason=reason,
                patches_rolled_back=[],
                success=False,
                error=f"Deployment not found: {deployment_id}",
            )
        
        if deployment.status == "rolled_back":
            return RollbackRecord(
                rollback_id=rollback_id,
                triggered_at=datetime.utcnow(),
                reason=reason,
                patches_rolled_back=[],
                success=False,
                error="Deployment already rolled back",
            )
        
        patches_rolled_back = []
        success = False
        error = None
        
        try:
            # Restore from backup
            backup_path = self.backup_dir / deployment.backup_id
            
            if backup_path.exists():
                # Remove current repo and restore
                import shutil
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    shutil.rmtree,
                    self.repo_path,
                )
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    shutil.copytree,
                    backup_path,
                    self.repo_path,
                )
                
                patches_rolled_back = [p.get("patch_id", "unknown") for p in deployment.patches]
                success = True
                logger.info(f"Rolled back deployment {deployment_id} from backup {deployment.backup_id}")
            else:
                error = f"Backup not found: {deployment.backup_id}"
                logger.error(error)
            
        except Exception as e:
            error = str(e)
            logger.error(f"Rollback failed: {e}")
        
        # Record rollback
        record = RollbackRecord(
            rollback_id=rollback_id,
            triggered_at=datetime.utcnow(),
            reason=reason,
            patches_rolled_back=patches_rolled_back,
            success=success,
            error=error,
            restored_from_backup=deployment.backup_id if success else None,
        )
        
        self._rollback_history.append(record)
        
        # Update deployment status
        deployment.status = "rolled_back"
        
        await self._save_history()
        
        return record
    
    async def rollback_specific_patches(
        self,
        patch_ids: List[str],
        reason: str = "Selective rollback",
    ) -> RollbackRecord:
        """
        Rollback specific patches from the last deployment.
        
        Note: This requires git to revert specific commits.
        
        Args:
            patch_ids: List of patch IDs to rollback
            reason: Reason for rollback
            
        Returns:
            RollbackRecord with operation details
        """
        rollback_id = f"rollback_{datetime.utcnow().timestamp()}"
        
        if not self._last_deployment:
            return RollbackRecord(
                rollback_id=rollback_id,
                triggered_at=datetime.utcnow(),
                reason=reason,
                patches_rolled_back=[],
                success=False,
                error="No deployment to rollback from",
            )
        
        # Find matching patches
        matching_patches = [
            p for p in self._last_deployment.patches
            if p.get("patch_id") in patch_ids
        ]
        
        if not matching_patches:
            return RollbackRecord(
                rollback_id=rollback_id,
                triggered_at=datetime.utcnow(),
                reason=reason,
                patches_rolled_back=[],
                success=False,
                error=f"No matching patches found for: {patch_ids}",
            )
        
        # Use git to revert
        try:
            for patch in matching_patches:
                commit_hash = patch.get("commit_hash")
                if commit_hash:
                    await self._git_revert(commit_hash)
            
            patches_rolled_back = [p.get("patch_id") for p in matching_patches]
            
            record = RollbackRecord(
                rollback_id=rollback_id,
                triggered_at=datetime.utcnow(),
                reason=reason,
                patches_rolled_back=patches_rolled_back,
                success=True,
            )
            
            self._rollback_history.append(record)
            await self._save_history()
            
            return record
            
        except Exception as e:
            record = RollbackRecord(
                rollback_id=rollback_id,
                triggered_at=datetime.utcnow(),
                reason=reason,
                patches_rolled_back=[],
                success=False,
                error=str(e),
            )
            
            self._rollback_history.append(record)
            await self._save_history()
            
            return record
    
    async def _git_revert(self, commit_hash: str) -> None:
        """Revert a specific commit using git."""
        proc = await asyncio.create_subprocess_exec(
            "git", "revert", "--no-edit", commit_hash,
            cwd=self.repo_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise RuntimeError(f"Git revert failed: {stderr.decode()}")
    
    async def verify_rollback(self, deployment_id: str) -> bool:
        """
        Verify that a rollback was successful by running tests.
        
        Args:
            deployment_id: Deployment that was rolled back
            
        Returns:
            True if verification passes
        """
        deployment = next(
            (d for d in self._deployment_history if d.deployment_id == deployment_id),
            None,
        )
        
        if not deployment:
            return False
        
        # Run tests to verify
        from src.autonomous_development.test_runner import TestRunner
        
        runner = TestRunner(str(self.repo_path))
        await runner.initialize()
        
        result = await runner.run_tests()
        
        return result.success
    
    def get_deployment_history(self, limit: int = 50) -> List[DeploymentRecord]:
        """Get deployment history."""
        return self._deployment_history[-limit:]
    
    def get_rollback_history(self, limit: int = 50) -> List[RollbackRecord]:
        """Get rollback history."""
        return self._rollback_history[-limit:]
    
    def get_last_deployment(self) -> Optional[DeploymentRecord]:
        """Get the last deployment record."""
        return self._last_deployment
    
    def get_stats(self) -> Dict[str, Any]:
        """Get rollback manager statistics."""
        return {
            "total_deployments": len(self._deployment_history),
            "successful_deployments": len([d for d in self._deployment_history if d.status == "success"]),
            "rolled_back_deployments": len([d for d in self._deployment_history if d.status == "rolled_back"]),
            "total_rollbacks": len(self._rollback_history),
            "successful_rollbacks": len([r for r in self._rollback_history if r.success]),
            "last_deployment": self._last_deployment.deployment_id if self._last_deployment else None,
            "backup_count": len([b for b in self.backup_dir.iterdir() if b.is_dir()]),
        }