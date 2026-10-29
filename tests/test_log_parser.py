"""Unit tests for log_parser.py."""

import pytest
import sys
from pathlib import Path

# Add app directory to sys.path
app_dir = Path(__file__).resolve().parent.parent / "app"
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

from log_parser import parse, Failure


def test_parse_import_error():
    log = """
2024-01-01T12:00:00.0000000Z Traceback (most recent call last):
2024-01-01T12:00:00.0000000Z   File "main.py", line 1, in <module>
2024-01-01T12:00:00.0000000Z     import yaml
2024-01-01T12:00:00.0000000Z ModuleNotFoundError: No module named 'yaml'
"""
    f = parse(log)
    assert f.kind == "import"
    assert f.message == "yaml"
    assert "No module named" in f.excerpt


def test_parse_lint_error():
    log = """
2024-01-01T12:00:01.1234567Z src/utils.py:42:5: F401 'os' imported but unused
2024-01-01T12:00:01.1234567Z Found 1 error.
"""
    f = parse(log)
    assert f.kind == "lint"
    assert "F401 'os' imported but unused" in f.message
    assert f.file == "src/utils.py"
    assert f.line == 42


def test_parse_type_error():
    log = """
2024-01-01T12:00:02.0000000Z src/server.py:15: error: Incompatible return value type (got "int", expected "str")
2024-01-01T12:00:02.0000000Z Found 1 error in 1 file (checked 10 source files)
"""
    f = parse(log)
    assert f.kind == "type"
    assert f.message == 'Incompatible return value type (got "int", expected "str")'
    assert f.file == "src/server.py"
    assert f.line == 15


def test_parse_pytest_failure_with_details():
    log = """
=================================== FAILURES ===================================
__________________________________ test_calc ___________________________________
tests/test_math.py:10: in test_calc
    assert calc(2, 2) == 5
E   assert 4 == 5
=========================== short test summary info ============================
FAILED tests/test_math.py::test_calc - assert 4 == 5
============================== 1 failed in 0.12s ===============================
"""
    f = parse(log)
    assert f.kind == "test"
    assert f.file == "tests/test_math.py"
    assert f.message == "assert 4 == 5"


def test_parse_pytest_failure_without_dash():
    log = """
FAILED tests/test_api.py::test_login
"""
    f = parse(log)
    assert f.kind == "test"
    assert f.file == "tests/test_api.py"
    assert f.message == "test_login"


def test_parse_runtime_error():
    log = """
Traceback (most recent call last):
  File "app.py", line 5, in run
    raise ValueError: Invalid token configuration
ValueError: Invalid token configuration
"""
    f = parse(log)
    assert f.kind == "runtime"
    assert f.message == "ValueError: Invalid token configuration"


def test_parse_unknown_error():
    log = """
Build failed with exit code 137 (OOM killed)
"""
    f = parse(log)
    assert f.kind == "unknown"
    assert "exit code 137" in f.message
