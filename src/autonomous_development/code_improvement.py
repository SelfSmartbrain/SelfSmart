"""
Code Improvement - Code analysis and improvement suggestions

The CodeImprovement module is responsible for:
- Analyzing code quality
- Suggesting improvements
- Identifying anti-patterns
- Performance optimization suggestions
"""

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional, Set
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)


class IssueSeverity(Enum):
    """Severity of code issues"""
    INFO = "info"
    MINOR = "minor"
    MAJOR = "major"
    CRITICAL = "critical"


@dataclass
class CodeIssue:
    """A code issue found during analysis"""
    issue_id: str
    file_path: str
    line_number: int
    severity: IssueSeverity
    category: str
    description: str
    suggestion: str
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


@dataclass
class ImprovementSuggestion:
    """A suggestion for code improvement"""
    suggestion_id: str
    file_path: str
    improvement_type: str
    description: str
    code_before: Optional[str] = None
    code_after: Optional[str] = None
    estimated_impact: str = "low"
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())


class CodeImprovement:
    """
    Code analysis and improvement suggestions.
    
    Provides:
    - Code quality analysis
    - Anti-pattern detection
    - Performance suggestions
    - Best practice recommendations
    """
    
    def __init__(self):
        self._issues: List[CodeIssue] = []
        self._suggestions: List[ImprovementSuggestion] = []
        
        # Analysis patterns
        self._anti_patterns = {
            "long_function": {"threshold": 50, "severity": IssueSeverity.MINOR},
            "deep_nesting": {"threshold": 4, "severity": IssueSeverity.MAJOR},
            "duplicate_code": {"threshold": 3, "severity": IssueSeverity.MINOR},
            "magic_numbers": {"threshold": 0, "severity": IssueSeverity.INFO},
        }
        
        # Statistics
        self._files_analyzed = 0
        self._issues_found = 0
        self._suggestions_generated = 0
    
    async def initialize(self) -> None:
        """Initialize code improvement module"""
        logger.info("CodeImprovement initialized")
    
    async def analyze_file(
        self,
        file_path: str,
        content: str,
    ) -> List[CodeIssue]:
        """
        Analyze a file for issues.
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            List of issues found
        """
        self._files_analyzed += 1
        
        issues = []
        lines = content.split("\n")
        
        # Check for long functions
        function_length = 0
        for i, line in enumerate(lines, 1):
            if line.strip().startswith("def "):
                if function_length > self._anti_patterns["long_function"]["threshold"]:
                    issues.append(CodeIssue(
                        issue_id=f"issue_{datetime.now().timestamp()}_{i}",
                        file_path=file_path,
                        line_number=i - function_length,
                        severity=self._anti_patterns["long_function"]["severity"],
                        category="complexity",
                        description=f"Function is {function_length} lines long",
                        suggestion="Consider breaking this function into smaller functions",
                    ))
                function_length = 0
            else:
                function_length += 1
        
        # Check for deep nesting
        for i, line in enumerate(lines, 1):
            nesting = (len(line) - len(line.lstrip())) // 4
            if nesting > self._anti_patterns["deep_nesting"]["threshold"]:
                issues.append(CodeIssue(
                    issue_id=f"issue_{datetime.now().timestamp()}_{i}",
                    file_path=file_path,
                    line_number=i,
                    severity=self._anti_patterns["deep_nesting"]["severity"],
                    category="readability",
                    description=f"Deep nesting ({nesting} levels)",
                    suggestion="Consider refactoring to reduce nesting",
                ))
        
        self._issues.extend(issues)
        self._issues_found += len(issues)
        
        logger.debug(f"Analyzed {file_path}: {len(issues)} issues found")
        return issues
    
    async def generate_suggestions(
        self,
        file_path: str,
        content: str,
    ) -> List[ImprovementSuggestion]:
        """
        Generate improvement suggestions for a file.
        
        Args:
            file_path: Path to the file
            content: File content
            
        Returns:
            List of suggestions
        """
        suggestions = []
        
        # Suggest type hints
        if "def " in content and " -> " not in content:
            suggestions.append(ImprovementSuggestion(
                suggestion_id=f"suggestion_{datetime.now().timestamp()}",
                file_path=file_path,
                improvement_type="type_hints",
                description="Add type hints to function signatures",
                estimated_impact="medium",
            ))
        
        # Suggest docstrings
        if "def " in content and '"""' not in content and "'''" not in content:
            suggestions.append(ImprovementSuggestion(
                suggestion_id=f"suggestion_{datetime.now().timestamp()}",
                file_path=file_path,
                improvement_type="documentation",
                description="Add docstrings to functions",
                estimated_impact="medium",
            ))
        
        # Suggest error handling
        if "except:" in content:
            suggestions.append(ImprovementSuggestion(
                suggestion_id=f"suggestion_{datetime.now().timestamp()}",
                file_path=file_path,
                improvement_type="error_handling",
                description="Avoid bare except clauses",
                estimated_impact="high",
            ))
        
        self._suggestions.extend(suggestions)
        self._suggestions_generated += len(suggestions)
        
        logger.debug(f"Generated {len(suggestions)} suggestions for {file_path}")
        return suggestions
    
    async def analyze_directory(
        self,
        directory_path: str,
        file_pattern: str = "*.py",
    ) -> Dict[str, Any]:
        """
        Analyze all files in a directory.
        
        Args:
            directory_path: Path to directory
            file_pattern: File pattern to match
            
        Returns:
            Analysis summary
        """
        # Placeholder for directory analysis
        # In full implementation, would walk directory and analyze files
        
        summary = {
            "files_analyzed": self._files_analyzed,
            "issues_found": self._issues_found,
            "suggestions_generated": self._suggestions_generated,
            "severity_breakdown": self._get_severity_breakdown(),
        }
        
        return summary
    
    def _get_severity_breakdown(self) -> Dict[str, int]:
        """Get breakdown of issues by severity"""
        breakdown = {severity.value: 0 for severity in IssueSeverity}
        
        for issue in self._issues:
            breakdown[issue.severity.value] += 1
        
        return breakdown
    
    def get_issues(
        self,
        severity: Optional[IssueSeverity] = None,
        category: Optional[str] = None,
        limit: int = 100,
    ) -> List[CodeIssue]:
        """
        Get issues, optionally filtered.
        
        Args:
            severity: Filter by severity
            category: Filter by category
            limit: Maximum results
            
        Returns:
            List of issues
        """
        issues = self._issues
        
        if severity:
            issues = [i for i in issues if i.severity == severity]
        
        if category:
            issues = [i for i in issues if i.category == category]
        
        return issues[:limit]
    
    def get_suggestions(
        self,
        improvement_type: Optional[str] = None,
        limit: int = 100,
    ) -> List[ImprovementSuggestion]:
        """
        Get suggestions, optionally filtered.
        
        Args:
            improvement_type: Filter by type
            limit: Maximum results
            
        Returns:
            List of suggestions
        """
        suggestions = self._suggestions
        
        if improvement_type:
            suggestions = [s for s in suggestions if s.improvement_type == improvement_type]
        
        return suggestions[:limit]
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get code improvement metrics"""
        return {
            "files_analyzed": self._files_analyzed,
            "issues_found": self._issues_found,
            "suggestions_generated": self._suggestions_generated,
            "severity_breakdown": self._get_severity_breakdown(),
        }
