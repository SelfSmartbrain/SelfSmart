"""Unit tests for guardrails.py."""

import pytest
import subprocess
import tempfile
import sys
from pathlib import Path

app_dir = Path(__file__).resolve().parent.parent / "app"
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

import config
import guardrails


@pytest.fixture
def temp_repo():
    """Create a temporary git repository for guardrail testing."""
    d = tempfile.mkdtemp()
    subprocess.run(['git', 'init'], cwd=d, check=True, capture_output=True)
    subprocess.run(['git', 'config', 'user.name', 'test'], cwd=d, check=True)
    subprocess.run(['git', 'config', 'user.email', 'test@example.com'], cwd=d, check=True)

    # Initial commit with a test file
    test_file = Path(d) / "tests" / "test_sample.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(
        "def test_addition():\n    assert 1 + 1 == 2\n\ndef test_subtraction():\n    assert 2 - 1 == 1\n"
    )
    subprocess.run(['git', 'add', '-A'], cwd=d, check=True)
    subprocess.run(['git', 'commit', '-m', 'initial'], cwd=d, check=True)
    yield d


def test_guardrails_rejects_no_changes(temp_repo):
    allowed, reason = guardrails.check(temp_repo)
    assert not allowed
    assert reason == "no changes were made"


def test_guardrails_rejects_removed_test(temp_repo):
    test_file = Path(temp_repo) / "tests" / "test_sample.py"
    # Remove def test_subtraction
    test_file.write_text("def test_addition():\n    assert 1 + 1 == 2\n")
    allowed, reason = guardrails.check(temp_repo)
    assert not allowed
    assert reason == "a test was removed"


def test_guardrails_rejects_skipped_test(temp_repo):
    test_file = Path(temp_repo) / "tests" / "test_sample.py"
    test_file.write_text(
        "import pytest\n@pytest.mark.skip(reason='broken')\ndef test_addition():\n    assert 1 + 1 == 2\n"
    )
    allowed, reason = guardrails.check(temp_repo)
    assert not allowed
    assert reason == "tests must not be skipped"


def test_guardrails_rejects_blocked_path(temp_repo):
    # .github/ or auth/ or migrations/
    blocked = Path(temp_repo) / ".github" / "workflows" / "ci.yml"
    blocked.parent.mkdir(parents=True, exist_ok=True)
    blocked.write_text("name: CI\n")
    allowed, reason = guardrails.check(temp_repo)
    assert not allowed
    assert "blocked path" in reason


def test_guardrails_rejects_too_many_files(temp_repo):
    # Exceed MAX_FILES (5)
    for i in range(config.MAX_FILES + 1):
        f = Path(temp_repo) / f"module_{i}.py"
        f.write_text(f"# module {i}\n")
    allowed, reason = guardrails.check(temp_repo)
    assert not allowed
    assert reason == "too many files changed"


def test_guardrails_rejects_diff_too_large(temp_repo):
    # Exceed MAX_LINES (150)
    large_file = Path(temp_repo) / "large.py"
    large_file.write_text("\n".join(f"x_{i} = {i}" for i in range(config.MAX_LINES + 10)))
    allowed, reason = guardrails.check(temp_repo)
    assert not allowed
    assert reason == "diff too large"


def test_guardrails_accepts_clean_valid_fix(temp_repo):
    src_file = Path(temp_repo) / "calculator.py"
    src_file.write_text("def add(a, b):\n    return a + b\n")
    allowed, reason = guardrails.check(temp_repo)
    assert allowed
    assert reason == ""
