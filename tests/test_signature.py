"""Unit tests for signature.py."""

import pytest
import sys
from pathlib import Path

app_dir = Path(__file__).resolve().parent.parent / "app"
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

from log_parser import Failure
from signature import signature


def test_signature_deterministic():
    f1 = Failure(kind="test", message="assert 4 == 5", file="test_calc.py", line=10)
    f2 = Failure(kind="test", message="assert 4 == 5", file="test_calc.py", line=10)
    assert signature(f1) == signature(f2)


def test_signature_normalizes_numbers():
    # Two failures with different line/pid/thread numbers should have the EXACT same signature
    f1 = Failure(kind="test", message="assertion error on line 42 at process 1205", file="test_math.py")
    f2 = Failure(kind="test", message="assertion error on line 999 at process 8841", file="test_math.py")
    assert signature(f1) == signature(f2)


def test_signature_normalizes_memory_addresses():
    # Two failures with differing object pointers / memory addresses should match
    f1 = Failure(kind="runtime", message="Segfault in object at 0x7ffee1b2c450", file="core.py")
    f2 = Failure(kind="runtime", message="Segfault in object at 0x10a4b901a880", file="core.py")
    assert signature(f1) == signature(f2)


def test_signature_differentiates_different_files():
    f1 = Failure(kind="test", message="assert False", file="tests/test_a.py")
    f2 = Failure(kind="test", message="assert False", file="tests/test_b.py")
    assert signature(f1) != signature(f2)


def test_signature_differentiates_different_kinds():
    f1 = Failure(kind="lint", message="F401 imported but unused", file="src/main.py")
    f2 = Failure(kind="import", message="F401 imported but unused", file="src/main.py")
    assert signature(f1) != signature(f2)
