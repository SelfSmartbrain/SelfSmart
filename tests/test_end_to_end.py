"""End-to-end integration tests for the Junior Engineering Agent."""

import hashlib
import hmac
import json
import os
import shutil
import subprocess
import tempfile
import pytest
import sys
from pathlib import Path
from fastapi.testclient import TestClient

app_dir = Path(__file__).resolve().parent.parent / "app"
if str(app_dir) not in sys.path:
    sys.path.insert(0, str(app_dir))

import config
import store
import orchestrator
import events
from main import app


@pytest.fixture(autouse=True)
def setup_test_db(tmp_path):
    """Use a temporary database for each test."""
    db_file = tmp_path / "test_agent.db"
    store.config.DB_PATH = str(db_file)
    # Re-initialize store db
    import sqlite3
    store.db = sqlite3.connect(str(db_file), check_same_thread=False)
    store.db.execute(
        'create table if not exists errors (sig text primary key, repo text, issue int, status text, attempts int default 0, pr_url text)'
    )
    store.db.execute('create table if not exists deliveries (id text primary key)')
    store.db.commit()
    yield
    store.db.close()


def make_signature(body: bytes, secret: str = config.WEBHOOK_SECRET) -> str:
    return "sha256=" + hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()


def test_webhook_hmac_verification():
    client = TestClient(app)
    payload = {"repository": {"full_name": "owner/repo"}}
    body = json.dumps(payload).encode()

    # 1. Bad signature -> 401
    resp = client.post(
        "/webhook",
        content=body,
        headers={"X-Hub-Signature-256": "sha256=invalid", "X-GitHub-Delivery": "del-1"},
    )
    assert resp.status_code == 401
    assert "bad signature" in resp.text

    # 2. Good signature -> 200
    valid_sig = make_signature(body)
    resp = client.post(
        "/webhook",
        content=body,
        headers={
            "X-Hub-Signature-256": valid_sig,
            "X-GitHub-Delivery": "del-1",
            "X-GitHub-Event": "ping",
        },
    )
    assert resp.status_code == 200
    assert resp.json() == {"status": "ignored"}

    # 3. Duplicate delivery -> duplicate status
    resp_dup = client.post(
        "/webhook",
        content=body,
        headers={
            "X-Hub-Signature-256": valid_sig,
            "X-GitHub-Delivery": "del-1",
            "X-GitHub-Event": "ping",
        },
    )
    assert resp_dup.status_code == 200
    assert resp_dup.json() == {"status": "duplicate"}


def test_loop_prevention_on_agent_branches():
    # If CI fails on a branch starting with agent/, events.to_job MUST return None
    payload = {
        "repository": {"full_name": "owner/repo"},
        "sender": {"type": "User"},
        "action": "completed",
        "workflow_run": {
            "id": 101,
            "conclusion": "failure",
            "head_branch": "agent/fix-12345678",
        },
    }
    job = events.to_job("workflow_run", payload)
    assert job is None  # Loop prevention active!


class MockGH:
    """Mock GitHub client simulating GitHub API calls."""

    def __init__(self, repo, sample_log=""):
        self.repo = repo
        self.token = "mock-token"
        self.sample_log = sample_log
        self.created_issues = []
        self.comments = []
        self.labels = []
        self.prs = []

    def run_log(self, run_id):
        return self.sample_log

    def create_issue(self, title, body, labels):
        num = len(self.created_issues) + 1
        self.created_issues.append({"number": num, "title": title, "body": body, "labels": labels})
        return num

    def comment(self, number, body):
        self.comments.append({"number": number, "body": body})

    def add_labels(self, number, labels):
        self.labels.append({"number": number, "labels": labels})

    def default_branch(self):
        return "main"

    def create_pr(self, head, base, title, body):
        pr_url = f"https://github.com/{self.repo}/pull/{len(self.prs) + 1}"
        self.prs.append({"head": head, "base": base, "title": title, "body": body, "url": pr_url})
        return pr_url


def test_full_pipeline_end_to_end(monkeypatch, tmp_path):
    """
    Test the entire pipeline from CI failure to PR creation:
    1. Parse log with missing dependency ('yaml')
    2. Flag issue
    3. Triage -> 'rule' route
    4. Sandbox clone
    5. MissingModuleFixer adds 'pyyaml' to requirements.txt
    6. Verifier proves fix
    7. Guardrails validate changes
    8. PR is committed, pushed, and opened
    """
    # Create a local test git repo to act as the target repository
    repo_dir = tmp_path / "target_repo"
    repo_dir.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=repo_dir, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Tester"], cwd=repo_dir, check=True)
    subprocess.run(["git", "config", "user.email", "tester@example.com"], cwd=repo_dir, check=True)

    # Initial files in target repo
    req_file = repo_dir / "requirements.txt"
    req_file.write_text("pytest\n")
    test_file = repo_dir / "tests" / "test_app.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text("def test_ok():\n    assert True\n")

    subprocess.run(["git", "add", "-A"], cwd=repo_dir, check=True)
    subprocess.run(["git", "commit", "-m", "init"], cwd=repo_dir, check=True)

    # Simulated CI log with missing module error
    ci_log = """
2024-01-01T10:00:00.0000000Z Traceback (most recent call last):
2024-01-01T10:00:00.0000000Z   File "app.py", line 1, in <module>
2024-01-01T10:00:00.0000000Z     import yaml
2024-01-01T10:00:00.0000000Z ModuleNotFoundError: No module named 'yaml'
"""
    mock_gh = MockGH(repo=str(repo_dir), sample_log=ci_log)

    # Monkeypatch GH in orchestrator to return our mock_gh
    monkeypatch.setattr(orchestrator, "GH", lambda repo: mock_gh)

    # Monkeypatch verifier.run to simulate verification check:
    # 1. On un-reproduced check (initial check): return False (bug is present)
    # 2. After fix: return True (clean test pass)
    step = {"count": 0}
    def mock_verifier_run(workdir, kind=""):
        req_content = (Path(workdir) / "requirements.txt").read_text()
        if "pyyaml" in req_content:
            return True, "1 passed in 0.05s"
        return False, "ModuleNotFoundError: No module named 'yaml'"

    monkeypatch.setattr(orchestrator.verifier, "run", mock_verifier_run)

    # Monkeypatch pr._push so it does not attempt network push to remote github.com
    monkeypatch.setattr(orchestrator.pr, "_push", lambda gh, workdir, branch: None)

    # Build the CI Job
    ci_job = {
        "kind": "ci",
        "repo": str(repo_dir),
        "run_id": 9999,
        "branch": "main",
    }

    # Execute orchestrator pipeline
    orchestrator.run_job(ci_job)

    # 1. Issue was flagged
    assert len(mock_gh.created_issues) == 1
    issue = mock_gh.created_issues[0]
    assert "[agent]" in issue["title"]
    assert "agent-flagged" in issue["labels"]

    # 2. PR was opened
    assert len(mock_gh.prs) == 1
    pr = mock_gh.prs[0]
    assert pr["head"].startswith("agent/fix-")
    assert pr["base"] == "main"
    assert "Closes #1" in pr["body"]

    # 3. Store status updated to pr_open
    stored = store.db.execute("select status, pr_url, attempts from errors").fetchone()
    assert stored is not None
    assert stored[0] == "pr_open"
    assert "pull/1" in stored[1]
    assert stored[2] == 1
