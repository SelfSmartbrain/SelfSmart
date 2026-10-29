"""
Role: the last gate before a PR. It checks the staged diff, not what the fixer claims. It
rejects: no change, too many files, blocked paths, oversized diff, removed tests, skipped
tests.
"""

import subprocess
try:
    import config
except ImportError:
    from app import config


def _git(workdir, *args):
    return subprocess.run(
        ['git', '-C', workdir] + list(args),
        capture_output=True,
        text=True,
    ).stdout


def check(workdir):
    _git(workdir, 'add', '-A')
    files = _git(workdir, 'diff', '--cached', '--name-only').split()
    diff = _git(workdir, 'diff', '--cached', '-U0')

    if not files:
        return False, 'no changes were made'
    if len(files) > config.MAX_FILES:
        return False, 'too many files changed'

    for f in files:
        if f.startswith(config.BLOCKED_PATHS):
            return False, 'blocked path: ' + f

    changed = [
        l for l in diff.splitlines()
        if l.startswith(('+', '-')) and not l.startswith(('+++', '---'))
    ]
    if len(changed) > config.MAX_LINES:
        return False, 'diff too large'

    for l in changed:
        if l.startswith('-') and 'def test_' in l:
            return False, 'a test was removed'
        if l.startswith('+') and ('skip' in l or 'xfail' in l):
            return False, 'tests must not be skipped'

    return True, ''
