"""
Static Analyzer - Static code analysis for security and correctness.

Analyzes self-generated or modified code for:
- Security vulnerabilities
- Code quality issues
- Performance problems
- Correctness concerns
- Best practice violations
"""

import ast
import logging
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set
from collections import defaultdict

logger = logging.getLogger(__name__)


class Severity(Enum):
    """Severity levels for findings."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class FindingType(Enum):
    """Types of static analysis findings."""
    # Security
    SQL_INJECTION = "sql_injection"
    COMMAND_INJECTION = "command_injection"
    PATH_TRAVERSAL = "path_traversal"
    XSS = "xss"
    HARDCODED_SECRET = "hardcoded_secret"
    WEAK_CRYPTO = "weak_crypto"
    INSECURE_DESERIALIZATION = "insecure_deserialization"
    
    # Code Quality
    UNUSED_VARIABLE = "unused_variable"
    UNUSED_IMPORT = "unused_import"
    DEAD_CODE = "dead_code"
    LONG_FUNCTION = "long_function"
    HIGH_COMPLEXITY = "high_complexity"
    DUPLICATE_CODE = "duplicate_code"
    MISSING_DOCSTRING = "missing_docstring"
    MISSING_TYPE_HINTS = "missing_type_hints"
    
    # Performance
    INEFFICIENT_LOOP = "inefficient_loop"
    N_PLUS_ONE_QUERY = "n_plus_one_query"
    MEMORY_LEAK = "memory_leak"
    BLOCKING_CALL = "blocking_call"
    
    # Correctness
    POSSIBLE_NULL_DEREF = "possible_null_deref"
    TYPE_MISMATCH = "type_mismatch"
    INFINITE_LOOP = "infinite_loop"
    OFF_BY_ONE = "off_by_one"
    RESOURCE_LEAK = "resource_leak"
    
    # Best Practices
    MUTABLE_DEFAULT_ARG = "mutable_default_arg"
    BARE_EXCEPT = "bare_except"
    GLOBAL_VARIABLE = "global_variable"
    MAGIC_NUMBER = "magic_number"
    
    # Self-Modification Specific
    SELF_MODIFYING_CODE = "self_modifying_code"
    RUNTIME_CODE_GENERATION = "runtime_code_generation"
    EVAL_EXEC_USAGE = "eval_exec_usage"
    DYNAMIC_IMPORT = "dynamic_import"


@dataclass
class Finding:
    """A static analysis finding."""
    finding_id: str
    finding_type: FindingType
    severity: Severity
    file_path: str
    line_number: int
    column: int
    message: str
    code_snippet: str = ""
    recommendation: str = ""
    confidence: float = 1.0  # 0.0 to 1.0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "finding_id": self.finding_id,
            "finding_type": self.finding_type.value,
            "severity": self.severity.value,
            "file_path": self.file_path,
            "line_number": self.line_number,
            "column": self.column,
            "message": self.message,
            "code_snippet": self.code_snippet,
            "recommendation": self.recommendation,
            "confidence": self.confidence,
            "metadata": self.metadata,
        }


@dataclass
class AnalysisConfig:
    """Configuration for static analysis."""
    # Enable/disable check categories
    enable_security_checks: bool = True
    enable_quality_checks: bool = True
    enable_performance_checks: bool = True
    enable_correctness_checks: bool = True
    enable_best_practice_checks: bool = True
    enable_self_modification_checks: bool = True
    
    # Severity thresholds
    min_severity: Severity = Severity.INFO
    
    # Thresholds
    max_function_lines: int = 50
    max_complexity: int = 10
    max_file_lines: int = 500
    max_nesting_depth: int = 4
    
    # External tools
    use_bandit: bool = True  # Python security linter
    use_pylint: bool = True
    use_mypy: bool = True
    use_flake8: bool = True
    
    # Exclusions
    exclude_patterns: List[str] = field(default_factory=lambda: [
        "**/test_*.py",
        "**/*_test.py",
        "**/migrations/**",
        "**/venv/**",
        "**/.venv/**",
    ])
    
    # Custom rules
    custom_rules: List[Callable] = field(default_factory=list)


@dataclass
class AnalysisResult:
    """Result of static analysis."""
    file_path: str
    timestamp: float = field(default_factory=lambda: datetime.now().timestamp())
    findings: List[Finding] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)
    execution_time_seconds: float = 0.0
    success: bool = True
    error: Optional[str] = None
    
    @property
    def severity_counts(self) -> Dict[Severity, int]:
        counts = defaultdict(int)
        for f in self.findings:
            counts[f.severity] += 1
        return dict(counts)
    
    @property
    def type_counts(self) -> Dict[FindingType, int]:
        counts = defaultdict(int)
        for f in self.findings:
            counts[f.finding_type] += 1
        return dict(counts)
    
    def get_findings_by_severity(self, severity: Severity) -> List[Finding]:
        return [f for f in self.findings if f.severity == severity]
    
    def get_findings_by_type(self, finding_type: FindingType) -> List[Finding]:
        return [f for f in self.findings if f.finding_type == finding_type]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "file_path": self.file_path,
            "timestamp": self.timestamp,
            "findings": [f.to_dict() for f in self.findings],
            "metrics": self.metrics,
            "execution_time_seconds": self.execution_time_seconds,
            "success": self.success,
            "error": self.error,
            "severity_counts": {k.value: v for k, v in self.severity_counts.items()},
            "type_counts": {k.value: v for k, v in self.type_counts.items()},
        }


class StaticAnalyzer:
    """
    Static code analyzer for security and quality.
    
    Uses AST-based analysis and external tools for comprehensive
    code review of self-generated or modified code.
    """
    
    def __init__(self, config: Optional[AnalysisConfig] = None):
        self.config = config or AnalysisConfig()
        self._analyzers = [
            self._analyze_security,
            self._analyze_quality,
            self._analyze_performance,
            self._analyze_correctness,
            self._analyze_best_practices,
            self._analyze_self_modification,
        ]
        
        # External tool availability
        self._bandit_available = self._check_tool("bandit")
        self._pylint_available = self._check_tool("pylint")
        self._mypy_available = self._check_tool("mypy")
        self._flake8_available = self._check_tool("flake8")
        
        logger.info(f"StaticAnalyzer initialized (bandit: {self._bandit_available}, "
                   f"pylint: {self._pylint_available}, mypy: {self._mypy_available})")
    
    def _check_tool(self, tool: str) -> bool:
        """Check if external tool is available."""
        try:
            subprocess.run([tool, "--version"], capture_output=True, timeout=5)
            return True
        except Exception:
            return False
    
    def analyze_file(self, file_path: str) -> AnalysisResult:
        """Analyze a single Python file."""
        start_time = datetime.now()
        path = Path(file_path)
        
        if not path.exists():
            return AnalysisResult(
                file_path=file_path,
                success=False,
                error=f"File not found: {file_path}",
            )
        
        # Check exclusions
        for pattern in self.config.exclude_patterns:
            if path.match(pattern):
                return AnalysisResult(
                    file_path=file_path,
                    findings=[],
                    metrics={"skipped": True, "reason": f"Matches exclusion pattern: {pattern}"},
                )
        
        # Read source
        try:
            source = path.read_text()
        except Exception as e:
            return AnalysisResult(
                file_path=file_path,
                success=False,
                error=f"Failed to read file: {e}",
            )
        
        # Parse AST
        try:
            tree = ast.parse(source, filename=file_path)
        except SyntaxError as e:
            return AnalysisResult(
                file_path=file_path,
                success=False,
                error=f"Syntax error: {e}",
findings=[Finding(
                        finding_id=f"syntax_{uuid.uuid4().hex[:8]}",
                        finding_type=FindingType.TYPE_MISMATCH,
                        severity=Severity.ERROR,
                        file_path=file_path,
                        line_number=e.lineno or 0,
                        column=e.offset or 0,
                        message=f"Syntax error: {e.msg}",
                    )],
            )
        
        # Run all analyzers
        all_findings = []
        
        for analyzer in self._analyzers:
            if self._should_run_analyzer(analyzer):
                try:
                    findings = analyzer(tree, source, file_path)
                    all_findings.extend(findings)
                except Exception as e:
                    logger.error(f"Analyzer {analyzer.__name__} failed: {e}")
        
        # Run external tools
        external_findings = self._run_external_tools(file_path)
        all_findings.extend(external_findings)
        
        # Filter by severity
        all_findings = [f for f in all_findings if self._severity_meets_threshold(f.severity)]
        
        # Calculate metrics
        metrics = self._calculate_metrics(tree, source)
        
        execution_time = (datetime.now() - datetime.fromtimestamp(start_time.timestamp())).total_seconds()
        
        return AnalysisResult(
            file_path=file_path,
            findings=all_findings,
            metrics=metrics,
            execution_time_seconds=execution_time,
        )
    
    def _should_run_analyzer(self, analyzer: Callable) -> bool:
        """Check if analyzer should run based on config."""
        name = analyzer.__name__
        if "security" in name:
            return self.config.enable_security_checks
        elif "quality" in name:
            return self.config.enable_quality_checks
        elif "performance" in name:
            return self.config.enable_performance_checks
        elif "correctness" in name:
            return self.config.enable_correctness_checks
        elif "best_practices" in name:
            return self.config.enable_best_practice_checks
        elif "self_modification" in name:
            return self.config.enable_self_modification_checks
        return True
    
    def _severity_meets_threshold(self, severity: Severity) -> bool:
        """Check if severity meets minimum threshold."""
        severity_order = [Severity.INFO, Severity.WARNING, Severity.ERROR, Severity.CRITICAL]
        return severity_order.index(severity) >= severity_order.index(self.config.min_severity)
    
    # Analyzer implementations
    
    def _analyze_security(self, tree: ast.AST, source: str, file_path: str) -> List[Finding]:
        """Analyze for security vulnerabilities."""
        findings = []
        
        for node in ast.walk(tree):
            # SQL Injection
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ("execute", "executemany", "cursor"):
                        # Check for string formatting in SQL
                        for arg in node.args:
                            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Mod):
                                findings.append(self._make_finding(
                                    FindingType.SQL_INJECTION,
                                    Severity.HIGH,
                                    file_path,
                                    node.lineno,
                                    node.col_offset,
                                    "Possible SQL injection via string formatting",
                                    "Use parameterized queries instead",
                                    source,
                                ))
                
                # Command Injection
                if isinstance(node.func, ast.Name):
                    if node.func.id in ("system", "popen", "run", "call"):
                        for arg in node.args:
                            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                                findings.append(self._make_finding(
                                    FindingType.COMMAND_INJECTION,
                                    Severity.CRITICAL,
                                    file_path,
                                    node.lineno,
                                    node.col_offset,
                                    "Possible command injection",
                                    "Use subprocess with shell=False and list arguments",
                                    source,
                                ))
            
            # eval/exec usage
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in ("eval", "exec", "compile"):
                        findings.append(self._make_finding(
                            FindingType.EVAL_EXEC_USAGE,
                            Severity.HIGH,
                            file_path,
                            node.lineno,
                            node.col_offset,
                            f"Use of {node.func.id}() is dangerous",
                            "Avoid dynamic code execution; use safer alternatives",
                            source,
                        ))
            
            # Hardcoded secrets
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name):
                        name = target.id.lower()
                        if any(secret in name for secret in ["password", "secret", "key", "token", "api"]):
                            if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                                if len(node.value.value) > 8:
                                    findings.append(self._make_finding(
                                        FindingType.HARDCODED_SECRET,
                                        Severity.CRITICAL,
                                        file_path,
                                        node.lineno,
                                        node.col_offset,
                                        f"Possible hardcoded secret: {target.id}",
                                        "Use environment variables or secret managers",
                                        source,
                                    ))
            
            # Path traversal
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ("open", "read", "write", "read_text", "write_text"):
                        for arg in node.args:
                            if isinstance(arg, ast.BinOp) and isinstance(arg.op, ast.Add):
                                # Check for path concatenation with user input
                                pass
        
        return findings
    
    def _analyze_quality(self, tree: ast.AST, source: str, file_path: str) -> List[Finding]:
        """Analyze code quality issues."""
        findings = []
        lines = source.split('\n')
        
        for node in ast.walk(tree):
            # Long functions
            if isinstance(node, ast.FunctionDef):
                func_lines = node.end_lineno - node.lineno + 1 if node.end_lineno else 0
                if func_lines > self.config.max_function_lines:
                    findings.append(self._make_finding(
                        FindingType.LONG_FUNCTION,
                        Severity.WARNING,
                        file_path,
                        node.lineno,
                        node.col_offset,
                        f"Function '{node.name}' is {func_lines} lines (max: {self.config.max_function_lines})",
                        "Consider breaking into smaller functions",
                        source,
                    ))
                
                # Missing docstring
                if not ast.get_docstring(node):
                    findings.append(self._make_finding(
                        FindingType.MISSING_DOCSTRING,
                        Severity.INFO,
                        file_path,
                        node.lineno,
                        node.col_offset,
                        f"Function '{node.name}' missing docstring",
                        "Add docstring describing purpose, args, and returns",
                        source,
                    ))
                
                # Missing type hints
                if node.returns is None and any(arg.annotation is None for arg in node.args.args):
                    findings.append(self._make_finding(
                        FindingType.MISSING_TYPE_HINTS,
                        Severity.INFO,
                        file_path,
                        node.lineno,
                        node.col_offset,
                        f"Function '{node.name}' missing type hints",
                        "Add type annotations for parameters and return type",
                        source,
                    ))
            
            # High complexity (nested blocks)
            if isinstance(node, (ast.If, ast.For, ast.While, ast.Try)):
                depth = self._calculate_nesting_depth(node, tree)
                if depth > self.config.max_nesting_depth:
                    findings.append(self._make_finding(
                        FindingType.HIGH_COMPLEXITY,
                        Severity.WARNING,
                        file_path,
                        node.lineno,
                        node.col_offset,
                        f"Nesting depth {depth} exceeds maximum {self.config.max_nesting_depth}",
                        "Refactor to reduce nesting",
                        source,
                    ))
            
            # Unused imports (basic check)
            if isinstance(node, ast.Import):
                for alias in node.names:
                    # Simple check - would need full scope analysis for accuracy
                    pass
        
        # Check file length
        if len(lines) > self.config.max_file_lines:
            findings.append(self._make_finding(
                FindingType.LONG_FUNCTION,
                Severity.WARNING,
                file_path,
                1,
                0,
                f"File has {len(lines)} lines (max: {self.config.max_file_lines})",
                "Consider splitting into multiple modules",
                source,
            ))
        
        return findings
    
    def _analyze_performance(self, tree: ast.AST, source: str, file_path: str) -> List[Finding]:
        """Analyze performance issues."""
        findings = []
        
        for node in ast.walk(tree):
            # Inefficient loops
            if isinstance(node, ast.For):
                # Check for list comprehension opportunity
                if (isinstance(node.body, list) and len(node.body) == 1 
                    and isinstance(node.body[0], ast.Expr)
                    and isinstance(node.body[0].value, ast.Call)
                    and isinstance(node.body[0].value.func, ast.Attribute)
                    and node.body[0].value.func.attr == "append"):
                    findings.append(self._make_finding(
                        FindingType.INEFFICIENT_LOOP,
                        Severity.INFO,
                        file_path,
                        node.lineno,
                        node.col_offset,
                        "Loop with append could use list comprehension",
                        "Consider using list comprehension for better performance",
                        source,
                    ))
            
            # N+1 query pattern (simplified)
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr in ("filter", "get", "all", "first"):
                        # Could be N+1 if in a loop
                        pass
            
            # Blocking calls in async functions
            if isinstance(node, ast.AsyncFunctionDef):
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            if child.func.id in ("time.sleep", "requests.get", "requests.post"):
                                findings.append(self._make_finding(
                                    FindingType.BLOCKING_CALL,
                                    Severity.WARNING,
                                    file_path,
                                    child.lineno,
                                    child.col_offset,
                                    f"Blocking call {child.func.id} in async function",
                                    "Use async alternatives (asyncio.sleep, aiohttp)",
                                    source,
                                ))
        
        return findings
    
    def _analyze_correctness(self, tree: ast.AST, source: str, file_path: str) -> List[Finding]:
        """Analyze correctness issues."""
        findings = []
        
        for node in ast.walk(tree):
            # Possible null dereference
            if isinstance(node, ast.Attribute):
                if isinstance(node.value, ast.Name):
                    # Could be None - would need flow analysis
                    pass
            
            # Infinite loop detection
            if isinstance(node, ast.While):
                if isinstance(node.test, ast.Constant) and node.test.value is True:
                    has_break = any(isinstance(n, ast.Break) for n in ast.walk(node))
                    if not has_break:
                        findings.append(self._make_finding(
                            FindingType.INFINITE_LOOP,
                            Severity.WARNING,
                            file_path,
                            node.lineno,
                            node.col_offset,
                            "Possible infinite loop (while True without break)",
                            "Ensure loop has exit condition",
                            source,
                        ))
            
            # Off-by-one errors
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "range":
                    if len(node.args) >= 2:
                        if (isinstance(node.args[0], ast.Constant) and isinstance(node.args[1], ast.Constant)
                            and node.args[0].value == 1):
                            findings.append(self._make_finding(
                                FindingType.OFF_BY_ONE,
                                Severity.INFO,
                                file_path,
                                node.lineno,
                                node.col_offset,
                                "range(1, n) excludes n, consider range(n) or range(1, n+1)",
                                "Verify loop bounds",
                                source,
                            ))
            
            # Resource leak - file opened but not closed
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "open":
                    # Check if in with statement
                    parent = getattr(node, 'parent', None)
                    if not isinstance(parent, ast.With):
                        findings.append(self._make_finding(
                            FindingType.RESOURCE_LEAK,
                            Severity.WARNING,
                            file_path,
                            node.lineno,
                            node.col_offset,
                            "File opened without context manager",
                            "Use 'with open(...) as f:' to ensure closure",
                            source,
                        ))
        
        return findings
    
    def _analyze_best_practices(self, tree: ast.AST, source: str, file_path: str) -> List[Finding]:
        """Analyze best practice violations."""
        findings = []
        
        for node in ast.walk(tree):
            # Mutable default arguments
            if isinstance(node, ast.FunctionDef):
                for default in node.args.defaults:
                    if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                        findings.append(self._make_finding(
                            FindingType.MUTABLE_DEFAULT_ARG,
                            Severity.WARNING,
                            file_path,
                            node.lineno,
                            node.col_offset,
                            "Mutable default argument",
                            "Use None as default and create mutable inside function",
                            source,
                        ))
            
            # Bare except
            if isinstance(node, ast.ExceptHandler):
                if node.type is None:
                    findings.append(self._make_finding(
                        FindingType.BARE_EXCEPT,
                        Severity.WARNING,
                        file_path,
                        node.lineno,
                        node.col_offset,
                        "Bare except clause",
                        "Specify exception type(s) to catch",
                        source,
                    ))
            
            # Global variables
            if isinstance(node, ast.Global):
                for name in node.names:
                    findings.append(self._make_finding(
                        FindingType.GLOBAL_VARIABLE,
                        Severity.INFO,
                        file_path,
                        node.lineno,
                        node.col_offset,
                        f"Global variable '{name}'",
                        "Consider using dependency injection or class attributes",
                        source,
                    ))
            
            # Magic numbers
            if isinstance(node, ast.Constant):
                if isinstance(node.value, (int, float)) and node.value not in (0, 1, -1, 2, 10, 100):
                    # Skip if in allowed contexts
                    parent = getattr(node, 'parent', None)
                    if not (isinstance(parent, (ast.Assign, ast.AnnAssign)) and 
                           isinstance(parent.targets[0], ast.Name) and parent.targets[0].id.isupper()):
                        findings.append(self._make_finding(
                            FindingType.MAGIC_NUMBER,
                            Severity.INFO,
                            file_path,
                            getattr(node, 'lineno', 0),
                            getattr(node, 'col_offset', 0),
                            f"Magic number: {node.value}",
                            "Define as named constant",
                            source,
                        ))
        
        return findings
    
    def _analyze_self_modification(self, tree: ast.AST, source: str, file_path: str) -> List[Finding]:
        """Analyze self-modification patterns."""
        findings = []
        
        for node in ast.walk(tree):
            # Dynamic imports
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id == "__import__":
                    findings.append(self._make_finding(
                        FindingType.DYNAMIC_IMPORT,
                        Severity.WARNING,
                        file_path,
                        node.lineno,
                        node.col_offset,
                        "Dynamic import via __import__()",
                        "Use importlib.import_module() for clarity",
                        source,
                    ))
                
                # importlib usage
                if isinstance(node.func, ast.Attribute):
                    if node.func.attr == "import_module":
                        findings.append(self._make_finding(
                            FindingType.DYNAMIC_IMPORT,
                            Severity.INFO,
                            file_path,
                            node.lineno,
                            node.col_offset,
                            "Dynamic import via importlib",
                            "Ensure module name is validated",
                            source,
                        ))
            
            # Runtime code generation
            if isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in ("compile", "exec", "eval"):
                    findings.append(self._make_finding(
                        FindingType.RUNTIME_CODE_GENERATION,
                        Severity.HIGH,
                        file_path,
                        node.lineno,
                        node.col_offset,
                        "Runtime code generation",
                        "Avoid dynamic code execution; use metaprogramming patterns",
                        source,
                    ))
            
            # Self-modifying code patterns
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Attribute):
                        if target.attr in ("__code__", "__dict__", "__class__"):
                            findings.append(self._make_finding(
                                FindingType.SELF_MODIFYING_CODE,
                                Severity.CRITICAL,
                                file_path,
                                node.lineno,
                                node.col_offset,
                                "Self-modifying code detected",
                                "Avoid modifying code objects at runtime",
                                source,
                            ))
        
        return findings
    
    def _run_external_tools(self, file_path: str) -> List[Finding]:
        """Run external static analysis tools."""
        findings = []
        
        if self._bandit_available and self.config.use_bandit:
            findings.extend(self._run_bandit(file_path))
        
        if self._pylint_available and self.config.use_pylint:
            findings.extend(self._run_pylint(file_path))
        
        if self._mypy_available and self.config.use_mypy:
            findings.extend(self._run_mypy(file_path))
        
        if self._flake8_available and self.config.use_flake8:
            findings.extend(self._run_flake8(file_path))
        
        return findings
    
    def _run_bandit(self, file_path: str) -> List[Finding]:
        """Run bandit security linter."""
        findings = []
        try:
            result = subprocess.run(
                ["bandit", "-f", "json", file_path],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.stdout:
                import json
                data = json.loads(result.stdout)
                for issue in data.get("results", []):
                    findings.append(Finding(
                        finding_id=f"bandit_{uuid.uuid4().hex[:8]}",
                        finding_type=self._map_bandit_type(issue.get("test_id", "")),
                        severity=self._map_bandit_severity(issue.get("severity", "")),
                        file_path=file_path,
                        line_number=issue.get("line_number", 0),
                        column=issue.get("col_offset", 0),
                        message=issue.get("issue_text", ""),
                        code_snippet=issue.get("code", ""),
                        recommendation="Review bandit finding",
                        confidence=0.8,
                        metadata={"bandit_test_id": issue.get("test_id", "")},
                    ))
        except Exception as e:
            logger.debug(f"Bandit failed: {e}")
        return findings
    
    def _run_pylint(self, file_path: str) -> List[Finding]:
        """Run pylint code quality checker."""
        findings = []
        try:
            result = subprocess.run(
                ["pylint", "--output-format=json", file_path],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.stdout:
                import json
                data = json.loads(result.stdout)
                for issue in data:
                    findings.append(Finding(
                        finding_id=f"pylint_{uuid.uuid4().hex[:8]}",
                        finding_type=self._map_pylint_type(issue.get("message-id", "")),
                        severity=self._map_pylint_severity(issue.get("type", "")),
                        file_path=file_path,
                        line_number=issue.get("line", 0),
                        column=issue.get("column", 0),
                        message=issue.get("message", ""),
                        recommendation="Review pylint finding",
                        confidence=0.7,
                    ))
        except Exception as e:
            logger.debug(f"Pylint failed: {e}")
        return findings
    
    def _run_mypy(self, file_path: str) -> List[Finding]:
        """Run mypy type checker."""
        findings = []
        try:
            result = subprocess.run(
                ["mypy", "--output=json", file_path],
                capture_output=True,
                text=True,
                timeout=60,
            )
            if result.stdout:
                import json
                data = json.loads(result.stdout)
                for issue in data:
                    findings.append(Finding(
                        finding_id=f"mypy_{uuid.uuid4().hex[:8]}",
                        finding_type=FindingType.TYPE_MISMATCH,
                        severity=Severity.WARNING,
                        file_path=file_path,
                        line_number=issue.get("line", 0),
                        column=issue.get("column", 0),
                        message=issue.get("message", ""),
                        recommendation="Fix type annotation",
                        confidence=0.9,
                    ))
        except Exception as e:
            logger.debug(f"Mypy failed: {e}")
        return findings
    
    def _run_flake8(self, file_path: str) -> List[Finding]:
        """Run flake8 style checker."""
        findings = []
        try:
            result = subprocess.run(
                ["flake8", "--format=json", file_path],
                capture_output=True,
                text=True,
                timeout=30,
            )
            if result.stdout:
                import json
                for line in result.stdout.strip().split('\n'):
                    if line:
                        issue = json.loads(line)
                        findings.append(Finding(
                            finding_id=f"flake8_{uuid.uuid4().hex[:8]}",
                            finding_type=FindingType.MISSING_DOCSTRING,  # Default
                            severity=Severity.INFO,
                            file_path=file_path,
                            line_number=issue.get("line_number", 0),
                            column=issue.get("column_number", 0),
                            message=issue.get("text", ""),
                            recommendation="Fix style issue",
                            confidence=0.6,
                        ))
        except Exception as e:
            logger.debug(f"Flake8 failed: {e}")
        return findings
    
    def _make_finding(
        self,
        finding_type: FindingType,
        severity: Severity,
        file_path: str,
        line_number: int,
        column: int,
        message: str,
        recommendation: str,
        source: str,
    ) -> Finding:
        """Create a finding with code snippet."""
        lines = source.split('\n')
        snippet_start = max(0, line_number - 3)
        snippet_end = min(len(lines), line_number + 2)
        snippet = '\n'.join(lines[snippet_start:snippet_end])
        
        return Finding(
            finding_id=f"{finding_type.value}_{uuid.uuid4().hex[:8]}",
            finding_type=finding_type,
            severity=severity,
            file_path=file_path,
            line_number=line_number,
            column=column,
            message=message,
            code_snippet=snippet,
            recommendation=recommendation,
            confidence=0.8,
        )
    
    def _calculate_nesting_depth(self, node: ast.AST, tree: ast.AST) -> int:
        """Calculate nesting depth of a node."""
        depth = 0
        current = node
        while hasattr(current, 'parent') and current.parent:
            if isinstance(current.parent, (ast.If, ast.For, ast.While, ast.Try, ast.With, ast.AsyncWith)):
                depth += 1
            current = current.parent
        return depth
    
    def _calculate_metrics(self, tree: ast.AST, source: str) -> Dict[str, Any]:
        """Calculate code metrics."""
        lines = source.split('\n')
        
        functions = 0
        classes = 0
        imports = 0
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions += 1
            elif isinstance(node, ast.ClassDef):
                classes += 1
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                imports += 1
        
        return {
            "total_lines": len(lines),
            "non_empty_lines": len([l for l in lines if l.strip()]),
            "functions": functions,
            "classes": classes,
            "imports": imports,
        }
    
    def _map_bandit_type(self, test_id: str) -> FindingType:
        mapping = {
            "B601": FindingType.COMMAND_INJECTION,
            "B602": FindingType.COMMAND_INJECTION,
            "B603": FindingType.COMMAND_INJECTION,
            "B604": FindingType.COMMAND_INJECTION,
            "B605": FindingType.COMMAND_INJECTION,
            "B606": FindingType.COMMAND_INJECTION,
            "B607": FindingType.COMMAND_INJECTION,
            "B608": FindingType.COMMAND_INJECTION,
            "B609": FindingType.COMMAND_INJECTION,
            "B610": FindingType.SQL_INJECTION,
            "B611": FindingType.SQL_INJECTION,
        }
        return mapping.get(test_id, FindingType.WEAK_CRYPTO)
    
    def _map_bandit_severity(self, severity: str) -> Severity:
        mapping = {
            "HIGH": Severity.CRITICAL,
            "MEDIUM": Severity.ERROR,
            "LOW": Severity.WARNING,
        }
        return mapping.get(severity, Severity.WARNING)
    
    def _map_pylint_type(self, msg_id: str) -> FindingType:
        if msg_id.startswith("W"):
            return FindingType.HIGH_COMPLEXITY
        elif msg_id.startswith("E"):
            return FindingType.TYPE_MISMATCH
        elif msg_id.startswith("C"):
            return FindingType.MISSING_DOCSTRING
        return FindingType.MISSING_DOCSTRING
    
    def _map_pylint_severity(self, ptype: str) -> Severity:
        mapping = {
            "error": Severity.ERROR,
            "warning": Severity.WARNING,
            "convention": Severity.INFO,
            "refactor": Severity.WARNING,
        }
        return mapping.get(ptype, Severity.INFO)
    
    def analyze_directory(
        self,
        directory: str,
        pattern: str = "**/*.py",
    ) -> Dict[str, AnalysisResult]:
        """Analyze all Python files in a directory."""
        results = {}
        path = Path(directory)
        
        for file_path in path.glob(pattern):
            if file_path.is_file():
                results[str(file_path)] = self.analyze_file(str(file_path))
        
        return results