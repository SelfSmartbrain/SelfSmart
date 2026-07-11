"""
Sandboxed filesystem operations tool.

Provides safe file operations within a restricted base directory.
Prevents path traversal attacks and unauthorized access.
"""

import os
import shutil
from pathlib import Path
from typing import Optional

from src.config.logging import get_logger

logger = get_logger(__name__)


class FilesystemTool:
    """
    Sandboxed filesystem tool that restricts all operations to a base directory.
    
    All paths are resolved relative to base_dir and validated to prevent
    path traversal attacks (e.g., ../../etc/passwd).
    """

    def __init__(self, base_dir: Optional[str] = None):
        """
        Initialize the filesystem tool with a base directory.
        
        Args:
            base_dir: The root directory for all operations. Defaults to current working directory.
        """
        self.base_dir = Path(base_dir).resolve() if base_dir else Path(os.getcwd()).resolve()
        logger.info(f"FilesystemTool initialized with base_dir: {self.base_dir}")

    def _resolve_path(self, path: str) -> Path:
        """
        Resolve a path relative to base_dir and validate it's within the sandbox.
        
        Args:
            path: Relative or absolute path
            
        Returns:
            Resolved Path object within base_dir
            
        Raises:
            ValueError: If the path attempts to traverse outside base_dir
        """
        p = Path(path)
        
        # If relative, resolve relative to base_dir
        if not p.is_absolute():
            p = self.base_dir / p
        
        # Resolve to absolute path (follows symlinks)
        try:
            p = p.resolve()
        except Exception as e:
            raise ValueError(f"Invalid path: {path}") from e
        
        # Validate the path is within base_dir (prevents path traversal)
        try:
            p.relative_to(self.base_dir)
        except ValueError:
            logger.warning(f"Path traversal attempt blocked: {path} -> {p}")
            raise ValueError(f"Path traversal attempt: {path} is outside allowed directory")
        
        return p

    def _validate_path(self, path: str) -> Path:
        """Validate and resolve a path, raising ValueError if invalid."""
        return self._resolve_path(path)

    def read_file(self, path: str) -> str:
        """
        Read a file within the sandbox.
        
        Args:
            path: Path to the file (relative to base_dir)
            
        Returns:
            File contents as string, or error message
        """
        try:
            p = self._validate_path(path)
            if not p.exists():
                return f"Error: File not found: {path}"
            if not p.is_file():
                return f"Error: Not a file: {path}"
            return p.read_text()
        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            return f"Error reading file: {e}"

    def write_file(self, path: str, content: str) -> str:
        """
        Write a file within the sandbox.
        
        Args:
            path: Path to the file (relative to base_dir)
            content: Content to write
            
        Returns:
            Success message or error message
        """
        try:
            p = self._validate_path(path)
            # Ensure parent directory exists
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(content)
            logger.info(f"Successfully wrote to {path}")
            return f"Successfully wrote to {path}"
        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            logger.error(f"Error writing file {path}: {e}")
            return f"Error writing file: {e}"

    def search(self, query: str) -> str:
        """
        Search for files matching a query.
        
        Args:
            query: Search query
            
        Returns:
            Search results or not implemented message
        """
        return f"Search for {query} not implemented yet."

    def replace(self, path: str, old: str, new: str) -> str:
        """
        Replace text in a file.
        
        Args:
            path: Path to the file
            old: Text to replace
            new: Replacement text
            
        Returns:
            Result message
        """
        content = self.read_file(path)
        if content.startswith("Error"):
            return content
        new_content = content.replace(old, new)
        return self.write_file(path, new_content)

    def move(self, src: str, dst: str) -> str:
        """
        Move a file or directory within the sandbox.
        
        Args:
            src: Source path
            dst: Destination path
            
        Returns:
            Result message
        """
        try:
            src_path = self._validate_path(src)
            dst_path = self._validate_path(dst)
            
            if not src_path.exists():
                return f"Error: Source not found: {src}"
            
            # Ensure destination parent exists
            dst_path.parent.mkdir(parents=True, exist_ok=True)
            
            shutil.move(str(src_path), str(dst_path))
            logger.info(f"Moved {src} to {dst}")
            return f"Moved {src} to {dst}"
        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            logger.error(f"Error moving {src} to {dst}: {e}")
            return f"Error moving: {e}"

    def delete(self, path: str, recursive: bool = False, confirm: bool = False) -> str:
        """
        Delete a file or directory within the sandbox.
        
        Args:
            path: Path to delete
            recursive: If True, delete directories recursively
            confirm: If True, require confirmation (not used in automated context)
            
        Returns:
            Result message
        """
        try:
            p = self._validate_path(path)
            
            if not p.exists():
                return f"Error: Path not found: {path}"
            
            if p.is_file():
                p.unlink()
                logger.info(f"Deleted file: {path}")
                return f"Deleted file: {path}"
            elif p.is_dir():
                if not recursive:
                    return f"Error: {path} is a directory. Use recursive=True to delete directories."
                shutil.rmtree(p)
                logger.info(f"Deleted directory: {path}")
                return f"Deleted directory: {path}"
            else:
                return f"Error: Unknown path type: {path}"
        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            logger.error(f"Error deleting {path}: {e}")
            return f"Error deleting: {e}"

    def list_directory(self, path: str = ".") -> str:
        """
        List contents of a directory.
        
        Args:
            path: Directory path (relative to base_dir)
            
        Returns:
            Directory listing or error message
        """
        try:
            p = self._validate_path(path)
            
            if not p.exists():
                return f"Error: Directory not found: {path}"
            if not p.is_dir():
                return f"Error: Not a directory: {path}"
            
            items = []
            for item in p.iterdir():
                items.append({
                    "name": item.name,
                    "type": "directory" if item.is_dir() else "file",
                    "size": item.stat().st_size if item.is_file() else None,
                })
            
            return str(items)
        except ValueError as e:
            return f"Error: {e}"
        except Exception as e:
            logger.error(f"Error listing directory {path}: {e}")
            return f"Error listing directory: {e}"