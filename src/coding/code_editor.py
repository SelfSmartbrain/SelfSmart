"""Code editor for reading, writing, and modifying code files."""

import difflib
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import hashlib


@dataclass
class EditResult:
    """Result of a code edit operation."""
    file_path: str
    success: bool
    before: str = ""
    after: str = ""
    diff: str = ""
    error: Optional[str] = None
    checksum_before: str = ""
    checksum_after: str = ""

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'file_path': self.file_path,
            'success': self.success,
            'before': self.before,
            'after': self.after,
            'diff': self.diff,
            'error': self.error,
            'checksum_before': self.checksum_before,
            'checksum_after': self.checksum_after
        }


@dataclass
class FileChange:
    """Represents a single file change."""
    file_path: str
    operation: str  # 'read', 'write', 'patch', 'replace_block', 'refactor', 'create'
    content: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    old_content: Optional[str] = None
    new_content: Optional[str] = None


class CodeEditor:
    """Editor for code files with change tracking和 diff generation."""

    def __init__(self, repository_path: str):
        self.repository_path = Path(repository_path)
        self.change_history: List[EditResult] = []

    def read_file(self, file_path: str) -> EditResult:
        """Read a file from the repository."""
        full_path = self.repository_path / file_path
        
        if not full_path.exists():
            return EditResult(
                file_path=file_path,
                success=False,
                error=f"File not found: {file_path}"
            )

        try:
            content = full_path.read_text()
            checksum = self._compute_checksum(content)
            
            return EditResult(
                file_path=file_path,
                success=True,
                before=content,
                after=content,
                diff="",
                checksum_before=checksum,
                checksum_after=checksum
            )
        except Exception as e:
            return EditResult(
                file_path=file_path,
                success=False,
                error=str(e)
            )

    def write_file(self, file_path: str, content: str) -> EditResult:
        """Write content to a file, tracking changes."""
        full_path = self.repository_path / file_path
        full_path.parent.mkdir(parents=True, exist_ok=True)
        
        before = ""
        if full_path.exists():
            before = full_path.read_text()
        
        checksum_before = self._compute_checksum(before)
        
        try:
            full_path.write_text(content)
            checksum_after = self._compute_checksum(content)
            diff = self._generate_diff(before, content, file_path)
            
            result = EditResult(
                file_path=file_path,
                success=True,
                before=before,
                after=content,
                diff=diff,
                checksum_before=checksum_before,
                checksum_after=checksum_after
            )
            
            self.change_history.append(result)
            return result
            
        except Exception as e:
            return EditResult(
                file_path=file_path,
                success=False,
                before=before,
                after=before,
                error=str(e),
                checksum_before=checksum_before,
                checksum_after=checksum_before
            )

    def patch_file(self, file_path: str, old_content: str, new_content: str) -> EditResult:
        """Apply a patch by replacing old_content with new_content."""
        full_path = self.repository_path / file_path
        
        if not full_path.exists():
            return EditResult(
                file_path=file_path,
                success=False,
                error=f"File not found: {file_path}"
            )
        
        before = full_path.read_text()
        checksum_before = self._compute_checksum(before)
        
        if old_content not in before:
            return EditResult(
                file_path=file_path,
                success=False,
                before=before,
                after=before,
                error="Old content not found in file",
                checksum_before=checksum_before,
                checksum_after=checksum_before
            )
        
        try:
            after = before.replace(old_content, new_content, 1)
            full_path.write_text(after)
            checksum_after = self._compute_checksum(after)
            diff = self._generate_diff(before, after, file_path)
            
            result = EditResult(
                file_path=file_path,
                success=True,
                before=before,
                after=after,
                diff=diff,
                checksum_before=checksum_before,
                checksum_after=checksum_after
            )
            
            self.change_history.append(result)
            return result
            
        except Exception as e:
            return EditResult(
                file_path=file_path,
                success=False,
                before=before,
                after=before,
                error=str(e),
                checksum_before=checksum_before,
                checksum_after=checksum_before
            )

    def replace_block(self, file_path: str, line_start: int, line_end: int, new_content: str) -> EditResult:
        """Replace a block of lines with new content."""
        full_path = self.repository_path / file_path
        
        if not full_path.exists():
            return EditResult(
                file_path=file_path,
                success=False,
                error=f"File not found: {file_path}"
            )
        
        before = full_path.read_text()
        checksum_before = self._compute_checksum(before)
        lines = before.split('\n')
        
        if line_start < 1 or line_end > len(lines) or line_start > line_end:
            return EditResult(
                file_path=file_path,
                success=False,
                before=before,
                after=before,
                error=f"Invalid line range: {line_start}-{line_end}",
                checksum_before=checksum_before,
                checksum_after=checksum_before
            )
        
        try:
            new_lines = lines[:line_start-1] + [new_content] + lines[line_end:]
            after = '\n'.join(new_lines)
            full_path.write_text(after)
            checksum_after = self._compute_checksum(after)
            diff = self._generate_diff(before, after, file_path)
            
            result = EditResult(
                file_path=file_path,
                success=True,
                before=before,
                after=after,
                diff=diff,
                checksum_before=checksum_before,
                checksum_after=checksum_after
            )
            
            self.change_history.append(result)
            return result
            
        except Exception as e:
            return EditResult(
                file_path=file_path,
                success=False,
                before=before,
                after=before,
                error=str(e),
                checksum_before=checksum_before,
                checksum_after=checksum_before
            )

    def refactor_function(self, file_path: str, function_name: str, new_implementation: str) -> EditResult:
        """Refactor a function with a new implementation."""
        full_path = self.repository_path / file_path
        
        if not full_path.exists():
            return EditResult(
                file_path=file_path,
                success=False,
                error=f"File not found: {file_path}"
            )
        
        before = full_path.read_text()
        checksum_before = self._compute_checksum(before)
        
        # Simple pattern matching for function definition
        # This is a basic implementation; for production, use AST parsing
        try:
            import ast
            tree = ast.parse(before)
            
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef) and node.name == function_name:
                    # Found the function, now replace it
                    # This is simplified; in production, use ast.unparse or similar
                    start_line = node.lineno
                    end_line = node.end_lineno if node.end_lineno else start_line
                    
                    lines = before.split('\n')
                    new_lines = lines[:start_line-1] + [new_implementation] + lines[end_line:]
                    after = '\n'.join(new_lines)
                    
                    full_path.write_text(after)
                    checksum_after = self._compute_checksum(after)
                    diff = self._generate_diff(before, after, file_path)
                    
                    result = EditResult(
                        file_path=file_path,
                        success=True,
                        before=before,
                        after=after,
                        diff=diff,
                        checksum_before=checksum_before,
                        checksum_after=checksum_after
                    )
                    
                    self.change_history.append(result)
                    return result
            
            return EditResult(
                file_path=file_path,
                success=False,
                before=before,
                after=before,
                error=f"Function not found: {function_name}",
                checksum_before=checksum_before,
                checksum_after=checksum_before
            )
            
        except Exception as e:
            return EditResult(
                file_path=file_path,
                success=False,
                before=before,
                after=before,
                error=str(e),
                checksum_before=checksum_before,
                checksum_after=checksum_before
            )

    def create_file(self, file_path: str, content: str) -> EditResult:
        """Create a new file with content."""
        full_path = self.repository_path / file_path
        
        if full_path.exists():
            return EditResult(
                file_path=file_path,
                success=False,
                error=f"File already exists: {file_path}"
            )
        
        return self.write_file(file_path, content)

    def apply_patch(self, patch: FileChange) -> EditResult:
        """Apply a file change operation."""
        if patch.operation == 'read':
            return self.read_file(patch.file_path)
        elif patch.operation == 'write':
            return self.write_file(patch.file_path, patch.content or "")
        elif patch.operation == 'patch':
            return self.patch_file(patch.file_path, patch.old_content or "", patch.new_content or "")
        elif patch.operation == 'replace_block':
            return self.replace_block(
                patch.file_path,
                patch.line_start or 1,
                patch.line_end or 1,
                patch.new_content or ""
            )
        elif patch.operation == 'refactor':
            return self.refactor_function(patch.file_path, patch.old_content or "", patch.new_content or "")
        elif patch.operation == 'create':
            return self.create_file(patch.file_path, patch.content or "")
        else:
            return EditResult(
                file_path=patch.file_path,
                success=False,
                error=f"Unknown operation: {patch.operation}"
            )

    def get_change_history(self) -> List[EditResult]:
        """Get the history of all changes made."""
        return self.change_history

    def undo_last_change(self) -> Optional[EditResult]:
        """Undo the last change made."""
        if not self.change_history:
            return None
        
        last_change = self.change_history.pop()
        if last_change.success and last_change.before:
            result = self.write_file(last_change.file_path, last_change.before)
            result.error = "Undo operation"
            return result
        
        return last_change

    def _compute_checksum(self, content: str) -> str:
        """Compute checksum for content."""
        return hashlib.md5(content.encode()).hexdigest()

    def _generate_diff(self, before: str, after: str, file_path: str) -> str:
        """Generate unified diff between before and after."""
        before_lines = before.splitlines(keepends=True)
        after_lines = after.splitlines(keepends=True)
        
        diff = difflib.unified_diff(
            before_lines,
            after_lines,
            fromfile=f"a/{file_path}",
            tofile=f"b/{file_path}",
            lineterm=""
        )
        
        return ''.join(diff)
