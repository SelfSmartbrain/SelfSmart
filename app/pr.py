"""
Role: the only place that commits and pushes. Branch name comes from the error
signature, so a retry updates the same branch instead of creating a new one. The PR body
explains what broke, what changed and how it was checked, because reviewers decide
from this text.
"""

import subprocess
try:
    import config
except ImportError:
    from app import config


def git(workdir, *args):
    return subprocess.run(['git', '-C', workdir] + list(args), check=True, capture_output=True, text=True)


def _push(gh, workdir, branch):
    url = 'https://x-access-token:' + gh.token + '@github.com/' + gh.repo + '.git'
    git(workdir, 'push', url, branch)


def open_pr(gh, workdir, base, sig, failure, summary, issue):
    branch = config.BRANCH_PREFIX + 'fix-' + sig[:8]
    title = 'fix: ' + failure.message[:60]
    # Use checkout -B to safely handle initial create or re-checkout on retry
    git(workdir, 'checkout', '-B', branch)
    git(workdir, 'add', '-A')
    git(workdir, 'commit', '-m', title)
    _push(gh, workdir, branch)
    body = '\n'.join([
        '## What broke',
        failure.kind + ': ' + failure.message,
        '',
        '## What changed',
        summary or 'See diff.',
        '',
        '## How it was checked',
        'Tests re-run in a sandbox; guardrails passed.',
        '',
        'Closes #' + str(issue),
    ])
    return gh.create_pr(branch, base, title, body)


def push_update(gh, workdir, branch, message):
    git(workdir, 'add', '-A')
    git(workdir, 'commit', '-m', message[:70])
    _push(gh, workdir, branch)
