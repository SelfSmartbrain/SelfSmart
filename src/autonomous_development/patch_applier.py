"""
Patch Applier - Applies generated patches to codebase.

Handles applying patches to both sandbox environments and production
repository with proper backup and rollback support.
"""

import asyncio
import logging
import shutil
import tempfile
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from src.coding.patch_generator import GeneratedPatch, FileChange

logger = logging.getLogger(__name__)


@dataclass
class PatchResult:
    """Result of applying a patch."""

    success: bool
    patch_id: str
    applied_files: List[str] = None
    failed_files: List[str] = None
    error: Optional[str] = None
    backup_id: Optional[str] = None

    def __post_init__(self):
        if self.applied_files is None:
            self.applied_files = []
        if self.failed_files is None:
            self.failed_files = []


class PatchApplier:
    """
    Applies generated patches to a codebase.

    Supports:
    - Applying to sandbox for testing
    - Applying to production with backup
    - Dry-run mode for validation
    - Partial application with rollback on failure
    """

    def __init__(
        self,
        repo_path: str,
        backup_dir: Optional[str] = None,
    ):
        self.repo_path = Path(repo_path).resolve()
        self.backup_dir = Path(backup_dir) if backup_dir else self.repo_path / ".patch_backups"
        self.backup_dir.mkdir(parents=True, exist_ok=True)

        self._sandbox_dirs: List[Path] = []

    async def initialize(self) -> None:
        """Initialize the patch applier."""
        # Verify git repo
        if not (self.repo_path / ".git").exists():
            logger.warning(f"Not a git repository: {self.repo_path}")
        logger.info(f"PatchApplier initialized for {self.repo_path}")

    async def create_sandbox(self) -> Path:
        """
        Create a sandbox copy of the repository.

        Returns:
            Path to sandbox directory
        """
        # Create temp directory
        sandbox = Path(tempfile.mkdtemp(prefix="patch_sandbox_"))

        # Copy repository (excluding .git and large dirs)
        await self._copy_repo(sandbox)

        self._sandbox_dirs.append(sandbox)
        logger.debug(f"Created sandbox: {sandbox}")

        return sandbox

    async def _copy_repo(self, target: Path) -> None:
        """Copy repository to target, excluding certain directories."""
        exclude = {".git", "__pycache__", ".pytest_cache", ".venv", "node_modules", ".mypy_cache"}

        def ignore_func(dirname, names):
            return [n for n in names if n in exclude or n.startswith(".")]

        # Use async thread pool for I/O
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            lambda: shutil.copytree(
                self.repo_path,
                target,
                ignore=ignore_func,
                dirs_exist_ok=True,
            ),
        )

    async def cleanup_sandbox(self, sandbox: Path) -> None:
        """Clean up a sandbox directory."""
        try:
            await asyncio.get_event_loop().run_in_executor(
                None,
                shutil.rmtree,
                sandbox,
            )
            if sandbox in self._sandbox_dirs:
                self._sandbox_dirs.remove(sandbox)
            logger.debug(f"Cleaned up sandbox: {sandbox}")
        except Exception as e:
            logger.error(f"Failed to cleanup sandbox {sandbox}: {e}")

    async def apply_patch(
        self,
        target_path: Path,
        patch: GeneratedPatch,
        dry_run: bool = False,
        create_backup: bool = True,
    ) -> PatchResult:
        """
        Apply a generated patch to target path.

        Args:
            target_path: Path to apply patch to
            patch: GeneratedPatch to apply
            dry_run: If True, only validate without applying
            create_backup: If True, create backup before applying

        Returns:
            PatchResult with success status and details
        """
        patch_id = patch.metadata.get("task_type", "patch")
        backup_id = None

        try:
            # Create backup if requested
            if create_backup and not dry_run:
                backup_id = await self._create_backup(target_path, patch_id)

            applied = []
            failed = []

            for change in patch.file_changes:
                file_path = target_path / change.file_path

                try:
                    if dry_run:
                        # Just validate the change can be applied
                        await self._validate_change(file_path, change)
                        applied.append(change.file_path)
                    else:
                        await self._apply_change(file_path, change)
                        applied.append(change.file_path)

                except Exception as e:
                    logger.error(f"Failed to apply change to {change.file_path}: {e}")
                    failed.append(change.file_path)

            if failed and not dry_run:
                # Rollback on partial failure
                if backup_id:
                    await self._restore_backup(target_path, backup_id)
                return PatchResult(
                    success=False,
                    patch_id=patch_id,
                    applied_files=applied,
                    failed_files=failed,
                    error=f"Failed to apply {len(failed)} files",
                    backup_id=backup_id,
                )

            return PatchResult(
                success=len(failed) == 0,
                patch_id=patch_id,
                applied_files=applied,
                failed_files=failed,
                backup_id=backup_id,
            )

        except Exception as e:
            logger.error(f"Patch application failed: {e}")
            if backup_id and not dry_run:
                await self._restore_backup(target_path, backup_id)
            return PatchResult(
                success=False,
                patch_id=patch_id,
                error=str(e),
                backup_id=backup_id,
            )

    async def _validate_change(self, file_path: Path, change: FileChange) -> None:
        """Validate that a change can be applied."""
        if change.operation == "create":
            if file_path.exists():
                raise ValueError(f"File already exists: {file_path}")
            # Check parent directory exists
            if not file_path.parent.exists():
                raise ValueError(f"Parent directory does not exist: {file_path.parent}")

        elif change.operation == "patch":
            if not file_path.exists():
                raise ValueError(f"File does not exist: {file_path}")

            # Verify old_content matches if provided
            if change.old_content:
                current_content = file_path.read_text()
                if change.old_content not in current_content:
                    raise ValueError(f"Old content doesn't match file: {file_path}")

        elif change.operation == "delete":
            if not file_path.exists():
                raise ValueError(f"File does not exist: {file_path}")

    async def _apply_change(self, file_path: Path, change: FileChange) -> None:
        """Apply a single file change."""
        if change.operation == "create":
            file_path.parent.mkdir(parents=True, exist_ok=True)
            file_path.write_text(change.new_content or change.content)

        elif change.operation == "patch":
            current = file_path.read_text()
            if change.old_content and change.old_content in current:
                new_content = current.replace(change.old_content, change.new_content)
            elif change.new_content:
                new_content = change.new_content
            else:
                new_content = change.content
            file_path.write_text(new_content)

        elif change.operation == "delete":
            file_path.unlink()
            # Remove empty parent directories
            try:
                file_path.parent.rmdir()
            except OSError:
                pass  # Not empty

    async def _create_backup(self, target_path: Path, patch_id: str) -> str:
        """Create a backup of the target before applying patch."""
        import uuid

        backup_id = f"{patch_id}_{uuid.uuid4().hex[:8]}"
        backup_path = self.backup_dir / backup_id

        # Copy only the files that might be changed
        # For simplicity, backup the whole repo
        await asyncio.get_event_loop().run_in_executor(
            None,
            lambda: shutil.copytree(target_path, backup_path, dirs_exist_ok=True),
        )

        logger.info(f"Created backup: {backup_id}")
        return backup_id

    async def _restore_backup(self, target_path: Path, backup_id: str) -> bool:
        """Restore from backup."""
        backup_path = self.backup_dir / backup_id

        if not backup_path.exists():
            logger.error(f"Backup not found: {backup_id}")
            return False

        try:
            # Remove target and restore from backup
            await asyncio.get_event_loop().run_in_executor(
                None,
                shutil.rmtree,
                target_path,
            )
            await asyncio.get_event_loop().run_in_executor(
                None,
                shutil.copytree,
                backup_path,
                target_path,
            )
            logger.info(f"Restored from backup: {backup_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to restore backup {backup_id}: {e}")
            return False

    async def apply_multiple(
        self,
        target_path: Path,
        patches: List[GeneratedPatch],
        continue_on_error: bool = False,
    ) -> List[PatchResult]:
        """Apply multiple patches sequentially."""
        results = []

        for patch in patches:
            result = await self.apply_patch(target_path, patch)
            results.append(result)

            if not result.success and not continue_on_error:
                logger.warning(f"Stopping on failed patch: {patch.metadata.get('task_type')}")
                break

        return results

    async def dry_run(self, patch: GeneratedPatch) -> PatchResult:
        """Perform a dry run of patch application."""
        return await self.apply_patch(self.repo_path, patch, dry_run=True)

    def list_backups(self) -> List[Dict[str, Any]]:
        """List available backups."""
        backups = []
        for backup in sorted(
            self.backup_dir.iterdir(), key=lambda x: x.stat().st_mtime, reverse=True
        ):
            if backup.is_dir():
                stat = backup.stat()
                backups.append(
                    {
                        "id": backup.name,
                        "created": stat.st_mtime,
                        "size": sum(f.stat().st_size for f in backup.rglob("*") if f.is_file()),
                    }
                )
        return backups

    async def cleanup_old_backups(self, keep: int = 10) -> int:
        """Remove old backups beyond keep limit."""
        backups = sorted(
            self.backup_dir.iterdir(),
            key=lambda x: x.stat().st_mtime,
            reverse=True,
        )

        removed = 0
        for backup in backups[keep:]:
            try:
                await asyncio.get_event_loop().run_in_executor(
                    None,
                    shutil.rmtree,
                    backup,
                )
                removed += 1
            except Exception as e:
                logger.error(f"Failed to remove backup {backup}: {e}")

        return removed
