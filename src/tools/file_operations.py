"""
Sandboxed file operations tool for the Autonomous Agent Platform.

Provides read, write, list, and delete operations within a configurable
workspace directory.  All paths are validated to prevent directory
traversal attacks.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, Field

from src.config.logging import get_logger
from src.tools.base import AgentTool, ToolExecutionError

logger = get_logger(__name__)

# Default workspace root — can be overridden per-instance
_DEFAULT_WORKSPACE = os.path.join(os.getcwd(), "workspace")

# Maximum file size for read/write (10 MB)
_MAX_FILE_SIZE = 10 * 1024 * 1024


# ---------------------------------------------------------------------------
# Input schema
# ---------------------------------------------------------------------------

class FileOperationsInput(BaseModel):
    """Input schema for FileOperationsTool."""

    operation: Literal["read", "write", "list", "delete"] = Field(
        ...,
        description="Operation to perform: read, write, list, or delete",
    )
    path: str = Field(
        ...,
        min_length=1,
        max_length=1024,
        description="Relative path within the workspace directory",
    )
    content: str | None = Field(
        default=None,
        description="File content (required for write operation)",
    )


# ---------------------------------------------------------------------------
# Tool implementation
# ---------------------------------------------------------------------------

class FileOperationsTool(AgentTool):
    """Read, write, list, and delete files within a sandboxed workspace.

    All file operations are constrained to a configurable workspace
    directory.  Path traversal attempts (e.g. ``../../etc/passwd``) are
    detected and rejected before any I/O occurs.

    Example usage::

        tool = FileOperationsTool()
        result = await tool._arun(operation="read", path="notes.txt")
    """

    name: str = "file_operations"
    description: str = (
        "Read, write, list, or delete files within a sandboxed workspace "
        "directory. All paths must be relative to the workspace root."
    )
    args_schema: type[BaseModel] = FileOperationsInput
    max_retries: int = 1
    timeout_seconds: float = 30.0

    # Workspace root — instance-level override
    workspace_root: str = Field(
        default=_DEFAULT_WORKSPACE,
        description="Absolute path to the workspace root directory",
    )

    # ------------------------------------------------------------------
    # Core execution
    # ------------------------------------------------------------------

    async def _execute(self, **kwargs: Any) -> dict[str, Any]:
        """Dispatch to the appropriate file operation.

        Args:
            **kwargs: Validated fields from :class:`FileOperationsInput`.

        Returns:
            A dict describing the operation result.
        """
        operation: str = kwargs["operation"]
        path: str = kwargs["path"]
        content: str | None = kwargs.get("content")

        resolved = self._resolve_safe_path(path)

        dispatch = {
            "read": self._read,
            "write": self._write,
            "list": self._list,
            "delete": self._delete,
        }

        handler = dispatch.get(operation)
        if handler is None:
            raise ToolExecutionError(
                tool_name=self.name,
                message=f"Unknown operation: {operation!r}",
            )

        return await handler(resolved, content)

    # ------------------------------------------------------------------
    # Operations
    # ------------------------------------------------------------------

    async def _read(self, path: Path, _content: str | None) -> dict[str, Any]:
        """Read and return the contents of a file."""
        log = logger.bind(tool=self.name, operation="read", path=str(path))

        if not path.is_file():
            raise ToolExecutionError(
                tool_name=self.name,
                message=f"File not found: {path.relative_to(self.workspace_root)}",
            )

        size = path.stat().st_size
        if size > _MAX_FILE_SIZE:
            raise ToolExecutionError(
                tool_name=self.name,
                message=f"File too large ({size} bytes). Maximum is {_MAX_FILE_SIZE} bytes.",
            )

        text = path.read_text(encoding="utf-8")
        log.info("file_operations.read", size=len(text))
        return {
            "operation": "read",
            "path": str(path.relative_to(self.workspace_root)),
            "content": text,
            "size_bytes": len(text.encode("utf-8")),
        }

    async def _write(self, path: Path, content: str | None) -> dict[str, Any]:
        """Write content to a file, creating parent directories as needed."""
        log = logger.bind(tool=self.name, operation="write", path=str(path))

        if content is None:
            raise ToolExecutionError(
                tool_name=self.name,
                message="Content is required for write operations.",
            )

        encoded = content.encode("utf-8")
        if len(encoded) > _MAX_FILE_SIZE:
            raise ToolExecutionError(
                tool_name=self.name,
                message=f"Content too large ({len(encoded)} bytes). Maximum is {_MAX_FILE_SIZE} bytes.",
            )

        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")

        log.info("file_operations.write", size=len(encoded))
        return {
            "operation": "write",
            "path": str(path.relative_to(self.workspace_root)),
            "size_bytes": len(encoded),
            "status": "success",
        }

    async def _list(self, path: Path, _content: str | None) -> dict[str, Any]:
        """List files and directories at the given path."""
        log = logger.bind(tool=self.name, operation="list", path=str(path))

        # If the path points to a file, list its parent
        target = path if path.is_dir() else path.parent

        if not target.exists():
            raise ToolExecutionError(
                tool_name=self.name,
                message=f"Directory not found: {target.relative_to(self.workspace_root)}",
            )

        entries: list[dict[str, Any]] = []
        for entry in sorted(target.iterdir()):
            try:
                stat = entry.stat()
                entries.append(
                    {
                        "name": entry.name,
                        "type": "directory" if entry.is_dir() else "file",
                        "size_bytes": stat.st_size if entry.is_file() else None,
                        "modified": stat.st_mtime,
                    }
                )
            except OSError:
                entries.append(
                    {
                        "name": entry.name,
                        "type": "unknown",
                        "size_bytes": None,
                        "modified": None,
                    }
                )

        log.info("file_operations.list", entry_count=len(entries))
        return {
            "operation": "list",
            "path": str(target.relative_to(self.workspace_root)),
            "entries": entries,
            "entry_count": len(entries),
        }

    async def _delete(self, path: Path, _content: str | None) -> dict[str, Any]:
        """Delete a file (not directories)."""
        log = logger.bind(tool=self.name, operation="delete", path=str(path))

        if not path.exists():
            raise ToolExecutionError(
                tool_name=self.name,
                message=f"File not found: {path.relative_to(self.workspace_root)}",
            )

        if path.is_dir():
            raise ToolExecutionError(
                tool_name=self.name,
                message="Cannot delete directories. Only individual files may be deleted.",
            )

        file_size = path.stat().st_size
        path.unlink()

        log.info("file_operations.delete", size=file_size)
        return {
            "operation": "delete",
            "path": str(path.relative_to(self.workspace_root)),
            "size_bytes": file_size,
            "status": "success",
        }

    # ------------------------------------------------------------------
    # Path validation
    # ------------------------------------------------------------------

    def _resolve_safe_path(self, relative_path: str) -> Path:
        """Resolve a relative path and ensure it stays within the workspace.

        Args:
            relative_path: User-supplied path relative to the workspace root.

        Returns:
            The resolved absolute :class:`Path`.

        Raises:
            ToolExecutionError: If the resolved path escapes the workspace.
        """
        workspace = Path(self.workspace_root).resolve()

        # Reject absolute paths
        if os.path.isabs(relative_path):
            raise ToolExecutionError(
                tool_name=self.name,
                message="Absolute paths are not allowed. Use a path relative to the workspace.",
            )

        # Reject obviously dangerous components
        if ".." in Path(relative_path).parts:
            raise ToolExecutionError(
                tool_name=self.name,
                message="Path traversal ('..') is not allowed.",
            )

        resolved = (workspace / relative_path).resolve()

        # Final fence: resolved path must be under the workspace root
        try:
            resolved.relative_to(workspace)
        except ValueError:
            raise ToolExecutionError(
                tool_name=self.name,
                message="Path escapes the sandbox workspace.",
            )

        return resolved
