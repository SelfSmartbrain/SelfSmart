"""
Autonomous Junior Engineer - Automated Codebase Reviewer, Security Auditor, and Bug Fixer.
"""

from __future__ import annotations

import ast
import json
import os
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Set


class Severity(str, Enum):
    CRITICAL = "CRITICAL"
    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"
    INFO = "INFO"


class Category(str, Enum):
    SECURITY = "SECURITY"
    BUG_RISK = "BUG_RISK"
    PERFORMANCE = "PERFORMANCE"
    CODE_SMELL = "CODE_SMELL"
    STYLE = "STYLE"
    TESTING = "TESTING"


@dataclass
class Issue:
    file_path: str
    line_number: int
    rule_id: str
    title: str
    description: str
    severity: Severity
    category: Category
    code_snippet: str = ""
    suggestion: str = ""
    auto_fixable: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["severity"] = self.severity.value
        d["category"] = self.category.value
        return d


@dataclass
class AuditReport:
    repo_path: str
    timestamp: str
    total_files_scanned: int
    total_loc: int
    issues: List[Issue] = field(default_factory=list)
    health_score: int = 100

    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.CRITICAL)

    @property
    def high_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.HIGH)

    @property
    def medium_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.MEDIUM)

    @property
    def low_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.LOW)

    @property
    def info_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.INFO)

    def calculate_health_score(self) -> int:
        # Base 100, deduction per severity
        penalty = (
            (self.critical_count * 25)
            + (self.high_count * 10)
            + (self.medium_count * 3)
            + (self.low_count * 1)
        )
        self.health_score = max(0, 100 - penalty)
        return self.health_score


class ASTIssueVisitor(ast.NodeVisitor):
    """AST Visitor detecting common bugs, code smells, and security anti-patterns."""

    def __init__(self, file_path: str, lines: List[str]):
        self.file_path = file_path
        self.lines = lines
        self.issues: List[Issue] = []

    def _get_snippet(self, line_num: int) -> str:
        if 1 <= line_num <= len(self.lines):
            return self.lines[line_num - 1].strip()
        return ""

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        # Check mutable default arguments: def foo(x=[]) or def bar(x={})
        for default in node.args.defaults:
            if isinstance(default, (ast.List, ast.Dict, ast.Set)):
                self.issues.append(
                    Issue(
                        file_path=self.file_path,
                        line_number=default.lineno,
                        rule_id="BUG-001",
                        title="Mutable Default Argument",
                        description=f"Function '{node.name}' uses a mutable default argument ({type(default).__name__.lower()}).",
                        severity=Severity.HIGH,
                        category=Category.BUG_RISK,
                        code_snippet=self._get_snippet(default.lineno),
                        suggestion="Use 'None' as default value and initialize inside function body.",
                        auto_fixable=True,
                    )
                )

        # Check function complexity (> 80 lines)
        func_len = getattr(node, "end_lineno", node.lineno) - node.lineno
        if func_len > 80:
            self.issues.append(
                Issue(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    rule_id="SMELL-001",
                    title="High Function Complexity",
                    description=f"Function '{node.name}' is too long ({func_len} lines).",
                    severity=Severity.LOW,
                    category=Category.CODE_SMELL,
                    code_snippet=self._get_snippet(node.lineno),
                    suggestion="Refactor function into smaller helper functions.",
                    auto_fixable=False,
                )
            )

        # Check missing docstring for public functions
        if not node.name.startswith("_") and not ast.get_docstring(node):
            self.issues.append(
                Issue(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    rule_id="DOC-001",
                    title="Missing Public Function Docstring",
                    description=f"Public function '{node.name}' has no docstring.",
                    severity=Severity.INFO,
                    category=Category.STYLE,
                    code_snippet=self._get_snippet(node.lineno),
                    suggestion=f'Add a descriptive docstring summarizing what {node.name}() does.',
                    auto_fixable=True,
                )
            )

        self.generic_visit(node)

    def visit_ExceptHandler(self, node: ast.ExceptHandler) -> None:
        # Check bare except or except Exception: pass
        is_bare = node.type is None
        is_swallowing = False

        if len(node.body) == 1 and isinstance(node.body[0], ast.Pass):
            is_swallowing = True
        elif len(node.body) == 1 and isinstance(node.body[0], ast.Expr) and isinstance(node.body[0].value, ast.Constant):
            is_swallowing = True  # docstring or string inside except

        if is_bare:
            self.issues.append(
                Issue(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    rule_id="BUG-002",
                    title="Bare Except Clause",
                    description="Bare 'except:' catches KeyboardInterrupt, SystemExit, and obscure exceptions.",
                    severity=Severity.HIGH,
                    category=Category.BUG_RISK,
                    code_snippet=self._get_snippet(node.lineno),
                    suggestion="Catch specific exceptions like 'except Exception:' or specific error classes.",
                    auto_fixable=True,
                )
            )
        elif is_swallowing:
            self.issues.append(
                Issue(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    rule_id="BUG-003",
                    title="Silent Exception Swallowing",
                    description="Exception handler silently passes without logging or handling.",
                    severity=Severity.MEDIUM,
                    category=Category.BUG_RISK,
                    code_snippet=self._get_snippet(node.lineno),
                    suggestion="Log the exception with logger.warning/exception or handle it properly.",
                    auto_fixable=True,
                )
            )

        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        # Check dangerous calls: eval, exec
        func_name = ""
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
        elif isinstance(node.func, ast.Attribute):
            func_name = node.func.attr

        if func_name in ("eval", "exec"):
            self.issues.append(
                Issue(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    rule_id="SEC-001",
                    title=f"Dangerous Dynamic Code Execution ({func_name})",
                    description=f"Use of '{func_name}' allows arbitrary code execution.",
                    severity=Severity.CRITICAL,
                    category=Category.SECURITY,
                    code_snippet=self._get_snippet(node.lineno),
                    suggestion="Avoid eval/exec. Use ast.literal_eval for literals or structured parsing.",
                    auto_fixable=False,
                )
            )

        # Check subprocess with shell=True
        if func_name in ("Popen", "run", "call", "check_call", "check_output"):
            for kw in node.keywords:
                if kw.arg == "shell" and isinstance(kw.value, ast.Constant) and kw.value.value is True:
                    self.issues.append(
                        Issue(
                            file_path=self.file_path,
                            line_number=node.lineno,
                            rule_id="SEC-002",
                            title="Command Injection Risk (shell=True)",
                            description="subprocess invoked with shell=True is vulnerable to shell command injection.",
                            severity=Severity.HIGH,
                            category=Category.SECURITY,
                            code_snippet=self._get_snippet(node.lineno),
                            suggestion="Use shell=False and pass arguments as a list of strings.",
                            auto_fixable=True,
                        )
                    )

        # Check pickle.loads
        if func_name in ("loads", "load"):
            if isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                if node.func.value.id == "pickle":
                    self.issues.append(
                        Issue(
                            file_path=self.file_path,
                            line_number=node.lineno,
                            rule_id="SEC-003",
                            title="Insecure Deserialization (pickle)",
                            description="pickle deserialization from untrusted sources enables arbitrary code execution.",
                            severity=Severity.HIGH,
                            category=Category.SECURITY,
                            code_snippet=self._get_snippet(node.lineno),
                            suggestion="Use safer serialization formats like JSON, MessagePack, or Protocol Buffers.",
                            auto_fixable=False,
                        )
                    )

        # Check insecure hashing: md5, sha1
        if func_name in ("md5", "sha1"):
            self.issues.append(
                Issue(
                    file_path=self.file_path,
                    line_number=node.lineno,
                    rule_id="SEC-004",
                    title=f"Weak Cryptographic Hash ({func_name})",
                    description=f"{func_name.upper()} has known collision vulnerabilities.",
                    severity=Severity.MEDIUM,
                    category=Category.SECURITY,
                    code_snippet=self._get_snippet(node.lineno),
                    suggestion="Use SHA-256 (hashlib.sha256) or bcrypt/argon2 for passwords.",
                    auto_fixable=True,
                )
            )

        self.generic_visit(node)


class JuniorEngineer:
    """
    Autonomous Junior Engineer that scans codebases, identifies security vulnerabilities,
    detects code smells, suggests improvements, and generates remediation reports.
    """

    SECRET_PATTERNS = [
        (re.compile(r"""(?:api_key|apikey|secret|password|passwd|token|auth_token)\s*=\s*['"][a-zA-Z0-9_\-\.]{16,}['"]""", re.IGNORECASE), "SEC-005", "Hardcoded Secret / API Key", Severity.CRITICAL),
        (re.compile(r"""-----BEGIN (?:RSA |EC )?PRIVATE KEY-----"""), "SEC-006", "Exposed Private Key", Severity.CRITICAL),
        (re.compile(r"""ghp_[a-zA-Z0-9]{36}"""), "SEC-007", "Exposed GitHub Personal Access Token", Severity.CRITICAL),
        (re.compile(r"""sk-[a-zA-Z0-9]{48}"""), "SEC-008", "Exposed OpenAI / LLM Secret Key", Severity.CRITICAL),
    ]

    IGNORE_DIRS = {
        ".git",
        ".venv",
        "venv",
        ".venv-test",
        "__pycache__",
        "node_modules",
        ".pytest_cache",
        "dist",
        "build",
        ".next",
        "logs",
        ".cursor",
    }

    def __init__(self, repo_path: str = "."):
        self.repo_path = Path(repo_path).resolve()

    def scan_file(self, file_path: Path) -> List[Issue]:
        issues: List[Issue] = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception as e:
            return issues

        lines = content.splitlines()
        rel_path = str(file_path.relative_to(self.repo_path)) if file_path.is_relative_to(self.repo_path) else str(file_path)

        # 1. Regex & Pattern Checks (Secrets, etc.)
        for idx, line in enumerate(lines, start=1):
            for pattern, rule_id, title, severity in self.SECRET_PATTERNS:
                if pattern.search(line) and not line.strip().startswith("#"):
                    # Avoid false positives in test files or examples
                    if "example" in rel_path.lower() or "test" in rel_path.lower():
                        continue
                    issues.append(
                        Issue(
                            file_path=rel_path,
                            line_number=idx,
                            rule_id=rule_id,
                            title=title,
                            description=f"Potential exposed credential detected: '{pattern.pattern[:30]}...'",
                            severity=severity,
                            category=Category.SECURITY,
                            code_snippet=line.strip()[:80],
                            suggestion="Move secrets to environment variables (.env) or Secret Manager.",
                            auto_fixable=False,
                        )
                    )

            # Check unhandled TODOs or FIXMEs
            if re.search(r"""#\s*(?:TODO|FIXME|HACK|XXX):""", line, re.IGNORECASE):
                issues.append(
                    Issue(
                        file_path=rel_path,
                        line_number=idx,
                        rule_id="TODO-001",
                        title="Unresolved TODO / Technical Debt",
                        description=line.strip(),
                        severity=Severity.INFO,
                        category=Category.CODE_SMELL,
                        code_snippet=line.strip(),
                        suggestion="Address the TODO or track it in a GitHub issue.",
                        auto_fixable=False,
                    )
                )

        # 2. Python AST Checks
        if file_path.suffix == ".py":
            try:
                tree = ast.parse(content, filename=str(file_path))
                visitor = ASTIssueVisitor(rel_path, lines)
                visitor.visit(tree)
                issues.extend(visitor.issues)
            except SyntaxError as e:
                issues.append(
                    Issue(
                        file_path=rel_path,
                        line_number=e.lineno or 1,
                        rule_id="SYN-001",
                        title="Syntax Error",
                        description=f"SyntaxError: {e.msg}",
                        severity=Severity.CRITICAL,
                        category=Category.BUG_RISK,
                        code_snippet=lines[e.lineno - 1] if e.lineno and e.lineno <= len(lines) else "",
                        suggestion="Fix invalid Python syntax.",
                        auto_fixable=False,
                    )
                )

        return issues

    def scan_repository(
        self,
        target_path: Optional[str] = None,
        max_files: int = 1000,
    ) -> AuditReport:
        base_path = Path(target_path).resolve() if target_path else self.repo_path
        total_files = 0
        total_loc = 0
        all_issues: List[Issue] = []

        # If target is a single file
        if base_path.is_file():
            total_files = 1
            try:
                total_loc = len(base_path.read_text(encoding="utf-8", errors="ignore").splitlines())
            except Exception:
                pass
            all_issues.extend(self.scan_file(base_path))
        else:
            for root, dirs, files in os.walk(base_path):
                # Prune ignored directories in place
                dirs[:] = [d for d in dirs if d not in self.IGNORE_DIRS and not d.startswith(".")]

                for file in files:
                    if total_files >= max_files:
                        break
                    file_path = Path(root) / file
                    if file_path.suffix in (".py", ".js", ".ts", ".tsx", ".yaml", ".yml", ".json", ".sh"):
                        total_files += 1
                        try:
                            loc = len(file_path.read_text(encoding="utf-8", errors="ignore").splitlines())
                            total_loc += loc
                        except Exception:
                            pass

                        issues = self.scan_file(file_path)
                        all_issues.extend(issues)

        report = AuditReport(
            repo_path=str(base_path),
            timestamp=datetime.utcnow().isoformat() + "Z",
            total_files_scanned=total_files,
            total_loc=total_loc,
            issues=all_issues,
        )
        report.calculate_health_score()
        return report

    def generate_markdown_report(self, report: AuditReport) -> str:
        md = []
        md.append(f"# 🧑‍💻 Autonomous Junior Engineer — Codebase Audit Report")
        md.append(f"**Target Repository:** `{report.repo_path}`  ")
        md.append(f"**Generated At:** {report.timestamp}  ")
        md.append(f"**Files Scanned:** {report.total_files_scanned} | **Total LOC:** {report.total_loc:,}  ")
        md.append("")
        
        # Badge score
        score = report.health_score
        status_color = "🟢" if score >= 80 else ("🟡" if score >= 60 else "🔴")
        md.append(f"### {status_color} Repository Health Score: **{score}/100**")
        md.append("")
        md.append("| Severity | Count |")
        md.append("|---|---|")
        md.append(f"| 🚨 Critical | {report.critical_count} |")
        md.append(f"| ⚠️ High | {report.high_count} |")
        md.append(f"| 🟡 Medium | {report.medium_count} |")
        md.append(f"| ℹ️ Low / Info | {report.low_count + report.info_count} |")
        md.append(f"| **Total Issues** | **{len(report.issues)}** |")
        md.append("")

        if not report.issues:
            md.append("> 🎉 **Clean bill of health!** No security vulnerabilities or code smells detected.")
            return "\n".join(md)

        md.append("## 📋 Detected Issues & Recommendations")
        md.append("")

        # Group by severity
        for sev in [Severity.CRITICAL, Severity.HIGH, Severity.MEDIUM, Severity.LOW, Severity.INFO]:
            sev_issues = [i for i in report.issues if i.severity == sev]
            if not sev_issues:
                continue

            md.append(f"### {sev.value} ({len(sev_issues)})")
            md.append("")
            for idx, issue in enumerate(sev_issues, start=1):
                md.append(f"#### {idx}. [{issue.rule_id}] {issue.title}")
                md.append(f"- **Location:** `{issue.file_path}:{issue.line_number}`")
                md.append(f"- **Category:** `{issue.category.value}`")
                md.append(f"- **Details:** {issue.description}")
                if issue.code_snippet:
                    md.append(f"```python\n{issue.code_snippet}\n```")
                if issue.suggestion:
                    md.append(f"- 💡 **Junior Engineer Suggestion:** {issue.suggestion}")
                md.append("")

        return "\n".join(md)
